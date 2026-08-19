from html.parser import HTMLParser
from typing import Optional, List, Dict, Any
from django.utils import timezone
from django.db import transaction
from ..models import Site, Page
from django.utils.text import slugify
from dotenv import load_dotenv

load_dotenv()

from .gpt_client import GPTSiteClient
from .image_generator import ImageGenerator
from . import seo_files
from django.conf import settings
from pathlib import Path
from urllib.parse import urlparse, urlunparse
import re
from xml.etree.ElementTree import Element, SubElement, tostring


class SiteGenerator:
    def __init__(self, gpt: Optional[GPTSiteClient] = None):
        self.gpt = gpt or GPTSiteClient()

    def _sanitize_landing_sections(self, sections, site=None):
        """Normalise generator output to the canonical schema (map common key
        synonyms), strip absolute hrefs (-> '#'), and drop model-invented images
        (we inject our own). Makes the home robust to LLM key drift.

        Absolute hrefs on the site's own domain (incl. subdomains, e.g. live
        platform apps like fracto.mindsgate.com) are kept when `site` is given."""
        if not isinstance(sections, list):
            return []

        allowed_suffix = ""
        if site is not None and site.base_url:
            host = urlparse(site.base_url).netloc.lower()
            parts = host.split(".")
            allowed_suffix = ".".join(parts[-2:]) if len(parts) >= 2 else host

        def fix_href(v):
            if not (isinstance(v, str) and v.startswith(("http://", "https://", "//"))):
                return v
            if allowed_suffix:
                url = v if v.startswith(("http://", "https://")) else "https:" + v
                host = urlparse(url).netloc.lower()
                if host == allowed_suffix or host.endswith("." + allowed_suffix):
                    return v
            return "#"

        def alias(d, canonical, *alts):
            if isinstance(d, dict) and not d.get(canonical):
                for a in alts:
                    if d.get(a):
                        d[canonical] = d.pop(a)
                        break

        for blk in sections:
            if not isinstance(blk, dict):
                continue
            t = blk.get("type")
            blk.pop("image", None)

            # `anchor` (in-page link target, human-curated like hero `background`):
            # keep only slug-like values so it's always a safe id attribute.
            anchor = blk.get("anchor")
            if anchor is not None and not (
                isinstance(anchor, str) and re.fullmatch(r"[a-z][a-z0-9-]{0,39}", anchor)
            ):
                blk.pop("anchor", None)

            # contact_form `endpoint` is human-curated: https URLs only, else the
            # template falls back to the default CRM intake endpoint.
            if t == "contact_form":
                ep = blk.get("endpoint")
                if not (isinstance(ep, str) and ep.startswith("https://")):
                    blk.pop("endpoint", None)

            if t == "hero":
                alias(blk, "headline", "title", "heading", "header")
                alias(blk, "headline_accent", "accent", "highlight")
                alias(blk, "subhead", "subtitle", "subheading", "description", "sub")
                alias(blk, "primary_cta", "cta", "primaryCta", "primary_button", "button")
                alias(blk, "secondary_cta", "secondaryCta", "secondary_button")
                # `background` is human-curated per site (never LLM-emitted). Keep only
                # whitelisted animated backgrounds; drop anything else.
                if blk.get("background") not in ("golden-spiral", "glow"):
                    blk.pop("background", None)
            elif t == "cta":
                alias(blk, "heading", "title", "headline")
                alias(blk, "text", "subhead", "subtitle", "description")
                alias(blk, "button", "cta", "primary_cta", "primaryCta")
            else:
                alias(blk, "heading", "title", "header", "headline")
                alias(blk, "subhead", "subtitle", "description")
                alias(blk, "eyebrow", "kicker", "overline")

            for k in ("primary_cta", "secondary_cta", "button"):
                cta = blk.get(k)
                if isinstance(cta, dict):
                    alias(cta, "label", "text", "title", "name")
                    alias(cta, "href", "url", "link")
                    if "href" in cta:
                        cta["href"] = fix_href(cta["href"])

            items = blk.get("items")
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    item.pop("image", None)
                    if t == "stats":
                        alias(item, "value", "number", "stat", "metric", "figure", "amount")
                        alias(item, "label", "caption", "name", "title", "text")
                        alias(item, "sublabel", "detail", "note", "description", "sub")
                    else:
                        alias(item, "title", "name", "heading", "label")
                        alias(item, "text", "description", "body", "content", "subtitle")
                        alias(item, "badge", "status", "tag")
                        alias(item, "badge_color", "badgeColor", "status_color", "color")
                        alias(item, "link_label", "cta_label", "link_text", "linkText")
                    alias(item, "href", "url", "link")
                    if "href" in item:
                        item["href"] = fix_href(item["href"])
        return sections

    def _rewrite_internal_placeholders(self, site: Site, value: str) -> str:
        """
        Convert internal placeholders into real relative URLs.

        Supported placeholders:
        - internal://<slug>
        - {{internal:<slug>}}

        Rules:
        - internal://index or internal://home -> /
        - otherwise -> /<slug>.html  (only if slug exists)
        - if slug does not exist: return '#' (safe) to avoid broken build links
        """
        if not value:
            return value

        known_slugs = set(site.pages.all().values_list("slug", flat=True))

        def to_href(slug: str) -> str:
            s = (slug or "").strip().strip("/")
            if not s or s in ("index", "home", "root"):
                return "index.html"
            if s in known_slugs:
                return f"{s}.html"
            return "#"

        # internal://slug
        m = re.match(r"^internal://(.+)$", value.strip(), flags=re.IGNORECASE)
        if m:
            return to_href(m.group(1))

        # {{internal:slug}}
        mm = re.match(r"^\{\{\s*internal\s*:\s*([^\}]+)\}\}$", value.strip(), flags=re.IGNORECASE)
        if mm:
            return to_href(mm.group(1))

        return value

    def _normalize_body_links(self, site: Site, html: str) -> str:
        """
        Fix common GPT link mistakes:
        - '/<domain>/' stuck into path (e.g. /www.example.com/foo)
        - 'www.example.com/foo' missing scheme
        - internal links missing '.html'
        - internal placeholders internal://<slug> and {{internal:<slug>}}
        """
        if not html:
            return html

        domain = (site.domain or "").strip()
        if "://" in domain:
            domain = urlparse(domain).netloc
        domain = domain.strip("/").lower()

        known_slugs = set(site.pages.all().values_list("slug", flat=True))

        class _Rewriter(HTMLParser):
            def __init__(self):
                super().__init__()
                self.out = []

            def handle_starttag(self, tag, attrs):
                attrs = attrs or []
                new_attrs = []
                for k, v in attrs:
                    if k in ("href", "src") and v:
                        vv = v.strip()

                        # 1) Rewrite internal placeholders first
                        vv = self._rewrite_internal(vv)

                        # Skip non-http-ish targets
                        p = urlparse(vv)
                        if p.scheme in ("mailto", "tel", "javascript", "data"):
                            new_attrs.append((k, vv))
                            continue

                        # If value is "www.example.com/..." without scheme, add https://
                        if vv.lower().startswith("www."):
                            vv = "https://" + vv

                        # If it is "/<domain>/something", strip the domain part
                        if domain and vv.lower().startswith(f"/{domain}/"):
                            vv = vv[len(domain) + 1:]  # removes "/{domain}"

                        # If it is absolute to our own domain, convert to relative path
                        pp = urlparse(vv)
                        if domain and pp.netloc.lower() == domain:
                            vv = pp.path or "/"
                            if pp.query:
                                vv = vv + "?" + pp.query

                        # Add .html for internal slug-ish links (no extension)
                        path = urlparse(vv).path or ""
                        slugish = path.lstrip("/").rstrip("/")
                        last = slugish.split("/")[-1] if slugish else ""
                        if last and "." not in last and last not in ("", "/"):
                            if last in known_slugs:
                                vv = f"{slugish}.html"

                        new_attrs.append((k, vv))
                    else:
                        new_attrs.append((k, v))

                attr_txt = "".join([f' {k}="{(v or "")}"' for k, v in new_attrs])
                self.out.append(f"<{tag}{attr_txt}>")

            def _rewrite_internal(self, vv: str) -> str:
                try:
                    return self._outer._rewrite_internal_placeholders(site, vv)
                except Exception:
                    return vv

            def handle_endtag(self, tag):
                self.out.append(f"</{tag}>")

            def handle_data(self, data):
                self.out.append(data)

            def handle_startendtag(self, tag, attrs):
                attrs = attrs or []
                new_attrs = []
                for k, v in attrs:
                    if k in ("href", "src") and v:
                        vv = v.strip()
                        try:
                            vv = self._outer._rewrite_internal_placeholders(site, vv)
                        except Exception:
                            pass
                        new_attrs.append((k, vv))
                    else:
                        new_attrs.append((k, v))
                attr_txt = "".join([f' {k}="{(v or "")}"' for k, v in new_attrs])
                self.out.append(f"<{tag}{attr_txt} />")

        r = _Rewriter()
        r._outer = self  # small bridge for inner class
        try:
            r.feed(html)
            return "".join(r.out)
        except Exception:
            return html

    def _site_context_for_prompt(self, site: Site) -> Dict[str, Any]:
        pages = site.pages.all().values("slug", "title", "depth", "parent_id", "is_root")
        return {
            "site_name": site.name,
            "description": site.description,
            "pages": list(pages),
        }

    def _output_site_dir(self, site: Site) -> Path:
        return Path(settings.BASE_DIR) / "output" / "sites" / site.slug

    def _base_url(self, site: Site) -> str:
        raw = (site.domain or "").strip()
        if not raw:
            return ""
        if "://" not in raw:
            raw = "https://" + raw
        p = urlparse(raw)
        netloc = p.netloc.strip().lower()
        scheme = (p.scheme or "https").lower()
        return urlunparse((scheme, netloc, "", "", "", "")).rstrip("/")

    def _page_url(self, site: Site, page: Page) -> str:
        base = self._base_url(site)
        if not base:
            return ""
        if getattr(page, "is_root", False):
            return base + "/"
        slug = (page.slug or "").strip().strip("/")
        if not slug:
            return base + "/"
        return f"{base}/{slug}.html"

    # SEO writers moved to services/seo_files.py so StaticBuilder.build_site can
    # refresh them on every rebuild too. Kept as thin wrappers for existing callers.
    def _write_robots_txt(self, site: Site) -> None:
        seo_files.write_robots_txt(site)

    def _write_sitemap_xml(self, site: Site) -> None:
        seo_files.write_sitemap_xml(site)

    def _write_seo_files(self, site: Site) -> None:
        seo_files.write_seo_files(site)

    @transaction.atomic
    def ensure_root_page(self, site: Site) -> Page:
        root = site.pages.filter(is_root=True).first()
        if root:
            return root

        self.gpt.set_billing(site, "generate_site")
        data = self.gpt.generate_root_page(site.description)

        # Optional editor pass on root
        try:
            site_ctx = self._site_context_for_prompt(site)
            page_ctx = {"title": data.get("title"), "slug": "index", "depth": 0, "is_root": True}
            data = self.gpt.refine_page_content(site_context=site_ctx, page=page_ctx, draft={
                "meta_title": data.get("meta_title", ""),
                "meta_description": data.get("meta_description", ""),
                "focus_keyword": data.get("focus_keyword", ""),
                "body_html": data.get("body_html", ""),
            })
        except Exception as e:
            print(f"[WARN] Root editor pass failed: {e}")

        body_html = self._normalize_body_links(site, data.get("body_html") or "")

        root = Page.objects.create(
            site=site,
            title=data.get("title") or "Home",
            meta_title=(data.get("meta_title") or "")[:255],
            meta_description=(data.get("meta_description") or "")[:512],
            focus_keyword=(data.get("focus_keyword") or "")[:255],
            body_html=body_html,
            depth=0,
            is_root=True,
            last_generated_at=timezone.now(),
        )

        # hero image
        try:
            image_gen = ImageGenerator(Path(settings.BASE_DIR) / "output" / "sites")
            hero_context = f"Root page for site '{site.name}'. Site description: {site.description}."
            image_url = image_gen.generate_page_hero(site.slug, root.slug, hero_context, usage_obj=site, usage_action="image_hero")
            root.hero_image_url = image_url
            root.save(update_fields=["hero_image_url"])
        except Exception as e:
            print(f"[WARN] Failed to generate hero image for root page: {e}")

        # Compose the home as a marketing LANDING page (section blocks).
        # body_html above stays as a fallback; landing_sections drive the home.
        try:
            sections = self.gpt.generate_landing_sections(site.description, page_title=root.title)
            sections = self._sanitize_landing_sections(sections, site=site)
            if root.hero_image_url:
                for blk in sections:
                    if isinstance(blk, dict) and blk.get("type") == "hero":
                        blk["image"] = root.hero_image_url  # only image we trust
                        break
            self._generate_card_images(site, sections)
            if sections:
                root.page_type = Page.PAGE_TYPE_LANDING
                root.landing_sections = sections
                root.save(update_fields=["page_type", "landing_sections"])
        except Exception as e:
            print(f"[WARN] Failed to generate landing sections for root page: {e}")

        # Keep minimal: if root produced child hints, add them as skeletons
        for idx, child in enumerate(data.get("children", []), start=10):
            Page.objects.get_or_create(
                site=site,
                parent=root,
                title=child.get("title") or "Page",
                defaults={"depth": 1, "nav_order": idx},
            )

        return root

    def _generate_card_images(self, site, sections, limit: int = 8):
        """Generate an image for each 'cards' item that has no icon and no image
        (icon-cards stay icon-only; existing images are respected). Bounded by `limit`."""
        image_gen = ImageGenerator(Path(settings.BASE_DIR) / "output" / "sites")
        made = 0
        for sec in sections:
            if not isinstance(sec, dict) or sec.get("type") != "cards":
                continue
            for item in sec.get("items", []) or []:
                if made >= limit:
                    return
                if not isinstance(item, dict) or item.get("icon") or item.get("image"):
                    continue
                try:
                    ctx = f"{item.get('title','')}. {item.get('text','')}. For the site '{site.name}'."
                    slug = "card-" + (slugify(item.get("title") or "item")[:40] or "item")
                    item["image"] = image_gen.generate_page_hero(
                        site.slug, slug, ctx, usage_obj=site, usage_action="image_card")
                    made += 1
                except Exception as e:  # noqa: BLE001
                    print(f"[WARN] Card image generation failed: {e}")
        return made

    def convert_home_to_landing(self, site, *, generate_hero: bool = True,
                                generate_card_images: bool = True, theme: str = "editorial"):
        """Convert an EXISTING site's home page into a generated marketing landing
        page (page_type=landing + AI-generated section blocks + optional hero image).
        Returns the home Page. Caller is responsible for rebuilding the static site."""
        root = site.pages.get(is_root=True)
        self.gpt.set_billing(site, "convert_to_landing")

        if theme and site.theme_css != theme:
            site.theme_css = theme
            site.save(update_fields=["theme_css"])

        sections = self.gpt.generate_landing_sections(
            site.description or site.name, page_title=root.title
        )
        sections = self._sanitize_landing_sections(sections, site=site)
        if not sections:
            raise RuntimeError("Generator returned no landing sections.")

        if generate_hero:
            try:
                image_gen = ImageGenerator(Path(settings.BASE_DIR) / "output" / "sites")
                hero_context = f"Hero image for '{site.name}'. {site.description or ''}"
                image_url = image_gen.generate_page_hero(site.slug, "home", hero_context, usage_obj=site, usage_action="image_hero")
                root.hero_image_url = image_url
                for blk in sections:
                    if isinstance(blk, dict) and blk.get("type") == "hero":
                        blk["image"] = image_url  # only image we trust
                        break
            except Exception as e:
                print(f"[WARN] Hero image generation failed: {e}")

        if generate_card_images:
            self._generate_card_images(site, sections)

        root.page_type = Page.PAGE_TYPE_LANDING
        root.is_locked = False  # so the landing template (not frozen HTML) renders
        root.landing_sections = sections
        root.save(update_fields=["page_type", "is_locked", "landing_sections", "hero_image_url"])
        return root

    def _ensure_site_ia(self, site: Site) -> None:
        """
        Auto-create a stable top-level menu/page structure before generating lots of content.

        Behavior:
        - If the site has only the root page (or only a couple of skeletons), create an IA plan.
        - Materialize planned pages as Page records (skeletons) under root.
        - Keeps structure lean by targeting a small page count.
        """
        self.gpt.set_billing(site, "site_ia")
        page_count = site.pages.count()

        # If you already have a decent structure, do nothing.
        if page_count >= site.target_page_count:
            return

        # Soft defaults, no model changes required:
        target_page_count = getattr(site, "target_page_count", None) or 8
        max_depth = getattr(site, "max_depth", None) or 2
        try:
            ia = self.gpt.generate_site_ia(
                site_description=site.description or "",
                target_page_count=int(target_page_count),
                max_depth=int(max_depth),
            )
            site.ia_plan = ia
            site.ia_planned_at = timezone.now()
            site.save(update_fields=["ia_plan", "ia_planned_at"])
        except Exception as e:
            print(f"[WARN] IA generation failed: {e}")
            return

        root = site.pages.filter(is_root=True).first()
        if not root:
            root = self.ensure_root_page(site)

        # Build a slug->Page map for existing pages
        existing = {p.slug: p for p in site.pages.all() if p.slug}

        def ensure_page(title: str, slug: str, parent: Page, depth: int, nav_order: int) -> Page:
            # Prefer a stable planned slug, then reuse a same-title sibling.
            p = existing.get(slug) or parent.children.filter(title=title).first()
            if p is not None:
                changed_fields = []
                if p.parent_id != parent.id or p.depth != depth or p.nav_order != nav_order:
                    p.parent = parent
                    p.depth = depth
                    p.nav_order = nav_order
                    changed_fields.extend(["parent", "depth", "nav_order"])
                if slug and p.slug != slug:
                    p.slug = slug
                    changed_fields.append("slug")
                if changed_fields:
                    p.save(update_fields=changed_fields)
                existing[p.slug] = p
                return p

            p = Page.objects.create(
                site=site,
                parent=parent,
                title=title,
                slug=slug,
                depth=depth,
                nav_order=nav_order,
            )

            # slug might be auto-derived in model.save(); refresh to capture
            p.refresh_from_db()
            if p.slug:
                existing[p.slug] = p
            return p

        # Create nav structure (depth-limited)
        nav = ia.get("nav") or []
        for i, item in enumerate(nav, start=10):
            t = (item.get("title") or "").strip()
            s = (item.get("slug") or "").strip()
            if not t or not s:
                continue

            top = ensure_page(t, s, root, 1, nav_order=i)

            children = item.get("children") or []
            if top.depth + 1 > max_depth:
                continue

            for j, ch in enumerate(children, start=10):
                ct = (ch.get("title") or "").strip()
                cs = (ch.get("slug") or "").strip()
                if not ct or not cs:
                    continue
                ensure_page(ct, cs, top, top.depth + 1, nav_order=j)

    def _get_expandable_pages(self, site: Site) -> List[tuple[Page, int]]:
        pages = site.pages.all()
        expandable: List[tuple[Page, int]] = []
        for p in pages:
            if p.depth >= site.max_depth:
                continue
            current_children = p.children.count()
            if current_children >= site.max_children_per_page:
                continue
            expandable.append((p, current_children))
        return expandable

    @transaction.atomic
    def expand_site(self, site: Site, max_new_pages: int = 10) -> int:
        """
        Generates content for new child pages, respecting per-site depth & children limits.
        Returns the number of pages created/updated this run.

        Upgrades:
        - Ensure IA/menu structure first (lean, stable)
        - Optionally cap total pages via site.target_page_count (if present)
        - Editor pass refinement for higher quality copy
        - Internal links can be internal://slug placeholders
        """
        self.ensure_root_page(site)
        self.gpt.set_billing(site, "expand_site")
        self._ensure_site_ia(site)
        if getattr(site, "structure_locked", False):
            self._write_seo_files(site)
            return 0

        created_count = 0

        # Optional global cap without model changes
        target_page_count = getattr(site, "target_page_count", None)
        if target_page_count is None:
            # sensible default if you do not have this on the model yet
            target_page_count = 12

        # If already at/over target, do nothing
        try:
            remaining_quota = max(0, int(target_page_count) - site.pages.count())
            if remaining_quota <= 0:
                self._write_seo_files(site)
                return 0
            max_new_pages = min(max_new_pages, remaining_quota)
        except Exception:
            pass

        expandable = self._get_expandable_pages(site)
        site_ctx = self._site_context_for_prompt(site)

        for parent, current_children in expandable:
            if created_count >= max_new_pages:
                break

            remaining_slots = site.max_children_per_page - current_children
            if remaining_slots <= 0:
                continue

            parent_ctx = {
                "title": parent.title,
                "slug": parent.slug,
                "depth": parent.depth,
            }

            resp = self.gpt.generate_children_for_page(
                site_context=site_ctx,
                parent_page=parent_ctx,
                remaining_slots=min(remaining_slots, max_new_pages - created_count),
            )

            for child_data in resp.get("children", []):
                if created_count >= max_new_pages:
                    break

                title = child_data.get("title") or "Page"
                child_page = parent.children.filter(title=title).first()

                # 🔒 If exists and locked, skip
                if child_page is not None and getattr(child_page, "is_locked", False):
                    continue

                # Create if missing
                if child_page is None:
                    child_page = Page(
                        site=site,
                        parent=parent,
                        depth=parent.depth + 1,
                        title=title,
                    )

                draft = {
                    "meta_title": (child_data.get("meta_title") or "")[:255],
                    "meta_description": (child_data.get("meta_description") or "")[:512],
                    "focus_keyword": (child_data.get("focus_keyword") or "")[:255],
                    "body_html": (child_data.get("body_html") or ""),
                }

                # Editor pass (best-effort)
                try:
                    page_ctx = {
                        "title": child_page.title,
                        "slug": child_page.slug or "",
                        "depth": child_page.depth,
                        "is_root": False,
                    }
                    refined = self.gpt.refine_page_content(site_context=site_ctx, page=page_ctx, draft=draft)
                    if isinstance(refined, dict) and refined.get("body_html"):
                        draft = {
                            "meta_title": (refined.get("meta_title") or draft["meta_title"])[:255],
                            "meta_description": (refined.get("meta_description") or draft["meta_description"])[:512],
                            "focus_keyword": (refined.get("focus_keyword") or draft["focus_keyword"])[:255],
                            "body_html": refined.get("body_html") or draft["body_html"],
                        }
                except Exception as e:
                    print(f"[WARN] Editor pass failed for '{child_page.title}': {e}")

                child_page.meta_title = draft["meta_title"]
                child_page.meta_description = draft["meta_description"]
                child_page.focus_keyword = draft["focus_keyword"]
                child_page.body_html = self._normalize_body_links(site, draft["body_html"])
                child_page.last_generated_at = timezone.now()
                child_page.save()
                created_count += 1

                # Hero image
                try:
                    image_gen = ImageGenerator(Path(settings.BASE_DIR) / "output" / "sites")
                    hero_context = f"Page title: {child_page.title}. Site description: {site.description}."
                    image_url = image_gen.generate_page_hero(site.slug, child_page.slug, hero_context, usage_obj=child_page, usage_action="image_hero")
                    child_page.hero_image_url = image_url
                    child_page.save(update_fields=["hero_image_url"])
                except Exception as e:
                    print(f"[WARN] Failed to generate hero image for page '{child_page.slug}': {e}")

        self._write_seo_files(site)
        return created_count

    @transaction.atomic
    def regenerate_page(self, page: Page) -> Page:
        """
        Regenerate a single page's content (overwrite meta + body_html).
        Respects is_locked.
        """
        if getattr(page, "is_locked", False):
            raise ValueError("Page is locked and cannot be regenerated.")

        site = page.site
        self.gpt.set_billing(page, "regenerate_page")
        site_ctx = self._site_context_for_prompt(site)

        parent_ctx = None
        if page.parent:
            parent_ctx = {
                "title": page.parent.title,
                "slug": page.parent.slug,
                "depth": page.parent.depth,
            }

        page_ctx = {
            "id": page.id,
            "title": page.title,
            "slug": page.slug,
            "depth": page.depth,
            "is_root": bool(getattr(page, "is_root", False)),
        }

        data = self.gpt.regenerate_page_content(
            site_context=site_ctx,
            page=page_ctx,
            parent_page=parent_ctx,
        )

        # Optional editor pass (best-effort)
        try:
            data = self.gpt.refine_page_content(site_context=site_ctx, page=page_ctx, draft={
                "meta_title": data.get("meta_title", ""),
                "meta_description": data.get("meta_description", ""),
                "focus_keyword": data.get("focus_keyword", ""),
                "body_html": data.get("body_html", ""),
            })
        except Exception as e:
            print(f"[WARN] Editor pass failed during regenerate for '{page.slug}': {e}")

        page.meta_title = (data.get("meta_title") or "")[:255]
        page.meta_description = (data.get("meta_description") or "")[:512]
        page.focus_keyword = (data.get("focus_keyword") or "")[:255]
        page.body_html = self._normalize_body_links(site, data.get("body_html") or "")
        page.last_generated_at = timezone.now()
        page.save()

        try:
            image_gen = ImageGenerator(Path(settings.BASE_DIR) / "output" / "sites")
            hero_context = f"Page title: {page.title}. Site description: {site.description}."
            image_url = image_gen.generate_page_hero(site.slug, page.slug, hero_context)
            page.hero_image_url = image_url
            page.save(update_fields=["hero_image_url"])
        except Exception as e:
            print(f"[WARN] Failed to generate hero image for page '{page.slug}': {e}")

        self._write_seo_files(site)
        return page

    def fill_missing_content(self, site: Site, limit: int = 50) -> int:
        """
        Generate content for pages that exist but have blank/empty body_html.
        Does NOT create new pages. Safe when structure is locked.
        """
        updated = 0
        site_ctx = self._site_context_for_prompt(site)

        # Define "empty" as None, "", or whitespace, or very short
        self.gpt.set_billing(site, "fill_content")
        qs = site.pages.all().order_by("depth", "nav_order", "id")
        for page in qs:
            if updated >= limit:
                break

            if getattr(page, "is_locked", False):
                continue

            body = (page.body_html or "").strip()
            if body and len(body) > 50:
                continue  # already has content

            parent_ctx = None
            if page.parent:
                parent_ctx = {
                    "title": page.parent.title,
                    "slug": page.parent.slug,
                    "depth": page.parent.depth,
                }

            page_ctx = {
                "id": page.id,
                "title": page.title,
                "slug": page.slug,
                "depth": page.depth,
                "is_root": bool(getattr(page, "is_root", False)),
            }

            try:
                data = self.gpt.regenerate_page_content(
                    site_context=site_ctx,
                    page=page_ctx,
                    parent_page=parent_ctx,
                )

                # Optional editor pass (best-effort)
                try:
                    data = self.gpt.refine_page_content(site_context=site_ctx, page=page_ctx, draft={
                        "meta_title": data.get("meta_title", ""),
                        "meta_description": data.get("meta_description", ""),
                        "focus_keyword": data.get("focus_keyword", ""),
                        "body_html": data.get("body_html", ""),
                    })
                except Exception:
                    pass

                page.meta_title = (data.get("meta_title") or "")[:255]
                page.meta_description = (data.get("meta_description") or "")[:512]
                page.focus_keyword = (data.get("focus_keyword") or "")[:255]
                page.body_html = self._normalize_body_links(site, data.get("body_html") or "")
                page.last_generated_at = timezone.now()
                page.save()

                updated += 1
            except Exception as e:
                print(f"[WARN] fill_missing_content failed for '{page.slug}': {e}")

        return updated
