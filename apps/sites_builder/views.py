import io
import json
import logging
import random
import re
import socket
import time
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone as dt_timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods, require_POST

from apps.common.chat_r1 import chat_with_gpt_json

from .forms import WebsiteDownloadForm
from .models import (
    ArticleCornerstoneLink,
    DeploymentTarget,
    EvergreenArticle,
    Page,
    Site,
    SiteAuditIssue,
    SiteAuditRun,
)
from .services.deployment import Deployer
from .services.ga4_service import fetch_summary
from .services.generator import SiteGenerator
from .services.hero_image_regenerator import regenerate_site_hero_images
from .services.image_generator import ImageGenerator
from .services.static_builder import StaticBuilder


logger = logging.getLogger(__name__)


@login_required
def site_regenerate_hero_images(request, pk):
    """
    Replace all generated hero images for pages in this site and rebuild the static output.
    """
    site = get_object_or_404(Site, pk=pk)

    if request.method != "POST":
        return redirect(reverse("sites_builder:site_detail", args=[pk]))

    stats = regenerate_site_hero_images(site, rebuild=True)

    if stats["generated"]:
        messages.success(
            request,
            f"Regenerated {stats['generated']} page hero image(s) and "
            f"{stats['landing_images_generated']} landing card image(s), deleted "
            f"{stats['files_deleted']} stale file(s), and rebuilt the static site.",
        )
    else:
        messages.warning(
            request,
            f"No hero images were regenerated. Failed: {stats['failed']}.",
        )

    return redirect(reverse("sites_builder:site_detail", args=[pk]))

def _build_page_tree(pages):
    """
    Build a nested tree structure for display:

    Returns a list of nodes:
    [
      { "page": Page, "children": [...] },
      ...
    ]
    """
    by_id = {p.id: {"page": p, "children": []} for p in pages}
    roots = []

    for p in pages:
        node = by_id[p.id]
        if p.parent_id and p.parent_id in by_id:
            by_id[p.parent_id]["children"].append(node)
        else:
            roots.append(node)

    return roots


# ---------------- After Deploy Audit (Crawler) ------------------------------

class _LinkExtractor(HTMLParser):
    """
    Minimal HTML link extractor using stdlib (no bs4 dependency).
    Extracts:
      - <a href=...>
      - <img src=...>
      - <script src=...>
      - <link href=...>
    """
    def __init__(self):
        super().__init__()
        self.links = []  # list of tuples (link_type, url)

    def handle_starttag(self, tag, attrs):
        attr_map = dict(attrs or [])
        if tag == "a" and "href" in attr_map:
            self.links.append(("a", attr_map.get("href")))
        elif tag == "img" and "src" in attr_map:
            self.links.append(("img", attr_map.get("src")))
        elif tag == "script" and "src" in attr_map:
            self.links.append(("script", attr_map.get("src")))
        elif tag == "link" and "href" in attr_map:
            self.links.append(("link", attr_map.get("href")))


_SKIP_SCHEMES = {"mailto", "tel", "javascript", "data"}


def _normalize_start_domain(domain: str) -> str:
    """
    Ensure the site's domain is a full URL with scheme.
    Accepts:
      example.com
      https://example.com
      https://example.com/
    Returns a normalized base URL with scheme.
    """
    domain = (domain or "").strip()
    if not domain:
        return ""

    # If no scheme, assume https
    if "://" not in domain:
        domain = "https://" + domain

    # Remove trailing spaces etc.
    domain = domain.strip()
    return domain.rstrip("/")


def _should_enqueue_as_page(url: str) -> bool:
    """
    Decide if an internal URL looks like an HTML page worth crawling further.
    """
    parsed = urlparse(url)
    path = parsed.path or "/"

    # Skip obvious binaries
    if re.search(r"\.(png|jpg|jpeg|gif|webp|svg|ico|pdf|zip|gz|mp4|mp3|woff2?|ttf|eot)$", path, re.I):
        return False

    # Crawl directories and .html (or extensionless paths)
    if path.endswith("/") or path.endswith(".html") or "." not in path.split("/")[-1]:
        return True

    return False


def _check_url(session: requests.Session, url: str, timeout=(5, 15)) -> tuple[int | None, str]:
    """
    Returns (status_code, error_message).
    If success: (status_code, "")
    If exception: (None, "...")
    """
    try:
        # HEAD first (fast), then fallback to GET
        resp = session.head(url, allow_redirects=True, timeout=timeout)
        if resp.status_code in (405, 403) or resp.status_code >= 400:
            resp = session.get(url, allow_redirects=True, timeout=timeout)
        return resp.status_code, ""
    except requests.RequestException as e:
        return None, str(e)
    except socket.timeout as e:
        return None, f"timeout: {e}"
    except Exception as e:
        return None, str(e)


def _extract_links(html_text: str) -> list[tuple[str, str]]:
    parser = _LinkExtractor()
    try:
        parser.feed(html_text or "")
    except Exception:
        # If parsing fails, just return what we got so far
        pass
    return [(t, u) for (t, u) in parser.links if u]

def _polite_sleep(min_s=0.12, max_s=0.35):
    time.sleep(random.uniform(min_s, max_s))


def _backoff_sleep(attempt: int):
    # 0->1s, 1->2s, 2->4s, 3->8s (cap at ~10s) + jitter
    base = min(10.0, 2 ** attempt)
    time.sleep(base + random.uniform(0.0, 0.7))


