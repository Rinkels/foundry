import ftplib
import shutil
from pathlib import Path
from typing import Optional
from django.conf import settings
from ..models import DeploymentTarget


class Deployer:
    def __init__(self, base_output_dir: Optional[Path] = None):
        if base_output_dir is None:
            base_output_dir = Path(settings.BASE_DIR) / "output" / "sites"
        self.base_output_dir = base_output_dir

    def deploy(self, target: DeploymentTarget):
        if target.type == DeploymentTarget.TYPE_FTP:
            return self._deploy_ftp(target)
        elif target.type == DeploymentTarget.TYPE_LOCAL:
            return self._deploy_local(target)
        else:
            raise ValueError(f"Unsupported deployment type: {target.type}")

    def _ftp_ensure_dir(self, ftp: ftplib.FTP, remote_dir_posix: str):
        """
        Ensure a remote directory exists on the FTP server.
        remote_dir_posix MUST use forward slashes, e.g. 'assets/css'.
        """
        remote_dir_posix = remote_dir_posix.strip("/")
        if not remote_dir_posix:
            return

        # Walk and create one segment at a time (most compatible approach)
        parts = remote_dir_posix.split("/")
        for part in parts:
            if not part:
                continue
            try:
                ftp.cwd(part)
            except ftplib.error_perm:
                # Doesn't exist; create then enter
                ftp.mkd(part)
                ftp.cwd(part)

    def _deploy_ftp(self, target: DeploymentTarget):
        site_dir = self.base_output_dir / target.site.slug
        if not site_dir.exists():
            raise FileNotFoundError(f"Site output not found: {site_dir}")

        with ftplib.FTP(target.ftp_host) as ftp:
            ftp.login(target.ftp_username, target.ftp_password)

            # Start at configured remote root (if any)
            if target.ftp_remote_root:
                # Important: remote roots should also be POSIX-ish
                ftp.cwd(str(target.ftp_remote_root).replace("\\", "/"))

            # Remember where "root" is so we can always return after mkdir/cwd
            root_pwd = ftp.pwd()

            # First create directories, then upload files (cleaner + fewer edge cases)
            for path in site_dir.rglob("*"):
                if path.is_dir():
                    rel_dir = path.relative_to(site_dir).as_posix()
                    if rel_dir:
                        ftp.cwd(root_pwd)
                        try:
                            self._ftp_ensure_dir(ftp, rel_dir)
                        except ftplib.error_perm:
                            # If server forbids creating some dir, surface the context
                            raise

            for path in site_dir.rglob("*"):
                if path.is_file():
                    rel_path_posix = path.relative_to(site_dir).as_posix()
                    remote_dir = str(Path(rel_path_posix).parent).replace("\\", "/")
                    remote_name = Path(rel_path_posix).name

                    ftp.cwd(root_pwd)
                    if remote_dir not in ("", "."):
                        self._ftp_ensure_dir(ftp, remote_dir)

                    with open(path, "rb") as f:
                        ftp.storbinary(f"STOR {remote_name}", f)

    def _deploy_local(self, target: DeploymentTarget):
        site_dir = self.base_output_dir / target.site.slug
        if not site_dir.exists():
            raise FileNotFoundError(f"Site output not found: {site_dir}")

        dest = Path(target.local_path)
        dest.mkdir(parents=True, exist_ok=True)

        for path in site_dir.rglob("*"):
            rel = path.relative_to(site_dir)
            target_path = dest / rel
            if path.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target_path)
