from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.html import format_html

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "priority",
        "due_date",
        "assigned_to",
        "related_badge",
        "related_link",
        "created_at",
    )
    list_filter = ("status", "priority", "due_date", "assigned_to", "related_content_type")
    search_fields = ("title", "description", "assigned_to__username", "assigned_to__email")
    ordering = ("-created_at",)

    # Editing ergonomics
    autocomplete_fields = ("assigned_to",)
    raw_id_fields = ("related_content_type",)  # makes ContentType selection usable

    fieldsets = (
        (None, {"fields": ("title", "status", "priority", "due_date", "assigned_to")}),
        ("Details", {"fields": ("description",)}),
        ("Attach to object (optional)", {"fields": ("related_content_type", "related_object_id")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # avoid N+1 on assigned_to + related_content_type
        return qs.select_related("assigned_to", "related_content_type")

    @admin.display(description="Related type")
    def related_badge(self, obj: Task):
        if not obj.related_content_type_id:
            return "—"
        # e.g. "code_analyzer | scannedproject"
        return f"{obj.related_content_type.app_label} | {obj.related_content_type.model}"

    @admin.display(description="Related object")
    def related_link(self, obj: Task):
        """
        Tries to link to the admin change page for the related object.
        Falls back to a plain label if not resolvable.
        """
        if not obj.related_content_type_id or not obj.related_object_id:
            return "—"

        ct: ContentType = obj.related_content_type
        model_class = ct.model_class()
        if model_class is None:
            return f"{ct.app_label}.{ct.model} #{obj.related_object_id}"

        # Build the admin URL: admin:<app_label>_<model>_change
        url_name = f"admin:{ct.app_label}_{ct.model}_change"
        try:
            url = reverse(url_name, args=[obj.related_object_id])
        except Exception:
            return f"{ct.app_label}.{ct.model} #{obj.related_object_id}"

        # Try to fetch a friendly label (safe-ish; may 404 if object removed)
        try:
            related_obj = model_class.objects.get(pk=obj.related_object_id)
            label = str(related_obj)
        except Exception:
            label = f"{ct.app_label}.{ct.model} #{obj.related_object_id}"

        return format_html('<a href="{}">{}</a>', url, label)
