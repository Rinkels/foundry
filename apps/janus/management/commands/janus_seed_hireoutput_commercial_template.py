# python manage.py janus_seed_hireoutput_commercial_template
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.janus.models import (
    TargetCompany,
    ScoreScale,
    DDTemplate,
    DDSection,
    DDCriterion,
)


class Command(BaseCommand):
    help = "Seed Janus template: Commercial Due Diligence (v1) for reuse (templates only; no runs)."

    @transaction.atomic
    def handle(self, *args, **options):
        # ---- Scale ----
        maturity_0_5, _ = ScoreScale.objects.get_or_create(
            name="0-5 maturity",
            defaults={
                "min_value": 0,
                "max_value": 5,
                "labels_json": {"0": "none", "3": "adequate", "5": "excellent"},
            },
        )

        # ---- Template ----
        template, _ = DDTemplate.objects.get_or_create(
            name="Commercial Due Diligence",
            version="v1",
            defaults={
                "description": "Baseline commercial due diligence rubric (Janus).",
                "is_active": True,
            },
        )

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
            evidence_required: bool = False,
            non_negotiable: bool = False,
            pass_threshold: int | None = None,
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
                    "non_negotiable": non_negotiable,
                    "pass_threshold": pass_threshold,
                    "description": description,
                },
            )
            updates = {}
            for field, value in [
                ("weight", weight),
                ("order_index", order),
                ("scoring_scale", maturity_0_5),
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

        # =========================
        # Sections + Criteria
        # =========================

        s_icp = upsert_section("ICP, Positioning & Value Proposition", 20, 10)
        upsert_criterion(s_icp, "ICP is defined, testable, and used in targeting", 25, 10, True, False, None,
                         "Is there a clear ideal customer profile used operationally?")
        upsert_criterion(s_icp, "Positioning is distinct and defensible vs competitors", 25, 20, True, False, None,
                         "Do buyers understand why this solution wins?")
        upsert_criterion(s_icp, "Value proposition is measurable (ROI story)", 25, 30, True, False, None,
                         "Is impact quantified with real customer outcomes?")
        upsert_criterion(s_icp, "Messaging consistency across website, decks, sales motion", 25, 40, False, False, None,
                         "Are claims consistent and credible across channels?")

        s_pipe = upsert_section("Pipeline Health & Sales Process", 20, 20)
        upsert_criterion(s_pipe, "Funnel metrics are tracked and reliable", 25, 10, True, False, None,
                         "Lead→SQL→Opp→Win conversion tracked with definitions.")
        upsert_criterion(s_pipe, "Sales stages are defined and adhered to", 25, 20, True, False, None,
                         "Is there a consistent stage gating discipline?")
        upsert_criterion(s_pipe, "CRM hygiene and forecasting accuracy", 25, 30, True, False, None,
                         "Can pipeline be trusted for forecast decisions?")
        upsert_criterion(s_pipe, "Sales cycle length and drivers understood", 25, 40, True, False, None,
                         "Do they know what accelerates or stalls deals?")

        s_cust = upsert_section("Customers, Retention & Expansion", 20, 30)
        upsert_criterion(s_cust, "Retention/churn is measured and understood", 25, 10, True, False, None,
                         "Do they know churn causes and cohorts?")
        upsert_criterion(s_cust, "Customer references available and credible", 25, 20, True, False, None,
                         "Can we validate outcomes with references?")
        upsert_criterion(s_cust, "Expansion motion exists (upsell/cross-sell)", 25, 30, True, False, None,
                         "Is there a repeatable land-and-expand path?")
        upsert_criterion(s_cust, "Customer concentration risk is understood", 25, 40, True, True, 3,
                         "If top customers dominate revenue, is there mitigation?")

        s_pricing = upsert_section("Pricing, Packaging & Monetization", 15, 40)
        upsert_criterion(s_pricing, "Pricing model matches buyer value and usage", 34, 10, True, False, None,
                         "Is the pricing model aligned with value metrics and willingness to pay?")
        upsert_criterion(s_pricing, "Discounting discipline and approvals", 33, 20, True, False, None,
                         "Are discounts controlled with guardrails?")
        upsert_criterion(s_pricing, "Contract terms support scalable selling", 33, 30, True, False, None,
                         "Are terms standardized, enforceable, and not bespoke chaos?")

        s_gtm = upsert_section("GTM Channels & Marketing Readiness", 15, 50)
        upsert_criterion(s_gtm, "Channel mix and acquisition sources are understood", 34, 10, True, False, None,
                         "Can they trace pipeline sources and cost per channel?")
        upsert_criterion(s_gtm, "Content/brand assets support the sales motion", 33, 20, False, False, None,
                         "Is there collateral that maps to stages and objections?")
        upsert_criterion(s_gtm, "Partnerships strategy and leverage potential", 33, 30, False, False, None,
                         "Are partners bringing measurable pipeline or distribution?")

        s_market = upsert_section("Market, Competition & Strategic Fit", 10, 60)
        upsert_criterion(s_market, "Market size and growth assumptions are credible", 34, 10, True, False, None,
                         "Is TAM/SAM/SOM grounded, not vibes?")
        upsert_criterion(s_market, "Competitive landscape mapped and differentiated", 33, 20, True, False, None,
                         "Do they understand substitutes and threats?")
        upsert_criterion(s_market, "Strategic fit and integration thesis is strong", 33, 30, True, False, None,
                         "Is there a clear integration and cross-sell story with TrustBIX/Mindsgate stack?")

        # ---- Target company (optional: no runs created) ----
        TargetCompany.objects.get_or_create(
            name="Hire Output Tools",
            defaults={
                "website": "https://www.hireoutput.tools",
                "deal_stage": TargetCompany.DealStage.DILIGENCE,
                "notes": "Seeded target for due diligence templates (financial/commercial).",
            },
        )

        self.stdout.write(self.style.SUCCESS("Seeded template: Commercial Due Diligence v1 (templates only)."))
