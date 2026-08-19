"""Exposure / reachability ranking for security findings.

Achilles can't build a full call graph cheaply, but the *file's role* is a strong,
free signal for how reachable/exposed a finding is:

- HIGH  — routed views, URL configs, settings, middleware, admin, tasks, API/edge
          handlers, and anything flagged as a leaked secret (exposed if committed).
- LOW   — tests, migrations, scripts, fixtures, samples/examples/seeds/demos.
- MED   — everything else (models/services/utils — reached indirectly).

priority = severity_weight * 3 + exposure_weight, so severity dominates and
exposure breaks ties. Findings are annotated + sorted so the riskiest surface
first (and the AI "verify sample" spends on those first).
"""
from __future__ import annotations

import re

_SEV_RE = re.compile(r"^\[(HIGH|MED|LOW)\]")

HIGH_HINTS = (
    "views.py", "urls.py", "settings.py", "asgi.py", "wsgi.py", "middleware",
    "tasks.py", "celery", "admin.py", "consumers.py", "routes", "/api/",
    "/functions/", "handler", "serverless",
)
LOW_HINTS = (
    "/tests/", "/test_", "_test.py", "test_", ".test.", "/migrations/",
    "/scripts/", "/fixtures/", "fixture", "/samples/", "sample", "/examples/",
    "example", "conftest.py", "/demo", "seed",
)
SECRETY = ("secret", "password", "token", "api key", "apikey", "credential", "private key")

SEV_W = {"HIGH": 3, "MED": 2, "LOW": 1, "": 1}
EXP_W = {"high": 3, "med": 2, "low": 1}


def severity_label(item) -> str:
    m = _SEV_RE.match(item.name or "")
    return m.group(1) if m else (item.severity or "")


def exposure(item) -> str:
    f = (item.file or "").replace("\\", "/").lower()
    name = (item.name or "").lower()
    if any(s in name for s in SECRETY):
        return "high"
    if any(h in f for h in LOW_HINTS):
        return "low"
    if any(h in f for h in HIGH_HINTS):
        return "high"
    return "med"


def priority(item) -> int:
    return SEV_W.get(severity_label(item), 1) * 3 + EXP_W.get(exposure(item), 2)


def annotate_and_sort(items: list) -> list:
    """Attach .severity_label / .exposure / .priority and return sorted (riskiest first)."""
    for it in items:
        it.severity_label = severity_label(it)
        it.exposure = exposure(it)
        it.priority = priority(it)
    return sorted(items, key=lambda x: (-x.priority, x.file or "", x.lineno or 0))
