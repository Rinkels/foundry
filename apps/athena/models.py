# apps/athena/models.py
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class PromptStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    APPROVED = "approved", "Approved"
    DEPRECATED = "deprecated", "Deprecated"


class PromptConsumer(models.TextChoices):
    GENERAL = "general", "General"
    JANUS = "janus", "Janus"
    OKR = "okr", "OKR"
    SITES = "sites", "Site Builder"
    CODE = "code", "Code Analyzer"


class PromptRole(models.TextChoices):
    """
    Functional slot a prompt fills in the Studio pipeline. Replaces the old
    fuzzy key/name matching ("feature-designer" in key) with an explicit field.
    """
    NONE = "none", "None"
    FEATURE_DESIGNER = "feature_designer", "Feature Designer"
    APP_BUILDER = "app_builder", "App Builder"
    IMPL_GENERATOR = "impl_generator", "Implementation Generator"


class PromptTemplate(models.Model):
    key = models.SlugField(max_length=120, unique=True, help_text="Stable key used by other modules, e.g. janus_gate_summary")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=PromptStatus.choices, default=PromptStatus.DRAFT)
    consumer = models.CharField(max_length=24, choices=PromptConsumer.choices, default=PromptConsumer.GENERAL)
    role = models.CharField(
        max_length=32,
        choices=PromptRole.choices,
        default=PromptRole.NONE,
        db_index=True,
        help_text="Functional slot in the Studio pipeline (feature designer, app builder, impl generator).",
    )
    tags = models.CharField(max_length=300, blank=True, help_text="Comma-separated tags (MVP)")

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="athena_prompts")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    approved_version = models.ForeignKey("PromptVersion", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    current_version = models.ForeignKey("PromptVersion", null=True, blank=True, on_delete=models.SET_NULL, related_name="as_current_for")

    def __str__(self) -> str:
        return f"{self.name} ({self.key})"


class VarType(models.TextChoices):
    TEXT = "text", "Text"
    NUMBER = "number", "Number"
    BOOL = "bool", "Boolean"
    JSON = "json", "JSON"


class PromptVariable(models.Model):
    template = models.ForeignKey(PromptTemplate, on_delete=models.CASCADE, related_name="variables")
    name = models.SlugField(max_length=80, help_text="Variable name used in prompt, e.g. project_name")
    var_type = models.CharField(max_length=16, choices=VarType.choices, default=VarType.TEXT)
    required = models.BooleanField(default=True)
    default_value = models.TextField(blank=True)

    help_text = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("template", "name")]

    def __str__(self) -> str:
        return f"{self.template.key}.{self.name}"


class PromptVersion(models.Model):
    template = models.ForeignKey(PromptTemplate, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()

    # Structured blocks (MVP keeps these as plain text fields)
    goal = models.TextField(blank=True)
    context = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    output_contract = models.TextField(blank=True, help_text="Expected output shape, JSON schema, headings, etc.")
    tone = models.TextField(blank=True)
    guardrails = models.TextField(blank=True)

    # Rendered prompt body (optional: you can generate it from blocks; for MVP keep it explicit)
    body = models.TextField(blank=True, help_text="The actual prompt template text. Use {{ var_name }} placeholders.")

    changelog = models.CharField(max_length=300, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="athena_versions")
    created_at = models.DateTimeField(default=timezone.now)
    auto_compose = models.BooleanField(default=True, help_text="If enabled, body is composed from structured fields.")


    class Meta:
        unique_together = [("template", "version")]
        ordering = ["-version"]

    def __str__(self) -> str:
        return f"{self.template.key}@v{self.version}"

    def save(self, *args, **kwargs):
        if self.auto_compose:
            from apps.athena.services.composer import compose_body  # local import avoids cycles
            self.body = compose_body(self)
        super().save(*args, **kwargs)

class PromptTestCase(models.Model):
    template = models.ForeignKey(PromptTemplate, on_delete=models.CASCADE, related_name="test_cases")
    name = models.CharField(max_length=200)
    input_json = models.JSONField(default=dict)

    # MVP checks (expand later)
    require_substrings = models.JSONField(default=list, blank=True)  # list[str]
    require_json = models.BooleanField(default=False)  # if true, output must parse as JSON

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.template.key} :: {self.name}"


class RunStatus(models.TextChoices):
    PASS = "pass", "Pass"
    FAIL = "fail", "Fail"


