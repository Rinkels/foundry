# -*- coding: utf-8 -*-
"""ITIL Foundation (Version 5) glossary — article generator.

Sibling of generate_cissp_glossary.py: same rendering machinery, new content.
Authored from the official PeopleCert syllabus v5.0 (February 2026) — see
C:\\Projects\\fractals\\itil\\syllabus-notes.md for the condensed spec.
Content rule: concepts in our own words only; never PeopleCert text/questions.

Renders an EvergreenArticle on mindsgate-redesign
  -> /insights/itil-foundation-glossary.html
and a shared JSON data source
  -> assets/data/itil-glossary.json  (future flashcards/tracker pages read it)

Design notes (constraints of the sites_builder article pipeline):
- Body starts with "<" so _render_article_html passes it through as HTML.
- NO <dl> anywhere (cardify_subsections would accordion-ize it).
- Each category is a direct-child <section> of one outer <section>.
- All CSS/JS inline and dependency-free; readable with JS disabled.

Run:
  python manage.py shell -c "exec(open(r'C:\\Projects\\foundry\\scripts\\generate_itil_glossary.py', encoding='utf-8').read())"
Then:
  python manage.py build_site mindsgate-redesign
"""
import re
from html import escape


def slug_id(acr):
    """Stable per-term anchor id — must match term_id() used for the JSON export."""
    return re.sub(r"[^a-z0-9]+", "-", acr.lower()).strip("-")

SLUG = "itil-foundation-glossary"
TITLE = "ITIL 5 Foundation Glossary: Key Terms & Definitions for the Version 5 Exam"
META_DESCRIPTION = ("Free ITIL 5 Foundation glossary: 60+ key terms and definitions across all "
                    "7 syllabus categories, with official exam weightings, comparison tables and "
                    "study tips — aligned to the PeopleCert Version 5.0 syllabus. No sign-up, "
                    "from the team behind the free CISSP study suite.")
PEOPLECERT_URL = ("https://www.peoplecert.org/browse-certifications/"
                  "it-governance-and-service-management/itil-1/itil-5-foundation-version-50-4154/")
DISCLAIMER = ("Independent ITIL study aid. ITIL\u00ae and PRINCE2\u00ae are registered trademarks "
              "of PeopleCert International Limited. This resource is not affiliated with or "
              "endorsed by PeopleCert.")

# key -> (full name, short chip label) — the 7 official syllabus categories.
CATS = [
    ("terms", "Key ITIL Terms & Definitions \u00b7 30%", "Key terms"),
    ("dims", "The Four Dimensions \u00b7 10%", "Four Dimensions"),
    ("lifecycle", "The Product & Service Lifecycle \u00b7 10%", "Lifecycle"),
    ("svs", "The ITIL Value System \u00b7 40%", "Value System"),
    ("streams", "Value Streams \u00b7 5%", "Value streams"),
    ("ai", "ITIL and AI \u00b7 2.5%", "AI"),
    ("frameworks", "ITIL and Other Frameworks \u00b7 2.5%", "Frameworks"),
]

