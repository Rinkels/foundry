"""Generate the customer-facing one-page exposure report.

    python manage.py aegis_report --profile alberta-motor-association
    python manage.py aegis_report --profile acme --out C:\\reports\\acme.pdf --posture

Reads whatever is already in the database. Run `aegis_scan` first, triage the
findings (the triage notes are what the report prints), then generate.
"""
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.aegis.models import Exposure, WatchProfile
from apps.aegis.services import posture as posture_service
from apps.aegis.services import report as report_service


class Command(BaseCommand):
    help = "Generate the one-page public exposure report for a watch profile."

    def add_arguments(self, parser):
        parser.add_argument("--profile", required=True, help="WatchProfile slug.")
        parser.add_argument("--out", default="", help="Output path (default: CWD).")
        parser.add_argument(
            "--posture", action="store_true",
            help="Refresh public-footprint stats before rendering.",
        )
        parser.add_argument(
            "--footer", default="",
            help="Byline printed at the foot (default: settings.AEGIS_REPORT_FOOTER).",
        )

    def handle(self, *args, **opts):
        try:
            profile = WatchProfile.objects.get(slug=opts["profile"])
        except WatchProfile.DoesNotExist:
            raise CommandError(f"No profile with slug '{opts['profile']}'.") from None

        if opts["posture"]:
            if not profile.org_list:
                self.stdout.write(self.style.WARNING(
                    "  --posture skipped: no GitHub org on this profile."))
            else:
                self.stdout.write("Collecting footprint posture…")
                posture_service.collect(profile)

        run = profile.runs.first()
        if not run:
            self.stdout.write(self.style.WARNING(
                "No sweep on record — the report will have no scan figures. "
                "Run `aegis_scan` first."))

        untriaged = profile.exposures.filter(
            status=Exposure.STATUS_NEW,
            severity__in=report_service.MATERIAL_SEVERITIES,
        ).count()
        if untriaged:
            self.stdout.write(self.style.WARNING(
                f"{untriaged} untriaged finding(s) will appear as 'requiring attention'. "
                "Mark false positives before sending this to a customer."))

        pdf = report_service.build(
            profile,
            run=run,
            generated_by=opts["footer"] or getattr(settings, "AEGIS_REPORT_FOOTER", ""),
        )

        out = Path(opts["out"]) if opts["out"] else Path(report_service.filename_for(profile, run))
        if out.is_dir():
            out = out / report_service.filename_for(profile, run)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(pdf)

        self.stdout.write(self.style.SUCCESS(f"Wrote {out}  ({len(pdf):,} bytes)"))
