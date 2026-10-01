from pathlib import Path

from django.db import models


class MarkdownDoc(models.Model):
    """An index entry for a Markdown file discovered on disk under
    MD_LIBRARY_ROOTS. The FILE is the source of truth; this row is a cache that
    a rescan refreshes. Codex never edits the file — read-only discovery."""

    path = models.CharField(max_length=1000, unique=True)          # absolute path
    project = models.CharField(max_length=200, blank=True, default="", db_index=True)
    rel_path = models.CharField(max_length=1000, blank=True, default="")
    title = models.CharField(max_length=300, blank=True, default="")
    excerpt = models.TextField(blank=True, default="")
    size_bytes = models.BigIntegerField(default=0)
    mtime = models.DateTimeField(null=True, blank=True)             # file modified time
    read = models.BooleanField(default=False)
    pinned = models.BooleanField(default=False)
    last_indexed = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-pinned", "-mtime", "title"]
        indexes = [
            models.Index(fields=["project", "-mtime"]),
            models.Index(fields=["read"]),
        ]

    def __str__(self) -> str:
        return self.title or self.rel_path or self.path

    @property
    def exists(self) -> bool:
        try:
            return Path(self.path).exists()
        except Exception:
            return False

    @property
    def size_human(self) -> str:
        n = float(self.size_bytes or 0)
        for unit in ("B", "KB", "MB"):
            if n < 1024:
                return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} GB"
