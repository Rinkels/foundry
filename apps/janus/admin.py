from django.contrib import admin
from django.utils import timezone
from django.db import transaction

from .models import (
    Idea, Hypothesis, ValidationSprint, CustomerEvidence,
    GateResult, PortfolioScore, Graduation
)

from django.contrib import admin
from .models import DDQuantitativeSnapshot, DueDiligenceRun


class DDQuantitativeSnapshotInline(admin.StackedInline):
    model = DDQuantitativeSnapshot
    extra = 0
    can_delete = True

@admin.register(Idea)
class IdeaAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "idea_type", "entity", "founder_conviction", "updated_at")
    list_filter = ("status", "idea_type", "entity")
    search_fields = ("name", "problem_statement", "target_customer")
    readonly_fields = ("created_at", "updated_at", "killed_at")

    actions = [
        "action_kill_idea",
        "action_mark_validated",
        "action_eval_customer_pain_gate",
        "action_graduate_to_okr",
    ]

    @admin.action(description="Kill selected ideas (adds generic reason)")
    def action_kill_idea(self, request, queryset):
        for idea in queryset:
            idea.kill("Killed via admin action.")
        self.message_user(request, f"Killed {queryset.count()} idea(s).")

    @admin.action(description="Mark selected ideas as VALIDATED (does not auto-pass gates)")
    def action_mark_validated(self, request, queryset):
        updated = queryset.update(status=Idea.Status.VALIDATED, updated_at=timezone.now())
        self.message_user(request, f"Marked {updated} idea(s) as VALIDATED.")

    @admin.action(description="Evaluate Gate 1: Customer Pain (from active sprint evidence)")
    def action_eval_customer_pain_gate(self, request, queryset):
        for idea in queryset:
            sprint = idea.active_sprint
            if not sprint:
                GateResult.objects.update_or_create(
                    idea=idea, gate=GateResult.Gate.CUSTOMER_PAIN,
                    defaults={"passed": False, "rationale": "No active sprint."}
                )
                continue

            interview_count = sprint.interview_count
            avg_pain = sprint.avg_pain
            passed = (interview_count >= sprint.required_interviews) and (avg_pain >= sprint.pain_threshold)

            rationale = (
                f"Interviews: {interview_count}/{sprint.required_interviews}. "
                f"Avg pain: {avg_pain:.2f} (threshold {sprint.pain_threshold})."
            )

            GateResult.objects.update_or_create(
                idea=idea, gate=GateResult.Gate.CUSTOMER_PAIN,
                defaults={"passed": passed, "rationale": rationale}
            )

            # Optional auto-kill on failure (you can remove this if you prefer manual)
            if not passed and idea.status in [Idea.Status.VALIDATING, Idea.Status.DRAFT]:
                idea.kill(f"Failed customer pain gate. {rationale}")

        self.message_user(request, f"Evaluated Customer Pain gate for {queryset.count()} idea(s).")

    @admin.action(description="Graduate VALIDATED ideas to OKR (create Strategy + Objective)")
    def action_graduate_to_okr(self, request, queryset):
        from apps.okr.models import Strategy, Objective, KeyResult  # adjust path if your OKR app differs

        graduated = 0
        for idea in queryset:
            if not idea.can_graduate():
                continue

            with transaction.atomic():
                # Strategy: reuse proposed if set, else create
                strategy = idea.proposed_strategy
                if not strategy:
                    strategy = Strategy.objects.create(
                        entity=idea.entity,
                        name=f"[Janus] {idea.name}",
                        description=idea.problem_statement,
                        theme="gray",
                    )

                # Objective
                today = timezone.localdate()
                obj = Objective.objects.create(
                    strategy=strategy,
                    name=idea.name,
                    description=idea.problem_statement,
                    owner="Founder",
                    start_date=today,
                    end_date=today + timezone.timedelta(days=90),
                    completed=False,
                )

                # Seed 1 KR placeholder (you’ll replace with real KRs)
                KeyResult.objects.create(
                    objective=obj,
                    name="Validation KR (placeholder)",
                    description="Replace with measurable proof KR(s) derived from validated hypotheses.",
                    target_value=1.0,
                    current_value=0.0,
                    unit="pass",
                )

                Graduation.objects.update_or_create(
                    idea=idea,
                    defaults={"strategy": strategy, "objective": obj}
                )

                graduated += 1

        self.message_user(request, f"Graduated {graduated} idea(s) to OKR.")


