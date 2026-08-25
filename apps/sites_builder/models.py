from urllib.parse import urlparse

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

class Developer(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)

    def __str__(self) -> str:
        return self.name


class Site(models.Model):
    owner = models.ForeignKey(
        Developer, on_delete=models.CASCADE, related_name="sites"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=100)
    description = models.TextField(help_text="Short description used as seed for GPT.")
    domain = models.CharField(
        max_length=255,
        blank=True,
        help_text="Canonical domain, e.g. https://example.com (optional)",
    )

    # Per-site runaway protection
    max_depth = models.PositiveIntegerField(default=3)
    max_children_per_page = models.PositiveIntegerField(default=3)

    # Turbo controls
    structure_locked = models.BooleanField(default=False)
    target_page_count = models.PositiveIntegerField(default=12)

    # NEW: Store the IA/menu plan returned by GPT (audit trail / preview / diffs)
    ia_plan = models.JSONField(null=True, blank=True)
    ia_planned_at = models.DateTimeField(null=True, blank=True)
    ga4_property_id = models.CharField(max_length=32, blank=True, null=True)  # "123456789"
    # optional: store measurement id if you want to inject tracking tags too (G-XXXX)
    ga4_measurement_id = models.CharField(max_length=32, blank=True, null=True)
    # Branding / theming (v1; extend later)
    THEME_LIGHT = "light"
    THEME_DARK = "dark"
    THEME_CHOICES = [
        (THEME_LIGHT, "Light"),
        (THEME_DARK, "Dark"),
    ]
    theme = models.CharField(
        max_length=20,
        choices=THEME_CHOICES,
        default=THEME_LIGHT,
    )
    # ✅ NEW: select which source CSS file to use (builder still outputs assets/css/site.css)
    THEME_CSS_NEON = "neon_glass"
    THEME_CSS_STARTUP = "startup"
    THEME_CSS_AURORA = "aurora"
    THEME_CSS_VERDANT = "verdant"
    THEME_CSS_BAUHAUS = "bauhaus"
    THEME_CSS_EDITORIAL = "editorial"
    THEME_CSS_MINDSGATE = "mindsgate"
    THEME_CSS_HUMAINX = "humainx"
    THEME_CSS_CHOICES = [
        (THEME_CSS_NEON, "Neon Glass"),
        (THEME_CSS_STARTUP, "Startup Modern"),
        (THEME_CSS_AURORA, "Aurora"),
        (THEME_CSS_VERDANT, "Verdant"),
        (THEME_CSS_BAUHAUS, "Bauhaus"),
        (THEME_CSS_EDITORIAL, "Editorial"),
        (THEME_CSS_MINDSGATE, "Mindsgate (dark premium)"),
        (THEME_CSS_HUMAINX, "HumainX (research publication)"),
    ]

    theme_css = models.CharField(
        max_length=50,
        choices=THEME_CSS_CHOICES,
        default=THEME_CSS_NEON,
        help_text="Select the source theme stylesheet to copy into assets/css/site.css",
    )
    logo_url = models.URLField(blank=True)
    primary_color = models.CharField(max_length=20, blank=True)
    secondary_color = models.CharField(max_length=20, blank=True)

    # Optional header CTA button (e.g. "Talk to an Architect" -> contact.html)
    nav_cta_label = models.CharField(max_length=60, blank=True)
    nav_cta_url = models.CharField(max_length=255, blank=True)

    # Optional footer links (e.g. live platform logins). List of dicts:
    # [{"label": "Fracto", "href": "https://fracto.mindsgate.com", "external": true}]
    footer_links = models.JSONField(default=list, blank=True)
    newsletter_config = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Public newsletter-form configuration. Expected keys include enabled, "
            "provider, username, form_action, button_label, and success_url."
        ),
    )
    reader_feedback_config = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Public reader-feedback configuration. Expected keys include enabled, "
            "provider, form_url, and button_label. No API credentials are required."
        ),
    )
    hide_builder_credit = models.BooleanField(
        default=False,
        help_text="Hide the Mindsgate builder credit in the generated site footer.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

    def ensure_slug(self):
        if not self.slug:
            self.slug = slugify(self.name)

    def seed_top_nav_from_pages(self):
        if self.top_nav_items.exists():
            return
        roots = self.pages.filter(parent__isnull=True).order_by("nav_order", "title")[:6]
        for i, p in enumerate(roots):
            SiteTopNavItem.objects.create(
                site=self,
                label=p.title,
                url=f"{p.slug}.html",
                order=i * 10,
                is_enabled=True,
            )

    @property
    def base_url(self) -> str:
        """
        Normalized absolute base URL with scheme, e.g. https://www.mindsgate.com
        Accepts stored values like:
          - www.mindsgate.com
          - https://www.mindsgate.com
          - http://www.mindsgate.com/
        """
        raw = (self.domain or "").strip()
        if not raw:
            return ""
        if "://" not in raw:
            raw = "https://" + raw
        p = urlparse(raw)
        return f"{p.scheme}://{p.netloc}".rstrip("/")

class DeploymentTarget(models.Model):
    TYPE_FTP = "ftp"
    TYPE_LOCAL = "local"
    TYPE_CF_PAGES = "cf_pages"

    TYPE_CHOICES = [
        (TYPE_FTP, "FTP"),
        (TYPE_LOCAL, "Local folder"),
        (TYPE_CF_PAGES, "Cloudflare Pages"),
    ]

    site = models.ForeignKey(
        Site, on_delete=models.CASCADE, related_name="deployment_targets"
    )
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_FTP)

    # FTP fields
    ftp_host = models.CharField(max_length=255, blank=True)
    ftp_username = models.CharField(max_length=255, blank=True)
    ftp_password = models.CharField(max_length=255, blank=True)
    ftp_remote_root = models.CharField(
        max_length=255,
        blank=True,
        help_text="Remote root path, e.g. /public_html/myclient",
    )

    # Local folder (for copy-based deployment)
    local_path = models.CharField(
        max_length=512,
        blank=True,
        help_text="Absolute path on server to copy files to for LOCAL deployment.",
    )

    # Cloudflare Pages (wrangler-based deployment; auth via wrangler OAuth
    # login on this host, or CLOUDFLARE_API_TOKEN in the environment)
    cf_project_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Cloudflare Pages project name for CF_PAGES deployment, e.g. gym2x.",
    )

    is_default = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.site.slug} -> {self.name} ({self.type})"


