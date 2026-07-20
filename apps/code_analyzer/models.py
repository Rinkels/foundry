from __future__ import annotations

from django.db import models
from django.utils import timezone


class ScanRun(models.Model):
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    root_path = models.CharField(max_length=512)
    large_loc_threshold = models.PositiveIntegerField(default=50)

    # Summary stats (portfolio-level)
    total_projects = models.PositiveIntegerField(default=0)
    total_components = models.PositiveIntegerField(default=0)

    duplicate_names_count = models.PositiveIntegerField(default=0)
    large_components_count = models.PositiveIntegerField(default=0)

    security_findings_count = models.PositiveIntegerField(default=0)
    security_high_count = models.PositiveIntegerField(default=0)

    warnings_count = models.PositiveIntegerField(default=0)

    duration_ms = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"ScanRun #{self.id} @ {self.created_at:%Y-%m-%d %H:%M:%S}"


class ScannedProject(models.Model):
    scan_run = models.ForeignKey(ScanRun, on_delete=models.CASCADE, related_name="projects")

    name = models.CharField(max_length=200, db_index=True)
    path = models.CharField(max_length=700)
    project_type = models.CharField(max_length=80, blank=True, default="")

    # Per-project counts (optional but handy)
    components_count = models.PositiveIntegerField(default=0)
    security_findings_count = models.PositiveIntegerField(default=0)
    security_high_count = models.PositiveIntegerField(default=0)
    warnings_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["scan_run", "name"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.project_type})"


class ScanItem(models.Model):
    """
    One row per component OR finding OR warning.
    """
    SEVERITY_CHOICES = [
        ("", "—"),
        ("LOW", "LOW"),
        ("MED", "MED"),
        ("HIGH", "HIGH"),
    ]

    scan_project = models.ForeignKey(ScannedProject, on_delete=models.CASCADE, related_name="items")

    bucket = models.CharField(max_length=40, db_index=True)   # models/views/security/warnings/etc
    kind = models.CharField(max_length=30, blank=True, default="", db_index=True)  # function/class/security/warning
    severity = models.CharField(max_length=6, blank=True, default="", choices=SEVERITY_CHOICES, db_index=True)

    name = models.CharField(max_length=500)  # function name OR "[HIGH] ..." message
    file = models.CharField(max_length=700, db_index=True)
    lineno = models.PositiveIntegerField(null=True, blank=True)
    loc = models.PositiveIntegerField(null=True, blank=True)

    # Useful for filtering/UX
    is_duplicate_name = models.BooleanField(default=False, db_index=True)
    is_large = models.BooleanField(default=False, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["scan_project", "bucket"]),
            models.Index(fields=["scan_project", "kind"]),
            models.Index(fields=["scan_project", "severity"]),
        ]

    def __str__(self) -> str:
        return f"{self.bucket}:{self.name}"
