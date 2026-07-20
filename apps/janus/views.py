from __future__ import annotations


from .services import (
    get_dd_cockpit,
    get_dd_compare_payload,
    get_run_dashboard,
    promote_run_to_okrs,
)
from .views_pdf import build_risk_matrix
from django import forms
from django.db.models import Count
from .models import Idea, ValidationSprint, CustomerEvidence, DDResponse
from .models import GateResult
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from apps.mnemos.models import FileAttachment
from .services import get_dd_cockpit, get_run_dashboard
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class IdeaForm(forms.ModelForm):
    class Meta:
        model = Idea
        fields = ["entity", "proposed_strategy", "name", "problem_statement", "target_customer", "idea_type", "founder_conviction", "notes"]


class SprintForm(forms.ModelForm):
    class Meta:
        model = ValidationSprint
        fields = ["start_date", "duration_days", "budget_cap", "required_interviews", "pain_threshold"]


class EvidenceForm(forms.ModelForm):
    class Meta:
        model = CustomerEvidence
        fields = ["kind", "customer_name", "customer_org", "quote", "summary", "pain_intensity", "pain_frequency"]

@login_required
def dashboard(request):
    ideas = (
        Idea.objects
        .select_related("entity", "proposed_strategy")
        .annotate(hypothesis_count=Count("hypotheses"))
        .order_by("-updated_at")
    )
    dd_cards = get_dd_cockpit()[:6]  # show top 6 (adjust)
    return render(request, "janus/dashboard.html", {
        "ideas": ideas,
        "dd_cards": dd_cards,
    })

@login_required
def idea_create(request):
    if request.method == "POST":
        form = IdeaForm(request.POST)
        if form.is_valid():
            idea = form.save()
            return redirect("janus:idea_detail", pk=idea.pk)
    else:
        form = IdeaForm()
    return render(request, "janus/idea_form.html", {"form": form})

styles = getSampleStyleSheet()
H1 = styles["Heading1"]
H2 = styles["Heading2"]
H3 = styles["Heading3"]
N  = styles["BodyText"]



from reportlab.platypus import Image as RLImage, Table, TableStyle, Spacer
from reportlab.lib.units import inch


@login_required
def idea_detail(request, pk: int):
    idea = get_object_or_404(Idea, pk=pk)

    sprints = idea.sprints.order_by("-created_at")
    active_sprint = idea.active_sprint
    latest_sprint = sprints.first()

    sprint_for_stats = active_sprint or latest_sprint

    interview_count = sprint_for_stats.interview_count if sprint_for_stats else 0
    avg_pain = sprint_for_stats.avg_pain if sprint_for_stats else 0.0

    required_interviews = sprint_for_stats.required_interviews if sprint_for_stats else None
    pain_threshold = sprint_for_stats.pain_threshold if sprint_for_stats else None

    # Gate evaluation is meaningful if we have a sprint and at least one interview
    can_eval_gate1 = bool(sprint_for_stats) and interview_count > 0

    gate1_would_pass = False
    if sprint_for_stats and required_interviews is not None and pain_threshold is not None:
        gate1_would_pass = (interview_count >= required_interviews) and (avg_pain >= float(pain_threshold))

    pain_type = None
    if sprint_for_stats:
        summaries = sprint_for_stats.evidence.values_list("summary", flat=True)
        text = " ".join(summaries).lower()

        if "risk pain" in text or "eol" in text or "end-of-life" in text or "cobol" in text:
            pain_type = "Risk"
        elif "operational pain" in text:
            pain_type = "Operational"

    return render(
        request,
        "janus/idea_detail.html",
        {
            "idea": idea,
            "sprints": sprints,
            "active_sprint": active_sprint,
            "latest_sprint": latest_sprint,
            "interview_count": interview_count,
            "avg_pain": avg_pain,
            "required_interviews": required_interviews,
            "pain_threshold": pain_threshold,
            "can_eval_gate1": can_eval_gate1,
            "gate1_would_pass": gate1_would_pass,
            "pain_type": pain_type,
        },
    )

@login_required
def sprint_create(request, pk: int):
    idea = get_object_or_404(Idea, pk=pk)
    if request.method == "POST":
        form = SprintForm(request.POST)
        if form.is_valid():
            sprint = form.save(commit=False)
            sprint.idea = idea
            sprint.save()
            return redirect("janus:idea_detail", pk=idea.pk)
    else:
        form = SprintForm()
    return render(request, "janus/sprint_form.html", {"idea": idea, "form": form})

