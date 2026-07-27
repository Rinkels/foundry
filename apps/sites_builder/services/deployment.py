import ftplib
import os
import shutil
import subprocess
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
        elif target.type == DeploymentTarget.TYPE_CF_PAGES:
            return self._deploy_cf_pages(target)
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

    def _deploy_cf_pages(self, target: DeploymentTarget):
        """Deploy via `npx wrangler pages deploy`. Auth comes from the host's
        wrangler OAuth login or a CLOUDFLARE_API_TOKEN env var (inherited)."""
        site_dir = self.base_output_dir / target.site.slug
        if not site_dir.exists():
            raise FileNotFoundError(f"Site output not found: {site_dir}")
        if not target.cf_project_name:
            raise ValueError("cf_project_name is required for Cloudflare Pages deployment.")

        # cwd = the site output dir: wrangler reads .env from its cwd, and
        # foundry's own .env holds a DNS-only token that can't deploy Pages.
        cmd = (f'npx wrangler pages deploy . '
               f'--project-name {target.cf_project_name} --branch main --commit-dirty=true')

        def run(env):
            return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                  encoding='utf-8', errors='replace',
                                  timeout=600, env=env, cwd=str(site_dir))

        result = run(None)  # inherit env: uses CLOUDFLARE_API_TOKEN if set
        combined = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0 and 'Authentication error' in combined \
                and os.environ.get('CLOUDFLARE_API_TOKEN'):
            # The env token may lack Pages permissions (e.g. DNS-only token);
            # retry with the host's wrangler OAuth login instead.
            env = os.environ.copy()
            env.pop('CLOUDFLARE_API_TOKEN', None)
            result = run(env)

        stdout = result.stdout or ""
        stderr = result.stderr or ""
        if result.returncode != 0:
            raise RuntimeError(
                f"wrangler deploy failed (exit {result.returncode}):\n"
                f"{stdout[-1000:]}\n{stderr[-1000:]}")
        return stdout.strip().splitlines()[-1] if stdout.strip() else "deployed"

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
