"""Drain the Atlas deploy queue.

Durable background processing for queued deploys. Run it as a long-lived
process (e.g. a Cloud Run Job, a systemd service, or a sidecar):

    python manage.py atlas_worker                 # loop forever, poll every 5s
    python manage.py atlas_worker --once          # process pending then exit
    python manage.py atlas_worker --interval 10   # custom poll interval
    python manage.py atlas_worker --reclaim 1800  # requeue runs stuck >30m

When ATLAS_INLINE_WORKER is False (recommended for production), this is the
only thing that processes deploys — the web process just enqueues them.
"""
from __future__ import annotations

import time

from django.core.management.base import BaseCommand

from apps.atlas.services import provisioner


class Command(BaseCommand):
    help = "Process queued Atlas deploy jobs."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process pending jobs once and exit.")
        parser.add_argument("--interval", type=int, default=5, help="Poll interval in seconds (loop mode).")
        parser.add_argument(
            "--reclaim", type=int, default=0,
            help="At startup, requeue 'running' jobs older than N seconds (crash recovery).",
        )

    def handle(self, *args, **opts):
        if opts["reclaim"]:
            n = provisioner.reclaim_stale(opts["reclaim"])
            if n:
                self.stdout.write(self.style.WARNING(f"Reclaimed {n} stale running job(s)."))

        if opts["once"]:
            processed = provisioner.process_pending()
            self.stdout.write(self.style.SUCCESS(f"Processed {processed} job(s)."))
            return

        self.stdout.write(self.style.SUCCESS("Atlas worker started. Ctrl-C to stop."))
        try:
            while True:
                processed = provisioner.process_pending()
                if processed:
                    self.stdout.write(f"Processed {processed} job(s).")
                time.sleep(opts["interval"])
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Atlas worker stopped."))
