from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.athena.models import AppContextSnapshot, AthenaStudioRun
from apps.athena.services import context_export


class Command(BaseCommand):
    help = "Export an approved AppContextSnapshot (and optional design doc) into a target repo."

    def add_arguments(self, parser):
        parser.add_argument("--key", required=True, help="Snapshot key, e.g. nurbai_produce")
        parser.add_argument("--version", type=int, default=None, help="Snapshot version (default: latest approved)")
        parser.add_argument("--target", default=None, help="Target repo dir (default: resolve via CloudProject.source_path)")
        parser.add_argument("--design-doc", dest="design_doc", default=None,
                            help="AthenaStudioRun id to also export as the design doc")

    def handle(self, *args, **opts):
        key, version = opts["key"], opts["version"]
        if version is not None:
            snap = AppContextSnapshot.objects.filter(key=key, version=version).first()
        else:
            snap = AppContextSnapshot.objects.filter(key=key, is_approved=True).order_by("-version").first()
        if snap is None:
            raise CommandError(f"No snapshot found for key='{key}'"
                               + (f" version={version}" if version is not None else " (approved)"))

        try:
            target = Path(opts["target"]) if opts["target"] else context_export.resolve_target_for_snapshot(snap)
            ce = context_export.export_context(snap, target)
        except context_export.ExportError as exc:
            raise CommandError(str(exc))

        self.stdout.write(self.style.SUCCESS(
            f"context -> {ce.target_path}  ({ce.bytes_written} bytes, sha256 {ce.sha256[:12]})"
        ))

        if opts["design_doc"]:
            run = AthenaStudioRun.objects.filter(pk=opts["design_doc"]).first()
            if run is None:
                raise CommandError(f"AthenaStudioRun id={opts['design_doc']} not found.")
            try:
                de = context_export.export_design_doc(run, target)
            except context_export.ExportError as exc:
                raise CommandError(str(exc))
            self.stdout.write(self.style.SUCCESS(f"design_doc -> {de.target_path}"))
