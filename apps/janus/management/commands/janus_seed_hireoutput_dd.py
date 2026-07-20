from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.janus.models import (
    TargetCompany,
    ScoreScale,
    DDTemplate,
    DDSection,
    DDCriterion,
    DueDiligenceRun,
    DDParticipant,
)


def get_or_create_user(username: str, email: str | None = None, first_name: str = "", last_name: str = ""):
    """
    Tries to find a user by username, then email. Creates a placeholder user if not found.
    Works with default Django User model and most custom ones that keep username/email.
    """
    User = settings.AUTH_USER_MODEL
    # settings.AUTH_USER_MODEL is a string; use get_user_model for safety
    from django.contrib.auth import get_user_model

    U = get_user_model()

    user = None
    if username:
        user = U.objects.filter(username__iexact=username).first()

    if not user and email:
        user = U.objects.filter(email__iexact=email).first()

    if user:
        return user

    # Create placeholder
    kwargs = {}
    if hasattr(U, "username"):
        kwargs["username"] = username
    if email and hasattr(U, "email"):
        kwargs["email"] = email
    if hasattr(U, "first_name"):
        kwargs["first_name"] = first_name
    if hasattr(U, "last_name"):
        kwargs["last_name"] = last_name

    user = U.objects.create(**kwargs)
    if hasattr(user, "set_unusable_password"):
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


