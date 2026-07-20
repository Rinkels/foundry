#python manage.py janus_seed_hireoutput_financial_template
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
    help = "Seed Janus template: Financial Due Diligence (v1) for reuse (templates only; no runs)."

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
            name="Financial Due Diligence",
            version="v1",
            defaults={
                "description": "Baseline financial due diligence rubric (Janus).",
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

        s_fs = upsert_section("Financial Statements & Controls", 20, 10)
        upsert_criterion(s_fs, "Financial statements completeness and accuracy", 25, 10, True, True, 3,
                         "Are historical financials complete, reconcilable, and reliable?")
        upsert_criterion(s_fs, "Accounting policies and consistency (GAAP/IFRS)", 25, 20, True, False, None,
                         "Are accounting policies documented and consistently applied?")
        upsert_criterion(s_fs, "Monthly close process and cadence", 25, 30, True, False, None,
                         "Is close performed on a predictable schedule with review controls?")
        upsert_criterion(s_fs, "Internal controls and segregation of duties", 25, 40, True, True, 3,
                         "Are there controls to prevent/identify errors and fraud risk?")

        s_rev = upsert_section("Revenue Quality & Recognition", 20, 20)
        upsert_criterion(s_rev, "Revenue recognition approach fits contracts", 25, 10, True, True, 3,
                         "Does revenue recognition align with contract structure and obligations?")
        upsert_criterion(s_rev, "Recurring revenue clarity (MRR/ARR) and reconciliation", 25, 20, True, False, None,
                         "Is recurring revenue defined, tracked, and reconciled to accounting?")
        upsert_criterion(s_rev, "Churn/retention measured and trusted", 25, 30, True, False, None,
                         "Are churn/retention metrics defined and traceable to source systems?")
        upsert_criterion(s_rev, "Customer concentration risk understood", 25, 40, True, True, 3,
                         "Is concentration measured, monitored, and disclosed with mitigation?")

        s_unit = upsert_section("Unit Economics & Margin", 15, 30)
        upsert_criterion(s_unit, "Gross margin accuracy (COGS definition + attribution)", 34, 10, True, False, None,
                         "Is COGS defined correctly and allocated consistently?")
        upsert_criterion(s_unit, "CAC, LTV, payback computed with defensible assumptions", 33, 20, True, False, None,
                         "Are CAC/LTV/payback metrics computed from real costs and cohorts?")
        upsert_criterion(s_unit, "Pricing/discounting discipline reflected in margin", 33, 30, True, False, None,
                         "Are discounts controlled and margins stable by segment?")

        s_wc = upsert_section("Working Capital, Cash & Runway", 15, 40)
        upsert_criterion(s_wc, "Cash position, burn, and runway visibility", 34, 10, True, True, 3,
                         "Is burn tracked and runway accurate with scenario sensitivity?")
        upsert_criterion(s_wc, "AR/AP health and collections process", 33, 20, True, False, None,
                         "Are receivables current and collections disciplined?")
        upsert_criterion(s_wc, "Deferred revenue and contract liabilities tracked", 33, 30, True, False, None,
                         "Are deferred revenues and contract liabilities accurately tracked?")

        s_tax = upsert_section("Tax, Legal & Contingent Liabilities", 15, 50)
        upsert_criterion(s_tax, "Tax filings up to date and risks identified", 34, 10, True, True, 3,
                         "Are corporate/payroll/sales taxes filed and risk exposure understood?")
        upsert_criterion(s_tax, "Outstanding liabilities (debt, leases, obligations) documented", 33, 20, True, True, 3,
                         "Are all obligations documented with terms and schedules?")
        upsert_criterion(s_tax, "Contingent liabilities (claims/disputes) surfaced", 33, 30, True, False, None,
                         "Are disputes, claims, or contingent liabilities identified and scoped?")

        s_fcst = upsert_section("Forecasting, Reporting & KPI Discipline", 15, 60)
        upsert_criterion(s_fcst, "Forecast model quality and assumptions", 34, 10, True, False, None,
                         "Is the model coherent, assumptions explicit, and tie-out plausible?")
        upsert_criterion(s_fcst, "Board/management reporting cadence and variance analysis", 33, 20, True, False, None,
                         "Are KPIs reported regularly with variance explanations?")
        upsert_criterion(s_fcst, "Single source of truth for financial KPIs", 33, 30, True, False, None,
                         "Do KPI numbers reconcile across accounting/CRM/billing sources?")

        # ---- Target company (optional: no runs created) ----
        TargetCompany.objects.get_or_create(
            name="Hire Output Tools",
            defaults={
                "website": "https://www.hireoutput.tools",
                "deal_stage": TargetCompany.DealStage.DILIGENCE,
                "notes": "Seeded target for due diligence templates (financial/commercial).",
            },
        )

        self.stdout.write(self.style.SUCCESS("Seeded template: Financial Due Diligence v1 (templates only)."))