class Page(models.Model):
    site = models.ForeignKey(
        Site, on_delete=models.CASCADE, related_name="pages"
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    hero_image_url = models.CharField(max_length=512, blank=True)
    depth = models.PositiveIntegerField(default=0)
    is_root = models.BooleanField(default=False)
    nav_order = models.PositiveIntegerField(
        default=0,
        help_text="Controls menu ordering. Lower comes first."
    )

    # 🔒 Lockdown / manual override
    is_locked = models.BooleanField(
        default=False,
        help_text="If set, this page will not be auto-regenerated."
    )
    manual_html = models.TextField(
        blank=True,
        null=True,
        help_text="Optional manual HTML override when the page is locked."
    )
    locked_at = models.DateTimeField(blank=True, null=True)
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="locked_pages",
    )

    # Page type: article = editorial single-column flow; landing = composed
    # marketing sections (hero/stats/features/cards/cta). Drives template + styling.
    PAGE_TYPE_ARTICLE = "article"
    PAGE_TYPE_LANDING = "landing"
    PAGE_TYPE_CHOICES = [
        (PAGE_TYPE_ARTICLE, "Article (editorial)"),
        (PAGE_TYPE_LANDING, "Landing (marketing)"),
    ]
    page_type = models.CharField(
        max_length=20, choices=PAGE_TYPE_CHOICES, default=PAGE_TYPE_ARTICLE,
        help_text="Article = editorial single-column; Landing = composed marketing sections.",
    )
    TEMPLATE_DEFAULT = ""
    TEMPLATE_HUMAINX = "humainx"
    TEMPLATE_HUMAINX_HOME = "humainx_home"
    TEMPLATE_NEO_COTTAGE = "neo_cottage"
    TEMPLATE_VARIANT_CHOICES = [
        (TEMPLATE_DEFAULT, "Default for page type"),
        (TEMPLATE_HUMAINX, "HumainX landing page"),
        (TEMPLATE_HUMAINX_HOME, "HumainX standalone home page"),
        (TEMPLATE_NEO_COTTAGE, "Neo-Cottage definition page"),
    ]
    template_variant = models.CharField(
        max_length=50,
        choices=TEMPLATE_VARIANT_CHOICES,
        blank=True,
        default=TEMPLATE_DEFAULT,
        help_text="Optional curated template variant used by the static builder.",
    )
    # For landing pages: ordered list of typed section blocks the generator emits
    # as JSON, e.g. [{"type":"hero","headline":...}, {"type":"stats","items":[...]}].
    landing_sections = models.JSONField(
        default=list, blank=True,
        help_text="Landing pages only: ordered section blocks (hero, stats, features, cards, cta, richtext).",
    )

    # Generated content (article pages)
    body_html = models.TextField(blank=True)

    # Basic SEO fields
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=512, blank=True)
    focus_keyword = models.CharField(max_length=255, blank=True)

    # Future: schema.org JSON-LD etc.
    schema_jsonld = models.TextField(blank=True)

    last_generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("site", "slug")
        ordering = ("nav_order", "title", "id")

    def __str__(self) -> str:
        return f"{self.site.slug}: {self.title}"

    def save(self, *args, **kwargs):
        """
        Ensure slug is unique per site.
        """
        if not self.slug:
            base = slugify(self.title) or "page"
            slug = base
            i = 2

            qs = Page.objects.filter(site=self.site)
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            while qs.filter(slug=slug).exists():
                slug = f"{base}-{i}"
                i += 1

            self.slug = slug

        super().save(*args, **kwargs)