def _check_url_cached(session, url: str, cache: dict, timeout=(10, 20)) -> tuple[int | None, str]:
    """
    Cached link checker. Uses HEAD then falls back to GET for troublesome servers.
    Returns (status_code, error_message)
    """
    if url in cache:
        return cache[url]

    try:
        resp = session.head(url, allow_redirects=True, timeout=timeout)
        # Some servers block/lie on HEAD; fallback to GET
        if resp.status_code in (405, 403) or resp.status_code >= 400:
            resp = session.get(url, allow_redirects=True, timeout=timeout)
        result = (resp.status_code, "")
    except requests.RequestException as e:
        result = (None, str(e))
    except Exception as e:
        result = (None, str(e))

    cache[url] = result
    return result


def _run_site_audit(site: Site, max_pages: int = 200, max_links: int = 5000) -> SiteAuditRun:
    """
    Crawl from site.domain and record broken links.
    """
    start_base = _normalize_start_domain(site.domain)
    run = SiteAuditRun.objects.create(
        site=site,
        status=SiteAuditRun.STATUS_RUNNING,
        start_url=start_base or "",
    )

    if not start_base:
        run.status = SiteAuditRun.STATUS_FAILED
        run.notes = "Site.domain is empty. Please set a domain (e.g. https://example.com) and retry."
        run.finished_at = datetime.now(dt_timezone.utc)
        run.save(update_fields=["status", "notes", "finished_at"])
        return run

    start_url = start_base.rstrip("/") + "/"
    start_netloc = urlparse(start_url).netloc.lower()

    visited_pages = set()
    queued_pages = [start_url]

    links_checked = 0
    pages_scanned = 0
    broken_count = 0

    # Cache all checked URLs so we don't hammer duplicates
    checked_links: dict[str, tuple[int | None, str]] = {}

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "FractalsSiteAudit/1.0 (+link-checker)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )

    # Track “host unhappiness” to back off a bit
    trouble_streak = 0

    try:
        while queued_pages and pages_scanned < max_pages and links_checked < max_links:
            _polite_sleep()

            page_url = queued_pages.pop(0)
            page_url = urldefrag(page_url)[0]

            if page_url in visited_pages:
                continue
            visited_pages.add(page_url)

            # ✅ Single GET for the page (avoid _check_url + GET double hit)
            try:
                resp = session.get(page_url, allow_redirects=True, timeout=(10, 25))
                status = resp.status_code
                html_text = resp.text if resp is not None else ""
                links_checked += 1
            except Exception as e:
                status = None
                html_text = ""
                links_checked += 1
                err = str(e)[:512]

                SiteAuditIssue.objects.create(
                    run=run,
                    source_url="",
                    target_url=page_url,
                    link_type="page",
                    is_internal=True,
                    status_code=None,
                    error=err,
                )
                broken_count += 1
                pages_scanned += 1

                trouble_streak += 1
                if trouble_streak >= 3:
                    _backoff_sleep(min(trouble_streak - 3, 3))
                continue

            # Reset trouble streak on success-ish
            if status and status < 400:
                trouble_streak = 0

            if status is None or status >= 400:
                SiteAuditIssue.objects.create(
                    run=run,
                    source_url="",
                    target_url=page_url,
                    link_type="page",
                    is_internal=True,
                    status_code=status,
                    error="",
                )
                broken_count += 1
                pages_scanned += 1

                # Back off a bit if the host starts returning “nope”
                if status in (429, 503):
                    trouble_streak += 1
                    _backoff_sleep(min(trouble_streak, 4))
                continue

            pages_scanned += 1

            for link_type, raw in _extract_links(html_text):
                if links_checked >= max_links:
                    break

                raw = (raw or "").strip()
                if not raw:
                    continue

                parsed_raw = urlparse(raw)
                if parsed_raw.scheme and parsed_raw.scheme.lower() in _SKIP_SCHEMES:
                    continue

                abs_url = urljoin(page_url, raw)
                abs_url = urldefrag(abs_url)[0]

                parsed = urlparse(abs_url)
                if not parsed.scheme.startswith("http"):
                    continue

                is_internal = (parsed.netloc or "").lower() == start_netloc

                _polite_sleep()  # a tiny pause per link check too

                status2, err2 = _check_url_cached(session, abs_url, checked_links, timeout=(10, 20))
                links_checked += 1

                # Back off if rate-limited or service unavailable
                if status2 in (429, 503) or (status2 is None and "timed out" in (err2 or "").lower()):
                    trouble_streak += 1
                    if trouble_streak >= 3:
                        _backoff_sleep(min(trouble_streak - 3, 4))
                else:
                    trouble_streak = 0

                if status2 is None or status2 >= 400:
                    SiteAuditIssue.objects.create(
                        run=run,
                        source_url=page_url,
                        target_url=abs_url,
                        link_type=link_type,
                        is_internal=is_internal,
                        status_code=status2,
                        error=err2[:512] if err2 else "",
                    )
                    broken_count += 1

                if is_internal and _should_enqueue_as_page(abs_url) and abs_url not in visited_pages:
                    queued_pages.append(abs_url)

        run.status = SiteAuditRun.STATUS_DONE
        run.pages_scanned = pages_scanned
        run.links_checked = links_checked
        run.broken_count = broken_count
        run.notes = f"Scanned up to max_pages={max_pages}, max_links={max_links}. Unique URLs checked: {len(checked_links)}."
        run.finished_at = datetime.now(dt_timezone.utc)
        run.save(update_fields=["status", "pages_scanned", "links_checked", "broken_count", "notes", "finished_at"])
        return run

    except Exception as e:
        run.status = SiteAuditRun.STATUS_FAILED
        run.notes = f"Audit crashed: {e}"
        run.pages_scanned = pages_scanned
        run.links_checked = links_checked
        run.broken_count = broken_count
        run.finished_at = datetime.now(dt_timezone.utc)
        run.save(update_fields=["status", "notes", "pages_scanned", "links_checked", "broken_count", "finished_at"])
        return run

