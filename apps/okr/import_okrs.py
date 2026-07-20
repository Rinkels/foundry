import json
from datetime import date
from okr.models import Strategy, Objective, KeyResult  # Adjust if your app is named differently

# Load the JSON structure (paste the JSON or load from a file)
okr_data = [
    {
        "strategy": "Market Leadership through Technology & Traceability",
        "objectives": [
            {
                "title": "Launch and scale AFSI ERP platform",
                "owner": "Ruan Wannenburg",
                "key_results": [
                    "MVP ERP system deployed for internal use by May 30",
                    "ERP deployed to 3 franchise pilot farms by Q3",
                    "Achieve 90% uptime and 80% daily usage rate across pilots",
                    "Train 100% of pilot users with feedback scores >80%"
                ]
            },
            {
                "title": "Operationalize Certified Origins module",
                "owner": "Ruan Wannenburg",
                "key_results": [
                    "Complete blockchain integration and trace one crop cycle by July",
                    "Obtain 1 certification or government endorsement by Q4",
                    "Create a digital report dashboard for farm traceability"
                ]
            }
        ]
    },
    {
        "strategy": "Scalable Franchise Ecosystem",
        "objectives": [
            {
                "title": "Build and refine the franchise playbook",
                "owner": "Hubert Lau",
                "key_results": [
                    "Publish full franchise operations manual by June",
                    "Identify and onboard 3 early franchisees by Q3",
                    "Deliver full onboarding and training within 30 days of sign-up"
                ]
            },
            {
                "title": "Support franchise success through centralized services",
                "owner": "Hubert Lau",
                "key_results": [
                    "Launch a centralized support portal by August",
                    "Implement an NPS survey and achieve >70 by year-end",
                    "Provide weekly crop performance dashboard for all franchisees"
                ]
            }
        ]
    },
    {
        "strategy": "Vertical Integration & Recurring Revenue",
        "objectives": [
            {
                "title": "Streamline and scale the consumables supply chain",
                "owner": "Joshua Lau",
                "key_results": [
                    "Identify 3 preferred suppliers and secure volume discounts",
                    "Reduce delivery lead time for consumables to <5 days",
                    "Introduce auto-replenishment for 80% of franchisees"
                ]
            },
            {
                "title": "Develop and launch at least one high-margin specialty crop line",
                "owner": "Joshua Lau",
                "key_results": [
                    "Conduct R&D on 5 high-potential niche crops by Q3",
                    "Pilot 2 new crops in 3 farm locations",
                    "Achieve a 20% margin improvement compared to baseline produce"
                ]
            }
        ]
    },
    {
        "strategy": "Community Impact & Strategic Partnerships",
        "objectives": [
            {
                "title": "Position AFSI as a community food security partner",
                "owner": "Hubert Lau",
                "key_results": [
                    "Launch 1 municipally-backed indoor farm project",
                    "Partner with 2 non-profits or First Nations groups",
                    "Host 2 community awareness or education events"
                ]
            },
            {
                "title": "Secure strategic funding and policy alignment",
                "owner": "Ruan Wannenburg",
                "key_results": [
                    "Submit 3 grant applications by end of Q2",
                    "Meet with 5 key policymakers and stakeholders",
                    "Raise $X from strategic ESG-aligned investors"
                ]
            }
        ]
    }
]

# Loop through the data and populate the DB
for entry in okr_data:
    strategy, _ = Strategy.objects.get_or_create(name=entry['strategy'])
    for obj in entry['objectives']:
        objective = Objective.objects.create(
            name=obj['title'],
            description="",
            owner=obj['owner'],
            strategy=strategy,
            start_date=date.today(),
            end_date=date.today().replace(month=12, day=31),
            completed=False
        )
        for kr in obj['key_results']:
            KeyResult.objects.create(
                name=kr,
                description="",
                target_value=100,
                current_value=0,
                unit="%",
                objective=objective
            )

print("OKRs imported successfully.")
