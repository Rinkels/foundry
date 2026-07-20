from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from .models import NewsletterSeries, NewsletterIssue
from .services.renderer import render_issue_markdown

@login_required
def newsletters_index(request):
    series_list = NewsletterSeries.objects.filter(is_active=True).order_by("name")
    return render(request, "hermes/newsletters_index.html", {"series_list": series_list})

@login_required
def series_index(request, series_slug: str):
    series = get_object_or_404(NewsletterSeries, slug=series_slug, is_active=True)
    issues = (
        series.issues.filter(status=NewsletterIssue.Status.PUBLISHED)
        .order_by("-published_at", "-created_at")
    )
    return render(request, "hermes/series_index.html", {"series": series, "issues": issues})

@login_required
def issue_detail(request, series_slug: str, issue_slug: str):
    series = get_object_or_404(NewsletterSeries, slug=series_slug, is_active=True)
    issue = get_object_or_404(series.issues, slug=issue_slug, status=NewsletterIssue.Status.PUBLISHED)

    rendered = render_issue_markdown(issue.body_md)
    return render(
        request,
        "hermes/issue.html",
        {"series": series, "issue": issue, "issue_body_html": rendered.html_body},
    )
