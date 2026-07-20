from __future__ import annotations

from pathlib import Path
from typing import Dict
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.utils.text import slugify

from ..models import Site
from .image_generator import ImageGenerator
from .static_builder import StaticBuilder


IMAGE_SUFFIXES = (".png", ".webp", ".jpg", ".jpeg")


def delete_site_image_asset(base_dir: Path, site_slug: str, image_url: str) -> int:
    """
    Delete a generated image and common optimized variants from a site's output folder.
    Returns the number of files removed.
    """
    if not image_url:
        return 0

    parsed = urlparse(image_url)
    relative_path = unquote(parsed.path or image_url).lstrip("/\\")
    if not relative_path.startswith("assets/"):
        return 0

    site_dir = (base_dir / site_slug).resolve()
    target = (site_dir / relative_path).resolve()
    try:
        target.relative_to(site_dir)
    except ValueError:
        return 0

    candidates = {target}
    if target.suffix.lower() in IMAGE_SUFFIXES:
        candidates.update(target.with_suffix(suffix) for suffix in IMAGE_SUFFIXES)

    removed = 0
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            candidate.unlink()
            removed += 1

    return removed


def delete_site_image_webp(base_dir: Path, site_slug: str, image_url: str) -> int:
    """
    Delete only the optimized WebP sibling for an image URL.
    """
    if not image_url:
        return 0

    parsed = urlparse(image_url)
    relative_path = unquote(parsed.path or image_url).lstrip("/\\")
    if not relative_path.startswith("assets/"):
        return 0

    site_dir = (base_dir / site_slug).resolve()
    target = (site_dir / relative_path).resolve().with_suffix(".webp")
    try:
        target.relative_to(site_dir)
    except ValueError:
        return 0

    if target.exists() and target.is_file():
        target.unlink()
        return 1
    return 0


def regenerate_site_hero_images(site: Site, *, rebuild: bool = True) -> Dict[str, object]:
    """
    Replace all page hero images for a site, clean stale optimized files, and optionally rebuild.
    """
    base_dir = Path(settings.BASE_DIR) / "output" / "sites"
    image_gen = ImageGenerator(base_dir)

    stats: Dict[str, object] = {
        "pages_seen": 0,
        "generated": 0,
        "failed": 0,
        "landing_images_generated": 0,
        "files_deleted": 0,
        "build_output": "",
    }

    for page in site.pages.all().order_by("depth", "title"):
        stats["pages_seen"] += 1
        old_image_url = page.hero_image_url

        hero_context = f"Page title: {page.title}. Site description: {site.description}."
        try:
            url = image_gen.generate_page_hero(site.slug, page.slug, hero_context)
            if old_image_url and old_image_url != url:
                stats["files_deleted"] += delete_site_image_asset(base_dir, site.slug, old_image_url)
            elif url:
                stats["files_deleted"] += delete_site_image_webp(base_dir, site.slug, url)
            page.hero_image_url = url
            if page.is_root and page.landing_sections:
                sections = page.landing_sections
                for block in sections:
                    if isinstance(block, dict) and block.get("type") == "hero":
                        old_block_image = block.get("image", "")
                        block["image"] = url
                        if old_block_image and old_block_image != url:
                            stats["files_deleted"] += delete_site_image_asset(base_dir, site.slug, old_block_image)
                        break
                page.landing_sections = sections
                page.save(update_fields=["hero_image_url", "landing_sections"])
            else:
                page.save(update_fields=["hero_image_url"])
            stats["generated"] += 1
        except Exception as e:  # noqa: BLE001
            stats["failed"] += 1
            print(f"[WARN] Failed to regenerate hero image for page '{page.slug}': {e}")

    root = site.pages.filter(is_root=True).first()
    if root and root.landing_sections:
        sections = root.landing_sections
        changed = False
        for block in sections:
            if not isinstance(block, dict) or block.get("type") != "cards":
                continue
            for item in block.get("items", []) or []:
                if not isinstance(item, dict) or item.get("icon"):
                    continue
                old_image_url = item.get("image", "")
                title = item.get("title") or "item"
                text = item.get("text") or ""
                slug = "card-" + (slugify(title)[:40] or "item")
                card_context = f"{title}. {text}. For the site '{site.name}'. Site description: {site.description}."
                try:
                    url = image_gen.generate_page_hero(site.slug, slug, card_context)
                    if old_image_url and old_image_url != url:
                        stats["files_deleted"] += delete_site_image_asset(base_dir, site.slug, old_image_url)
                    elif url:
                        stats["files_deleted"] += delete_site_image_webp(base_dir, site.slug, url)
                    item["image"] = url
                    stats["landing_images_generated"] += 1
                    changed = True
                except Exception as e:  # noqa: BLE001
                    stats["failed"] += 1
                    print(f"[WARN] Failed to regenerate card image '{slug}': {e}")
        if changed:
            root.landing_sections = sections
            root.save(update_fields=["landing_sections"])

    if rebuild:
        out_dir = StaticBuilder().build_site(site)
        stats["build_output"] = str(out_dir)

    return stats
