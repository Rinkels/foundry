from django.contrib import admin

from .models import Initiative, InitiativeUpdate


class InitiativeUpdateInline(admin.TabularInline):
    model = InitiativeUpdate
    extra = 1
    fields = ["kind", "occurred_on", "body", "author"]
    ordering = ["-occurred_on"]


@admin.register(Initiative)
class InitiativeAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "status", "atlas_project", "site", "owner", "updated_at"]
    list_filter = ["status", "kind", "owner"]
    list_editable = ["status"]
    search_fields = ["name", "slug", "summary", "repo_url", "live_url"]
    prepopulated_fields = {"slug": ("name",)}
    raw_id_fields = ["atlas_project", "site", "owner"]
    inlines = [InitiativeUpdateInline]


@admin.register(InitiativeUpdate)
class InitiativeUpdateAdmin(admin.ModelAdmin):
    list_display = ["initiative", "kind", "occurred_on", "body", "author"]
    list_filter = ["kind", "occurred_on"]
    search_fields = ["body", "initiative__name"]
