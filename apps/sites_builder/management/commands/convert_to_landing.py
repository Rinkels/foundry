from django.core.management.base import BaseCommand, CommandError

from ...models import Site
from ...services.generator import SiteGenerator
from ...services.static_builder import StaticBuilder


class Command(BaseCommand):
    help = "Convert a site's home page into a generated marketing landing page (page_type=landing)."

    def add_arguments(self, parser):
        parser.add_argument("slug", help="Site slug, e.g. albertaincubator")
        parser.add_argument("--no-hero", action="store_true", help="Skip hero image generation.")
        parser.add_argument("--no-card-images", action="store_true", help="Skip per-card image generation.")
        parser.add_argument("--theme", default="editorial", help="Theme to apply (default: editorial).")
        parser.add_argument("--no-build", action="store_true", help="Don't rebuild the static site afterward.")

    def handle(self, *args, **o):
        try:
            site = Site.objects.get(slug=o["slug"])
        except Site.DoesNotExist:
            raise CommandError(f"No site with slug '{o['slug']}'.")

        self.stdout.write(f"Generating landing sections for '{site.slug}'…")
        root = SiteGenerator().convert_home_to_landing(
            site, generate_hero=not o["no_hero"],
            generate_card_images=not o["no_card_images"], theme=o["theme"],
        )
        types = [b.get("type") for b in (root.landing_sections or [])]
        self.stdout.write(self.style.SUCCESS(f"  {len(types)} sections: {types}"))

        if not o["no_build"]:
            out = StaticBuilder().build_site(site)
            self.stdout.write(self.style.SUCCESS(f"Rebuilt static site at: {out}"))
        else:
            self.stdout.write("Skipped rebuild (--no-build).")
