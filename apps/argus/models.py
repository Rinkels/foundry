from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Initiative(models.Model):
    """A portfolio item — an app, website, experiment, or external project.
    May optionally link to a concrete Foundry artifact (an Atlas CloudProject or
    a Sites Builder Site), or to nothing (e.g. not-yet-in-Foundry repos)."""

    KIND_CHOICES = [
        ("app", "App"),
        ("website", "Website"),
        ("experiment", "Experiment"),
        ("tool", "Tool"),
        ("external", "External"),
    ]
    STATUS_CHOICES = [
        ("idea", "Idea"),
        ("building", "Building"),
        ("live", "Live"),
        ("paused", "Paused"),
        ("archived", "Archived"),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    summary = models.CharField(max_length=400, blank=True, default="")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="app")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="building")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="initiatives",
    )

    # Optional links to whatever backs this initiative (any / none)
    atlas_project = models.ForeignKey(
        "atlas.CloudProject", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="initiatives",
    )
    site = models.ForeignKey(
        "sites_builder.Site", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="initiatives",
    )
    repo_url = models.URLField(blank=True, default="")
    live_url = models.URLField(blank=True, default="")

    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:200]
        super().save(*args, **kwargs)

    @property
    def status_badge_class(self) -> str:
        return {
            "building": "bg-info", "live": "bg-success", "idea": "bg-secondary",
            "paused": "bg-warning text-dark", "archived": "bg-dark",
        }.get(self.status, "bg-secondary")

    @property
    def primary_url(self) -> str:
        if self.live_url:
            return self.live_url
        if self.site_id and getattr(self.site, "base_url", ""):
            return self.site.base_url
        return self.repo_url or ""


class InitiativeUpdate(models.Model):
    """A timestamped progress entry. `done` = work completed (rolls up into
    'this week'); `next` = planned/intended; `note` = general."""

    KIND_CHOICES = [("done", "Done"), ("next", "Next"), ("note", "Note")]

    initiative = models.ForeignKey(Initiative, on_delete=models.CASCADE, related_name="updates")
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default="done")
    body = models.TextField()
    occurred_on = models.DateField(default=timezone.localdate)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-occurred_on", "-created_at"]
        indexes = [models.Index(fields=["kind", "-occurred_on"])]

    def __str__(self) -> str:
        return f"{self.initiative.name}: {self.get_kind_display()} ({self.occurred_on})"