# ---------------- Existing Views -------------------------------------------

@login_required
def site_dashboard(request):
    """
    List all sites with basic stats and quick links.
    """
    sites = Site.objects.all().prefetch_related("pages").order_by("name")

    site_infos = []
    for s in sites:
        pages = s.pages.all()
        site_infos.append(
            {
                "site": s,
                "page_count": pages.count(),
                "root_count": pages.filter(is_root=True).count(),
            }
        )

    context = {"site_infos": site_infos}
    return render(request, "sites_builder/ui/site_dashboard.html", context)


@login_required
def site_detail(request, pk):
    """
    Detail page for a single site: show pages, tree, and action buttons.
    """
    site = get_object_or_404(Site, pk=pk)
    pages = site.pages.all().order_by("depth", "title")
    targets = site.deployment_targets.all()

    page_tree = _build_page_tree(pages)

    preview_url = ""
    base = getattr(settings, "STATIC_SITE_PREVIEW_BASE_URL", "").strip()
    if base:
        preview_url = f"{base.rstrip('/')}/{site.slug}/index.html"

    latest_audit = site.audit_runs.order_by("-started_at").first()
    latest_issues = []
    if latest_audit:
        latest_issues = list(latest_audit.issues.order_by("-created_at")[:50])

    ga_summary = None
    if site.ga4_property_id:
        end = date.today()
        start = end - timedelta(days=7)

        # ✅ include property_id in the cache key (prevents stale “None” when you changed IDs)
        cache_key = f"ga4:{site.id}:{site.ga4_property_id}:summary:7d"

        # ✅ allow forcing a refresh: /builder/site/<pk>/?ga_refresh=1
        force = request.GET.get("ga_refresh") == "1"
        if force:
            cache.delete(cache_key)

        ga_summary = cache.get(cache_key)

        # ✅ treat falsy as a miss AND do not cache None/empty
        if not ga_summary:
            ga_summary = fetch_summary(site.ga4_property_id, start, end)

            if ga_summary and (ga_summary.active_users or ga_summary.sessions or ga_summary.page_views):
                cache.set(cache_key, ga_summary, 15 * 60)

    logger.debug("GA4 summary computed for site=%s: %r", site.id, ga_summary)
    articles = site.evergreen_articles.all()
    evergreen_stats = {
        "total": articles.count(),
        "drafts": articles.filter(status="draft").count(),
        "published": articles.filter(status="published").count(),
        "last_published": articles.filter(status="published").aggregate(Max("published_at"))["published_at__max"],
    }
    theme_css_choices = Site._meta.get_field("theme_css").choices
    context = {
        "site": site,
        "pages": pages,
        "page_tree": page_tree,
        "targets": targets,
        "preview_url": preview_url,
        "latest_audit": latest_audit,
        "latest_issues": latest_issues,
        "ga_summary": ga_summary,
        "evergreen_stats": evergreen_stats,
        "theme_css_choices": theme_css_choices,
    }
    return render(request, "sites_builder/ui/site_detail.html", context)


@login_required
def site_expand(request, pk):
    """
    Trigger GPT expansion for this site.
    """
    site = get_object_or_404(Site, pk=pk)

    if request.method != "POST":
        return redirect(reverse("sites_builder:site_detail", args=[pk]))

    max_new = int(request.POST.get("max_new_pages", "5") or 5)

    gen = SiteGenerator()
    if site.structure_locked:
        created = gen.fill_missing_content(site, limit=50)
    else:
        created = gen.expand_site(site, max_new_pages=max_new)

    messages.success(
        request,
        f"Expanded site '{site.slug}'. Pages created/updated: {created}",
    )
    return redirect(reverse("sites_builder:site_detail", args=[pk]))


@login_required
def site_build(request, pk):
    """
    Build static files for this site.
    """
    site = get_object_or_404(Site, pk=pk)

    if request.method != "POST":
        return redirect(reverse("sites_builder:site_detail", args=[pk]))

    builder = StaticBuilder()
    out_dir = builder.build_site(site)

    messages.success(
        request,
        f"Built static site for '{site.slug}' at: {out_dir}",
    )
    return redirect(reverse("sites_builder:site_detail", args=[pk]))


@login_required
def site_deploy(request, pk):
    """
    Deploy the site's built files via selected DeploymentTarget.
    """
    site = get_object_or_404(Site, pk=pk)

    if request.method != "POST":
        return redirect(reverse("sites_builder:site_detail", args=[pk]))

    target_id = request.POST.get("target_id")
    if not target_id:
        messages.error(request, "No deployment target selected.")
        return redirect(reverse("sites_builder:site_detail", args=[pk]))

    target = get_object_or_404(DeploymentTarget, pk=target_id, site=site)

    deployer = Deployer()
    try:
        deployer.deploy(target)
        messages.success(
            request,
            f"Deployed site '{site.slug}' using target '{target.name}' ({target.type}).",
        )
    except Exception as e:
        messages.error(request, f"Deployment failed: {e}")

    return redirect(reverse("sites_builder:site_detail", args=[pk]))


