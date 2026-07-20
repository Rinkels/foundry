#python manage.py janus_seed_predd --name "Zen Cyber" --website "https://zencyber.ca"

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.janus.models import (
    TargetCompany,
    ScoreScale,
    DDTemplate,
    DDSection,
    DDCriterion,
    DueDiligenceRun,
    DDResponse,
    DDQuantitativeSnapshot,
)


class Command(BaseCommand):
    help = "Seed NewCo: Preliminary Due Diligence (Pre-DD) template + Round 1 run + blank responses + snapshot."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="Target company name (exact).")
        parser.add_argument("--website", default="", help="Target website URL.")
        parser.add_argument("--round", type=int, default=1, help="Round number (default 1).")

    @transaction.atomic
    def handle(self, *args, **options):
        # -----------------------------
        # 1) Ensure scoring scale exists
        # -----------------------------
        maturity_0_5, _ = ScoreScale.objects.get_or_create(
            name="0-5 maturity",
            defaults={
                "min_value": 0,
                "max_value": 5,
                "labels_json": {"0": "none", "3": "adequate", "5": "excellent"},
            },
        )

        # -----------------------------
        # 2) Ensure target exists
        # -----------------------------
        target_name = options["name"].strip()
        target_website = (options.get("website") or "").strip()
        round_number = int(options.get("round") or 1)

        target, _ = TargetCompany.objects.get_or_create(
            name=target_name,
            defaults={
                "website": target_website,
                "deal_stage": getattr(TargetCompany.DealStage, "DILIGENCE", "diligence"),
                "notes": "Seeded target for due diligence.",
            },
        )

        # Only set website if blank and a website was provided
        if target_website and not getattr(target, "website", ""):
            target.website = target_website
            target.save(update_fields=["website", "updated_at"])

        # -----------------------------
        # 3) Create/Update template
        # -----------------------------
        template, _ = DDTemplate.objects.get_or_create(
            name="Preliminary Due Diligence (Pre-DD)",
            version="v1",
            defaults={
                "description": "Stage-gate template: 5 most important questions each for Technical, Financial, Commercial.",
                "is_active": True,
            },
        )
        if not template.is_active:
            template.is_active = True
            template.save(update_fields=["is_active", "updated_at"])

        def upsert_section(title: str, weight: int, order: int):
            sec, _ = DDSection.objects.get_or_create(
                template=template,
                title=title,
                defaults={"weight": weight, "order_index": order},
            )
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

        def upsert_criterion(
            section,
            title: str,
            weight: int,
            order: int,
            evidence_required: bool = True,
            description: str = "",
        ):
            crit, _ = DDCriterion.objects.get_or_create(
                section=section,
                title=title,
                defaults={
                    "weight": weight,
                    "order_index": order,
                    "scoring_scale": maturity_0_5,
                    "evidence_required": evidence_required,
                    "non_negotiable": True,
                    "pass_threshold": 3,
                    "description": description,
                },
            )

            updates = {}
            for field, value in [
                ("weight", weight),
                ("order_index", order),
                ("scoring_scale", maturity_0_5),
                ("evidence_required", evidence_required),
                ("non_negotiable", True),
                ("pass_threshold", 3),
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

        # -----------------------------
        # 4) Sections (5 each)
        # -----------------------------
        s_tech = upsert_section("Pre-DD: Technical Viability", 34, 10)
        s_fin = upsert_section("Pre-DD: Financial Integrity", 33, 20)
        s_com = upsert_section("Pre-DD: Commercial Strength", 33, 30)

        # ---- Technical (5) ----
        upsert_criterion(s_tech, "Security posture is acceptable for our risk tolerance", 20, 10, True,
                         "Access control, secrets handling, vuln hygiene, incident history, baseline security practices.")
        upsert_criterion(s_tech, "Core architecture is maintainable and scalable (not a rewrite trap)", 20, 20, True,
                         "Architecture clarity, modularity, coupling, scaling constraints.")
        upsert_criterion(s_tech, "Codebase quality supports continued delivery without heroics", 20, 30, True,
                         "Testing, CI/CD, standards, complexity hotspots, technical debt.")
        upsert_criterion(s_tech, "Data/IP ownership and critical dependencies are clear and acceptable", 20, 40, True,
                         "Repo ownership, licensing, third-party dependencies, vendor lock-in risks.")
        upsert_criterion(s_tech, "Key-person dependency risk is manageable", 20, 50, True,
                         "Bus factor, documentation, support/on-call, knowledge distribution.")

        # ---- Financial (5) ----
        upsert_criterion(s_fin, "Revenue is real, verifiable, and reconciles across systems", 20, 10, True,
                         "Revenue proof: billing platform, bank statements, GL tie-outs, contract support.")
        upsert_criterion(s_fin, "Gross margin and COGS assumptions are credible", 20, 20, True,
                         "COGS definition, hosting/support labor, vendor costs, margin stability.")
        upsert_criterion(s_fin, "Customer concentration risk is quantified and acceptable", 20, 30, True,
                         "Top customer % of revenue, churn sensitivity, mitigation plan.")
        upsert_criterion(s_fin, "Cash burn and runway are understood and sufficient for the plan", 20, 40, True,
                         "Burn rate, runway, obligations, near-term cash risks.")
        upsert_criterion(s_fin, "No hidden liabilities likely to change valuation materially", 20, 50, True,
                         "Debt/leases, tax posture, disputes/claims, contractual liabilities.")

        # ---- Commercial (5) ----
        upsert_criterion(s_com, "ICP and positioning are clear and repeatable", 20, 10, True,
                         "Defined ICP, buyer pain, differentiation, why they win.")
        upsert_criterion(s_com, "Retention health is acceptable (churn understood, NRR plausible)", 20, 20, True,
                         "Churn/NRR definition, cohorts, renewal dynamics, CS motion.")
        upsert_criterion(s_com, "Pipeline is real and measurable (not vibes) and win-rate is credible", 20, 30, True,
                         "CRM hygiene, stage definitions, conversion metrics, forecast discipline.")
        upsert_criterion(s_com, "Pricing and discount discipline support scalable growth", 20, 40, True,
                         "Pricing model, discount approvals, packaging clarity, margin impact.")
        upsert_criterion(s_com, "Strategic fit is strong with TrustBIX/Mindsgate platform thesis", 20, 50, True,
                         "Cross-sell potential, integration synergies, strengthens group strategy.")

        # -----------------------------
        # 5) Create Round 1 run
        # verdict has no NONE option; keep blank.
        # -----------------------------
        run, _ = DueDiligenceRun.objects.get_or_create(
            target_company=target,
            template=template,
            round_number=round_number,
            defaults={
                "status": DueDiligenceRun.Status.IN_PROGRESS,
                "verdict": "",  # blank allowed
            },
        )

        # If it already existed and is draft, advance it
        if run.status == DueDiligenceRun.Status.DRAFT:
            run.status = DueDiligenceRun.Status.IN_PROGRESS
            run.save(update_fields=["status", "updated_at"])

        # -----------------------------
        # 6) Ensure blank responses exist
        # -----------------------------
        crit_ids = list(
            DDCriterion.objects.filter(section__template=template).values_list("id", flat=True)
        )
        existing = set(
            DDResponse.objects.filter(run=run).values_list("criterion_id", flat=True)
        )
        missing = [cid for cid in crit_ids if cid not in existing]
        if missing:
            DDResponse.objects.bulk_create(
                [DDResponse(run=run, criterion_id=cid) for cid in missing],
                ignore_conflicts=True,
            )

        # -----------------------------
        # 7) Ensure snapshot exists
        # -----------------------------
        DDQuantitativeSnapshot.objects.get_or_create(run=run)

        # Recalc after seeding responses
        run.recalc_scores(save=True)

        self.stdout.write(self.style.SUCCESS(
            "Seeded Pre-DD template v1 + Hire Output Round 1 run + blank responses + snapshot."
        ))