@admin.register(ValidationSprint)
class ValidationSprintAdmin(admin.ModelAdmin):
    list_display = ("idea", "status", "start_date", "end_date", "budget_cap", "required_interviews", "pain_threshold")
    list_filter = ("status",)
    search_fields = ("idea__name",)
    actions = ["action_activate_sprint"]

    @admin.action(description="Activate selected planned sprints")
    def action_activate_sprint(self, request, queryset):
        activated = 0
        for sprint in queryset:
            if sprint.status == ValidationSprint.Status.PLANNED:
                sprint.activate()
                activated += 1
        self.message_user(request, f"Activated {activated} sprint(s).")


@admin.register(Hypothesis)
class HypothesisAdmin(admin.ModelAdmin):
    list_display = ("idea", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("idea__name", "statement")


@admin.register(CustomerEvidence)
class CustomerEvidenceAdmin(admin.ModelAdmin):
    list_display = ("sprint", "kind", "pain_intensity", "pain_frequency", "created_at")
    list_filter = ("kind",)
    search_fields = ("sprint__idea__name", "summary", "quote", "customer_org", "customer_name")


@admin.register(GateResult)
class GateResultAdmin(admin.ModelAdmin):
    list_display = ("idea", "gate", "passed", "evaluated_at")
    list_filter = ("gate", "passed")


@admin.register(PortfolioScore)
class PortfolioScoreAdmin(admin.ModelAdmin):
    list_display = ("idea", "total", "created_at")
    actions = ["action_recompute_total"]

    @admin.action(description="Recompute totals for selected scores")
    def action_recompute_total(self, request, queryset):
        for score in queryset:
            score.recompute_total()
        self.message_user(request, "Recomputed totals.")


@admin.register(Graduation)
class GraduationAdmin(admin.ModelAdmin):
    list_display = ("idea", "strategy", "objective", "created_at")

from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import (
    TargetCompany,
    ScoreScale,
    DDTemplate,
    DDSection,
    DDCriterion,
    DueDiligenceRun,
    DDResponse,
    DDEvidence,
    DDRisk,
    DDCondition,
    DDParticipant,
    DDPromotionBatch,
    DDPromotedItem,
)


# -------------------------
# Actions
# -------------------------
@admin.action(description="Recalculate overall score for selected DD runs")
def recalc_overall_score(modeladmin, request, queryset):
    for run in queryset:
        run.recalc_scores(save=True)


@admin.action(description="Mark selected DD runs as COMPLETE")
def mark_runs_complete(modeladmin, request, queryset):
    for run in queryset:
        run.mark_complete()


@admin.action(description="Promote selected DD runs to execution")
def promote_runs(modeladmin, request, queryset):
    for run in queryset:
        run.promote_to_execution()


# -------------------------
# Inlines
# -------------------------
class DDSectionInline(admin.TabularInline):
    model = DDSection
    extra = 0
    fields = ("order_index", "title", "weight")
    ordering = ("order_index", "id")


class DDCriterionInline(admin.TabularInline):
    model = DDCriterion
    extra = 0
    fields = (
        "order_index",
        "title",
        "weight",
        "scoring_scale",
        "evidence_required",
        "non_negotiable",
        "pass_threshold",
    )
    ordering = ("order_index", "id")


class DDResponseInline(admin.TabularInline):
    model = DDResponse
    extra = 0
    fields = ("criterion", "score_value", "confidence", "assessed_by", "assessed_at")
    readonly_fields = ("assessed_at",)
    autocomplete_fields = ("criterion", "assessed_by")
    show_change_link = True


class DDEvidenceInline(admin.TabularInline):
    model = DDEvidence
    extra = 0
    fields = ("title", "evidence_type", "url", "file_path", "sensitivity", "uploaded_by", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("uploaded_by", "section", "criterion")
    show_change_link = True


class DDRiskInline(admin.TabularInline):
    model = DDRisk
    extra = 0
    fields = ("title", "category", "severity", "likelihood", "risk_score", "status", "blocking", "owner")
    readonly_fields = ("risk_score",)
    autocomplete_fields = ("owner",)
    show_change_link = True


class DDConditionInline(admin.TabularInline):
    model = DDCondition
    extra = 0
    fields = ("title", "must_complete_before", "due_by", "status", "mapped_risk")
    autocomplete_fields = ("mapped_risk",)
    show_change_link = True


class DDParticipantInline(admin.TabularInline):
    model = DDParticipant
    extra = 0
    fields = ("user", "role", "permission")
    autocomplete_fields = ("user",)
    show_change_link = True


class DDPromotedItemInline(admin.TabularInline):
    model = DDPromotedItem
    extra = 0
    fields = ("source_type", "source_id", "proposed_objective", "proposed_key_result", "priority", "okr_objective_id", "okr_key_result_id")
    show_change_link = True


class DDPromotionBatchInline(admin.TabularInline):
    model = DDPromotionBatch
    extra = 0
    fields = ("created_by", "target_context_label", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("created_by",)
    show_change_link = True


# -------------------------
# Admin registrations
# -------------------------
@admin.register(TargetCompany)
class TargetCompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "deal_stage", "website_link", "owner", "created_at", "updated_at")
    list_filter = ("deal_stage",)
    search_fields = ("name", "website", "notes")
    autocomplete_fields = ("owner",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name",)

    def website_link(self, obj):
        if not obj.website:
            return "-"
        return format_html('<a href="{}" target="_blank" rel="noopener">Open</a>', obj.website)

    website_link.short_description = "Website"


@admin.register(ScoreScale)
class ScoreScaleAdmin(admin.ModelAdmin):
    list_display = ("name", "min_value", "max_value", "updated_at")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(DDTemplate)
class DDTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "is_active", "section_count", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "version", "description")
    readonly_fields = ("created_at", "updated_at")
    inlines = [DDSectionInline]
    ordering = ("-is_active", "name", "version")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_section_count=Count("sections"))

    def section_count(self, obj):
        return getattr(obj, "_section_count", 0)

    section_count.short_description = "Sections"


@admin.register(DDSection)
class DDSectionAdmin(admin.ModelAdmin):
    list_display = ("template", "order_index", "title", "weight", "criteria_count", "updated_at")
    list_filter = ("template",)
    search_fields = ("title", "template__name", "template__version")
    readonly_fields = ("created_at", "updated_at")
    inlines = [DDCriterionInline]
    ordering = ("template", "order_index", "id")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_criteria_count=Count("criteria"))

    def criteria_count(self, obj):
        return getattr(obj, "_criteria_count", 0)

    criteria_count.short_description = "Criteria"


