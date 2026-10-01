from django.core.management.base import BaseCommand, CommandError

from ...models import Site
from ...services.hero_image_regenerator import regenerate_site_hero_images


class Command(BaseCommand):
    help = "Replace generated hero images for all pages in a site, then rebuild static output."

    def add_arguments(self, parser):
        parser.add_argument("site_slug", type=str, help="Slug of the site to process.")
        parser.add_argument(
            "--no-build",
            action="store_true",
            help="Regenerate image files without rebuilding the static site afterward.",
        )

    def handle(self, *args, **options):
        site_slug = options["site_slug"]

        try:
            site = Site.objects.get(slug=site_slug)
        except Site.DoesNotExist:
            raise CommandError(f"Site with slug '{site_slug}' not found.")

        self.stdout.write(f"Regenerating hero images for '{site.slug}'...")
        stats = regenerate_site_hero_images(site, rebuild=not options["no_build"])

        self.stdout.write(
            self.style.SUCCESS(
                "Done. "
                f"Pages seen: {stats['pages_seen']}; "
                f"generated: {stats['generated']}; "
                f"landing images generated: {stats['landing_images_generated']}; "
                f"failed: {stats['failed']}; "
                f"files deleted: {stats['files_deleted']}."
            )
        )

        if stats["build_output"]:
            self.stdout.write(self.style.SUCCESS(f"Rebuilt static site at: {stats['build_output']}"))
        else:
            self.stdout.write("Skipped rebuild (--no-build).")
