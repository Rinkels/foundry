import json
from datetime import datetime, timezone as datetime_timezone

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.template.loader import render_to_string

from ...models import EvergreenArticle, Page, Site, SiteTopNavItem
from ...services.static_builder import StaticBuilder


ARTICLE_SLUG = "neo-cottage-revolution"
LEGACY_ARTICLE_SLUG = "the-second-cottage-revolution"
ARTICLE_TEMPLATE = (
    "sites_builder/content/humainx/the_second_cottage_revolution.html"
)
READER_FEEDBACK_FORM_URL = "https://tally.so/r/kd8gJZ"


class Command(BaseCommand):
    help = "Configure HumainX for a Mindsgate site and optionally build it."

    def add_arguments(self, parser):
        parser.add_argument(
            "--site-slug",
            default="mindsgate-redesign",
            help="Site to configure (default: mindsgate-redesign).",
        )
        parser.add_argument(
            "--no-build",
            action="store_true",
            help="Update Foundry content without generating static output.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        site_slug = options["site_slug"]
        try:
            site = Site.objects.get(slug=site_slug)
        except Site.DoesNotExist as exc:
            raise CommandError(f"Site with slug '{site_slug}' not found.") from exc

        root = site.pages.filter(is_root=True).order_by("id").first()
        if root is None:
            raise CommandError(
                f"Site '{site_slug}' needs a root page before HumainX can be configured."
            )

        site.newsletter_config = {
            **(site.newsletter_config or {}),
            "enabled": True,
            "provider": "buttondown",
            "username": "HumainX",
            "form_action": (
                "https://buttondown.com/api/emails/embed-subscribe/HumainX"
            ),
            "button_label": "Follow HumainX",
            "success_url": "",
            "series": "HumainX",
            "article_anchor": "follow-humainx",
            "article_link_label": "Follow HumainX",
            "section_eyebrow": "Follow the exploration",
            "section_description": (
                "New arguments, counterarguments, reader predictions and evidence "
                "as we work toward understanding the economy of 2036."
            ),
        }
        existing_feedback = site.reader_feedback_config or {}
        feedback_form_url = (
            str(existing_feedback.get("form_url") or "").strip()
            or READER_FEEDBACK_FORM_URL
        )
        site.reader_feedback_config = {
            **existing_feedback,
            "enabled": bool(feedback_form_url),
            "provider": existing_feedback.get("provider") or "tally",
            "form_url": feedback_form_url,
            "button_label": (
                existing_feedback.get("button_label")
                or "Share your reasoning →"
            ),
        }
        site.save(
            update_fields=[
                "newsletter_config", "reader_feedback_config", "updated_at"
            ]
        )

        page, page_created = Page.objects.update_or_create(
            site=site,
            slug="humainx",
            defaults={
                "title": "HumainX",
                "parent": root,
                "depth": root.depth + 1,
                "is_root": False,
                "nav_order": 35,
                "page_type": Page.PAGE_TYPE_LANDING,
                "template_variant": Page.TEMPLATE_HUMAINX,
                "meta_title": (
                    "HumainX — What happens when intelligence is no longer scarce?"
                ),
                "meta_description": (
                    "HumainX is a Mindsgate exploration of work, ownership, "
                    "companies and economic life as AI makes intelligence "
                    "increasingly abundant."
                ),
                "focus_keyword": "future of work and AI",
                "hero_image_url": (
                    f"{site.base_url}/assets/images/neo-cottage-revolution-og.png"
                    if site.base_url
                    else ""
                ),
                "schema_jsonld": json.dumps(
                    {
                        "@context": "https://schema.org",
                        "@type": "CollectionPage",
                        "name": "HumainX",
                        "description": (
                            "An exploration of work, ownership and economic life "
                            "as AI makes intelligence increasingly abundant."
                        ),
                        "url": f"{site.base_url}/humainx.html" if site.base_url else "",
                    },
                    separators=(",", ":"),
                ),
                "last_generated_at": datetime(
                    2026, 8, 20, tzinfo=datetime_timezone.utc
                ),
            },
        )

        pillar, pillar_created = Page.objects.update_or_create(
            site=site,
            slug="neo-cottage-economy",
            defaults={
                "title": "What Is the Neo-Cottage Economy?",
                "parent": root,
                "depth": root.depth + 1,
                "is_root": False,
                "nav_order": 36,
                "page_type": Page.PAGE_TYPE_LANDING,
                "template_variant": Page.TEMPLATE_NEO_COTTAGE,
                "meta_title": "What Is the Neo-Cottage Economy? | HumainX",
                "meta_description": (
                    "The neo-cottage economy describes a future where AI makes "
                    "individuals and tiny teams viable units of production. "
                    "Explore the evidence and implications."
                ),
                "focus_keyword": "neo-cottage economy",
                "hero_image_url": (
                    f"{site.base_url}/assets/images/neo-cottage-revolution-og.png"
                    if site.base_url
                    else ""
                ),
                "schema_jsonld": json.dumps(
                    {
                        "@context": "https://schema.org",
                        "@graph": [
                            {
                                "@type": "WebPage",
                                "@id": (
                                    f"{site.base_url}/neo-cottage-economy.html"
                                    if site.base_url
                                    else "neo-cottage-economy.html"
                                ),
                                "name": "What Is the Neo-Cottage Economy?",
                                "description": (
                                    "A working definition and evidence framework "
                                    "for the AI-enabled neo-cottage economy."
                                ),
                            },
                            {
                                "@type": "DefinedTerm",
                                "name": "Neo-cottage economy",
                                "description": (
                                    "An emerging model in which AI makes individuals "
                                    "and very small teams economically viable units of "
                                    "production at a scale that once required larger firms."
                                ),
                                "inDefinedTermSet": "HumainX economic concepts",
                            },
                        ],
                    },
                    separators=(",", ":"),
                ),
                "last_generated_at": datetime(
                    2026, 8, 20, tzinfo=datetime_timezone.utc
                ),
            },
        )

        nav = (
            site.top_nav_items.filter(label__iexact="HumainX").order_by("id").first()
            or site.top_nav_items.filter(url="humainx.html").order_by("id").first()
        )
        nav_created = nav is None
        if nav is None:
            nav = SiteTopNavItem(site=site)
        nav.label = "HumainX"
        nav.url = "humainx.html"
        nav.order = 35
        nav.open_in_new_tab = False
        nav.is_enabled = True
        nav.is_cta = False
        nav.save()

        article_body = render_to_string(ARTICLE_TEMPLATE).strip()
        article = site.evergreen_articles.filter(slug=ARTICLE_SLUG).first()
        legacy_article = site.evergreen_articles.filter(
            slug=LEGACY_ARTICLE_SLUG
        ).first()
        article_created = article is None and legacy_article is None
        if article is None:
            article = legacy_article or EvergreenArticle(site=site)
        elif legacy_article is not None and legacy_article.pk != article.pk:
            # A partially migrated database can contain both slugs. Keep the
            # canonical record and retire the duplicate so it cannot re-enter
            # the sitemap or overwrite the redirect fallback.
            legacy_article.status = EvergreenArticle.STATUS_ARCHIVED
            legacy_article.save(update_fields=["status", "updated_at"])

        article_values = {
                "slug": ARTICLE_SLUG,
                "title": "The Neo-Cottage Revolution",
                "status": EvergreenArticle.STATUS_PUBLISHED,
                "is_cornerstone": False,
                "series": "HumainX",
                "series_number": 1,
                "hypothesis": "H1",
                "feedback_identifier": "HX01",
                "reader_question": (
                    "Ten years from now, will most people still earn the majority "
                    "of their income from a single employer?"
                ),
                "reader_answer_options": [
                    "Yes, largely unchanged",
                    "Yes, but companies will employ far fewer people",
                    "No, multiple income sources will become the norm",
                    "No, traditional employment itself will become much less important",
                    "I have absolutely no idea",
                ],
                "excerpt": (
                    "The Industrial Revolution pulled production into "
                    "organizations. Could AI push it back toward the individual?"
                ),
                "body_md": article_body,
                "meta_title": (
                    "The Neo-Cottage Revolution | HumainX by Mindsgate"
                ),
                "meta_description": (
                    "The Neo-Cottage Revolution: how AI could shrink firms, "
                    "distribute productive power, and reshape work and "
                    "ownership by 2036."
                ),
                "canonical_url": "",
                "hero_image_url": "assets/images/neo-cottage-revolution-og.png",
                "author_name": "HumainX",
                "author_url": (
                    f"{site.base_url}/humainx.html" if site.base_url else ""
                ),
                "content_updated_at": datetime(
                    2026, 8, 20, tzinfo=datetime_timezone.utc
                ),
                "legacy_slugs": [LEGACY_ARTICLE_SLUG],
                "published_at": datetime(
                    2026, 8, 18, tzinfo=datetime_timezone.utc
                ),
            }
        for field, value in article_values.items():
            setattr(article, field, value)
        article.save()

        self.stdout.write(
            self.style.SUCCESS(
                "HumainX configured: "
                f"page={'created' if page_created else 'updated'}, "
                f"pillar={'created' if pillar_created else 'updated'}, "
                f"navigation={'created' if nav_created else 'updated'}, "
                f"article={'created' if article_created else 'updated'} "
                f"({article.reading_minutes} min read)."
            )
        )

        if not options["no_build"]:
            output_dir = StaticBuilder().build_site(site)
            self.stdout.write(
                self.style.SUCCESS(f"Built static site at: {output_dir}")
            )
