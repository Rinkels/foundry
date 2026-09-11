"""Replay GitHub push webhooks that failed while Foundry was down.

    python manage.py atlas_redeliver              # replay missed deliveries (last 72h)
    python manage.py atlas_redeliver --dry-run    # just list them
    python manage.py atlas_redeliver --hours 168  # look back a week

Also runs automatically ~20s after `runserver` starts (ATLAS_REDELIVER_ON_START).
Foundry must be listening on the tunnel's port for a redelivery to succeed.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.atlas.services import redelivery


class Command(BaseCommand):
    help = "Replay GitHub push webhook deliveries that failed (e.g. 502 while Foundry was down)."

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=None, help="Look-back window (default: ATLAS_REDELIVER_HOURS).")
        parser.add_argument("--dry-run", action="store_true", help="List missed deliveries without replaying them.")

    def handle(self, *args, **opts):
        summary = redelivery.redeliver_missed(opts["hours"], dry_run=opts["dry_run"])
        if not summary["found"]:
            self.stdout.write(self.style.SUCCESS("No missed deliveries."))
            return
        self.stdout.write(f"Missed: {len(summary['found'])}")
        for label in summary["found"]:
            self.stdout.write(f"  - {label}")
        if summary["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run — nothing replayed."))
            return
        for label in summary["redelivered"]:
            self.stdout.write(self.style.SUCCESS(f"Redelivered: {label}"))
        for err in summary["errors"]:
            self.stdout.write(self.style.ERROR(err))
