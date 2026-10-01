from collections import OrderedDict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Exposure, WatchProfile, WatchRun
from .services import posture as posture_service
from .services import report as report_service
from .services import scan as scan_service

SEVERITY_ORDER = [
    Exposure.SEV_CRITICAL, Exposure.SEV_HIGH, Exposure.SEV_MEDIUM,
    Exposure.SEV_LOW, Exposure.SEV_INFO,
]


@login_required
def dashboard(request):
    profiles = list(
        WatchProfile.objects.select_related("credential", "cloud_project")
        .prefetch_related("runs")
    )

    for p in profiles:
        open_ex = p.exposures.filter(status__in=[Exposure.STATUS_NEW, Exposure.STATUS_TRIAGED])
        p.open_count = open_ex.count()
        p.critical_count = open_ex.filter(severity=Exposure.SEV_CRITICAL).count()
        p.high_count = open_ex.filter(severity=Exposure.SEV_HIGH).count()
        p.latest_run = p.runs.first()

    recent_runs = (
        WatchRun.objects.select_related("profile").order_by("-started_at")[:10]
    )

    return render(request, "aegis/dashboard.html", {
        "profiles": profiles,
        "recent_runs": recent_runs,
        "total_open": sum(p.open_count for p in profiles),
    })


@login_required
def profile_detail(request, slug):
    profile = get_object_or_404(
        WatchProfile.objects.select_related("credential", "cloud_project"), slug=slug
    )

    show_closed = request.GET.get("closed") == "1"
    qs = profile.exposures.all()
    if not show_closed:
        qs = qs.filter(status__in=[Exposure.STATUS_NEW, Exposure.STATUS_TRIAGED])

    groups = OrderedDict((s, []) for s in SEVERITY_ORDER)
    for ex in qs:
        groups.setdefault(ex.severity, []).append(ex)
    groups = OrderedDict((s, v) for s, v in groups.items() if v)

    return render(request, "aegis/profile_detail.html", {
        "profile": profile,
        "groups": groups,
        "severity_labels": dict(Exposure.SEVERITY_CHOICES),
        "status_choices": Exposure.STATUS_CHOICES,
        "latest_run": profile.runs.first(),
        "runs": profile.runs.all()[:10],
        "show_closed": show_closed,
        "total_shown": qs.count(),
    })


@login_required
@require_POST
def scan_now(request, slug):
    profile = get_object_or_404(WatchProfile, slug=slug)
    run = scan_service.run_scan(profile, triggered_by=request.user)

    if run.status == WatchRun.STATUS_FAILED:
        messages.error(request, f"Sweep failed — see the run log on {profile.name}.")
    else:
        msg = (
            f"Sweep complete: {run.queries_run} queries, {run.files_examined} files, "
            f"{run.findings_new} new finding{'' if run.findings_new == 1 else 's'}."
        )
        if run.queries_skipped:
            msg += f" {run.queries_skipped} queries skipped by the cap."
        messages.success(request, msg)

    return redirect("aegis:profile_detail", slug=profile.slug)


@login_required
@require_POST
def set_exposure_status(request, pk):
    exposure = get_object_or_404(Exposure, pk=pk)
    new_status = request.POST.get("status", "")

    if new_status not in dict(Exposure.STATUS_CHOICES):
        messages.error(request, "Unknown status.")
        return redirect("aegis:profile_detail", slug=exposure.profile.slug)

    from django.utils import timezone
    exposure.status = new_status
    exposure.resolved_at = timezone.now() if new_status == Exposure.STATUS_RESOLVED else None
    # Blank input leaves an existing note alone — the triage rationale is report
    # content, so losing it to an accidental empty submit would be costly.
    note = request.POST.get("triage_note", "").strip()
    if note:
        exposure.triage_note = note[:400]
    exposure.save(update_fields=["status", "resolved_at", "triage_note"])

    messages.success(request, f"Marked as {exposure.get_status_display().lower()}.")
    return redirect("aegis:profile_detail", slug=exposure.profile.slug)


@login_required
def report_pdf(request, slug):
    """Download the customer-facing one-pager."""
    profile = get_object_or_404(WatchProfile, slug=slug)
    pdf = report_service.build(
        profile,
        generated_by=getattr(settings, "AEGIS_REPORT_FOOTER", ""),
    )
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = (
        f'attachment; filename="{report_service.filename_for(profile)}"'
    )
    return resp


@login_required
@require_POST
def refresh_posture(request, slug):
    """Re-collect public-footprint stats. Cheap — uses the core API, not code search."""
    profile = get_object_or_404(WatchProfile, slug=slug)
    if not profile.org_list:
        messages.error(request, "Add a GitHub org to this profile first.")
        return redirect("aegis:profile_detail", slug=profile.slug)
    try:
        posture_service.collect(profile)
        messages.success(request, "Footprint posture refreshed.")
    except Exception as exc:  # noqa: BLE001 - surfaced to the user, not swallowed
        messages.error(request, f"Posture collection failed: {exc}")
    return redirect("aegis:profile_detail", slug=profile.slug)


@login_required
def run_log(request, pk):
    run = get_object_or_404(WatchRun.objects.select_related("profile"), pk=pk)
    return render(request, "aegis/run_log.html", {"run": run})
