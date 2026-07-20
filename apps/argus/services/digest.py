"""Build the Foundry weekly digest — shared by the Argus digest view and the
`argus_weekly_digest` management command."""
from __future__ import annotations

from collections import Counter
from datetime import timedelta

from django.utils import timezone

from ..models import Initiative, InitiativeUpdate


def week_bounds(ref=None):
    today = ref or timezone.localdate()
    start = today - timedelta(days=today.weekday())  # Monday
    return start, start + timedelta(days=6)           # Sunday


def build_digest(week_start=None) -> dict:
    if week_start is None:
        ws, we = week_bounds()
    else:
        ws, we = week_start, week_start + timedelta(days=6)

    done = list(
        InitiativeUpdate.objects.filter(kind="done", occurred_on__range=(ws, we))
        .select_related("initiative")
    )
    upcoming = list(
        InitiativeUpdate.objects.filter(kind="next").select_related("initiative")[:40]
    )
    new_inits = list(Initiative.objects.filter(created_at__date__range=(ws, we)))

    deploys = []
    try:
        from apps.atlas.models import DeploymentRun
        for it in Initiative.objects.filter(atlas_project__isnull=False).select_related("atlas_project"):
            c = DeploymentRun.objects.filter(
                cloud_project_id=it.atlas_project_id,
                started_at__date__range=(ws, we), status="success",
            ).count()
            if c:
                deploys.append((it, c))
    except Exception:
        pass

    counts = Counter(Initiative.objects.exclude(status="archived").values_list("status", flat=True))

    return {
        "week_start": ws, "week_end": we,
        "done": done, "next": upcoming, "new_inits": new_inits,
        "deploys": deploys, "status_counts": dict(counts),
        "prev_week": ws - timedelta(days=7), "next_week": ws + timedelta(days=7),
    }


def digest_text(d: dict) -> str:
    lines = [f"Foundry — week of {d['week_start']:%b %d}–{d['week_end']:%b %d}", ""]
    lines.append("Shipped this week:")
    if d["done"]:
        lines += [f"  - [{u.initiative.name}] {u.body}" for u in d["done"]]
    else:
        lines.append("  (nothing logged)")
    if d["deploys"]:
        lines += ["", "Deploys:"] + [f"  - {it.name}: {c} successful" for it, c in d["deploys"]]
    lines += ["", "Next up:"]
    if d["next"]:
        lines += [f"  - [{u.initiative.name}] {u.body}" for u in d["next"]]
    else:
        lines.append("  (none planned)")
    if d["new_inits"]:
        lines += ["", "New initiatives:"] + [f"  - {i.name}" for i in d["new_inits"]]
    lines += ["", "Portfolio: " + ", ".join(f"{k} {v}" for k, v in d["status_counts"].items())]
    return "\n".join(lines)
