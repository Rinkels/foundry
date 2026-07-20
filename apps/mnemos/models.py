from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class FileAsset(models.Model):
    file = models.FileField(upload_to="mnemos/%Y/%m/")
    original_name = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["original_name"]),
        ]

    def __str__(self) -> str:
        return self.original_name or (self.file.name if self.file else f"FileAsset #{self.pk}")


class FileAttachment(models.Model):
    file_asset = models.ForeignKey(FileAsset, on_delete=models.CASCADE, related_name="attachments")

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    label = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self) -> str:
        base = self.label or "Attachment"
        name = self.file_asset.original_name if self.file_asset_id else ""
        return f"{base}: {name}".strip(": ")


class AiArtifact(models.Model):
    ARTIFACT_TYPES = [
        ("analysis", "Analysis"),
        ("summary", "Summary"),
        ("extraction", "Extraction"),
    ]

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    artifact_type = models.CharField(max_length=32, choices=ARTIFACT_TYPES, default="analysis")
    title = models.CharField(max_length=255, blank=True)

    prompt = models.TextField(blank=True)
    output_text = models.TextField()

    model = models.CharField(max_length=80, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    attachments = models.ManyToManyField(
        "mnemos.FileAttachment",
        blank=True,
        related_name="ai_artifacts",
    )

    usage_event_id = models.BigIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["artifact_type", "-created_at"]),
        ]

    def __str__(self) -> str:
        return self.title or f"{self.get_artifact_type_display()} #{self.pk}"
