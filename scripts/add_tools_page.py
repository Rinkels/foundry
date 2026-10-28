"""Upsert the Tools hub page (slug `tools`) on mindsgate-redesign, add a
"Tools" top-nav entry, and add the OT security card to the solutions page.

The hub indexes the free interactive pages: the CISSP study suite (which
stays at its live /insights/ URLs) and the OT security Purdue Model Explorer.

Run from the foundry root:

    python manage.py shell -c "exec(open('scripts/add_tools_page.py', encoding='utf-8').read())"
    python manage.py build_site mindsgate-redesign

Re-running is safe: pages are updated in place and the nav/card inserts are
idempotent.
"""
import os

from apps.sites_builder.models import Page, Site, SiteTopNavItem

SITE_SLUG = os.environ.get("SITE_SLUG", "mindsgate-redesign")
PAGE_SLUG = "tools"

SECTIONS = [
    {
        "type": "hero",
        "background": "glow",
        "eyebrow": "Tools · Free to use",
        "headline": "Working tools, built in the open.",
        "headline_accent": "built in the open.",
        "subhead": (
            "Interactive study aids and security briefings we built for our own "
            "work and left open for everyone. No sign-up and no tracking — your "
            "progress is saved in your own browser."
        ),
        "primary_cta": {"label": "CISSP study suite", "href": "tools.html#cissp"},
        "secondary_cta": {"label": "OT security briefing", "href": "internal://ot-security"},
    },
    {
        "type": "cards",
        "anchor": "cissp",
        "eyebrow": "CISSP study suite",
        "heading": "Four tools, two deep dives, one shared glossary.",
        "subhead": (
            "Built around a single structured glossary of exam concepts: every "
            "flashcard, mind-map node and quiz question draws from the same data."
        ),
        "items": [
            {
                "icon": "📖",
                "title": "Security glossary",
                "text": "120+ exam concepts across all 8 domains, with the step lists and phase orders the exam actually asks about.",
                "href": "insights/cissp-security-glossary.html",
                "link_label": "Browse the glossary",
            },
            {
                "icon": "🗂️",
                "title": "Flashcards & exam practice",
                "text": "Spaced-repetition flashcards plus auto-graded exam-style questions. Progress saves locally; export and import anytime.",
                "href": "insights/cissp-flashcards.html",
                "link_label": "Start a session",
            },
            {
                "icon": "🧠",
                "title": "Domain mind map",
                "text": "All 8 domains as a collapsible tree with exam weights, linked straight into the glossary.",
                "href": "insights/cissp-mind-map.html",
                "link_label": "Open the map",
            },
            {
                "icon": "📊",
                "title": "Chapter score tracker",
                "text": "Log practice-test scores by study-guide chapter and see weight-adjusted readiness per domain.",
                "href": "insights/cissp-score-tracker.html",
                "link_label": "Track your scores",
            },
            {
                "icon": "🏛️",
                "title": "Deep dive: security models",
                "text": "Bell-LaPadula, Biba, Clark-Wilson and Brewer-Nash side by side, with the simple-vs-star trick spelled out.",
                "href": "insights/cissp-security-models.html",
                "link_label": "Read the deep dive",
            },
            {
                "icon": "📋",
                "title": "Deep dive: SOC reports",
                "text": "SOC 1, 2 and 3 and Type I vs Type II — which report answers which question, and who gets to read it.",
                "href": "insights/cissp-soc-reports.html",
                "link_label": "Read the deep dive",
            },
        ],
    },
    {
        "type": "cards",
        "eyebrow": "Security briefings",
        "heading": "Interactive briefings for operators.",
        "items": [
            {
                "icon": "🏭",
                "title": "Purdue Model Explorer",
                "badge": "New",
                "badge_color": "accent",
                "text": "An interactive Purdue model of a power plant: normal data flows, residual attack paths, and the routes six real OT incidents took.",
                "href": "internal://ot-security",
                "link_label": "Explore the model",
            },
            {
                "icon": "🧭",
                "title": "Sales Process Explorer",
                "text": "An interactive B2B pipeline: the happy path, the stalls and loops where leads wait, and the CRM activity that keeps a deal moving.",
                "href": "internal://sales-process",
                "link_label": "Explore the process",
            },
            {
                "icon": "📈",
                "title": "Fracto market tools",
                "text": "Free market dashboards from our Fracto platform, including the weekly CFTC Commitments of Traders report across 31 markets.",
                "href": "https://fracto.mindsgate.com/tools/",
                "link_label": "Open Fracto tools",
            },
        ],
    },
    {
        "type": "cta",
        "heading": "Want a tool like this for your team?",
        "text": (
            "Everything here runs on the same platform machinery we build for "
            "clients. If an interactive briefing or training tool would move the "
            "needle for your organisation, let's scope it."
        ),
        "button": {"label": "Talk to an Architect", "href": "internal://contact"},
    },
]

site = Site.objects.get(slug=SITE_SLUG)

# 1. Upsert the tools page
page, created = Page.objects.get_or_create(
    site=site,
    slug=PAGE_SLUG,
    defaults={"title": "Tools", "page_type": "landing", "nav_order": 25},
)
page.title = "Tools"
page.page_type = "landing"
page.landing_sections = SECTIONS
page.meta_title = "Free tools: CISSP study suite & OT security explorer | Mindsgate"
page.meta_description = (
    "Free interactive tools from Mindsgate: a CISSP study suite (glossary, "
    "flashcards, mind map, score tracker) and an interactive Purdue model "
    "OT security briefing."
)
page.is_locked = False
page.save()
print(f"{'created' if created else 'updated'} page {site.slug}/{page.slug} (id={page.id})")

# 2. Top-nav entry between Venture Studio (20) and Insights (30)
nav, nav_created = SiteTopNavItem.objects.get_or_create(
    site=site, label="Tools", url="tools.html",
    defaults={"order": 25, "is_enabled": True},
)
print(f"{'created' if nav_created else 'kept'} nav item {nav.label} -> {nav.url} (order={nav.order})")

# 3. OT security card on the solutions page (idempotent insert)
solutions = Page.objects.get(site=site, slug="solutions")
for sec in solutions.landing_sections:
    if sec.get("type") == "cards":
        items = sec.setdefault("items", [])
        if not any(i.get("href") == "internal://ot-security" for i in items):
            items.append({
                "icon": "🏭",
                "title": "OT Security Briefing",
                "badge": "Interactive",
                "badge_color": "accent",
                "text": "An interactive Purdue model of a power plant — see the attack paths two-way firewalls leave open and how real incidents used them.",
                "href": "internal://ot-security",
                "link_label": "Explore the model",
            })
            solutions.save()
            print("added OT security card to solutions page")
        else:
            print("solutions page already has the OT security card")
        break
