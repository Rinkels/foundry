from django.core.management.base import BaseCommand, CommandError
from ...models import Site, DeploymentTarget
from ...services.deployment import Deployer


class Command(BaseCommand):
    help = "Deploy a site's static files using its DeploymentTarget."

    def add_arguments(self, parser):
        parser.add_argument("site_slug", type=str)
        parser.add_argument(
            "--target-name",
            type=str,
            default=None,
            help="Optional deployment target name. If omitted, use default target.",
        )
        parser.add_argument(
            "--backup", action="store_true",
            help="FTP only: download the current remote site to output/backups/<slug>/<ts>/ before uploading.",
        )
        parser.add_argument(
            "--prune-stale", action="store_true",
            help="FTP only: after upload, delete remote files not in the build (.well-known, cgi-bin, .htaccess etc. are protected).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Show the deploy plan (upload count, backup destination, exact stale-file list) without changing anything.",
        )

    def handle(self, *args, **options):
        site_slug = options["site_slug"]
        target_name = options["target_name"]

        try:
            site = Site.objects.get(slug=site_slug)
        except Site.DoesNotExist:
            raise CommandError(f"Site with slug '{site_slug}' not found.")

        if target_name:
            try:
                target = site.deployment_targets.get(name=target_name)
            except DeploymentTarget.DoesNotExist:
                raise CommandError(
                    f"DeploymentTarget '{target_name}' not found for site '{site_slug}'."
                )
        else:
            target = site.deployment_targets.filter(is_default=True).first()
            if not target:
                raise CommandError(
                    f"No default DeploymentTarget found for site '{site_slug}'. "
                    "Specify --target-name."
                )

        deployer = Deployer()

        # The current Deployer (rewritten for Cloudflare Pages support) does not
        # implement backup/prune/dry-run. Honour the flags loudly, not silently.
        import inspect
        supported = set(inspect.signature(deployer.deploy).parameters)
        kwargs = {}
        for opt in ("backup", "prune_stale", "dry_run"):
            if options.get(opt):
                if opt in supported:
                    kwargs[opt] = True
                else:
                    raise CommandError(
                        f"--{opt.replace('_', '-')} is not supported by the current "
                        "Deployer implementation (removed in the Cloudflare Pages rework)."
                    )

        deployer.deploy(target, **kwargs)

        if options.get("dry_run"):
            self.stdout.write(self.style.WARNING("Dry run — nothing was changed."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Deployed site '{site_slug}' using target '{target.name}' ({target.type})."
                )
            )