@admin.register(DDCriterion)
class DDCriterionAdmin(admin.ModelAdmin):
    list_display = (
        "section",
        "order_index",
        "title",
        "weight",
        "scoring_scale",
        "evidence_required",
        "non_negotiable",
        "pass_threshold",
        "updated_at",
    )
    list_filter = ("section__template", "section", "scoring_scale", "evidence_required", "non_negotiable")
    search_fields = ("title", "description", "section__title", "section__template__name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("section", "order_index", "id")


@admin.register(DueDiligenceRun)
class DueDiligenceRunAdmin(admin.ModelAdmin):
    list_display = (
        "target_company",
        "template",
        "round_number",
        "status",
        "overall_score",
        "verdict",
        "due_date",
        "completed_at",
        "promoted_to_execution",
    )
    list_filter = ("status", "verdict", "template", "promoted_to_execution")
    search_fields = ("target_company__name", "template__name", "template__version", "verdict_rationale")
    autocomplete_fields = ("target_company", "template")
    readonly_fields = ("created_at", "updated_at", "completed_at", "promoted_at", "overall_score")
    inlines = [DDResponseInline, DDEvidenceInline, DDRiskInline, DDConditionInline, DDParticipantInline, DDPromotionBatchInline, DDQuantitativeSnapshotInline]
    actions = [recalc_overall_score, mark_runs_complete, promote_runs]
    ordering = ("-created_at",)

    fieldsets = (
        ("Core", {"fields": ("target_company", "template", "round_number", "status")}),
        ("Dates", {"fields": ("start_date", "due_date", "completed_at")}),
        ("Outcome", {"fields": ("overall_score", "verdict", "verdict_rationale")}),
        ("Execution Handoff", {"fields": ("promoted_to_execution", "promoted_at")}),
        ("System", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(DDResponse)
class DDResponseAdmin(admin.ModelAdmin):
    list_display = ("run", "criterion", "score_value", "confidence", "assessed_by", "assessed_at", "computed_weighted_score")
    list_filter = ("run", "confidence", "criterion__section__template", "criterion__section")
    search_fields = ("run__target_company__name", "criterion__title", "commentary")
    autocomplete_fields = ("run", "criterion", "assessed_by")
    readonly_fields = ("created_at", "updated_at", "assessed_at", "computed_weighted_score")
    ordering = ("-assessed_at", "criterion__section__order_index", "criterion__order_index")


@admin.register(DDEvidence)
class DDEvidenceAdmin(admin.ModelAdmin):
    list_display = ("run", "title", "evidence_type", "sensitivity", "uploaded_by", "created_at")
    list_filter = ("evidence_type", "sensitivity", "run__template")
    search_fields = ("title", "notes", "url", "file_path", "run__target_company__name")
    autocomplete_fields = ("run", "section", "criterion", "uploaded_by")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(DDRisk)
class DDRiskAdmin(admin.ModelAdmin):
    list_display = ("run", "title", "category", "severity", "likelihood", "risk_score", "status", "blocking", "owner", "updated_at")
    list_filter = ("category", "status", "blocking", "run__template")
    search_fields = ("title", "description", "mitigation_plan", "run__target_company__name")
    autocomplete_fields = ("run", "owner", "related_criteria")
    readonly_fields = ("created_at", "updated_at", "risk_score")
    filter_horizontal = ("related_criteria",)
    ordering = ("-updated_at",)


@admin.register(DDCondition)
class DDConditionAdmin(admin.ModelAdmin):
    list_display = ("run", "title", "must_complete_before", "due_by", "status", "mapped_risk", "updated_at")
    list_filter = ("must_complete_before", "status", "run__template")
    search_fields = ("title", "description", "run__target_company__name")
    autocomplete_fields = ("run", "mapped_risk")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-updated_at",)


@admin.register(DDParticipant)
class DDParticipantAdmin(admin.ModelAdmin):
    list_display = ("run", "user", "role", "permission", "created_at")
    list_filter = ("role", "permission", "run__template")
    search_fields = ("run__target_company__name", "user__username", "user__email")
    autocomplete_fields = ("run", "user")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(DDPromotionBatch)
class DDPromotionBatchAdmin(admin.ModelAdmin):
    list_display = ("run", "created_by", "target_context_label", "created_at", "item_count")
    list_filter = ("run__template",)
    search_fields = ("run__target_company__name", "target_context_label", "notes")
    autocomplete_fields = ("run", "created_by")
    readonly_fields = ("created_at", "updated_at")
    inlines = [DDPromotedItemInline]
    ordering = ("-created_at",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_item_count=Count("items"))

    def item_count(self, obj):
        return getattr(obj, "_item_count", 0)

    item_count.short_description = "Items"


@admin.register(DDPromotedItem)
class DDPromotedItemAdmin(admin.ModelAdmin):
    list_display = ("batch", "source_type", "source_id", "priority", "okr_objective_id", "okr_key_result_id", "created_at")
    list_filter = ("source_type", "priority")
    search_fields = ("proposed_objective", "proposed_key_result")
    autocomplete_fields = ("batch",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)

@admin.register(DDQuantitativeSnapshot)
class DDQuantitativeSnapshotAdmin(admin.ModelAdmin):
    list_display = ("run", "metrics_as_of_date", "confidence", "total_customers", "arr", "gross_margin_pct", "burn_rate_monthly", "runway_months")
    search_fields = ("run__target_company__name",)
