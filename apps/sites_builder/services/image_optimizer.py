from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Dict, Tuple

from PIL import Image, ImageFile

# Prevent "image file is truncated" crashes on slightly imperfect files
ImageFile.LOAD_TRUNCATED_IMAGES = True


@dataclass
class ImageOptimizeConfig:
    # Only process these extensions (case-insensitive)
    exts: Tuple[str, ...] = (".png", ".jpg", ".jpeg")

    # WebP quality target (sweet spot for UI/illustrations)
    webp_quality: int = 82

    # Don’t waste cycles on tiny files
    min_bytes_to_process: int = 25_000  # 25 KB

    # If True, overwrite original PNG/JPG only when smaller
    replace_only_if_smaller: bool = True


def optimize_images_dir(images_dir: Path, config: ImageOptimizeConfig | None = None) -> Dict[str, int]:
    """
    Optimize raster images in-place and create .webp siblings.

    Returns stats:
      {"files_seen": X, "optimized": Y, "webp_created": Z, "bytes_saved": N}
    """
    config = config or ImageOptimizeConfig()

    stats = {"files_seen": 0, "optimized": 0, "webp_created": 0, "bytes_saved": 0}

    if not images_dir.exists():
        return stats

    for p in images_dir.rglob("*"):
        if not p.is_file():
            continue

        ext = p.suffix.lower()
        if ext not in config.exts:
            continue

        stats["files_seen"] += 1

        try:
            orig_bytes = p.stat().st_size
        except OSError:
            continue

        if orig_bytes < config.min_bytes_to_process:
            # Still create webp for consistency if missing (heroes may be small-ish)
            _ensure_webp(p, config, stats)
            continue

        if ext == ".png":
            saved = _optimize_png_in_place(p, config)
            if saved > 0:
                stats["optimized"] += 1
                stats["bytes_saved"] += saved
        else:
            saved = _optimize_jpeg_in_place(p, config)
            if saved > 0:
                stats["optimized"] += 1
                stats["bytes_saved"] += saved

        _ensure_webp(p, config, stats)

    return stats


def _ensure_webp(src_path: Path, config: ImageOptimizeConfig, stats: Dict[str, int]) -> None:
    webp_path = src_path.with_suffix(".webp")
    if webp_path.exists():
        return

    try:
        with Image.open(src_path) as im:
            im = im.convert("RGBA") if im.mode in ("P", "LA") else im

            # If no alpha, use RGB (smaller)
            if "A" in im.getbands():
                out = im
            else:
                out = im.convert("RGB")

            out.save(
                webp_path,
                format="WEBP",
                quality=config.webp_quality,
                method=6,          # best compression effort
                optimize=True,
            )
        stats["webp_created"] += 1
    except Exception:
        # Don’t fail the whole build because one image is weird
        return


def _optimize_png_in_place(path: Path, config: ImageOptimizeConfig) -> int:
    """
    Re-save PNG with optimize=True + max compression.
    Overwrites only if smaller (unless config says otherwise).
    Returns bytes saved.
    """
    try:
        before = path.stat().st_size
        with Image.open(path) as im:
            # Preserve alpha/mode; just recompress
            buf = BytesIO()
            im.save(buf, format="PNG", optimize=True, compress_level=9)
            new_bytes = buf.getvalue()

        after = len(new_bytes)
        if config.replace_only_if_smaller and after >= before:
            return 0

        path.write_bytes(new_bytes)
        return max(0, before - after)
    except Exception:
        return 0


def _optimize_jpeg_in_place(path: Path, config: ImageOptimizeConfig) -> int:
    """
    Re-save JPEG with optimize/progressive.
    Returns bytes saved.
    """
    try:
        before = path.stat().st_size
        with Image.open(path) as im:
            im = im.convert("RGB")
            buf = BytesIO()
            im.save(buf, format="JPEG", optimize=True, progressive=True, quality=85)
            new_bytes = buf.getvalue()

        after = len(new_bytes)
        if config.replace_only_if_smaller and after >= before:
            return 0

        path.write_bytes(new_bytes)
        return max(0, before - after)
    except Exception:
        return 0
