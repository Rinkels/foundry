from django.db import migrations


def seed_ifms_scorecard(apps, schema_editor):
    ScorecardTemplate = apps.get_model("janus", "ScorecardTemplate")
    ScorecardSection = apps.get_model("janus", "ScorecardSection")
    ScorecardCriterion = apps.get_model("janus", "ScorecardCriterion")

    template, created = ScorecardTemplate.objects.get_or_create(
        name="IFMS Acquisition – Distressed Indoor Farms (Cannabis & Small Indoor)",
        defaults={
            "description": "Evaluate distressed/failed indoor farms for acquisition based on infrastructure salvageability and IFMS leverage.",
            "version": "v1.0",
            "is_active": True,
        }
    )

    # If it already exists, avoid duplicating sections/criteria
    if not created and template.sections.exists():
        return

    sections_data = [
        ("Physical & Infrastructure Salvageability", "Is the facility physically worth buying?", 25, 10, [
            ("Facility condition", "Roof, HVAC, insulation, general integrity.", 5, False),
            ("Electrical capacity", "Load headroom for lighting and controls.", 5, False),
            ("Water & drainage", "Recirculation potential, drainage, leak risk.", 5, False),
            ("Grow infrastructure", "Racks/tables/irrigation usable or cheap to restore.", 5, False),
            ("Sensor retrofit ease", "Can IFMS sensors be installed quickly?", 5, False),
        ]),
        ("Operational Failure Type", "Is the failure operational (fixable) vs structural (not)?", 20, 20, [
            ("Process control weakness", "Inconsistent yields, unstable environment control.", 5, False),
            ("Manual ops / spreadsheet dependence", "No automation, paper logs, tribal knowledge.", 5, False),
            ("Staff skill gaps", "Grow success depends on a few individuals.", 5, False),
            ("No data feedback loops", "No trend tracking, no root-cause ability.", 5, False),
            ("Overbuilt / underused capacity", "CapEx sunk but output low.", 5, False),
        ]),
        ("IFMS Leverage Potential", "Can IFMS become system of record and improve outcomes fast?", 25, 30, [
            ("Environmental sensor coverage", "Temp/RH/CO2/PPFD can be measured reliably.", 5, False),
            ("Automation potential", "Lights/fans/pumps can be controlled.", 5, False),
            ("AI optimization upside", "Clear levers to improve yield/energy/water.", 5, False),
            ("Digital SOP potential", "Processes can be standardized & trained.", 5, False),
            ("Traceability / compliance value", "Demand exists for audits, ESG, provenance.", 5, False),
        ]),
        ("Financial Reset Viability", "Does the deal structure allow a clean reset?", 15, 40, [
            ("Asset discount", "Can assets be bought at strong discount?", 5, False),
            ("Debt cleanliness", "Asset-only purchase feasible (avoid liabilities).", 5, True),  # hard-stop candidate
            ("Restart cost", "Cost/time to first harvest is reasonable.", 5, False),
            ("Energy efficiency upside", "Lighting/HVAC improvements possible.", 5, False),
            ("Labor reduction via automation", "Automation can reduce headcount or overtime.", 5, False),
        ]),
        ("Founder / Operator Dependency", "Can the operation run without the original crew?", 10, 50, [
            ("Founder dependency level", "Success tied to one person?", 5, False),
            ("SOP documentation gap", "Processes undocumented?", 5, False),
            ("Tribal knowledge dominance", "Critical knowledge not transferable?", 5, False),
            ("Ops independence potential", "Can ops stabilize under new team?", 5, False),
        ]),
        ("Regulatory & Repurposing Flexibility", "Can the facility be repurposed or simplified?", 5, 60, [
            ("Repurpose feasibility", "Cannabis → leafy greens or other crops viable.", 5, False),
            ("Licensing constraints", "Licensing transferable or irrelevant to new crop.", 5, False),
            ("Zoning flexibility", "No zoning dead-end risks.", 5, True),  # hard-stop candidate
        ]),
    ]

    for section_name, section_desc, weight, order, criteria in sections_data:
        section = ScorecardSection.objects.create(
            template=template,
            name=section_name,
            description=section_desc,
            weight=weight,
            order=order,
        )
        for i, (crit_name, crit_desc, max_score, hard_stop) in enumerate(criteria, start=1):
            ScorecardCriterion.objects.create(
                section=section,
                name=crit_name,
                description=crit_desc,
                max_score=max_score,
                is_hard_stop=hard_stop,
                order=i * 10,
            )


def unseed_ifms_scorecard(apps, schema_editor):
    ScorecardTemplate = apps.get_model("janus", "ScorecardTemplate")
    tpl = ScorecardTemplate.objects.filter(
        name="IFMS Acquisition – Distressed Indoor Farms (Cannabis & Small Indoor)"
    ).first()
    if tpl:
        tpl.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("janus", "0003_scorecardsection_scorecardtemplate_and_more"),  # <-- update this
    ]

    operations = [
        migrations.RunPython(seed_ifms_scorecard, unseed_ifms_scorecard),
    ]