# (cat, short term, full term, definition, priority "core"|"ext", study tip or None)
TERMS = [
    # ---- 1. Key ITIL terms & definitions (30%) -----------------------------
    ("terms", "Exam facts", "How the ITIL 5 Foundation Exam Works",
     "40 multiple-choice questions in 60 minutes, closed book. 26 correct answers (65%) pass, "
     "and there is no negative marking. The category weightings below come from the official "
     "PeopleCert syllabus v5.0 — categories 1 and 4 alone carry about 70% of the marks.", "core",
     "No negative marking means an unanswered question is the only guaranteed lost mark — never leave a blank."),
    ("terms", "Value", "Value",
     "The perceived benefits, usefulness and importance of something. Value is subjective — "
     "different stakeholders perceive it differently — and it is always co-created through the "
     "relationship between provider and consumer, never delivered one-way.", "core",
     "If an option says the provider \u201cdelivers value to\u201d the consumer, be suspicious — value is CO-created."),
    ("terms", "Value co-creation", "Value Co-creation",
     "The active collaboration between service providers, service consumers and other "
     "stakeholders through which value is generated. Consumers contribute requirements, "
     "feedback and participation; providers contribute products, services and expertise.", "core", None),
    ("terms", "Output", "Output",
     "A tangible or intangible deliverable produced by an activity — a report, an app build, "
     "a configured laptop. Outputs are what the work produces, not what it achieves.", "core",
     "Output = the deliverable. Outcome = the result the deliverable enables. The exam tests this pair relentlessly."),
    ("terms", "Outcome", "Outcome",
     "A result for a stakeholder that is enabled by one or more outputs. \u201cThe sales team can "
     "close deals from anywhere\u201d is an outcome; the mobile CRM app that made it possible is "
     "an output.", "core", None),
    ("terms", "Cost", "Cost",
     "The amount of money or resources spent on a specific activity or resource. In a service "
     "relationship, consumers weigh the costs the service removes (running it themselves) "
     "against the costs it imposes (fees, training, integration).", "core", None),
    ("terms", "Risk", "Risk",
     "A possible event that could cause harm or loss, or make it harder to achieve objectives. "
     "Like costs, risks run both ways: a service removes some risks from the consumer and "
     "imposes others.", "core",
     "Outcomes, costs AND risks all contribute to value — an option that weighs only benefits is incomplete."),
    ("terms", "Service", "Service",
     "A means of enabling value co-creation by facilitating the outcomes consumers want to "
     "achieve, without the consumer having to manage all of the associated costs and risks.", "core",
     "The classic missing-word question. Key markers: \u201cenabling value co-creation\u201d + \u201coutcomes\u201d + \u201cwithout managing all costs and risks\u201d."),
    ("terms", "Product", "Product",
     "A configuration of an organization's resources, designed to offer value to consumers. "
     "Products are built and evolved by the provider; services are how their value reaches "
     "consumers.", "core", None),
    ("terms", "Digital product", "Digital Product & Digital Service",
     "A product or service that is built on, delivered or enabled through digital technology — "
     "software, data and connectivity. Version 5 puts digital products and services at the "
     "centre of the whole framework.", "core", None),
    ("terms", "DPSM", "Digital Product and Service Management",
     "The discipline of creating, delivering, operating and continually improving digital "
     "products and services across their whole lifecycle — the subject of ITIL Version 5.", "core", None),
    ("terms", "Goods", "Goods",
     "Tangible items that are transferred to the consumer, who takes ownership and "
     "responsibility for their future use — a handset, a sensor, a laptop.", "core",
     "Goods = ownership moves. Access to resources = the provider keeps ownership and upkeep. Don't mix the two."),
    ("terms", "Continual improvement", "Continual Improvement",
     "A recurring organizational activity, performed at all levels, that keeps products, "
     "services, practices and the organization itself aligned with changing stakeholder needs "
     "and expectations.", "core",
     "\u201cContinual\u201d (recurring, embedded) — the structured step-by-step loop is the Continual Improvement Model in the Value System category."),
    ("terms", "Utility", "Utility",
     "The functionality offered by a product or service — what it does. Utility is \u201cfitness "
     "for purpose\u201d: does it support the consumer's intended use?", "core", None),
    ("terms", "Warranty", "Warranty",
     "Assurance that a product or service will perform as agreed — how well it works. Warranty "
     "is \u201cfitness for use\u201d: availability, capacity, security and continuity at agreed levels.", "core",
     "A service with great features that keeps falling over has utility but lacks warranty. Both are needed for value."),
    ("terms", "User experience", "User Experience (UX)",
     "How users perceive and feel about their interactions with a product or service. Version 5 "
     "raises experience to a first-class value consideration alongside utility and warranty.", "core", None),
    ("terms", "Sustainability", "Sustainability",
     "The environmental, social and economic responsibility of a product or service across its "
     "lifecycle. In Version 5 it joins utility, warranty and user experience as a dimension of "
     "value that consumers weigh.", "core",
     "The v5 value quartet: utility, warranty, user experience, sustainability. Older material stops at the first two."),
    ("terms", "Service offering", "Service Offering",
     "A description of one or more services, formulated for a target consumer group. An "
     "offering can combine service actions, transfer of goods, and access to resources.", "core", None),
    ("terms", "Organization", "Organization",
     "A person or group of people with its own functions, responsibilities, authorities and "
     "relationships, working to achieve its objectives. Both providers and consumers are "
     "organizations — the terms name roles, not company types.", "ext",
     "Provider and consumer are ROLES in a relationship: the same organization plays both in different relationships."),
    ("terms", "Service provider", "Service Provider",
     "The role an organization plays when it provides services to consumers. Internal IT "
     "departments and external suppliers are both service providers.", "core", None),
    ("terms", "Service consumer", "Service Consumer",
     "The role an organization plays when it receives services. Within a consumer organization, "
     "the sponsor, customer and user roles can be held by different people — or one.", "core", None),
    ("terms", "Product vendor", "Digital Product Vendor",
     "The role of an organization that produces and sells digital products — a software house "
     "or SaaS maker. Version 5 names this as a third key role alongside service provider and "
     "service consumer.", "core",
     "New in Version 5 — three roles in modern relationships: provider, consumer, and digital product vendor."),
    ("terms", "Consumer roles", "Sponsor, Customer & User",
     "The three roles inside a service consumer organization: the sponsor authorizes the "
     "budget, the customer defines requirements and takes responsibility for the outcomes, and "
     "the user actually uses the service.", "core",
     "Budget \u2192 sponsor. Requirements & outcomes \u2192 customer. Day-to-day use \u2192 user. One person can hold all three roles."),
    ("terms", "Service relationship", "Service Relationship (Basic / Cooperative / Collaborative)",
     "The cooperation between a provider and a consumer, covering service provision, service "
     "consumption and relationship management. Version 5 distinguishes three types by depth: "
     "basic, cooperative, and collaborative (partnership).", "core",
     "The ladder is depth of trust and joint working: basic = transactional, cooperative = joint work in defined areas, collaborative = shared goals, risks and innovation."),
    ("terms", "Service journey", "Service Journey",
     "The end-to-end experience a service consumer has with a provider, across every "
     "interaction and touchpoint — from first contact through onboarding, use, support and "
     "renewal.", "core", None),
    ("terms", "Service quality", "Service Quality & Service Level",
     "Service quality is how well a service meets stakeholder expectations and needs. A "
     "service level expresses quality as one or more measurable targets — availability "
     "percentages, response times, satisfaction scores.", "core", None),
    ("terms", "SLA", "Service Level Agreement",
     "A documented agreement between a service provider and a customer that identifies the "
     "services covered and the service levels both sides have committed to.", "core",
     "Beware the \u201cwatermelon SLA\u201d — metrics green on the outside, users unhappy inside. It is why v5 elevates experience alongside levels."),

    # ---- 2. The Four Dimensions (10%) ---------------------------------------
    ("dims", "Four dimensions", "The Four Dimensions of Product and Service Management",
     "The four perspectives that must ALL be considered for effective product and service "
     "management: organizations and people; information and technology; partners and "
     "suppliers; and value streams and processes. Neglect any one and value delivery suffers.", "core",
     "A question listing a fifth \u201cdimension\u201d (governance, finance, security\u2026) is testing whether you know the real four."),
    ("dims", "PESTLE", "PESTLE — External Factors",
     "The external forces that influence all four dimensions from outside the organization: "
     "Political, Economic, Social, Technological, Legal and Environmental factors.", "core",
     "The four dimensions are internal perspectives; PESTLE is the weather they all sit in."),

    # ---- 3. The Product & Service Lifecycle (10%) ---------------------------
    ("lifecycle", "Lifecycle", "The ITIL Product and Service Lifecycle",
     "Version 5's model of the eight activities through which digital products and services "
     "are managed from idea to retirement: discover, design, acquire, build, transition, "
     "operate, deliver and support. The activities are used iteratively — they are not a "
     "sequential waterfall.", "core",
     "Two near-certain marks: the purpose of a named activity, and knowing the activities are iterative, not linear."),
    ("lifecycle", "Discover", "Discover (Lifecycle Activity)",
     "The lifecycle activity focused on understanding markets, consumers, needs and "
     "opportunities, and deciding which products and services are worth pursuing — before "
     "anything is designed or built.", "core", None),
    ("lifecycle", "Transition", "Transition (Lifecycle Activity)",
     "The lifecycle activity that moves new or changed products, services and components into "
     "the live environment safely and effectively, so that improvements arrive without "
     "breaking what already runs.", "core",
     "Build creates it; transition takes it live; operate keeps it running. Keep the hand-offs straight."),

    # ---- 4. The ITIL Value System (40%) --------------------------------------
    ("svs", "ITIL VS", "The ITIL Value System (ITIL VS)",
     "Version 5's model of how all the framework's components work together, as one system, to "
     "enable value creation. Its components: the guiding principles, governance, the value "
     "chain, the management practices, and continual improvement.", "core",
     "The heaviest-weighted exam category lives here. Memorize the five components cold — and note the four dimensions are NOT one of them."),
    ("svs", "Guiding principles", "The Seven ITIL Guiding Principles",
     "Universal recommendations that guide an organization in all circumstances, whatever its "
     "goals, strategy or structure. They interact and are normally applied together, not one "
     "at a time.", "core",
     "Scenario questions describe a behaviour and ask which principle it shows — learn each principle's one-line signature from the table."),
    ("svs", "Governance", "Governance",
     "The means by which an organization is directed and controlled. Governance is enabling "
     "rather than commanding: it evaluates options, sets direction, and monitors whether the "
     "organization is achieving what was intended.", "core",
     "Evaluate \u2192 direct \u2192 monitor. Governance steers; management rows."),
    ("svs", "Value chain", "Value Chain",
     "The set of interconnected activities within an organization's operating model that turn "
     "demand into value. In Version 5, the value chain activities are what ENABLE the product "
     "and service lifecycle activities — two linked models, not one.", "core",
     "Lifecycle = the product's journey. Value chain = the organization's activities powering that journey. Don't conflate them."),
    ("svs", "Operating model", "Operating Model",
     "How an organization arranges its capabilities — people, processes, partners and "
     "technology — to deliver on its purpose and create value. The value chain activities and "
     "management practices together support the operating model.", "core", None),
    ("svs", "Management practice", "Management Practice",
     "A set of organizational resources designed for performing work or accomplishing an "
     "objective — people, information, technology, processes and skills together, not just a "
     "process. Version 5 organizes the practices into two groups.", "core",
     "Version 5 has TWO practice groups: general, and product & service management. The old three-group split is an exam trap from ITIL 4 material."),
    ("svs", "Practice guides", "ITIL Practice Guides",
     "The official, individually maintained guides — one per management practice — kept "
     "separate from the core book so each can evolve on its own. They give organizations "
     "consistent, proven ways of working without reinventing each practice from scratch.", "core", None),
    ("svs", "Metric", "Metric",
     "A measurement or calculation that is monitored or reported for management and "
     "improvement — the raw numbers behind service levels, KPIs and improvement decisions.", "ext", None),
    ("svs", "CSF", "Critical Success Factor",
     "A necessary precondition for achieving intended results. CSFs state what must be true; "
     "metrics and KPIs then measure whether you are getting there.", "core",
     "CSF = the condition (\u201caccurate configuration data exists\u201d). Metric/KPI = the measurement of progress toward it."),
    ("svs", "Incident", "Incident",
     "An unplanned interruption to a service, or a reduction in the quality of a service. "
     "Incidents are about restoring normal service fast — root cause is the problem record's "
     "job.", "core",
     "Broken = incident. Wanted = service request. Cause = problem. Three different records."),
    ("svs", "Event", "Event",
     "Any change of state that has significance for the management of a product, service or "
     "other managed component. Many events are informational; some indicate warnings or "
     "failures and lead to incidents.", "ext", None),
    ("svs", "Service request", "Service Request",
     "A user-initiated request for something that is a normal, pre-agreed part of service "
     "delivery — information, access, advice, or a standard provisioning item. Nothing is "
     "broken; nothing is being investigated.", "core", None),
    ("svs", "Problem", "Problem, Error & Known Error",
     "A problem is the cause, or potential cause, of one or more incidents. An error is an "
     "identified flaw or defect that causes or could cause incidents. A known error is an "
     "error that has been analyzed and documented — usually with a workaround — but not yet "
     "permanently fixed.", "core",
     "The exam asks the distinction directly: problem = under investigation; error = identified flaw; known error = diagnosed and documented."),
    ("svs", "Disaster", "Disaster",
     "A sudden, unplanned event causing damage or serious disruption on a scale beyond normal "
     "incident handling, triggering the organization's recovery arrangements.", "ext", None),
    ("svs", "Release & test", "Release & Test",
     "A release is a version of a service, product or component (or a set of them) made "
     "available for use. Testing is the assurance activity confirming that what is released "
     "meets its requirements and will not degrade the live environment.", "ext", None),
    ("svs", "CI/CD", "Continuous Integration, Delivery & Deployment",
     "Three related automation practices: continuous integration merges and verifies code "
     "changes frequently; continuous delivery keeps the product releasable at any moment with "
     "a human deciding when to deploy; continuous deployment automatically deploys every "
     "change that passes the pipeline.", "core",
     "Delivery = CAN deploy at any time (human gate). Deployment = every passing change DOES deploy (no gate). That one word is the whole question."),
    ("svs", "Reliability", "Reliability",
     "The ability of a product, service or component to perform as required, without failure, "
     "for a given period under stated conditions.", "ext", None),
    ("svs", "SRE", "Site Reliability Engineering",
     "Applying software-engineering approaches to operations work — automating toil, managing "
     "reliability with explicit targets and error budgets — so systems stay reliable at scale. "
     "Named core content in the Version 5 syllabus.", "core", None),
    ("svs", "Observability", "Observability",
     "The ability to understand a system's internal state from its external outputs — logs, "
     "metrics and traces. Observability lets engineers diagnose novel failures without "
     "shipping new instrumentation first.", "core",
     "Monitoring answers questions you prepared in advance; observability lets you ask new ones after the surprise."),
    ("svs", "Product spec", "Product Specification & Prototype",
     "A product specification documents what a product must be and do — its requirements and "
     "characteristics. A prototype is an early working version built to test ideas and "
     "assumptions before committing to the full build.", "ext", None),
    ("svs", "CI Model", "The Continual Improvement Model",
     "The step-by-step loop that structures any improvement, from strategy to daily work. Its "
     "seven questions run from vision to momentum — see the table — and the loop repeats "
     "rather than ends.", "core",
     "Learn the seven steps in order; \u201cwhich step comes next/first\u201d is a classic recall mark."),

    # ---- 5. Value streams (5%) ----------------------------------------------
    ("streams", "Value stream", "Value Stream (Core & Enabling)",
     "The series of steps an organization takes to create and deliver products and services "
     "to consumers. Core value streams directly create value for external consumers; enabling "
     "value streams are the internal streams that make the core ones possible.", "core",
     "Customer-facing flow = core stream. The platform/onboarding/tooling work behind it = enabling stream."),
    ("streams", "VSM", "Value Stream Mapping & Management",
     "Mapping visualizes a stream end to end — steps, workflows, hand-offs, queues and wait "
     "times — to expose where work stalls and value leaks. Management is the ongoing "
     "discipline of governing and optimizing the streams the maps reveal.", "core",
     "Mapping is the snapshot; management is the ongoing practice built on it."),
    ("streams", "Complexity thinking", "Complexity Thinking",
     "Recognizing that organizations are complex systems whose behaviour cannot be fully "
     "predicted, and matching the way of working to the situation — standardize what is "
     "stable, experiment and iterate where outcomes are uncertain.", "ext", None),

    # ---- 6. ITIL and AI (2.5%) ------------------------------------------------
    ("ai", "AI & GenAI", "AI, AI Maturity & Generative AI",
     "Artificial intelligence: systems performing tasks that normally require human "
     "intelligence. AI maturity: how far an organization has progressed in adopting and "
     "governing AI. Generative AI: models that create new content — text, images, code — "
     "from what they have learned.", "ext", None),
    ("ai", "Agentic AI", "Agentic AI",
     "AI that can autonomously plan and execute multi-step actions toward a goal with limited "
     "human supervision — not just answering, but doing. New, explicitly named content in the "
     "Version 5 syllabus.", "core",
     "GenAI creates content; agentic AI takes actions. One word \u2014 \u201cautonomously\u201d \u2014 usually decides the question."),
    ("ai", "AI governance", "AI Governance & the ITIL AI Capability Model",
     "Directing and controlling the responsible use of AI — policies, accountability, "
     "transparency and risk management. Version 5 also introduces the ITIL AI Capability "
     "Model, its structured view of how organizations develop AI capability.", "core",
     "AI Governance is also the only extension module in the Version 5 certification scheme."),

    # ---- 7. ITIL and other frameworks (2.5%) ---------------------------------
    ("frameworks", "DevOps", "ITIL and DevOps",
     "DevOps is a culture and set of practices uniting development and operations for fast, "
     "reliable flow of change. ITIL and DevOps are complementary: ITIL contributes the "
     "service-management structure and value focus, DevOps contributes speed, automation and "
     "flow.", "ext",
     "Any option claiming one \u201creplaces\u201d the other is wrong — the syllabus word is complementary."),
    ("frameworks", "PRINCE2", "ITIL and PRINCE2",
     "PRINCE2 is a structured project management method. Projects introduce change; products "
     "and services live on after the project ends — so PRINCE2 manages the change initiative "
     "while ITIL manages the product or service across its whole lifecycle. Complementary, "
     "not competing.", "ext",
     "Project = temporary, with an end date. Product/service = ongoing lifecycle. That contrast is the whole exam angle."),
]

