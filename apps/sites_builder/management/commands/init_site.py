from django.utils.text import slugify
from django.core.management.base import BaseCommand, CommandError
from apps.sites_builder.models import Site
from apps.sites_builder.services.static_builder import StaticBuilder


class Command(BaseCommand):
    help = "Create a new Site and generate its root page."

    def add_arguments(self, parser):
        parser.add_argument("developer_name", type=str, help="Developer name (existing or new).")
        parser.add_argument("site_name", type=str, help="Site name.")
        parser.add_argument("description", type=str, help="Short description to seed GPT.")

    def handle(self, *args, **options):
        dev_name = options["developer_name"]
        site_name = options["site_name"]
        description = options["description"]

        developer, _ = Developer.objects.get_or_create(name=dev_name)

        slug = slugify(site_name)
        if Site.objects.filter(slug=slug).exists():
            raise CommandError(
                f"A Site with slug '{slug}' already exists. "
                f"Use a different site name or delete the existing Site first."
            )

        site = Site.objects.create(
            owner=developer,
            name=site_name,
            slug=slug,
            description=description,
        )

        gen = SiteGenerator()
        root = gen.ensure_root_page(site)

        self.stdout.write(
            self.style.SUCCESS(
                f"Site '{site.slug}' created with root page '{root.title}'."
            )
        )
