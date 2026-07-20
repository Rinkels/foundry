from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from apps.hermes.services.publisher import publish_newsletters_for_site


class Command(BaseCommand):
    help = "Build static newsletter pages into the site output folder."

    def add_arguments(self, parser):
        parser.add_argument("site_slug", type=str)

    def handle(self, *args, **options):
        site_slug = options["site_slug"].strip()

        # Adjust this to match your actual output root
        output_root = Path(getattr(settings, "SITES_OUTPUT_ROOT", Path("output/sites")))
        site_output_dir = (output_root / site_slug).resolve()

        if not site_output_dir.exists():
            raise CommandError(f"Site output dir not found: {site_output_dir}")

        written = publish_newsletters_for_site(site_output_dir=site_output_dir, site_context={
            "site_slug": site_slug,
        })

        self.stdout.write(self.style.SUCCESS(f"Published {len(written)} newsletter files."))
        for p in written[:10]:
            self.stdout.write(f" - {p}")
        if len(written) > 10:
            self.stdout.write(f" ... and {len(written)-10} more")
