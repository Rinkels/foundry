"""Upsert the OT security page (slug `ot-security`) on the mindsgate-redesign site.

The page is composed from existing landing blocks plus the new `ot_explorer`
block (apps/sites_builder/templates/.../partials/sections/ot_explorer.html).

Run from the foundry root:

    python manage.py shell -c "exec(open('scripts/add_ot_explorer_page.py', encoding='utf-8').read())"
    python manage.py build_site mindsgate-redesign

Re-running is safe: it updates the page in place. Pass SITE_SLUG via env to
target a different site.
"""
import os

from apps.sites_builder.models import Page, Site

SITE_SLUG = os.environ.get("SITE_SLUG", "mindsgate-redesign")
PAGE_SLUG = "ot-security"

SECTIONS = [
    {
        "type": "hero",
        "background": "glow",
        "eyebrow": "OT security · Interactive briefing",
        "headline": "See every way into the plant, then take them off the board.",
        "headline_accent": "take them off the board.",
        "subhead": (
            "An interactive Purdue model of an electric power generation plant. "
            "Watch how data crosses from the internet to the turbine on an ordinary day, "
            "count the attack paths that two-way firewalls leave open, and trace the routes "
            "that real incidents took."
        ),
        # NB: a bare "#anchor" href is treated as a page slug by the builder's link
        # resolver, so in-page anchors must carry the page filename.
        "primary_cta": {"label": "Explore the model", "href": "ot-security.html#explorer"},
        "secondary_cta": {"label": "Talk to an Architect", "href": "internal://contact"},
    },
    {
        "type": "ot_explorer",
        "anchor": "explorer",
        "eyebrow": "Purdue Model Explorer",
        "heading": "Electric power generation",
        "subhead": "Three views of the same plant. Switch between them, harden a crossing, pick an incident.",
        "default_view": "flow",
    },
    {
        "type": "features",
        "eyebrow": "What the model shows",
        "heading": "Three lessons the diagram makes obvious",
        "numbered": True,
        "items": [
            {
                "title": "Every two-way firewall is a path, not a wall",
                "text": (
                    "A firewall permits a live session in both directions. Whatever rides that "
                    "session, from a vendor's stolen VPN credential to a poisoned patch, arrives "
                    "inside the plant with the same permissions as the legitimate traffic."
                ),
            },
            {
                "title": "Hardware-enforced crossings change the count",
                "text": (
                    "Unidirectional gateways, hardware-enforced remote access and protocol-enforced "
                    "inbound gateways remove the return path. The risk view counts the ways in; "
                    "each hardened crossing takes one off the board."
                ),
            },
            {
                "title": "The incidents that mattered used the ordinary paths",
                "text": (
                    "BlackEnergy rode remote access. Triton walked from IT through the DMZ to the "
                    "safety system. Colonial Pipeline never touched OT and still stopped the pipeline. "
                    "The known attacks view traces each one through this plant."
                ),
            },
        ],
    },
    {
        "type": "cta",
        "heading": "Want this drawn for your plant?",
        "text": (
            "We map your actual crossings, count the paths, and give you a prioritised "
            "hardening plan with the business case for each gateway."
        ),
        "button": {"label": "Talk to an Architect", "href": "internal://contact"},
    },
]

site = Site.objects.get(slug=SITE_SLUG)
page, created = Page.objects.get_or_create(
    site=site,
    slug=PAGE_SLUG,
    defaults={
        "title": "OT security: Purdue Model Explorer",
        "page_type": "landing",
        "nav_order": 50,
    },
)
page.title = "OT security: Purdue Model Explorer"
page.page_type = "landing"
page.landing_sections = SECTIONS
page.meta_title = "Purdue Model Explorer for power generation | Mindsgate"
page.meta_description = (
    "Interactive Purdue model of an electric power plant: operational data flows, "
    "residual risk and attack paths, and the routes known OT attacks took."
)
page.is_locked = False
page.save()
print(f"{'created' if created else 'updated'} page {site.slug}/{page.slug} (id={page.id})")