class SiteTopNavItem(models.Model):
    """
    Per-site top navigation item.
    If no items exist for a site, templates can fall back to Page-based nav.
    """
    site = models.ForeignKey(
        Site, on_delete=models.CASCADE, related_name="top_nav_items"
    )

    label = models.CharField(max_length=100)
    url = models.CharField(
        max_length=255,
        help_text="Relative link like 'about-us.html' or absolute like 'https://...'",
    )
    order = models.PositiveIntegerField(default=0)

    # Optional behavior flags
    open_in_new_tab = models.BooleanField(default=False)
    is_enabled = models.BooleanField(default=True)

    # Optional helper if you want pretty headers later (CTA button, highlight, etc.)
    is_cta = models.BooleanField(default=False)

    class Meta:
        ordering = ("order", "label", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["site", "label", "url"],
                name="uniq_site_topnav_label_url",
            )
        ]

    def __str__(self) -> str:
        return f"{self.site.slug}: {self.label} -> {self.url}"

# --- After Deploy Audit Models ---------------------------------------------

class SiteAuditRun(models.Model):
    STATUS_RUNNING = "running"
    STATUS_DONE = "done"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_RUNNING, "Running"),
        (STATUS_DONE, "Done"),
        (STATUS_FAILED, "Failed"),
    ]

    site = models.ForeignKey(
        Site, on_delete=models.CASCADE, related_name="audit_runs"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RUNNING)

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    # Summary stats
    start_url = models.URLField(blank=True)
    pages_scanned = models.PositiveIntegerField(default=0)
    links_checked = models.PositiveIntegerField(default=0)
    broken_count = models.PositiveIntegerField(default=0)

    # Optional message for failures / notes
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"Audit {self.site.slug} @ {self.started_at:%Y-%m-%d %H:%M} ({self.status})"