class PromptRun(models.Model):
    template = models.ForeignKey(PromptTemplate, on_delete=models.CASCADE, related_name="runs")
    version = models.ForeignKey(PromptVersion, on_delete=models.PROTECT, related_name="runs")
    test_case = models.ForeignKey(PromptTestCase, null=True, blank=True, on_delete=models.SET_NULL, related_name="runs")

    rendered_prompt = models.TextField(blank=True)
    output_text = models.TextField(blank=True)

    status = models.CharField(max_length=8, choices=RunStatus.choices, default=RunStatus.PASS)
    check_results = models.JSONField(default=dict, blank=True)  # {check_name: {pass: bool, detail: str}}

    rating = models.PositiveSmallIntegerField(null=True, blank=True)  # 1-5
    notes = models.TextField(blank=True)

    model_name = models.CharField(max_length=80, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="athena_runs")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

# apps/athena/models.py (append near bottom)

from django.db import models
from django.conf import settings
from django.utils import timezone


class LLMProviderType(models.TextChoices):
    ECHO = "echo", "Echo (dev)"
    OPENAI = "openai", "OpenAI"
    ANTHROPIC = "anthropic", "Anthropic (Claude)"
    AZURE_OPENAI = "azure_openai", "Azure OpenAI"
    LOCAL = "local", "Local"


class AthenaModelSettings(models.Model):
    """
    Saved model configs (like a 'connection profile' + tuning).
    """
    name = models.CharField(max_length=120, unique=True)
    provider = models.CharField(max_length=24, choices=LLMProviderType.choices, default=LLMProviderType.ECHO)

    model = models.CharField(max_length=80, blank=True, help_text="e.g. gpt-4.1-mini (or Azure deployment name)")
    temperature = models.FloatField(default=0.2)
    max_tokens = models.PositiveIntegerField(default=800)
    top_p = models.FloatField(default=1.0)
    frequency_penalty = models.FloatField(default=0.0)
    presence_penalty = models.FloatField(default=0.0)

    # For provider-specific extras (endpoint, api_version, deployment, etc.)
    extra = models.JSONField(default=dict, blank=True)

    is_default = models.BooleanField(default=False)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Athena Model Settings"
        verbose_name_plural = "Athena Model Settings"

    def __str__(self) -> str:
        return f"{self.name} ({self.provider})"


# apps/athena/models.py

class AthenaThread(models.Model):
    MODE_ENHANCEMENT = "enhancement"
    MODE_NEW_APP = "new_app"
    MODE_CHOICES = [
        (MODE_ENHANCEMENT, "Enhancement"),
        (MODE_NEW_APP, "New App"),
    ]

    title = models.CharField(max_length=200, default="New Thread")
    last_design_doc = models.TextField(blank=True, default="")

    # ✅ NEW: persist Studio UI selections per thread
    mode = models.CharField(max_length=32, choices=MODE_CHOICES, default=MODE_ENHANCEMENT)
    ui_state = models.JSONField(default=dict, blank=True)  # {prompt_id, snapshot_id, settings_id, approved_only}

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title


class AthenaMessageRole(models.TextChoices):
    SYSTEM = "system", "System"
    USER = "user", "User"
    ASSISTANT = "assistant", "Assistant"


class AthenaMessage(models.Model):
    thread = models.ForeignKey(AthenaThread, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=16, choices=AthenaMessageRole.choices)
    content = models.TextField()

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.thread_id}:{self.role}"


