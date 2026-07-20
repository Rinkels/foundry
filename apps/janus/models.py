# apps/janus/models.py
from __future__ import annotations
from django.conf import settings
from decimal import Decimal
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils import timezone

# --- Constants based on your validation rules ---
DEFAULT_SPRINT_DAYS = 14
DEFAULT_BUDGET_CAP = Decimal("5000.00")


class Idea(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        VALIDATING = "validating", "Validating"
        VALIDATED = "validated", "Validated"
        KILLED = "killed", "Killed"
        ARCHIVED = "archived", "Archived"

    class IdeaType(models.TextChoices):
        CORE = "core", "Core"
        ADJACENT = "adjacent", "Adjacent"
        LONGSHOT = "longshot", "Long-shot"

    # Connect to your OKR domain
    entity = models.ForeignKey(
        "okr.Entity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="janus_ideas",
        help_text="Which business entity / venture this idea belongs to.",
    )

    # Optional: if you already know the strategy bucket, link it
    proposed_strategy = models.ForeignKey(
        "okr.Strategy",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="janus_ideas",
        help_text="Optional: existing Strategy this idea aligns to.",
    )

    name = models.CharField(max_length=255)
    problem_statement = models.TextField(help_text="Use customer language. What pain exists?")
    target_customer = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    idea_type = models.CharField(max_length=20, choices=IdeaType.choices, default=IdeaType.ADJACENT)

    # Founder-first signal
    founder_conviction = models.PositiveSmallIntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Founder conviction 1–5 (explicit gut check)."
    )

    # Kill switch
    killed_reason = models.TextField(blank=True, default="")
    killed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]

    def __str__(self) -> str:
        return self.name

    @property
    def active_sprint(self) -> "ValidationSprint | None":
        return self.sprints.filter(status=ValidationSprint.Status.ACTIVE).first()

    @property
    def latest_score(self) -> "PortfolioScore | None":
        return self.scores.order_by("-created_at").first()

    def kill(self, reason: str) -> None:
        self.status = self.Status.KILLED
        self.killed_reason = reason.strip()
        self.killed_at = timezone.now()
        self.save(update_fields=["status", "killed_reason", "killed_at", "updated_at"])

    def can_graduate(self) -> bool:
        """
        Minimal rule: must have passed Gate #1 (Customer Pain) and be VALIDATED.
        You can tighten this later (e.g. require 2+ hypotheses validated).
        """
        if self.status != self.Status.VALIDATED:
            return False
        return self.gates.filter(gate=GateResult.Gate.CUSTOMER_PAIN, passed=True).exists()


