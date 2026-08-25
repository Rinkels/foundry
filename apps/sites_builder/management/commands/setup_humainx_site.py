import json

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from ...models import DeploymentTarget, Developer, Page, Site
from ...services.static_builder import StaticBuilder


class Command(BaseCommand):
    help = "Create or update the standalone humainx.com landing site."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-build",
            action="store_true",
            help="Update Foundry content without generating the static site.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        mindsgate = Site.objects.filter(slug="mindsgate-redesign").first()
        owner = mindsgate.owner if mindsgate else Developer.objects.order_by("id").first()
        if owner is None:
            owner = Developer.objects.create(name="Mindsgate")

        newsletter_config = {
            "enabled": True,
            "provider": "buttondown",
            "username": "HumainX",
            "form_action": "https://buttondown.com/api/emails/embed-subscribe/HumainX",
            "button_label": "Follow HumainX",
            "success_url": "",
            "series": "HumainX",
        }
        reader_feedback_config = {
            "enabled": True,
            "provider": "tally",
            "form_url": "https://tally.so/r/kd8gJZ",
            "button_label": "Share your reasoning →",
        }

        site, site_created = Site.objects.update_or_create(
            slug="humainx",
            defaults={
                "owner": owner,
                "name": "HumainX",
                "description": (
                    "A public inquiry into work, ownership and economic life as "
                    "artificial intelligence makes intelligence less scarce."
                ),
                "domain": "humainx.com",
                "theme": Site.THEME_DARK,
                "theme_css": Site.THEME_CSS_HUMAINX,
                "primary_color": "#4fd8c4",
                "secondary_color": "#7c8cf8",
                "structure_locked": True,
                "target_page_count": 1,
                "max_depth": 1,
                "max_children_per_page": 1,
                "nav_cta_label": "",
                "nav_cta_url": "",
                "footer_links": [],
                "newsletter_config": newsletter_config,
                "reader_feedback_config": reader_feedback_config,
                "hide_builder_credit": True,
            },
        )

        schema = {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "WebSite",
                    "@id": "https://humainx.com/#website",
                    "url": "https://humainx.com/",
                    "name": "HumainX",
                    "description": (
                        "A public inquiry into work, ownership and economic life "
                        "when intelligence is no longer scarce."
                    ),
                    "publisher": {"@id": "https://humainx.com/#organization"},
                },
                {
                    "@type": "Organization",
                    "@id": "https://humainx.com/#organization",
                    "name": "HumainX",
                    "url": "https://humainx.com/",
                    "logo": "https://humainx.com/assets/images/favicon.jpg",
                    "parentOrganization": {
                        "@type": "Organization",
                        "name": "Mindsgate",
                        "url": "https://www.mindsgate.com/",
                    },
                },
            ],
        }
        page, page_created = Page.objects.update_or_create(
            site=site,
            slug="home",
            defaults={
                "title": "HumainX",
                "parent": None,
                "depth": 0,
                "is_root": True,
                "nav_order": 0,
                "page_type": Page.PAGE_TYPE_LANDING,
                "template_variant": Page.TEMPLATE_HUMAINX_HOME,
                "meta_title": (
                    "HumainX — What happens when intelligence is no longer scarce?"
                ),
                "meta_description": (
                    "HumainX is a public inquiry into work, firms, ownership and "
                    "economic life as AI makes intelligence increasingly abundant."
                ),
                "focus_keyword": "abundant intelligence economy",
                "hero_image_url": (
                    "https://humainx.com/assets/images/"
                    "neo-cottage-revolution-og.png"
                ),
                "schema_jsonld": json.dumps(
                    schema, ensure_ascii=False, separators=(",", ":")
                ),
                "last_generated_at": timezone.now(),
            },
        )
        site.pages.exclude(pk=page.pk).filter(is_root=True).update(is_root=False)

        target, target_created = DeploymentTarget.objects.update_or_create(
            site=site,
            name="Cloudflare Pages (humainx.com)",
            defaults={
                "type": DeploymentTarget.TYPE_CF_PAGES,
                "cf_project_name": "humainx",
                "is_default": True,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                "HumainX standalone site configured: "
                f"site={'created' if site_created else 'updated'}, "
                f"home={'created' if page_created else 'updated'}, "
                f"deployment={'created' if target_created else 'updated'}."
            )
        )

        if not options["no_build"]:
            output_dir = StaticBuilder().build_site(site)
            self.stdout.write(self.style.SUCCESS(f"Built static site at: {output_dir}"))
