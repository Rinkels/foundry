"""python manage.py janus_backfill_responses
# or only Hire Output run 1
python manage.py janus_backfill_responses --run-id 1"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.janus.models import DueDiligenceRun, DDResponse, DDCriterion


class Command(BaseCommand):
    help = "Ensure every DueDiligenceRun has a blank DDResponse for each criterion in its template."

    def add_arguments(self, parser):
        parser.add_argument("--run-id", type=int, help="Only backfill this run id.")
        parser.add_argument("--template", type=str, help="Template name contains filter.")
        parser.add_argument("--limit", type=int, default=0, help="Limit processed runs (0 = no limit).")

    @transaction.atomic
    def handle(self, *args, **opts):
        qs = DueDiligenceRun.objects.select_related("template").all().order_by("-created_at")

        if opts.get("run_id"):
            qs = qs.filter(id=opts["run_id"])
        if opts.get("template"):
            qs = qs.filter(template__name__icontains=opts["template"])
        if opts.get("limit") and opts["limit"] > 0:
            qs = qs[: opts["limit"]]

        total_runs = qs.count()
        if total_runs == 0:
            self.stdout.write(self.style.WARNING("No runs matched."))
            return

        self.stdout.write(f"Processing {total_runs} run(s)...")

        for run in qs.iterator():
            criteria_ids = list(
                DDCriterion.objects.filter(section__template=run.template).values_list("id", flat=True)
            )
            existing = set(
                DDResponse.objects.filter(run=run).values_list("criterion_id", flat=True)
            )
            missing = [cid for cid in criteria_ids if cid not in existing]

            if not missing:
                self.stdout.write(f"[{run.id}] OK (no missing responses)")
                continue

            DDResponse.objects.bulk_create(
                [DDResponse(run=run, criterion_id=cid) for cid in missing],
                ignore_conflicts=True,
            )
            run.recalc_scores(save=True)
            self.stdout.write(self.style.SUCCESS(f"[{run.id}] Added {len(missing)} blank response(s)"))

        self.stdout.write(self.style.SUCCESS("Backfill complete."))