@login_required
def site_audit_run(request, pk):
    """
    Run the after-deploy audit: crawl from Site.domain and report broken links.
    """
    site = get_object_or_404(Site, pk=pk)

    if request.method != "POST":
        return redirect(reverse("sites_builder:site_detail", args=[pk]))

    # Optional controls (safe defaults)
    max_pages = int(request.POST.get("max_pages", "200") or 200)
    max_links = int(request.POST.get("max_links", "5000") or 5000)

    run = _run_site_audit(site, max_pages=max_pages, max_links=max_links)

    if run.status == SiteAuditRun.STATUS_DONE:
        if run.broken_count:
            messages.warning(
                request,
                f"Audit complete: {run.broken_count} broken link(s) found. "
                f"Pages scanned: {run.pages_scanned}, links checked: {run.links_checked}.",
            )
        else:
            messages.success(
                request,
                f"Audit complete: no broken links found. "
                f"Pages scanned: {run.pages_scanned}, links checked: {run.links_checked}.",
            )
    else:
        messages.error(request, f"Audit failed: {run.notes}")

    return redirect(reverse("sites_builder:site_detail", args=[pk]))

@login_required
def site_theme_update(request, pk):
    """
    Update logo URL, brand colors, and theme for a site.
    """
    site = get_object_or_404(Site, pk=pk)

    if request.method != "POST":
        return redirect(reverse("sites_builder:site_detail", args=[pk]))

    logo_url = request.POST.get("logo_url", "").strip()
    primary_color = request.POST.get("primary_color", "").strip()
    secondary_color = request.POST.get("secondary_color", "").strip()

    # ✅ THIS is the missing part
    theme_css = (request.POST.get("theme_css", "") or site.theme_css or "aurora").strip()

    site.logo_url = logo_url
    site.primary_color = primary_color
    site.secondary_color = secondary_color
    site.theme_css = theme_css

    site.save(update_fields=["logo_url", "primary_color", "secondary_color", "theme_css"])

    messages.success(request, "Theme & branding updated.")
    return redirect(reverse("sites_builder:site_detail", args=[pk]))



@login_required
def site_backfill_hero_images(request, pk):
    """
    Generate hero images for pages in this site that don't have one yet.
    """
    site = get_object_or_404(Site, pk=pk)

    if request.method != "POST":
        return redirect(reverse("sites_builder:site_detail", args=[pk]))

    base_dir = Path(settings.BASE_DIR) / "output" / "sites"
    image_gen = ImageGenerator(base_dir)

    pages = site.pages.filter(hero_image_url="")  # no hero image yet
    total = 0
    for page in pages:
        hero_context = f"Page title: {page.title}. Site description: {site.description}."
        try:
            url = image_gen.generate_page_hero(site.slug, page.slug, hero_context)
            page.hero_image_url = url
            page.save(update_fields=["hero_image_url"])
            total += 1
        except Exception as e:
            # Don't fail the whole run; just log a warning
            print(f"[WARN] Failed to generate hero image for page '{page.slug}': {e}")

    if total:
        messages.success(
            request,
            f"Generated hero images for {total} page(s) with missing images.",
        )
    else:
        messages.info(
            request,
            "No pages were missing hero images; nothing to do.",
        )

    return redirect(reverse("sites_builder:site_detail", args=[pk]))

@require_POST
@login_required
def page_regenerate(request, site_pk, page_pk):
    site = get_object_or_404(Site, pk=site_pk)
    page = get_object_or_404(Page, pk=page_pk, site=site)

    if getattr(page, "is_locked", False):
        messages.error(request, "This page is locked and cannot be regenerated.")
        return redirect(reverse("sites_builder:site_detail", args=[site.pk]))

    try:
        gen = SiteGenerator()
        gen.regenerate_page(page)
        messages.success(request, f"Regenerated page: {page.title}")
    except Exception as e:
        messages.error(request, f"Regeneration failed: {e}")

    return redirect(reverse("sites_builder:site_detail", args=[site.pk]))

def scrape_and_package_website(url):
    """
    Scrape the website at `url` and package its HTML and assets into a zip archive in memory.
    For simplicity, only downloads the main HTML and linked CSS/JS/images referenced in <link>, <script>, <img>.
    """
    session = requests.Session()
    response = session.get(url, timeout=(5, 30))
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    # Collect assets URLs
    assets = set()

    # CSS files
    for link in soup.find_all('link', href=True):
        href = link['href']
        if href.startswith('http') or href.startswith('/'):
            assets.add(requests.compat.urljoin(url, href))

    # JS files
    for script in soup.find_all('script', src=True):
        src = script['src']
        assets.add(requests.compat.urljoin(url, src))

    # Images
    for img in soup.find_all('img', src=True):
        src = img['src']
        assets.add(requests.compat.urljoin(url, src))

    # Create in-memory zip
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        # Add main HTML
        zip_file.writestr('index.html', response.text)

        # Download and add assets
        for asset_url in assets:
            try:
                asset_resp = session.get(asset_url, timeout=(5, 30))
                asset_resp.raise_for_status()
                # Use the path part of the URL as filename inside zip
                path = requests.compat.urlparse(asset_url).path.lstrip('/')
                if not path:
                    path = asset_url.replace('://', '_').replace('/', '_')
                zip_file.writestr(path, asset_resp.content)
            except Exception:
                # Skip assets that fail to download
                continue

    zip_buffer.seek(0)
    return zip_buffer

def website_download_view(request):
    if request.method == 'POST':
        form = WebsiteDownloadForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data['url']
            try:
                zip_buffer = scrape_and_package_website(url)
                response = HttpResponse(zip_buffer, content_type='application/zip')
                response['Content-Disposition'] = f'attachment; filename=website_{url.replace("://", "_").replace("/", "_")}.zip'
                return response
            except Exception as e:
                form.add_error(None, f"Failed to download website: {e}")
    else:
        form = WebsiteDownloadForm()

    return render(request, 'site_builder/website_download.html', {'form': form})