@login_required
def evidence_create(request, sprint_id: int):
    sprint = get_object_or_404(ValidationSprint, pk=sprint_id)
    if request.method == "POST":
        form = EvidenceForm(request.POST)
        if form.is_valid():
            ev = form.save(commit=False)
            ev.sprint = sprint
            ev.save()
            return redirect("janus:idea_detail", pk=sprint.idea.pk)
    else:
        form = EvidenceForm()
    return render(request, "janus/evidence_form.html", {"sprint": sprint, "form": form})

@login_required
@require_POST
def evaluate_gate_customer_pain(request, pk: int):
    idea = get_object_or_404(Idea, pk=pk)

    sprint = idea.active_sprint or idea.sprints.order_by("-created_at").first()
    if not sprint:
        GateResult.objects.update_or_create(
            idea=idea,
            gate=GateResult.Gate.CUSTOMER_PAIN,
            defaults={"passed": False, "rationale": "No sprint found. Create a sprint first."},
        )
        messages.error(request, "Gate 1 could not be evaluated: no sprint found.")
        return redirect("janus:idea_detail", pk=idea.pk)

    interview_count = sprint.interview_count
    avg_pain = sprint.avg_pain

    passed = (interview_count >= sprint.required_interviews) and (avg_pain >= sprint.pain_threshold)

    # Derive pain context from evidence summaries (no schema change)
    pain_context = "Unknown"
    if sprint:
        summaries = sprint.evidence.values_list("summary", flat=True)
        text = " ".join(summaries).lower()

        if "risk pain" in text or "cobol" in text or "eol" in text or "end-of-life" in text:
            pain_context = "Risk-driven (Cobol end-of-life)"
        elif "operational pain" in text:
            pain_context = "Operational"

    rationale = (
        f"Interviews: {interview_count}/{sprint.required_interviews}. "
        f"Avg pain: {avg_pain:.2f} (threshold {sprint.pain_threshold}). "
        f"Primary pain type: {pain_context}. "
        f"Sprint status: {sprint.status}."
    )

    GateResult.objects.update_or_create(
        idea=idea,
        gate=GateResult.Gate.CUSTOMER_PAIN,
        defaults={"passed": passed, "rationale": rationale},
    )

    if passed:
        messages.success(request, f"Gate 1 PASS. {rationale}")
    else:
        messages.warning(request, f"Gate 1 FAIL. {rationale}")

    return redirect("janus:idea_detail", pk=idea.pk)




@login_required
def dd_cockpit(request):
    cards = get_dd_cockpit()
    return render(request, "janus/dd_cockpit.html", {"cards": cards})


@login_required
def dd_compare(request):
    payload = get_dd_compare_payload()
    return render(request, "janus/dd_compare.html", payload)


@login_required
def dd_run_detail(request, run_id: int):
    payload = get_run_dashboard(run_id)
    payload["risk_matrix"] = build_risk_matrix(payload["risks"])
    return render(request, "janus/dd_run_detail.html", payload)


@login_required
@require_POST
def dd_run_promote(request, run_id: int):
    run = get_object_or_404(DueDiligenceRun, id=run_id)
    batch = promote_run_to_okrs(run, request.user)

    # mark run promoted for convenience
    run.promote_to_execution()

    messages.success(request, f"Promotion batch created (Batch #{batch.id}) with draft OKR items.")
    return redirect("janus:dd-run-detail", run_id=run.id)


@login_required
def dd_run_responses(request, run_id: int):
    run = get_object_or_404(DueDiligenceRun, id=run_id)

    qs = (
        DDResponse.objects
        .filter(run=run)
        .select_related("criterion", "criterion__section", "assessed_by")
        .order_by("criterion__section__order_index", "criterion__order_index", "criterion__id")
    )

    # Optional simple filters
    only_unknown = request.GET.get("unknown") == "1"
    only_nonneg = request.GET.get("nonneg") == "1"

    if only_unknown:
        # "Unknown" convention: score_value == 0 AND empty commentary
        qs = qs.filter(Q(score_value=0) & (Q(commentary="") | Q(commentary__isnull=True)))

    if only_nonneg:
        qs = qs.filter(criterion__non_negotiable=True)

    edit_id = request.GET.get("edit")
    selected_attachments = []

    ddresponse_ct = ContentType.objects.get_for_model(DDResponse)

    selected_attachments = []
    if edit_id:
        selected_attachments = (
            FileAttachment.objects.select_related("file_asset")
            .filter(content_type=ddresponse_ct, object_id=int(edit_id))
            .order_by("-created_at")
        )

    return render(request, "janus/dd_run_responses.html", {
        "run": run,
        "responses": qs,
        "only_unknown": only_unknown,
        "only_nonneg": only_nonneg,
        "selected_attachments": selected_attachments,
        "edit_id": edit_id,
        "ddresponse_ct_id": ddresponse_ct.id,
    })

