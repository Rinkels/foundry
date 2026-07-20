"""Dispatch GitHub webhook events to Atlas actions.

Kept separate from the view so it's easy to unit-test with raw payload
dicts. The view is responsible for signature verification; everything
here assumes the payload is already trusted.

Deploys are run in a background thread because Cloud Build can take
minutes and GitHub expects a fast 2xx. This matches the project's current
"background jobs later" posture (no Celery/Cloud Tasks yet) — when a real
queue is added, swap `_spawn_deploy` for an enqueue call.
"""
from __future__ import annotations

from django.utils.text import slugify

from ..models import CloudProject, GitHubInstallation
from . import provisioner


def handle_event(event_type: str, payload: dict) -> dict:
    if event_type == "ping":
        return {"ok": True, "message": "pong"}
    if event_type in ("installation", "installation_repositories"):
        return _handle_installation(payload)
    if event_type == "push":
        return _handle_push(payload)
    return {"ok": True, "message": f"ignored event: {event_type}"}


# --------------------------------------------------------------------------- #

def _upsert_installation(payload: dict) -> GitHubInstallation | None:
    inst = payload.get("installation") or {}
    inst_id = inst.get("id")
    if not inst_id:
        return None
    account = inst.get("account") or {}
    obj, _ = GitHubInstallation.objects.update_or_create(
        installation_id=inst_id,
        defaults={
            "account_login": account.get("login", ""),
            "account_type": account.get("type", ""),
        },
    )
    return obj


def _ensure_project_for_repo(installation: GitHubInstallation, repo: dict) -> None:
    """Create a planning-stage CloudProject stub for a newly-added repo."""
    full_name = repo.get("full_name") or repo.get("name")
    if not full_name:
        return
    short = full_name.split("/")[-1]
    CloudProject.objects.get_or_create(
        github_repo=full_name,
        defaults={
            "name": short,
            "slug": slugify(full_name.replace("/", "-")),
            "origin": "internal",
            "status": "planning",
            "repo_url": f"https://github.com/{full_name}",
            "github_installation": installation,
            "auto_deploy": False,
        },
    )


def _handle_installation(payload: dict) -> dict:
    installation = _upsert_installation(payload)
    if installation is None:
        return {"ok": False, "message": "no installation in payload"}

    repos = payload.get("repositories") or payload.get("repositories_added") or []
    created = 0
    for repo in repos:
        _ensure_project_for_repo(installation, repo)
        created += 1
    return {"ok": True, "installation": installation.installation_id, "repos_seen": created}


def _handle_push(payload: dict) -> dict:
    repo = (payload.get("repository") or {})
    full_name = repo.get("full_name")
    ref = payload.get("ref", "")  # e.g. refs/heads/main
    if not full_name or not ref.startswith("refs/heads/"):
        return {"ok": True, "message": "ignored (not a branch push)"}

    branch = ref[len("refs/heads/"):]
    default_branch = repo.get("default_branch", "main")

    triggered = []
    projects = CloudProject.objects.filter(github_repo=full_name, auto_deploy=True)
    for project in projects:
        want = project.deploy_branch or default_branch
        if branch != want:
            continue
        provisioner.enqueue_deploy(project, user=None)
        triggered.append(project.slug)

    return {"ok": True, "branch": branch, "triggered": triggered}
