"""Discover Markdown files under MD_LIBRARY_ROOTS and index them.

Read-only over the filesystem: reads each .md to pull a title + excerpt, then
upserts a MarkdownDoc per path and prunes rows whose file has vanished. User
flags (read/pinned) are preserved across rescans.
"""
from __future__ import annotations

import datetime
import os
import re
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .models import MarkdownDoc

# Directories we never descend into (noise / huge / vendored).
EXCLUDE_DIRS = {
    "node_modules", ".git", ".venv", "venv", "env", "__pycache__",
    "site-packages", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "dist", "build", ".next", ".cache", ".idea", ".vs", ".tox", "staticfiles",
}
MD_EXTS = {".md", ".markdown", ".mdx"}
_H1 = re.compile(r"^\s*#\s+(.+?)\s*#*\s*$", re.M)


def library_roots() -> list[Path]:
    roots = getattr(settings, "MD_LIBRARY_ROOTS", None) or [r"C:\Projects"]
    return [Path(r) for r in roots]


def _title_and_excerpt(text: str, fallback: str) -> tuple[str, str]:
    m = _H1.search(text)
    title = (m.group(1).strip() if m else fallback)[:300]
    parts: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("```") or s.startswith("---") or s.startswith("|"):
            continue
        parts.append(s)
        if len(" ".join(parts)) >= 220:
            break
    return title, " ".join(parts)[:400]


def scan() -> dict:
    """(Re)index every .md under the configured roots. Returns run stats."""
    seen: set[str] = set()
    added = updated = 0
    now = timezone.now()

    for root in library_roots():
        if not root.exists() or not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for fn in filenames:
                if Path(fn).suffix.lower() not in MD_EXTS:
                    continue
                fp = Path(dirpath) / fn
                try:
                    st = fp.stat()
                    text = fp.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                path = str(fp)
                seen.add(path)
                rel = fp.relative_to(root).as_posix()
                project = rel.split("/", 1)[0] if "/" in rel else (root.name or "(root)")
                title, excerpt = _title_and_excerpt(text, fp.stem)
                mtime = datetime.datetime.fromtimestamp(st.st_mtime, tz=datetime.timezone.utc)
                _, created = MarkdownDoc.objects.update_or_create(
                    path=path,
                    defaults=dict(
                        project=project, rel_path=rel, title=title, excerpt=excerpt,
                        size_bytes=st.st_size, mtime=mtime, last_indexed=now,
                    ),
                )
                added += int(created)
                updated += int(not created)

    pruned = MarkdownDoc.objects.exclude(path__in=seen).delete()[0] if seen else 0
    return {"added": added, "updated": updated, "pruned": pruned, "total": MarkdownDoc.objects.count()}
