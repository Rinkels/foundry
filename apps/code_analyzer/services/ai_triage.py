"""AI triage for Achilles security findings.

For each raw pattern finding, ask a model to (a) confirm REAL vs FALSE-POSITIVE
for this specific code, (b) explain briefly with evidence, and (c) suggest a
concrete fix. Verdicts are stored on the ScanItem; spend is recorded to the
shared AiUsageEvent ledger. `estimate()` gives a pre-run cost (transparency).
"""
from __future__ import annotations

import json
import os
import re
from decimal import Decimal
from pathlib import Path

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from apps.common.models import AiUsageEvent
from ..models import ScanItem, ScanRun

MODEL = "gpt-4o-mini"                 # cheap + fast; good for localized triage
PRICE_IN = 0.15 / 1_000_000          # $/input token
PRICE_OUT = 0.60 / 1_000_000         # $/output token
_CTX_RADIUS = 22                     # lines of code context around the finding
_JSON = re.compile(r"\{.*\}", re.DOTALL)


def security_items(scan_run: ScanRun):
    return (ScanItem.objects
            .filter(scan_project__scan_run=scan_run, bucket="security")
            .select_related("scan_project")
            .order_by("scan_project__name", "file", "lineno"))


def estimate(scan_run: ScanRun) -> dict:
    """Rough pre-run cost estimate (~700 in / ~280 out tokens per finding)."""
    n = security_items(scan_run).count()
    est_in, est_out = n * 700, n * 280
    cost = est_in * PRICE_IN + est_out * PRICE_OUT
    return {"count": n, "est_input_tokens": est_in, "est_output_tokens": est_out,
            "est_cost_usd": round(cost, 4), "model": MODEL}


def _read_context(item: ScanItem) -> str:
    try:
        fp = Path(item.scan_project.path) / item.file
        if not fp.exists():
            fp = Path(item.file)
        lines = fp.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return "(source unavailable)"
    ln = item.lineno or 1
    lo, hi = max(0, ln - _CTX_RADIUS), min(len(lines), ln + _CTX_RADIUS)
    return "\n".join(
        f"{'>>' if (i + 1) == ln else '  '}{i + 1:5} {lines[i]}" for i in range(lo, hi)
    )


def _prompt(item: ScanItem, context: str) -> str:
    return (
        "You are a senior application-security engineer triaging ONE static-analysis "
        "finding. Decide if it is a REAL issue or a FALSE POSITIVE for this specific "
        "code, explain briefly citing the code, and give a concrete fix.\n\n"
        "Return STRICT JSON only, no markdown:\n"
        '{"verdict":"real|false_positive|uncertain","confidence":"low|medium|high",'
        '"explanation":"1-3 sentences referencing the code","fix":"specific remediation '
        '(short code snippet or steps)"}\n\n'
        f"Project type: {item.scan_project.project_type or 'unknown'}\n"
        f"Finding: {item.name}\n"
        f"File: {item.file} (line {item.lineno})\n\n"
        f"Code (>> marks the flagged line):\n{context}\n"
    )


def _extract(raw: str) -> dict:
    m = _JSON.search(raw or "")
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}


def run_triage(scan_run: ScanRun, user=None, limit: int | None = None) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    from . import ranking
    items = ranking.annotate_and_sort(list(security_items(scan_run)))  # riskiest first
    if limit:
        items = items[:limit]

    reviewed = real = fp = unc = 0
    in_tok = out_tok = 0
    for it in items:
        prompt = _prompt(it, _read_context(it))
        try:
            resp = client.responses.create(model=MODEL, input=prompt, temperature=0.1, max_output_tokens=500)
            data = _extract(getattr(resp, "output_text", "") or "")
            u = getattr(resp, "usage", None)
            if u:
                in_tok += getattr(u, "input_tokens", 0) or 0
                out_tok += getattr(u, "output_tokens", 0) or 0
        except Exception as e:  # noqa: BLE001
            data = {"verdict": "uncertain", "confidence": "low",
                    "explanation": f"AI review failed: {e}", "fix": ""}

        verdict = (data.get("verdict") or "uncertain").lower()
        if verdict not in ("real", "false_positive", "uncertain"):
            verdict = "uncertain"
        it.ai_verdict = verdict
        it.ai_confidence = (data.get("confidence") or "")[:8]
        it.ai_explanation = (data.get("explanation") or "")[:2000]
        it.ai_fix = (data.get("fix") or "")[:3000]
        it.ai_reviewed_at = timezone.now()
        it.status = {"real": "confirmed", "false_positive": "false_positive"}.get(verdict, "open")
        it.save(update_fields=["ai_verdict", "ai_confidence", "ai_explanation",
                               "ai_fix", "ai_reviewed_at", "status"])
        reviewed += 1
        real += verdict == "real"
        fp += verdict == "false_positive"
        unc += verdict == "uncertain"

    cost = in_tok * PRICE_IN + out_tok * PRICE_OUT
    try:
        AiUsageEvent.objects.create(
            content_type=ContentType.objects.get_for_model(ScanRun), object_id=scan_run.id,
            actor=user, action="achilles_ai_triage", model=MODEL,
            input_tokens=in_tok, output_tokens=out_tok, total_tokens=in_tok + out_tok,
            cost_usd=Decimal(str(round(cost, 6))),
            meta={"reviewed": reviewed, "real": real, "false_positive": fp, "uncertain": unc},
        )
    except Exception:  # noqa: BLE001
        pass

    return {"reviewed": reviewed, "real": real, "false_positive": fp, "uncertain": unc,
            "cost_usd": round(cost, 4), "input_tokens": in_tok, "output_tokens": out_tok}