# "Remember This" cards, placed inside their most relevant category section.
REMEMBER = {
    "terms": ("Value vocabulary", ["Output = what the work produces",
                                   "Outcome = the result the output enables for a stakeholder",
                                   "Utility = fit for purpose (what it does)",
                                   "Warranty = fit for use (how reliably it does it)",
                                   "Value = perceived benefits \u2014 always co-created"]),
    "dims": ("The four dimensions", ["Organizations & people",
                                     "Information & technology",
                                     "Partners & suppliers",
                                     "Value streams & processes",
                                     "PESTLE presses on all four from outside"]),
    "svs": ("ITIL Value System components", ["Guiding principles",
                                             "Governance",
                                             "Value chain",
                                             "Management practices",
                                             "Continual improvement"]),
    "streams": ("Two kinds of stream", ["Core stream = value for external consumers",
                                        "Enabling stream = keeps the core streams possible"]),
}

LIFECYCLE_FLOW = ["Discover", "Design", "Acquire", "Build",
                  "Transition", "Operate", "Deliver", "Support"]

CSS = """
<style>
.gl-jump{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 4px;padding:0}
.gl-chip{display:inline-block;font-size:.85rem;font-weight:600;padding:7px 14px;border-radius:999px;
  border:1px solid var(--site-border,rgba(148,163,199,.25));color:var(--site-text,#dfe4ee);
  background:var(--site-surface,rgba(255,255,255,.03));text-decoration:none;cursor:pointer;font-family:inherit}
.gl-chip:hover{border-color:var(--site-accent,#5dd6c6)}
.gl-chip.is-on{border-color:var(--site-accent,#5dd6c6);color:var(--site-accent,#5dd6c6)}
.gl-controls{margin-top:16px}
.gl-search{width:100%;max-width:520px;padding:12px 14px;border-radius:10px;font:inherit;
  border:1px solid var(--site-border,rgba(148,163,199,.25));
  background:var(--site-surface,rgba(255,255,255,.03));color:var(--site-text,#dfe4ee)}
.gl-search:focus{outline:none;border-color:var(--site-accent,#5dd6c6)}
.gl-chiprow{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}
.gl-count{color:var(--site-muted,#8b93a7);font-size:.9rem;margin:6px 0 0}
.gl-entry{padding:14px 0;border-bottom:1px solid var(--site-border,rgba(148,163,199,.14))}
.gl-entry:last-child{border-bottom:0}
.gl-entry__head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.gl-entry__acr{font-weight:700;color:var(--site-heading,#f4f6f9);min-width:5.5rem}
.gl-entry__term{color:var(--site-accent,#5dd6c6);font-size:.95rem}
.gl-entry__pri{font-size:.68rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
  padding:2px 9px;border-radius:999px;margin-left:auto;white-space:nowrap}
.gl-entry__pri--core{color:var(--site-gold,#d9b36b);border:1px solid var(--site-gold,#d9b36b)}
.gl-entry__pri--ext{color:var(--site-muted,#8b93a7);border:1px solid var(--site-border,rgba(148,163,199,.25))}
.gl-entry__def{margin:6px 0 0;color:var(--site-text,#dfe4ee)}
.gl-entry__tip{margin:6px 0 0;font-size:.9rem;color:var(--site-muted,#8b93a7)}
.gl-entry__tip strong{color:var(--site-gold,#d9b36b)}
.gl-remember{border:1px solid var(--site-gold,#d9b36b);border-left-width:4px;border-radius:12px;
  padding:16px 20px;margin:22px 0 6px;background:var(--site-surface,rgba(255,255,255,.03))}
.gl-remember h3{margin:0 0 8px;font-size:1rem;color:var(--site-gold,#d9b36b)}
.gl-remember ul{margin:0;padding-left:1.1rem}
.gl-remember li{margin:3px 0;color:var(--site-text,#dfe4ee)}
.gl-ir{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:18px 0 6px}
.gl-ir__step{border:1px solid var(--site-accent,#5dd6c6);color:var(--site-accent,#5dd6c6);
  border-radius:10px;padding:8px 14px;font-weight:600;font-size:.9rem}
.gl-ir__arrow{color:var(--site-muted,#8b93a7)}
.gl-disclaimer{font-size:.85rem;color:var(--site-muted,#8b93a7);border-top:1px solid var(--site-border,rgba(148,163,199,.14));
  padding-top:14px;margin-top:20px}
.gl-cat__count{font-size:.85rem;color:var(--site-muted,#8b93a7);font-weight:400}
.gl-flash{margin:14px 0 0;display:flex;gap:22px;flex-wrap:wrap}
.gl-flash a{color:var(--site-gold,#d9b36b);font-weight:600;text-decoration:none;border-bottom:1px solid var(--site-gold,#d9b36b)}
.gl-flash a:hover{opacity:.85}
.gl-entry.gl-hit{animation:glHit 2.4s ease}
@keyframes glHit{0%,60%{background:rgba(217,179,107,.14);box-shadow:inset 3px 0 0 var(--site-gold,#d9b36b)}100%{background:transparent}}
@media (prefers-reduced-motion:reduce){.gl-entry.gl-hit{animation:none;box-shadow:inset 3px 0 0 var(--site-gold,#d9b36b)}}
.gl-more{margin:8px 0 0;font-size:.9rem}
.gl-more summary{cursor:pointer;color:var(--site-gold,#d9b36b);font-weight:600;font-size:.84rem}
.gl-more summary:hover{opacity:.85}
.gl-more ul{margin:8px 0 0;padding-left:20px;color:var(--site-muted,#a8b3c9)}
.gl-more li{margin:3px 0}
.gl-table__cap{margin:10px 0 6px;font-size:.82rem;color:var(--site-muted,#a8b3c9);font-style:italic}
.gl-tablewrap{overflow-x:auto;margin-top:8px}
.gl-table{width:100%;border-collapse:collapse;font-size:.84rem;min-width:560px}
.gl-table th{text-align:left;padding:7px 10px;color:var(--site-gold,#d9b36b);font-size:.74rem;letter-spacing:.06em;text-transform:uppercase;border-bottom:1px solid var(--site-border-strong,rgba(255,255,255,.18));white-space:nowrap}
.gl-table td{padding:7px 10px;border-bottom:1px solid var(--site-border,rgba(255,255,255,.08));color:var(--site-muted,#a8b3c9);vertical-align:top;line-height:1.45}
.gl-table td:first-child{color:var(--site-heading,#fff);font-weight:600;white-space:nowrap}
.gl-table tr:last-child td{border-bottom:0}
.gl-studying .gl-entry{cursor:pointer}
.gl-studying .gl-entry__body{display:none}
.gl-studying .gl-entry.gl-open .gl-entry__body{display:block}
@media (max-width:640px){
  .gl-entry__pri{margin-left:0}
  .gl-entry__acr{min-width:0}
}
</style>
"""

