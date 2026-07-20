from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class GitHubInstallation(models.Model):
    """A GitHub App installation (one per org/user that installed the Atlas App)."""

    installation_id = models.BigIntegerField(unique=True)
    account_login = models.CharField(max_length=200, blank=True, default="")
    account_type = models.CharField(max_length=40, blank=True, default="")  # User / Organization

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["account_login"]

    def __str__(self) -> str:
        return f"{self.account_login or 'installation'} (#{self.installation_id})"


class CloudCredential(models.Model):
    """A GCP identity used to run gcloud actions for one customer/project.

    Two isolation methods are supported via the gcloud CLI, both per-command
    (safe for concurrent deploys):

    * ``impersonate`` — run with ``--impersonate-service-account=<email>``.
      Keyless; the host identity needs ``roles/iam.serviceAccountTokenCreator``
      on the target SA. Recommended.
    * ``key_file`` — point gcloud at a service-account JSON key for that one
      invocation via ``CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE``.

    ``host`` (no credential attached) falls back to whatever identity the
    server's gcloud is logged in as — fine for internal/dev only.
    """

    METHOD_IMPERSONATE = "impersonate"
    METHOD_KEY_FILE = "key_file"
    METHOD_CHOICES = [
        (METHOD_IMPERSONATE, "Impersonate service account"),
        (METHOD_KEY_FILE, "Service account key file"),
    ]

    name = models.CharField(max_length=200, help_text="Label, e.g. the customer/org name.")
    gcp_project_id = models.CharField(
        max_length=120, blank=True, default="",
        help_text="Default GCP project for this identity (overrides global GCP_PROJECT_ID).",
    )
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default=METHOD_IMPERSONATE)

    service_account_email = models.EmailField(
        blank=True, default="", help_text="For impersonation: the SA to act as.",
    )
    key_file_path = models.CharField(
        max_length=700, blank=True, default="",
        help_text="For key_file: absolute path to the SA JSON key on the server.",
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_method_display()})"


class CloudProject(models.Model):
    """A project tracked for migration to / management in Google Cloud."""

    ORIGIN_CHOICES = [
        ("internal", "Internal (Django/React)"),
        ("loveable", "Loveable.com"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("planning", "Planning"),
        ("provisioning", "Provisioning"),
        ("deployed", "Deployed"),
        ("failed", "Failed"),
        ("archived", "Archived"),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)

    origin = models.CharField(max_length=20, choices=ORIGIN_CHOICES, default="internal")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planning")

    # Where the source code lives locally (e.g. picked up by code_analyzer) or its repo.
    source_path = models.CharField(max_length=700, blank=True, default="")
    repo_url = models.URLField(blank=True, default="")

    # GitHub App integration
    github_repo = models.CharField(
        max_length=255, blank=True, default="", db_index=True,
        help_text="owner/name — used to match incoming push webhooks.",
    )
    github_installation = models.ForeignKey(
        GitHubInstallation, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="projects",
    )
    auto_deploy = models.BooleanField(
        default=False,
        help_text="Deploy automatically on push to the deploy branch.",
    )
    deploy_branch = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Branch that triggers auto-deploy. Blank = match any branch's default.",
    )

    # GCP target
    credential = models.ForeignKey(
        CloudCredential, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="projects",
        help_text="Per-customer GCP identity. Blank = use the server's host identity.",
    )
    gcp_project_id = models.CharField(max_length=120, blank=True, default="")
    gcp_region = models.CharField(max_length=60, blank=True, default="us-central1")
    service_name = models.CharField(
        max_length=63, blank=True, default="",
        help_text="Cloud Run service name override. Blank = derived from the slug. "
                  "Set this to target an existing service (e.g. 'dealermaster').",
    )

    # Security hardening status (DEBUG off, secrets in Secret Manager, creds rotated, etc.)
    hardened = models.BooleanField(
        default=False,
        help_text="Has this project been through the production hardening pass?",
    )
    hardened_at = models.DateTimeField(null=True, blank=True)
    hardened_notes = models.TextField(blank=True, default="")

    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        # Stamp/clear hardened_at as the flag flips.
        if self.hardened and self.hardened_at is None:
            self.hardened_at = timezone.now()
        elif not self.hardened:
            self.hardened_at = None
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class CloudResource(models.Model):
    """A single provisioned (or planned) GCP resource belonging to a CloudProject."""

    RESOURCE_TYPES = [
        ("cloud_run", "Cloud Run service"),
        ("cloud_sql", "Cloud SQL instance"),
        ("storage_bucket", "Cloud Storage bucket"),
        ("secret", "Secret Manager secret"),
        ("artifact_repo", "Artifact Registry repo"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("planned", "Planned"),
        ("provisioning", "Provisioning"),
        ("active", "Active"),
        ("error", "Error"),
        ("deleted", "Deleted"),
    ]

    cloud_project = models.ForeignKey(CloudProject, on_delete=models.CASCADE, related_name="resources")

    resource_type = models.CharField(max_length=30, choices=RESOURCE_TYPES)
    name = models.CharField(max_length=200)
    identifier = models.CharField(max_length=500, blank=True, default="")  # full resource name / URL

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planned")
    config = models.JSONField(blank=True, default=dict)

    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["cloud_project", "resource_type", "name"]
        indexes = [
            models.Index(fields=["cloud_project", "resource_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_resource_type_display()}: {self.name}"


class DeploymentRun(models.Model):
    """A log entry for a provisioning/deploy/migration/monitoring action."""

    ACTION_CHOICES = [
        ("provision", "Provision"),
        ("pull", "Pull source"),
        ("deploy", "Deploy"),
        ("migrate", "Migrate"),
        ("sync_status", "Sync status"),
        ("teardown", "Teardown"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    cloud_project = models.ForeignKey(CloudProject, on_delete=models.CASCADE, related_name="runs")

    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    log = models.TextField(blank=True, default="")

    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["cloud_project", "-started_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_action_display()} #{self.pk} ({self.status})"