@require_POST
def plan_menu(request, site_id: int):
    site = get_object_or_404(Site, id=site_id)
    gen = SiteGenerator()
    try:
        gen.ensure_root_page(site)
        gen._ensure_site_ia(site)
        # optional: lock immediately (turbo mode)
        site.structure_locked = True
        site.save(update_fields=["structure_locked"])

        messages.success(request, "🚀 Menu planned (IA created), skeleton pages created, structure locked.")
    except Exception as e:
        messages.error(request, f"Plan menu failed: {e}")

    return redirect(request.META.get("HTTP_REFERER", "/"))

@require_POST
def site_fill_content(request, pk: int):
    site = get_object_or_404(Site, pk=pk)

    gen = SiteGenerator()
    try:
        updated = gen.fill_missing_content(site, limit=50)
        if updated == 0:
            messages.info(request, "No blank pages found. Nothing to fill.")
        else:
            messages.success(request, f"Filled content for {updated} page(s).")
    except Exception as e:
        messages.error(request, f"Fill Missing Content failed: {e}")

    return redirect("sites_builder:site_detail", pk=site.pk)

@login_required
def article_list(request, pk):
    site = get_object_or_404(Site, pk=pk)
    status = request.GET.get("status", "").strip()
    cornerstones_only = request.GET.get("cornerstones_only") == "1"

    articles = site.evergreen_articles.all().order_by("-updated_at")
    if status:
        articles = articles.filter(status=status)
    if cornerstones_only:
        articles = articles.filter(is_cornerstone=True)

    cs_map = defaultdict(list)
    for link in ArticleCornerstoneLink.objects.filter(site=site).select_related("cornerstone"):
        cs_map[link.supporting_id].append(link.cornerstone.title)

    return render(request, "sites_builder/ui/article_list.html", {
        "site": site,
        "articles": articles,
        "status": status,
        "cornerstones_only": cornerstones_only,
        "cornerstone_title_map": dict(cs_map),
        "clusters_url_name": "sites_builder:article_clusters",  # if you have this route
    })


@login_required
def article_create(request, pk):
    site = get_object_or_404(Site, pk=pk)
    cornerstones = site.evergreen_articles.filter(is_cornerstone=True).order_by("title")

    if request.method == "POST":
        a = EvergreenArticle(
            site=site,
            title=request.POST.get("title", "").strip(),
            slug=request.POST.get("slug", "").strip(),
            excerpt=request.POST.get("excerpt", "").strip(),
            body_md=request.POST.get("body_md", "").strip(),
            meta_title=request.POST.get("meta_title", "").strip(),
            meta_description=request.POST.get("meta_description", "").strip(),
            canonical_url=request.POST.get("canonical_url", "").strip(),
            hero_image_url=request.POST.get("hero_image_url", "").strip(),
            author_name=request.POST.get("author_name", "").strip(),
            author_url=request.POST.get("author_url", "").strip(),
            legacy_slugs=[
                slugify(value)
                for value in re.split(
                    r"[,\n]", request.POST.get("legacy_slugs", "")
                )
                if slugify(value)
            ],
            content_updated_at=timezone.now(),
            status=request.POST.get("status", EvergreenArticle.STATUS_DRAFT),
        )
        if not a.title:
            messages.error(request, "Title is required.")
            return redirect("sites_builder:article_create", pk=site.pk)

        a.save()
        selected_cornerstones = request.POST.getlist("cornerstone_ids")
        # clear any existing (new article will have none, but safe)
        ArticleCornerstoneLink.objects.filter(site=site, supporting=a).delete()

        for cs_id in selected_cornerstones:
            cs = site.evergreen_articles.filter(id=cs_id, is_cornerstone=True).first()
            if cs:
                ArticleCornerstoneLink.objects.create(site=site, cornerstone=cs, supporting=a)

        messages.success(request, "Article created.")
        return redirect("sites_builder:article_edit", pk=site.pk, article_id=a.pk)

    return render(request, "sites_builder/ui/article_form.html", {
        "site": site,
        "article": None,
        "cornerstones": cornerstones,
        "selected_cornerstone_ids": set(),
    })


