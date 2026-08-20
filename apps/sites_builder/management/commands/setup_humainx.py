from datetime import datetime, timezone as datetime_timezone

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.template.loader import render_to_string

from ...models import EvergreenArticle, Page, Site, SiteTopNavItem
from ...services.static_builder import StaticBuilder


ARTICLE_SLUG = "the-second-cottage-revolution"
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
        article, article_created = EvergreenArticle.objects.update_or_create(
            site=site,
            slug=ARTICLE_SLUG,
            defaults={
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
                    "The Industrial Revolution pulled production into "
                    "organizations. Could AI push economic capability back "
                    "toward individuals and small teams? HumainX explores the "
                    "economy of 2036."
                ),
                "canonical_url": "",
                "published_at": datetime(
                    2026, 8, 18, tzinfo=datetime_timezone.utc
                ),
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                "HumainX configured: "
                f"page={'created' if page_created else 'updated'}, "
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
