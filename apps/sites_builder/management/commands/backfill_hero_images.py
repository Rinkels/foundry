from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from sites_builder.models import Site, Page
from sites_builder.services.image_generator import ImageGenerator


class Command(BaseCommand):
    help = "Generate hero images for pages that don't have one yet."

    def add_arguments(self, parser):
        parser.add_argument(
            "site_slug",
            type=str,
            help="Slug of the site to backfill (use 'ALL' to process all sites).",
        )

    def handle(self, *args, **options):
        site_slug = options["site_slug"]

        base_dir = Path(settings.BASE_DIR) / "output" / "sites"
        image_gen = ImageGenerator(base_dir)

        if site_slug.upper() == "ALL":
            sites = Site.objects.all()
        else:
            try:
                sites = [Site.objects.get(slug=site_slug)]
            except Site.DoesNotExist:
                raise CommandError(f"Site with slug '{site_slug}' not found.")

        total = 0
        for site in sites:
            qs = site.pages.filter(hero_image_url="")  # empty string / no image
            count = qs.count()
            self.stdout.write(f"Processing site '{site.slug}' ({count} pages missing images)...")

            for page in qs:
                hero_context = f"Page title: {page.title}. Site description: {site.description}."
                try:
                    url = image_gen.generate_page_hero(site.slug, page.slug, hero_context)
                    page.hero_image_url = url
                    page.save(update_fields=["hero_image_url"])
                    total += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(
                        f"  [WARN] Failed for page '{page.slug}': {e}"
                    ))

        self.stdout.write(self.style.SUCCESS(
            f"Backfill complete. Generated hero images for {total} pages."
        ))