JS = """
<script>
(function () {
  var controls = document.getElementById("gl-controls");
  if (!controls) return;
  controls.hidden = false;

  var entries = Array.prototype.slice.call(document.querySelectorAll(".gl-entry"));
  var cats = Array.prototype.slice.call(document.querySelectorAll(".gl-cat"));
  var search = document.getElementById("gl-search");
  var chips = Array.prototype.slice.call(document.querySelectorAll(".gl-chiprow .gl-chip[data-cat]"));
  var coreBtn = document.getElementById("gl-core");
  var studyBtn = document.getElementById("gl-study");
  var count = document.getElementById("gl-count");
  var state = { q: "", cat: "all", core: false, study: false };

  function catBox(sec) { return sec.closest(".section-card") || sec; }

  function apply() {
    var shown = 0;
    entries.forEach(function (e) {
      var ok = (state.cat === "all" || e.dataset.cat === state.cat) &&
               (!state.core || e.dataset.pri === "core") &&
               (!state.q || e.dataset.hay.indexOf(state.q) !== -1);
      e.hidden = !ok;
      if (ok) shown++;
    });
    cats.forEach(function (sec) {
      var any = sec.querySelector(".gl-entry:not([hidden])");
      catBox(sec).hidden = !any;
    });
    count.textContent = "Showing " + shown + " of " + entries.length + " terms" +
      (state.core ? " (Core only)" : "") + (state.q ? " matching \\u201C" + state.q + "\\u201D" : "");
  }

  search.addEventListener("input", function () {
    state.q = search.value.trim().toLowerCase();
    apply();
  });

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      state.cat = chip.dataset.cat;
      chips.forEach(function (c) {
        var on = c === chip;
        c.classList.toggle("is-on", on);
        c.setAttribute("aria-pressed", on ? "true" : "false");
      });
      apply();
    });
  });

  coreBtn.addEventListener("click", function () {
    state.core = !state.core;
    coreBtn.classList.toggle("is-on", state.core);
    coreBtn.setAttribute("aria-pressed", state.core ? "true" : "false");
    apply();
  });

  function setStudy(on) {
    state.study = on;
    var root = document.querySelector("main") || document.body;
    root.classList.toggle("gl-studying", on);
    studyBtn.classList.toggle("is-on", on);
    studyBtn.setAttribute("aria-pressed", on ? "true" : "false");
    entries.forEach(function (e) {
      if (on) {
        e.setAttribute("tabindex", "0");
        e.setAttribute("role", "button");
        e.setAttribute("aria-expanded", e.classList.contains("gl-open") ? "true" : "false");
      } else {
        e.removeAttribute("tabindex");
        e.removeAttribute("role");
        e.removeAttribute("aria-expanded");
        e.classList.remove("gl-open");
      }
    });
  }

  studyBtn.addEventListener("click", function () { setStudy(!state.study); });

  function toggleEntry(e) {
    if (!state.study) return;
    e.classList.toggle("gl-open");
    e.setAttribute("aria-expanded", e.classList.contains("gl-open") ? "true" : "false");
  }
  entries.forEach(function (e) {
    e.addEventListener("click", function () { toggleEntry(e); });
    e.addEventListener("keydown", function (ev) {
      if (state.study && (ev.key === "Enter" || ev.key === " ")) {
        ev.preventDefault();
        toggleEntry(e);
      }
    });
  });

  apply();

  // Deep links (…#t-<id>): clear filters so the target is visible, scroll, flash.
  function jumpToHash() {
    var h = location.hash;
    if (!h || h.indexOf("#t-") !== 0) return;
    var el = document.getElementById(h.slice(1));
    if (!el) return;
    state.q = ""; state.cat = "all"; state.core = false;
    search.value = "";
    chips.forEach(function (c) {
      var on = c.dataset.cat === "all";
      c.classList.toggle("is-on", on);
      c.setAttribute("aria-pressed", on ? "true" : "false");
    });
    coreBtn.classList.remove("is-on");
    coreBtn.setAttribute("aria-pressed", "false");
    apply();
    if (state.study) el.classList.add("gl-open");
    el.scrollIntoView({ block: "center" });
    el.classList.remove("gl-hit");
    void el.offsetWidth;
    el.classList.add("gl-hit");
  }
  window.addEventListener("hashchange", jumpToHash);
  jumpToHash();
})();
</script>
"""


