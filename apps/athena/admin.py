# apps/athena/admin.py
from django.contrib import admin
from .models import PromptTemplate, PromptVersion, PromptVariable, PromptTestCase, PromptRun


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "role", "status", "consumer", "updated_at")
    list_editable = ("role",)
    search_fields = ("name", "key", "description", "tags")
    list_filter = ("status", "consumer", "role")


@admin.register(PromptVersion)
class PromptVersionAdmin(admin.ModelAdmin):
    list_display = ("template", "version", "created_at", "created_by", "changelog")
    search_fields = ("template__key", "template__name", "body")
    list_filter = ("template",)


@admin.register(PromptVariable)
class PromptVariableAdmin(admin.ModelAdmin):
    list_display = ("template", "name", "var_type", "required")
    search_fields = ("template__key", "name")


@admin.register(PromptTestCase)
class PromptTestCaseAdmin(admin.ModelAdmin):
    list_display = ("template", "name", "created_at")
    search_fields = ("template__key", "name")
    list_filter = ("template",)


@admin.register(PromptRun)
class PromptRunAdmin(admin.ModelAdmin):
    list_display = ("template", "version", "test_case", "status", "created_at", "created_by")
    search_fields = ("template__key", "output_text")
    list_filter = ("status", "template")

# apps/athena/admin.py (add to PromptTemplateAdmin)
from django.contrib import admin, messages
from apps.athena.services.runtime import approve_current_version

@admin.action(description="Approve current version (set as canonical)")
def action_approve_current(modeladmin, request, queryset):
    count = 0
    for t in queryset:
        try:
            approve_current_version(t.key)
            count += 1
        except Exception as e:
            messages.error(request, f"Failed to approve {t.key}: {e}")
    if count:
        messages.success(request, f"Approved {count} prompt(s).")

@admin.action(description="Mark as deprecated")
def action_deprecate(modeladmin, request, queryset):
    updated = queryset.update(status="deprecated")
    messages.success(request, f"Deprecated {updated} prompt(s).")


# inside PromptTemplateAdmin:
actions = [action_approve_current, action_deprecate]


# apps/athena/admin.py (append)

from .models import AthenaModelSettings, AthenaThread, AthenaMessage, AthenaStudioRun

@admin.register(AthenaModelSettings)
class AthenaModelSettingsAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "model", "temperature", "max_tokens", "is_default")
    list_filter = ("provider", "is_default")
    search_fields = ("name", "model")


@admin.register(AthenaThread)
class AthenaThreadAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "updated_at")
    search_fields = ("title",)


@admin.register(AthenaMessage)
class AthenaMessageAdmin(admin.ModelAdmin):
    list_display = ("thread", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("content",)


@admin.register(AthenaStudioRun)
class AthenaStudioRunAdmin(admin.ModelAdmin):
    list_display = ("thread", "template", "version", "ok", "created_at")
    list_filter = ("ok", "template")

from django.utils import timezone
from django.contrib import admin
from .models import AppContextSnapshot

@admin.action(description="Approve selected snapshots")
def approve_snapshots(modeladmin, request, queryset):
    queryset.update(is_approved=True, approved_at=timezone.now(), approved_by=request.user)

@admin.register(AppContextSnapshot)
class AppContextSnapshotAdmin(admin.ModelAdmin):
    list_display = ("title", "key", "version", "is_approved", "created_at")
    list_filter = ("is_approved", "source")
    search_fields = ("title", "key", "app_path")
    actions = [approve_snapshots]
    readonly_fields = ("version", "created_at", "approved_at", "approved_by")


# --- Athena → Claude Code context export (Phase 1) ---
from .models import ContextExport


@admin.register(ContextExport)
class ContextExportAdmin(admin.ModelAdmin):
    list_display = ("id", "kind", "target_path", "bytes_written", "sha256_short", "snapshot", "created_by", "created_at")
    list_filter = ("kind", "created_at")
    search_fields = ("target_path", "sha256", "snapshot__key")
    readonly_fields = ("snapshot", "studio_run", "kind", "target_path", "bytes_written", "sha256", "created_by", "created_at")

    @admin.display(description="sha256")
    def sha256_short(self, obj):
        return (obj.sha256 or "")[:12]


# --- Athena → Claude Code agent invocation (Phase 2) ---
from .models import AgentRun


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "template", "version", "snapshot", "branch",
                    "exit_code", "cost_usd", "triggered_by", "started_at")
    list_filter = ("status", "started_at", "template")
    search_fields = ("branch", "target_path", "brief_path", "base_commit", "result_commit")
    readonly_fields = (
        "thread", "studio_run", "template", "version", "snapshot", "context_export",
        "cloud_project", "target_path", "brief_path", "command", "log", "exit_code",
        "branch", "base_commit", "result_commit", "diff_stat",
        "input_tokens", "output_tokens", "cost_usd", "triggered_by",
        "started_at", "finished_at",
    )
