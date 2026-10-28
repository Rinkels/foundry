"""Upsert the sales process page (slug `sales-process`) on the mindsgate-redesign site.

The page is composed from existing landing blocks plus the `sales_explorer`
block (apps/sites_builder/templates/.../partials/sections/sales_explorer.html),
ported from the standalone C:\\Projects\\fractals\\sales-process-explorer.html.

Run from the foundry root:

    python manage.py shell -c "exec(open('scripts/add_sales_explorer_page.py', encoding='utf-8').read())"
    python manage.py build_site mindsgate-redesign

Re-running is safe: it updates the page in place. Pass SITE_SLUG via env to
target a different site.
"""
import os

from apps.sites_builder.models import Page, Site

SITE_SLUG = os.environ.get("SITE_SLUG", "mindsgate-redesign")
PAGE_SLUG = "sales-process"

SECTIONS = [
    {
        "type": "hero",
        "background": "glow",
        "eyebrow": "Sales operations · Interactive tool",
        "headline": "See where leads stall, and what to log so they don't.",
        "headline_accent": "what to log so they don't.",
        "subhead": (
            "An interactive map of a B2B sales process. Follow the happy path from "
            "enquiry to signed deal, open up the stalls and loops where pipelines "
            "quietly die, and see the CRM activity that keeps every lead moving — "
            "then walk one lead through the whole thing."
        ),
        # NB: a bare "#anchor" href is treated as a page slug by the builder's link
        # resolver, so in-page anchors must carry the page filename.
        "primary_cta": {"label": "Explore the process", "href": "sales-process.html#explorer"},
        "secondary_cta": {"label": "Talk to an Architect", "href": "internal://contact"},
    },
    {
        "type": "sales_explorer",
        "anchor": "explorer",
        "eyebrow": "Sales Process Explorer",
        "heading": "One pipeline, four ways to read it",
        "subhead": "Switch views, click any box for its entry and exit rules, or walk a single lead start to finish.",
        "default_view": "happy",
    },
    {
        "type": "features",
        "eyebrow": "What the model enforces",
        "heading": "Three rules that keep a pipeline honest",
        "numbered": True,
        "items": [
            {
                "title": "Every hold has a date and a limit",
                "text": (
                    "Unresponsive, Not ready, Nurture, Negotiation, Deferred — a lead "
                    "may wait in any of them, but never without a review date, a retry "
                    "cadence and a limit that forces a decision."
                ),
            },
            {
                "title": "The CRM loop runs under every stage",
                "text": (
                    "Follow-up scheduled, follow-up completed, reassess. Three records "
                    "per touch — what is next, what happened, what changed — under "
                    "Outreach, Discovery and Proposal alike."
                ),
            },
            {
                "title": "Classification routes six kinds of enquiry",
                "text": (
                    "Qualified, Nurture, Disqualified, Existing customer, Partner or "
                    "referral, Non-sales. Deciding what a lead is before anyone sells "
                    "to it is what keeps the pipeline numbers meaning something."
                ),
            },
        ],
    },
    {
        "type": "cta",
        "heading": "Want this wired into your CRM?",
        "text": (
            "This process is how our Contax CRM thinks about leads out of the box. "
            "We can map your pipeline the same way — stages, holds, limits and the "
            "fields worth logging — and build it into your tooling."
        ),
        "button": {"label": "Talk to an Architect", "href": "internal://contact"},
    },
]

site = Site.objects.get(slug=SITE_SLUG)
page, created = Page.objects.get_or_create(
    site=site,
    slug=PAGE_SLUG,
    defaults={
        "title": "B2B sales process explorer",
        "page_type": "landing",
        "nav_order": 51,
    },
)
page.title = "B2B sales process explorer"
page.page_type = "landing"
page.landing_sections = SECTIONS
page.meta_title = "B2B sales process explorer | Mindsgate"
page.meta_description = (
    "Interactive B2B sales process: pipeline stages from lead to handoff, the "
    "stall states and loops where leads wait, and the CRM activity that keeps "
    "every deal moving."
)
page.is_locked = False
page.save()
print(f"{'created' if created else 'updated'} page {site.slug}/{page.slug} (id={page.id})")
