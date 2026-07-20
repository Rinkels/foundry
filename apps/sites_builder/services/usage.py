"""Record sites_builder AI calls (text + image generation) into the shared
AI billing ledger (apps.common.AiUsageEvent) so they roll up on the Fractals
home AI-Spend card — mirrors apps/athena/services/usage.py."""
from __future__ import annotations

from typing import Optional

from django.contrib.contenttypes.models import ContentType

from apps.common.models import AiUsageEvent
from apps.common.services.ai_pricing import estimate_cost_usd, estimate_image_cost_usd


def _record(obj, **fields) -> Optional[AiUsageEvent]:
    if obj is None or getattr(obj, "pk", None) is None:
        return None
    return AiUsageEvent.objects.create(
        content_type=ContentType.objects.get_for_model(obj.__class__),
        object_id=obj.pk,
        **fields,
    )


def record_text_usage(*, obj, action: str, model: str, input_tokens: int = 0,
                      output_tokens: int = 0, cached_input_tokens: int = 0,
                      total_tokens: int = 0, meta: Optional[dict] = None) -> Optional[AiUsageEvent]:
    """Token-based LLM call (e.g. landing-section / page generation)."""
    input_tokens = int(input_tokens or 0)
    output_tokens = int(output_tokens or 0)
    cached_input_tokens = int(cached_input_tokens or 0)
    total_tokens = int(total_tokens or 0) or (input_tokens + output_tokens)
    if not model or total_tokens <= 0:
        return None
    cost = estimate_cost_usd(model, input_tokens, output_tokens, cached_input_tokens=cached_input_tokens)
    return _record(
        obj, action=action, model=model,
        input_tokens=input_tokens, cached_input_tokens=cached_input_tokens,
        output_tokens=output_tokens, total_tokens=total_tokens,
        cost_usd=cost, meta=meta or {},
    )


def record_image_usage(*, obj, action: str, model: str, size: str, quality: str = "high",
                       count: int = 1, meta: Optional[dict] = None) -> Optional[AiUsageEvent]:
    """Image generation — a flat per-image fee booked as tool_cost_usd (no tokens)."""
    if not model:
        return None
    cost = estimate_image_cost_usd(model, size, quality, count=count)
    m = {"size": size, "quality": quality, "images": int(count or 1)}
    if meta:
        m.update(meta)
    return _record(obj, action=action, model=model, tool_cost_usd=cost, meta=m)
