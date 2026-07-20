from django.contrib import admin
from .models import NewsletterSeries, NewsletterIssue


@admin.register(NewsletterSeries)
class NewsletterSeriesAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")


@admin.register(NewsletterIssue)
class NewsletterIssueAdmin(admin.ModelAdmin):
    list_display = ("title", "series", "issue_number", "status", "published_at", "updated_at")
    list_filter = ("status", "series")
    search_fields = ("title", "subject", "series__name", "series__slug")
    autocomplete_fields = ("series",)
    ordering = ("-published_at", "-created_at")
