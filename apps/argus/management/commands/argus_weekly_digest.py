"""Print (and optionally email) the Foundry weekly digest. Wire to cron for a
Monday-morning summary:  python manage.py argus_weekly_digest --email you@x.com"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from apps.argus.services.digest import build_digest, digest_text


class Command(BaseCommand):
    help = "Print the Foundry weekly digest (and optionally email it)."

    def add_arguments(self, parser):
        parser.add_argument("--email", help="Send the digest to this address.")

    def handle(self, *args, **opts):
        text = digest_text(build_digest())
        self.stdout.write(text)
        if opts.get("email"):
            send_mail(
                subject=f"Foundry weekly digest",
                message=text,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[opts["email"]],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f"\nEmailed to {opts['email']}"))
