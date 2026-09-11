"""Replay GitHub push webhooks that failed while Foundry was down.

The webhook receiver is Foundry's local runserver behind a Cloudflare tunnel.
When it isn't running, GitHub gets a 502 from the tunnel and — crucially —
does NOT retry, so the deploy is silently lost (this ate three crm deploys on
8–9 Sep 2026). GitHub keeps a delivery log, though, and lets us ask for a
redelivery. So on startup (and via `manage.py atlas_redeliver`) we look for
recent failed push deliveries to a deploy branch of an auto-deploy project
and replay them. A redelivery shows up as a new delivery with the same guid,
so once one attempt succeeds the guid is never replayed again.

Also home to the webhook-receiver health check the dashboard shows.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx
from django.conf import settings
from django.core.cache import cache

from ..models import CloudProject, DeploymentRun
from . import github

log = logging.getLogger(__name__)


@dataclass
class Missed:
    delivery_id: int
    guid: str
    delivered_at: str
    status_code: int
    repo: str
    branch: str
    commit: str
    project_slug: str


def _ok(status: int) -> bool:
    return 200 <= status < 300


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def deploy_targets() -> dict[str, set[str]]:
    """{github_repo: {branches that trigger a deploy}} for auto-deploy projects."""
    out: dict[str, set[str]] = {}
    for p in CloudProject.objects.filter(auto_deploy=True).exclude(github_repo=""):
        out.setdefault(p.github_repo, set()).add(p.deploy_branch or "main")
    return out


def find_missed(hours: int | None = None, deliveries: list[dict] | None = None) -> list[Missed]:
    """Failed push deliveries (last `hours`) whose guid never succeeded, that
    target a deploy branch of an auto-deploy project. One entry per guid."""
    hours = hours or getattr(settings, "ATLAS_REDELIVER_HOURS", 72)
    deliveries = github.list_deliveries(100) if deliveries is None else deliveries
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    succeeded = {d["guid"] for d in deliveries if _ok(d["status_code"])}
    targets = deploy_targets()

    seen: set[str] = set()
    missed: list[Missed] = []
    for d in deliveries:  # newest first
        if d.get("event") != "push" or _ok(d["status_code"]) or d["guid"] in succeeded or d["guid"] in seen:
            continue
        if _parse(d["delivered_at"]) < cutoff:
            continue
        seen.add(d["guid"])
        det = github.delivery_detail(d["id"])
        payload = (det.get("request") or {}).get("payload") or {}
        ref = payload.get("ref") or ""
        repo = (payload.get("repository") or {}).get("full_name") or ""
        if not ref.startswith("refs/heads/") or repo not in targets:
            continue
        branch = ref[len("refs/heads/"):]
        if branch not in targets[repo]:
            continue
        slug = (CloudProject.objects.filter(github_repo=repo, auto_deploy=True).values_list("slug", flat=True).first()) or ""
        # Atlas deploys current HEAD, not the pushed commit — so a successful
        # deploy AFTER this delivery already shipped it. Replaying would just
        # queue a redundant build.
        if DeploymentRun.objects.filter(
            cloud_project__slug=slug, action="deploy", status="success",
            finished_at__gt=_parse(d["delivered_at"]),
        ).exists():
            continue
        missed.append(Missed(
            delivery_id=d["id"], guid=d["guid"], delivered_at=d["delivered_at"], status_code=d["status_code"],
            repo=repo, branch=branch, commit=(payload.get("after") or "")[:7], project_slug=slug,
        ))
    return missed


def redeliver_missed(hours: int | None = None, *, dry_run: bool = False) -> dict:
    """Replay every missed delivery. Returns a summary safe to print/log."""
    missed = find_missed(hours)
    redelivered, errors = [], []
    for m in missed:
        label = f"{m.repo}@{m.branch} {m.commit} ({m.delivered_at}, HTTP {m.status_code})"
        if dry_run:
            continue
        try:
            if github.redeliver(m.delivery_id):
                redelivered.append(label)
            else:
                errors.append(f"{label}: GitHub did not accept the redelivery")
        except Exception as exc:  # noqa: BLE001 — one bad delivery mustn't stop the rest
            errors.append(f"{label}: {exc}")
    return {"found": [f"{m.repo}@{m.branch} {m.commit}" for m in missed],
            "redelivered": redelivered, "errors": errors, "dry_run": dry_run}


# --------------------------------------------------------------------------- #
# Webhook receiver health (for the dashboard)
# --------------------------------------------------------------------------- #

HEALTH_KEY = "atlas:webhook_health"
DELIVERIES_KEY = "atlas:recent_deliveries"


def webhook_health(*, force: bool = False) -> dict:
    """Probe the PUBLIC webhook URL (through the tunnel), the way GitHub does.
    405 = healthy (route exists, GET refused). 5xx / connection error = the
    tunnel is up but Foundry isn't listening on the port it forwards to."""
    if not force:
        cached = cache.get(HEALTH_KEY)
        if cached:
            return cached
    url = getattr(settings, "ATLAS_WEBHOOK_PUBLIC_URL", "")
    result: dict = {"url": url, "ok": False, "status": None, "detail": ""}
    if not url:
        result["detail"] = "ATLAS_WEBHOOK_PUBLIC_URL not set"
    else:
        try:
            r = httpx.get(url, timeout=6, follow_redirects=False)
            result["status"] = r.status_code
            result["ok"] = r.status_code < 500
            result["detail"] = "reachable" if result["ok"] else "tunnel up, origin not answering (is runserver on 8086?)"
        except httpx.HTTPError as exc:
            result["detail"] = f"unreachable: {exc.__class__.__name__}"
    cache.set(HEALTH_KEY, result, 60)
    return result


def recent_deliveries(limit: int = 12, *, force: bool = False) -> dict:
    """Recent push deliveries + which ones are still missed. Cached 5 min so
    the dashboard doesn't hammer the API."""
    if not force:
        cached = cache.get(DELIVERIES_KEY)
        if cached:
            return cached
    result: dict = {"deliveries": [], "missed": [], "error": ""}
    try:
        deliveries = github.list_deliveries(100)
        pushes = [d for d in deliveries if d.get("event") == "push"][:limit]
        result["deliveries"] = [{
            "delivered_at": d["delivered_at"], "status_code": d["status_code"],
            "ok": _ok(d["status_code"]), "redelivery": bool(d.get("redelivery")),
        } for d in pushes]
        result["missed"] = [m.__dict__ for m in find_missed(deliveries=deliveries)]
    except Exception as exc:  # noqa: BLE001 — GitHub being unreachable must not break the dashboard
        result["error"] = f"{exc.__class__.__name__}: {exc}"
    cache.set(DELIVERIES_KEY, result, 300)
    return result