# Per-term reference tables, rendered inside the "In depth" <details> block and
# exported to the shared JSON as `table`. {acr: {"caption","headers","rows"}}
TABLES = {
    "Exam facts": {
        "caption": ("Official syllabus v5.0 category weightings — categories 1 and 4 together "
                    "are worth about 28 of the 40 marks."),
        "headers": ["Category", "Weight", "\u2248Marks of 40"],
        "rows": [
            ["1. Key ITIL terms & definitions", "30%", "12"],
            ["2. The Four Dimensions", "10%", "4"],
            ["3. Product & Service Lifecycle", "10%", "4"],
            ["4. The ITIL Value System", "40%", "16"],
            ["5. Value streams", "5%", "2"],
            ["6. ITIL and AI", "2.5%", "1"],
            ["7. ITIL and other frameworks", "2.5%", "1"],
        ],
    },
    "Consumer roles": {
        "caption": "The three roles inside a service consumer — one person can hold all three.",
        "headers": ["Role", "Responsibility"],
        "rows": [
            ["Sponsor", "Authorizes the budget for service consumption"],
            ["Customer", "Defines the requirements and takes responsibility for the outcomes"],
            ["User", "Uses the services day to day"],
        ],
    },
    "Service relationship": {
        "caption": "The three relationship types — the ladder is depth of trust and joint working.",
        "headers": ["Type", "Character"],
        "rows": [
            ["Basic", "Standardized and transactional — predefined offerings, little tailoring or joint work"],
            ["Cooperative", "Joint working toward shared goals in defined areas; more dialogue and tailoring"],
            ["Collaborative (partnership)", "Strategic: shared goals and risks, co-innovation, deep mutual trust"],
        ],
    },
    "Four dimensions": {
        "caption": "All four must be considered together — plus the PESTLE factors pressing from outside.",
        "headers": ["Dimension", "What it covers"],
        "rows": [
            ["Organizations & people", "Structure, roles, authority, culture, skills and capacity"],
            ["Information & technology", "The information, knowledge and technologies that products, services and relationships need"],
            ["Partners & suppliers", "The organization's relationships with the other organizations involved across the lifecycle"],
            ["Value streams & processes", "How work flows through the organization to create value"],
        ],
    },
    "Lifecycle": {
        "caption": ("The eight lifecycle activities and their purpose — used iteratively, not in "
                    "strict sequence."),
        "headers": ["Activity", "Purpose"],
        "rows": [
            ["Discover", "Understand markets, consumers and opportunities; decide what is worth pursuing"],
            ["Design", "Shape the product or service \u2014 requirements, architecture, experience \u2014 to deliver the intended value"],
            ["Acquire", "Source the needed components, resources and capabilities from suppliers and partners"],
            ["Build", "Create, assemble and configure the product or service, making it ready for use"],
            ["Transition", "Move new or changed components into the live environment safely and effectively"],
            ["Operate", "Run and maintain the product or service and its technology so it performs as intended"],
            ["Deliver", "Provide the service to consumers and fulfil demand as it arises"],
            ["Support", "Help users, handle incidents and requests, and restore normal service"],
        ],
    },
    "ITIL VS": {
        "caption": "The five components of the ITIL Value System and the role each plays.",
        "headers": ["Component", "Role"],
        "rows": [
            ["Guiding principles", "Universal recommendations shaping every decision"],
            ["Governance", "Directs and controls: evaluate, set direction, monitor"],
            ["Value chain", "The operating model's interconnected activities that turn demand into value"],
            ["Management practices", "Organizational resources and proven ways of working"],
            ["Continual improvement", "Keeps the whole system aligned with changing needs"],
        ],
    },
    "Guiding principles": {
        "caption": "The seven guiding principles — learn each one's one-line signature.",
        "headers": ["Principle", "Signature"],
        "rows": [
            ["Focus on value", "Everything should map to value for stakeholders"],
            ["Start where you are", "Assess and reuse what exists before replacing it"],
            ["Progress iteratively with feedback", "Small slices, learn, adjust \u2014 don't big-bang"],
            ["Collaborate and promote visibility", "Work together and make work and information visible"],
            ["Think and work holistically", "End to end, across silos \u2014 no component stands alone"],
            ["Keep it simple and practical", "The fewest steps that still achieve the outcome"],
            ["Optimize and automate", "Improve the thing FIRST, then automate the optimized version"],
        ],
    },
    "Problem": {
        "caption": "Four records the exam loves to swap — know which is which.",
        "headers": ["Term", "Meaning", "Status"],
        "rows": [
            ["Incident", "An unplanned service interruption or quality drop", "What the user feels"],
            ["Problem", "The cause, or potential cause, of one or more incidents", "Under investigation"],
            ["Error", "An identified flaw or defect that causes or could cause incidents", "Identified"],
            ["Known error", "An error that has been analyzed and documented, usually with a workaround", "Diagnosed, awaiting permanent fix"],
        ],
    },
    "CI/CD": {
        "caption": "The three continuous practices — the human gate is the discriminator.",
        "headers": ["Practice", "Meaning", "Human gate?"],
        "rows": [
            ["Continuous integration", "Merge and automatically verify code changes frequently", "\u2014"],
            ["Continuous delivery", "Product is always releasable; deployment happens on demand", "Yes \u2014 a person decides when"],
            ["Continuous deployment", "Every change that passes the pipeline deploys automatically", "No \u2014 the pipeline decides"],
        ],
    },
    "CI Model": {
        "caption": "The Continual Improvement Model — a loop, not a one-way street.",
        "headers": ["Step", "Focus"],
        "rows": [
            ["1. What is the vision?", "Business context, direction and high-level goals"],
            ["2. Where are we now?", "Honest baseline assessment of the current state"],
            ["3. Where do we want to be?", "Measurable targets and the gap to close"],
            ["4. How do we get there?", "The improvement plan \u2014 usually iterative"],
            ["5. Take action", "Execute the plan"],
            ["6. Did we get there?", "Evaluate against the targets from step 3"],
            ["7. How do we keep the momentum going?", "Embed the gains, share, continue the loop"],
        ],
    },
}

# Optional "In depth" expansions, rendered as a native <details> block and
# exported to the shared JSON as `detail`. {acr: [line, ...]}
DETAILS = {
    "Exam facts": [
        "40 Objective Test Questions, 1 mark each \u2014 no negative marking, so never leave a blank",
        "60 minutes, closed book (75 minutes when sitting in a language that is not your native or working language)",
        "Pass mark: 26 of 40 (65%)",
        "Question styles: Standard MCQ \u00b7 Missing word(s) \u00b7 List (choose the 2 correct statements of 4 \u2014 never negatively worded) \u00b7 Negative standard (rare, used only where knowing what NOT to do is the point)",
        "Bloom mix: about 40% recall (Define/List/Know) and 60% understanding (Explain/Describe/Understand)",
        "Weight your revision like the exam does: categories 1 and 4 are ~70% of the marks",
    ],
    "Service offering": [
        "Service actions \u2014 things done for the consumer (user support, handling a claim)",
        "Transfer of goods \u2014 ownership moves to the consumer (a handset, a sensor)",
        "Access to resources \u2014 the consumer uses something the provider keeps owning and maintaining (a network, a SaaS platform)",
        "One offering can combine all three: a mobile contract bundles a phone (goods), network access (access) and support (actions)",
    ],
    "Management practice": [
        "Version 5 organizes the practices into TWO groups: general management practices, and product and service management practices",
        "ITIL 4's three-group split (general / service management / technical management) is gone \u2014 a likely trap for anyone revising from old material",
        "Each practice has its own official Practice Guide (see that entry)",
    ],
    "Practice guides": [
        "One official guide per management practice, maintained separately from the core book so each can evolve",
        "They give organizations consistent, proven ways of working without reinventing each practice",
        "Typical contents: the practice's purpose, key concepts and terms, value contribution, activities, roles and metrics",
    ],
    "Guiding principles": [
        "The principles interact \u2014 organizations normally apply several together, and the syllabus tests exactly that",
        "They apply in ALL circumstances: any goal, any strategy, any type of organization",
    ],
    "Lifecycle": [
        "The activities are NOT sequential \u2014 a live product loops through them iteratively as needs change",
        "The value chain activities ENABLE the lifecycle activities \u2014 two linked models; don't conflate them",
        "Expect \u201cwhat is the purpose of the <activity> activity?\u201d questions \u2014 the table rows are the revision set",
    ],
    "Value stream": [
        "Core value stream \u2014 directly creates and delivers value for external consumers",
        "Enabling value stream \u2014 internal streams that make the core streams possible (platform engineering, onboarding, tooling)",
        "An organization runs many streams at once; mapping shows where work waits",
    ],
    "VSM": [
        "Typical elements of a value stream map: the steps and activities, workflows and hand-offs, information flows, queues and wait times, and the metrics attached to them",
        "Mapping exposes delay and waste; management then optimizes the stream \u2014 and keeps optimizing it",
        "Complexity thinking applies here: optimize workflows differently where behaviour is unpredictable",
    ],
    "AI & GenAI": [
        "AI \u2014 systems performing tasks that normally require human intelligence",
        "AI maturity \u2014 how far the organization has progressed in adopting, integrating and governing AI",
        "Generative AI (GenAI) \u2014 models that create new content: text, images, code",
        "Agentic AI \u2014 plans and executes multi-step actions autonomously (see its own entry)",
    ],
    "AI governance": [
        "Covers policy, accountability, transparency and risk management for AI use",
        "The ITIL AI Capability Model is Version 5's structured view of building AI capability \u2014 study its detail from the Official Book",
        "AI Governance is the single extension module in the Version 5 certification scheme",
    ],
}


