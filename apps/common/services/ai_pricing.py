from decimal import Decimal

# Rates are USD per 1M tokens.
# For Anthropic, cached_input is the prompt-cache *read* rate (~0.1x input).
MODEL_RATES = {
    "gpt-4o": {
        "input": Decimal("2.50"),
        "cached_input": Decimal("1.25"),
        "output": Decimal("10.00"),
    },
    "gpt-4o-mini": {
        "input": Decimal("0.15"),
        "cached_input": Decimal("0.08"),
        "output": Decimal("0.60"),
    },
    # gpt-4.1 family (used by sites_builder's generator). Longer keys first for prefix match.
    "gpt-4.1-mini": {"input": Decimal("0.40"), "cached_input": Decimal("0.10"), "output": Decimal("1.60")},
    "gpt-4.1-nano": {"input": Decimal("0.10"), "cached_input": Decimal("0.025"), "output": Decimal("0.40")},
    "gpt-4.1": {"input": Decimal("2.00"), "cached_input": Decimal("0.50"), "output": Decimal("8.00")},
    # OpenAI current lineup — https://developers.openai.com/api/docs/pricing
    # (the gpt-5.x family; gpt-4.1/o3/o4 are legacy and no longer listed)
    "gpt-5.5-pro": {  # longer key must precede "gpt-5.5" for prefix matching
        "input": Decimal("30.00"),
        "cached_input": Decimal("30.00"),  # no cached rate published; charge full
        "output": Decimal("180.00"),
    },
    "gpt-5.5": {
        "input": Decimal("5.00"),
        "cached_input": Decimal("0.50"),
        "output": Decimal("30.00"),
    },
    "gpt-5.4-mini": {
        "input": Decimal("0.75"),
        "cached_input": Decimal("0.075"),
        "output": Decimal("4.50"),
    },
    "gpt-5.4-nano": {
        "input": Decimal("0.20"),
        "cached_input": Decimal("0.02"),
        "output": Decimal("1.25"),
    },
    "gpt-5.4-pro": {
        "input": Decimal("30.00"),
        "cached_input": Decimal("30.00"),  # no cached rate published; charge full
        "output": Decimal("180.00"),
    },
    "gpt-5.4": {
        "input": Decimal("2.50"),
        "cached_input": Decimal("0.25"),
        "output": Decimal("15.00"),
    },
    "gpt-5.3-codex": {
        "input": Decimal("1.75"),
        "cached_input": Decimal("0.175"),
        "output": Decimal("14.00"),
    },
    "chat-latest": {
        "input": Decimal("5.00"),
        "cached_input": Decimal("0.50"),
        "output": Decimal("30.00"),
    },
    # Anthropic (Claude) — https://platform.claude.com/docs/en/pricing
    "claude-opus-4-8": {
        "input": Decimal("5.00"),
        "cached_input": Decimal("0.50"),
        "output": Decimal("25.00"),
    },
    "claude-opus-4-7": {
        "input": Decimal("5.00"),
        "cached_input": Decimal("0.50"),
        "output": Decimal("25.00"),
    },
    "claude-sonnet-4-6": {
        "input": Decimal("3.00"),
        "cached_input": Decimal("0.30"),
        "output": Decimal("15.00"),
    },
    "claude-haiku-4-5": {
        "input": Decimal("1.00"),
        "cached_input": Decimal("0.10"),
        "output": Decimal("5.00"),
    },
}


def _resolve_rates(model: str):
    """
    Resolve rates for a model id, tolerating dated/suffixed variants
    (e.g. 'claude-opus-4-8-20260101' or 'gpt-4o-2024-08-06') by longest
    matching prefix.
    """
    if not model:
        return None
    if model in MODEL_RATES:
        return MODEL_RATES[model]
    for key in sorted(MODEL_RATES, key=len, reverse=True):
        if model.startswith(key):
            return MODEL_RATES[key]
    return None


# Per-image fees (USD), keyed by model -> quality -> size. Estimates; tune as needed.
IMAGE_RATES = {
    "gpt-image-1": {
        "low":    {"1024x1024": Decimal("0.011"), "1536x1024": Decimal("0.016"), "1024x1536": Decimal("0.016")},
        "medium": {"1024x1024": Decimal("0.042"), "1536x1024": Decimal("0.063"), "1024x1536": Decimal("0.063")},
        "high":   {"1024x1024": Decimal("0.167"), "1536x1024": Decimal("0.25"),  "1024x1536": Decimal("0.25")},
    },
    "dall-e-3": {
        "standard": {"1024x1024": Decimal("0.04"), "1792x1024": Decimal("0.08"), "1024x1792": Decimal("0.08")},
        "hd":       {"1024x1024": Decimal("0.08"), "1792x1024": Decimal("0.12"), "1024x1792": Decimal("0.12")},
    },
}


def estimate_image_cost_usd(model: str, size: str, quality: str = "high", count: int = 1) -> Decimal:
    """Flat per-image fee for image models (gpt-image-1, dall-e-3). Returns 0 if unknown."""
    by_quality = IMAGE_RATES.get(model) or {}
    by_size = by_quality.get((quality or "").lower()) or {}
    rate = by_size.get(size)
    if rate is None:
        # fall back to any rate for that quality, else 0
        rate = next(iter(by_size.values()), Decimal("0"))
    return (rate * Decimal(int(count or 1))).quantize(Decimal("0.000001"))


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int, cached_input_tokens: int = 0) -> Decimal:
    rates = _resolve_rates(model)
    if not rates:
        return Decimal("0")

    uncached_input = max(0, int(input_tokens) - int(cached_input_tokens))

    cost = (
        Decimal(uncached_input) * rates["input"] +
        Decimal(cached_input_tokens) * rates["cached_input"] +
        Decimal(output_tokens) * rates["output"]
    ) / Decimal("1000000")

    return cost.quantize(Decimal("0.000001"))
