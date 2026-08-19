import json

from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    ArticleCornerstoneLink,
    DeploymentTarget,
    Developer,
    EvergreenArticle,
    Page,
    Site,
    SiteTopNavItem,
)
from .services.generator import SiteGenerator


@admin.register(Developer)
class DeveloperAdmin(admin.ModelAdmin):
    list_display = ("name", "email")
    search_fields = ("name", "email")


class DeploymentTargetInline(admin.TabularInline):
    model = DeploymentTarget
    extra = 0


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "site",
        "slug",
        "parent",
        "depth",
        "is_root",
        "is_locked",
        "last_generated_at",
        "locked_by",
        "nav_order"
    )
    list_filter = ("site", "is_root", "depth", "is_locked", "nav_order")
    search_fields = ("title", "slug", "meta_title", "meta_description")
    raw_id_fields = ("parent", "site")
    list_editable = ("is_locked",)
    ordering = ("site", "depth", "nav_order", "title")
    readonly_fields = ("locked_at", "locked_by", "last_generated_at")

    fieldsets = (
        (None, {
            "fields": ("site", "title", "slug", "parent", "hero_image_url", "depth", "is_root"),
        }),
        ("Content", {
            "fields": (
                "page_type", "template_variant", "landing_sections", "body_html",
                "meta_title", "meta_description", "focus_keyword", "schema_jsonld",
            ),
        }),
        ("Lockdown / Manual override", {
            "fields": ("is_locked", "manual_html", "locked_at", "locked_by"),
            "classes": ("collapse",),
        }),
        ("Generation info", {
            "fields": ("last_generated_at",),
        }),
    )

    actions = ["lock_selected_pages", "unlock_selected_pages"]

    @admin.action(description="Lock selected pages (prevent regeneration)")
    def lock_selected_pages(self, request, queryset):
        now = timezone.now()
        queryset.update(
            is_locked=True,
            locked_at=now,
            locked_by=request.user,
        )

    @admin.action(description="Unlock selected pages (allow regeneration)")
    def unlock_selected_pages(self, request, queryset):
        queryset.update(is_locked=False)

    def save_model(self, request, obj, form, change):
        # If lock flag was just turned on in the admin, stamp who/when
        if "is_locked" in form.changed_data and obj.is_locked:
            obj.locked_at = timezone.now()
            obj.locked_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DeploymentTarget)
class DeploymentTargetAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "type", "is_default")
    list_filter = ("type", "is_default", "site")
    search_fields = ("name", "site__name", "ftp_host", "local_path")



@admin.action(description="🚀 Plan Menu (IA) + Create Page Skeletons")
def plan_menu_ia(modeladmin, request, queryset):
    gen = SiteGenerator()
    count = 0
    for site in queryset:
        try:
            gen.ensure_root_page(site)
            gen._ensure_site_ia(site)  # materializes IA structure
            count += 1
        except Exception as e:
            messages.error(request, f"[{site.slug}] Failed: {e}")
    messages.success(request, f"Planned menu / IA for {count} site(s).")


@admin.action(description="🔒 Lock Structure (stop adding new pages)")
def lock_structure(modeladmin, request, queryset):
    updated = queryset.update(structure_locked=True)
    messages.success(request, f"Locked structure for {updated} site(s).")


@admin.action(description="🔓 Unlock Structure (allow adding pages again)")
def unlock_structure(modeladmin, request, queryset):
    updated = queryset.update(structure_locked=False)
    messages.success(request, f"Unlocked structure for {updated} site(s).")

@admin.action(description="🧹 Normalize Nav Order (10,20,30…) for selected site(s)")
def normalize_nav_order(modeladmin, request, queryset):
    """
    For each selected Site:
    - For each parent page (including None if you ever allow that), renumber its direct children
      by (nav_order, title, id) into 10,20,30...
    - Keeps hierarchy the same; only updates nav_order.
    """
    updated_total = 0

    from .models import Page  # local import to avoid circulars in some setups

    for site in queryset:
        with transaction.atomic():
            # All pages in site, we'll group by parent_id
            pages = list(Page.objects.filter(site=site).only("id", "parent_id", "nav_order", "title"))
            by_parent = {}
            for p in pages:
                by_parent.setdefault(p.parent_id, []).append(p)

            site_updates = 0
            for parent_id, children in by_parent.items():
                # Sort siblings deterministically
                children_sorted = sorted(children, key=lambda x: (x.nav_order or 0, (x.title or "").lower(), x.id))
                # Assign 10,20,30...
                next_order = 10
                for ch in children_sorted:
                    if ch.nav_order != next_order:
                        ch.nav_order = next_order
                        ch.save(update_fields=["nav_order"])
                        site_updates += 1
                    next_order += 10

            updated_total += site_updates

    messages.success(request, f"Normalized nav_order. Updated {updated_total} page(s).")

