from django.core.management.base import BaseCommand, CommandError
from sites_builder.models import Site
from sites_builder.services.generator import SiteGenerator


class Command(BaseCommand):
    help = "Expand a site by generating new pages via ChatGPT."

    def add_arguments(self, parser):
        parser.add_argument("site_slug", type=str)
        parser.add_argument(
            "--max-new-pages",
            type=int,
            default=10,
            help="Maximum number of new/updated pages to create this run.",
        )

    def handle(self, *args, **options):
        site_slug = options["site_slug"]
        max_new_pages = options["max_new_pages"]

        try:
            site = Site.objects.get(slug=site_slug)
        except Site.DoesNotExist:
            raise CommandError(f"Site with slug '{site_slug}' not found.")

        gen = SiteGenerator()
        if site.structure_locked:
            created = gen.fill_missing_content(site, limit=50)
        else:
            created = gen.expand_site(site, max_new_pages=10)

        self.stdout.write(
            self.style.SUCCESS(
                f"Expanded site '{site_slug}', pages created/updated: {created}"
            )
        )
