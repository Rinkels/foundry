# apps/atlas/apps.py
import logging
import os
import sys
import threading
import time

from django.apps import AppConfig

log = logging.getLogger(__name__)


class AtlasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.atlas"
    label = "atlas"
    verbose_name = "Atlas"

    def ready(self):
        # Self-healing: once the webhook receiver is up, replay any push
        # deliveries GitHub couldn't hand us while Foundry was down. Only under
        # runserver (not tests/migrations/other commands), and only in the
        # process that actually serves (the autoreloader's child, or the single
        # --noreload process).
        from django.conf import settings
        if not getattr(settings, "ATLAS_REDELIVER_ON_START", True) or "runserver" not in sys.argv:
            return
        if "--noreload" not in sys.argv and os.environ.get("RUN_MAIN") != "true":
            return
        threading.Thread(target=_startup_redeliver, name="atlas-redeliver", daemon=True).start()


def _startup_redeliver() -> None:
    from django.db import connections
    from .services import redelivery
    time.sleep(20)  # let the server bind and the tunnel start answering
    try:
        summary = redelivery.redeliver_missed()
        if summary["found"]:
            log.warning("Atlas replayed missed webhook deliveries: %s (errors: %s)",
                        summary["redelivered"], summary["errors"])
    except Exception as exc:  # noqa: BLE001 — never take the server down over this
        log.warning("Atlas startup redelivery skipped: %s", exc)
    finally:
        connections.close_all()
