import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django.conf import settings

from .models import BackupRun, CloudProject
from .services import backup, backup_health, github, provisioner, webhooks
from .services import manage as mgmt


@login_required
def dashboard(request):
    projects = CloudProject.objects.prefetch_related("resources", "runs")
    return render(request, "atlas/dashboard.html", {"projects": projects})


@login_required
def backups(request):
    """Backups dashboard: recent BackupRuns + per-project 'back up now'."""
    runs = BackupRun.objects.select_related("cloud_project").all()[:100]
    projects = CloudProject.objects.order_by("name")
    return render(request, "atlas/backups.html", {"runs": runs, "projects": projects})


@login_required
@require_POST
def backup_now(request, slug):
    """Create a code-snapshot backup (git bundle) of one project's source."""
    project = get_object_or_404(CloudProject, slug=slug)
    run = backup.run_backup(project, user=request.user)
    if run.status == "success":
        messages.success(request, f"Backup complete (#{run.pk}) — {run.location}")
    else:
        messages.error(request, f"Backup failed (#{run.pk}) — see the log on the Backups page.")
    return redirect("atlas:backups")


@login_required
def project_detail(request, slug):
    project = get_object_or_404(CloudProject, slug=slug)
    return render(
        request,
        "atlas/project_detail.html",
        {
            "project": project,
            "resources": project.resources.all(),
            "runs": project.runs.all()[:20],
        },
    )


@login_required
def sync_status(request, slug):
    project = get_object_or_404(CloudProject, slug=slug)
    run = provisioner.sync_status(project, user=request.user)
    if run.status == "success":
        messages.success(request, "Status sync complete.")
    else:
        messages.error(request, f"Status sync failed: {run.log}")
    return redirect("atlas:project_detail", slug=project.slug)


@login_required
def deploy(request, slug):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    project = get_object_or_404(CloudProject, slug=slug)
    run = provisioner.enqueue_deploy(project, user=request.user)
    messages.success(request, f"Deploy queued (run #{run.pk}). Watch the run log below for progress.")
    return redirect("atlas:project_detail", slug=project.slug)


@login_required
@require_POST
def pull(request, slug):
    """Fetch the latest source locally for review/debugging — no deploy."""
    project = get_object_or_404(CloudProject, slug=slug)
    run, path = provisioner.pull_source(project, user=request.user)
    if run.status == "success":
        messages.success(request, f"Pulled latest source (run #{run.pk}). Ready for review at: {path}")
    else:
        messages.error(request, f"Pull failed (run #{run.pk}) — see the run log below.")
    return redirect("atlas:project_detail", slug=project.slug)


@login_required
def project_manage(request, slug):
    """Live management panel: health, revisions (+ rollback), recent logs, metrics."""
    project = get_object_or_404(CloudProject, slug=slug)
    overview = mgmt.service_overview(project)
    url = overview.get("url") if isinstance(overview, dict) else None
    health = mgmt.health_check(project, url)
    traffic = overview.get("traffic") if isinstance(overview, dict) else None
    revisions = mgmt.list_revisions(project, traffic=traffic)
    logs = mgmt.recent_logs(project)
    metrics = mgmt.metrics(project)
    rate = float(getattr(settings, "ATLAS_RUN_BLENDED_RATE", 0.0000253))
    cost = None
    if isinstance(metrics, dict) and metrics.get("has_data"):
        cost = metrics.get("billable_instance_sec", 0) * rate + metrics.get("requests", 0) / 1_000_000 * 0.40
    sql_backup_health = backup_health.project_backup_health(project)
    return render(request, "atlas/manage.html", {
        "project": project, "overview": overview, "health": health,
        "revisions": revisions, "logs": logs, "metrics": metrics, "cost": cost,
        "backup_health": sql_backup_health,
    })


@login_required
@require_POST
def project_rollback(request, slug):
    project = get_object_or_404(CloudProject, slug=slug)
    revision = (request.POST.get("revision") or "").strip()
    if not revision:
        messages.error(request, "No revision specified.")
        return redirect("atlas:project_manage", slug=project.slug)
    res = mgmt.rollback(project, revision)
    if getattr(res, "ok", False):
        messages.success(request, f"Rolled back: 100% traffic to {revision}.")
    else:
        messages.error(request, f"Rollback failed: {(getattr(res, 'output', '') or '')[-300:]}")
    return redirect("atlas:project_manage", slug=project.slug)


@login_required
@require_POST
def harden(request, slug):
    project = get_object_or_404(CloudProject, slug=slug)
    target = not project.hardened  # toggle
    ok, message = provisioner.set_hardened(project, target, user=request.user)
    if ok:
        messages.success(request, message)
    else:
        messages.error(request, f"Could not change hardening: {message}")
    return redirect("atlas:project_detail", slug=project.slug)


@csrf_exempt
@require_POST
def github_webhook(request):
    """Receive GitHub App webhooks: verify signature, then dispatch."""
    signature = request.headers.get("X-Hub-Signature-256")
    if not github.verify_signature(request.body, signature):
        return HttpResponseForbidden("Invalid signature")

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return HttpResponseBadRequest("Invalid JSON")

    event_type = request.headers.get("X-GitHub-Event", "")
    result = webhooks.handle_event(event_type, payload)
    return JsonResponse(result)
