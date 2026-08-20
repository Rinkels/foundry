"""Achilles -> Sentry (DG security-posture platform) export.

Emits Achilles security findings in a normalized, source-agnostic shape that
maps 1:1 onto Sentry's models (SecuritySource -> SecurityDefinition ->
SecurityFinding, per SecurityApplication/Asset). Sentry pulls this like it pulls
Snyk/Tenable/Invicti for the AMA client — but Achilles is the source for our OWN
apps. Findings are keyed by the same fingerprint the deploy gate uses, so Sentry
can dedupe/trend across scans.

Contract (schema_version 1.0):
{
  "source": {"vendor": "achilles", "name": "...", "external_id": "achilles-foundry"},
  "schema_version": "1.0", "generated_at": ISO8601, "scan_run_id": int,
  "applications": [
    {"name": "DG", "asset": {"identifier","type","path"},
     "findings": [
        {"fingerprint","external_id","title",
         "definition": {"external_id","title","family","cwe":[...]},
         "native_severity":"HIGH","severity":"high|medium|low|info",
         "status","disposition","location":{"file","line"},
         "exposure","ai_verdict","ai_explanation","ai_fix","raw":{...}}]}
  ]
}
"""
from __future__ import annotations

import re

from django.utils import timezone

from ..models import ScanItem, ScanRun, ScannedProject
from . import deploy_gate, ranking

_SEV_MAP = {"HIGH": "high", "MED": "medium", "MEDIUM": "medium", "LOW": "low", "": "info"}

# (family, regex) — first match wins. Families roughly map to SOC2 control groups.
_FAMILIES = [
    ("secrets", r"secret|hardcoded|token|password|api[_-]?key"),
    ("access-control", r"login_required|LoginRequiredMixin|CBV missing|authenticat"),
    ("injection", r"\bSQL\b|injection|f-string"),
    ("dangerous-call", r"\beval\b|\bexec\b|pickle|yaml\.load|shell=True|mktemp"),
    ("tls", r"verify=False|TLS|unverified|ssl"),
    ("secure-config", r"DEBUG|ALLOWED_HOSTS|SECRET_KEY|SecurityMiddleware|HSTS|sqlite|hardening|cookie"),
]
# CWE hints per family (best-effort; Sentry can enrich).
_CWE = {"secrets": ["CWE-798"], "access-control": ["CWE-306"], "injection": ["CWE-89"],
        "dangerous-call": ["CWE-94"], "tls": ["CWE-295"], "secure-config": ["CWE-16"]}


def _strip_sev(name: str) -> str:
    return re.sub(r"^\s*\[[A-Z]+\]\s*", "", name or "").strip()


def _severity(it) -> str:
    lbl = (getattr(it, "severity_label", "") or it.severity or "").upper()
    return _SEV_MAP.get(lbl, "info")


def _family(name: str) -> str:
    for fam, pat in _FAMILIES:
        if re.search(pat, name or "", re.I):
            return fam
    return "other"


def _rule_id(name: str) -> str:
    base = _strip_sev(name).split(":")[0].split("(")[0].strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", base).strip("-")[:80]
    return "achilles." + (slug or "finding")


def _disposition(it) -> str:
    v = (it.ai_verdict or "").lower()
    if v in ("false_positive", "false-positive", "fp"):
        return "false_positive"
    if v == "real":
        return "confirmed"
    return "open"


def build_export(run: ScanRun | None = None) -> dict:
    run = run or ScanRun.objects.order_by("-created_at", "-id").first()
    applications = []
    if run:
        for sp in ScannedProject.objects.filter(scan_run=run):
            items = ranking.annotate_and_sort(
                list(ScanItem.objects.filter(scan_project=sp, bucket="security"))
            )
            findings = []
            for it in items:
                fp = deploy_gate._fp(it)
                fam = _family(it.name)
                findings.append({
                    "fingerprint": fp,
                    "external_id": fp,
                    "title": _strip_sev(it.name)[:300],
                    "definition": {
                        "external_id": _rule_id(it.name),
                        "title": _strip_sev(it.name)[:300],
                        "family": fam,
                        "cwe": _CWE.get(fam, []),
                    },
                    "native_severity": (getattr(it, "severity_label", "") or it.severity or "").upper(),
                    "severity": _severity(it),
                    "status": it.status or "open",
                    "disposition": _disposition(it),
                    "location": {"file": it.file, "line": it.lineno},
                    "exposure": getattr(it, "exposure", None),
                    "ai_verdict": it.ai_verdict or None,
                    "ai_explanation": it.ai_explanation or None,
                    "ai_fix": it.ai_fix or None,
                    "raw": {"bucket": it.bucket, "kind": it.kind, "priority": getattr(it, "priority", None)},
                })
            applications.append({
                "name": sp.name,
                "asset": {"identifier": sp.name, "type": "code_repository",
                          "path": getattr(sp, "path", "") or ""},
                "findings": findings,
            })
    return {
        "source": {"vendor": "achilles", "name": "Achilles (Foundry code analyzer)",
                   "external_id": "achilles-foundry"},
        "schema_version": "1.0",
        "generated_at": timezone.now().isoformat(),
        "scan_run_id": run.id if run else None,
        "applications": applications,
    }