class AthenaStudioRun(models.Model):
    """
    One execution: prompt version + inputs + model settings -> assistant output.
    """
    thread = models.ForeignKey(AthenaThread, on_delete=models.CASCADE, related_name="runs")
    template = models.ForeignKey("PromptTemplate", on_delete=models.PROTECT, related_name="studio_runs")
    version = models.ForeignKey("PromptVersion", on_delete=models.PROTECT, related_name="studio_runs")
    model_settings = models.ForeignKey(AthenaModelSettings, null=True, blank=True, on_delete=models.SET_NULL)

    inputs_json = models.JSONField(default=dict, blank=True)
    rendered_prompt = models.TextField(blank=True)
    response_text = models.TextField(blank=True)

    ok = models.BooleanField(default=True)
    error = models.TextField(blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

# apps/athena/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone


class AppContextSnapshot(models.Model):
    """
    Versioned, diff-friendly snapshot of an app/project extracted by Code Analyzer.
    This becomes the canonical 'app_description' input for Athena prompts.
    """
    key = models.SlugField(max_length=80, db_index=True, help_text="Stable key e.g. nurbai_produce")
    title = models.CharField(max_length=160, help_text="Human name e.g. Nurbai Produce App")
    app_path = models.CharField(max_length=300, help_text="Filesystem path e.g. /nurbai/apps/produce")

    version = models.PositiveIntegerField(default=1, help_text="Monotonic version per key")
    source = models.CharField(max_length=40, default="code_analyzer")

    # Structured facts from analyzer (diffable)
    snapshot_json = models.JSONField(default=dict, blank=True)

    # Optional: rendered human-readable canonical description (Markdown)
    description_md = models.TextField(blank=True)

    # Governance
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="athena_approved_snapshots")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="athena_snapshots")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("key", "version")]
        indexes = [
            models.Index(fields=["key", "version"]),
            models.Index(fields=["key", "is_approved"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} v{self.version} ({'approved' if self.is_approved else 'draft'})"


class ContextExport(models.Model):
    """Audit record of an Athena context / design-doc export into a target repo's
    working tree. Follows the field conventions of atlas.DeploymentRun — one row
    per successful export, immutable."""

    KIND_CONTEXT = "context"
    KIND_DESIGN_DOC = "design_doc"
    KIND_CHOICES = [
        (KIND_CONTEXT, "Context (CLAUDE.md)"),
        (KIND_DESIGN_DOC, "Design doc"),
    ]

    snapshot = models.ForeignKey(
        AppContextSnapshot, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="context_exports",
    )
    studio_run = models.ForeignKey(
        AthenaStudioRun, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="context_exports",
    )
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, default=KIND_CONTEXT)

    target_path = models.CharField(max_length=700)
    bytes_written = models.PositiveIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True, default="")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="athena_context_exports",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["snapshot", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} -> {self.target_path} ({self.sha256[:8]})"


class AgentRun(models.Model):
    """Phase 2 — a headless Claude Code run against an exported brief, in an
    isolated git worktree. The FKs ARE the point: a finished run answers, from
    stored fields alone, which prompt version / snapshot / design doc / branch /
    commits produced the code. Async lifecycle mirrors atlas.DeploymentRun."""

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    # --- provenance chain ---
    thread = models.ForeignKey(AthenaThread, on_delete=models.CASCADE, related_name="agent_runs")
    studio_run = models.ForeignKey(
        AthenaStudioRun, null=True, blank=True, on_delete=models.SET_NULL, related_name="agent_runs")
    template = models.ForeignKey("PromptTemplate", on_delete=models.PROTECT, related_name="agent_runs")
    version = models.ForeignKey("PromptVersion", on_delete=models.PROTECT, related_name="agent_runs")
    snapshot = models.ForeignKey(
        AppContextSnapshot, null=True, blank=True, on_delete=models.SET_NULL, related_name="agent_runs")
    context_export = models.ForeignKey(
        ContextExport, null=True, blank=True, on_delete=models.SET_NULL, related_name="agent_runs")

    # --- target / execution ---
    cloud_project = models.ForeignKey(
        "atlas.CloudProject", null=True, blank=True, on_delete=models.SET_NULL, related_name="agent_runs")
    target_path = models.CharField(max_length=700)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    brief_path = models.CharField(max_length=700, blank=True, default="")
    command = models.TextField(blank=True, default="")
    log = models.TextField(blank=True, default="")
    exit_code = models.IntegerField(null=True, blank=True)
    timeout_seconds = models.PositiveIntegerField(null=True, blank=True, help_text="Per-run override; blank = settings default.")

    # --- git isolation record ---
    branch = models.CharField(max_length=200, blank=True, default="")
    base_commit = models.CharField(max_length=64, blank=True, default="")
    result_commit = models.CharField(max_length=64, blank=True, default="")
    diff_stat = models.TextField(blank=True, default="")
    # Human-initiated adopt: the agent NEVER merges itself (brief), but a
    # reviewer may merge the result branch from the run detail page.
    merged_at = models.DateTimeField(null=True, blank=True)
    merged_into = models.CharField(max_length=200, blank=True, default="")
    merge_commit = models.CharField(max_length=64, blank=True, default="")

    # --- cost (best-effort, via ai_pricing) ---
    input_tokens = models.IntegerField(null=True, blank=True)
    output_tokens = models.IntegerField(null=True, blank=True)
    cost_usd = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)

    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="athena_agent_runs")
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["status", "-started_at"]),
            models.Index(fields=["thread", "-started_at"]),
        ]

    def __str__(self) -> str:
        return f"AgentRun #{self.pk} ({self.status}) on {self.branch or self.target_path}"
