# apps/athena/services/usage.py
"""
Record Athena LLM runs into the shared AI billing ledger (apps.common.AiUsageEvent)
so they roll up on the Fractals home dashboard's AI Spend card.

Each Studio run is linked to its AthenaStudioRun via the generic content_object.
Echo/dev runs (zero tokens) are skipped so the ledger isn't polluted with $0 rows.
"""
from __future__ import annotations

from typing import Optional

from django.contrib.contenttypes.models import ContentType

from apps.common.models import AiUsageEvent
from apps.common.services.ai_pricing import estimate_cost_usd


def record_studio_usage(
    *,
    run,                      # AthenaStudioRun (the thing this spend was for)
    actor=None,
    action: str = "athena_studio_run",
    model: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_input_tokens: int = 0,
    total_tokens: int = 0,
    meta: Optional[dict] = None,
) -> Optional[AiUsageEvent]:
    """
    Create an AiUsageEvent for a completed Studio run. Returns None when there's
    nothing to bill (no model or zero tokens — e.g. the Echo dev provider).
    """
    input_tokens = int(input_tokens or 0)
    output_tokens = int(output_tokens or 0)
    cached_input_tokens = int(cached_input_tokens or 0)
    total_tokens = int(total_tokens or 0) or (input_tokens + output_tokens)

    if not model or total_tokens <= 0:
        return None

    cost = estimate_cost_usd(model, input_tokens, output_tokens, cached_input_tokens=cached_input_tokens)

    return AiUsageEvent.objects.create(
        content_type=ContentType.objects.get_for_model(run.__class__),
        object_id=run.pk,
        actor=actor if (actor is not None and getattr(actor, "is_authenticated", False)) else None,
        action=action,
        model=model,
        input_tokens=input_tokens,
        cached_input_tokens=cached_input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cost_usd=cost,
        meta=meta or {},
    )


def record_studio_usage_from_result(*, run, actor, llm_result, action: str = "athena_studio_run", meta=None):
    """Convenience wrapper for the non-streaming paths that have an LLMResult."""
    return record_studio_usage(
        run=run,
        actor=actor,
        action=action,
        model=getattr(llm_result, "model", "") or "",
        input_tokens=getattr(llm_result, "input_tokens", 0),
        output_tokens=getattr(llm_result, "output_tokens", 0),
        cached_input_tokens=getattr(llm_result, "cached_input_tokens", 0),
        total_tokens=getattr(llm_result, "total_tokens", 0),
        meta=meta,
    )
