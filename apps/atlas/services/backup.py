"""Backup actions for a CloudProject.

MVP: a **code snapshot** = refresh the project's source, then create a
self-contained `git bundle --all` (full history, every branch, in one file)
under ATLAS_BACKUP_ROOT/<slug>/, with simple retention. Each run is recorded
as a BackupRun so the Atlas Backups view can show status/size/history.

Next step (not yet done): push the bundle off-machine (GCS) — a local bundle
alone would not survive a disk loss. The structure here makes that a small add.
"""
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.utils import timezone

from ..models import BackupRun, CloudProject
from . import provisioner, shell


def _backup_root() -> Path:
    root = Path(getattr(settings, "ATLAS_BACKUP_ROOT",
                        Path(settings.BASE_DIR) / "output" / "atlas" / "_backups"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _append(run: BackupRun, text: str) -> None:
    run.log = (run.log + "\n" + text).strip()
    run.save(update_fields=["log"])


def _finish(run: BackupRun, status: str, msg: str = "") -> BackupRun:
    run.status = status
    if msg:
        run.log = (run.log + "\n" + msg).strip()
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "log", "finished_at", "location", "size_bytes"])
    return run


def _prune(dest_dir: Path, keep: int, run: BackupRun) -> None:
    bundles = sorted(dest_dir.glob("*.bundle"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in bundles[keep:]:
        try:
            old.unlink()
            _append(run, f"Pruned old backup: {old.name}")
        except Exception:  # noqa: BLE001
            pass


def run_backup(cloud_project: CloudProject, user=None, keep: int = 7) -> BackupRun:
    """Create a git-bundle code snapshot of the project's source. Keeps the
    newest `keep` bundles per project."""
    run = BackupRun.objects.create(
        cloud_project=cloud_project, kind="code", status="running", triggered_by=user,
    )
    _append(run, f"Code backup requested by {getattr(user, 'email', None) or user or 'system'}.")
    try:
        # Refresh / clone the source (reuses Atlas's robust git logic).
        src = provisioner.resolve_source_dir(cloud_project, run)
        if not src or not (Path(src) / ".git").exists():
            return _finish(run, "failed", "No git source to bundle (need a repo or a git clone).")

        dest_dir = _backup_root() / cloud_project.slug
        dest_dir.mkdir(parents=True, exist_ok=True)
        stamp = timezone.now().strftime("%Y%m%d-%H%M%S")
        dest = dest_dir / f"{cloud_project.slug}-{stamp}.bundle"

        res = shell.run(["git", "-C", str(src), "bundle", "create", str(dest), "--all"])
        _append(run, res.command)
        if res.output:
            _append(run, res.output)
        if not res.ok or not dest.exists():
            return _finish(run, "failed", "git bundle failed — see log above.")

        run.location = str(dest)
        run.size_bytes = dest.stat().st_size
        _prune(dest_dir, keep, run)
        return _finish(run, "success", f"Bundle created: {dest.name} ({run.size_bytes:,} bytes)")
    except Exception as exc:  # noqa: BLE001
        return _finish(run, "failed", f"Backup error: {exc}")
