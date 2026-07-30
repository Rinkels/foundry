from django.core.management.base import BaseCommand

from apps.codex.scanner import library_roots, scan


class Command(BaseCommand):
    help = "Discover .md files under MD_LIBRARY_ROOTS and (re)index them into Codex."

    def handle(self, *args, **options):
        self.stdout.write("Roots: " + ", ".join(str(r) for r in library_roots()))
        s = scan()
        self.stdout.write(self.style.SUCCESS(
            f"Codex: {s['total']} docs indexed "
            f"({s['added']} new, {s['updated']} updated, {s['pruned']} pruned)."
        ))