class Command(BaseCommand):
    help = "Seed the first Technical Due Diligence run for Hire Output Tools."

    @transaction.atomic
    def handle(self, *args, **options):
        # ---- Users ----
        # Adjust usernames/emails here if your auth uses different identifiers.
        ruan = get_or_create_user(
            username="ruan",
            email=None,
            first_name="Ruan",
            last_name="Wannenburg",
        )
        ted = get_or_create_user(
            username="ted",
            email=None,
            first_name="Ted",
            last_name="Powers",
        )

        # ---- Scales ----
        maturity_0_5, _ = ScoreScale.objects.get_or_create(
            name="0-5 maturity",
            defaults={"min_value": 0, "max_value": 5, "labels_json": {"0": "none", "3": "adequate", "5": "excellent"}},
        )
        pass_fail, _ = ScoreScale.objects.get_or_create(
            name="pass/fail",
            defaults={"min_value": 0, "max_value": 1, "labels_json": {"0": "fail", "1": "pass"}},
        )

        # ---- Template ----
        template, _ = DDTemplate.objects.get_or_create(
            name="Technical Due Diligence",
            version="v1",
            defaults={"description": "Baseline technical due diligence rubric (Janus).", "is_active": True},
        )

        # Helper to upsert section + criteria (idempotent seeding)
        def upsert_section(title: str, weight: int, order: int):
            sec, _ = DDSection.objects.get_or_create(
                template=template,
                title=title,
                defaults={"weight": weight, "order_index": order},
            )
            # keep seed idempotent but allow tuning weights/orders later if you re-run:
            updates = {}
            if sec.weight != weight:
                updates["weight"] = weight
            if sec.order_index != order:
                updates["order_index"] = order
            if updates:
                for k, v in updates.items():
                    setattr(sec, k, v)
                sec.save(update_fields=list(updates.keys()) + ["updated_at"])
            return sec

        def upsert_criterion(section, title: str, weight: int, order: int, scale, evidence_required=False, non_negotiable=False, pass_threshold=None, description=""):
            crit, _ = DDCriterion.objects.get_or_create(
                section=section,
                title=title,
                defaults={
                    "weight": weight,
                    "order_index": order,
                    "scoring_scale": scale,
                    "evidence_required": evidence_required,
                    "non_negotiable": non_negotiable,
                    "pass_threshold": pass_threshold,
                    "description": description,
                },
            )
            # Update if changed
            updates = {}
            for field, value in [
                ("weight", weight),
                ("order_index", order),
                ("scoring_scale", scale),
                ("evidence_required", evidence_required),
                ("non_negotiable", non_negotiable),
                ("pass_threshold", pass_threshold),
            ]:
                if getattr(crit, field) != value:
                    updates[field] = value
            if description and crit.description != description:
                updates["description"] = description

            if updates:
                for k, v in updates.items():
                    setattr(crit, k, v)
                crit.save(update_fields=list(updates.keys()) + ["updated_at"])
            return crit

        # ---- Sections + Criteria (starter pack) ----
        s_arch = upsert_section("Architecture & Stack", 20, 10)
        upsert_criterion(s_arch, "Stack clarity & ownership", 25, 10, maturity_0_5, True, False, None, "Can we clearly map services, repos, and owners?")
        upsert_criterion(s_arch, "Deployment architecture & environments", 25, 20, maturity_0_5, True)
        upsert_criterion(s_arch, "Scalability constraints known", 25, 30, maturity_0_5, False)
        upsert_criterion(s_arch, "Observability (logs/metrics/tracing)", 25, 40, maturity_0_5, True)

        s_sec = upsert_section("Security & Compliance", 25, 20)
        upsert_criterion(s_sec, "Authentication/authorization model", 20, 10, maturity_0_5, True, True, 3)
        upsert_criterion(s_sec, "Secrets handling & rotation", 20, 20, maturity_0_5, True, True, 3)
        upsert_criterion(s_sec, "Dependency & vulnerability management", 20, 30, maturity_0_5, True)
        upsert_criterion(s_sec, "Incident history & response process", 20, 40, maturity_0_5, False)
        upsert_criterion(s_sec, "Data privacy posture (PII)", 20, 50, maturity_0_5, True, True, 3)

        s_code = upsert_section("Code Quality & Delivery", 20, 30)
        upsert_criterion(s_code, "Repo hygiene (branching, PRs, reviews)", 25, 10, maturity_0_5, True)
        upsert_criterion(s_code, "Test coverage & test strategy", 25, 20, maturity_0_5, True)
        upsert_criterion(s_code, "CI/CD maturity", 25, 30, maturity_0_5, True)
        upsert_criterion(s_code, "Release discipline & rollback", 25, 40, maturity_0_5, False)

        s_data = upsert_section("Data, IP & Portability", 20, 40)
        upsert_criterion(s_data, "Data ownership & exportability", 34, 10, maturity_0_5, True, True, 3)
        upsert_criterion(s_data, "IP clarity (licenses, 3rd-party)", 33, 20, maturity_0_5, True, True, 3)
        upsert_criterion(s_data, "Vendor lock-in & portability", 33, 30, maturity_0_5, False)

        s_team = upsert_section("Team & Knowledge Risk", 15, 50)
        upsert_criterion(s_team, "Bus factor & succession", 50, 10, maturity_0_5, True)
        upsert_criterion(s_team, "Documentation reality check", 50, 20, maturity_0_5, False)

        # ---- Target company ----
        target, _ = TargetCompany.objects.get_or_create(
            name="Hire Output Tools",
            defaults={
                "website": "https://www.hireoutput.tools",
                "deal_stage": TargetCompany.DealStage.DILIGENCE,
                "owner": ruan,
                "notes": "Seeded for first technical due diligence run.",
            },
        )
        # Ensure website fixed if it existed with typo
        if target.website != "https://www.hireoutput.tools":
            target.website = "https://www.hireoutput.tools"
            target.save(update_fields=["website", "updated_at"])

        # ---- DD Run ----
        run, created = DueDiligenceRun.objects.get_or_create(
            target_company=target,
            template=template,
            round_number=1,
            defaults={
                "status": DueDiligenceRun.Status.IN_PROGRESS,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created DD run: {run}"))
        else:
            self.stdout.write(self.style.WARNING(f"DD run already exists: {run}"))

        # ---- Participants ----
        DDParticipant.objects.get_or_create(
            run=run,
            user=ruan,
            defaults={"role": DDParticipant.Role.LEAD, "permission": DDParticipant.Permission.ADMIN},
        )
        DDParticipant.objects.get_or_create(
            run=run,
            user=ted,
            defaults={"role": DDParticipant.Role.REVIEWER, "permission": DDParticipant.Permission.SCORE},
        )

        # Recalc score (will be 0 until responses entered)
        run.recalc_scores(save=True)

        self.stdout.write(self.style.SUCCESS("Seed complete. Participants assigned: Ruan (Lead/Admin), Ted (Reviewer/Score)."))
        self.stdout.write("Next: enter DDResponse scores in admin, and attach evidence links/files.")
