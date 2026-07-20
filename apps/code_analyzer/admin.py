from django.contrib import admin
from .models import ScanRun, ScannedProject, ScanItem


@admin.register(ScanRun)
class ScanRunAdmin(admin.ModelAdmin):
    list_display = (
        "id", "created_at", "root_path",
        "total_projects", "total_components",
        "security_findings_count", "security_high_count",
        "warnings_count", "duration_ms"
    )
    list_filter = ("created_at",)
    search_fields = ("root_path",)


@admin.register(ScannedProject)
class ScannedProjectAdmin(admin.ModelAdmin):
    list_display = (
        "id", "scan_run", "name", "project_type",
        "components_count", "security_findings_count", "warnings_count",
    )
    list_filter = ("project_type",)
    search_fields = ("name", "path")
    raw_id_fields = ("scan_run",)


@admin.register(ScanItem)
class ScanItemAdmin(admin.ModelAdmin):
    list_display = (
        "id", "scan_project", "bucket", "kind", "severity",
        "name", "file", "lineno", "loc",
        "is_duplicate_name", "is_large",
    )
    list_filter = ("bucket", "kind", "severity", "is_duplicate_name", "is_large")
    search_fields = ("name", "file")
    raw_id_fields = ("scan_project",)
