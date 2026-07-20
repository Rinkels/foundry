from django import template
from django.utils.html import escape, mark_safe

register = template.Library()


@register.filter
def accentize(headline: str, accent: str) -> str:
    """Wrap the first occurrence of `accent` within `headline` in
    <span class="lp-accent">…</span> for a highlighted/gradient phrase.
    Everything is HTML-escaped; returns safe HTML."""
    headline = headline or ""
    if not accent or accent not in headline:
        return mark_safe(escape(headline))
    i = headline.find(accent)
    before, after = headline[:i], headline[i + len(accent):]
    return mark_safe(
        f"{escape(before)}<span class=\"lp-accent\">{escape(accent)}</span>{escape(after)}"
    )

@register.filter
def to_webp(url: str) -> str:
    """
    Convert a raster image URL to a .webp sibling.
    Examples:
      assets/images/x.png -> assets/images/x.webp
      assets/images/x.jpg -> assets/images/x.webp
      assets/images/x.jpeg -> assets/images/x.webp
    If the URL doesn't end with a known raster extension, returns unchanged.
    """
    if not url:
        return url

    lower = url.lower()
    for ext in (".png", ".jpg", ".jpeg"):
        if lower.endswith(ext):
            return url[: -len(ext)] + ".webp"
    return url