def entry_html(cat, acr, term, definition, pri, tip):
    hay = escape((acr + " " + term + " " + definition).lower(), quote=True)
    pri_label = "Core" if pri == "core" else "Extended"
    tip_html = ""
    if tip:
        tip_html = ('<p class="gl-entry__tip"><strong>Study tip:</strong> '
                    + escape(tip) + "</p>")
    return (
        '<div class="gl-entry" id="t-' + slug_id(acr) + '" data-cat="' + cat + '" data-pri="' + pri
        + '" data-hay="' + hay + '">'
        + '<div class="gl-entry__head">'
        + '<span class="gl-entry__acr">' + escape(acr) + "</span>"
        + '<span class="gl-entry__term">' + escape(term) + "</span>"
        + '<span class="gl-entry__pri gl-entry__pri--' + pri + '">' + pri_label + "</span>"
        + "</div>"
        + '<div class="gl-entry__body">'
        + '<p class="gl-entry__def">' + escape(definition) + "</p>"
        + tip_html
        + detail_block(acr)
        + "</div></div>"
    )


def detail_block(acr):
    det = DETAILS.get(acr)
    tab = TABLES.get(acr)
    if not det and not tab:
        return ""
    inner = ""
    if det:
        inner += "<ul>" + "".join("<li>" + escape(x) + "</li>" for x in det) + "</ul>"
    if tab:
        head = "".join("<th>" + escape(h) + "</th>" for h in tab["headers"])
        rows = "".join(
            "<tr>" + "".join("<td>" + escape(c) + "</td>" for c in row) + "</tr>"
            for row in tab["rows"]
        )
        cap = ('<p class="gl-table__cap">' + escape(tab["caption"]) + "</p>") if tab.get("caption") else ""
        inner += (cap + '<div class="gl-tablewrap"><table class="gl-table">'
                  "<thead><tr>" + head + "</tr></thead><tbody>" + rows + "</tbody></table></div>")
    return ('<details class="gl-more"><summary>In depth \u2014 what gets tested</summary>'
            + inner + "</details>")


def remember_html(title, lines):
    lis = "".join("<li>" + escape(x) + "</li>" for x in lines)
    return ('<div class="gl-remember"><h3>Remember this \u2014 ' + escape(title)
            + "</h3><ul>" + lis + "</ul></div>")


def build_body():
    by_cat = {k: [] for k, _, _ in CATS}
    for t in TERMS:
        by_cat[t[0]].append(t)

    total = len(TERMS)
    parts = ["<section>", CSS]

    # Intro
    parts.append(
        "<section>"
        "<p>ITIL Foundation (Version 5) is, before anything else, a vocabulary exam: 40 "
        "questions, 65% to pass, and roughly 40% of the marks are pure recall of definitions. "
        "This glossary covers " + str(total) + " key terms in plain English, organized into the "
        "seven categories of the official PeopleCert syllabus v5.0 \u2014 with each category's "
        "exam weighting on its chip, so you study in proportion to the marks.</p>"
        "<p>It's written for ITIL 5 Foundation candidates, and equally for anyone who wants a "
        "working service-management vocabulary. From the same team whose free CISSP study "
        "suite carried its authors through that exam in 2026. Educational reference only "
        "\u2014 see the note at the end of the page.</p>"
        "</section>"
    )

    # Controls + no-JS category jump nav
    jump = "".join(
        '<a class="gl-chip" href="#gl-' + key + '">' + escape(label) + "</a>"
        for key, label, _ in CATS
    )
    chiprow = '<button type="button" class="gl-chip is-on" data-cat="all" aria-pressed="true">All</button>' + "".join(
        '<button type="button" class="gl-chip" data-cat="' + key + '" aria-pressed="false">'
        + escape(chip) + "</button>"
        for key, _, chip in CATS
    )
    parts.append(
        "<section>"
        "<h2>Browse the glossary</h2>"
        '<nav class="gl-jump" aria-label="Jump to a category">' + jump + "</nav>"
        '<p class="gl-flash"><a href="../tools.html">More free study tools \u2014 including the CISSP suite this one grew from \u2192</a></p>'
        '<div class="gl-controls" id="gl-controls" hidden>'
        '<input class="gl-search" id="gl-search" type="search" '
        'placeholder="Search terms, definitions\u2026" aria-label="Search the glossary">'
        '<div class="gl-chiprow" role="group" aria-label="Filter by category">' + chiprow + "</div>"
        '<div class="gl-chiprow">'
        '<button type="button" class="gl-chip" id="gl-core" aria-pressed="false">\u2605 Core terms only</button>'
        '<button type="button" class="gl-chip" id="gl-study" aria-pressed="false">Study Mode \u2014 hide definitions</button>'
        "</div>"
        '<p class="gl-count" id="gl-count" role="status" aria-live="polite"></p>'
        "</div>"
        "</section>"
    )

    # Category sections
    for key, label, _ in CATS:
        rows = sorted(by_cat[key], key=lambda t: t[1].lower())
        inner = "".join(entry_html(c, a, t, d, p, tip) for c, a, t, d, p, tip in rows)
        extra = ""
        if key in REMEMBER:
            extra += remember_html(*REMEMBER[key])
        if key == "lifecycle":
            steps = ('<span class="gl-ir__arrow" aria-hidden="true">\u2192</span>'.join(
                '<span class="gl-ir__step">' + escape(s) + "</span>" for s in LIFECYCLE_FLOW))
            extra += ('<div class="gl-remember"><h3>Remember this \u2014 the eight lifecycle activities</h3>'
                      '<div class="gl-ir" aria-label="Product and service lifecycle activities">'
                      + steps + "</div>"
                      "<ul><li>Presented in this order \u2014 but used iteratively, never as a one-way waterfall</li></ul></div>")
        parts.append(
            '<section class="gl-cat" id="gl-' + key + '" data-cat="' + key + '">'
            + "<h2>" + escape(label)
            + ' <span class="gl-cat__count">(' + str(len(rows)) + " terms)</span></h2>"
            + inner + extra + "</section>"
        )

    # Further study + disclaimer
    parts.append(
        "<section>"
        "<h2>Further study</h2>"
        '<p>The authoritative statement of what the exam covers is the official PeopleCert '
        '<a href="' + PEOPLECERT_URL + '" target="_blank" rel="noopener">ITIL Foundation '
        "(Version 5)</a> syllabus and Official Book. Definitions in this glossary are "
        "independently written summaries \u2014 use the syllabus weightings to divide your "
        "study time across the categories.</p>"
        '<p class="gl-disclaimer">' + escape(DISCLAIMER) + "</p>"
        "</section>"
    )

    parts.append(JS)
    parts.append("</section>")
    return "".join(parts)


from apps.sites_builder.models import Site, EvergreenArticle

site = Site.objects.get(slug="mindsgate-redesign")
body = build_body()

article, created = EvergreenArticle.objects.get_or_create(
    site=site, slug=SLUG,
    defaults={"title": TITLE, "status": EvergreenArticle.STATUS_PUBLISHED},
)
article.title = TITLE
article.status = EvergreenArticle.STATUS_PUBLISHED
article.excerpt = ("A free, searchable glossary of " + str(len(TERMS)) + " ITIL 5 Foundation "
                   "terms across all 7 official syllabus categories, with exam weightings, "
                   "comparison tables and study tips.")
article.body_md = body
article.meta_title = TITLE
article.meta_description = META_DESCRIPTION
article.save()
print(("created" if created else "updated"), "article", SLUG,
      "| terms:", len(TERMS), "| body bytes:", len(body))

# ---------------------------------------------------------------------------
# Shared JSON data source (for the future ITIL flashcards/tracker pages).
# Written into the built site as assets/data/itil-glossary.json.
# ---------------------------------------------------------------------------
import json as _json
import re as _re
from datetime import datetime as _dt, timezone as _tz
from pathlib import Path as _Path
from django.conf import settings as _settings


def term_id(acr):
    return _re.sub(r"[^a-z0-9]+", "-", acr.lower()).strip("-")


