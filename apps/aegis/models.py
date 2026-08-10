"""Aegis — public-exposure monitoring for Iris tenants.

Answers one question for a customer we're about to migrate (or already run):
*what is publicly visible on GitHub about this app right now?*

Three models:
    WatchProfile — what to watch, for whom (the tenant boundary).
    WatchRun     — one execution of a sweep.
    Exposure     — a deduplicated finding, with lifecycle.

Deliberately **never stores a raw secret** — only a redacted preview and a
fingerprint. See services/detect.py.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def _split_lines(raw: str) -> list[str]:
    """Newline/comma separated textarea -> clean list."""
    out = []
    for chunk in raw.replace(",", "\n").splitlines():
        chunk = chunk.strip()
        if chunk and chunk not in out:
            out.append(chunk)
    return out


class WatchProfile(models.Model):
    """What we watch on behalf of one tenant.

    Scope is the union of `github_orgs` and `github_repos`. Keywords are
    tenant-specific strings (company name, internal domains, project
    codenames) that produce `info`-level brand hits on their own, and raise
    the confidence of a credential hit found alongside them.
    """

    name = models.CharField(max_length=200, help_text="Usually the customer/org name.")
    slug = models.SlugField(max_length=200, unique=True, blank=True)

    # Tenant boundary — mirrors how Atlas isolates customers.
    credential = models.ForeignKey(
        "atlas.CloudCredential", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="watch_profiles",
        help_text="The Atlas customer this profile belongs to.",
    )
    cloud_project = models.ForeignKey(
        "atlas.CloudProject", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="watch_profiles",
        help_text="Optional: the specific app this exposure check covers.",
    )
    github_installation = models.ForeignKey(
        "atlas.GitHubInstallation", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="watch_profiles",
        help_text="Use this installation's token for API calls. "
                  "Falls back to settings.AEGIS_GITHUB_TOKEN.",
    )

    # Scope
    github_orgs = models.TextField(
        blank=True, default="",
        help_text="One GitHub org/user login per line. Searches every public repo they own.",
    )
    github_repos = models.TextField(
        blank=True, default="",
        help_text="One owner/name per line, for targeted checks.",
    )
    keywords = models.TextField(
        blank=True, default="",
        help_text="One per line: company name, internal domains, project codenames.",
    )

    enabled = models.BooleanField(default=True)
    notify_email = models.EmailField(
        blank=True, default="", help_text="Where new findings are sent. Blank = no email.",
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:200]
        super().save(*args, **kwargs)

    # -- parsed accessors ---------------------------------------------------
    @property
    def org_list(self) -> list[str]:
        return _split_lines(self.github_orgs)

    @property
    def repo_list(self) -> list[str]:
        return _split_lines(self.github_repos)

    @property
    def keyword_list(self) -> list[str]:
        return _split_lines(self.keywords)

    @property
    def scope_qualifiers(self) -> list[str]:
        """GitHub code-search qualifiers restricting a query to this tenant."""
        return [f"org:{o}" for o in self.org_list] + [f"repo:{r}" for r in self.repo_list]

    @property
    def open_exposure_count(self) -> int:
        return self.exposures.filter(status__in=[Exposure.STATUS_NEW, Exposure.STATUS_TRIAGED]).count()


class WatchRun(models.Model):
    """One sweep. Keeps the log so a failed run is debuggable after the fact."""

    STATUS_RUNNING = "running"
    STATUS_OK = "ok"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_RUNNING, "Running"),
        (STATUS_OK, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    SOURCE_CODE_SEARCH = "code_search"
    SOURCE_GHARCHIVE = "gharchive"
    SOURCE_CHOICES = [
        (SOURCE_CODE_SEARCH, "GitHub code search"),
        (SOURCE_GHARCHIVE, "GH Archive stream"),
    ]

    profile = models.ForeignKey(WatchProfile, on_delete=models.CASCADE, related_name="runs")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_CODE_SEARCH)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_RUNNING)

    queries_run = models.PositiveIntegerField(default=0)
    queries_skipped = models.PositiveIntegerField(
        default=0, help_text="Dropped by the per-run query cap — surfaced, never silent.",
    )
    files_examined = models.PositiveIntegerField(default=0)
    findings_new = models.PositiveIntegerField(default=0)
    findings_seen = models.PositiveIntegerField(default=0)

    log = models.TextField(blank=True, default="")
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
    )
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.profile.name} sweep {self.started_at:%Y-%m-%d %H:%M}"

    @property
    def duration_s(self) -> float | None:
        if not self.finished_at:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    def append_log(self, line: str) -> None:
        self.log = f"{self.log}{line}\n"


class Exposure(models.Model):
    """A deduplicated public-exposure finding.

    `fingerprint` is a hash of (repo, path, detector, hash-of-matched-value), so
    the same leaked key in the same place collapses to one row across runs,
    while a *rotated* key in that spot correctly opens a new one.
    """

    SEV_CRITICAL = "critical"
    SEV_HIGH = "high"
    SEV_MEDIUM = "medium"
    SEV_LOW = "low"
    SEV_INFO = "info"
    SEVERITY_CHOICES = [
        (SEV_CRITICAL, "Critical"),
        (SEV_HIGH, "High"),
        (SEV_MEDIUM, "Medium"),
        (SEV_LOW, "Low"),
        (SEV_INFO, "Info"),
    ]
    SEVERITY_ORDER = {SEV_CRITICAL: 0, SEV_HIGH: 1, SEV_MEDIUM: 2, SEV_LOW: 3, SEV_INFO: 4}

    STATUS_NEW = "new"
    STATUS_TRIAGED = "triaged"
    STATUS_FALSE_POSITIVE = "false_positive"
    STATUS_RESOLVED = "resolved"
    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_TRIAGED, "Triaged"),
        (STATUS_FALSE_POSITIVE, "False positive"),
        (STATUS_RESOLVED, "Resolved"),
    ]

    profile = models.ForeignKey(WatchProfile, on_delete=models.CASCADE, related_name="exposures")
    first_run = models.ForeignKey(
        WatchRun, null=True, blank=True, on_delete=models.SET_NULL, related_name="first_findings",
    )

    fingerprint = models.CharField(max_length=64, db_index=True)

    # Where
    repo_full_name = models.CharField(max_length=300, db_index=True)
    file_path = models.CharField(max_length=700, blank=True, default="")
    url = models.URLField(max_length=900, blank=True, default="")
    source = models.CharField(
        max_length=20, choices=WatchRun.SOURCE_CHOICES, default=WatchRun.SOURCE_CODE_SEARCH,
    )

    # What
    detector = models.CharField(max_length=60, db_index=True)
    detector_label = models.CharField(max_length=200, blank=True, default="")
    severity = models.CharField(
        max_length=10, choices=SEVERITY_CHOICES, default=SEV_MEDIUM, db_index=True,
    )
    matched_keyword = models.CharField(max_length=200, blank=True, default="")
    redacted_snippet = models.CharField(
        max_length=500, blank=True, default="",
        help_text="Redacted preview. The raw secret is never persisted.",
    )
    note = models.CharField(max_length=400, blank=True, default="")

    # Lifecycle
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW, db_index=True,
    )
    first_seen = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now)
    times_seen = models.PositiveIntegerField(default=1)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["severity", "-last_seen"]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "fingerprint"], name="aegis_exposure_unique_per_profile",
            ),
        ]
        indexes = [
            models.Index(fields=["profile", "status", "severity"]),
        ]

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.detector} in {self.repo_full_name}"

    @property
    def is_open(self) -> bool:
        return self.status in (self.STATUS_NEW, self.STATUS_TRIAGED)

    @property
    def severity_badge_class(self) -> str:
        return {
            self.SEV_CRITICAL: "bg-danger",
            self.SEV_HIGH: "bg-danger",
            self.SEV_MEDIUM: "bg-warning text-dark",
            self.SEV_LOW: "bg-info",
            self.SEV_INFO: "bg-secondary",
        }.get(self.severity, "bg-secondary")

    @property
    def sort_key(self) -> int:
        return self.SEVERITY_ORDER.get(self.severity, 9)