class SiteAuditIssue(models.Model):
    run = models.ForeignKey(
        SiteAuditRun, on_delete=models.CASCADE, related_name="issues"
    )

    source_url = models.URLField(blank=True)  # page where we found the link
    target_url = models.URLField()            # the link we tried

    link_type = models.CharField(max_length=50, blank=True)  # a, img, script, link, etc.
    is_internal = models.BooleanField(default=False)

    status_code = models.IntegerField(blank=True, null=True)
    error = models.CharField(max_length=512, blank=True)  # exception msg, timeout, etc.

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.status_code or 'ERR'} {self.target_url}"

class EvergreenArticle(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_ARCHIVED = "archived"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    site = models.ForeignKey("sites_builder.Site", on_delete=models.CASCADE, related_name="evergreen_articles")
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_cornerstone = models.BooleanField(default=False)
    series = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional editorial series, for example HumainX.",
    )
    series_number = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        help_text="Optional sequence number within the editorial series.",
    )
    hypothesis = models.CharField(
        max_length=20,
        blank=True,
        help_text="Optional hypothesis identifier, for example H1.",
    )
    feedback_identifier = models.CharField(
        max_length=64,
        blank=True,
        help_text="Stable public feedback identifier, for example HX01.",
    )
    reader_question = models.TextField(
        blank=True,
        help_text="Optional reader-response question displayed at the end of the article.",
    )
    reader_answer_options = models.JSONField(
        default=list,
        blank=True,
        help_text="Optional ordered list of display-only reader answer options.",
    )

    # content
    excerpt = models.TextField(blank=True)
    body_md = models.TextField(blank=True)  # keep it simple: markdown or plain HTML

    # basic SEO fields
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=320, blank=True)
    canonical_url = models.URLField(blank=True)

    # optional visuals
    hero_image_url = models.URLField(blank=True)

    # authorship and URL-history signals used by public article metadata
    author_name = models.CharField(max_length=200, blank=True)
    author_url = models.URLField(blank=True)
    content_updated_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date of the most recent significant editorial update.",
    )
    legacy_slugs = models.JSONField(
        default=list,
        blank=True,
        help_text="Previous article slugs that should permanently redirect here.",
    )

    published_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["site", "slug"], name="uniq_site_article_slug")
        ]

    def __str__(self):
        return f"{self.title} ({self.site})"

    @property
    def editorial_label(self) -> str:
        if not self.series:
            return "INSIGHT"
        label = self.series.upper()
        if self.series_number is not None:
            return f"{label} / {self.series_number:02d}"
        return label

    @property
    def reading_minutes(self) -> int:
        from .services.reading_time import estimate_reading_minutes

        return estimate_reading_minutes(self.body_md)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:255]
        # auto-set published_at on publish
        if self.status == self.STATUS_PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

class ArticleCornerstoneLink(models.Model):
    """
    Links a supporting article -> a cornerstone article.
    (cornerstone should have is_cornerstone=True; enforced in clean/save)
    """
    site = models.ForeignKey("sites_builder.Site", on_delete=models.CASCADE, related_name="article_cornerstone_links")
    cornerstone = models.ForeignKey("EvergreenArticle", on_delete=models.CASCADE, related_name="cornerstone_links")
    supporting = models.ForeignKey("EvergreenArticle", on_delete=models.CASCADE, related_name="supporting_links")

    # optional niceties
    is_primary = models.BooleanField(default=False)
    anchor_text = models.CharField(max_length=140, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("cornerstone", "supporting")]
        ordering = ["-is_primary", "id"]

    def __str__(self):
        return f"{self.supporting} -> {self.cornerstone}"

    def clean(self):
        # Lightweight guardrails (also safe to re-check in save())
        if self.cornerstone_id == self.supporting_id:
            raise ValueError("An article cannot link to itself as a cornerstone.")