@login_required
def article_edit(request, pk, article_id):
    site = get_object_or_404(Site, pk=pk)
    a = get_object_or_404(EvergreenArticle, pk=article_id, site=site)

    if request.method == "POST":
        previous_editorial_content = (
            a.title,
            a.excerpt,
            a.body_md,
            a.meta_title,
            a.meta_description,
            a.hero_image_url,
        )
        a.title = request.POST.get("title", "").strip()
        a.slug = request.POST.get("slug", "").strip() or a.slug
        a.excerpt = request.POST.get("excerpt", "").strip()
        a.body_md = request.POST.get("body_md", "").strip()
        a.meta_title = request.POST.get("meta_title", "").strip()
        a.meta_description = request.POST.get("meta_description", "").strip()
        a.canonical_url = request.POST.get("canonical_url", "").strip()
        a.hero_image_url = request.POST.get("hero_image_url", "").strip()
        a.author_name = request.POST.get("author_name", "").strip()
        a.author_url = request.POST.get("author_url", "").strip()
        a.legacy_slugs = [
            slugify(value)
            for value in re.split(r"[,\n]", request.POST.get("legacy_slugs", ""))
            if slugify(value)
        ]
        a.is_cornerstone = bool(request.POST.get("is_cornerstone"))

        current_editorial_content = (
            a.title,
            a.excerpt,
            a.body_md,
            a.meta_title,
            a.meta_description,
            a.hero_image_url,
        )
        if current_editorial_content != previous_editorial_content:
            a.content_updated_at = timezone.now()

        status = request.POST.get("status", a.status)
        if status in dict(EvergreenArticle.STATUS_CHOICES):
            a.status = status

        a.save()
        selected_cornerstones = set(request.POST.getlist("cornerstone_ids"))

        # 1) Remove links that were unselected
        ArticleCornerstoneLink.objects.filter(
            site=site,
            supporting=a
        ).exclude(
            cornerstone_id__in=selected_cornerstones
        ).delete()

        # 2) Add links that are newly selected
        existing_ids = set(
            ArticleCornerstoneLink.objects.filter(
                site=site,
                supporting=a
            ).values_list("cornerstone_id", flat=True)
        )

        to_add = selected_cornerstones - existing_ids

        for cs_id in to_add:
            cs = site.evergreen_articles.filter(
                id=cs_id,
                is_cornerstone=True
            ).first()

            if cs:
                ArticleCornerstoneLink.objects.get_or_create(
                    site=site,
                    cornerstone=cs,
                    supporting=a,
                    defaults={
                        "is_primary": False,
                        "anchor_text": "",
                    },
                )

        messages.success(request, "Saved.")
        return redirect("sites_builder:article_edit", pk=site.pk, article_id=a.pk)

    cornerstones = site.evergreen_articles.filter(is_cornerstone=True).order_by("title")

    selected_cornerstone_ids = set(
        ArticleCornerstoneLink.objects.filter(site=site, supporting=a)
        .values_list("cornerstone_id", flat=True)
    )

    return render(request, "sites_builder/ui/article_form.html", {
        "site": site,
        "article": a,
        "cornerstones": cornerstones,
        "selected_cornerstone_ids": selected_cornerstone_ids,
    })

@login_required
def article_publish(request, pk, article_id):
    site = get_object_or_404(Site, pk=pk)
    a = get_object_or_404(EvergreenArticle, pk=article_id, site=site)
    if request.method == "POST":
        a.status = EvergreenArticle.STATUS_PUBLISHED
        a.published_at = a.published_at or timezone.now()
        a.save()
        messages.success(request, "Published.")
    return redirect("sites_builder:article_edit", pk=site.pk, article_id=a.pk)


@login_required
def article_archive(request, pk, article_id):
    site = get_object_or_404(Site, pk=pk)
    a = get_object_or_404(EvergreenArticle, pk=article_id, site=site)
    if request.method == "POST":
        a.status = EvergreenArticle.STATUS_ARCHIVED
        a.save()
        messages.success(request, "Archived.")
    return redirect("sites_builder:article_list", pk=site.pk)

def _site_content_digest(site: Site, max_chars: int = 6000) -> str:
    """
    Builds a compact digest from existing site pages to ground title suggestions.
    Keeps it simple: titles + small snippets of body.
    """
    parts = []
    pages = site.pages.all().order_by("is_root", "depth", "nav_order", "title")[:30]
    for p in pages:
        title = (p.title or p.slug or "").strip()
        body = (p.body_html or "").strip()
        if body:
            body = " ".join(body.split())
            body = body[:280]
        parts.append(f"- {title}: {body}")
    digest = "\n".join(parts)
    return digest[:max_chars]


@login_required
def article_ai_studio(request, pk):
    site = get_object_or_404(Site, pk=pk)
    tone = request.GET.get("tone", "friendly")
    audience = request.GET.get("audience", "general")
    keyword = request.GET.get("keyword", "").strip()
    length = request.GET.get("length", "medium")
    digest = _site_content_digest(site)
    kw_line = f"Primary keyword to include when relevant: {keyword}" if keyword else "No required keyword."
    prompt = f"""
    You are an SEO strategist.

    Tone: {tone}
    Audience: {audience}
    {kw_line}

    Based on the website digest below, propose 12 evergreen article titles.

    Output STRICT JSON only: {{ "titles": ["..."] }}

    Website digest:
    {digest}
    """.strip()
    titles = []
    try:
        data = chat_with_gpt_json(prompt, temperature=0.2, max_output_tokens=800)
        titles = (data.get("titles") or [])[:12]
    except Exception as e:
        messages.error(request, f"AI suggestions failed: {e}")

    return render(request, "sites_builder/ui/article_ai_studio.html", {
        "site": site,
        "titles": titles,
    })


