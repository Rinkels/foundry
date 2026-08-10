from django.contrib import admin

from .models import Exposure, WatchProfile, WatchRun


@admin.register(WatchProfile)
class WatchProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "credential", "cloud_project", "enabled", "open_exposure_count", "updated_at"]
    list_filter = ["enabled", "credential"]
    list_editable = ["enabled"]
    search_fields = ["name", "slug", "github_orgs", "github_repos", "keywords"]
    prepopulated_fields = {"slug": ("name",)}
    raw_id_fields = ["credential", "cloud_project", "github_installation"]
    fieldsets = [
        (None, {"fields": ["name", "slug", "enabled", "notify_email"]}),
        ("Tenant", {"fields": ["credential", "cloud_project", "github_installation"]}),
        ("Scope", {"fields": ["github_orgs", "github_repos", "keywords"]}),
        ("Global search", {
            "fields": ["search_globally", "repo_denylist"],
            "description": "Searching all of public GitHub is the only way to catch a "
                           "leak in a repo you don't own. Pair it with a denylist — "
                           "crawler datasets match every brand keyword.",
        }),
    ]


@admin.register(WatchRun)
class WatchRunAdmin(admin.ModelAdmin):
    list_display = [
        "profile", "source", "status", "queries_run", "files_examined",
        "findings_new", "started_at", "duration_s",
    ]
    list_filter = ["status", "source", "profile"]
    readonly_fields = ["log"]
    raw_id_fields = ["profile", "triggered_by"]


@admin.register(Exposure)
class ExposureAdmin(admin.ModelAdmin):
    list_display = [
        "severity", "detector", "repo_full_name", "file_path",
        "status", "times_seen", "last_seen",
    ]
    list_filter = ["severity", "status", "detector", "profile"]
    list_editable = ["status"]
    search_fields = ["repo_full_name", "file_path", "detector", "matched_keyword", "note"]
    raw_id_fields = ["profile", "first_run"]
    readonly_fields = ["fingerprint", "redacted_snippet", "first_seen", "last_seen", "times_seen"]
    fields = [
        "profile", "first_run", "severity", "status", "triage_note",
        "detector", "detector_label", "repo_full_name", "file_path", "url",
        "matched_keyword", "note", "redacted_snippet", "fingerprint",
        "first_seen", "last_seen", "times_seen", "resolved_at",
    ]
