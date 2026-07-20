"""# Recalc everything
python manage.py janus_recalc_scores

# Only Zen Cyber (name contains)
python manage.py janus_recalc_scores --target "Zen"

# Only template name contains "Technical"
python manage.py janus_recalc_scores --template "Technical"

# Only in-progress runs
python manage.py janus_recalc_scores --status in_progress

# One specific run
python manage.py janus_recalc_scores --run-id 12

# Dry run preview
python manage.py janus_recalc_scores --target "Goal" --dry-run
"""
from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import DDResponse, DDCriterion, DDSection, ScoreScale, DueDiligenceRun


def _recalc_runs(qs):
    """
    Recalc scores for each run in queryset.
    Uses iterator() to avoid loading everything at once.
    """
    for run in qs.iterator():
        run.recalc_scores(save=True)


def _runs_for_template(template_id: int):
    return DueDiligenceRun.objects.filter(template_id=template_id)


# ---------------------------------------
# Response signals (already requested)
# ---------------------------------------
@receiver(post_save, sender=DDResponse)
def ddresponse_saved_recalc_run(sender, instance: DDResponse, **kwargs):
    if instance.run_id:
        instance.run.recalc_scores(save=True)


@receiver(post_delete, sender=DDResponse)
def ddresponse_deleted_recalc_run(sender, instance: DDResponse, **kwargs):
    if instance.run_id:
        instance.run.recalc_scores(save=True)


# ---------------------------------------
# Criterion/Section changes (weights, etc.)
# ---------------------------------------
@receiver(post_save, sender=DDCriterion)
def ddcriterion_saved_recalc_runs(sender, instance: DDCriterion, **kwargs):
    """
    If criterion weight/scale/non-negotiable changes, overall score can change
    even if responses stay the same.
    Recalc all runs for the criterion's template.
    """
    template_id = instance.section.template_id
    _recalc_runs(_runs_for_template(template_id))


@receiver(post_delete, sender=DDCriterion)
def ddcriterion_deleted_recalc_runs(sender, instance: DDCriterion, **kwargs):
    """
    Removing a criterion impacts scoring normalization and section totals.
    Recalc all runs for the criterion's template.
    """
    # instance.section may still be available in post_delete
    template_id = getattr(getattr(instance, "section", None), "template_id", None)
    if template_id:
        _recalc_runs(_runs_for_template(template_id))


@receiver(post_save, sender=DDSection)
def ddsection_saved_recalc_runs(sender, instance: DDSection, **kwargs):
    """
    Section weight/order changes can change overall score weighting.
    Recalc all runs for the template.
    """
    _recalc_runs(_runs_for_template(instance.template_id))


@receiver(post_delete, sender=DDSection)
def ddsection_deleted_recalc_runs(sender, instance: DDSection, **kwargs):
    template_id = getattr(instance, "template_id", None)
    if template_id:
        _recalc_runs(_runs_for_template(template_id))


# ---------------------------------------
# Score scale changes (min/max labels)
# ---------------------------------------
@receiver(post_save, sender=ScoreScale)
def scorescale_saved_recalc_runs(sender, instance: ScoreScale, **kwargs):
    """
    If scale bounds change, normalization changes.
    Recalc runs for any template that uses this scale.
    """
    template_ids = (
        DDCriterion.objects.filter(scoring_scale=instance)
        .values_list("section__template_id", flat=True)
        .distinct()
    )
    _recalc_runs(DueDiligenceRun.objects.filter(template_id__in=list(template_ids)))


@receiver(post_delete, sender=ScoreScale)
def scorescale_deleted_recalc_runs(sender, instance: ScoreScale, **kwargs):
    # If a scale is deleted, criteria would be blocked (PROTECT), so this may never fire.
    pass
