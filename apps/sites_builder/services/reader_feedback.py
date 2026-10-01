from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def build_reader_feedback_context(article, config: dict | None) -> dict:
    """Build a public feedback link without requiring provider API access."""
    config = config or {}
    provider = str(config.get("provider") or "").strip().lower()
    button_label = str(
        config.get("button_label") or "Share your reasoning →"
    ).strip()
    form_url = str(config.get("form_url") or "").strip()

    context = {
        "enabled": False,
        "provider": provider,
        "url": "",
        "button_label": button_label,
    }
    if not config.get("enabled") or provider != "tally" or not form_url:
        return context

    parts = urlsplit(form_url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return context

    metadata = {
        "article": str(getattr(article, "feedback_identifier", "") or "").strip(),
        "series": str(getattr(article, "series", "") or "").strip(),
        "hypothesis": str(getattr(article, "hypothesis", "") or "").strip(),
    }
    metadata = {key: value for key, value in metadata.items() if value}

    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key not in metadata
    ]
    query.extend(metadata.items())
    context["url"] = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
    context["enabled"] = True
    return context
