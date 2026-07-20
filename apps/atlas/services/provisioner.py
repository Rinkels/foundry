"""Provisioning / deploy / status-sync actions for a CloudProject.

The quickest-path implementation: Atlas shells out to the locally
installed `gcloud` and `git` CLIs (see shell.py) rather than the Python
SDKs. The operator must be logged in (`gcloud auth login` /
`gcloud auth application-default login`) on the host running this.

Every action records a DeploymentRun so the dashboard shows what was
attempted, by whom, when, and the full CLI output.
"""
from __future__ import annotations

import re
import shutil
import threading
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import connections
from django.utils import timezone

from ..models import CloudCredential, CloudProject, CloudResource, DeploymentRun
from . import github, shell

# Cloud Run service names: lowercase letters, digits, hyphens; must start
# with a letter; max 63 chars.
_SERVICE_NAME_RE = re.compile(r"[^a-z0-9-]")


def _service_name(cloud_project: CloudProject) -> str:
    name = _SERVICE_NAME_RE.sub("-", cloud_project.slug.lower()).strip("-")
    if not name or not name[0].isalpha():
        name = f"app-{name}".strip("-")
    return name[:63]


def _project_id(cloud_project: CloudProject) -> str:
    if cloud_project.gcp_project_id:
        return cloud_project.gcp_project_id
    if cloud_project.credential and cloud_project.credential.gcp_project_id:
        return cloud_project.credential.gcp_project_id
    return getattr(settings, "GCP_PROJECT_ID", "")


def _auth(cloud_project: CloudProject) -> tuple[list[str], dict[str, str]]:
    """Return (extra gcloud args, extra env) for this project's GCP identity.

    Empty/empty means "use the host's logged-in gcloud identity".
    """
    cred = cloud_project.credential
    if not cred:
        return [], {}
    if cred.method == CloudCredential.METHOD_IMPERSONATE and cred.service_account_email:
        return ["--impersonate-service-account", cred.service_account_email], {}
    if cred.method == CloudCredential.METHOD_KEY_FILE and cred.key_file_path:
        return [], {"CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE": cred.key_file_path}
    return [], {}


def _identity_label(cloud_project: CloudProject) -> str:
    cred = cloud_project.credential
    if not cred:
        return "host gcloud identity"
    if cred.method == CloudCredential.METHOD_IMPERSONATE:
        return f"impersonating {cred.service_account_email}"
    return f"key file {cred.key_file_path}"


def _region(cloud_project: CloudProject) -> str:
    return cloud_project.gcp_region or getattr(settings, "GCP_REGION", "us-central1")


def _work_root() -> Path:
    root = Path(getattr(settings, "ATLAS_WORK_ROOT", Path(settings.BASE_DIR) / "output" / "atlas"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _start_run(cloud_project: CloudProject, action: str, user=None) -> DeploymentRun:
    return DeploymentRun.objects.create(
        cloud_project=cloud_project,
        action=action,
        status="running",
        triggered_by=user,
    )


def _finish_run(run: DeploymentRun, status: str, log: str = "") -> DeploymentRun:
    run.status = status
    if log:
        run.log = (run.log + "\n" + log).strip()
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "log", "finished_at"])
    return run


def _append(run: DeploymentRun, text: str) -> None:
    run.log = (run.log + "\n" + text).strip()
    run.save(update_fields=["log"])


# --------------------------------------------------------------------------- #
# Source resolution (GitHub repo or local path)
# --------------------------------------------------------------------------- #

def resolve_source_dir(cloud_project: CloudProject, run: DeploymentRun) -> Path | None:
    """Return a local directory containing the project's source.

    Prefers a configured local `source_path`; otherwise clones/pulls the
    `repo_url` into ATLAS_WORK_ROOT/<slug>. Returns None (and logs) if
    neither yields a usable directory.
    """
    if cloud_project.source_path:
        path = Path(cloud_project.source_path)
        if path.exists():
            _append(run, f"Using local source: {path}")
            return path
        _append(run, f"Configured source_path does not exist: {path}")

    # Determine the clone URL: prefer a GitHub App installation token (works
    # for private repos), falling back to the plain repo_url (public repos).
    clone_url = cloud_project.repo_url
    if cloud_project.github_repo and cloud_project.github_installation_id:
        try:
            token = github.installation_token(cloud_project.github_installation.installation_id)
            clone_url = github.authed_clone_url(cloud_project.github_repo, token)
            _append(run, f"Using GitHub App installation token for {cloud_project.github_repo}")
        except Exception as exc:  # noqa: BLE001
            _append(run, f"Could not mint installation token ({exc}); falling back to repo_url.")

    if clone_url:
        dest = _work_root() / cloud_project.slug
        ok, used = _git_sync(dest, clone_url, _git_branch(cloud_project), run)
        if ok:
            _maybe_heal_branch(cloud_project, used, run)
            return dest
        _append(run, "git sync failed.")
        return None

    _append(run, "No source_path, github_repo, or repo_url configured for this project.")
    return None


