"""SEO file writers (robots.txt, sitemap.xml) for built sites.

Shared by SiteGenerator (generation time) and StaticBuilder (build time) so a
plain rebuild also refreshes these files. Sitemap covers pages AND published
Evergreen articles (insights/<slug>.html).
"""
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from xml.etree.ElementTree import Element, SubElement, tostring

from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


def output_site_dir(site) -> Path:
    return Path(settings.BASE_DIR) / "output" / "sites" / site.slug


def base_url(site) -> str:
    raw = (site.domain or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "https://" + raw
    p = urlparse(raw)
    netloc = p.netloc.strip().lower()
    scheme = (p.scheme or "https").lower()
    return urlunparse((scheme, netloc, "", "", "", "")).rstrip("/")


def page_url(site, page) -> str:
    base = base_url(site)
    if not base:
        return ""
    if getattr(page, "is_root", False):
        return base + "/"
    slug = (page.slug or "").strip().strip("/")
    if not slug:
        return base + "/"
    return f"{base}/{slug}.html"


def write_robots_txt(site) -> None:
    out_dir = output_site_dir(site)
    out_dir.mkdir(parents=True, exist_ok=True)

    base = base_url(site)
    sitemap_url = f"{base}/sitemap.xml" if base else "sitemap.xml"

    robots = "\n".join(
        [
            "User-agent: *",
            "Disallow:",
            "",
            f"Sitemap: {sitemap_url}",
            "",
        ]
    )
    (out_dir / "robots.txt").write_text(robots, encoding="utf-8")


def write_sitemap_xml(site) -> None:
    from ..models import EvergreenArticle

    out_dir = output_site_dir(site)
    out_dir.mkdir(parents=True, exist_ok=True)

    base = base_url(site)

    urlset = Element("urlset")
    urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
    now_iso = timezone.now().date().isoformat()

    def add(loc: str, lastmod: str, changefreq: str, priority: str) -> None:
        u = SubElement(urlset, "url")
        SubElement(u, "loc").text = loc
        SubElement(u, "lastmod").text = lastmod
        SubElement(u, "changefreq").text = changefreq
        SubElement(u, "priority").text = priority

    for p in site.pages.all().order_by("is_root", "depth", "id"):
        loc = page_url(site, p)
        if not loc:
            continue
        lg = getattr(p, "last_generated_at", None)
        lastmod = lg.date().isoformat() if lg else now_iso
        cf = "weekly" if getattr(p, "is_root", False) else "monthly"
        depth = int(getattr(p, "depth", 0) or 0)
        if getattr(p, "is_root", False):
            pr = "1.0"
        else:
            pr = f"{max(0.3, 0.8 - (depth * 0.1)):.1f}"
        add(loc, lastmod, cf, pr)

    if base:
        articles = EvergreenArticle.objects.filter(
            site=site, status=EvergreenArticle.STATUS_PUBLISHED
        ).order_by("-published_at", "-updated_at")
        for a in articles:
            slug = (a.slug or slugify(a.title))[:255]
            stamp = a.content_updated_at or a.updated_at or a.published_at
            add(
                f"{base}/insights/{slug}.html",
                stamp.date().isoformat() if stamp else now_iso,
                "monthly",
                "0.6",
            )

    xml_bytes = tostring(urlset, encoding="utf-8", method="xml")
    (out_dir / "sitemap.xml").write_bytes(
        b'<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
    )


def write_seo_files(site) -> None:
    try:
        write_robots_txt(site)
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] Failed to write robots.txt for site '{site.slug}': {e}")
    try:
        write_sitemap_xml(site)
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] Failed to write sitemap.xml for site '{site.slug}': {e}")
