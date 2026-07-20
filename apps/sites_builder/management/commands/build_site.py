from django.core.management.base import BaseCommand, CommandError
from ...models import Site
from ...services.static_builder import StaticBuilder


class Command(BaseCommand):
    help = "Build static HTML files for a site."

    def add_arguments(self, parser):
        parser.add_argument("site_slug", type=str)

    def handle(self, *args, **options):
        site_slug = options["site_slug"]

        try:
            site = Site.objects.get(slug=site_slug)
        except Site.DoesNotExist:
            raise CommandError(f"Site with slug '{site_slug}' not found.")

        builder = StaticBuilder()
        out_dir = builder.build_site(site)

        self.stdout.write(
            self.style.SUCCESS(f"Built static site for '{site_slug}' at: {out_dir}")
        )
