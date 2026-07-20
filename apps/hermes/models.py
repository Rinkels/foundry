from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class NewsletterSeries(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)

    description = models.TextField(blank=True)
    from_name = models.CharField(max_length=200, blank=True)
    from_email = models.EmailField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:220]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class NewsletterIssue(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    series = models.ForeignKey(NewsletterSeries, on_delete=models.CASCADE, related_name="issues")

    title = models.CharField(max_length=240)
    issue_number = models.PositiveIntegerField(default=1)

    subject = models.CharField(max_length=240, blank=True)
    preheader = models.CharField(max_length=300, blank=True)

    slug = models.SlugField(max_length=260, blank=True)
    body_md = models.TextField(help_text="Markdown content for the issue.")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("series", "issue_number")]
        ordering = ["-published_at", "-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = f"issue-{self.issue_number:03d}-{self.title}"
            self.slug = slugify(base)[:260]
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.series.slug} #{self.issue_number:03d} - {self.title}"