# (term the scenario resolves to, original scenario question)
SCENARIOS = [
    ("Warranty", "Users praise everything the service can do, but it keeps failing during month-end peaks. Which value concept is missing?"),
    ("Outcome", "A provider measures not the reports it ships but the decisions its customers can now make because of them. What is it measuring?"),
    ("Service request", "A user asks for a new laptop from the standard catalogue — nothing is broken and nothing needs investigating. What should the provider log?"),
    ("Problem", "Users report repeated crashes, and the team opens a record to investigate the underlying cause. What kind of record is this?"),
    ("Agentic AI", "An AI system plans a sequence of remediation steps, executes them on its own, and checks the results as it goes. Which capability class?"),
    ("PESTLE", "A team lists the political, legal and environmental forces shaping its service strategy. Which analysis frame is it using?"),
    ("Service journey", "A provider maps every touchpoint a consumer passes through, from first contact to renewal. What is it mapping?"),
    ("Value stream", "An organization charts the series of steps that turns a sales enquiry into a delivered subscription. What is it charting?"),
    ("Observability", "Engineers diagnose a completely novel failure purely from logs, metrics and traces, without shipping new instrumentation. Which property enables this?"),
    ("SLA", "A document lists the services provided to a customer and the measurable levels both sides committed to. What is it?"),
]

_terms_by_acr = {t[1]: t for t in TERMS}
_ids = [term_id(t[1]) for t in TERMS]
assert len(set(_ids)) == len(_ids), "term id collision"
for _acr, _q in SCENARIOS:
    assert _acr in _terms_by_acr, "scenario references unknown term: " + _acr
for _k in list(DETAILS) + list(TABLES):
    assert _k in _terms_by_acr, "detail/table references unknown term: " + _k

_cat_labels = {k: label for k, label, _ in CATS}
_json_terms = [
    {"id": term_id(a), "acronym": a, "full_term": t, "definition": d,
     "category": c, "category_label": _cat_labels[c],
     "study_tip": tip or "", "priority": ("Core" if p == "core" else "Extended"),
     **({"detail": DETAILS[a]} if a in DETAILS else {}),
     **({"table": TABLES[a]} if a in TABLES else {})}
    for c, a, t, d, p, tip in TERMS
]
_json_scenarios = []
for i, (acr, q) in enumerate(SCENARIOS, 1):
    t = _terms_by_acr[acr]
    _json_scenarios.append({
        "id": "sc-%02d" % i, "type": "scenario", "category": t[0],
        "category_label": _cat_labels[t[0]],
        "question": q, "answer_acronym": acr, "answer_term": t[2],
        "term_id": term_id(acr),
    })

