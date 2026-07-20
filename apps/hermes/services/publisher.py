from pathlib import Path
from django.template.loader import render_to_string
from django.utils import timezone

from ..models import NewsletterSeries, NewsletterIssue
from .renderer import render_issue_markdown


def publish_newsletters_for_site(site_output_dir: Path, site_context: dict | None = None) -> list[Path]:
    """
    Creates static HTML files under:
      <site_output_dir>/newsletters/...
    Returns list of written file paths.
    """
    site_context = site_context or {}
    written: list[Path] = []

    newsletters_root = site_output_dir / "hermes"
    newsletters_root.mkdir(parents=True, exist_ok=True)

    # Index of all series
    series_qs = NewsletterSeries.objects.filter(is_active=True).order_by("name")
    index_html = render_to_string(
        "hermes/newsletters_index.html",
        {"series_list": series_qs, **site_context},
    )
    p = newsletters_root / "index.html"
    p.write_text(index_html, encoding="utf-8")
    written.append(p)

    for series in series_qs:
        series_dir = newsletters_root / series.slug
        series_dir.mkdir(parents=True, exist_ok=True)

        issues_qs = (
            series.issues.filter(status=NewsletterIssue.Status.PUBLISHED)
            .order_by("-published_at", "-created_at")
        )

        series_html = render_to_string(
            "hermes/series_index.html",
            {"series": series, "issues": issues_qs, **site_context},
        )
        p = series_dir / "index.html"
        p.write_text(series_html, encoding="utf-8")
        written.append(p)

        for issue in issues_qs:
            issue_dir = series_dir / issue.slug
            issue_dir.mkdir(parents=True, exist_ok=True)

            rendered = render_issue_markdown(issue.body_md)
            issue_html = render_to_string(
                "hermes/issue.html",
                {
                    "series": series,
                    "issue": issue,
                    "issue_body_html": rendered.html_body,
                    "generated_at": timezone.now(),
                    **site_context,
                },
            )
            p = issue_dir / "index.html"
            p.write_text(issue_html, encoding="utf-8")
            written.append(p)

    return written
