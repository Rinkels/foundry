"""Run an Aegis exposure check.

Two modes:

    # Existing profile(s)
    python manage.py aegis_scan --profile acme-corp
    python manage.py aegis_scan --all

    # Ad-hoc: point it at a repo or org without creating a profile first.
    # (An ephemeral profile is created so findings are still tracked.)
    python manage.py aegis_scan --repo Rinkels/xevent --keywords "xevent,miventi"
    python manage.py aegis_scan --org Rinkels
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.aegis.models import Exposure, WatchProfile
from apps.aegis.services import scan as scan_service


class Command(BaseCommand):
    help = "Scan public GitHub for exposed credentials and tracked keywords."

    def add_arguments(self, parser):
        parser.add_argument("--profile", help="Slug of an existing WatchProfile.")
        parser.add_argument("--all", action="store_true", help="Scan every enabled profile.")
        parser.add_argument("--repo", help="Ad-hoc target: owner/name.")
        parser.add_argument("--org", help="Ad-hoc target: a GitHub org or user login.")
        parser.add_argument("--keywords", default="", help="Comma-separated tenant keywords.")
        parser.add_argument(
            "--installation", type=int, default=None,
            help="GitHub App installation_id to authenticate with (ad-hoc targets). "
                 "Defaults to the only installation if there is exactly one.",
        )
        parser.add_argument(
            "--max-queries", type=int, default=None,
            help="Override the per-run query cap (default: settings.AEGIS_MAX_QUERIES).",
        )

    def handle(self, *args, **opts):
        profiles = self._resolve_profiles(opts)
        if not profiles:
            raise CommandError("Nothing to scan. Pass --profile, --all, --repo or --org.")

        for profile in profiles:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n▶ {profile.name}"))
            run = scan_service.run_scan(profile, max_queries=opts.get("max_queries"))
            self._report(profile, run)

    def _resolve_profiles(self, opts) -> list[WatchProfile]:
        if opts.get("all"):
            return list(WatchProfile.objects.filter(enabled=True))

        if opts.get("profile"):
            try:
                return [WatchProfile.objects.get(slug=opts["profile"])]
            except WatchProfile.DoesNotExist:
                raise CommandError(f"No profile with slug '{opts['profile']}'.") from None

        target = opts.get("repo") or opts.get("org")
        if not target:
            return []

        # Ad-hoc target: reuse the profile if we've scanned this target before,
        # so findings accumulate instead of duplicating across runs.
        slug = slugify(f"adhoc-{target}")[:200]
        profile, created = WatchProfile.objects.get_or_create(
            slug=slug,
            defaults={"name": f"Ad-hoc: {target}", "enabled": False},
        )
        if opts.get("repo"):
            profile.github_repos = opts["repo"]
        else:
            profile.github_orgs = opts["org"]
        if opts.get("keywords"):
            profile.keywords = "\n".join(
                k.strip() for k in opts["keywords"].split(",") if k.strip()
            )

        # Ad-hoc runs have no tenant, so pick an installation explicitly rather
        # than letting resolve_token guess — guessing across tenants is exactly
        # the mistake this app must not make.
        from apps.atlas.models import GitHubInstallation
        if opts.get("installation"):
            profile.github_installation = GitHubInstallation.objects.filter(
                installation_id=opts["installation"]
            ).first()
            if not profile.github_installation:
                raise CommandError(f"No installation with id {opts['installation']}.")
        elif not profile.github_installation_id:
            installs = list(GitHubInstallation.objects.all()[:2])
            if len(installs) == 1:
                profile.github_installation = installs[0]
                self.stdout.write(f"Using GitHub installation '{installs[0].account_login}'.")

        profile.save()

        if created:
            self.stdout.write(f"Created ad-hoc profile '{profile.slug}'.")
        return [profile]

    def _report(self, profile: WatchProfile, run) -> None:
        if run.status == run.STATUS_FAILED:
            self.stdout.write(self.style.ERROR("  FAILED"))
            self.stdout.write(run.log)
            return

        self.stdout.write(
            f"  {run.queries_run} queries · {run.files_examined} files · "
            f"{run.findings_new} new · {run.findings_seen} repeat"
        )
        if run.queries_skipped:
            self.stdout.write(
                self.style.WARNING(
                    f"  {run.queries_skipped} queries skipped by the cap — coverage is partial."
                )
            )

        open_ex = profile.exposures.filter(
            status__in=[Exposure.STATUS_NEW, Exposure.STATUS_TRIAGED]
        ).order_by("severity", "-last_seen")

        if not open_ex:
            self.stdout.write(self.style.SUCCESS("  No open exposures."))
            return

        styles = {
            Exposure.SEV_CRITICAL: self.style.ERROR,
            Exposure.SEV_HIGH: self.style.ERROR,
            Exposure.SEV_MEDIUM: self.style.WARNING,
        }
        for ex in open_ex[:40]:
            style = styles.get(ex.severity, self.style.NOTICE)
            self.stdout.write(
                style(f"  [{ex.severity.upper():8}] {ex.detector_label} — "
                      f"{ex.repo_full_name}/{ex.file_path}")
            )
            if ex.note:
                self.stdout.write(f"             {ex.note}")

        if open_ex.count() > 40:
            self.stdout.write(f"  … and {open_ex.count() - 40} more (see /aegis/p/{profile.slug}/).")
