from collections import OrderedDict
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from .models import Initiative, InitiativeUpdate

# Display order + badge class for statuses
STATUS_ORDER = ["building", "live", "idea", "paused"]
STATUS_BADGE = {
    "building": "bg-info", "live": "bg-success", "idea": "bg-secondary",
    "paused": "bg-warning", "archived": "bg-dark",
}


@login_required
def dashboard(request):
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())   # Monday
    week_end = week_start + timedelta(days=6)               # Sunday

    inits = list(
        Initiative.objects.exclude(status="archived")
        .select_related("atlas_project", "site", "owner")
    )

    # Weekly roll-ups across all initiatives
    done_this_week = list(
        InitiativeUpdate.objects.filter(kind="done", occurred_on__range=(week_start, week_end))
        .select_related("initiative")
    )
    next_up = list(
        InitiativeUpdate.objects.filter(kind="next").select_related("initiative")[:30]
    )

    # Auto-activity: Atlas deploys this week for linked initiatives (attached to each obj)
    for it in inits:
        it.deploy_count = 0
    try:
        from apps.atlas.models import DeploymentRun
        for it in inits:
            if it.atlas_project_id:
                it.deploy_count = DeploymentRun.objects.filter(
                    cloud_project_id=it.atlas_project_id,
                    started_at__date__range=(week_start, week_end),
                ).count()
    except Exception:
        pass

    # Group initiatives by status (ordered)
    groups = OrderedDict((s, []) for s in STATUS_ORDER)
    for it in inits:
        groups.setdefault(it.status, []).append(it)
    groups = OrderedDict((s, v) for s, v in groups.items() if v)

    return render(request, "argus/dashboard.html", {
        "groups": groups,
        "initiatives": inits,
        "done_this_week": done_this_week,
        "next_up": next_up,
        "week_start": week_start,
        "week_end": week_end,
        "today": today,
        "total": len(inits),
    })


@login_required
@require_POST
def log_update(request):
    iid = request.POST.get("initiative")
    kind = request.POST.get("kind", "done")
    body = (request.POST.get("body") or "").strip()
    if not iid or not body:
        messages.error(request, "Pick an initiative and enter a note.")
        return redirect("argus:dashboard")
    it = Initiative.objects.filter(pk=iid).first()
    if not it:
        messages.error(request, "Initiative not found.")
        return redirect("argus:dashboard")
    valid_kinds = dict(InitiativeUpdate.KIND_CHOICES)
    u = InitiativeUpdate(
        initiative=it,
        kind=kind if kind in valid_kinds else "done",
        body=body,
        author=request.user,
    )
    d = parse_date(request.POST.get("occurred_on") or "")
    if d:
        u.occurred_on = d
    u.save()
    messages.success(request, f"Logged: {it.name} — {u.get_kind_display()}.")
    return redirect("argus:dashboard")


@login_required
def digest(request):
    from .services.digest import build_digest
    wk = parse_date(request.GET.get("week") or "")
    return render(request, "argus/digest.html", {"d": build_digest(wk)})