class Hypothesis(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        SUPPORTED = "supported", "Supported"
        DISPROVEN = "disproven", "Disproven"

    class Criticality(models.TextChoices):
        NON_NEGOTIABLE = "non_negotiable", "Non-negotiable (Kill if false)"
        IMPORTANT = "important", "Important"
        OPTIONAL = "optional", "Optional"

    class RiskProfile(models.TextChoices):
        NORMAL = "normal", "Normal"
        LONGSHOT = "longshot", "Long-shot"

    idea = models.ForeignKey(Idea, on_delete=models.CASCADE, related_name="hypotheses")

    statement = models.TextField(help_text="We believe that…")
    must_be_true = models.TextField(blank=True, default="")
    disproof = models.TextField(blank=True, default="")

    # 🆕 intent signals
    criticality = models.CharField(
        max_length=20,
        choices=Criticality.choices,
        default=Criticality.IMPORTANT,
        help_text="If this is false, does the idea die?"
    )

    risk_profile = models.CharField(
        max_length=20,
        choices=RiskProfile.choices,
        default=RiskProfile.NORMAL,
        help_text="Is this a long-shot hypothesis?"
    )

    # 🆕 expected evidence
    validation_signals = models.TextField(
        blank=True,
        default="",
        help_text="What evidence or signals would support this hypothesis?"
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)



class ValidationSprint(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        ACTIVE = "active", "Active"
        COMPLETE = "complete", "Complete"
        CANCELLED = "cancelled", "Cancelled"

    idea = models.ForeignKey(Idea, on_delete=models.CASCADE, related_name="sprints")
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True)
    duration_days = models.PositiveSmallIntegerField(default=DEFAULT_SPRINT_DAYS)
    budget_cap = models.DecimalField(max_digits=12, decimal_places=2, default=DEFAULT_BUDGET_CAP)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)

    # Success definition for the sprint (signals, not full success)
    required_interviews = models.PositiveSmallIntegerField(default=5)
    pain_threshold = models.PositiveSmallIntegerField(
        default=4, validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Minimum avg pain intensity (1–5) to pass the customer pain gate."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Sprint for {self.idea.name} ({self.status})"

    def activate(self) -> None:
        if self.status != self.Status.PLANNED:
            return
        self.status = self.Status.ACTIVE
        # auto-calc end_date if not set
        if not self.end_date:
            self.end_date = self.start_date + timezone.timedelta(days=int(self.duration_days))
        self.save(update_fields=["status", "end_date"])

        self.idea.status = Idea.Status.VALIDATING
        self.idea.save(update_fields=["status", "updated_at"])

    @property
    def interview_count(self) -> int:
        return self.evidence.filter(kind=CustomerEvidence.Kind.INTERVIEW).count()

    @property
    def avg_pain(self) -> float:
        qs = self.evidence.filter(kind=CustomerEvidence.Kind.INTERVIEW, pain_intensity__isnull=False)
        if not qs.exists():
            return 0.0
        return float(qs.aggregate(models.Avg("pain_intensity"))["pain_intensity__avg"] or 0.0)


class CustomerEvidence(models.Model):
    class Kind(models.TextChoices):
        INTERVIEW = "interview", "Customer Interview"
        LOI = "loi", "LOI / Pilot Interest"
        SURVEY = "survey", "Survey"
        OTHER = "other", "Other"

    sprint = models.ForeignKey(ValidationSprint, on_delete=models.CASCADE, related_name="evidence")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.INTERVIEW)

    customer_name = models.CharField(max_length=255, blank=True, default="")
    customer_org = models.CharField(max_length=255, blank=True, default="")
    quote = models.TextField(blank=True, default="", help_text="Direct quote (gold).")
    summary = models.TextField(help_text="What was learned?")

    pain_intensity = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1–5. Only required for interviews."
    )
    pain_frequency = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1–5. How often does the pain occur?"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.kind} evidence for {self.sprint.idea.name}"


class GateResult(models.Model):
    class Gate(models.TextChoices):
        CUSTOMER_PAIN = "customer_pain", "Gate 1: Customer Pain"
        TIMEBOX = "timebox", "Gate 2: Two-week Signal"
        BUDGET = "budget", "Gate 2b: Budget Cap"
        PORTFOLIO = "portfolio", "Gate 3: Portfolio Rank (post-gate)"

    idea = models.ForeignKey(Idea, on_delete=models.CASCADE, related_name="gates")
    gate = models.CharField(max_length=30, choices=Gate.choices)
    passed = models.BooleanField(default=False)
    rationale = models.TextField(blank=True, default="")
    evaluated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("idea", "gate")
        ordering = ["gate"]

    def __str__(self) -> str:
        return f"{self.idea.name} | {self.gate} = {'PASS' if self.passed else 'FAIL'}"


class PortfolioScore(models.Model):
    """
    Portfolio ranking AFTER gates.
    Keep it light and editable; you can refine weights later.
    """
    idea = models.ForeignKey(Idea, on_delete=models.CASCADE, related_name="scores")

    pain_intensity = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    pain_frequency = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    capital_efficiency = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    strategic_leverage = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    time_to_signal = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])

    # Computed-ish snapshot
    total = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-total", "-created_at"]

    def __str__(self) -> str:
        return f"Score {self.total} for {self.idea.name}"

    def recompute_total(self) -> None:
        self.total = int(
            self.pain_intensity
            + self.pain_frequency
            + self.capital_efficiency
            + self.strategic_leverage
            + self.time_to_signal
            + self.idea.founder_conviction  # tiny founder bias, explicit
        )
        self.save(update_fields=["total"])


class Graduation(models.Model):
    """
    Records the handoff into OKR execution.
    """
    idea = models.OneToOneField(Idea, on_delete=models.CASCADE, related_name="graduation")
    created_at = models.DateTimeField(auto_now_add=True)

    # Link what this became in OKR world
    strategy = models.ForeignKey("okr.Strategy", on_delete=models.SET_NULL, null=True, blank=True)
    objective = models.ForeignKey("okr.Objective", on_delete=models.SET_NULL, null=True, blank=True)

    notes = models.TextField(blank=True, default="")

    def __str__(self) -> str:
        return f"Graduation: {self.idea.name}"