# ---------------------------------------------------------------------------
# ORIGINAL exam-style practice questions, mirroring the real exam's question
# styles (standard, missing-word, list-pick-2, rare negative). None reproduce
# PeopleCert content. options[0] is ALWAYS the correct answer as authored;
# the app shuffles presentation order.
# (category, question, [correct, d1, d2, d3], explanation)
# ---------------------------------------------------------------------------
QUIZ = [
    # --- Key terms -----------------------------------------------------------
    ("terms",
     "Identify the missing words: \u201cA [ ? ] is a means of enabling value co-creation by facilitating the outcomes consumers want to achieve, without the consumer managing all of the associated costs and risks.\u201d",
     ["Service", "Product", "Service offering", "Output"],
     "The three markers — value CO-creation, outcomes, and not managing all costs and risks — form the service definition. A product is a configuration of resources; a service offering is a formulated description of services; an output is a deliverable."),
    ("terms",
     "A provider launches a mobile banking app, and customers can now pay bills from anywhere. Which of these is the OUTCOME?",
     ["Customers can pay bills from anywhere", "The mobile banking app itself", "The app's release notes", "The app's source code"],
     "The outcome is the result enabled for the stakeholder. The app, its notes and its code are all outputs — things produced, not results achieved."),
    ("terms",
     "A streaming service offers a huge catalogue but buffers constantly during peak hours. Which statement is TRUE?",
     ["It provides utility but lacks warranty", "It provides warranty but lacks utility", "It lacks both utility and warranty", "It provides both utility and warranty"],
     "What it DOES (the catalogue) is utility — fit for purpose. How reliably it performs is warranty — fit for use — and constant buffering is a warranty failure. Value needs both."),
    ("terms",
     "Alongside utility and warranty, which TWO considerations does Version 5 add to how consumers judge value?",
     ["User experience and sustainability", "User experience and profitability", "Scalability and sustainability", "Security and usability"],
     "Version 5's value quartet is utility, warranty, user experience and sustainability. Profitability, scalability, security and usability are real concerns but not the named additions."),
    ("terms",
     "Which of the following is NOT a possible component of a service offering?",
     ["A guiding principle", "Transfer of goods", "Access to resources", "Service actions"],
     "A service offering can combine goods (ownership transfers), access to resources (provider keeps ownership) and service actions (things done for the consumer). Guiding principles belong to the ITIL Value System."),
    ("terms",
     "An employee uses a car-sharing scheme: vehicles stay owned, insured and maintained by the scheme operator. Which service offering component is this?",
     ["Access to resources", "Transfer of goods", "A service action", "A service level agreement"],
     "The consumer uses the car but never owns it — access to resources. If the company bought the employee a car, ownership would transfer: goods."),
    ("terms",
     "Within a service consumer organization, who authorizes the budget for service consumption?",
     ["The sponsor", "The customer", "The user", "The service provider"],
     "Sponsor = budget, customer = requirements and outcomes, user = day-to-day use. The provider sits on the other side of the relationship entirely."),
    ("terms",
     "A provider and consumer jointly set strategy, share risks and co-innovate on new services. Which type of service relationship is this?",
     ["Collaborative (partnership)", "Basic", "Cooperative", "Transactional"],
     "Shared strategy, shared risk and co-innovation mark the deepest rung: a collaborative partnership. Cooperative relationships do joint work only in defined areas; basic ones are standardized and transactional."),
    ("terms",
     "Identify the missing word: \u201cAn [ ? ] is a documented agreement between a service provider and a customer that identifies both the services required and the expected levels.\u201d",
     ["SLA", "OLA", "Outcome", "Offering"],
     "Documented agreement + provider and customer + services and levels = the SLA definition. An outcome is a result; an offering is a description of services for a consumer group."),
    ("terms",
     "Which role does Version 5 name ALONGSIDE service provider and service consumer in modern service relationships?",
     ["Digital product vendor", "Process owner", "Service integrator", "Account manager"],
     "Version 5 adds the digital product vendor — the organization that produces and sells digital products — as a third key role. The other titles are jobs, not relationship roles."),

    # --- Four dimensions -----------------------------------------------------
    ("dims",
     "Which of the following is NOT one of the four dimensions of product and service management?",
     ["Governance and compliance", "Organizations and people", "Partners and suppliers", "Value streams and processes"],
     "The four dimensions are organizations & people, information & technology, partners & suppliers, and value streams & processes. Governance is a component of the ITIL Value System, not a dimension."),
    ("dims",
     "New data-protection legislation forces a redesign of a provider's data flows. Under which PESTLE factor does this influence fall?",
     ["Legal", "Political", "Social", "Economic"],
     "Legislation that binds the organization is the Legal factor. Political covers government direction and stability; social covers attitudes and demographics; economic covers market and financial conditions."),

    # --- Lifecycle -----------------------------------------------------------
    ("lifecycle",
     "Which lifecycle activity moves a new or changed component into the live environment?",
     ["Transition", "Deliver", "Build", "Operate"],
     "Build makes it ready; transition takes it live; operate keeps it running; deliver provides the service to consumers and fulfils demand."),
    ("lifecycle",
     "Which statement about the ITIL Product and Service Lifecycle activities is CORRECT?",
     ["They are used iteratively and are not strictly sequential", "They must always be completed in the published order", "Each product passes through each activity exactly once", "They replace the need for a value chain"],
     "The lifecycle is explicitly non-linear: live products loop through the activities as needs change. And the value chain is not replaced — its activities are what enable the lifecycle."),
    ("lifecycle",
     "Which lifecycle activity is focused on understanding markets, consumer needs and opportunities BEFORE anything is designed?",
     ["Discover", "Design", "Acquire", "Operate"],
     "Discover decides what is worth pursuing. Design then shapes it, acquire sources the components, and operate belongs to the live half of the lifecycle."),

    # --- Value System --------------------------------------------------------
    ("svs",
     "Which of the following is NOT a component of the ITIL Value System?",
     ["The four dimensions", "The guiding principles", "Governance", "Continual improvement"],
     "The ITIL VS components are guiding principles, governance, value chain, management practices and continual improvement. The four dimensions are a separate model — the classic swap."),
    ("svs",
     "A team redesigns an onboarding flow using the fewest steps that still achieve the outcome. Which guiding principle is it applying?",
     ["Keep it simple and practical", "Optimize and automate", "Focus on value", "Start where you are"],
     "Minimum steps that still deliver the outcome is the signature of keep it simple and practical. Optimize and automate is about improving before automating; start where you are is about reusing what exists."),
    ("svs",
     "A team wants to automate its messy, duplicate-ridden approval workflow exactly as it stands. Which guiding principle warns against this?",
     ["Optimize and automate", "Progress iteratively with feedback", "Collaborate and promote visibility", "Think and work holistically"],
     "Optimize and automate means improve the process FIRST, then automate the optimized version — automating a mess just produces faster mess."),
    ("svs",
     "Before replacing its monitoring stack, a team assesses what the current tools already do well and keeps what works. Which guiding principle?",
     ["Start where you are", "Focus on value", "Keep it simple and practical", "Progress iteratively with feedback"],
     "Assessing and reusing the current state instead of starting from scratch is start where you are. Iterative progress is about delivery in small slices, which isn't the behaviour described."),
    ("svs",
     "A user asks for access to a shared mailbox. Nothing is broken. What should the provider record this as?",
     ["A service request", "An incident", "A problem", "An event"],
     "A pre-agreed, user-initiated ask with no failure involved is a service request. An incident needs an interruption or quality drop; a problem is a cause under investigation."),
    ("svs",
     "Identify the missing word: \u201cA [ ? ] is the cause, or potential cause, of one or more incidents.\u201d",
     ["Problem", "Known error", "Event", "Disaster"],
     "Cause of incidents = problem. Once the underlying error is analyzed and documented — usually with a workaround — it becomes a known error."),
    ("svs",
     "A recurring crash has been analyzed, its flaw documented, and a workaround published while the permanent fix waits in the backlog. What is this now?",
     ["A known error", "A problem", "An incident", "A service request"],
     "Analyzed + documented + workaround = known error. It began life as incidents (user impact) and a problem (cause under investigation)."),
    ("svs",
     "Every change that passes the automated pipeline is released to production with no human approval step. Which practice is this?",
     ["Continuous deployment", "Continuous delivery", "Continuous integration", "Release management"],
     "No human gate means continuous deployment. Continuous delivery keeps the product releasable but a person decides when; continuous integration is about merging and verifying code frequently."),
    ("svs",
     "Which question begins the Continual Improvement Model?",
     ["What is the vision?", "Where are we now?", "How do we get there?", "Did we get there?"],
     "The loop runs: vision \u2192 where are we now \u2192 where do we want to be \u2192 how do we get there \u2192 take action \u2192 did we get there \u2192 keep the momentum going."),
    ("svs",
     "Which are the TWO groups of management practices in ITIL Version 5?",
     ["General practices, and product and service management practices", "General, service management and technical management practices", "Core practices and enabling practices", "Strategic practices and operational practices"],
     "Version 5 has two groups: general, and product & service management. The three-group split (general/service/technical) is ITIL 4 — exactly the trap old study notes set."),
    ("svs",
     "Identify the missing words: \u201cA [ ? ] is a necessary precondition for the achievement of intended results.\u201d",
     ["Critical success factor", "Key performance indicator", "Metric", "Service level"],
     "A CSF states the condition that must hold; KPIs and metrics then measure progress toward it, and a service level expresses agreed quality targets."),
    ("svs",
     "Engineers want to understand a system's internal state from its logs, metrics and traces so they can diagnose failures they never anticipated. Which capability are they building?",
     ["Observability", "Reliability", "Continuous integration", "Site reliability engineering"],
     "Inferring internal state from external outputs is observability. SRE is the engineering discipline that uses it; reliability is the outcome being protected."),

    # --- Value streams -------------------------------------------------------
    ("streams",
     "The stream that delivers an organization's customer-facing mobile app is which type of value stream?",
     ["A core value stream", "An enabling value stream", "A support stream", "A primary process"],
     "It creates value directly for external consumers — core. The internal platform and onboarding streams that make it possible are enabling streams."),
    ("streams",
     "What is the purpose of value stream MAPPING, as distinct from value stream management?",
     ["To visualize a stream's steps, flow and wait times so delays and waste become visible", "To continuously govern and optimize all of an organization's streams", "To automate a stream end to end", "To assign owners to every process"],
     "Mapping is the visualization snapshot that exposes queues and waste; management is the ongoing governing and optimizing discipline built on top of it."),

    # --- AI ------------------------------------------------------------------
    ("ai",
     "An AI assistant autonomously plans the multi-step rollback of a failed change and executes it, checking results between steps. Which capability is this?",
     ["Agentic AI", "Generative AI", "AI maturity", "AI governance"],
     "Planning and autonomously executing actions toward a goal is agentic AI. GenAI creates content; AI maturity describes the organization; AI governance directs and controls the use of all of it."),

    # --- Other frameworks ----------------------------------------------------
    ("frameworks",
     "Which statement BEST describes the relationship between ITIL and DevOps?",
     ["They are complementary: ITIL contributes service-management structure, DevOps contributes flow and automation", "DevOps replaces ITIL for digital organizations", "ITIL must be fully implemented before DevOps can be adopted", "They cannot be used in the same organization"],
     "The syllabus position is complementarity — each strengthens the other. Any option built on 'replaces', 'must come first' or 'incompatible' contradicts it."),
    ("frameworks",
     "Why are PRINCE2 and ITIL described as complementary?",
     ["PRINCE2 manages the temporary project that introduces a change; ITIL manages the product or service across its ongoing lifecycle", "PRINCE2 covers services and ITIL covers projects", "They are alternative names for the same framework", "PRINCE2 is the successor to ITIL"],
     "Projects are temporary and end; products and services live on. PRINCE2 governs the change initiative, ITIL the lifecycle it lands in — the reverse mapping is the standard distractor."),
]

_json_quiz = []
for i, (cat, q, options, expl) in enumerate(QUIZ, 1):
    assert cat in _cat_labels, cat
    assert len(options) == 4, q
    _json_quiz.append({
        "id": "qz-%02d" % i, "type": "quiz", "category": cat,
        "category_label": _cat_labels[cat], "question": q,
        "options": options, "answer": 0,  # authored order: index 0 correct; app shuffles
        "explanation": expl,
    })

# Official syllabus categories mapped onto our keys — shared source for the
# glossary chips and the future flashcards filters / score tracker.
DOMAINS = [
    {"number": 1, "key": "terms",      "name": "Key ITIL terms and definitions",                 "weight": 30},
    {"number": 2, "key": "dims",       "name": "The Four Dimensions of Product and Service Management", "weight": 10},
    {"number": 3, "key": "lifecycle",  "name": "The ITIL Product and Service Lifecycle",         "weight": 10},
    {"number": 4, "key": "svs",        "name": "The ITIL Value System",                          "weight": 40},
    {"number": 5, "key": "streams",    "name": "Value stream identification, mapping, and management", "weight": 5},
    {"number": 6, "key": "ai",         "name": "ITIL and AI",                                    "weight": 2.5},
    {"number": 7, "key": "frameworks", "name": "ITIL and other frameworks",                      "weight": 2.5},
]
assert {d["key"] for d in DOMAINS} == set(_cat_labels), "domain keys must match categories"

_data = {
    "version": 1,
    "generated": _dt.now(_tz.utc).isoformat(timespec="seconds"),
    "exam": {"questions": 40, "minutes": 60, "pass_mark": 26, "pass_pct": 65,
             "negative_marking": False, "closed_book": True},
    "categories": _cat_labels,
    "domains": DOMAINS,
    "terms": _json_terms,
    "scenarios": _json_scenarios,
    "quiz": _json_quiz,
}
_out = (_Path(_settings.BASE_DIR) / "output" / "sites" / site.slug
        / "assets" / "data" / "itil-glossary.json")
_out.parent.mkdir(parents=True, exist_ok=True)
_out.write_text(_json.dumps(_data, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", _out, "| terms:", len(_json_terms), "| scenarios:", len(_json_scenarios),
      "| quiz:", len(_json_quiz))