PRIVACY_HTML = """<h1>Privacy Policy</h1>
<p><em>Last updated: {date}</em></p>

<h2>Overview</h2>
<p>This Privacy Policy explains how {site_name} collects, uses, and protects information when you visit our website.</p>

<h2>Information we collect</h2>
<ul>
  <li><strong>Contact information</strong> you submit (e.g., name, email, phone) through forms.</li>
  <li><strong>Usage data</strong> (e.g., pages visited, approximate location, device/browser information) collected through standard logs and analytics tools, if enabled.</li>
</ul>

<h2>How we use information</h2>
<ul>
  <li>To respond to inquiries and provide requested services.</li>
  <li>To operate, maintain, and improve our website.</li>
  <li>To monitor security and prevent abuse.</li>
</ul>

<h2>Cookies and analytics</h2>
<p>We may use cookies or similar technologies to understand site usage and improve performance. You can control cookies through your browser settings.</p>

<h2>Sharing</h2>
<p>We do not sell personal information. We may share information with trusted service providers who help operate the website, subject to confidentiality and security obligations, or when required by law.</p>

<h2>Data retention</h2>
<p>We retain information only as long as necessary for the purposes described above, unless a longer retention period is required by law.</p>

<h2>Security</h2>
<p>We use reasonable safeguards designed to protect information. No method of transmission or storage is 100% secure.</p>

<h2>Your choices</h2>
<p>You may request access, correction, or deletion of your personal information by contacting us.</p>

<h2>Contact</h2>
<p>If you have questions about this policy, please contact us via the Contact page.</p>
"""

TERMS_HTML = """<h1>Terms of Service</h1>
<p><em>Last updated: {date}</em></p>

<h2>Acceptance of terms</h2>
<p>By accessing or using this website, you agree to these Terms of Service.</p>

<h2>Use of the website</h2>
<p>You agree to use the website lawfully and not to attempt to disrupt, damage, or compromise the site’s security or availability.</p>

<h2>Content and intellectual property</h2>
<p>Website content is provided by {site_name} and is protected by applicable intellectual property laws. You may not copy or redistribute content without permission, except as allowed by law.</p>

<h2>Third-party links</h2>
<p>This website may include links to third-party sites. We are not responsible for third-party content, policies, or practices.</p>

<h2>Disclaimer</h2>
<p>This website is provided “as is” without warranties of any kind, express or implied, to the fullest extent permitted by law.</p>

<h2>Limitation of liability</h2>
<p>To the fullest extent permitted by law, {site_name} will not be liable for any indirect, incidental, special, consequential, or punitive damages arising from your use of the website.</p>

<h2>Changes</h2>
<p>We may update these Terms from time to time. Changes are effective when posted on this page.</p>

<h2>Contact</h2>
<p>If you have questions about these Terms, please contact us via the Contact page.</p>
"""