@login_required
@require_POST
def dd_response_quick_update(request, response_id: int):
    r = get_object_or_404(DDResponse, id=response_id)

    # Basic fields
    score_value = request.POST.get("score_value", "").strip()
    confidence = request.POST.get("confidence", "").strip()
    commentary = request.POST.get("commentary", "").strip()

    # Validate score
    try:
        score_value_int = int(score_value)
    except ValueError:
        messages.error(request, "Score must be a number.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    # Clamp to scale
    scale = r.criterion.scoring_scale
    score_value_int = max(scale.min_value, min(scale.max_value, score_value_int))

    r.score_value = score_value_int
    if confidence in [c[0] for c in r.Confidence.choices]:
        r.confidence = confidence
    r.commentary = commentary

    # Who assessed it
    r.assessed_by = request.user

    r.save()
    # Recalc run score
    r.run.recalc_scores(save=True)

    messages.success(request, "Response updated.")
    return redirect(request.META.get("HTTP_REFERER", f"/janus/dd/run/{r.run_id}/responses/"))

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import DueDiligenceRun, DDQuantitativeSnapshot


@login_required
@require_POST
def dd_snapshot_quick_update(request, run_id: int):
    run = get_object_or_404(DueDiligenceRun, id=run_id)
    snap = getattr(run, "snapshot", None)

    if not snap:
        snap = DDQuantitativeSnapshot.objects.create(run=run)

    def parse_int(val):
        val = (val or "").strip()
        if val == "":
            return None
        return int(val)

    def parse_decimal(val):
        val = (val or "").strip()
        if val == "":
            return None
        return val  # Django DecimalField can accept string

    def parse_date(val):
        val = (val or "").strip()
        return val or None  # "YYYY-MM-DD" or None

    # Meta
    snap.metrics_as_of_date = parse_date(request.POST.get("metrics_as_of_date"))
    conf = (request.POST.get("confidence") or "").strip()
    if conf in dict(DDQuantitativeSnapshot.Confidence.choices):
        snap.confidence = conf
    snap.source_notes = (request.POST.get("source_notes") or "").strip()

    # Commercial
    snap.total_customers = parse_int(request.POST.get("total_customers"))
    snap.active_customers = parse_int(request.POST.get("active_customers"))
    snap.top_1_customer_pct_revenue = parse_decimal(request.POST.get("top_1_customer_pct_revenue"))
    snap.top_3_customer_pct_revenue = parse_decimal(request.POST.get("top_3_customer_pct_revenue"))
    snap.avg_contract_value = parse_decimal(request.POST.get("avg_contract_value"))

    snap.churn_rate_pct = parse_decimal(request.POST.get("churn_rate_pct"))
    snap.net_revenue_retention_pct = parse_decimal(request.POST.get("net_revenue_retention_pct"))
    snap.win_rate_pct = parse_decimal(request.POST.get("win_rate_pct"))
    snap.sales_cycle_days = parse_int(request.POST.get("sales_cycle_days"))
    snap.pipeline_value = parse_decimal(request.POST.get("pipeline_value"))

    # Financial
    snap.revenue_ttm = parse_decimal(request.POST.get("revenue_ttm"))
    snap.mrr = parse_decimal(request.POST.get("mrr"))
    snap.arr = parse_decimal(request.POST.get("arr"))

    snap.gross_margin_pct = parse_decimal(request.POST.get("gross_margin_pct"))
    snap.operating_income_ttm = parse_decimal(request.POST.get("operating_income_ttm"))

    snap.burn_rate_monthly = parse_decimal(request.POST.get("burn_rate_monthly"))
    snap.runway_months = parse_int(request.POST.get("runway_months"))

    snap.save()

    messages.success(request, "Quantitative snapshot updated.")
    return redirect(request.META.get("HTTP_REFERER", f"/janus/dd/run/{run.id}/"))