@login_required
@require_http_methods(["POST"])
def article_ai_generate(request, pk):
    site = get_object_or_404(Site, pk=pk)
    title = (request.POST.get("title") or "").strip()
    tone = request.POST.get("tone", "friendly")
    audience = request.POST.get("audience", "general")
    keyword = (request.POST.get("keyword") or "").strip()
    length = request.POST.get("length", "medium")

    length_map = {"short": "600-900", "medium": "900-1400", "long": "1400-2200"}
    target_words = length_map.get(length, "900-1400")
    kw_line = f"Primary keyword: {keyword} (use naturally in H1/H2 and a few times)" if keyword else "No required keyword."
    if not title:
        messages.error(request, "Missing title.")
        return redirect("sites_builder:article_ai_studio", pk=site.pk)

    # Generate full draft article
    digest = _site_content_digest(site)
    prompt = f"""
    You are a helpful content writer and SEO editor.

    Tone: {tone}
    Audience: {audience}
    Target length (words): {target_words}
    {kw_line}

    Return STRICT JSON only with keys:
    - title
    - slug
    - excerpt
    - meta_title (<= 60 chars)
    - meta_description (<= 155 chars)
    - body_md (markdown with headings, bullets, short conclusion)
    - suggested_internal_links (array of strings: page titles or slugs to link to)

    Website digest:
    {digest}

    Requested title:
    {title}
    """.strip()

    try:
        data = chat_with_gpt_json(prompt, temperature=0.2)

        a = EvergreenArticle(
            site=site,
            title=data.get("title") or title,
            slug=data.get("slug") or slugify(title),
            excerpt=(data.get("excerpt") or "").strip(),
            meta_title=(data.get("meta_title") or "").strip(),
            meta_description=(data.get("meta_description") or "").strip(),
            body_md=(data.get("body_md") or "").strip(),
            status=EvergreenArticle.STATUS_DRAFT,
        )
        a.save()

        messages.success(request, "Draft generated with AI.")
        return redirect("sites_builder:article_edit", pk=site.pk, article_id=a.pk)

    except Exception as e:
        messages.error(request, f"AI generation failed: {e}")
        return redirect("sites_builder:article_ai_studio", pk=site.pk)

@login_required
@require_http_methods(["POST"])
def article_ai_generate_cluster(request, pk):
    site = get_object_or_404(Site, pk=pk)
    topic = (request.POST.get("topic") or "").strip()
    tone = request.POST.get("tone", "friendly")
    audience = request.POST.get("audience", "general")
    keyword = (request.POST.get("keyword") or "").strip()
    length = request.POST.get("length", "medium")
    extra_cornerstone_ids = request.POST.getlist("extra_cornerstone_ids")  # optional

    if not topic:
        messages.error(request, "Topic is required.")
        return redirect("sites_builder:article_ai_studio", pk=site.pk)

    digest = _site_content_digest(site)
    # use your robust chat_with_gpt_json helper
    data = chat_with_gpt_json(f"""
Return STRICT JSON only:
{{
  "cornerstone": {{ "title": "...", "slug": "...", "excerpt":"...", "meta_title":"...", "meta_description":"...", "body_md":"..." }},
  "supporting": [
    {{ "title":"...", "slug":"...", "excerpt":"...", "meta_title":"...", "meta_description":"...", "body_md":"...", "anchor_text":"..." }}
  ]
}}

Tone: {tone}
Audience: {audience}
Primary keyword: {keyword if keyword else "none"}
Target length: {length}
Topic: {topic}

Website digest:
{digest}
""", temperature=0.25, max_output_tokens=2600)

    cs = data["cornerstone"]
    cornerstone = EvergreenArticle.objects.create(
        site=site,
        title=cs["title"],
        slug=cs.get("slug") or slugify(cs["title"]),
        excerpt=cs.get("excerpt", ""),
        meta_title=cs.get("meta_title", ""),
        meta_description=cs.get("meta_description", ""),
        body_md=cs.get("body_md", ""),
        status=EvergreenArticle.STATUS_DRAFT,
        is_cornerstone=True,
    )

    # create supporting + link to cornerstone (and optional extra cornerstones)
    supporting_items = data.get("supporting") or []
    created_supporting = []
    for s in supporting_items[:4]:
        art = EvergreenArticle.objects.create(
            site=site,
            title=s["title"],
            slug=s.get("slug") or slugify(s["title"]),
            excerpt=s.get("excerpt", ""),
            meta_title=s.get("meta_title", ""),
            meta_description=s.get("meta_description", ""),
            body_md=s.get("body_md", ""),
            status=EvergreenArticle.STATUS_DRAFT,
            is_cornerstone=False,
        )
        created_supporting.append(art)

        ArticleCornerstoneLink.objects.create(
            site=site,
            cornerstone=cornerstone,
            supporting=art,
            is_primary=True,
            anchor_text=(s.get("anchor_text") or "").strip(),
        )

        # also attach to other existing cornerstones (optional)
        for extra_id in extra_cornerstone_ids:
            extra = site.evergreen_articles.filter(id=extra_id, is_cornerstone=True).first()
            if extra:
                ArticleCornerstoneLink.objects.get_or_create(
                    site=site,
                    cornerstone=extra,
                    supporting=art,
                    defaults={"is_primary": False, "anchor_text": ""},
                )

    messages.success(request, "Cornerstone + supporting cluster drafts generated.")
    return redirect("sites_builder:article_edit", pk=site.pk, article_id=cornerstone.pk)

@login_required
def article_clusters(request, pk):
    site = get_object_or_404(Site, pk=pk)

    cornerstones = (
        site.evergreen_articles
        .filter(is_cornerstone=True)
        .order_by("-updated_at", "title")
    )

    rows = []
    for cs in cornerstones:
        supporting_qs = (
            ArticleCornerstoneLink.objects
            .filter(site=site, cornerstone=cs)
            .select_related("supporting")
        )
        rows.append({
            "cornerstone": cs,
            "supporting_total": supporting_qs.count(),
            "supporting_published": supporting_qs.filter(supporting__status="published").count(),
            "supporting_drafts": supporting_qs.filter(supporting__status="draft").count(),
        })

    return render(request, "sites_builder/ui/article_clusters.html", {
        "site": site,
        "rows": rows,
    })