@admin.action(description="📜 Create Legal Pages (Privacy Policy + Terms) with standard content")
def create_legal_pages(modeladmin, request, queryset):
    created_total = 0
    updated_total = 0
    today = timezone.now().date().isoformat()

    for site in queryset:
        root = site.pages.filter(is_root=True).first()
        if not root:
            messages.warning(request, f"[{site.slug}] No root page found. Generate root first.")
            continue

        defs = [
            ("Privacy Policy", "privacy-policy", PRIVACY_HTML),
            ("Terms of Service", "terms-of-service", TERMS_HTML),
        ]

        for title, slug, html_tpl in defs:
            page, created = Page.objects.get_or_create(
                site=site,
                slug=slug,
                defaults={
                    "title": title,
                    "parent": root,
                    "depth": 1,
                    "nav_order": 990 if slug == "privacy-policy" else 991,
                    "meta_title": f"{title} | {site.name}",
                    "meta_description": f"{title} for {site.name}.",
                    "focus_keyword": title,
                    "body_html": "",
                },
            )
            if created:
                created_total += 1

            # Ensure it shows up under root and at the bottom of nav
            changed_fields = []
            if page.parent_id != root.id:
                page.parent = root
                changed_fields.append("parent")
            if page.depth != 1:
                page.depth = 1
                changed_fields.append("depth")
            desired_order = 990 if slug == "privacy-policy" else 991
            if page.nav_order != desired_order:
                page.nav_order = desired_order
                changed_fields.append("nav_order")

            # If body is empty, populate with standard deterministic HTML
            if not (page.body_html or "").strip():
                page.body_html = html_tpl.format(date=today, site_name=site.name)
                changed_fields.append("body_html")

            # Keep meta consistent too (optional but nice)
            if not (page.meta_title or "").strip():
                page.meta_title = f"{title} | {site.name}"
                changed_fields.append("meta_title")
            if not (page.meta_description or "").strip():
                page.meta_description = f"{title} for {site.name}."
                changed_fields.append("meta_description")
            if not (page.focus_keyword or "").strip():
                page.focus_keyword = title
                changed_fields.append("focus_keyword")

            if changed_fields:
                page.save(update_fields=changed_fields)
                updated_total += 1

    messages.success(
        request,
        f"Legal pages done. Created: {created_total}. Updated: {updated_total}."
    )

@admin.register(EvergreenArticle)
class EvergreenArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "site", "series", "series_number", "status", "published_at", "updated_at")
    list_filter = ("status", "series", "site")
    search_fields = ("title", "slug", "excerpt", "body_md")
    prepopulated_fields = {"slug": ("title",)}

@admin.register(ArticleCornerstoneLink)
class ArticleCornerstoneLinkAdmin(admin.ModelAdmin):
    list_display = ("site", "supporting", "cornerstone", "is_primary", "anchor_text", "created_at")
    list_filter = ("site", "is_primary")
    search_fields = ("supporting__title", "cornerstone__title", "anchor_text")

class SiteTopNavItemInline(admin.TabularInline):
    model = SiteTopNavItem
    extra = 1
    fields = ("order", "label", "url", "is_enabled", "open_in_new_tab", "is_cta")
    ordering = ("order",)


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    inlines = [DeploymentTargetInline, SiteTopNavItemInline]  # ✅ include both
    list_display = (
        "name", "slug", "owner", "domain", "theme", "theme_css",
        "ga4_property_id", "ga4_measurement_id",
        "max_depth", "max_children_per_page",
    )
    search_fields = ("name", "slug", "domain", "owner__name")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = getattr(admin.ModelAdmin, "readonly_fields", ()) + ("ia_planned_at", "ia_plan_pretty")
    actions = [plan_menu_ia, lock_structure, unlock_structure, normalize_nav_order, create_legal_pages]
    list_filter = ("theme", "theme_css", "structure_locked")
    list_editable = ("ga4_property_id", "ga4_measurement_id")
    fieldsets = (
        (None, {"fields": ("owner", "name", "slug", "domain", "description")}),
        ("Generation Controls",
         {"fields": ("structure_locked", "target_page_count", "max_depth", "max_children_per_page")}),
        ("IA Plan", {"fields": ("ia_planned_at", "ia_plan_pretty")}),
        ("Branding / Theme", {
            "fields": (
                "theme", "theme_css", "logo_url", "primary_color", "secondary_color",
                "hide_builder_credit",
            )
        }),
        ("Newsletter", {"fields": ("newsletter_config",)}),
        ("Analytics (GA4)", {"fields": ("ga4_property_id", "ga4_measurement_id")}),
    )

    def ia_plan_pretty(self, obj):
        if not obj.ia_plan:
            return "(none)"
        pretty = json.dumps(obj.ia_plan, indent=2, ensure_ascii=False)
        return format_html(
            "<pre style='white-space:pre-wrap; max-height:480px; overflow:auto;'>{}</pre>",
            pretty,
        )

    ia_plan_pretty.short_description = "IA Plan (JSON)"

