from django.contrib import admin

from .models import CloudCredential, CloudProject, CloudResource, DeploymentRun, GitHubInstallation


class CloudResourceInline(admin.TabularInline):
    model = CloudResource
    extra = 0


class DeploymentRunInline(admin.TabularInline):
    model = DeploymentRun
    extra = 0
    fields = ["action", "status", "started_at", "finished_at", "triggered_by"]
    readonly_fields = ["started_at", "finished_at"]


@admin.register(CloudCredential)
class CloudCredentialAdmin(admin.ModelAdmin):
    list_display = ["name", "method", "gcp_project_id", "service_account_email", "updated_at"]
    list_filter = ["method"]
    search_fields = ["name", "gcp_project_id", "service_account_email"]


@admin.register(CloudProject)
class CloudProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "origin", "status", "github_repo", "auto_deploy", "hardened", "credential", "gcp_project_id", "updated_at"]
    list_filter = ["origin", "status", "auto_deploy", "hardened", "credential"]
    list_editable = ["auto_deploy", "hardened"]
    readonly_fields = ["hardened_at"]
    search_fields = ["name", "slug", "gcp_project_id", "source_path", "repo_url", "github_repo"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [CloudResourceInline, DeploymentRunInline]


@admin.register(GitHubInstallation)
class GitHubInstallationAdmin(admin.ModelAdmin):
    list_display = ["installation_id", "account_login", "account_type", "updated_at"]
    search_fields = ["account_login", "installation_id"]


@admin.register(CloudResource)
class CloudResourceAdmin(admin.ModelAdmin):
    list_display = ["cloud_project", "resource_type", "name", "status", "last_synced_at"]
    list_filter = ["resource_type", "status"]
    search_fields = ["name", "identifier"]


@admin.register(DeploymentRun)
class DeploymentRunAdmin(admin.ModelAdmin):
    list_display = ["cloud_project", "action", "status", "started_at", "finished_at", "triggered_by"]
    list_filter = ["action", "status"]