def _redact(url: str) -> str:
    """Hide an installation token embedded in an https clone URL."""
    if url and "x-access-token:" in url:
        return re.sub(r"x-access-token:[^@]+@", "x-access-token:***@", url)
    return url or ""


def _log_res(run: DeploymentRun, res, secret: str | None = None) -> None:
    """Append a shell result to the run log, redacting an embedded token."""
    cmd, out = res.command, (res.output or "")
    if secret:
        cmd = cmd.replace(secret, _redact(secret))
        out = out.replace(secret, _redact(secret))
    _append(run, cmd)
    if out:
        _append(run, out)


def _git_branch(cloud_project: CloudProject) -> str:
    return (cloud_project.deploy_branch or "").strip()


def _remote_default_branch(dest: Path) -> str | None:
    """Return the remote's default branch short name (e.g. 'master'), or None."""
    shell.run(["git", "-C", str(dest), "remote", "set-head", "origin", "--auto"])
    res = shell.run(["git", "-C", str(dest), "symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
    if res.ok and res.output:
        name = res.output.strip()
        return name.split("/", 1)[1] if name.startswith("origin/") else name
    return None


def _cleanup_partial(dest: Path) -> None:
    """Remove a partial/empty dir left by a failed clone so a retry can proceed."""
    try:
        if dest.exists() and not (dest / ".git").exists():
            shutil.rmtree(dest, ignore_errors=True)
    except Exception:  # noqa: BLE001
        pass


def _maybe_heal_branch(cloud_project: CloudProject, used: str | None, run: DeploymentRun) -> None:
    """Persist the branch actually synced when it differs from the stored one, so
    a stale/blank deploy_branch self-corrects after the first successful sync."""
    if used and used != (cloud_project.deploy_branch or ""):
        old = cloud_project.deploy_branch or "(blank)"
        cloud_project.deploy_branch = used
        cloud_project.save(update_fields=["deploy_branch"])
        _append(run, f"Updated deploy_branch: {old} -> {used}.")


def _git_sync(dest: Path, clone_url: str | None, branch: str, run: DeploymentRun) -> tuple[bool, str | None]:
    """Robustly bring `dest` to the latest remote commit; returns (ok, branch_used).

    Existing clone: refresh the remote URL (so an expired embedded token is
    replaced), fetch, then HARD-RESET to origin/<branch> (survives force-pushes /
    non-fast-forward history that `pull --ff-only` chokes on). Fresh: clone.

    If the configured `branch` doesn't exist on the remote, fall back to the
    remote's DEFAULT branch (origin/HEAD) instead of hard-failing — e.g. a record
    set to 'main' against a 'master' repo still pulls. Returns the branch actually
    synced so the caller can self-heal a stale deploy_branch.
    Note: a hard reset discards uncommitted local edits in `dest`.
    """
    if (dest / ".git").exists():
        if clone_url:
            _log_res(run, shell.run(["git", "-C", str(dest), "remote", "set-url", "origin", clone_url]), clone_url)
        _log_res(run, shell.run(["git", "-C", str(dest), "fetch", "--prune", "origin"]), clone_url)
        if branch:
            used = branch
            res = shell.run(["git", "-C", str(dest), "reset", "--hard", f"origin/{branch}"])
            if not res.ok:  # configured branch may not exist on the remote
                default = _remote_default_branch(dest)
                if default and default != branch:
                    _append(run, f"origin/{branch} not found; falling back to default origin/{default}.")
                    used = default
                    res = shell.run(["git", "-C", str(dest), "reset", "--hard", f"origin/{default}"])
        else:
            used = _remote_default_branch(dest)
            res = shell.run(["git", "-C", str(dest), "reset", "--hard", "@{u}"])
        _log_res(run, res, clone_url)
        return (res.ok and dest.exists()), used

    # Fresh clone
    args = ["git", "clone"] + (["--branch", branch] if branch else []) + [clone_url, str(dest)]
    res = shell.run(args)
    _log_res(run, res, clone_url)
    used = branch or None
    if not res.ok and branch:  # configured branch likely doesn't exist — retry the repo default
        _cleanup_partial(dest)
        _append(run, f"Clone of branch '{branch}' failed; retrying with the repository's default branch.")
        res = shell.run(["git", "clone", clone_url, str(dest)])
        _log_res(run, res, clone_url)
        used = None
    if res.ok and dest.exists() and used is None:
        used = _remote_default_branch(dest)
    return (res.ok and dest.exists()), used


def pull_source(cloud_project: CloudProject, user=None) -> tuple[DeploymentRun, Path | None]:
    """Fetch the latest source WITHOUT deploying — for reviewing/debugging the
    newest code locally. Refreshes a local `source_path` clone in place, or the
    managed clone under ATLAS_WORK_ROOT/<slug>. Records a `pull` run."""
    run = _start_run(cloud_project, "pull", user)
    _append(run, f"Pull latest source requested by {getattr(user, 'email', None) or user or 'system'} (no deploy).")
    branch = _git_branch(cloud_project)

    # Local working clone (e.g. a third-party repo checked out for review)
    if cloud_project.source_path:
        path = Path(cloud_project.source_path)
        if (path / ".git").exists():
            _append(run, f"Refreshing local clone in place: {path}")
            _append(run, "Note: uncommitted local changes are discarded (hard reset to latest remote).")
            ok, used = _git_sync(path, None, branch, run)  # use the clone's own remote/creds
            _maybe_heal_branch(cloud_project, used, run)
            return _finish_pull(run, path if ok else None)
        if path.exists():
            _append(run, f"Local source is not a git repo (no .git): {path} — nothing to pull.")
            return _finish_pull(run, path)

    # Managed clone from repo_url / GitHub App installation token
    clone_url = cloud_project.repo_url
    if cloud_project.github_repo and cloud_project.github_installation_id:
        try:
            token = github.installation_token(cloud_project.github_installation.installation_id)
            clone_url = github.authed_clone_url(cloud_project.github_repo, token)
            _append(run, f"Using GitHub App installation token for {cloud_project.github_repo}")
        except Exception as exc:  # noqa: BLE001
            _append(run, f"Could not mint installation token ({exc}); falling back to repo_url.")
    if clone_url:
        dest = _work_root() / cloud_project.slug
        ok, used = _git_sync(dest, clone_url, branch, run)
        _maybe_heal_branch(cloud_project, used, run)
        return _finish_pull(run, dest if ok else None)

    _append(run, "No source_path, github_repo, or repo_url configured for this project.")
    return _finish_pull(run, None)


def _finish_pull(run: DeploymentRun, path: Path | None) -> tuple[DeploymentRun, Path | None]:
    if path and (path / ".git").exists():
        head = shell.run(["git", "-C", str(path), "log", "-1", "--pretty=format:%h  %an  %ad  %s", "--date=short"])
        if head.ok and head.output:
            _append(run, "HEAD now at: " + head.output.strip())
    if path:
        _finish_run(run, "success", f"Source ready for review at: {path}")
    else:
        _finish_run(run, "failed", "Pull failed — see log above.")
    return run, path


# --------------------------------------------------------------------------- #
# Actions
# --------------------------------------------------------------------------- #

def deploy_cloud_run(
    cloud_project: CloudProject,
    user=None,
    *,
    run: DeploymentRun | None = None,
    allow_unauthenticated: bool = True,
) -> DeploymentRun:
    """Build from source via Cloud Build and deploy to Cloud Run.

    Uses `gcloud run deploy --source <dir>`, which builds the container
    (from a Dockerfile if present, else buildpacks) and deploys it.

    If `run` is given (e.g. a pending job picked up by the worker), it's
    reused and marked running; otherwise a fresh run is created. This lets
    the same function back both the synchronous path and the queue worker.
    """
    if run is None:
        run = _start_run(cloud_project, "deploy", user)
    else:
        run.status = "running"
        if user and not run.triggered_by_id:
            run.triggered_by = user
        run.started_at = timezone.now()
        run.save(update_fields=["status", "triggered_by", "started_at"])

    cloud_project.status = "provisioning"
    cloud_project.save(update_fields=["status"])

    try:
        shell.resolve_tool("gcloud")  # fail fast with a clear message

        project_id = _project_id(cloud_project)
        if not project_id:
            return _finish_run(run, "failed", "No GCP project id (set on the project or GCP_PROJECT_ID in .env).")

        source_dir = resolve_source_dir(cloud_project, run)
        if source_dir is None:
            cloud_project.status = "failed"
            cloud_project.save(update_fields=["status"])
            return _finish_run(run, "failed", "Could not resolve source directory.")

        service = _service_name(cloud_project)
        region = _region(cloud_project)
        auth_args, auth_env = _auth(cloud_project)
        _append(run, f"Identity: {_identity_label(cloud_project)}")

        deploy_cmd = [
            "gcloud", "run", "deploy", service,
            "--source", str(source_dir),
            "--project", project_id,
            "--region", region,
            "--quiet",
            *auth_args,
        ]
        deploy_cmd.append("--allow-unauthenticated" if allow_unauthenticated else "--no-allow-unauthenticated")

        res = shell.run(deploy_cmd, timeout=getattr(settings, "ATLAS_DEPLOY_TIMEOUT", 1800), env=auth_env)
        _append(run, res.command)
        _append(run, res.output)

        if not res.ok:
            cloud_project.status = "failed"
            cloud_project.save(update_fields=["status"])
            return _finish_run(run, "failed", f"Deploy exited with code {res.returncode}.")

        # Fetch the clean service URL separately (combined output above is noisy).
        url = ""
        describe = shell.run([
            "gcloud", "run", "services", "describe", service,
            "--project", project_id, "--region", region,
            "--format", "value(status.url)",
            *auth_args,
        ], env=auth_env)
        if describe.ok:
            url = describe.output.strip().splitlines()[-1].strip() if describe.output.strip() else ""

        resource, _ = CloudResource.objects.get_or_create(
            cloud_project=cloud_project,
            resource_type="cloud_run",
            name=service,
        )
        resource.identifier = url
        resource.status = "active"
        resource.config = {"region": region, "project_id": project_id, "source": str(source_dir)}
        resource.last_synced_at = timezone.now()
        resource.save()

        cloud_project.status = "deployed"
        cloud_project.save(update_fields=["status"])

        return _finish_run(run, "success", f"Deployed Cloud Run service '{service}'" + (f" → {url}" if url else ""))

    except shell.ToolNotFound as exc:
        cloud_project.status = "failed"
        cloud_project.save(update_fields=["status"])
        return _finish_run(run, "failed", str(exc))
    except Exception as exc:  # noqa: BLE001 - surface any error into the run log
        cloud_project.status = "failed"
        cloud_project.save(update_fields=["status"])
        return _finish_run(run, "failed", f"Unexpected error: {exc}")


# --------------------------------------------------------------------------- #
# Durable deploy queue (DB-backed)
# --------------------------------------------------------------------------- #

def enqueue_deploy(cloud_project: CloudProject, user=None) -> DeploymentRun:
    """Persist a pending deploy job and (optionally) kick it off immediately.

    The job is written to the DB first, so it survives a process restart
    and can be drained by the `atlas_worker` management command (which can
    run as a Cloud Run Job). When ATLAS_INLINE_WORKER is on (default), a
    background thread also processes it right away for zero-setup dev use.
    """
    run = DeploymentRun.objects.create(
        cloud_project=cloud_project,
        action="deploy",
        status="pending",
        triggered_by=user,
    )
    if getattr(settings, "ATLAS_INLINE_WORKER", True):
        _process_async(run.pk)
    return run


def process_pending(limit: int | None = None) -> int:
    """Drain pending deploy jobs synchronously. Returns the number processed."""
    qs = DeploymentRun.objects.filter(action="deploy", status="pending").order_by("started_at")
    if limit:
        qs = qs[:limit]
    processed = 0
    for run in list(qs):
        # Claim it (cheap optimistic guard against double-processing).
        claimed = DeploymentRun.objects.filter(pk=run.pk, status="pending").update(status="running")
        if not claimed:
            continue
        run.refresh_from_db()
        deploy_cloud_run(run.cloud_project, run=run)
        processed += 1
    return processed


def reclaim_stale(older_than_seconds: int = 3600) -> int:
    """Reset runs stuck in 'running' (e.g. from a crashed worker) back to pending."""
    cutoff = timezone.now() - timedelta(seconds=older_than_seconds)
    return DeploymentRun.objects.filter(
        action="deploy", status="running", started_at__lt=cutoff
    ).update(status="pending")


def _process_async(run_pk: int) -> None:
    threading.Thread(target=_async_worker, args=(run_pk,), daemon=True).start()


def _async_worker(run_pk: int) -> None:
    try:
        claimed = DeploymentRun.objects.filter(pk=run_pk, status="pending").update(status="running")
        if not claimed:
            return
        run = DeploymentRun.objects.get(pk=run_pk)
        deploy_cloud_run(run.cloud_project, run=run)
    except DeploymentRun.DoesNotExist:
        pass
    finally:
        connections.close_all()


def set_hardened(cloud_project: CloudProject, hardened: bool, user=None) -> tuple[bool, str]:
    """Toggle the project's hardened flag and the live service's DEBUG env.

    Hardening sets DJANGO_DEBUG=False on the running Cloud Run service;
    un-hardening sets it back to True so you can read browser tracebacks
    while debugging. The flag (and hardened_at) is updated regardless; the
    gcloud env update only runs if the service is actually deployed.

    Returns (ok, message).
    """
    debug_val = "False" if hardened else "True"
    msg = f"DEBUG set to {debug_val}."

    deployed = cloud_project.resources.filter(resource_type="cloud_run").exists()
    if deployed:
        try:
            shell.resolve_tool("gcloud")
            project_id = _project_id(cloud_project)
            if not project_id:
                return False, "No GCP project id configured."
            service = _service_name(cloud_project)
            region = _region(cloud_project)
            auth_args, auth_env = _auth(cloud_project)
            res = shell.run([
                "gcloud", "run", "services", "update", service,
                "--project", project_id, "--region", region,
                "--update-env-vars", f"DJANGO_DEBUG={debug_val}",
                "--quiet", *auth_args,
            ], env=auth_env)
            if not res.ok:
                return False, f"Failed to update DEBUG on '{service}':\n{res.output[-600:]}"
        except shell.ToolNotFound as exc:
            return False, str(exc)
        except Exception as exc:  # noqa: BLE001
            return False, f"Unexpected error: {exc}"
    else:
        msg = "No deployed service yet — flag updated only."

    cloud_project.hardened = hardened
    cloud_project.save()  # save() stamps/clears hardened_at
    state = "hardened" if hardened else "un-hardened (debug on)"
    return True, f"Project {state}. {msg}"


def sync_status(cloud_project: CloudProject, user=None) -> DeploymentRun:
    """Refresh each Cloud Run resource's live URL/status from GCP."""
    run = _start_run(cloud_project, "sync_status", user)
    try:
        shell.resolve_tool("gcloud")
        project_id = _project_id(cloud_project)
        if not project_id:
            return _finish_run(run, "failed", "No GCP project id configured.")

        region = _region(cloud_project)
        auth_args, auth_env = _auth(cloud_project)
        checked = 0
        for resource in cloud_project.resources.filter(resource_type="cloud_run"):
            res = shell.run([
                "gcloud", "run", "services", "describe", resource.name,
                "--project", project_id, "--region", region,
                "--format", "value(status.url)",
                *auth_args,
            ], env=auth_env)
            _append(run, res.command)
            _append(run, res.output)
            if res.ok and res.output.strip():
                resource.identifier = res.output.strip().splitlines()[-1].strip()
                resource.status = "active"
            else:
                resource.status = "error"
            resource.last_synced_at = timezone.now()
            resource.save(update_fields=["identifier", "status", "last_synced_at"])
            checked += 1

        return _finish_run(run, "success", f"Synced {checked} Cloud Run resource(s).")
    except shell.ToolNotFound as exc:
        return _finish_run(run, "failed", str(exc))
    except Exception as exc:  # noqa: BLE001
        return _finish_run(run, "failed", f"Unexpected error: {exc}")
