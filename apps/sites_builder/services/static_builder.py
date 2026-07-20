from pathlib import Path
from typing import Optional, Dict, Any, List
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.text import slugify
from datetime import datetime
from shutil import copyfile
from urllib.parse import urlparse, unquote
import copy
import json
import os
import re

try:
    import requests
except Exception:
    requests = None

from ..models import Site, ArticleCornerstoneLink, EvergreenArticle
from .seo_files import write_seo_files
from .image_optimizer import optimize_images_dir
from .content_styler import cardify_subsections

try:
    import markdown as md
except Exception:
    md = None

# Matches src/href pointing at an ABSOLUTE http(s) image URL.
_ABS_IMG_RE = re.compile(
    r'(src|href)\s*=\s*"(https?://[^"]+\.(?:png|jpe?g|webp|svg|gif))"',
    re.IGNORECASE,
)

THEME_CSS_MAP = {
    "neon_glass": "neon_glass.css",
    "minimal": "minimal.css",
    "startup": "startup.css",
    "aurora": "aurora.css",
    "verdant": "verdant.css",
    "editorial": "editorial.css",
    "mindsgate": "mindsgate.css",
}


class StaticBuilder:
    """
    Drop-in static site builder that also outputs Evergreen Articles and
    writes sitelinks.json (pages + articles).
    """

    def __init__(self, base_output_dir: Optional[Path] = None):
        if base_output_dir is None:
            base_output_dir = Path(settings.BASE_DIR) / "output" / "sites"
        self.base_output_dir = base_output_dir

    def _normalize_landing_href(
        self, site: Site, href: str, known_slugs: set[str], fallback_text: str = ""
    ) -> str:
        """
        Rewrite LLM-supplied landing-section links to files that exist in this static site.
        """
        if not href:
            return href

        value = str(href).strip()
        parsed = urlparse(value)
        if parsed.scheme in ("mailto", "tel", "javascript", "data"):
            return value
        if parsed.scheme in ("http", "https") and parsed.netloc:
            site_domain = (site.domain or "").strip().lower()
            site_domain = urlparse(site_domain).netloc if "://" in site_domain else site_domain
            if parsed.netloc.lower() != site_domain:
                return value
            value = parsed.path or "/"

        def resolve_slug(raw: str) -> str:
            slug = slugify((raw or "").strip().strip("/#"))
            if not slug or slug in ("home", "index", "root"):
                return "index.html"
            if slug in known_slugs:
                return f"{slug}.html"

            for known in sorted(known_slugs):
                if known.startswith(f"{slug}-") or slug in known.split("-"):
                    return f"{known}.html"

            return "#"

        def resolve_with_fallback(raw: str) -> str:
            resolved = resolve_slug(raw)
            if resolved != "#" or not fallback_text:
                return resolved
            return resolve_slug(fallback_text)

        if value.lower().startswith("internal://"):
            return resolve_with_fallback(value.split("://", 1)[1])

        if value.startswith("#"):
            return resolve_with_fallback(value[1:])

        path = value.split("?", 1)[0].split("#", 1)[0]
        if path in ("", "/"):
            return "index.html"
        if path.endswith(".html"):
            stem = Path(path).stem
            if stem in known_slugs or stem == "index":
                return path
            return resolve_with_fallback(stem)
        if "/" not in path and "." not in path:
            return resolve_with_fallback(path)

        return value

    def _normalize_landing_section_links(self, site: Site, sections):
        """
        Return a render-only copy of landing sections with CTA/card links fixed.
        """
        normalized = copy.deepcopy(sections or [])
        known_slugs = set(site.pages.exclude(is_root=True).values_list("slug", flat=True))

        for block in normalized:
            if not isinstance(block, dict):
                continue
            for key in ("primary_cta", "secondary_cta", "button"):
                cta = block.get(key)
                if isinstance(cta, dict) and cta.get("href"):
                    cta["href"] = self._normalize_landing_href(
                        site, cta["href"], known_slugs, cta.get("label", "")
                    )

            items = block.get("items")
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and item.get("href"):
                        item["href"] = self._normalize_landing_href(
                            site, item["href"], known_slugs, item.get("title", "")
                        )

        return normalized

    def _relativize_root_internal_links(self, site: Site, html: str, prefix: str = "") -> str:
        """
        Make root-relative links to generated pages portable for local folder previews.
        """
        if not html:
            return html

        known_files = {"index.html"}
        known_files.update(
            f"{slug}.html"
            for slug in site.pages.exclude(is_root=True).values_list("slug", flat=True)
            if slug
        )

        def repl(match):
            attr = match.group(1)
            quote = match.group(2)
            path = match.group(3)
            tail = match.group(4) or ""
            filename = path.lstrip("/")
            if filename in known_files:
                return f"{attr}={quote}{prefix}{filename}{tail}{quote}"
            return match.group(0)

        return re.sub(
            r'\b(href|src)=([\'"])/(?!/)([^\'"#?]+\.html)([#?][^\'"]*)?\2',
            repl,
            html,
            flags=re.IGNORECASE,
        )

    def _validate_links(self, site_dir: Path) -> Dict[str, Any]:
        """
        Offline link checker (no network calls).

        Checks:
        - href/src that look like internal relative links
        - ensures referenced .html (or assets) exist in site_dir
        - ignores: http(s), mailto, tel, javascript, data, #anchors
        """
        # ✅ include subfolders now (insights/*.html etc.)
        html_files = sorted(site_dir.glob("**/*.html"))
        issues: List[Dict[str, str]] = []

        link_re = re.compile(r"""(?:href|src)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)

        def is_external(u: str) -> bool:
            u = (u or "").strip().lower()
            return u.startswith(("http://", "https://", "www."))

        def is_ignored(u: str) -> bool:
            u = (u or "").strip().lower()
            return (
                u == ""
                or u.startswith("#")
                or u.startswith(("mailto:", "tel:", "javascript:", "data:"))
            )

        def resolve(u: str, from_dir: Path) -> Optional[Path]:
            # strip query/hash
            u2 = (u or "").strip()
            u2 = u2.split("#", 1)[0]
            u2 = u2.split("?", 1)[0]

            if u2 == "/":
                return site_dir / "index.html"

            # root-relative -> site root; otherwise relative to the SOURCE file's
            # folder (so ../foo.html from insights/*.html resolves correctly)
            if u2.startswith("/"):
                base = site_dir
                u2 = u2.lstrip("/")
            else:
                base = from_dir

            if not u2:
                return site_dir / "index.html"

            # If it ends with / treat as directory index.html
            if u2.endswith("/"):
                candidate = base / u2 / "index.html"
            else:
                candidate = base / u2

            # normalize ../ segments without touching the filesystem
            return Path(os.path.normpath(candidate))

        for f in html_files:
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for m in link_re.finditer(text):
                link = m.group(1).strip()
                if is_ignored(link) or is_external(link):
                    continue

                # allow protocol-relative //example.com as external-ish
                if link.startswith("//"):
                    continue

                target = resolve(link, f.parent)
                if target is None:
                    continue

                if not target.exists():
                    try:
                        resolved_rel = str(target.relative_to(site_dir))
                    except ValueError:
                        resolved_rel = str(target)  # escaped site_dir (genuinely broken)
                    issues.append({
                        "file": str(f.relative_to(site_dir)),
                        "link": link,
                        "resolved": resolved_rel,
                        "reason": "target_not_found",
                    })

        return {
            "ok": len(issues) == 0,
            "checked_files": len(html_files),
            "issues": issues,
        }

    def _render_article_html(self, site: Site, article: EvergreenArticle, build_id: str) -> str:
        """
        Render a standalone static HTML page for an article.
        Includes automatic Cornerstone/Supporting linking sections using ArticleCornerstoneLink.
        """
        title = (article.meta_title or article.title or "").strip()
        meta_desc = (article.meta_description or article.excerpt or "").strip()

        body = (article.body_md or "").strip()
        if md is not None and body:
            try:
                body_html = md.markdown(body, extensions=["extra", "tables", "toc"])
            except Exception:
                body_html = body
        else:
            body_html = body

        # ----------------------------
        # Cluster linking via join table
        # ----------------------------
        # Supporting -> cornerstones (many)
        cornerstone_links = (
            ArticleCornerstoneLink.objects
            .filter(site=site, supporting=article, cornerstone__status=EvergreenArticle.STATUS_PUBLISHED)
            .select_related("cornerstone")
            .order_by("-is_primary", "cornerstone__title")
        )

        # Cornerstone -> supporting (many)
        supporting_links = []
        if getattr(article, "is_cornerstone", False):
            supporting_links = (
                ArticleCornerstoneLink.objects
                .filter(site=site, cornerstone=article, supporting__status=EvergreenArticle.STATUS_PUBLISHED)
                .select_related("supporting")
                .order_by("-is_primary", "-supporting__published_at", "supporting__title")
            )

        # We are inside /insights/<slug>.html so sibling links are just "<other>.html"
        def sib_url(slug: str) -> str:
            return f"{slug}.html"

        cornerstone_box = ""
        if cornerstone_links:
            items = []
            for link in cornerstone_links:
                cs = link.cornerstone
                label = (cs.title or "").strip() or "Cornerstone"
                desc = (link.anchor_text or "").strip()

                if desc:
                    items.append(
                        f'<li><a href="{sib_url(cs.slug)}">{label}</a>'
                        f'<div class="text-soft small" style="margin-top:4px;">{desc}</div></li>'
                    )
                else:
                    items.append(f'<li><a href="{sib_url(cs.slug)}">{label}</a></li>')
            cornerstone_box = f"""
              <div class="neon-glass-card p-3" style="margin-bottom:14px;">
                <div class="text-soft small" style="margin-bottom:6px;"><b>Part of:</b></div>
                <ul style="margin:0; padding-left:18px;">{''.join(items)}</ul>
              </div>
            """

        supporting_section = ""
        if supporting_links:
            items = []
            for link in supporting_links:
                sup = link.supporting
                anchor = (link.anchor_text or sup.title).strip()
                items.append(f'<li><a href="{sib_url(sup.slug)}">{anchor}</a></li>')
            supporting_section = f"""
              <hr style="border-color: rgba(255,255,255,.10); margin: 22px 0;">
              <h3>Supporting articles</h3>
              <ul style="padding-left:18px;">{''.join(items)}</ul>
            """

        body_html = re.sub(r"^\s*<h1[^>]*>.*?</h1>\s*", "", body_html, flags=re.IGNORECASE | re.DOTALL)
        theme = (getattr(site, "theme_css", None) or "aurora").strip()

        # ----------------------------
        # HTML wrapper
        # ----------------------------
        theme = (getattr(site, "theme_css", None) or "aurora").strip()

        # relative paths because articles live in /insights/
        rel_root = "../"

        latest_articles = (
            EvergreenArticle.objects
            .filter(site=site, status=EvergreenArticle.STATUS_PUBLISHED)
            .order_by("-published_at", "-updated_at")[:5]
        )

        ctx = {
            "site": site,
            "build_id": build_id,
            "theme": theme,
            "rel_root": rel_root,
            "article": article,
            "latest_articles": latest_articles,
        }

        header_html = render_to_string(
            "sites_builder/sites/default/partials/header.html",
            ctx
        )

        footer_html = render_to_string(
            "sites_builder/sites/default/partials/footer.html",
            ctx
        )
        html = f"""<!doctype html>
        <html lang="en" class="theme-{theme}">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width,initial-scale=1">
          <title>{title}</title>
          {"<meta name='description' content='" + meta_desc.replace('"', "&quot;") + "'>" if meta_desc else ""}
          {"<link rel='canonical' href='" + (article.canonical_url or '').replace('"', "%22") + "'>" if getattr(article, "canonical_url", "") else ""}
          <link rel="stylesheet" href="{rel_root}assets/css/landing.css?v={build_id}">
          <link rel="stylesheet" href="{rel_root}assets/css/site.css?v={build_id}">
        </head>

        <body class="theme-{theme} article-page"; display: flex>
          {header_html}

          <main id="article-main"; flex: 1 0 auto; class="container" style="max-width:1100px; margin:0 auto; padding:18px 16px 48px;">
            <div class="article-shell">
              <div class="neon-glass-card p-4">

                <div class="text-soft small" style="margin-bottom:10px;">
                  <a href="{rel_root}insights.html" class="text-soft">← Back to Insights</a>
                  <a href="https://www.mindsgate.com" class="text-soft" style="margin-left:12px;">• Mindsgate.com</a>
                </div>

                <h1 style="margin-bottom:10px;">{article.title}</h1>
                {"<div class='text-soft' style='margin-bottom:14px;'>" + article.excerpt + "</div>" if article.excerpt else ""}

                <hr style="border-color: rgba(255,255,255,.10); margin: 16px 0;">

                <div class="article-body">
                  {cornerstone_box}
                  {body_html}
                  {supporting_section}
                </div>

              </div>
            </div>
          </main>

          {footer_html}
        </body>
        </html>
        """

        return html

    def _apply_theme_classes(self, html: str, theme: str) -> str:
        """
        Ensure <html> and <body> have the correct theme-* classes.
        Works for "locked" pages that we don't re-render from templates.
        """
        theme = (theme or "aurora").strip()
        theme_class = f"theme-{theme}"

        # ---- <html ...> ----
        # If <html> has a class="", replace any existing theme-* token and ensure theme_class is present.
        def repl_html_tag(m):
            tag = m.group(0)

            # If class attr exists, normalize it
            if re.search(r'\bclass\s*=\s*["\']', tag, flags=re.IGNORECASE):
                def repl_class(cm):
                    q = cm.group(1)
                    classes = cm.group(2)

                    # remove any existing theme-xxx tokens
                    parts = [c for c in re.split(r"\s+", classes.strip()) if c and not c.startswith("theme-")]
                    parts.append(theme_class)
                    new_classes = " ".join(dict.fromkeys(parts))  # de-dupe, preserve order
                    return f'class={q}{new_classes}{q}'

                tag = re.sub(r'class\s*=\s*(["\'])(.*?)\1', repl_class, tag, flags=re.IGNORECASE | re.DOTALL)
                return tag

            # No class attr: inject one
            # Add just before closing ">"
            return tag[:-1] + f' class="{theme_class}">'

        html = re.sub(r"<html\b[^>]*>", repl_html_tag, html, count=1, flags=re.IGNORECASE | re.DOTALL)

        # ---- <body ...> ----
        # Ensure body contains theme-* class too (your CSS scopes to body.theme-... a lot)
        def repl_body_tag(m):
            tag = m.group(0)

            if re.search(r'\bclass\s*=\s*["\']', tag, flags=re.IGNORECASE):
                def repl_class(cm):
                    q = cm.group(1)
                    classes = cm.group(2)

                    parts = [c for c in re.split(r"\s+", classes.strip()) if c and not c.startswith("theme-")]
                    parts.append(theme_class)
                    new_classes = " ".join(dict.fromkeys(parts))
                    return f'class={q}{new_classes}{q}'

                tag = re.sub(r'class\s*=\s*(["\'])(.*?)\1', repl_class, tag, flags=re.IGNORECASE | re.DOTALL)
                return tag

            return tag[:-1] + f' class="{theme_class}">'

        html = re.sub(r"<body\b[^>]*>", repl_body_tag, html, count=1, flags=re.IGNORECASE | re.DOTALL)

        return html

    def _render_insights_index(self, site: Site, articles: list, build_id: str) -> str:
        cards = []

        theme = (getattr(site, "theme_css", None) or "aurora").strip()

        latest_articles = (
            EvergreenArticle.objects
            .filter(site=site, status=EvergreenArticle.STATUS_PUBLISHED)
            .order_by("-published_at", "-updated_at")[:5]
        )

        ctx = {
            "site": site,
            "build_id": build_id,
            "theme": theme,
            "rel_root": "",  # insights.html sits at site root
            "latest_articles": latest_articles,
        }

        header_html = render_to_string(
            "sites_builder/sites/default/partials/header.html",
            ctx
        )

        footer_html = render_to_string(
            "sites_builder/sites/default/partials/footer.html",
            ctx
        )

        for a in articles:
            slug = a.slug
            url = f"insights/{slug}.html"
            excerpt = (a.excerpt or "").strip()
            cards.append(f"""
              <div class="neon-glass-card p-4 mb-3">
                <h3 class="mb-2"><a href="{url}" style="text-decoration:none;">{a.title}</a></h3>
                <div class="text-soft small">{excerpt}</div>
                <div class="mt-3">
                  <a class="btn-glass" href="{url}">Read</a>
                </div>
              </div>
            """)

        cards_html = "\n".join(cards) if cards else """
          <div class="neon-glass-card p-4">
            <div class="text-soft small">No insights published yet.</div>
          </div>
        """

        # Hero image candidates (prefer webp if present)
        hero_webp = "assets/images/hero-insights.webp"
        hero_png = "assets/images/hero-insights.png"
        hero_jpg = "assets/images/hero-insights.jpg"

        return f"""<!doctype html>
    <html lang="en" class="theme-{theme}">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <title>{site.name} | Insights</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
      <link rel="stylesheet" href="assets/css/landing.css?v={build_id}">
      <link rel="stylesheet" href="assets/css/site.css?v={build_id}">
    </head>

    <body class="theme-{getattr(site, 'theme_css', 'neon_glass') or 'neon_glass'}" style="min-height:100vh; display:flex; flex-direction:column;">
      {header_html}

      <main id="main" style="flex:1 0 auto;">
        <div class="container" style="max-width:1100px; margin:0 auto; padding:24px 16px;">

          <!-- Header band (no external image dependency) -->
          <div class="insights-hero mb-4">
            <h1 class="insights-hero__title">Insights</h1>
            <p class="insights-hero__lede">Field notes on architecture, AI in production, and modernizing the systems businesses run on.</p>
          </div>

          {cards_html}
        </div>
      </main>

      {footer_html}
      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>

    </body>
    </html>
    """

    def _write_sitelinks(self, site_dir: Path, links: List[Dict[str, str]]) -> None:
        """
        Write sitelinks.json.
        If it exists, overwrite with the new authoritative set.
        """
        out = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "links": links,
        }
        (site_dir / "sitelinks.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    def _localize_absolute_assets(self, html: str, site_dir: Path, cache: dict) -> str:
        """Make the built page self-contained: download any absolute http(s) image
        URL into assets/images/<slug> and rewrite the reference to a relative path.
        Falls back to leaving the original URL if the download fails (never breaks)."""
        if not requests:
            return html
        img_dir = site_dir / "assets" / "images"

        def repl(m):
            attr, url = m.group(1), m.group(2)
            if url in cache:
                return f'{attr}="{cache[url]}"' if cache[url] else m.group(0)
            base = unquote(urlparse(url).path.rsplit("/", 1)[-1]) or "asset"
            name, _, ext = base.rpartition(".")
            fname = f"{slugify(name) or 'asset'}.{(ext or 'img').lower()}"
            dest = img_dir / fname
            try:
                if not dest.exists():
                    img_dir.mkdir(parents=True, exist_ok=True)
                    r = requests.get(url, timeout=15)
                    r.raise_for_status()
                    dest.write_bytes(r.content)
                cache[url] = f"assets/images/{fname}"
                return f'{attr}="{cache[url]}"'
            except Exception as e:
                print(f"[WARN] Could not localize asset {url}: {e}")
                cache[url] = None
                return m.group(0)

        return _ABS_IMG_RE.sub(repl, html)

    def build_site(self, site: Site) -> Path:
        """
        Render all pages of a site to static HTML files under:
        output/sites/<site.slug>/
        Also generates published Evergreen Articles under:
        output/sites/<site.slug>/insights/<slug>.html
        And writes sitelinks.json.
        """
        site_dir = self.base_output_dir / site.slug
        site_dir.mkdir(parents=True, exist_ok=True)

        build_id = datetime.utcnow().strftime("%Y%m%d%H%M%S")

        # Per-build cache of localized absolute image URLs (download once, reuse).
        asset_cache: dict = {}

        # Collect links for sitelinks.json
        sitelinks: List[Dict[str, str]] = []

        pages = site.pages.select_related("parent").prefetch_related("children").order_by(
            "is_root", "depth", "nav_order", "title", "id"
        )
        latest_articles = list(
            EvergreenArticle.objects
            .filter(site=site, status=EvergreenArticle.STATUS_PUBLISHED)
            .order_by("-published_at", "-updated_at")[:3]
        )
        theme = (getattr(site, "theme_css", None) or "aurora").strip()
        for page in pages:
            parent = page.parent
            children = list(page.children.all().order_by("nav_order", "title", "id"))

            filename = "index.html" if page.is_root else f"{page.slug}.html"
            out_path = site_dir / filename

            if getattr(page, "is_locked", False):
                # ✅ Locked: do NOT regenerate content, but DO re-style the HTML
                source_html = None

                manual = (page.manual_html or "").strip()
                if manual:
                    source_html = manual
                else:
                    if out_path.exists():
                        source_html = out_path.read_text(encoding="utf-8", errors="ignore")
                    else:
                        print(f"[WARN] Page '{page.slug}' is locked but output is missing: {out_path}")
                        continue
                styled_html = cardify_subsections(source_html)
                styled_html = self._apply_theme_classes(styled_html, theme)  # ✅ add this
                styled_html = self._relativize_root_internal_links(site, styled_html)
                styled_html = self._localize_absolute_assets(styled_html, site_dir, asset_cache)
                out_path.write_text(styled_html, encoding="utf-8")
            else:
                context = {
                    "site": site,
                    "page": page,
                    "parent": parent,
                    "children": children,
                    "build_id": build_id,
                    "latest_articles": latest_articles,
                    "theme": theme,  # ✅ add this
                }

                if getattr(page, "page_type", "article") == "landing":
                    # Composed marketing layout — section blocks, no cardify.
                    page.landing_sections = self._normalize_landing_section_links(
                        site, page.landing_sections
                    )
                    html = render_to_string("sites_builder/sites/default/landing.html", context)
                else:
                    # Editorial article layout — single column, cardify subsections.
                    html = render_to_string("sites_builder/sites/default/page.html", context)
                    html = cardify_subsections(html)
                html = self._relativize_root_internal_links(site, html)
                html = self._localize_absolute_assets(html, site_dir, asset_cache)
                out_path.write_text(html, encoding="utf-8")

            sitelinks.append({
                "title": getattr(page, "title", page.slug),
                "url": filename,
                "type": "page",
            })

        # ---- Evergreen Articles ----
        insights_dir = site_dir / "insights"
        insights_dir.mkdir(parents=True, exist_ok=True)

        articles = (
            EvergreenArticle.objects
            .filter(site=site, status=EvergreenArticle.STATUS_PUBLISHED)
            .order_by("-published_at", "-updated_at", "title")
        )

        for a in articles:
            slug = (a.slug or slugify(a.title))[:255]
            filename = f"{slug}.html"
            out_path = insights_dir / filename

            html = self._render_article_html(site=site, article=a, build_id=build_id)
            html = cardify_subsections(html)
            html = self._relativize_root_internal_links(site, html, prefix="../")
            out_path.write_text(html, encoding="utf-8")

            sitelinks.append({
                "title": a.title,
                "url": f"insights/{filename}",
                "type": "evergreen_article",
            })

        # Build insights.html auto blog-index — UNLESS the site owns a deliberate
        # landing page at that slug (then that page wins; don't clobber it).
        has_insights_landing = site.pages.filter(
            slug="insights", page_type="landing"
        ).exists()
        if not has_insights_landing:
            insights_index = self._render_insights_index(site=site, articles=list(articles), build_id=build_id)
            (site_dir / "insights.html").write_text(insights_index, encoding="utf-8")

            # Add to sitelinks near the top (optional)
            sitelinks.append({
                "title": "Insights",
                "url": "insights.html",
                "type": "page",
            })

        # Write sitelinks.json (pages + articles)
        self._write_sitelinks(site_dir, sitelinks)

        # Refresh SEO files on every build (robots.txt + sitemap.xml incl. articles)
        write_seo_files(site)

        # Copy site css (theme source -> output assets/css/site.css)
        assets_css_dir = site_dir / "assets" / "css"
        assets_css_dir.mkdir(parents=True, exist_ok=True)
        dst_css = assets_css_dir / "site.css"

        # Shared landing-page layout (theme-agnostic) -> assets/css/landing.css
        shared_landing = Path(settings.BASE_DIR) / "static" / "themes" / "_landing.css"
        if shared_landing.exists():
            copyfile(shared_landing, assets_css_dir / "landing.css")

        theme_key = getattr(site, "theme_css", "neon_glass") or "neon_glass"
        theme_file = THEME_CSS_MAP.get(theme_key, "neon_glass.css")
        print("=====> Theme file:", theme_file, " theme_key:", theme_key)

        # Prefer /static/themes/<file>, fallback to /static/<file>
        src_css_candidates = [
            Path(settings.BASE_DIR) / "static" / "themes" / theme_file,
            Path(settings.BASE_DIR) / "static" / theme_file,
        ]
        src_css = next((p for p in src_css_candidates if p.exists()), None)

        if not src_css:
            dst_css.write_text(
                f"/* site.css missing: theme '{theme_key}' file not found ({theme_file}) */\n",
                encoding="utf-8",
            )
        else:
            css = src_css.read_text(encoding="utf-8", errors="ignore")

            # ✅ Normalize theme scope for neon_glass
            body_class = f"theme-{theme_key}"
            if theme_key == "neon_glass":
                css = css.replace("body.theme-neon ", f"body.{body_class} ")
                css = css.replace("body.theme-neon{", f"body.{body_class}{{")
                css = css.replace("body.theme-neon\n", f"body.{body_class}\n")
                css = css.replace("body.theme-neon,", f"body.{body_class},")
                css = css.replace("body.theme-neon.", f"body.{body_class}.")

            dst_css.write_text(css, encoding="utf-8")

        # Optimize images (PNG in-place + WebP siblings)
        try:
            assets_images_dir = site_dir / "assets" / "images"
            stats = optimize_images_dir(assets_images_dir)
            if stats.get("files_seen"):
                print(
                    f"[IMG] {site.slug}: seen={stats['files_seen']} "
                    f"optimized={stats['optimized']} webp={stats['webp_created']} "
                    f"saved={stats['bytes_saved']:,} bytes"
                )
        except Exception as e:
            print(f"[WARN] Image optimization failed: {e}")

        # Offline link validation report
        try:
            report = self._validate_links(site_dir)
            (site_dir / "link_report.json").write_text(
                json.dumps(report, indent=2),
                encoding="utf-8",
            )
            if not report.get("ok"):
                print(
                    f"[WARN] Link validation found {len(report.get('issues', []))} issue(s). "
                    f"See: {site_dir / 'link_report.json'}"
                )
        except Exception as e:
            print(f"[WARN] Failed to validate links: {e}")

        return site_dir
