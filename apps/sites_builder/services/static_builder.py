from pathlib import Path
from typing import Optional, Dict, Any, List
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import escape
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
from .reader_feedback import build_reader_feedback_context

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
    "startup": "startup.css",
    "aurora": "aurora.css",
    "verdant": "verdant.css",
    "bauhaus": "bauhaus.css",
    "editorial": "editorial.css",
    "mindsgate": "mindsgate.css",
}

THEME_FAVICON_MAP = {
    "mindsgate": "mindsgate-favicon.svg",
}

THEME_CONTENT_ASSET_MAP = {
    "mindsgate": ("neo-cottage-revolution-og.png",),
}

PAGE_TEMPLATE_MAP = {
    "humainx": "sites_builder/sites/default/humainx.html",
    "neo_cottage": "sites_builder/sites/default/neo_cottage.html",
}

ARTICLE_READER_RESPONSE_MARKER = "<!-- reader-response -->"


class StaticBuilder:
    """
    Drop-in static site builder that also outputs Evergreen Articles and
    writes sitelinks.json (pages + articles).
    """

    def __init__(self, base_output_dir: Optional[Path] = None):
        if base_output_dir is None:
            base_output_dir = Path(settings.BASE_DIR) / "output" / "sites"
        self.base_output_dir = base_output_dir

    def _inject_theme_favicon(self, html: str, theme: str, rel_root: str = "") -> str:
        """Add the configured theme favicon to generated and locked HTML."""
        if theme not in THEME_FAVICON_MAP or re.search(
            r'<link\b[^>]*\brel=["\'][^"\']*\bicon\b', html, re.IGNORECASE
        ):
            return html
        favicon = (
            f'  <link rel="icon" type="image/svg+xml" '
            f'href="{rel_root}assets/images/favicon.svg">\n'
        )
        return re.sub(r"</head>", f"{favicon}</head>", html, count=1, flags=re.IGNORECASE)

    def _copy_theme_favicon(self, site_dir: Path, theme: str) -> None:
        source_name = THEME_FAVICON_MAP.get(theme)
        if not source_name:
            return
        source = Path(settings.BASE_DIR) / "static" / "themes" / source_name
        if not source.is_file():
            raise FileNotFoundError(f"Theme favicon not found: {source}")
        destination_dir = site_dir / "assets" / "images"
        destination_dir.mkdir(parents=True, exist_ok=True)
        copyfile(source, destination_dir / "favicon.svg")
        jpeg_source = source.with_suffix(".jpg")
        if jpeg_source.is_file():
            copyfile(jpeg_source, destination_dir / "favicon.jpg")

    def _copy_theme_content_assets(self, site_dir: Path, theme: str) -> None:
        """Copy curated, theme-owned editorial assets into the static build."""
        source_dir = Path(settings.BASE_DIR) / "static" / "themes"
        destination_dir = site_dir / "assets" / "images"
        for source_name in THEME_CONTENT_ASSET_MAP.get(theme, ()):
            source = source_dir / source_name
            if not source.is_file():
                raise FileNotFoundError(f"Theme content asset not found: {source}")
            destination_dir.mkdir(parents=True, exist_ok=True)
            copyfile(source, destination_dir / source_name)

    @staticmethod
    def _normalize_article_body_markup(body: str) -> str:
        """Keep only article-body markup and prevent nested document headings."""
        body = (body or "").strip()
        document_body = re.search(
            r"<body\b[^>]*>(.*?)</body>", body, flags=re.IGNORECASE | re.DOTALL
        )
        if document_body:
            body = document_body.group(1).strip()
        return re.sub(
            r"<h1\b[^>]*>.*?</h1>",
            "",
            body,
            count=1,
            flags=re.IGNORECASE | re.DOTALL,
        ).strip()

    @staticmethod
    def _build_article_schema(
        site: Site,
        article: EvergreenArticle,
        canonical_url: str,
        image_url: str,
        author_name: str,
        author_url: str,
        modified_at,
    ) -> str:
        if not canonical_url:
            return ""

        author_type = (
            "Organization"
            if author_name.casefold() in {site.name.casefold(), "humainx"}
            else "Person"
        )
        author = {"@type": author_type, "name": author_name}
        if author_url:
            author["url"] = author_url

        article_node = {
            "@type": "Article",
            "@id": f"{canonical_url}#article",
            "headline": article.title,
            "description": article.meta_description or article.excerpt,
            "mainEntityOfPage": {"@type": "WebPage", "@id": canonical_url},
            "author": author,
            "publisher": {
                "@type": "Organization",
                "name": site.name,
                "url": site.base_url,
            },
        }
        if article.published_at:
            article_node["datePublished"] = article.published_at.isoformat()
        if modified_at:
            article_node["dateModified"] = modified_at.isoformat()
        if image_url:
            article_node["image"] = [image_url]
        if article.series:
            article_node["isPartOf"] = {
                "@type": "CreativeWorkSeries",
                "name": article.series,
                "url": f"{site.base_url}/{slugify(article.series)}.html",
            }

        breadcrumb = {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": site.name,
                    "item": f"{site.base_url}/",
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "Insights",
                    "item": f"{site.base_url}/insights.html",
                },
                {
                    "@type": "ListItem",
                    "position": 3,
                    "name": article.title,
                    "item": canonical_url,
                },
            ],
        }
        return json.dumps(
            {"@context": "https://schema.org", "@graph": [article_node, breadcrumb]},
            ensure_ascii=False,
            separators=(",", ":"),
        )

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
        """Render an Insight using the shared article system and optional series metadata."""
        body = (article.body_md or "").strip()
        if body.startswith("<"):
            # Curated article source may already be semantic HTML. Passing it
            # through Markdown can subtly alter component markup and spacing.
            body_html = body
        elif md is not None and body:
            try:
                body_html = md.markdown(body, extensions=["extra", "tables", "toc"])
            except Exception:
                body_html = body
        else:
            body_html = body

        cornerstone_links = (
            ArticleCornerstoneLink.objects
            .filter(site=site, supporting=article, cornerstone__status=EvergreenArticle.STATUS_PUBLISHED)
            .select_related("cornerstone")
            .order_by("-is_primary", "cornerstone__title")
        )

        supporting_links = []
        if getattr(article, "is_cornerstone", False):
            supporting_links = (
                ArticleCornerstoneLink.objects
                .filter(site=site, cornerstone=article, supporting__status=EvergreenArticle.STATUS_PUBLISHED)
                .select_related("supporting")
                .order_by("-is_primary", "-supporting__published_at", "supporting__title")
            )

        body_html = self._normalize_article_body_markup(body_html)
        article_body_before_feedback = body_html
        article_body_after_feedback = ""
        if ARTICLE_READER_RESPONSE_MARKER in body_html:
            article_body_before_feedback, article_body_after_feedback = body_html.split(
                ARTICLE_READER_RESPONSE_MARKER, 1
            )

        theme = (getattr(site, "theme_css", None) or "aurora").strip()
        latest_articles = (
            EvergreenArticle.objects
            .filter(site=site, status=EvergreenArticle.STATUS_PUBLISHED)
            .order_by("-published_at", "-updated_at")[:5]
        )
        canonical_url = article.canonical_url
        if not canonical_url and site.base_url:
            canonical_url = f"{site.base_url}/insights/{article.slug}.html"

        hero_url = (article.hero_image_url or "").strip()
        article_hero_page_url = hero_url
        article_hero_meta_url = hero_url
        article_hero_webp_page_url = ""
        parsed_hero_url = urlparse(hero_url)
        if hero_url and not parsed_hero_url.scheme and not parsed_hero_url.netloc:
            asset_path = hero_url.lstrip("/")
            article_hero_page_url = (
                hero_url if hero_url.startswith("../") else f"../{asset_path}"
            )
            if site.base_url:
                article_hero_meta_url = (
                    article_hero_page_url
                    if asset_path.startswith("../")
                    else f"{site.base_url}/{asset_path}"
                )
            else:
                article_hero_meta_url = article_hero_page_url

            local_asset = self.base_output_dir / site.slug / asset_path
            if asset_path.startswith("../") or not local_asset.is_file():
                # A missing optional hero must not create a broken link in every
                # generated article build. Editors can restore it by supplying
                # the asset (or an absolute URL).
                article_hero_page_url = ""
                article_hero_meta_url = ""
            else:
                webp_asset = local_asset.with_suffix(".webp")
                if webp_asset.is_file():
                    webp_path = Path(asset_path).with_suffix(".webp").as_posix()
                    article_hero_webp_page_url = f"../{webp_path}"

        article_modified_at = (
            article.content_updated_at or article.updated_at or article.published_at
        )
        article_author = {
            "name": (article.author_name or site.name).strip(),
            "url": (article.author_url or site.base_url).strip(),
        }
        article_schema_json = self._build_article_schema(
            site=site,
            article=article,
            canonical_url=canonical_url,
            image_url=article_hero_meta_url,
            author_name=article_author["name"],
            author_url=article_author["url"],
            modified_at=article_modified_at,
        )

        is_humainx = (article.series or "").casefold() == "humainx"
        newsletter = site.newsletter_config or {}
        configured_series = str(newsletter.get("series") or "").strip()
        series_matches = not configured_series or (
            configured_series.casefold() == (article.series or "").casefold()
        )
        article_follow = None
        if (
            article.series
            and series_matches
            and newsletter.get("enabled")
            and str(newsletter.get("provider") or "").casefold() == "buttondown"
            and newsletter.get("form_action")
        ):
            article_follow = {
                "anchor": str(newsletter.get("article_anchor") or "").strip()
                or f"follow-{slugify(article.series)}",
                "label": str(newsletter.get("article_link_label") or "").strip()
                or f"Follow {article.series}",
                "eyebrow": str(newsletter.get("section_eyebrow") or "").strip()
                or "Follow the exploration",
                "description": str(newsletter.get("section_description") or "").strip(),
            }

        reader_feedback = build_reader_feedback_context(
            article, site.reader_feedback_config
        )

        context = {
            "site": site,
            "build_id": build_id,
            "theme": theme,
            "rel_root": "../",
            "article": article,
            "article_body_before_feedback": article_body_before_feedback,
            "article_body_after_feedback": article_body_after_feedback,
            "canonical_url": canonical_url,
            "article_hero_page_url": article_hero_page_url,
            "article_hero_meta_url": article_hero_meta_url,
            "article_hero_webp_page_url": article_hero_webp_page_url,
            "article_modified_at": article_modified_at,
            "article_author": article_author,
            "article_schema_json": article_schema_json,
            "cornerstone_links": cornerstone_links,
            "supporting_links": supporting_links,
            "latest_articles": latest_articles,
            "is_humainx": is_humainx,
            "article_follow": article_follow,
            "reader_feedback": reader_feedback,
        }
        return render_to_string("sites_builder/sites/default/article.html", context)

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
        canonical_url = f"{site.base_url}/insights.html" if site.base_url else ""
        title = f"{site.name} | Insights"
        description = (
            "Insights from Mindsgate on AI, autonomous systems, software delivery, "
            "business architecture, and the future of work."
        )
        insights_schema = json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": title,
                "description": description,
                "url": canonical_url,
                "mainEntity": {
                    "@type": "ItemList",
                    "itemListElement": [
                        {
                            "@type": "ListItem",
                            "position": position,
                            "name": article.title,
                            "url": (
                                f"{site.base_url}/insights/{article.slug}.html"
                                if site.base_url
                                else f"insights/{article.slug}.html"
                            ),
                        }
                        for position, article in enumerate(articles, start=1)
                    ],
                },
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).replace("</", "<\\/")

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
            feature_class = " humainx-insight-feature" if (a.series or "").casefold() == "humainx" else ""
            published = a.published_at.strftime("%B %Y") if a.published_at else ""
            metadata = f"{a.editorial_label} · {a.reading_minutes} min read"
            if published:
                metadata += f" · {published}"
            cards.append(f"""
              <div class="neon-glass-card p-4 mb-3{feature_class}">
                <div class="insight-card__meta">{escape(metadata)}</div>
                <h3 class="mb-2"><a href="{escape(url)}" style="text-decoration:none;">{escape(a.title)}</a></h3>
                <div class="text-soft small">{escape(excerpt)}</div>
                <div class="mt-3">
                  <a class="btn-glass" href="{escape(url)}">Read</a>
                </div>
              </div>
            """)

        cards_html = "\n".join(cards) if cards else """
          <div class="neon-glass-card p-4">
            <div class="text-soft small">No insights published yet.</div>
          </div>
        """

        return f"""<!doctype html>
    <html lang="en" class="theme-{theme}">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <title>{escape(title)}</title>
      <meta name="description" content="{escape(description)}">
      <meta name="robots" content="index,follow">
      {f'<link rel="canonical" href="{escape(canonical_url)}">' if canonical_url else ''}
      <meta property="og:type" content="website">
      <meta property="og:title" content="{escape(title)}">
      <meta property="og:description" content="{escape(description)}">
      {f'<meta property="og:url" content="{escape(canonical_url)}">' if canonical_url else ''}
      <meta name="twitter:card" content="summary">
      <meta name="twitter:title" content="{escape(title)}">
      <meta name="twitter:description" content="{escape(description)}">
      <script type="application/ld+json">{insights_schema}</script>
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

    def _write_article_redirects(
        self, site_dir: Path, site: Site, articles: list[EvergreenArticle]
    ) -> None:
        """Write Apache 301 rules plus crawl-safe HTML fallbacks for old slugs."""
        redirect_rules = []
        insights_dir = site_dir / "insights"
        for article in articles:
            current_slug = (article.slug or slugify(article.title)).strip()
            for raw_slug in article.legacy_slugs or []:
                legacy_slug = slugify(str(raw_slug))
                if not legacy_slug or legacy_slug == current_slug:
                    continue

                source_path = f"/insights/{legacy_slug}.html"
                destination_path = f"/insights/{current_slug}.html"
                canonical_url = (
                    f"{site.base_url}{destination_path}"
                    if site.base_url
                    else destination_path
                )
                redirect_rules.append(
                    f"Redirect 301 {source_path} {canonical_url}"
                )

                relative_target = f"{current_slug}.html"
                fallback_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Moved: {escape(article.title)}</title>
  <meta name="robots" content="noindex,follow">
  <link rel="canonical" href="{escape(canonical_url)}">
  <meta http-equiv="refresh" content="0;url={escape(relative_target)}">
  <script>window.location.replace({json.dumps(relative_target)});</script>
</head>
<body>
  <p>This article has moved to <a href="{escape(relative_target)}">{escape(article.title)}</a>.</p>
</body>
</html>
"""
                (insights_dir / f"{legacy_slug}.html").write_text(
                    fallback_html, encoding="utf-8"
                )

        htaccess = site_dir / ".htaccess"
        marker_pattern = re.compile(
            r"(?:^|\n)# BEGIN FOUNDRY REDIRECTS\n.*?"
            r"# END FOUNDRY REDIRECTS\n?",
            flags=re.DOTALL,
        )
        existing_rules = (
            htaccess.read_text(encoding="utf-8", errors="ignore")
            if htaccess.is_file()
            else ""
        )
        preserved_rules = marker_pattern.sub("\n", existing_rules).strip()
        sections = [preserved_rules] if preserved_rules else []
        if redirect_rules:
            unique_rules = list(dict.fromkeys(redirect_rules))
            sections.append(
                "# BEGIN FOUNDRY REDIRECTS\n"
                + "\n".join(unique_rules)
                + "\n# END FOUNDRY REDIRECTS"
            )
        if sections:
            htaccess.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
        elif htaccess.is_file():
            htaccess.unlink()

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
        self._copy_theme_content_assets(site_dir, theme)
        # Create modern-format siblings before rendering so article templates can
        # emit a <picture> source on the first build, not only subsequent builds.
        optimize_images_dir(site_dir / "assets" / "images")
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
                styled_html = self._inject_theme_favicon(styled_html, theme)
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

                template_name = PAGE_TEMPLATE_MAP.get(getattr(page, "template_variant", ""))
                if template_name:
                    html = render_to_string(template_name, context)
                elif getattr(page, "page_type", "article") == "landing":
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
                html = self._inject_theme_favicon(html, theme)
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
            html = self._inject_theme_favicon(html, theme, rel_root="../")
            out_path.write_text(html, encoding="utf-8")

            sitelinks.append({
                "title": a.title,
                "url": f"insights/{filename}",
                "type": "evergreen_article",
            })

        self._write_article_redirects(site_dir, site, list(articles))

        # Build insights.html auto blog-index — UNLESS the site owns a deliberate
        # landing page at that slug (then that page wins; don't clobber it).
        has_insights_landing = site.pages.filter(
            slug="insights", page_type="landing"
        ).exists()
        if not has_insights_landing:
            insights_index = self._render_insights_index(site=site, articles=list(articles), build_id=build_id)
            insights_index = self._inject_theme_favicon(insights_index, theme)
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
        self._copy_theme_favicon(site_dir, theme_key)

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
