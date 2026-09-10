"""Drain the Athena agent-run queue.

Durable background processing for queued headless Claude Code runs. Mirrors
`atlas_worker`. Run as a long-lived process when ATHENA_INLINE_WORKER is False:

    python manage.py athena_agent_worker                 # loop forever, poll every 5s
    python manage.py athena_agent_worker --once          # process pending then exit
    python manage.py athena_agent_worker --interval 10   # custom poll interval
    python manage.py athena_agent_worker --reclaim 1800  # requeue runs stuck >30m
"""
from __future__ import annotations

import time

from django.core.management.base import BaseCommand

from apps.athena.services import agent_runner


class Command(BaseCommand):
    help = "Process queued Athena agent runs."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process pending runs once and exit.")
        parser.add_argument("--interval", type=int, default=5, help="Poll interval in seconds (loop mode).")
        parser.add_argument(
            "--reclaim", type=int, default=0,
            help="At startup, requeue 'running' runs older than N seconds (crash recovery).",
        )

    def handle(self, *args, **opts):
        if opts["reclaim"]:
            n = agent_runner.reclaim_stale(opts["reclaim"])
            if n:
                self.stdout.write(self.style.WARNING(f"Reclaimed {n} stale running run(s)."))

        if opts["once"]:
            processed = agent_runner.process_pending()
            self.stdout.write(self.style.SUCCESS(f"Processed {processed} run(s)."))
            return

        self.stdout.write(self.style.SUCCESS("Athena agent worker started. Ctrl-C to stop."))
        try:
            while True:
                processed = agent_runner.process_pending()
                if processed:
                    self.stdout.write(f"Processed {processed} run(s).")
                time.sleep(opts["interval"])
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Athena agent worker stopped."))