@login_required
@require_http_methods(["POST"])
def cluster_publish_all(request, pk, cornerstone_id):
    site = get_object_or_404(Site, pk=pk)
    cs = get_object_or_404(EvergreenArticle, pk=cornerstone_id, site=site)

    # publish cornerstone + all linked supportings
    link_qs = ArticleCornerstoneLink.objects.filter(site=site, cornerstone=cs).select_related("supporting")

    # publish cornerstone first
    if cs.status != EvergreenArticle.STATUS_PUBLISHED:
        cs.status = EvergreenArticle.STATUS_PUBLISHED
        cs.save()

    count = 0
    for link in link_qs:
        a = link.supporting
        if a.status != EvergreenArticle.STATUS_PUBLISHED:
            a.status = EvergreenArticle.STATUS_PUBLISHED
            a.save()
            count += 1

    messages.success(request, f"Published cornerstone and {count} supporting article(s).")
    return redirect("sites_builder:article_clusters", pk=site.pk)


@login_required
@require_http_methods(["POST"])
def cluster_generate_supporting(request, pk, cornerstone_id):
    site = get_object_or_404(Site, pk=pk)
    cs = get_object_or_404(EvergreenArticle, pk=cornerstone_id, site=site)

    tone = request.POST.get("tone", "friendly")
    audience = request.POST.get("audience", "general")
    keyword = (request.POST.get("keyword") or "").strip()
    length = request.POST.get("length", "medium")

    digest = _site_content_digest(site)

    kw_line = f"Primary keyword: {keyword} (use naturally)" if keyword else "No required keyword."

    # 1) Ask for 4 good supporting ideas first (titles + angle only)
    ideas_prompt = f"""
Return STRICT JSON only:
{{
  "supporting": [
    {{
      "title":"...",
      "slug":"...",
      "angle":"One sentence describing what makes this supporting article unique and narrower than the cornerstone.",
      "anchor_text":"..."
    }}
  ]
}}

Generate exactly 4 supporting evergreen article ideas for THIS cornerstone:
Cornerstone title: {cs.title}
Cornerstone excerpt: {cs.excerpt}

Tone: {tone}
Audience: {audience}
{kw_line}

Rules:
- Each supporting must be narrower than the cornerstone.
- No fluff, no invented metrics.
- Make titles distinct from each other.

Website digest:
{digest}
""".strip()

    ideas = chat_with_gpt_json(ideas_prompt, temperature=0.25, max_output_tokens=1200)
    idea_items = (ideas.get("supporting") or [])[:4]

    if not idea_items:
        messages.error(request, "AI did not return supporting article ideas.")
        return redirect("sites_builder:article_clusters", pk=site.pk)

    created = 0
    with transaction.atomic():
        for idea in idea_items:
            title = (idea.get("title") or "").strip()
            if not title:
                continue

            raw_slug = (idea.get("slug") or slugify(title))[:255]
            angle = (idea.get("angle") or "").strip()
            anchor_text = (idea.get("anchor_text") or "").strip()

            # 2) Now generate ONE full article at a time (so it can be long)
            article_prompt = f"""
Return STRICT JSON only:
{{
  "title":"{title}",
  "slug":"{raw_slug}",
  "excerpt":"...",
  "meta_title":"...",
  "meta_description":"...",
  "body_md":"..."
}}

Write ONE supporting evergreen article (900–1200 words) that supports this cornerstone:
Cornerstone title: {cs.title}
Cornerstone excerpt: {cs.excerpt}

This supporting article title: {title}
Angle: {angle}

Tone: {tone}
Audience: {audience}
{kw_line}

Required structure (use markdown headings exactly):
## Why it matters
## Key considerations
- include 4–7 bullets
## Practical examples
- include at least 2 realistic examples
## Common pitfalls
## FAQ
- include 3 Q&As
## How this connects back to the cornerstone
- include a short paragraph and explicitly reference the cornerstone topic

Rules:
- Minimum 900 words, maximum 1200 words.
- No fake statistics, no namedropping real companies as “clients”.
- Keep it specific and actionable.

Website digest:
{digest}
""".strip()

            s = chat_with_gpt_json(article_prompt, temperature=0.2, max_output_tokens=2600)

            final_title = (s.get("title") or title).strip()
            final_slug = (s.get("slug") or raw_slug).strip()[:255]

            a = EvergreenArticle.objects.create(
                site=site,
                title=final_title,
                slug=final_slug,
                excerpt=(s.get("excerpt") or "").strip(),
                meta_title=(s.get("meta_title") or "").strip(),
                meta_description=(s.get("meta_description") or "").strip(),
                body_md=(s.get("body_md") or "").strip(),
                status=EvergreenArticle.STATUS_DRAFT,
                is_cornerstone=False,
            )

            ArticleCornerstoneLink.objects.get_or_create(
                site=site,
                cornerstone=cs,
                supporting=a,
                defaults={
                    "is_primary": True,
                    "anchor_text": anchor_text or final_title,
                }
            )
            created += 1

    messages.success(request, f"Generated {created} supporting draft article(s).")
    return redirect("sites_builder:article_clusters", pk=site.pk)


@login_required
def site_convert_to_landing(request, pk):
    """One-click: turn the home page into a generated marketing landing page."""
    site = get_object_or_404(Site, pk=pk)
    if request.method != "POST":
        return redirect(reverse("sites_builder:site_detail", args=[pk]))
    try:
        from .services.generator import SiteGenerator
        root = SiteGenerator().convert_home_to_landing(site)
        StaticBuilder().build_site(site)
        messages.success(
            request,
            f"Home converted to a landing page ({len(root.landing_sections or [])} sections) and rebuilt.",
        )
    except Exception as e:  # noqa: BLE001 - surface generation errors to the user
        messages.error(request, f"Convert to landing failed: {e}")
    return redirect(reverse("sites_builder:site_detail", args=[pk]))