class ScorecardTemplate(models.Model):
    """
    Defines a reusable scorecard template.
    Example: IFMS Acquisition – Distressed Indoor Farms
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=20, default="v1.0")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.version})"


class ScorecardSection(models.Model):
    """
    Logical grouping of criteria.
    Example: Physical Salvageability, IFMS Leverage, Financial Reset
    """
    template = models.ForeignKey(
        ScorecardTemplate,
        related_name="sections",
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Weight as percentage of total score"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.template.name} – {self.name}"


class ScorecardCriterion(models.Model):
    """
    Individual scored question.
    Example: Electrical capacity sufficient for LED retrofit
    """
    section = models.ForeignKey(
        ScorecardSection,
        related_name="criteria",
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    max_score = models.PositiveIntegerField(default=5)
    is_hard_stop = models.BooleanField(
        default=False,
        help_text="If failed, auto-fail the scorecard"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name

from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.db.models import Sum
from django.conf import settings


DEC_2 = Decimal("0.01")


class ScorecardEvaluation(models.Model):
    template = models.ForeignKey("ScorecardTemplate", on_delete=models.PROTECT)

    target_name = models.CharField(max_length=255)
    target_type = models.CharField(max_length=100, help_text="e.g. Cannabis Farm, Indoor Greens Farm")

    evaluated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    notes = models.TextField(blank=True)

    total_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    decision = models.CharField(max_length=50, blank=True)

    hard_stop_triggered = models.BooleanField(default=False)
    hard_stop_reason = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.template.name} – {self.target_name}"

    def _decision_from_score(self, score: Decimal, hard_stop: bool) -> str:
        if hard_stop:
            return "Reject"
        if score >= Decimal("75"):
            return "Acquire Aggressively"
        if score >= Decimal("60"):
            return "Acquire with Conditions"
        if score >= Decimal("45"):
            return "Watchlist / Option Deal"
        return "Reject"

    def recalculate(self, save: bool = True) -> dict:
        """
        Recalculate weighted total score + hard-stop.
        Returns a dict with details for UI/debugging.
        """

        # Hard-stop check: any hard-stop criterion scored 0 triggers reject
        hard_stop_resp = (
            self.responses
            .select_related("criterion")
            .filter(criterion__is_hard_stop=True, score__lte=0)
            .first()
        )
        hard_stop_triggered = bool(hard_stop_resp)
        hard_stop_reason = hard_stop_resp.criterion.name if hard_stop_resp else ""

        # Weighted score:
        # For each section: average criterion percent (score/max) * section weight
        total = Decimal("0")
        detail = []

        sections = (
            self.template.sections
            .prefetch_related("criteria")
            .all()
        )

        # Build quick lookup: criterion_id -> response(score)
        responses = {r.criterion_id: r for r in self.responses.select_related("criterion").all()}

        for section in sections:
            crits = list(section.criteria.all())
            if not crits:
                continue

            # Section percent = mean of criterion percents (only those answered)
            percents = []
            missing = 0

            for c in crits:
                r = responses.get(c.id)
                if not r:
                    missing += 1
                    continue
                max_score = Decimal(str(c.max_score or 5))
                perc = (Decimal(str(r.score)) / max_score) if max_score > 0 else Decimal("0")
                percents.append(perc)

            if not percents:
                section_percent = Decimal("0")
            else:
                section_percent = sum(percents) / Decimal(str(len(percents)))

            section_weight = Decimal(str(section.weight))  # weight is percentage points
            section_contribution = (section_percent * section_weight)

            total += section_contribution

            detail.append({
                "section": section.name,
                "weight": str(section_weight),
                "answered": len(percents),
                "missing": missing,
                "section_percent": str((section_percent * Decimal("100")).quantize(DEC_2, rounding=ROUND_HALF_UP)),
                "contribution": str(section_contribution.quantize(DEC_2, rounding=ROUND_HALF_UP)),
            })

        total = total.quantize(DEC_2, rounding=ROUND_HALF_UP)
        decision = self._decision_from_score(total, hard_stop_triggered)

        if save:
            self.total_score = total
            self.decision = decision
            self.hard_stop_triggered = hard_stop_triggered
            self.hard_stop_reason = hard_stop_reason
            self.save(update_fields=["total_score", "decision", "hard_stop_triggered", "hard_stop_reason"])

        return {
            "total_score": str(total),
            "decision": decision,
            "hard_stop_triggered": hard_stop_triggered,
            "hard_stop_reason": hard_stop_reason,
            "sections": detail,
        }


class ScorecardResponse(models.Model):
    """
    Stores the score and notes for one criterion.
    """
    evaluation = models.ForeignKey(
        ScorecardEvaluation,
        related_name="responses",
        on_delete=models.CASCADE
    )
    criterion = models.ForeignKey(
        ScorecardCriterion,
        on_delete=models.PROTECT
    )

    score = models.PositiveIntegerField()
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("evaluation", "criterion")

    def __str__(self):
        return f"{self.criterion.name}: {self.score}"

class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class TargetCompany(TimestampedModel):
    class DealStage(models.TextChoices):
        LEAD = "lead", "Lead"
        LOI = "loi", "LOI"
        DILIGENCE = "diligence", "Diligence"
        DEFINITIVE = "definitive", "Definitive"
        CLOSED = "closed", "Closed"
        DROPPED = "dropped", "Dropped"

    name = models.CharField(max_length=200, unique=True)
    website = models.URLField(blank=True)
    logo_file = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Relative path under MEDIA_ROOT, e.g. company_logos/output.png",
    )
    deal_stage = models.CharField(max_length=20, choices=DealStage.choices, default=DealStage.LEAD)
    # Narrative profile (evergreen)
    short_description = models.CharField(max_length=280, blank=True, default="")
    long_description = models.TextField(blank=True, default="")
    long_description_updated_at = models.DateTimeField(null=True, blank=True)
    # You can later switch this to your Person model if needed.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="janus_target_companies",
    )

    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")

        # If update_fields is set and doesn't include long_description, skip any timestamp logic.
        if update_fields is not None and "long_description" not in update_fields:
            return super().save(*args, **kwargs)

        if self.pk:
            prior = type(self).objects.filter(pk=self.pk).values_list("long_description", flat=True).first()
            if prior != self.long_description:
                self.long_description_updated_at = timezone.now()
                if update_fields is not None:
                    kwargs["update_fields"] = set(update_fields) | {"long_description_updated_at"}
        else:
            if self.long_description:
                self.long_description_updated_at = timezone.now()
                if update_fields is not None:
                    kwargs["update_fields"] = set(update_fields) | {"long_description_updated_at"}

        return super().save(*args, **kwargs)

class ScoreScale(TimestampedModel):
    """
    Defines a scoring scale (e.g., 0-5 maturity, pass/fail).
    labels_json example:
      {"0": "none", "3": "adequate", "5": "excellent"}
    """
    name = models.CharField(max_length=120, unique=True)
    min_value = models.IntegerField(default=0)
    max_value = models.IntegerField(default=5)
    labels_json = models.JSONField(blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.min_value}-{self.max_value})"


class DDTemplate(TimestampedModel):
    name = models.CharField(max_length=200)
    version = models.CharField(max_length=40, default="v1")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = (("name", "version"),)
        indexes = [
            models.Index(fields=["is_active", "name"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} {self.version}"


class DDSection(TimestampedModel):
    template = models.ForeignKey(DDTemplate, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=200)
    weight = models.PositiveIntegerField(default=10, validators=[MinValueValidator(0), MaxValueValidator(100)])
    order_index = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = (("template", "title"),)
        ordering = ["template", "order_index", "id"]

    def __str__(self) -> str:
        return f"{self.template}: {self.title}"


class DDCriterion(TimestampedModel):
    section = models.ForeignKey(DDSection, on_delete=models.CASCADE, related_name="criteria")
    title = models.CharField(max_length=220)
    description = models.TextField(blank=True)

    weight = models.PositiveIntegerField(default=10, validators=[MinValueValidator(0), MaxValueValidator(100)])
    scoring_scale = models.ForeignKey(ScoreScale, on_delete=models.PROTECT, related_name="criteria")

    evidence_required = models.BooleanField(default=False)
    non_negotiable = models.BooleanField(default=False)
    order_index = models.PositiveIntegerField(default=0)

    # Optional: a threshold that counts as "pass" for non-negotiables.
    pass_threshold = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = (("section", "title"),)
        ordering = ["section", "order_index", "id"]

    def __str__(self) -> str:
        return f"{self.section.title}: {self.title}"


class DueDiligenceRun(TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_PROGRESS = "in_progress", "In Progress"
        BLOCKED = "blocked", "Blocked"
        COMPLETE = "complete", "Complete"

    class Verdict(models.TextChoices):
        PROCEED = "proceed", "Proceed"
        PROCEED_WITH_CONDITIONS = "proceed_with_conditions", "Proceed With Conditions"
        PAUSE = "pause", "Pause"
        WALK_AWAY = "walk_away", "Walk Away"

    target_company = models.ForeignKey(TargetCompany, on_delete=models.CASCADE, related_name="dd_runs")
    template = models.ForeignKey(DDTemplate, on_delete=models.PROTECT, related_name="dd_runs")
    round_number = models.PositiveIntegerField(default=1)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Cached rollups
    overall_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # 0..100
    verdict = models.CharField(max_length=30, choices=Verdict.choices, blank=True)
    verdict_rationale = models.TextField(blank=True)

    promoted_to_execution = models.BooleanField(default=False)
    promoted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = (("target_company", "template", "round_number"),)
        indexes = [
            models.Index(fields=["status", "due_date"]),
            models.Index(fields=["target_company", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.target_company} | {self.template} | Round {self.round_number}"

    def mark_complete(self) -> None:
        self.status = self.Status.COMPLETE
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])

    def promote_to_execution(self) -> None:
        self.promoted_to_execution = True
        self.promoted_at = timezone.now()
        self.save(update_fields=["promoted_to_execution", "promoted_at", "updated_at"])

    def recalc_scores(self, save: bool = True) -> float:
        """
        Recompute overall score (0..100) from section/criterion weights.
        Uses DDResponse.score_value mapped to criterion scale (normalized to 0..100).
        """
        # Gather responses with related criterion/section/scale in as few queries as possible.
        responses = (
            self.responses.select_related(
                "criterion",
                "criterion__scoring_scale",
                "criterion__section",
            )
            .all()
        )

        if not responses.exists():
            self.overall_score = 0
            if save:
                self.save(update_fields=["overall_score", "updated_at"])
            return 0.0

        # Aggregate per section
        section_totals: dict[int, dict[str, float]] = {}
        for r in responses:
            c = r.criterion
            scale = c.scoring_scale
            denom = max(scale.max_value - scale.min_value, 1)
            normalized = ((r.score_value - scale.min_value) / denom) * 100.0

            s_id = c.section_id
            if s_id not in section_totals:
                section_totals[s_id] = {"criterion_weight_sum": 0.0, "criterion_weighted_sum": 0.0, "section_weight": float(c.section.weight)}

            cw = float(c.weight)
            section_totals[s_id]["criterion_weight_sum"] += cw
            section_totals[s_id]["criterion_weighted_sum"] += normalized * cw

        # Convert each section to 0..100, then weight by section weight
        overall_weight_sum = 0.0
        overall_weighted_sum = 0.0
        for s_id, vals in section_totals.items():
            cw_sum = max(vals["criterion_weight_sum"], 1.0)
            section_score = vals["criterion_weighted_sum"] / cw_sum  # 0..100
            sw = vals["section_weight"]
            overall_weight_sum += sw
            overall_weighted_sum += section_score * sw

        overall = 0.0 if overall_weight_sum <= 0 else (overall_weighted_sum / overall_weight_sum)
        self.overall_score = round(overall, 2)

        if save:
            self.save(update_fields=["overall_score", "updated_at"])
        return float(self.overall_score)


class DDResponse(TimestampedModel):
    class Confidence(models.TextChoices):
        LOW = "low", "Low"
        MED = "med", "Medium"
        HIGH = "high", "High"

    run = models.ForeignKey(DueDiligenceRun, on_delete=models.CASCADE, related_name="responses")
    criterion = models.ForeignKey(DDCriterion, on_delete=models.CASCADE, related_name="responses")

    score_value = models.IntegerField(default=0)
    confidence = models.CharField(max_length=10, choices=Confidence.choices, default=Confidence.MED)
    commentary = models.TextField(blank=True)

    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="janus_dd_responses",
    )
    assessed_at = models.DateTimeField(default=timezone.now)

    computed_weighted_score = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["run", "criterion"], name="uniq_ddresponse_run_criterion")
        ]
        indexes = [
            models.Index(fields=["run", "criterion"]),
        ]

    def __str__(self) -> str:
        return f"{self.run} | {self.criterion.title}"

    def clean(self):
        # Enforce scale bounds if available
        scale = self.criterion.scoring_scale
        if self.score_value < scale.min_value or self.score_value > scale.max_value:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                {"score_value": f"Score must be between {scale.min_value} and {scale.max_value} for scale '{scale.name}'."}
            )

    def save(self, *args, **kwargs):
        # Compute weighted score (normalized 0..100 * criterion weight)
        scale = self.criterion.scoring_scale
        denom = max(scale.max_value - scale.min_value, 1)
        normalized = ((self.score_value - scale.min_value) / denom) * 100.0
        self.computed_weighted_score = round(normalized * float(self.criterion.weight), 2)
        super().save(*args, **kwargs)


class DDEvidence(TimestampedModel):
    class EvidenceType(models.TextChoices):
        DOC = "doc", "Document"
        LINK = "link", "Link"
        SCREENSHOT = "screenshot", "Screenshot"
        REPO_ACCESS = "repo_access", "Repo Access"
        INTERVIEW = "interview", "Interview"
        OTHER = "other", "Other"

    class Sensitivity(models.TextChoices):
        PUBLIC = "public", "Public"
        INTERNAL = "internal", "Internal"
        CONFIDENTIAL = "confidential", "Confidential"

    run = models.ForeignKey(DueDiligenceRun, on_delete=models.CASCADE, related_name="evidence")

    # Evidence can be attached broadly, to a section, or to a criterion.
    section = models.ForeignKey(DDSection, on_delete=models.SET_NULL, null=True, blank=True, related_name="evidence")
    criterion = models.ForeignKey(DDCriterion, on_delete=models.SET_NULL, null=True, blank=True, related_name="evidence")

    title = models.CharField(max_length=240)
    evidence_type = models.CharField(max_length=20, choices=EvidenceType.choices, default=EvidenceType.LINK)

    url = models.URLField(blank=True)

    # Optional integration point: replace with FK to your Mnemos FileAsset later.
    file_path = models.CharField(max_length=500, blank=True)

    notes = models.TextField(blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="janus_dd_evidence",
    )
    sensitivity = models.CharField(max_length=20, choices=Sensitivity.choices, default=Sensitivity.INTERNAL)

    class Meta:
        indexes = [
            models.Index(fields=["run", "evidence_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.run} | {self.title}"


class DDRisk(TimestampedModel):
    class Category(models.TextChoices):
        SECURITY = "security", "Security"
        LEGAL = "legal", "Legal"
        OPS = "ops", "Operations"
        TECH = "tech", "Technology"
        DEPENDENCY = "dependency", "Dependency"
        DATA = "data", "Data"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        MITIGATING = "mitigating", "Mitigating"
        ACCEPTED = "accepted", "Accepted"
        CLOSED = "closed", "Closed"

    run = models.ForeignKey(DueDiligenceRun, on_delete=models.CASCADE, related_name="risks")
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True)

    category = models.CharField(max_length=20, choices=Category.choices, default=Category.TECH)

    severity = models.PositiveIntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    likelihood = models.PositiveIntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    risk_score = models.PositiveIntegerField(default=9)  # cached = severity * likelihood

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="janus_dd_risks",
    )

    mitigation_plan = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    blocking = models.BooleanField(default=False)

    related_criteria = models.ManyToManyField(DDCriterion, blank=True, related_name="risks")

    class Meta:
        indexes = [
            models.Index(fields=["run", "blocking", "status"]),
            models.Index(fields=["run", "category"]),
        ]

    def __str__(self) -> str:
        return f"{self.run} | {self.title}"

    def save(self, *args, **kwargs):
        self.risk_score = int(self.severity) * int(self.likelihood)
        super().save(*args, **kwargs)


class DDCondition(TimestampedModel):
    class MustCompleteBefore(models.TextChoices):
        SIGNING = "signing", "Signing"
        CLOSING = "closing", "Closing"
        POST_CLOSE_30 = "post_close_30", "Post-close (30 days)"
        POST_CLOSE_90 = "post_close_90", "Post-close (90 days)"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        DONE = "done", "Done"
        WAIVED = "waived", "Waived"

    run = models.ForeignKey(DueDiligenceRun, on_delete=models.CASCADE, related_name="conditions")
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True)

    due_by = models.DateField(null=True, blank=True)
    must_complete_before = models.CharField(
        max_length=20,
        choices=MustCompleteBefore.choices,
        default=MustCompleteBefore.CLOSING,
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)

    mapped_risk = models.ForeignKey(DDRisk, on_delete=models.SET_NULL, null=True, blank=True, related_name="conditions")

    def __str__(self) -> str:
        return f"{self.run} | {self.title}"


class DDParticipant(TimestampedModel):
    class Role(models.TextChoices):
        LEAD = "lead", "Lead"
        REVIEWER = "reviewer", "Reviewer"
        SECURITY = "security", "Security"
        ARCH = "architecture", "Architecture"
        OPS = "ops", "Operations"
        LEGAL = "legal", "Legal"
        OBSERVER = "observer", "Observer"

    class Permission(models.TextChoices):
        VIEW = "view", "View"
        COMMENT = "comment", "Comment"
        SCORE = "score", "Score"
        ADMIN = "admin", "Admin"

    run = models.ForeignKey(DueDiligenceRun, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="janus_dd_participations")

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.REVIEWER)
    permission = models.CharField(max_length=10, choices=Permission.choices, default=Permission.VIEW)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["run", "user"], name="uniq_ddparticipant_run_user")
        ]

    def __str__(self) -> str:
        return f"{self.run} | {self.user} ({self.role})"


class DDPromotionBatch(TimestampedModel):
    run = models.ForeignKey(DueDiligenceRun, on_delete=models.CASCADE, related_name="promotion_batches")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="janus_dd_promotion_batches"
    )
    # Hook for your OKR Entity/Strategy later.
    target_context_label = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.run} | Batch {self.id}"


class DDPromotedItem(TimestampedModel):
    class SourceType(models.TextChoices):
        RISK = "risk", "Risk"
        CONDITION = "condition", "Condition"
        CRITERION = "criterion", "Criterion"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MED = "med", "Medium"
        HIGH = "high", "High"

    batch = models.ForeignKey(DDPromotionBatch, on_delete=models.CASCADE, related_name="items")

    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    source_id = models.PositiveIntegerField()

    proposed_objective = models.CharField(max_length=300)
    proposed_key_result = models.CharField(max_length=400, blank=True)

    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MED)

    # Optional: store created OKR IDs (integers) without hard-depending on OKR app models.
    okr_objective_id = models.PositiveIntegerField(null=True, blank=True)
    okr_key_result_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["batch", "source_type"]),
            models.Index(fields=["source_type", "source_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.batch} | {self.source_type}:{self.source_id}"

from django.db import models
from django.conf import settings


class DDQuantitativeSnapshot(models.Model):
    class Confidence(models.TextChoices):
        LOW = "low", "Low"
        MED = "med", "Medium"
        HIGH = "high", "High"

    run = models.OneToOneField(
        "DueDiligenceRun",
        on_delete=models.CASCADE,
        related_name="snapshot",
    )

    metrics_as_of_date = models.DateField(null=True, blank=True)
    confidence = models.CharField(
        max_length=10,
        choices=Confidence.choices,
        default=Confidence.MED,
    )
    source_notes = models.TextField(blank=True, default="")  # where numbers came from (P&L, Stripe, CRM, etc.)

    # -------- Commercial (facts) --------
    total_customers = models.IntegerField(null=True, blank=True)
    active_customers = models.IntegerField(null=True, blank=True)
    top_1_customer_pct_revenue = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    top_3_customer_pct_revenue = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    avg_contract_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    churn_rate_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)  # e.g., 4.25
    net_revenue_retention_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)  # e.g., 108.00
    win_rate_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    sales_cycle_days = models.IntegerField(null=True, blank=True)
    pipeline_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    # -------- Financial (facts) --------
    revenue_ttm = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)  # trailing 12 months
    mrr = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    arr = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)

    gross_margin_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    operating_income_ttm = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)

    burn_rate_monthly = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    runway_months = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Snapshot for Run #{self.run_id}"
