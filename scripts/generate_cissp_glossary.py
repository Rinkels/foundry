# -*- coding: utf-8 -*-
"""CISSP Security Acronyms & Definitions — glossary article generator.

The glossary is authored HERE as structured data (TERMS/REMEMBER below) and
rendered into a self-contained HTML body for an EvergreenArticle on the
mindsgate-redesign site -> /insights/cissp-security-glossary.html.

Design notes (constraints of the sites_builder article pipeline):
- Body starts with "<" so _render_article_html passes it through as HTML.
- NO <dl> anywhere: cardify_subsections converts every <dl> into a Bootstrap
  accordion, which would break no-JS readability and filtering.
- Each category is a direct-child <section> of one outer <section>, so
  cardify_subsections wraps each category in the house .section-card style.
- All CSS/JS is inline and dependency-free; the page is fully readable with
  JavaScript disabled (controls stay hidden until JS reveals them).

Run:
  python manage.py shell -c "exec(open(r'C:\\Projects\\foundry\\scripts\\generate_cissp_glossary.py', encoding='utf-8').read())"
Then:
  python manage.py build_site mindsgate-redesign
"""
import re
from html import escape


def slug_id(acr):
    """Stable per-term anchor id — must match term_id() used for the JSON export."""
    return re.sub(r"[^a-z0-9]+", "-", acr.lower()).strip("-")

SLUG = "cissp-security-glossary"
TITLE = "CISSP Security Acronyms & Definitions: A Practical Study Glossary"
META_DESCRIPTION = ("Practical CISSP cybersecurity glossary covering security acronyms, "
                    "definitions and study tips across risk, cryptography, IAM, networking, "
                    "security operations and secure software development.")
ISC2_OUTLINE_URL = "https://www.isc2.org/certifications/cissp/cissp-certification-exam-outline"
DISCLAIMER = ("Independent CISSP study aid. CISSP is a registered trademark of ISC2. "
              "This resource is not affiliated with or endorsed by ISC2.")

# key -> (full name, short chip label)
CATS = [
    ("risk", "Risk, Governance & Continuity", "Risk & Governance"),
    ("data", "Data & Asset Security", "Data"),
    ("crypto", "Cryptography", "Crypto"),
    ("network", "Communication & Network Security", "Network"),
    ("iam", "Identity & Access Management", "IAM"),
    ("assess", "Security Assessment & Testing", "Testing"),
    ("ops", "Security Operations", "Operations"),
    ("cloud", "Software & Cloud Security", "Software & Cloud"),
]

# (cat, acronym, full term, definition, priority "core"|"ext", study tip or None)
TERMS = [
    # ---- Risk, Governance & Continuity ------------------------------------
    ("risk", "Exam tips", "Exam Tips — Read Like a Lawyer",
     "Most lost marks are READING errors, not knowledge gaps: a missed NOT, a skimmed qualifier, a plausible extra ticked on a multi-select. Before answering, slow down on the question itself — the technique rules are under “In depth”. The same panel appears at the start of every Exam Practice session in the flashcards app.", "core",
     "Restate what the question actually asks in eight words or fewer BEFORE reading the options. If you can't, you haven't finished reading the question."),
    ("risk", "CIA", "Confidentiality, Integrity, Availability",
     "The three classic objectives of information security.", "core",
     "Practically every Domain 1 question maps back to one of these three."),
    ("risk", "GRC", "Governance, Risk and Compliance",
     "Organizational management of governance requirements, risk and compliance obligations.", "ext", None),
    ("risk", "BIA", "Business Impact Analysis",
     "Identifies critical business processes and evaluates the effect of disruption.", "core",
     "The BIA comes first — its findings feed RTO, RPO and MTD."),
    ("risk", "BC", "Business Continuity",
     "Maintaining essential business operations through a disruption.", "core", None),
    ("risk", "BCP", "Business Continuity Plan",
     "Documented approach for continuing critical business functions.", "core", None),
    ("risk", "DR", "Disaster Recovery",
     "Restoration of technology and services following a disruptive event.", "core",
     "BC keeps the business running; DR restores the technology behind it."),
    ("risk", "DRP", "Disaster Recovery Plan",
     "Documented procedures for restoring technology and services.", "core", None),
    ("risk", "RTO", "Recovery Time Objective",
     "Maximum target time for restoring a service after disruption.", "core",
     "\u201cHow long can the service be down?\u201d Pair it with RPO."),
    ("risk", "RPO", "Recovery Point Objective",
     "Maximum acceptable amount of data loss, measured in time.", "core",
     "\u201cHow much data can we lose?\u201d It sizes your backup frequency."),
    ("risk", "MTD", "Maximum Tolerable Downtime",
     "Longest period a business process can remain unavailable before unacceptable impact occurs.", "core",
     "MTD caps RTO: the RTO you commit to must fit inside the MTD."),
    ("risk", "MTTF", "Mean Time To Failure",
     "Expected operating time before a component fails.", "ext", None),
    ("risk", "MTTR", "Mean Time To Repair (or Recover)",
     "Average time required to restore a failed system or service.", "core",
     "MTTF is time until failure; MTTR is time to fix it."),
    ("risk", "SLE", "Single Loss Expectancy",
     "Expected monetary loss from one occurrence of a risk event.", "core",
     "SLE = Asset Value \u00d7 Exposure Factor."),
    ("risk", "ARO", "Annualized Rate of Occurrence",
     "Estimated number of times an event will occur in one year.", "core", None),
    ("risk", "ALE", "Annualized Loss Expectancy",
     "Expected annual financial loss from a risk.", "core",
     "ALE = SLE \u00d7 ARO — memorize it; quantitative-risk questions are free marks."),
    ("risk", "KPI", "Key Performance Indicator",
     "Metric measuring performance against an objective.", "ext", None),
    ("risk", "KRI", "Key Risk Indicator",
     "Metric indicating changing risk exposure.", "ext",
     "KPI looks at performance; KRI looks ahead at rising risk."),
    ("risk", "SLA", "Service Level Agreement",
     "Agreement defining measurable service expectations.", "core", None),
    ("risk", "SoD", "Separation (Segregation) of Duties",
     "Dividing sensitive responsibilities among multiple people to reduce fraud and error risk.", "core",
     "A classic control against fraud — often the answer when one person holds end-to-end power."),
    ("risk", "SCRM", "Supply Chain Risk Management",
     "Managing cybersecurity and operational risks introduced by suppliers, products and services.", "ext", None),
    ("risk", "NIST", "National Institute of Standards and Technology",
     "US standards organization that publishes widely used cybersecurity frameworks and guidance.", "core", None),
    ("risk", "COBIT", "Control Objectives for Information and Related Technologies",
     "ISACA framework for governance and management of enterprise IT, built on six key principles for the governance system.", "ext",
     "Know the six principles by name — plausible security phrases like “maintaining authenticity and accountability” are NOT among them."),
    ("risk", "Decomposition", "Reduction Analysis (Decomposing the System)",
     "The threat-modeling step after modeling itself: breaking an application, system or environment down to understand its logic, internal components and external interactions — identifying five key concepts.", "ext",
     "The five concepts are structural. “Patch/update versions” and “open- vs closed-source” sound reasonable but are NOT decomposition components."),
    ("risk", "SABSA", "Sherwood Applied Business Security Architecture",
     "Business-driven framework for security architecture.", "ext", None),
    ("risk", "Threat modeling", "Threat Modeling Approaches",
     "Structured identification of relevant threats. The three commonly recognized approaches are: focus on ATTACKERS (who would come after us and what are they capable of), focus on ASSETS (what is valuable and how could it be reached), and focus on SOFTWARE / systems (where could what we build be abused). Methodologies like STRIDE, PASTA and VAST operate within these approaches.", "core",
     "Exactly three recognized approaches: attackers, assets, software. “Focus on insiders” and “focus on stakeholders” are plausible-sounding distractors — insiders are a threat SOURCE, not an approach."),
    ("risk", "STRIDE", "Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege",
     "Microsoft's threat-categorization model: every identified threat is classified into one of the six S-T-R-I-D-E categories.", "core",
     "The four threat-modeling names in one line: STRIDE categorizes, DREAD rates, PASTA runs a 7-stage risk-centric process, VAST scales threat modeling into Agile."),
    ("risk", "PASTA", "Process for Attack Simulation and Threat Analysis",
     "Risk-centric threat-modeling methodology with seven stages — from business objectives through attack simulation to countermeasures weighted by the value of the assets protected.", "ext",
     "The exam phrase is “risk-centric / countermeasures in relation to asset value” — and know that it has SEVEN stages."),
    ("risk", "VAST", "Visual, Agile and Simple Threat",
     "Threat-modeling approach designed to integrate into Agile development pipelines and scale across an entire enterprise.", "ext",
     "“Agile” or “scalable” in the question stem points at VAST."),
    ("risk", "DREAD", "Damage, Reproducibility, Exploitability, Affected users, Discoverability",
     "Threat-rating scheme that scores each identified threat by answering five questions: Damage, Reproducibility, Exploitability, Affected users, Discoverability.", "ext",
     "DREAD does not find threats — it RATES threats you have already found."),
    ("risk", "PCI DSS", "Payment Card Industry Data Security Standard",
     "Security standard protecting payment-card data.", "ext", None),
    ("risk", "GLBA", "Gramm-Leach-Bliley Act",
     "US law governing how financial institutions handle customers' personal financial information, including privacy notices and safeguards.", "core",
     "Bank + personal information = GLBA. SOX is public-company financial REPORTING; HIPAA is health; FISMA is federal agencies."),
    ("risk", "HIPAA", "Health Insurance Portability and Accountability Act",
     "US law protecting the privacy and security of individually identifiable health information (PHI); carries civil and criminal penalties.", "core",
     "Health data = HIPAA, and it is one of the laws with CRIMINAL penalties (alongside SOX)."),
    ("risk", "SOX", "Sarbanes-Oxley Act",
     "US law imposing financial-reporting integrity and internal-control requirements on publicly traded companies; executives face criminal liability.", "core",
     "Public-company financial reporting = SOX. It is about report integrity, not personal-information privacy — the GLBA trap."),
    ("risk", "FERPA", "Family Educational Rights and Privacy Act",
     "US law protecting the privacy of student education records; enforcement is through federal-funding consequences, not criminal penalties.", "ext",
     "Education records = FERPA — the law WITHOUT criminal penalties in the classic compare-the-laws question."),
    ("risk", "FISMA", "Federal Information Security Modernization Act",
     "US law requiring federal agencies (and their contractors) to implement information-security programs, following NIST guidance.", "ext",
     "Federal agency or government contractor in the stem = FISMA."),
    ("risk", "CASL", "Canada's Anti-Spam Legislation",
     "Canadian federal law (in force 1 July 2014) regulating commercial electronic messages — email, SMS, social DMs — sent to or from Canada, and prohibiting unconsented software installation or alteration of transmission data.", "ext",
     "CASL is OPT-IN where the US CAN-SPAM Act is opt-out: consent must exist BEFORE the first message — and implied consent EXPIRES (about two years after a purchase, six months after an inquiry)."),
    ("risk", "GDPR", "General Data Protection Regulation",
     "European Union data-protection and privacy regulation.", "core", None),
    ("risk", "PbD", "Privacy by Design",
     "Cavoukian's guideline for integrating privacy into products during design rather than bolting it on afterwards, built on SEVEN foundational principles (listed under “In depth”). The exam loves salting the list with principles from other frameworks.", "core",
     "The classic fake options are borrowed from elsewhere: “never trust, always verify” (zero trust), “trust but verify” (the approach zero trust replaced), and Clark-Wilson's access triplet. If it sounds like network architecture, it isn't PbD."),
    ("risk", "Due care", "Due Care vs Due Diligence",
     "Due DILIGENCE is establishing the plan, policies and processes that protect the organization's interests — the homework and the programme design. Due CARE is practicing the individual, ongoing activities that maintain that effort — what a prudent person actually does day to day. Skipping periodic security audits is the classic sign that due care is not being maintained, because nobody is checking that the programme still works.", "core",
     "Diligence = Design the programme (plans, policies, board structures); Care = Carry it out (operate controls, audit periodically). The exam's favourite: absent AUDITS = due care in doubt."),
    ("risk", "Risk frameworks", "Risk Management Frameworks",
     "The named frameworks for managing risk the exam expects you to recognize: NIST RMF, COSO's ERM (Enterprise Risk Management), ISACA's Risk IT, OCTAVE, FAIR and TARA. The trap is the lookalikes: NIST itself is an agency, ARO is a quantitative-analysis metric, CEH is a certification, CCMP is a wireless cipher mode — none of them are frameworks.", "ext",
     "Memorize the six: RMF, COSO ERM, Risk IT, OCTAVE, FAIR, TARA. Everything else offered is usually a metric, an agency or a cert wearing a framework costume."),
    ("risk", "Divestiture", "Divestiture & Asset-Reduction Security",
     "When anything leaves the organization — a device, a service, an employee, a business unit — focused security processes reduce the risk of data loss: sanitize the assets, remove and destroy storage media, and debrief departing employees (remind them of NDAs and surrender of access). Updating firmware, renewing certificates or improving features on outbound assets is wasted effort.", "ext",
     "Divestiture questions are about what LEAVES: sanitize, destroy media, debrief people. Anything that invests in the departing asset (patches, certs, features) is a distractor."),
    ("risk", "VMS", "Vendor Management System",
     "Software for managing and procuring across multiple third-party suppliers: ordering convenience, order distribution, training management and consolidated billing in one place. Distinguish from the paper: an SLR states the expectations of a vendor's service before contract; an SLA makes agreed levels binding; a BPA is a contract between business partners defining their mutual obligations.", "ext",
     "“Many vendors, consolidate ordering/training/billing” = the VMS (a system). SLR/SLA/BPA are documents — if the stem asks for a management TOOL across existing suppliers, paper answers are wrong."),
    ("risk", "Risk financing", "Risk Financing & Retention Funds",
     "How an organization pays for losses it has decided to live with: transfer (insurance moves the financial impact to someone else) or retention (accept the loss and fund it in advance, through reserves, a captive insurer, or a dedicated self-insurance fund). A crypto exchange's pre-funded emergency fund — used to make customers whole after a breach — is risk retention with explicit financing, not a control that reduces likelihood.", "ext",
     "Buying insurance = transfer; a funded reserve = retention. Both address the financial IMPACT of residual risk — neither one reduces the risk itself."),
    ("risk", "Hoax", "Hoax (Social Engineering)",
     "A social-engineering message that uses FEAR to trick the victim into self-inflicted harm: it threatens damage, then helpfully supplies the “fix” — steps that actually cause the damage. Its three distinguishing indicators: the claimed sender confirms they never sent it, a threat of damage to your system, and encouragement to take specific steps to resolve the concern. Poor grammar, bad spelling, embedded hyperlinks and trusted-authority claims appear in legitimate AND malicious mail alike, so they identify nothing.", "ext",
     "Hoax indicators = sender denies sending + threatened harm + do-these-steps. Grammar, spelling, links and “I'm from IT” are shared with ordinary email and ordinary phishing — classic wrong answers."),
    ("risk", "DMCA", "Digital Millennium Copyright Act",
     "The 1998 US federal law that prohibits attempts to CIRCUMVENT copyright protection mechanisms (DRM, encryption on media) placed on a protected work — and gives online providers the safe-harbor/takedown regime. Keep the IP family straight: copyright protects expression, trademark protects brand identifiers, patents protect inventions, trade secrets protect confidential know-how.", "ext",
     "“Bypassing copy protection” = DMCA. The “Copyright Enhancement Act” does not exist, trade-secret law is a different branch of IP, and the PATRIOT Act is about surveillance powers — all decoys."),
    ("risk", "Third party", "Third-Party Connectivity Risk",
     "Risk-assessment areas of concern where an actual OUTSIDER connects directly to your on-premises networks: business partnerships, cloud services and telecommuting employees' home environments. Connecting your OWN branches over VPN links is not third-party connectivity — both ends are you.", "ext",
     "The test is “who is on the other end?”. Partner, cloud provider, teleworker = third party. Your own branch office = first party, however the link is built."),
    ("risk", "Ethics", "ISC2 Code of Ethics",
     "The four mandatory canons every ISC2 member commits to, in priority order: I — protect society, the common good, necessary public trust and confidence, and the infrastructure; II — act honorably, honestly, justly, responsibly and legally; III — provide diligent and competent service to principals; IV — advance and protect the profession. The heavily tested twist is WHO MAY FILE a complaint under each canon (see “In depth”).", "core",
     "Standing to complain: Canons I and II — ANY member of the public; Canon III — only an employer or contracted organization (the principal); Canon IV — other professionals (anyone certified or licensed in any field). An outside investigator who is a CPA = public (I, II) + professional (IV), but never III."),
    # ---- Data & Asset Security --------------------------------------------
    ("data", "PII", "Personally Identifiable Information",
     "Information that identifies, or can reasonably identify, an individual.", "core", None),
    ("data", "PHI", "Protected Health Information",
     "Individually identifiable health information subject to privacy and security protection.", "core", None),
    ("data", "DLP", "Data Loss Prevention",
     "Technologies and processes designed to detect and prevent unauthorized disclosure or movement of sensitive information.", "core",
     "DLP asks: \u201ccan the data leave?\u201d (NAC asks whether the device may enter.)"),
    ("data", "DRM", "Digital Rights Management",
     "Controls governing access to and use of protected digital content — typically via persistent online authentication, automatic expiration, and a continuous audit trail.", "ext",
     "Know the three real DRM techniques; “virtual licensing” is an invented distractor."),
    ("data", "Scoping", "Scoping (and Tailoring) of Baselines",
     "Part of tailoring a security baseline: reviewing the list of baseline controls and SELECTING only those that apply to the system being secured.", "ext",
     "Scoping = pick the applicable controls; tailoring = align the selected controls to the organization's mission; standards selection = adopting an external baseline a regulator or partner requires."),
    ("data", "CASB", "Cloud Access Security Broker",
     "Security policy and enforcement layer between cloud-service users and cloud providers.", "ext", None),
    ("data", "EOL", "End of Life",
     "Point at which a product is no longer actively developed.", "ext", None),
    ("data", "EOS", "End of Support",
     "Point after which the vendor no longer provides normal support or security updates.", "ext",
     "EOL ends development; EOS ends patches — EOS is the security cliff."),
    ("data", "FDE", "Full Disk Encryption",
     "Encryption protecting the contents of an entire storage device.", "core", None),
    # ---- Cryptography ------------------------------------------------------
    ("crypto", "AES", "Advanced Encryption Standard",
     "Widely used symmetric encryption algorithm suitable for fast bulk-data encryption.", "core",
     "Symmetric = one shared key = fast bulk encryption."),
    ("crypto", "RSA", "Rivest\u2013Shamir\u2013Adleman",
     "Asymmetric cryptographic algorithm used for operations including digital signatures and key-related functions.", "core",
     "Asymmetric = key pairs = signatures and key exchange, not bulk data."),
    ("crypto", "ECC", "Elliptic Curve Cryptography",
     "Public-key cryptography based on elliptic curves, providing strong security with comparatively small keys.", "core",
     "Same strength, smaller keys — think mobile and IoT."),
    ("crypto", "DH", "Diffie\u2013Hellman",
     "Cryptographic method allowing parties to establish shared key material over an untrusted network.", "core",
     "Key agreement, not encryption — it establishes a shared secret."),
    ("crypto", "ECDH", "Elliptic Curve Diffie\u2013Hellman",
     "Diffie\u2013Hellman key agreement implemented using elliptic-curve cryptography.", "ext", None),
    ("crypto", "SHA", "Secure Hash Algorithm",
     "Family of cryptographic hash functions used to create fixed-length message digests.", "core",
     "Hashing = integrity. One-way; no key; any change alters the digest."),
    ("crypto", "HMAC", "Hash-based Message Authentication Code",
     "Uses a cryptographic hash plus a secret key to provide message integrity and authenticity.", "core",
     "SHA proves integrity; adding the key (HMAC) also proves who sent it."),
    ("crypto", "PKI", "Public Key Infrastructure",
     "Technologies, policies and processes used to manage public/private keys and digital certificates.", "core", None),
    ("crypto", "CA", "Certificate Authority",
     "Trusted entity that issues and signs digital certificates.", "core", None),
    ("crypto", "RA", "Registration Authority",
     "Entity that verifies identities before certificate issuance.", "ext",
     "RA verifies; CA signs. The RA never issues certificates itself."),
    ("crypto", "CSR", "Certificate Signing Request",
     "Request containing the information a CA needs to issue a certificate.", "ext", None),
    ("crypto", "CRL", "Certificate Revocation List",
     "Published list of certificates revoked before their expiration date.", "core",
     "CRL = periodically downloaded list; OCSP = real-time status query."),
    ("crypto", "OCSP", "Online Certificate Status Protocol",
     "Protocol used to check whether a certificate has been revoked.", "core", None),
    ("crypto", "TPM", "Trusted Platform Module",
     "Hardware security component used to protect cryptographic keys and support platform integrity.", "core",
     "TPM is built into a platform; an HSM is dedicated key hardware."),
    ("crypto", "TCB", "Trusted Computing Base",
     "The combination of hardware, software and controls that enforces the security policy. Its access-validation concept is the REFERENCE MONITOR — which, when implemented in code, is called the SECURITY KERNEL.", "core",
     "The naming trap: one name in theory (reference monitor — validates every access before granting), another in implementation (security kernel). “TCB partition” and “trusted library” are invented components."),
    ("crypto", "ATO", "Authorization to Operate",
     "The formal risk-acceptance decision (NIST RMF) that a system may run. An authorizing official can issue four decision types: authorization to operate, common control authorization, authorization to use, and denial of authorization.", "ext",
     "Know the four real decisions — “mutual”, “verified” and “transfer” authorization are invented distractors."),
    ("crypto", "Rings", "Protection Ring Model",
     "Layered CPU/OS privilege model: Ring 0 = kernel (most privileged), Rings 1–2 = OS services and drivers, Ring 3 = user applications; inner rings control outer ones.", "ext",
     "Ring 0 vs Ring 3 is the tested pair — and “protection rings” also appears in the defense-in-depth term cluster."),
    ("crypto", "DiD", "Defense in Depth",
     "Multiple different controls arranged in series so that no single control's failure exposes the asset.", "core",
     "Study materials cluster these terms with DiD: layering, classifications, zones, realms, compartments, silos, segmentations, lattice structure, protection rings."),
    ("crypto", "CPA", "Critical Path Analysis",
     "Systematic facility-design method that maps the relationships between mission-critical applications, processes and operations and ALL of their supporting elements — power, HVAC, communications, water.", "ext",
     "Facility-design context is the tell. Risk analysis evaluates threats × consequences; inventory just lists assets — neither maps dependencies."),
    ("crypto", "CPTED", "Crime Prevention Through Environmental Design",
     "Reducing crime by shaping the physical environment itself — first-generation CPTED rests on four core strategies: natural access control, natural surveillance, territorial control, and image/milieu.", "core",
     "Know the four first-generation strategies; invented-sounding options (“natural training and enrichment”) are classic distractors."),
    ("crypto", "Sprinklers", "Water-Based Fire Suppression Systems",
     "Four types: wet pipe (water always charged), dry pipe (air-filled until triggered), preaction (two-stage trigger — best for computer facilities), and deluge (open heads, high volume).", "core",
     "Preaction is the answer for computer rooms: the second trigger prevents accidental water release. Wet, dry and deluge all release on a single trigger."),
    ("crypto", "Cable plant", "Cable Plant Management",
     "Mapping and documenting a facility's physical network cabling infrastructure, from the entrance facility (demarcation point) through distribution to the endpoints.", "ext",
     "Know the five elements — person traps, fire escapes, UPSs and loading docks are NOT cable-plant elements."),
    ("crypto", "6 Ds", "Physical Security Control Order",
     "The functional order in which physical security controls should engage an intruder: Deter → Deny → Detect → Delay → Determine → Decide.", "ext",
     "Order matters and is tested verbatim — deterrence comes first, decision comes last."),
    ("crypto", "HSM", "Hardware Security Module",
     "Dedicated secure hardware for generating, protecting and using cryptographic keys.", "core", None),
    ("crypto", "MPP", "Parallel Processing: SMP, AMP, MPP, Multicore",
     "The multiprocessing taxonomy: SMP (symmetric) — processors SHARE one OS, memory and bus; AMP (asymmetric) — each processor has its OWN instruction set, memory and bus; MPP (massive parallel processing) — thousands of AMP-style independent processors under a single master coordination system; multicore — multiple execution cores on one chip, a component of all of the above rather than an architecture.", "ext",
     "Read the scenario for ownership: shared OS/memory/bus = SMP; own instructions + own memory = AMP; thousands of those under one coordinator = MPP. Multicore alone is never the “large-scale system” answer."),
    ("crypto", "HPC", "High-Performance Computing",
     "Systems for real-time or near-real-time processing of massive data sets, built from three elements that must offer EQUIVALENT capability to avoid bottlenecks: compute resources, network capability and storage capacity. Distinguish grid computing: a LOOSE federation of many nodes volunteering cycles toward a goal, without the balanced, dedicated build.", "ext",
     "“Three elements — compute, network, storage — each equivalent” is the HPC fingerprint. Grid = loosely grouped distributed nodes; IoT = smart devices; EOSL = a product the vendor abandoned."),
    ("crypto", "Extinguishers", "Fire Extinguisher Classes",
     "The extinguisher classes and their media, tested as “which medium may/may not be used on a class X fire”. The full class table is under “In depth”. The headline trap: water is NEVER a medium for Class B (liquid) fires — it spreads burning liquid.", "core",
     "Class B = liquids = CO2, halon (or substitute) or soda acid — never water. Class C = electrical = must be non-conductive (CO2/halon). Class D = metals = dry powder. K = kitchen oils = wet chemical."),
    ("crypto", "PIDAS", "Perimeter Intrusion Detection and Assessment System",
     "A fence SYSTEM of two or three concentric fences: the space between them forms a clear patrol corridor for guards or dogs, one or more fences carry touch-detection sensors, and the plain outer fence keeps animals and casual trespassers off the sensor fence — cutting the nuisance alarm rate (NAR).", "ext",
     "Fences + guard corridor + sensing + fewer false alarms = PIDAS. CPTED is the design philosophy, a SCIF is a secure information facility, and an MDF is the main wiring closet."),
    ("crypto", "CC", "Common Criteria (ISO/IEC 15408)",
     "The international framework for evaluating security products. A customer's requirements are written as a Protection Profile (PP — the “I want”), a vendor's claims as a Security Target (ST — the “I will provide”) about the Target of Evaluation (TOE), and an independent lab grades the evaluation rigour as EAL1–7. Its defining difference from the systems it replaced (TCSEC/ITSEC): it is a DYNAMIC and SUBJECTIVE evaluation driven by comparing PPs against STs, not a fixed static checklist.", "core",
     "PP = customer's wish list, ST = vendor's promise, TOE = the product, EAL = how hard anyone checked. The “primary distinction” answer is dynamic + subjective via PP/ST comparison."),
    ("crypto", "UEM", "Unified Endpoint Management",
     "One management platform for every endpoint class — mobile phones, PCs, IoT, wearables, industrial devices — intended to replace separate MDM (mobile device management) and EMM (enterprise mobility management) products. Goals: enforce security policy, monitor, remotely manage and troubleshoot from a single console. Point controls like application allow-listing are features WITHIN such a solution, not the solution.", "ext",
     "“Best security control over mobile/endpoint equipment” = UEM (or MDM in older material). A single named feature — allow listing, geofencing, containerization — is never the “best overall control” answer."),
    ("crypto", "DSS", "Digital Signature Standard (FIPS 186-5)",
     "The US federal standard for digital signatures. FIPS 186-5 approves three algorithms: RSA, ECDSA (Elliptic Curve DSA) and EdDSA (Edwards-Curve DSA).", "ext",
     "Three approved: RSA, ECDSA, EdDSA. The original DSA was dropped in 186-5, and ElGamal was never in the standard — both are distractors."),
    ("crypto", "PFX", "Personal Information Exchange (PKCS#12)",
     "Binary certificate file format closely associated with Windows, typically bundling a certificate WITH its private key, password-protected (.pfx/.p12).", "ext",
     "Binary vs text is the tested split: PFX/P12 and DER are binary; PEM and P7B are text. Only PFX/P12 normally carries the private key."),
    ("crypto", "PFS", "Perfect Forward Secrecy",
     "Session-key design ensuring compromise of long-term keys does not expose previously encrypted sessions.", "ext",
     "Ephemeral session keys: yesterday's traffic stays safe even if today's private key leaks."),
    ("crypto", "MITM", "Man-in-the-Middle",
     "Attack in which an adversary intercepts and potentially alters communications between parties.", "core", None),
    ("crypto", "Merkle tree", "Merkle Tree (Hash Tree)",
     "A binary tree of hashes: each leaf is the hash of a data block and each parent is the hash of its two children, so one top value — the Merkle root — seals the entire data set. Changing any block changes the root, and membership of one block can be proven with only the sibling hashes up the tree (an inclusion proof). Used in blockchains, Certificate Transparency logs, secure file systems and exchange proof-of-reserves.", "ext",
     "The root is a tamper-evident seal; an inclusion proof needs log(n) sibling hashes, never the whole data set. That efficiency is what questions probe."),
    ("crypto", "ZKP", "Zero-Knowledge Proof",
     "A protocol by which a prover convinces a verifier that a statement is true without revealing anything beyond the statement itself. Defined by three properties: completeness (a true statement convinces an honest verifier), soundness (a false statement almost never convinces), and zero-knowledge (the verifier learns nothing else). zk-SNARKs are the succinct, non-interactive variant exchanges use to prove every customer balance was counted in a reserves total without revealing any account.", "ext",
     "Know the three properties: completeness, soundness, zero-knowledge. The exam angle is proving possession (of a password, a key, a balance) without disclosure."),
    ("crypto", "Cold storage", "Cold vs Hot Key Storage",
     "A key-management split by exposure: cold keys are generated and held on devices that never touch a network (offline HSMs, air-gapped signing machines) and sign rarely, by deliberate ceremony; hot keys sit on online systems so they can sign automatically, which makes them the attack surface. The same pattern as keeping a root CA offline while issuing CAs run online. In the 2026 Binance breach, attackers who reached the hot-wallet signing infrastructure drained it in minutes — cold reserves were untouched.", "ext",
     "Minimize what is signable online. “Hot = automated and exposed, cold = offline and ceremonial” maps to online issuing CA vs offline root CA."),
    ("crypto", "Dual control", "Dual Control & Split Knowledge",
     "Two complementary key-management safeguards: dual control requires two or more people to perform one sensitive operation (no single person can sign alone); split knowledge divides the secret itself so no single person ever knows all of it. M-of-N control (any m of n custodians can reconstruct or authorize) and multi-signature schemes implement both at once.", "core",
     "Dual control splits the OPERATION; split knowledge splits the INFORMATION. Multi-sig wallets and m-of-n key escrow are both children of these two ideas."),
    ("crypto", "Secure design", "Secure Design Principles",
     "The canonical list of principles woven into security architecture and policy: least privilege, secure defaults, fail securely, threat modeling, keep it simple, separation of duties, zero trust, privacy by design — plus defense in depth and trust-but-verify. The exam salts the list with three plausible-sounding IMPOSTORS, listed with the real set under “In depth”.", "core",
     "The three fakes to reject on sight: “people are the weakest link” (people are also a key control), “security is always top priority” (business objectives bound security), and “risk should be eliminated” (it can only be reduced, transferred, avoided or accepted)."),
    ("crypto", "Containers", "Containerization (OS Virtualization)",
     "Virtualization that eliminates duplication of OS elements: containers share the host kernel instead of each carrying a guest OS. Some solutions allow multiple concurrent applications within a single container, and many allow customization of how much interaction applications in separate containers may have. A FULL guest OS per instance is the virtual-machine model (hypervisor on bare metal), not containerization.", "core",
     "Container capabilities = multi-app per container + tunable inter-container interaction. “Full guest OS” and “hypervisor” point to VMs; “automate network monitoring and response” is SDV (software-defined visibility) — a different S-D entirely."),
    ("crypto", "Alarms", "Alarm Types (Physical Security)",
     "Alarms fire AFTER an intrusion is detected, so there is no such thing as a “preventive” alarm. The three typical types: deterrent alarms (engage locks/shutters to make further intrusion harder), repellent alarms (sirens and lights that drive the intruder off), and notification alarms (silently alert guards or police while recording).", "ext",
     "Deterrent, repellent, notification — and NEVER preventive: an alarm is a response to detection, not a prevention. “Which is not a typical alarm type?” = preventive."),
    ("crypto", "Key counts", "Cryptographic Key-Count Formulas",
     "The two formulas the exam loves: SYMMETRIC cryptography needs a unique shared key per pair — n(n−1)/2 keys for n participants (8 people = 28). ASYMMETRIC needs one key PAIR per participant — 2n keys (8 people = 16). Read which system the stem names before reaching for a formula.", "core",
     "Symmetric = n(n−1)/2 (pairs). Asymmetric = 2n (everyone gets a public+private pair). The distractors are always the OTHER formula's result — for 8 people: 16 vs 28, with 8 and 56 as noise."),
    ("crypto", "Cipher modes", "Block Cipher Modes of Operation",
     "How a block cipher is applied across many blocks: ECB, CBC, CFB, OFB, CTR, GCM and CCM. The tested properties are chaining (does each block depend on the previous one?) and parallelism. For a PARALLELIZED environment the answer is Galois/Counter Mode — counter modes break the work into independent steps, and GCM adds authentication; chaining modes (CBC, CFB) cannot parallelize, and ECB can but is insecure. Full table under “In depth”.", "core",
     "“Distribute encryption across processors” = GCM (or CTR). CBC/CFB chain on the previous block, so they can't. ECB parallelizes fine and is still wrong — identical blocks leak patterns."),
    ("crypto", "Cert checks", "Digital Certificate Verification",
     "What to verify BEFORE relying on a certificate: the CA's digital signature on it is authentic, it has not expired, and it has not been revoked (CRL/OCSP). What you do NOT pre-validate: the subject's public key — the key is the PAYLOAD you receive by trusting the certificate, not an input you check first.", "core",
     "Three checks: CA signature, expiry, revocation. “Verify the sender's public key is valid” is the trap — the certificate IS the validation of the key."),
    ("crypto", "Clark-Wilson", "Clark-Wilson Model Elements",
     "The integrity model built on well-formed transactions and separation of duties. Its defined elements: CDI (constrained data item — the protected data), UDI (unconstrained data item), TP (transformation procedure — the only way to change a CDI) and IVP (integrity verification procedure — checks CDIs are valid). Access flows through the triple subject→TP→CDI. A “redundant commit statement” belongs to database replication, not to this model.", "core",
     "CDI, UDI, TP, IVP — four elements, one access triple. Invented elements in the options usually sound like database admin vocabulary (“redundant commit statement”) rather than model vocabulary."),
    ("crypto", "Cache attacks", "Client Cache Attacks (Temporary Internet Files)",
     "If an adversary can reach the browser's temporary-internet-files cache, three attacks become possible: a split-response attack (tricks the client into caching content that was never part of the requested page), cache poisoning (a planted malicious item activates whenever a legitimate page calls the cached object), and DOM XSS (script abuses locally cached files to execute code or exfiltrate data). Identity THEFT is not among them — the cache rarely holds enough personal data to steal an identity.", "ext",
     "Cache access = split-response + cache poisoning + DOM XSS. Identity theft is the over-select bait: spoofing a site ≠ stealing an identity."),
    ("crypto", "Threads", "Multitasking, Multithreading, Multiprocessing",
     "The counting vocabulary: multitasking = the OS juggling several processes; multithreading = several threads within one process; multiprocessing = several processors (or cores) executing simultaneously. A dual-core single-processor system executes exactly TWO threads at any instant — one per core — no matter how many applications or threads are waiting; the OS schedules which ones run.", "core",
     "Threads running AT ANY GIVEN TIME = number of cores. Total threads that EXIST can be anything. A dual-core chip = 2 simultaneous; single-core = 1. Don't count the applications."),
    ("crypto", "DCE", "Distributed Computing Environment & IDL",
     "A DCE is a distributed system presenting many networked machines as one environment, typically defining client-server interfaces in an IDL (interface definition language). Example IDL frameworks: RPC (remote procedure calls), CORBA (Common Object Request Broker Architecture) and DCOM (Distributed Component Object Model). SAML is federation, OCSP is certificate status, SQL is database access — none is an IDL.", "ext",
     "The IDL family is RPC / CORBA / DCOM — all mechanisms for invoking code ACROSS machines. Anything whose job is authentication, revocation or queries is a decoy."),
    ("crypto", "Phys KPIs", "Physical Security KPIs",
     "The key performance indicators relevant to PHYSICAL security monitoring: number of successful intrusions, successful disruptions, unsuccessful incidents, time to detect incidents, time to respond to incidents, level of organizational impact, and number of false positives (false alarms). The distractors are IT metrics wearing a physical costume: compromised ACCOUNTS is logical security, and session disconnects, transmission errors and transactions-per-minute are network/operations statistics.", "ext",
     "If the metric counts something that happens to a NETWORK or an ACCOUNT, it is not a physical-security KPI. Doors, intruders, alarms, detection and response times — that's the physical list."),
    # ---- Communication & Network Security ----------------------------------
    ("network", "OSI", "Open Systems Interconnection",
     "Seven-layer conceptual networking model — 1 Physical, 2 Data Link, 3 Network, 4 Transport, 5 Session, 6 Presentation, 7 Application.", "core",
     "Know the seven layers in order (“Please Do Not Throw Sausage Pizza Away”) and which protocols and devices live at each."),
    ("network", "TCP/IP", "Transmission Control Protocol / Internet Protocol",
     "Core protocol suite underlying IP networks and the Internet; its four-layer model is Link, Internet, Transport, Application.", "core",
     "Mapping to OSI: Link ≈ 1–2, Internet ≈ 3, Transport ≈ 4, Application ≈ 5–7."),
    ("network", "IPSec", "Internet Protocol Security",
     "Suite of protocols for protecting IP communications. Operates at the NETWORK layer (OSI Layer 3) — the tested fact. AH authenticates, ESP encrypts, IKE negotiates keys; tunnel mode wraps whole packets, transport mode protects only the payload.", "core",
     "Layer placement is the question: IPsec = Layer 3. L2TP and PPTP are the Data Link VPNs; TLS and SSH protect at the Transport layer; and TCP/IP has no real Session layer at all."),
    ("network", "VPN", "Virtual Private Network",
     "Protected logical connection across an untrusted network. Protocols that CAN serve as a VPN: IPsec, TLS and SSH (plus the legacy L2TP/PPTP). Protocols that cannot: Kerberos (ticket-based SSO authentication), Signal (end-to-end encrypted messaging/voice) and S-RPC (authenticated remote procedure calls) — secure, but none of them carries general network traffic in a tunnel.", "core",
     "“Which can be used as a VPN?” = IPsec, TLS, SSH. The distractors are always secure protocols with a different job — authentication (Kerberos, S-RPC) or messaging (Signal)."),
    ("network", "VLAN", "Virtual Local Area Network",
     "Logical separation of network devices into distinct broadcast domains.", "core", None),
    ("network", "IDS", "Intrusion Detection System",
     "Detects suspicious or malicious activity.", "core",
     "IDS detects and alerts; IPS sits inline and can block."),
    ("network", "IPS", "Intrusion Prevention System",
     "Detects suspicious activity and can actively block it.", "core", None),
    ("network", "IDPS", "Intrusion Detection and Prevention System",
     "Combined intrusion detection and prevention capability.", "ext", None),
    ("network", "WAF", "Web Application Firewall",
     "Filters and protects HTTP/HTTPS traffic to web applications.", "core", None),
    ("network", "NAC", "Network Access Control",
     "Controls whether users and devices are permitted to connect to a network.", "core",
     "NAC asks: \u201cmay the device enter?\u201d (DLP asks whether the data may leave.)"),
    ("network", "SASE", "Secure Access Service Edge",
     "Cloud-delivered architecture combining networking and security capabilities.", "ext", None),
    ("network", "Converged protocols", "Converged Protocols",
     "Specialty traffic merged onto standard IP/Ethernet networks instead of dedicated infrastructure: iSCSI (SAN storage over IP), VoIP (voice), FCoE (Fibre Channel over Ethernet), MPLS (label-switched transport) and CXL (Compute Express Link — high-speed CPU-to-accelerator/memory interconnect used in AI/ML infrastructure). One network to manage; one network to attack.", "ext",
     "“SAN + voice + AI/ML on the ordinary network” = iSCSI, VoIP, CXL. TFTP is a file-transfer protocol, not a converged protocol — a favourite odd-one-out."),
    ("network", "BGP", "Border Gateway Protocol (exterior routing)",
     "THE exterior gateway protocol: routes traffic BETWEEN autonomous systems — your border router speaks BGP to the outside world. The interior protocols route WITHIN your network: RIP (distance-vector, hop count), OSPF (link-state) and IGRP/EIGRP (Cisco). Symptom mapping: external destinations unreachable while internal traffic flows = suspect the border router's BGP.", "core",
     "Exterior = BGP, full stop. RIP, OSPF and IGRP are all interior. “Internal works, external broken after a device change” points at the border — BGP."),
    ("network", "OFDM", "Wireless Frequency Access: FHSS, DSSS, OFDM",
     "The three spread-spectrum/access methods: FHSS hops rapidly across frequencies in sequence; DSSS spreads the signal across a band using a chipping code (can recover from some interference); OFDM transmits on many perpendicular (orthogonal) subcarriers at once — the highest throughput with the least interference, and the basis of modern Wi-Fi and LTE.", "ext",
     "“Greatest throughput, least interference” = OFDM — orthogonal subcarriers don't interfere with each other. Watch for OSPF in the options: a routing protocol planted among radio methods."),
    ("network", "Multicast", "Casting Methods & IGMP",
     "How traffic is addressed: unicast (one-to-one), multicast (one-to-many SPECIFIC registered recipients), broadcast (one-to-everyone on the segment) and anycast (to the nearest of several identical endpoints). IGMP manages a host's multicast group membership — which is why IGMP and content-caching protocols like TFTP can both show up in a multicast delivery chain.", "ext",
     "Multicast = many SPECIFIC recipients, managed by IGMP. Broadcast has no membership; simplex/duplex describe direction, not addressing."),
    ("network", "TCP Wrapper", "TCP Wrapper",
     "A host-based application that acts as a basic firewall for network services by restricting access based on user IDs or system IDs (classically via hosts.allow/hosts.deny on Unix inetd services). A hardening step on individual servers, not a network device.", "ext",
     "Basic firewall BY ID restriction on a host = TCP Wrapper. The distractors have homes: 802.1Q = switch encapsulation (VLAN tagging), IPsec = protecting traffic over WAN links, L2TP = tunneling through non-IP networks."),
    ("network", "SRTP", "Secure Real-time Transport Protocol",
     "Encryption, message authentication and replay protection for RTP — the protocol that actually carries VoIP and video streams. The answer to VoIP eavesdropping: plain RTP is cleartext on the wire. Note endpoints can still record a call that SRTP protected in transit.", "core",
     "VoIP call intercepted mid-stream = deploy SRTP. DISA secures PBX dial-in (not VoIP); DMARC is email authentication; adding collaboration features secures nothing."),
    ("network", "MUX", "Multiplexer",
     "A device that combines multiple input signals into a single output signal for transmission over one shared medium (by time slots, frequencies or wavelengths), with a demultiplexer separating them at the far end. The answer when many separate, protocol-diverse links must ride one new backbone.", "ext",
     "“Combine multiple input signals into a single output over a shared medium” is the MUX definition verbatim. SDN separates control from forwarding, IaC manages infrastructure as code — neither combines signals."),
    ("network", "LEO", "Satellite Internet Orbits: LEO, MEO, GEO",
     "Orbit choice drives latency and speed: LEO (low Earth orbit) constellations offer high speed and minimal latency — the pick for connectivity in uninhabited regions; MEO is where navigation constellations like GPS live; GEO satellites sit fixed over one spot but the ~36,000 km distance means high latency and lower throughput.", "ext",
     "Remote area + “high speed, minimal latency” = LEO. GEO's giveaway is the opposite pairing: fixed dish, high latency. Wi-Fi and cellular are absent where there's no infrastructure at all."),
    ("network", "DMARC", "Domain-based Message Authentication, Reporting and Conformance",
     "DNS-published email policy telling receiving servers what to do with messages that fail SPF or DKIM alignment for your domain (none/quarantine/reject) and where to send aggregate reports. The anti-spoofing capstone on top of SPF (authorized senders) and DKIM (signed messages).", "ext",
     "The email-auth trio: SPF says WHO may send, DKIM SIGNS the message, DMARC says what to DO on failure and reports. DMARC is email only — it secures no other protocol."),
    ("network", "Ports", "Standard & Well-Known Ports",
     "The default TCP/UDP ports of common services — tested constantly, usually as “which ports must the firewall open?”. Three ranges: well-known 0–1023, registered 1024–49151, dynamic/ephemeral 49152–65535. The full reference table is under “In depth” below.", "core",
     "The AAA pair is the classic trap: TACACS+ = TCP 49, RADIUS = UDP 1812 (1813 accounting) — each rides the transport most people guess for the other. Second favourite: SNMP polls on 161, traps arrive on 162."),
    ("network", "SAE", "Simultaneous Authentication of Equals (WPA3)",
     "WPA3's replacement for the preshared-key four-way handshake: a password-authenticated key exchange (the “dragonfly” handshake) that resists offline dictionary attacks and gives forward secrecy. Technologies DEFINED within 802.11 wireless networking: WPA3, SAE, 802.11i (the WPA2 security amendment) and WPS. 802.1X is an IEEE PORT-authentication standard used on wired and wireless networks alike — it underpins ENT/enterprise mode but is not itself an 802.11 technology.", "ext",
     "“Specifically part of 802.11” includes WPA3/SAE/802.11i/WPS — and excludes 802.1X, which is generic port-based authentication. SAE = WPA3's handshake upgrade over PSK."),
    ("network", "Duplex", "Media Control Modes: Simplex / Half-Duplex / Full-Duplex",
     "The THREE media management or control modes on transmission media: simplex (one direction only), half-duplex (two directions, one at a time) and full-duplex (both directions simultaneously). Multiplexing is a different idea — combining several signals onto one medium — and 802.1X is port authentication; neither is a control mode.", "ext",
     "The trio is simplex / half-duplex / full-duplex. When the list offers 802.1X or multiplexing as a fourth “mode”, strike them: one is authentication, the other is signal combining (see MUX)."),
    ("network", "VXLAN", "Virtual Extensible LAN",
     "An ENCAPSULATION protocol that lets switch-created network segments (VLANs) be stretched across subnets and geographic distances — satellite offices can sit on the same logical segment as headquarters. Distinguish the neighbours: SDN is centrally programmable network design, SD-WAN manages connectivity between distant sites over WAN links, and a VPN is a secured tunnel between networks.", "ext",
     "“Encapsulation + stretch VLAN segments across subnets/distance” = VXLAN. SD-WAN manages WAN connectivity; it doesn't extend Layer-2 segments. VLAN alone stops at the local switch fabric."),
    ("network", "DNS poisoning", "DNS Cache Poisoning & Diagnosis",
     "Corrupting name resolution so a correct FQDN returns an attacker's IP. The tested skill is DIAGNOSIS by elimination: flush the local cache (ipconfig /flushdns) — if the bad answer returns, the client cache wasn't the problem; a modified hosts file SURVIVES a flush and would reappear in the display, so an empty cache rules it out; a colleague elsewhere resolving correctly clears the authoritative zone file; correct DNS-server settings clear DHCP falsification. What remains: the LOCAL CACHING DNS SERVER is poisoned.", "ext",
     "Hosts-file entries are boot-persistent and visible in /displaydns even after a flush — if the flushed cache is clean, the hosts file is innocent. Remote user fine = authoritative server fine. What's left between you and the internet is your resolver."),
    ("network", "SDN", "Software Defined Networking",
     "Network architecture separating centralized software-based control from packet forwarding.", "ext",
     "Control plane and data plane are split — the controller is the crown jewel to protect. Access control inside SDNs is commonly ABAC (attribute-based)."),
    ("network", "EAP", "Extensible Authentication Protocol",
     "Authentication FRAMEWORK (one of PPP's three options, alongside PAP and CHAP) that supports 40+ pluggable methods rather than one fixed mechanism.", "core",
     "Real methods include LEAP, PEAP, EAP-TLS, EAP-TTLS, EAP-FAST, EAP-SIM, EAP-MD5, EAP-POTP. Invented names like “EAP-VPN” are standard distractors."),
    ("network", "PAP", "Password Authentication Protocol",
     "PPP authentication that transmits usernames and passwords in cleartext — no encryption or protection of logon credentials at all.", "core",
     "“No protection for credentials” = PAP, full stop. RADIUS is a AAA service, not the naked protocol."),
    ("network", "CHAP", "Challenge Handshake Authentication Protocol",
     "PPP authentication where the password never crosses the wire: the client answers a random server challenge with a hash computed from it.", "core",
     "PAP = plaintext, CHAP = challenge/response, EAP = extensible framework — the three PPP options in one line."),
    ("network", "RFC 1918", "Private IPv4 Address Ranges",
     "The three private, non-routable IPv4 blocks: 10.0.0.0/8, 172.16.0.0/12 (through 172.31.255.255), and 192.168.0.0/16.", "core",
     "The 172.16–172.31 boundary is the tested detail. 169.254.x.x is APIPA link-local — NOT an RFC 1918 range."),
    ("network", "APIPA", "Automatic Private IP Addressing",
     "Self-assigned 169.254.0.0/16 link-local address a host takes when no DHCP server responds.", "ext",
     "A 169.254 address on a client means “DHCP failed” — and it is not part of RFC 1918."),
    ("network", "PVC", "Permanent Virtual Circuit",
     "A logical circuit that always exists and waits for the customer to send data — versus an SVC (switched virtual circuit), built per session and torn down afterwards.", "ext",
     "“Always exists, waiting for data” = PVC; “created each time it's needed” = SVC. Think dedicated leased line vs dial-up, virtualized."),
    ("network", "NTP", "Network Time Protocol",
     "Synchronizes system clocks across a network — a dependency for Kerberos authentication and for correlating logs during investigations.", "ext",
     "Mysterious Kerberos logon failures on some hosts = check clock drift first (tolerance is about five minutes)."),
    ("network", "TLS", "Transport Layer Security",
     "Cryptographic protocol protecting data in transit.", "core", None),
    ("network", "SSL", "Secure Sockets Layer",
     "Older predecessor to TLS; obsolete versions should not be treated as secure.", "core",
     "If an answer offers SSL as the \u201csecure\u201d choice, be suspicious — TLS replaced it."),
    ("network", "SSH", "Secure Shell",
     "Secure protocol for remote system administration and related functions (secure file transfer, tunnelling); default port TCP 22.", "core",
     "Port 22 is the tested default — and the secure replacement for telnet (23), rlogin and FTP's credentials-in-the-clear."),
    ("network", "DNS", "Domain Name System",
     "Resolves human-readable domain names to network information such as IP addresses.", "core", None),
    ("network", "DNSSEC", "Domain Name System Security Extensions",
     "Adds origin authentication and integrity protection to DNS data.", "ext",
     "DNSSEC signs DNS data — it proves authenticity, not confidentiality."),
    ("network", "DHCP", "Dynamic Host Configuration Protocol",
     "Automatically supplies network configuration to clients.", "ext", None),
    ("network", "SNMP", "Simple Network Management Protocol",
     "Protocol for monitoring and managing network devices.", "ext",
     "Only SNMPv3 adds real security (authentication and encryption)."),
    ("network", "NGFW", "Next-Generation Firewall",
     "Firewall integrating traditional filtering with application awareness, IPS, TLS inspection and other services in one device — often described as unified threat management (UTM).", "ext",
     "“UTM” in a stem points at NGFW. It guards the network path; EDR guards the endpoint."),
    ("network", "ISFW", "Internal Segmentation Firewall",
     "Firewall deployed INSIDE the network to filter traffic between internal zones — the enforcement device behind segmentation and microsegmentation.", "ext",
     "Perimeter firewalls face the internet; ISFWs face east-west traffic between internal zones (even down to a single high-value host)."),
    ("network", "DMZ", "Demilitarized Zone (Screened Subnet)",
     "Buffer zone positioned between the private network and the internet that hosts publicly accessible services without exposing the internal LAN.", "core",
     "Screened subnet = DMZ. The intranet is the private network itself, an extranet serves selected partners only, and a honeypot is a trap — none of them buffer public services."),
    ("network", "CDN", "Content Delivery Network",
     "Geographically distributed service hosts that replicate and serve content close to users for low latency, high performance and high availability.", "ext",
     "“Replicas in many data centers worldwide” = CDN — not VPN (tunnels), SDN (control-plane separation) or CCMP (wireless encryption)."),
    ("network", "CCMP", "Counter Mode with CBC-MAC Protocol",
     "The AES-based encryption protocol of WPA2 — counter-mode encryption plus CBC-MAC integrity — replacing WEP and TKIP's weaknesses.", "ext",
     "Wireless lineage in order: WEP → TKIP (WPA) → CCMP/AES (WPA2) → SAE handshake (WPA3)."),
    ("network", "Zigbee", "Zigbee (IEEE 802.15.4)",
     "Low-power, short-range IoT communications protocol for sensors and hubs, encrypted with a 128-bit symmetric key.", "ext",
     "Tells: IoT sensor, metres of range, low power, encryption built in — where plain Bluetooth would be unencrypted."),
    ("network", "ARP", "Address Resolution Protocol",
     "Resolves IP addresses to MAC addresses on a LAN. ARP poisoning corrupts those mappings — often via unsolicited (gratuitous) replies — to redirect or intercept traffic.", "core",
     "Three different layer-2 attacks: ARP poisoning falsifies IP→MAC mappings; MAC spoofing falsifies a device's own hardware address; MAC flooding overloads a switch's CAM table."),
    ("network", "MAC spoofing", "MAC Address Spoofing",
     "Falsifying a device's hardware (MAC) address to impersonate an authorized device — e.g. to bypass port security or MAC filtering.", "ext",
     "Spoofing impersonates, flooding overloads switch memory, ARP poisoning corrupts neighbours' mappings."),
    ("network", "QoS", "Quality of Service",
     "Mechanisms for managing network performance and traffic priority.", "ext", None),
    # ---- Identity & Access Management --------------------------------------
    ("iam", "IAM", "Identity and Access Management",
     "Processes and technologies controlling identities and their access to resources.", "core", None),
    ("iam", "AAA", "Authentication, Authorization and Accounting",
     "Determines who a subject is, what it may do, and records relevant activity.", "core", None),
    ("iam", "MFA", "Multi-Factor Authentication",
     "Authentication requiring factors from more than one factor category.", "core",
     "Two passwords is not MFA — factors must come from different categories."),
    ("iam", "SSO", "Single Sign-On",
     "Allows one authentication event to provide access to multiple related systems.", "core", None),
    ("iam", "FIM", "Federated Identity Management",
     "Trust arrangement allowing identities to be recognized across security domains — users sign in with their EXISTING (normal) account credentials.", "ext",
     "In federation questions, the login ID stays the user's normal account; SSO is the resulting capability, not a kind of account."),
    ("iam", "Kerberos", "Kerberos Authentication Protocol",
     "Ticket-based network authentication: a Key Distribution Center issues ticket-granting tickets and service tickets, using AES symmetric cryptography.", "core",
     "Two exam hooks: clocks must agree within ~5 minutes (drift = logon failures, fix with NTP), and compromising the KRBTGT account lets attackers forge golden tickets."),
    ("iam", "PtH", "Pass the Hash",
     "Reusing a captured NTLM credential hash to authenticate to remote systems without ever knowing the password.", "ext",
     "Match attack to system: pass the hash = NTLM; pass the ticket and golden ticket = Kerberos; rainbow tables = offline password cracking."),
    ("iam", "RBAC", "Role-Based Access Control",
     "Assigns permissions according to organizational roles.", "core",
     "Roles decide (RBAC); attributes and context decide (ABAC)."),
    ("iam", "ABAC", "Attribute-Based Access Control",
     "Makes authorization decisions using attributes of users, resources and context.", "core", None),
    ("iam", "MAC", "Mandatory Access Control",
     "Centrally enforced access decisions based on classifications and labels. Supports three environment types: hierarchical, compartmentalized, and hybrid.", "core",
     "Context matters: MAC can also mean Media Access Control or Message Authentication Code on the exam."),
    ("iam", "DAC", "Discretionary Access Control",
     "Allows resource owners to decide who receives access.", "core",
     "Owner decides = DAC; labels and clearances decide = MAC."),
    ("iam", "PAM", "Privileged Access Management",
     "Controls and monitors highly privileged accounts and credentials.", "core", None),
    ("iam", "JIT", "Just-In-Time Access & Provisioning",
     "Two exam uses of JIT: just-in-time ACCESS grants elevated rights temporarily, only when required (the PAM angle); just-in-time PROVISIONING creates a federated user's account automatically the FIRST time they access a partner site — the minimal-administration answer when account management is outsourced. Exporting account databases, duplicating accounts or building a trust all cost far more admin effort (and a trust alone grants no accounts).", "ext",
     "“Outsourced service, minimize administrative workload” = JIT provisioning: the account creates itself on first access. Database transfers and internal duplication are the labour-heavy distractors."),
    ("iam", "IAAA", "Identification, Authentication, Authorization, Auditing, Accountability",
     "The five access-control elements in order: identification (claiming an identity), authentication (proving it), authorization (what the identity may do), auditing (recording activity into logs and audit trails) and ACCOUNTABILITY (holding users responsible by REVIEWING those logs and tracking activity back to a person). Reviewing server logs for malicious activity serves accountability — the audit trail is the DATA that review uses, not the purpose.", "core",
     "Auditing RECORDS; accountability REVIEWS and holds responsible. When the stem asks the PURPOSE of examining logs, answer accountability — “audit trails” is the bait, but it names the evidence, not the goal."),
    ("iam", "Cloud IdM", "Identity Management Deployment Models",
     "Where identity services live: ON-PREMISES identity management serves users of a single organization inside its own infrastructure; CLOUD-BASED identity management (IDaaS) serves users from MULTIPLE organizations logging into a shared service without re-authenticating; HYBRID combines both. Credential management is merely secure STORAGE of credentials — it is not an identity-management deployment model.", "ext",
     "“Employees of multiple organizations log on once and reach the service” = cloud-based identity management. One org, own servers = on-premises. “Credential management” answers a storage question, not a deployment question."),
    ("iam", "LDAP", "Lightweight Directory Access Protocol",
     "Protocol used to access and manage directory services.", "core", None),
    ("iam", "SAML", "Security Assertion Markup Language",
     "XML-based standard commonly used for federated identity and browser-based enterprise SSO.", "core",
     "SAML = enterprise federation and browser SSO."),
    ("iam", "OAuth", "Open Authorization",
     "Framework for delegated authorization allowing applications limited access to resources without sharing a user's password.", "core",
     "OAuth = authorization (what an app may do), not authentication."),
    ("iam", "OIDC", "OpenID Connect",
     "Identity and authentication layer built on OAuth 2.0, carrying identity claims in JSON Web Tokens (JWTs).", "core",
     "Token format is a tell: JSON Web Tokens = OIDC; XML assertions = SAML. OIDC adds the \u201cwho are you?\u201d answer on top of OAuth."),
    ("iam", "SCIM", "System for Cross-domain Identity Management",
     "Standard for automating identity provisioning and deprovisioning.", "ext", None),
    ("iam", "RADIUS", "Remote Authentication Dial-In User Service",
     "AAA protocol widely used for network-access authentication.", "core",
     "RADIUS for network access; TACACS+ (separate AAA, fully encrypted payload) for device administration."),
    ("iam", "TACACS+", "Terminal Access Controller Access-Control System Plus",
     "AAA protocol frequently used for administrative access to network equipment.", "core", None),
    ("iam", "KBA", "Knowledge-Based Authentication",
     "Identity proofing that asks questions drawn from AUTHORITATIVE RECORDS of the person's history — past addresses, loan payment amounts, vehicles owned — typically during account creation at a bank or credit bureau. Distinguish the lookalikes: a cognitive password asks questions the user previously ANSWERED themselves (favourite colour); registration is the internal enrollment process (often collecting biometrics); two-factor authentication combines two factor TYPES.", "ext",
     "Questions from records the user never supplied = KBA. Questions the user pre-answered = cognitive password. If the stem says “past addresses and current payment amounts”, the data came from a credit file — that's KBA."),
    ("iam", "Rule-BAC", "Rule-Based Access Control",
     "Access control driven by a set of GLOBAL, administrator-defined rules applied to every subject alike — the model a firewall's filter/ACL set implements. Contrast: role-based grants by group/role membership, MAC decides from classification labels, ABAC evaluates attributes and context.", "core",
     "Firewall filters = RULE-based access control, every time. MAC is the tempting wrong answer, but MAC means labels and clearances — a firewall rule set has neither."),
    # ---- Security Assessment & Testing -------------------------------------
    ("assess", "VA", "Vulnerability Assessment",
     "Process of identifying and evaluating security weaknesses.", "core",
     "VA finds weaknesses; a penetration test exploits them to show impact."),
    ("assess", "PT", "Penetration Test",
     "Authorized attempt to exploit vulnerabilities to demonstrate practical impact.", "core", None),
    ("assess", "CVE", "Common Vulnerabilities and Exposures",
     "Standard identifier assigned to publicly disclosed vulnerabilities.", "core", None),
    ("assess", "CVSS", "Common Vulnerability Scoring System",
     "Framework for expressing vulnerability severity.", "core", None),
    ("assess", "CWE", "Common Weakness Enumeration",
     "Catalog of common software and hardware weakness types.", "ext",
     "CVE names a specific vulnerability; CWE names the general weakness type behind it."),
    ("assess", "SAST", "Static Application Security Testing",
     "Analyzes source or compiled code without executing the application.", "core",
     "Static = code at rest. White-box, early in the pipeline."),
    ("assess", "DAST", "Dynamic Application Security Testing",
     "Tests a running application externally.", "core",
     "Dynamic = attack the running app from outside. Black-box."),
    ("assess", "IAST", "Interactive Application Security Testing",
     "Analyzes application behavior from within, via instrumentation, while the application executes.", "ext", None),
    ("assess", "SCA", "Software Composition Analysis",
     "Identifies third-party and open-source components and associated vulnerabilities or licensing concerns.", "ext",
     "SCA inspects your dependencies, not your own code."),
    ("assess", "RASP", "Runtime Application Self-Protection",
     "Application-integrated protection operating while software runs.", "ext", None),
    ("assess", "Nmap", "Network Mapper",
     "The standard network discovery tool: finds live hosts, open ports and service versions — the reconnaissance step BEFORE vulnerability scanning.", "ext",
     "Tool roles in one line: Nmap discovers, Nessus finds vulnerabilities, Metasploit exploits them, Wireshark captures traffic, lsof lists open files."),
    ("assess", "SOC reports", "System and Organization Controls Reports (SOC 1/2/3)",
     "Third-party attestation reports (issued under SSAE-18) about a service organization's controls — SOC 1 for financial reporting, SOC 2 for security, SOC 3 for public consumption. Formerly “Service Organization Control”; the AICPA renamed the suite in 2017.", "core",
     "SOC 1 = customers' FINANCIAL auditors; SOC 2 = security due diligence (Trust Services Criteria, NDA-restricted); SOC 3 = public summary. Type I = design at a point in time; Type II = operating effectiveness over a period."),
    ("assess", "SBOM", "Software Bill of Materials",
     "Structured inventory of components contained in a software product.", "ext", None),
    ("assess", "800-53", "NIST SP 800-53 Family (-53, -53A, -171, -171A)",
     "Four documents that differ by one suffix: SP 800-53 is the CATALOG of security and privacy controls for federal systems; SP 800-53A is the guide for ASSESSING those controls; SP 800-171 moves the requirements to CUI (controlled unclassified information) on NONFEDERAL systems; SP 800-171A assesses those. The suffix pattern is the whole question.", "ext",
     "A = Assess. Federal system + “determine whether controls are appropriate” = 800-53A; contractor holding CUI = 800-171 (assessed with 800-171A)."),
    ("assess", "Fagan", "Fagan Inspection",
     "The most formal code-review process: SIX defined steps — planning, overview, preparation, inspection, rework, follow-up — with defined roles and entry/exit criteria. Everything less formal (over-the-shoulder, pair programming, tool-assisted review) is just “code review”.", "ext",
     "“Rigorous / formal six-step review” = Fagan. The six steps in order are the test: Planning, Overview, Preparation, Inspection, Rework, Follow-up."),
    ("assess", "BAS", "Breach and Attack Simulation",
     "A platform that CONTINUOUSLY injects benign threat indicators and simulated attack behaviors into systems and networks to verify that security controls (IPS, EDR, SIEM rules) actually detect and respond — automated, ongoing purple-teaming. A penetration test gives the same assurance only as a point-in-time snapshot.", "ext",
     "“Verify the IPS/controls fire, on an ongoing basis” = BAS. The IDS/IPS is the control being tested, the SIEM is where alerts land, and a pentest is periodic — only BAS is continuous verification."),
    ("assess", "Misuse case", "Misuse Case Testing",
     "Software testing that starts by ENUMERATING the known ways an attacker might abuse or exploit the application, then works through each scenario with manual or automated attack techniques to see whether the application is vulnerable. Its neighbours on the exam: synthetic transactions (scripted benign transactions to verify behaviour/performance), test coverage analysis (how much of the code the tests exercise) and Fagan inspection (formal six-step code REVIEW — no execution at all).", "ext",
     "“List the ways an attacker might exploit it, then test each” = misuse case testing. Fagan reads code in a meeting, synthetic transactions are benign scripts, coverage analysis just measures — only misuse cases attack."),
    ("assess", "Synthetic transactions", "Synthetic Transactions",
     "Application testing that runs SCRIPTS of routine activity with KNOWN expected results, then compares actual outcomes against them — a dynamic technique used for verification and performance monitoring. Its neighbours: fuzzing throws invalid/random input (no expected-results script), mutation testing alters the code itself, static testing never executes anything, and misuse case testing scripts ATTACKS rather than routine activity.", "ext",
     "“Scripts of routine activity + compare against known results” = synthetic transactions. Fuzzing is the classic wrong answer — it also executes input, but random garbage, with no scripted expectations."),
    ("assess", "PoR", "Proof of Reserves",
     "A cryptographic attestation by a custodian — typically a crypto exchange — that the assets it holds cover customer balances 1:1. Customer balances are sealed into a Merkle tree, ownership of the on-chain wallets is demonstrated, and a zero-knowledge proof shows every account was counted without revealing any of them; each customer can verify their own leaf was included.", "ext",
     "It is an attestation, not an audit: it proves assets ≥ recorded liabilities at one snapshot, and cannot prove hidden liabilities don't exist. Same point-in-time vs period logic as SOC Type I vs Type II."),
    # ---- Security Operations ------------------------------------------------
    ("ops", "SOC", "Security Operations Center",
     "The team and facility that monitors, detects and responds to security events around the clock.", "core",
     "Collision alert: on the exam SOC can also mean Service Organization Control (audit reports) — context decides. A building full of analysts = this SOC; an auditor's attestation = SOC 1/2/3."),
    ("ops", "DoS", "Denial of Service Attacks",
     "Attacks on availability. The classic trio each abuses a different protocol: SYN flood (TCP), Smurf (ICMP amplification), Fraggle (UDP — Smurf's sibling).", "core",
     "The protocol IS the answer: Fraggle = UDP, Smurf = ICMP, SYN flood = TCP. Mnemonic: Fraggle and UDP both sound playful; Smurfs are blue like ICMP ping."),
    ("ops", "SIEM", "Security Information and Event Management",
     "Aggregates and correlates logs and security events for monitoring and investigation.", "core",
     "SIEM gives visibility; SOAR automates the response on top of it."),
    ("ops", "SOAR", "Security Orchestration, Automation and Response",
     "Automates and coordinates security-analysis and response workflows.", "ext", None),
    ("ops", "UEBA", "User and Entity Behavior Analytics",
     "Uses behavior patterns to detect anomalous or risky activity involving users and other entities.", "ext", None),
    ("ops", "EDR", "Endpoint Detection and Response",
     "Endpoint-focused monitoring, detection, investigation and response — the evolution of traditional antivirus, often reporting events to a central or cloud ML analysis engine.", "core",
     "Scenario tells: “evolution of antivirus”, “beyond AV/HIDS”, central ML analysis, endpoint focus. NGFW is a network device, WAF filters web traffic, and XSRF is an attack, not a control. (EDR = endpoints; NDR = network; XDR = correlated across layers.)"),
    ("ops", "XDR", "Extended Detection and Response",
     "Correlates security telemetry and response across multiple security layers.", "ext", None),
    ("ops", "NDR", "Network Detection and Response",
     "Detection and investigation based primarily on network telemetry.", "ext", None),
    ("ops", "IOC", "Indicator of Compromise",
     "Observable artifact or behavior suggesting possible compromise.", "core",
     "IOC = the artifact left behind; TTP = the adversary's behavior pattern."),
    ("ops", "TTP", "Tactics, Techniques and Procedures",
     "Patterns describing how adversaries pursue goals and conduct attacks.", "core", None),
    ("ops", "IR", "Incident Response",
     "Structured process for managing cybersecurity incidents.", "core",
     "Know the lifecycle IN ORDER: Detection/Analysis → Containment → Eradication → Recovery → Lessons Learned."),
    ("ops", "CSIRT", "Computer Security Incident Response Team",
     "Team responsible for coordinating response to cybersecurity incidents.", "core", None),
    ("ops", "HA", "High Availability",
     "Architecture intended to minimize service outages and increase resilience.", "ext", None),
    ("ops", "PAW", "Privileged Access Workstation",
     "A hardened, dedicated workstation used only for privileged operations — no email, browsing or productivity apps — so administrative credentials and signing operations never touch a general-purpose, phishable device. Usually paired with jump hosts and just-in-time elevation so compromise of a daily-driver endpoint cannot reach production controls.", "ext",
     "The 2026 Binance breach reportedly began on a compromised engineer's device with a path to withdrawal-signing systems — the exact scenario PAWs plus jump-host separation exist to prevent."),
    # ---- Software & Cloud Security ------------------------------------------
    ("cloud", "OOP", "Object-Oriented Programming Vocabulary",
     "The exam's OOP taxonomy, frozen in textbook form: a CLASS is a collection of the common methods from a set of objects that defines the behavior of those objects; an OBJECT is an instance of a class; a MESSAGE invokes a METHOD, and the result the object exhibits is its BEHAVIOR. Polymorphism is a property (one message, different behaviors by receiver), never a container of methods. The full vocabulary table is under “In depth”.", "core",
     "Developers lose points here by answering from their codebase: a class is NOT an object (blueprint vs building), and an interface is a contract WITHOUT behavior — when the stem says “defines the behavior”, the answer is class."),
    ("cloud", "Polyinstantiation", "Polyinstantiation",
     "A multilevel database security technique: the same primary key deliberately exists as multiple rows at different classification levels, so a lower-cleared user sees an unclassified cover story instead of an error or a gap. It defeats inference attacks — an empty or locked row would itself reveal that something classified exists.", "ext",
     "Same key, different rows by clearance = polyinstantiation. It only SOUNDS like polymorphism; one is database inference defence, the other is OOP message dispatch."),
    ("cloud", "IDEAL", "IDEAL Model",
     "CMU/SEI's software process improvement model, five phases spelling the name: Initiating, Diagnosing, Establishing, ACTING (develop, test, refine and implement the solutions) and Learning. A sibling of SW-CMM from the same stable.", "ext",
     "The name is the mnemonic. The tested phase is ACTING = “develop, test, refine, implement” — stop talking, start walking. Learning comes last, Initiating lays groundwork."),
    ("cloud", "IPT", "Integrated Product Team",
     "Multifunctional groups — developers, stakeholders, users — collaborating so decisions in software development are made in PARALLEL rather than sequentially. First introduced by the US Department of Defense in 1995. Agile and DevOps foster the same collaboration but arrived years later, first in the private sector — the DoD-in-the-1990s framing is the IPT fingerprint.", "ext",
     "“DoD, 1990s, multifunctional teams, parallel decisions” = IPTs. Agile (2001 manifesto) and DevOps (late 2000s) are the anachronistic distractors; COTS is just commercial off-the-shelf software."),
    ("cloud", "SAMM", "Software Assurance Maturity Model (OWASP SAMM)",
     "OWASP's maturity model for secure software, organized into FIVE business functions (listed under “In depth”): Governance, Design, Implementation, Verification and Operations. The tested trap: security training and awareness programmes for developers belong to GOVERNANCE (education & guidance), not Operations.", "ext",
     "Five functions: Governance, Design, Implementation, Verification, Operations. Training/awareness/culture = Governance — people guess Operations and lose the mark."),
    ("cloud", "SDLC", "Software Development Life Cycle",
     "Processes through which software is planned, designed, built, tested, operated and retired.", "core",
     "Phases in order: requirements → design → implementation → testing → deployment/operations → retirement."),
    ("cloud", "SW-CMM", "Software Capability Maturity Model",
     "Five-level software-process maturity model: 1 Initial → 2 Repeatable → 3 Defined → 4 Managed (quantitatively measured) → 5 Optimizing.", "ext",
     "Know the five levels in order; the trap is Defined (documented org-wide) vs Managed (measured)."),
    ("cloud", "XSRF", "Cross-Site Request Forgery (CSRF)",
     "Web attack that tricks an authenticated user's browser into sending unwanted, legitimate-looking requests to a site where the victim is already logged in.", "ext",
     "Also written CSRF. It is an ATTACK — when a question asks you to pick a defensive control, XSRF is always the distractor."),
    ("cloud", "SSDLC", "Secure Software Development Life Cycle",
     "SDLC in which security activities and controls are intentionally integrated.", "core",
     "Security built in, not bolted on — the recurring exam theme."),
    ("cloud", "CI/CD", "Continuous Integration / Continuous Delivery (Deployment)",
     "Automated practices for integrating, testing and releasing software.", "core", None),
    ("cloud", "API", "Application Programming Interface",
     "Defined interface enabling software systems to communicate.", "ext", None),
    ("cloud", "COTS", "Commercial Off-The-Shelf",
     "Commercially produced software acquired rather than custom developed.", "ext", None),
    ("cloud", "IaaS", "Infrastructure as a Service",
     "Cloud model providing computing infrastructure while customers manage the higher software layers.", "core",
     "Responsibility shifts to the provider as you move IaaS \u2192 PaaS \u2192 SaaS."),
    ("cloud", "PaaS", "Platform as a Service",
     "Cloud model providing infrastructure plus a managed application platform and runtime.", "core", None),
    ("cloud", "SaaS", "Software as a Service",
     "Cloud model delivering a complete managed application.", "core", None),
    ("cloud", "CSP", "Cloud Service Provider",
     "Organization providing cloud computing services.", "ext", None),
    ("cloud", "OWASP", "Open Worldwide Application Security Project",
     "Nonprofit community producing widely used application-security guidance and tools.", "core", None),
]

# "Remember This" cards, placed inside their most relevant category section.
REMEMBER = {
    "crypto": ("Encryption", ["AES = symmetric = fast bulk encryption",
                              "RSA / ECC = asymmetric = keys, signatures, public-key use",
                              "SHA = hashing = integrity"]),
    "iam": ("Federation", ["OAuth = authorization",
                           "OIDC = authentication / identity on OAuth",
                           "SAML = enterprise federation / browser SSO"]),
    "network": ("Network vs. Data", ["NAC = can the device enter?",
                                     "DLP = can the data leave?"]),
    "assess": ("Application testing", ["SAST = analyze code without executing it",
                                       "DAST = attack / test the running application",
                                       "SCA = inspect dependencies and components",
                                       "IAST = analyze from inside while the app executes"]),
    "risk": ("Recovery & quantitative risk", ["RTO = how long can the service be unavailable?",
                                              "RPO = how much data can be lost?",
                                              "SLE = Asset Value \u00d7 Exposure Factor",
                                              "ALE = SLE \u00d7 ARO"]),
}

IR_CALLOUT = ["Detection / Analysis", "Containment", "Eradication", "Recovery", "Lessons Learned"]

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

  // Deep links from the mind map (…#t-<id>): clear filters so the target is
  // visible, scroll to it, and flash a highlight.
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
    void el.offsetWidth; // restart the highlight animation on repeat hits
    el.classList.add("gl-hit");
  }
  window.addEventListener("hashchange", jumpToHash);
  jumpToHash();
})();
</script>
"""


# Optional "In depth" expansions for step/level/layer-based terms — the exam
# loves asking about the phases, so these enumerate them. Rendered as a native
# <details> block in the glossary (no JS required) and after the answer in
# flashcards; exported to the shared JSON as `detail`.
# Per-term reference tables, rendered inside the "In depth" <details> block
# after the step list and exported to the shared JSON as `table`.
# {acr: {"caption", "headers": [...], "rows": [[cell, ...], ...]}}
TABLES = {
    "Cipher modes": {
        "caption": ("Block cipher modes — the exam tests chaining (blocks the mode from parallelizing) "
                    "and authentication. “Parallelized environment” = counter family, best = GCM."),
        "headers": ["Mode", "Parallel?", "Authenticated?", "Exam hook"],
        "rows": [
            ["ECB — Electronic Codebook", "Yes", "No", "Identical plaintext blocks → identical ciphertext; parallelizes but never the right answer"],
            ["CBC — Cipher Block Chaining", "No (chains)", "No", "Each block XORed with previous ciphertext — chaining kills parallel encryption; errors propagate"],
            ["CFB — Cipher Feedback", "No (chains)", "No", "Streaming version of CBC — same chaining, same limits"],
            ["OFB — Output Feedback", "No", "No", "Keystream generated from the IV, independent of ciphertext — no error propagation"],
            ["CTR — Counter", "Yes", "No", "Counter per block = fully independent steps; parallel encrypt AND decrypt"],
            ["GCM — Galois/Counter", "Yes", "Yes (tag)", "CTR plus a Galois authentication tag (AEAD) — the “parallelized environment” answer"],
            ["CCM — Counter with CBC-MAC", "Partly", "Yes", "AEAD built from CTR + CBC-MAC; used in WPA2; 128-bit-block ciphers only"],
        ],
    },
    "Extinguishers": {
        "caption": ("Fire classes, what burns, and the media allowed — the question is usually "
                    "“all EXCEPT which medium”, so know the exclusions as well as the lists."),
        "headers": ["Class", "What's burning", "Suppression media", "Never use"],
        "rows": [
            ["A", "Common combustibles (wood, paper, cloth)", "Water, soda acid", "—"],
            ["B", "Flammable liquids (grease, oil, solvents)", "CO2, halon or substitute, soda acid", "Water — it spreads burning liquid"],
            ["C", "Energized electrical equipment", "CO2, halon or substitute (non-conductive)", "Water and any conductive medium"],
            ["D", "Combustible metals (magnesium, sodium)", "Dry powder", "Water, CO2"],
            ["K", "Commercial kitchen oils and fats", "Wet chemical (saponification)", "Water"],
        ],
    },
    "OOP": {
        "caption": ("The exam's object-oriented vocabulary — definition-recall questions quote "
                    "these near-verbatim, so match the dictionary, not your codebase."),
        "headers": ["Term", "Exam definition", "Developer-brain trap"],
        "rows": [
            ["Class", "Collection of the common methods from a set of objects that defines the behavior of those objects", "A class is NOT an object — blueprint vs building (even if your language makes classes objects at runtime)"],
            ["Object", "An instance of a class", "—"],
            ["Instance", "An object created (instantiated) from a class", "—"],
            ["Method", "Internal code that defines an object's actions in response to a message", "—"],
            ["Message", "A communication sent to an object to invoke a method", "“Method call” in modern speech"],
            ["Behavior", "The results or output an object exhibits in response to a message", "The thing a CLASS defines — the hook in the classic question"],
            ["Polymorphism", "The same message produces different behaviors depending on the receiving object", "A property, never a collection of methods"],
            ["Inheritance", "A subclass receives the methods of the class above it", "—"],
            ["Delegation", "An object forwards a request to another object", "—"],
            ["Cohesion", "How strongly a module's internal purposes relate — HIGH is good", "Pairs with coupling; the good answer is high cohesion + low coupling"],
            ["Coupling", "How much a module depends on other modules — LOW is good", "—"],
            ["Polyinstantiation", "Same database key, different rows per clearance level (inference defence)", "Not OOP at all — it just rhymes with polymorphism"],
        ],
    },
    "Ports": {
        "caption": ("The default ports the exam expects, in port order. Where a cleartext "
                    "service has a TLS-protected sibling, it is listed in the last column — "
                    "“which is the SECURE variant” is its own question style."),
        "headers": ["Port", "Transport", "Service", "Notes / secure variant"],
        "rows": [
            ["19", "TCP/UDP", "CHARGEN (Character Generator)", "Legacy test service; classic distractor and amplification vector"],
            ["20 / 21", "TCP", "FTP (20 data, 21 control)", "Cleartext → FTPS 989/990, or SFTP over SSH (22)"],
            ["22", "TCP", "SSH (also SCP, SFTP)", "The secure replacement for Telnet, rlogin, FTP"],
            ["23", "TCP", "Telnet", "Cleartext remote shell → use SSH 22"],
            ["25", "TCP", "SMTP (server-to-server relay)", "Submission: 587 (STARTTLS) or 465 (implicit TLS)"],
            ["49", "TCP", "TACACS+", "Whole AAA on one TCP port; encrypts the full payload"],
            ["53", "UDP + TCP", "DNS", "UDP for queries; TCP for zone transfers and large answers"],
            ["67 / 68", "UDP", "DHCP (67 server, 68 client)", "—"],
            ["69", "UDP", "TFTP", "No authentication at all; network-device config copies"],
            ["80", "TCP", "HTTP", "→ HTTPS 443"],
            ["88", "TCP/UDP", "Kerberos", "The authentication backbone of Active Directory"],
            ["110", "TCP", "POP3", "→ POP3S 995"],
            ["123", "UDP", "NTP", "Accurate time underpins logs, Kerberos and certificates"],
            ["137–139", "TCP/UDP", "NetBIOS", "Legacy Windows name/session services"],
            ["143", "TCP", "IMAP", "→ IMAPS 993"],
            ["161 / 162", "UDP", "SNMP (161 agent polls, 162 traps)", "Direction matters: traps are sent TO 162 on the manager"],
            ["389", "TCP/UDP", "LDAP", "Cleartext directory → LDAPS 636"],
            ["443", "TCP", "HTTPS", "Also the outer port for many VPNs (SSTP, OpenVPN-TCP)"],
            ["445", "TCP", "SMB / CIFS", "Windows file sharing; favourite worm and ransomware target"],
            ["514", "UDP", "Syslog", "TLS syslog = TCP 6514"],
            ["636", "TCP", "LDAPS", "LDAP over TLS"],
            ["1433", "TCP", "Microsoft SQL Server", "Other DBs: Oracle 1521, MySQL 3306, PostgreSQL 5432"],
            ["1812 / 1813", "UDP", "RADIUS (1812 auth, 1813 accounting)", "Legacy pair: 1645/1646"],
            ["1723", "TCP", "PPTP", "Obsolete VPN; its MS-CHAPv2 auth is broken"],
            ["3389", "TCP", "RDP", "Remote desktop; brute-force magnet — gate behind VPN/MFA"],
        ],
    },
    "OSI": {
        "caption": ("What lives at each layer — the protocol, PDU and device "
                    "placements the exam expects (Sybex keys ARP to Layer 2 and "
                    "TLS to Layer 4; other sources vary, the exam follows the guide)."),
        "headers": ["Layer", "Data unit (PDU)", "Protocols & technologies", "Devices"],
        "rows": [
            ["7 Application", "Data",
             "HTTP/HTTPS, FTP/SFTP, SMTP, IMAP, POP3, DNS, SNMP, SSH, Telnet, DHCP",
             "Application firewalls, gateways, proxies"],
            ["6 Presentation", "Data",
             "Formats and encodings: ASCII, EBCDIC, JPEG, MPEG, GIF; encryption and compression of application data",
             "—"],
            ["5 Session", "Data",
             "NFS, SQL sessions, RPC; dialog control: simplex, half-duplex, full-duplex",
             "—"],
            ["4 Transport", "Segment (TCP) / Datagram (UDP)",
             "TCP, UDP, TLS/SSL (keyed here in the study guide)",
             "—"],
            ["3 Network", "Packet",
             "IPv4/IPv6, ICMP, IGMP, IPsec, NAT; routing protocols: OSPF, BGP, RIP, EIGRP",
             "Routers, layer-3 switches"],
            ["2 Data Link", "Frame",
             "Ethernet (802.3), Wi-Fi (802.11), ARP, PPP, L2TP; MAC and LLC sublayers, MAC addressing, VLANs",
             "Switches, bridges, wireless access points"],
            ["1 Physical", "Bits",
             "Cabling (UTP, STP, fiber, coax), RS-232/RS-449, DSL, SONET; electrical, optical and radio signalling",
             "Hubs, repeaters, modems, media converters"],
        ],
    },
}

DETAILS = {
    "Exam tips": [
        "1 — Trigger words: circle NOT, EXCEPT, LEAST, ABSENCE, AVOID, BEST, FIRST, MOST, PRIMARY — they flip or rank the question",
        "2 — Count the negatives: stem plus option; an EVEN count means the statement is positive again",
        "3 — Restate the ask in ≤8 words before looking at the options (“which is NOT a design principle”)",
        "4 — Options as families: group the options (laws vs frameworks, attacks vs controls) — the odd family member is usually the answer to a NOT question",
        "5 — Last sentence first: in long scenarios the final sentence is the real question; read it, then mine the scenario for only what it needs",
        "6 — Multi-selects: tick only what is DEFINED AS part of the set, not what is merely associated with it (802.1X underpins wireless ENT auth but is not an 802.11 technology)",
        "7 — Multi-selects: reject the option that is DOWNSTREAM of the set — what the set produces or connects to (the public key is what trusting a certificate gives you, not a check you make first)"],
    "Ethics": [
        "Canon I — protect society, the common good, necessary public trust and confidence, and the infrastructure",
        "Canon II — act honorably, honestly, justly, responsibly and legally",
        "Canon III — provide diligent and competent service to principals",
        "Canon IV — advance and protect the profession",
        "Complaints under I & II — any member of the general public has standing",
        "Complaints under III — ONLY an employer or an organization under contract (the principal)",
        "Complaints under IV — any other professional: someone certified or licensed in any field (a CPA counts)",
        "Canons apply in priority order — when they conflict, the lower-numbered canon wins"],
    "Phys KPIs": [
        "Number of successful intrusions",
        "Number of successful disruptions",
        "Number of unsuccessful incidents (attempts that failed)",
        "Time to detect incidents",
        "Time to respond to incidents",
        "Level of organizational impact of incidents",
        "Number of false positives (false detection alerts/alarms)",
        "NOT physical KPIs — compromised accounts (logical security), session disconnects, transmission errors, transactions per minute (network/ops statistics)"],
    "Clark-Wilson": [
        "CDI — Constrained Data Item: the data whose integrity the model protects",
        "UDI — Unconstrained Data Item: input not yet validated (outside the protection)",
        "TP — Transformation Procedure: the ONLY operations allowed to modify a CDI",
        "IVP — Integrity Verification Procedure: confirms CDIs remain in a valid state",
        "Access triple — subject → TP → CDI: users never touch the data directly",
        "NOT an element — “redundant commit statement” (database replication vocabulary, not Clark-Wilson)"],
    "Cert checks": [
        "1 — The CA's digital signature on the certificate is authentic",
        "2 — The certificate has not expired (validity period)",
        "3 — The certificate has not been revoked (check CRL or OCSP)",
        "NOT a pre-check — validating the subject's public key: the key is what you GET by trusting the certificate"],
    "NAC": [
        "Agent-based — software on the host; can quarantine noncompliant devices and push updates automatically",
        "Dissolvable agent — downloaded per session, runs ONCE, then terminates",
        "Permanent agent — installed and resident on the device",
        "Agentless — scans from the network (port scans, service queries, vulnerability scans); CANNOT auto-quarantine or fix hosts — an admin resolves issues manually",
        "Preadmission NAC — device must meet all security requirements BEFORE it may communicate",
        "Postadmission NAC — decisions based on behaviour AFTER connection",
        "802.1X — often used by NAC for authentication, but NOT required by it"],
    "IPSec": [
        "AH — Authentication Header: integrity, data-origin authentication, anti-replay (no encryption)",
        "ESP — Encapsulating Security Payload: confidentiality + integrity of packet contents, limited authentication, anti-replay",
        "IKE — Internet Key Exchange: the key-management umbrella = OAKLEY + SKEME + ISAKMP",
        "OAKLEY — key agreement (Diffie-Hellman based); SKEME — secure key exchange mechanism",
        "ISAKMP — organizes/manages the exchanged keys via SECURITY ASSOCIATIONS; the SAs are what allow MULTIPLE SIMULTANEOUS VPNs per host",
        "Tunnel mode wraps the whole packet; transport mode protects the payload only"],
    "Secure design": [
        "Real principles — least privilege, secure defaults, fail securely, threat modeling, keep it simple, separation of duties, zero trust, privacy by design",
        "Also real (often unlisted) — defense in depth, trust but verify",
        "IMPOSTOR — “people are the weakest link”: people cause breaches but are also a key component of the solution; not a design principle",
        "IMPOSTOR — “security is always top priority”: security is bounded by business objectives and must support the mission, not obstruct it",
        "IMPOSTOR — “risk should be eliminated”: risk can only be reduced, transferred, avoided or accepted — never eliminated"],
    "SAMM": [
        "Governance — strategy & metrics, policy & compliance, EDUCATION & GUIDANCE (training, awareness, organization, culture)",
        "Design — threat assessment, security requirements, security architecture",
        "Implementation — secure build, secure deployment, defect management",
        "Verification — architecture assessment, requirements-driven testing, security testing",
        "Operations — incident management, environment management, operational management"],
    "PbD": ["1 — Proactive, not reactive; preventive, not remedial",
            "2 — Privacy as the DEFAULT setting",
            "3 — Privacy EMBEDDED into design",
            "4 — Full functionality: positive-sum, not zero-sum",
            "5 — End-to-end life cycle protection",
            "6 — Visibility and transparency: keep it open",
            "7 — Respect for user privacy: keep it user-centric",
            "NOT PbD — “never trust, always verify” (zero trust), “trust but verify” (pre-zero-trust management), Clark-Wilson's access triplet, “worse is better” (New Jersey style)"],
    "Fagan": ["Step 1 — Planning (schedule, participants, materials)",
              "Step 2 — Overview (author walks the team through the work)",
              "Step 3 — Preparation (reviewers study it individually)",
              "Step 4 — Inspection (the formal defect-finding meeting)",
              "Step 5 — Rework (author fixes what was found)",
              "Step 6 — Follow-up (verify the fixes; decide if re-inspection is needed)"],
    "IDEAL": ["Initiating — business reasons, sponsorship, infrastructure",
              "Diagnosing — assess the current state, recommend changes",
              "Establishing — prioritize, plan, and resource the work",
              "Acting — develop, test, refine and IMPLEMENT the solutions",
              "Learning — analyze results, propose future improvements"],
    "CC": ["PP (Protection Profile) — the customer's security requirements: “what I want”",
           "ST (Security Target) — the vendor's claims for its product: “what I provide”",
           "TOE (Target of Evaluation) — the product or system being evaluated",
           "Evaluation — an accredited lab checks the ST's claims at a chosen rigour",
           "EAL1 functionally tested → EAL2 structurally tested → EAL3 methodically tested & checked → EAL4 methodically designed, tested, reviewed → EAL5 semiformally designed & tested → EAL6 semiformally verified → EAL7 formally verified design and tested",
           "Why it replaced TCSEC/ITSEC — dynamic and subjective evaluation via PP-vs-ST comparison instead of a static checklist"],
    "Risk frameworks": ["NIST RMF — the US federal Risk Management Framework (categorize → select → implement → assess → authorize → monitor)",
                        "COSO ERM — enterprise risk management from the Treadway Commission",
                        "ISACA Risk IT — IT-risk framework from the makers of COBIT",
                        "OCTAVE — Operationally Critical Threat, Asset and Vulnerability Evaluation (self-directed, from CMU/SEI)",
                        "FAIR — Factor Analysis of Information Risk (quantitative, loss-magnitude based)",
                        "TARA — Threat Assessment and Remediation Analysis",
                        "NOT frameworks — NIST (an agency), ARO (a metric), CEH (a certification), CCMP (a wireless cipher mode)"],
    "Ports": ["Ranges — well-known 0–1023, registered 1024–49151, dynamic/ephemeral 49152–65535 (client source ports come from here)",
              "AAA — TACACS+ = TCP 49 (one port, full AAA, whole payload encrypted); RADIUS = UDP 1812 auth + 1813 accounting (legacy 1645/1646)",
              "Secure swaps — 23→22, 21→22 (SFTP), 80→443, 389→636, 110→995, 143→993, 25→587/465, 514→6514",
              "SNMP — agents LISTEN on 161 for polls; managers RECEIVE traps on 162",
              "DNS 53 — UDP for queries, TCP for zone transfers",
              "Databases — MS SQL 1433, Oracle 1521, MySQL 3306, PostgreSQL 5432"],
    "PoR": ["Step 1 — Prove wallet ownership: the custodian demonstrates control of its on-chain addresses (cold and hot)",
            "Step 2 — Snapshot liabilities: every customer balance is captured at one date and time",
            "Step 3 — Build the Merkle tree: each leaf hashes a customer ID + balance; the root seals the whole liability set",
            "Step 4 — Publish root + zero-knowledge proof: the ZKP shows all balances were counted, were non-negative, and sum to the claimed total — without revealing accounts",
            "Step 5 — Customer self-verification: each customer checks their own leaf (record ID) is under the published root",
            "Limitation — proves assets ≥ RECORDED liabilities at a snapshot; it cannot reveal off-book liabilities"],
    "Merkle tree": ["Leaves — hash each data block (file, transaction, account record)",
                    "Parents — hash the concatenation of each pair of children, repeating up the tree",
                    "Root — the single top hash that seals the entire set; any change to any block changes it",
                    "Inclusion proof — to prove one block belongs, supply only its sibling hashes up to the root (log n hashes)",
                    "Where it's used — blockchains, Certificate Transparency, backup/file-sync integrity, exchange proof-of-reserves"],
    "ZKP": ["Completeness — if the statement is true, an honest prover convinces an honest verifier",
            "Soundness — if the statement is false, no cheating prover can convince the verifier (except with negligible probability)",
            "Zero-knowledge — the verifier learns nothing beyond the truth of the statement",
            "zk-SNARK — Succinct Non-interactive ARgument of Knowledge: a tiny proof, verified fast, no back-and-forth",
            "Exam angle — proving possession (password, key, balance) WITHOUT disclosure; contrast with authentication that transmits the secret"],
    "PASTA": ["Stage 1 — Define Objectives (business & security goals)",
              "Stage 2 — Define Technical Scope (attack surface)",
              "Stage 3 — Application Decomposition (components, data flows, trust boundaries)",
              "Stage 4 — Threat Analysis (intel-driven threat identification)",
              "Stage 5 — Vulnerability & Weakness Analysis",
              "Stage 6 — Attack Modeling & Simulation",
              "Stage 7 — Risk & Impact Analysis (countermeasures weighted by asset value)"],
    "STRIDE": ["Spoofing — attacks authentication",
               "Tampering — attacks integrity",
               "Repudiation — attacks non-repudiation",
               "Information disclosure — attacks confidentiality",
               "Denial of service — attacks availability",
               "Elevation of privilege — attacks authorization"],
    "DREAD": ["Damage — how bad is the impact?",
              "Reproducibility — how reliably does the attack work?",
              "Exploitability — how much effort/skill to launch?",
              "Affected users — how many people are hit?",
              "Discoverability — how easily is the flaw found?"],
    "SW-CMM": ["Level 1 Initial — ad hoc, heroics",
               "Level 2 Repeatable — basic project management discipline",
               "Level 3 Defined — processes documented organization-wide",
               "Level 4 Managed — processes quantitatively measured",
               "Level 5 Optimizing — continuous process improvement"],
    "OSI": ["Layer 1 Physical — cables, signals, hubs",
            "Layer 2 Data Link — frames, MAC addresses, switches",
            "Layer 3 Network — packets, IP, routers",
            "Layer 4 Transport — TCP/UDP, ports, segmentation",
            "Layer 5 Session — dialog establishment and teardown",
            "Layer 6 Presentation — formats, compression, encryption",
            "Layer 7 Application — HTTP, DNS, SMTP and friends"],
    "TCP/IP": ["Link — OSI layers 1–2", "Internet — OSI layer 3 (IP)",
               "Transport — OSI layer 4 (TCP/UDP)", "Application — OSI layers 5–7"],
    "IR": ["ISC2's SEVEN incident-management steps, in order:",
           "Detection → Response → Mitigation → Reporting → Recovery → Remediation → Lessons Learned",
           "The condensed lifecycle (NIST-style) you'll also see:",
           "Detection/Analysis → Containment → Eradication → Recovery → Lessons Learned",
           "Both get tested — read the stem for “ISC2 steps” vs “lifecycle”"],
    "SDLC": ["Requirements — what must it do (start security HERE)",
             "Design — architecture and threat modeling",
             "Implementation — secure coding",
             "Testing — SAST/DAST, reviews, UAT",
             "Deployment / Operations — hardening, monitoring, patching",
             "Retirement — secure decommissioning and data disposal"],
    "TCB": ["TCB — hardware + software + controls that enforce the security policy",
            "Security perimeter — the boundary between the TCB and everything else",
            "Reference monitor — the CONCEPT: validates every access to every object before granting",
            "Security kernel — the IMPLEMENTATION of the reference monitor in hw/sw/firmware"],
    "ATO": ["Authorization to Operate — the standard full approval",
            "Common Control Authorization — approval of controls shared across systems",
            "Authorization to Use — accept another organization's authorization (e.g. cloud)",
            "Denial of Authorization — the risk is unacceptable; do not operate"],
    "Rings": ["Ring 0 — kernel: most privileged",
              "Rings 1–2 — OS services and device drivers",
              "Ring 3 — user applications: least privileged",
              "Inner rings service and control outer rings"],
    "CPTED": ["Natural access control — entrances, fencing, bollards and lighting subtly steer movement",
              "Natural surveillance — maximize visibility so offenders feel observable",
              "Territorial control — make the space feel owned by an inclusive, caring community",
              "Image and milieu — maintenance and surroundings that signal the area is cared for"],
    "Sprinklers": ["Wet pipe — pipes always charged with water; simplest, riskiest near electronics",
                   "Dry pipe — pipes hold pressurized air until a head opens; suits freezing areas",
                   "Preaction — TWO triggers (detector fills pipes, then head releases); computer facilities",
                   "Deluge — open heads flood the area with large volumes; not for electronics"],
    "Cable plant": ["Entrance facility — where the carrier enters (the demarcation point)",
                    "Equipment room — the main cross-connect and core gear",
                    "Backbone distribution system — links equipment room to telecom rooms between floors",
                    "Telecommunications room — per-floor connection point",
                    "Horizontal distribution system — telecom room out to the wall jacks"],
    "DSS": ["Approved under FIPS 186-5: RSA",
            "Approved: ECDSA (Elliptic Curve Digital Signature Algorithm)",
            "Approved: EdDSA (Edwards-Curve Digital Signature Algorithm)",
            "NOT approved: classic DSA (removed in 186-5) and ElGamal"],
    "PFX": ["DER — binary, single certificate (.der/.cer)",
            "PEM — base64 TEXT (-----BEGIN CERTIFICATE-----)",
            "PFX / P12 — BINARY, Windows, usually certificate + private key, password-protected",
            "P7B / PKCS#7 — text, certificate chains, never the private key"],
    "SOC reports": ["SOC 1 — controls affecting customers' FINANCIAL reporting (for their auditors)",
                    "SOC 2 — Trust Services Criteria: Security (always) + Availability, Processing Integrity, Confidentiality, Privacy; NDA-restricted",
                    "SOC 3 — public, marketing-grade summary of SOC 2",
                    "Type I — control DESIGN at a point in time",
                    "Type II — operating EFFECTIVENESS over a period (6–12 months); the one customers should ask for"],
    "DoS": ["SYN flood — TCP: half-open handshakes exhaust the connection table",
            "Smurf — ICMP: spoofed echo requests to a broadcast address, replies flood the victim",
            "Fraggle — UDP: same amplification trick as Smurf, but with UDP echo/chargen",
            "Mitigations: SYN cookies, disable directed broadcasts, rate limiting"],
    "CASL": ["Consent before sending: express (recorded opt-in) or implied (existing business relationship, published address, recent inquiry) — implied consent is TIME-LIMITED",
             "Sender identification in every message: name, mailing address, contact method",
             "Working unsubscribe, honoured within 10 business days",
             "Burden of proving consent is on the SENDER — keep consent records",
             "Enforced by the CRTC (with Competition Bureau and Privacy Commissioner); penalties up to CAD 1M (individuals) / 10M (organizations); directors personally liable",
             "Private right of action suspended indefinitely in 2017",
             "Related: PIPEDA (Canadian privacy), CAN-SPAM (US, opt-out), GDPR/ePrivacy (EU)"],
    "COBIT": ["1 Provide Stakeholder Value",
              "2 Holistic Approach",
              "3 Dynamic Governance System",
              "4 Governance Distinct from Management",
              "5 Tailored to Enterprise Needs",
              "6 End-to-End Governance System"],
    "Decomposition": ["Trust boundaries — where the level of trust changes",
                      "Dataflow paths — how data moves between components",
                      "Input points — where external input enters the system",
                      "Privileged operations — actions requiring elevated rights",
                      "Details about security stance and approach — the declared security posture"],
    "EAP": ["Real methods: LEAP, PEAP, EAP-TLS, EAP-TTLS, EAP-FAST, EAP-SIM, EAP-MD5, EAP-POTP",
            "More than 40 methods are defined — EAP is a framework, not one protocol",
            "Fakes that appear as distractors: EAP-VPN, EAP-MBL, VEAP"],
    "RFC 1918": ["10.0.0.0 – 10.255.255.255 (10.0.0.0/8)",
                 "172.16.0.0 – 172.31.255.255 (172.16.0.0/12)",
                 "192.168.0.0 – 192.168.255.255 (192.168.0.0/16)",
                 "NOT private: 169.254.x.x — that's APIPA link-local"],
    "Kerberos": ["KDC — Key Distribution Center (authentication + ticket-granting services)",
                 "TGT — ticket-granting ticket, obtained at logon",
                 "Service tickets — presented to each resource",
                 "Symmetric crypto (AES); passwords never cross the network",
                 "Clock tolerance ~5 minutes — drift breaks authentication (fix: NTP)",
                 "KRBTGT account compromise → forged golden tickets"],
    "PtH": ["Pass the hash — reuse an NTLM hash without knowing the password",
            "Pass the ticket — reuse a captured Kerberos ticket",
            "Golden ticket — forge TGTs after compromising KRBTGT (Kerberos)",
            "Rainbow table — offline cracking with precomputed hash tables"],
    "MAC": ["Hierarchical environment — ordered labels low → high (each level relates to the ones above/below)",
            "Compartmentalized environment — isolated compartments, no ordering between them",
            "Hybrid environment — hierarchical levels containing compartments",
            "These three are the ONLY MAC environments — 'bracketed' and 'centralized' are invented distractors"],
    "6 Ds": ["1 Deter — discourage the attempt (signage, fencing, lighting)",
             "2 Deny — block access (locks, barriers)",
             "3 Detect — notice the intrusion (sensors, cameras)",
             "4 Delay — slow progress until response arrives",
             "5 Determine — assess what is happening",
             "6 Decide — choose and execute the response"],
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
    return ('<details class="gl-more"><summary>In depth — the steps that get tested</summary>'
            + inner + "</details>")


def remember_html(title, lines):
    lis = "".join("<li>" + escape(x) + "</li>" for x in lines)
    return ('<div class="gl-remember"><h3>Remember this — ' + escape(title)
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
        "<p>CISSP asks for two vocabularies at once: the technical language of security "
        "engineering and the managerial language of risk, governance and continuity. A lot "
        "of exam questions are perfectly answerable — once you decode the acronyms they're "
        "wrapped in. This glossary is the decoder: " + str(total) + " terms in plain English, "
        "organized by the domains they belong to, with study tips on the pairs people "
        "actually confuse.</p>"
        "<p>It's written for CISSP candidates, and equally for technology executives who "
        "want a working cybersecurity vocabulary without a certification course. Educational "
        "reference only — see the note at the end of the page.</p>"
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
        '<p class="gl-flash"><a href="cissp-flashcards.html">Study these terms with flashcards &amp; exam-style practice questions →</a>'
        '<a href="cissp-mind-map.html">See the whole syllabus as a mind map →</a>'
        '<a href="cissp-score-tracker.html">Track your chapter scores →</a></p>'
        '<div class="gl-controls" id="gl-controls" hidden>'
        '<input class="gl-search" id="gl-search" type="search" '
        'placeholder="Search acronyms, terms, definitions\u2026" aria-label="Search the glossary">'
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
        if key == "ops":
            steps = ('<span class="gl-ir__arrow" aria-hidden="true">\u2192</span>'.join(
                '<span class="gl-ir__step">' + escape(s) + "</span>" for s in IR_CALLOUT))
            extra += ('<div class="gl-remember"><h3>Remember this — Incident response lifecycle</h3>'
                      '<div class="gl-ir" aria-label="Incident response lifecycle order">'
                      + steps + "</div></div>")
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
        '<p>The authoritative statement of what the exam covers is the official '
        '<a href="' + ISC2_OUTLINE_URL + '" target="_blank" rel="noopener">ISC2 CISSP '
        "Certification Exam Outline</a>. Definitions in this glossary are independently "
        "written summaries — use the outline to weight your study time across domains.</p>"
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
article.excerpt = ("A practical, searchable glossary of " + str(len(TERMS)) + " CISSP security "
                   "acronyms with plain-English definitions and study tips.")
article.body_md = body
article.meta_title = TITLE
article.meta_description = META_DESCRIPTION
article.save()
print(("created" if created else "updated"), "article", SLUG,
      "| terms:", len(TERMS), "| body bytes:", len(body))

# ---------------------------------------------------------------------------
# Shared JSON data source (consumed by the flashcards page, and any future
# tool). Written into the built site as assets/data/cissp-glossary.json.
# Original scenario questions (NOT ISC2 exam content) live here too.
# ---------------------------------------------------------------------------
import json as _json
import re as _re
from datetime import datetime as _dt, timezone as _tz
from pathlib import Path as _Path
from django.conf import settings as _settings


def term_id(acr):
    return _re.sub(r"[^a-z0-9]+", "-", acr.lower()).strip("-")


# (term acronym the scenario resolves to, original scenario question)
SCENARIOS = [
    ("DH", "Two parties need to establish shared key material over an untrusted network without ever transmitting the secret itself. Which method fits?"),
    ("ECC", "A battery-constrained mobile app needs strong public-key cryptography with small keys. Which approach fits best?"),
    ("SHA", "You must confirm a downloaded file hasn't been altered, with no shared secret involved. Which mechanism produces the fixed-length fingerprint?"),
    ("HMAC", "A message must be verifiable for both integrity and sender authenticity using a shared secret key. Which construction provides this?"),
    ("OCSP", "A client needs a real-time answer on whether a specific certificate has been revoked. Which protocol?"),
    ("HSM", "An organization wants dedicated, tamper-resistant hardware to generate and guard its signing keys. What should it deploy?"),
    ("PFS", "Even if a server's long-term private key is stolen next year, last month's captured sessions must stay unreadable. Which property guarantees this?"),
    ("Merkle tree", "A service publishes one hash and lets any customer prove their record was included in it using only a short chain of sibling hashes. Which structure?"),
    ("SRTP", "Voice calls must be protected against eavesdropping while the packets cross the network. Which protocol secures the media stream itself?"),
    ("UEM", "One console must enforce policy on phones, laptops, wearables and IoT devices alike. Which solution class?"),
    ("BGP", "Routing between your network and external autonomous systems has broken, while internal routing is fine. Which protocol is implicated?"),
    ("Polyinstantiation", "A database must show different rows for the same primary key depending on the reader's clearance, so classified entries stay invisible without leaving a telltale gap. Which technique?"),
    ("MUX", "Dozens of separate links carrying different protocols must share one new backbone line, their signals combined into a single output. Which device?"),
    ("PIDAS", "Two or three concentric fences create a guard corridor, carry touch sensors, and use the plain outer fence to keep animals from tripping alarms. Which system?"),
    ("LEO", "A field station in an uninhabited region needs high-speed, low-latency internet with no ground infrastructure. Which satellite service class?"),
    ("ZKP", "A prover must convince an auditor that every account was counted in a total — without revealing a single account. Which cryptographic technique?"),
    ("Dual control", "No withdrawal can be signed unless three of five officers participate, and no officer ever holds the whole key. Which paired principles are at work?"),
    ("OIDC", "Which identity standard adds authentication and identity information on top of OAuth 2.0?"),
    ("OAuth", "A third-party app needs limited access to a user's cloud files without ever learning the user's password. Which framework enables this?"),
    ("SAML", "An enterprise wants browser-based SSO into partner web applications using XML assertions. Which standard?"),
    ("MAC", "Access decisions are enforced centrally from classification labels and clearances — owners cannot override them. Which access-control model?"),
    ("JIT", "Administrators should hold elevated rights only for the duration of an approved change window. Which access approach?"),
    ("IPS", "Security wants suspicious network traffic detected AND actively blocked inline. Which control?"),
    ("NAC", "Unknown laptops must be checked and quarantined before they may join the corporate network. Which control decides admission?"),
    ("IPSec", "All IP traffic between two office sites must be protected at the network layer. Which protocol suite?"),
    ("DNSSEC", "Responses from your name servers must be verifiable as authentic and untampered. Which extension provides this?"),
    ("SIEM", "Logs from firewalls, servers and applications must be aggregated and correlated into one alerting view. Which platform?"),
    ("SOAR", "The SOC wants repetitive triage and response playbooks executed automatically. Which capability?"),
    ("TTP", "Analysts describe an adversary by its characteristic behaviors and methods across intrusions. What are they cataloguing?"),
    ("SCA", "Which technology identifies vulnerable open-source dependencies in an application's build pipeline?"),
    ("SAST", "Source code must be analyzed for security flaws without executing the application. Which testing approach?"),
    ("RPO", "A business can tolerate losing no more than 15 minutes of transaction data after a failure. Which recovery metric defines this requirement?"),
    ("RTO", "A critical service must be restored within four hours of an outage. Which recovery metric captures this target?"),
    ("Hoax", "An email warns that a virus will destroy your files unless you immediately delete a named system file — and the claimed sender confirms they never sent it. What kind of social-engineering message is this?"),
    ("DMCA", "A streaming service wants action against a user who bypassed the encryption protecting its video content. Which US federal law prohibits circumventing copyright protection mechanisms?"),
    ("SAE", "A Wi-Fi vendor says WPA3 replaces the preshared-key four-way handshake with a password-authenticated key exchange that resists offline dictionary attacks. Which technology?"),
    ("DNS poisoning", "After flushing their DNS cache a user still resolves a site to the wrong IP, the flushed cache shows no hosts-file entries, and a colleague on another network resolves it correctly. Which attack best explains this?"),
    ("VXLAN", "Satellite offices must join the same switch-created network segments as headquarters, using an encapsulation protocol that stretches them across subnets and distances. Which technology?"),
    ("DCE", "A distributed system presents many machines as one environment and defines client-server interfaces in an IDL, with RPC, CORBA and DCOM as examples. What is this environment called?"),
    ("IAAA", "An administrator reviews server logs to hold users responsible for their actions. Which access-control framework names the five elements this review serves?"),
    ("Synthetic transactions", "A monitoring tool replays scripted routine transactions with known expected results against a web application and compares the outcomes. Which testing technique?"),
]

_terms_by_acr = {t[1]: t for t in TERMS}
_ids = [term_id(t[1]) for t in TERMS]
assert len(set(_ids)) == len(_ids), "term id collision"

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
# ORIGINAL exam-style practice questions (single best answer, Sybex-difficulty
# STYLE only — scenario stems, sibling-concept distractors, BEST/FIRST/NOT
# phrasing). All scenarios written from scratch; none reproduce ISC2, Sybex,
# LearnZapp or any other question bank. options[0] is ALWAYS the correct
# answer as authored; the app shuffles presentation order.
# (category, question, [correct, d1, d2, d3], explanation)
# ---------------------------------------------------------------------------
QUIZ = [
    # --- Risk, Governance & Continuity --------------------------------------
    ("risk",
     "Which of the following is NOT one of the seven foundational principles of Privacy by Design?",
     ["Never trust, always verify", "Privacy as the default setting", "Full functionality — positive-sum, not zero-sum", "End-to-end life cycle protection"],
     "“Never trust, always verify” is zero trust — network architecture, not PbD. The other three are genuine PbD principles, alongside proactive-not-reactive, privacy embedded into design, visibility/transparency, and user-centricity."),
    ("risk",
     "A regulator finds that a firm wrote excellent security policies three years ago but has never since audited whether they are followed. Which principle is the firm failing?",
     ["Due care", "Due diligence", "Separation of duties", "Least privilege"],
     "The programme was ESTABLISHED (due diligence done) but is not being PRACTICED and verified — the ongoing prudent-person activities, periodic audits first among them, are due care. Diligence designs; care carries out."),
    ("risk",
     "Which of the following is NOT a risk management framework?",
     ["CCMP", "OCTAVE", "FAIR", "TARA"],
     "CCMP is the AES-based cipher mode protecting WPA2 wireless traffic — cryptography, not risk management. OCTAVE, FAIR and TARA all belong to the recognized framework list alongside NIST RMF, COSO ERM and ISACA Risk IT."),
    ("risk",
     "A business unit is being sold off. Which THREE security processes most directly reduce the data-loss risk of the divestiture?",
     ["Sanitize assets, destroy removed media, debrief departing employees", "Update firmware, renew certificates, sanitize assets", "Debrief employees, renew certificates, propose improvements", "Destroy media, update firmware, revoke certificates"],
     "Divestiture security is about what LEAVES: scrub the assets, physically destroy storage that leaves custody, and debrief the people (NDAs, access surrender). Firmware, certificates and feature work invest in assets that are departing — wasted and wrong."),
    ("risk",
     "A data center asset is valued at $200,000. A flood would damage 25% of it, and floods are expected once every five years. What is the ALE?",
     ["$10,000", "$50,000", "$40,000", "$250,000"],
     "SLE = $200,000 × 0.25 = $50,000 (that figure is the classic trap). ARO = 1/5 = 0.2, so ALE = SLE × ARO = $10,000."),
    ("risk",
     "An auditor notes that a payment process can only be defrauded if two employees cooperate. Which control created this property?",
     ["Separation of duties", "Least privilege", "Job rotation", "Need to know"],
     "Requiring collusion is the hallmark of SoD — one person creates, another approves. Least privilege limits each account's rights but one person could still hold a complete sensitive workflow."),
    ("risk",
     "A continuity planner documents that order processing can survive at most 18 hours of outage before the company suffers unacceptable harm. Which metric has she defined?",
     ["MTD", "RTO", "RPO", "MTTR"],
     "The maximum tolerable downtime bounds the business process itself; the RTO is the engineering target set BELOW the MTD, and RPO measures data loss, not time down."),
    ("risk",
     "The board asks for an early-warning metric that signals when patching discipline is drifting toward dangerous exposure. Which should the CISO present?",
     ["A KRI", "A KPI", "An SLA", "The ALE"],
     "A rising 'systems past patch deadline' figure indicates changing risk exposure — a key RISK indicator. A KPI measures performance against an objective, which is how the same number would be framed for the IT team."),
    ("risk",
     "A new CISO wants to build the organization's first business continuity plan. What should be completed FIRST?",
     ["A business impact analysis", "The disaster recovery plan", "A tabletop exercise", "Selection of an alternate site"],
     "The BIA identifies critical processes and quantifies disruption impact — everything else in BC/DR planning (including RTO/RPO targets and site strategy) is derived from it."),

    # --- Data & Asset Security ----------------------------------------------
    ("data",
     "A hospital wants to stop staff from emailing patient records to personal accounts or copying them to USB drives. Which control BEST addresses this?",
     ["DLP", "CASB", "FDE", "DRM"],
     "Detecting and blocking unauthorized movement of sensitive data is exactly DLP. CASB governs cloud-service usage, FDE protects a lost device, and DRM controls licensed content usage."),
    ("data",
     "A vendor announces that a product will receive no further security patches after June, though it will still function. What has the product reached?",
     ["End of Support", "End of Life", "End of Sale", "Planned obsolescence"],
     "No more support or security updates = EOS. EOL is the end of active development/marketing of the product; the two dates often differ, and the security cliff is EOS."),
    ("data",
     "A regional sales manager's laptop is stolen from a car overnight. Which control provides the STRONGEST protection for the data on it?",
     ["Full disk encryption", "TLS", "A VPN", "DLP"],
     "The threat is physical access to data at rest — FDE. TLS and VPNs protect data in transit, and DLP policies on a powered-off stolen disk enforce nothing."),
    ("data",
     "A billing export contains patient names, dates of service, and diagnosis codes. How should this file be classified?",
     ["PHI", "PII only", "PCI data", "Public data"],
     "Individually identifiable health information is PHI — a superset situation: it contains PII, but the health context triggers the stricter protection regime (e.g. HIPAA)."),
    ("data",
     "An e-book publisher wants purchased titles to open only inside its reader app and never be copied or printed. Which technology enforces this?",
     ["DRM", "DLP", "FDE", "A CASB"],
     "Controlling how licensed digital CONTENT may be used after delivery is digital rights management. DLP protects an organization's own sensitive data from leaving; it doesn't govern a customer's use of sold content."),

    # --- Cryptography --------------------------------------------------------
    ("crypto",
     "A weather-modelling build calls for over 4,000 processors, each running its own instruction set with its own memory and bus, all answering to one master coordination system. Which architecture is this?",
     ["MPP", "SMP", "Multicore", "Grid computing"],
     "Independent processors (own instructions, memory, bus) at thousands-scale under central coordination is massive parallel processing — essentially many AMP units federated. SMP would share one OS and memory; grid computing is loosely-coupled volunteer nodes, not a managed single system."),
    ("crypto",
     "An extinguisher rated for Class B flammable-liquid fires may use all of the following media EXCEPT:",
     ["Water", "Carbon dioxide", "A halon substitute", "Soda acid"],
     "Water is never a Class B medium — it splashes and spreads burning liquid. CO2, halon (or an approved substitute) and soda acid are all legitimate Class B options; soda acid is the one people wrongly exclude."),
    ("crypto",
     "Under the Common Criteria, a government agency documents the security capabilities it requires before approaching any vendor. Which document is it writing?",
     ["A Protection Profile", "A Security Target", "A Target of Evaluation", "An EAL4 assurance package"],
     "The PP is the customer's “I want”; the vendor answers with a Security Target (“I provide”) about its product (the TOE), and the lab grades the checking rigour as an EAL. Customer wish = PP is the whole question."),
    ("crypto",
     "A company issuing phones, laptops, smartwatches and IoT sensors wants one console to enforce policy, monitor and remotely manage all of them. What should it deploy?",
     ["UEM", "MDM", "Application allow listing", "NAC"],
     "Unified endpoint management spans EVERY endpoint class from one platform — it supersedes mobile-only MDM/EMM. Allow listing is one feature inside such a product, and NAC gates network admission rather than managing devices."),
    ("crypto",
     "An exchange publishes a single hash value and claims any of its ten million customers can prove their balance was included in it using only about 23 hashes. Which structure makes this possible?",
     ["A Merkle tree", "A blockchain", "An HMAC chain", "A digital signature over the full data set"],
     "A Merkle tree's inclusion proof needs only the sibling hashes up the tree — log2(10M) ≈ 23. A signature over the whole set proves the set's integrity but gives an individual no way to check their own record is inside it."),
    ("crypto",
     "A protocol must convince a verifier that a claim is true while revealing nothing beyond the truth of the claim. Which THREE properties define such a proof?",
     ["Completeness, soundness, zero-knowledge", "Confidentiality, integrity, availability", "Authentication, authorization, accounting", "Succinctness, non-interactivity, speed"],
     "The ZKP trio: a true claim always convinces (completeness), a false one almost never does (soundness), and the verifier learns nothing else (zero-knowledge). Succinct/non-interactive describe the zk-SNARK variant, not the defining properties."),
    ("crypto",
     "Authorizing a high-value transfer requires three of five hardware keys held by different officers, and no officer ever sees another officer's key material. Which pair of key-management principles is implemented?",
     ["Dual control and split knowledge", "Separation of duties and least privilege", "Defense in depth and need to know", "Job rotation and two-person integrity"],
     "Multiple people required for ONE operation = dual control; no one person holding the whole secret = split knowledge. Separation of duties divides different DUTIES across roles — here it is one duty, deliberately shared."),
    ("crypto",
     "Attackers who compromised an exchange's online signing infrastructure drained those wallets within minutes, yet most customer assets were unaffected. Which practice most directly explains the limited loss?",
     ["Most keys were held in offline cold storage", "Perfect forward secrecy", "Key escrow with a third party", "Certificate pinning on the wallet apps"],
     "Keys that never touch a network cannot be drained by compromising online systems — the hot/cold split caps the blast radius. PFS protects past session traffic, escrow is availability of keys, pinning authenticates servers to clients."),
    ("crypto",
     "Two services that already share a secret key must exchange terabytes of data nightly with minimal CPU cost. Which algorithm should encrypt the data?",
     ["AES", "RSA", "ECC", "SHA-256"],
     "Bulk encryption is symmetric work — AES. RSA/ECC are orders of magnitude slower and used for key exchange and signatures; SHA-256 is a hash and provides no confidentiality."),
    ("crypto",
     "Two internal services sharing a secret key need each message verified for integrity AND sender authenticity. Non-repudiation is not required. Which mechanism fits BEST?",
     ["HMAC", "A digital signature", "SHA-256 alone", "AES-CBC"],
     "HMAC = hash + shared secret → integrity and authenticity. A plain hash proves only integrity; digital signatures add non-repudiation but require asymmetric keys and PKI overhead the requirement doesn't ask for."),
    ("crypto",
     "A browser must confirm in real time, with minimal data transfer, whether a single certificate has been revoked. Which mechanism should it use?",
     ["OCSP", "A CRL download", "A new CSR", "Certificate pinning"],
     "OCSP queries the status of one certificate on demand; a CRL is a periodically published full list — heavier and potentially staler."),
    ("crypto",
     "A laptop fleet must verify boot integrity and protect disk-encryption keys using hardware built into each machine. Which component is being used?",
     ["TPM", "HSM", "A smart card", "Secure enclave software"],
     "Per-device platform integrity + key protection = the TPM. An HSM is dedicated (usually network/rack or PCIe) hardware for an organization's high-value keys, not a per-laptop boot-integrity chip."),
    ("crypto",
     "Two mobile apps with no prior shared secret must derive a session key over an untrusted network, using small keys suitable for low-power devices. Which approach fits BEST?",
     ["ECDH", "RSA encryption of a random key", "AES key wrapping", "HMAC"],
     "Key agreement without a pre-shared secret is Diffie-Hellman; the elliptic-curve variant gives equivalent strength with far smaller keys — the low-power requirement is the discriminator against RSA."),

    # --- Communication & Network Security ------------------------------------
    ("network",
     "An infrastructure refresh must carry storage-array traffic, replace desk phones, and link AI/ML accelerators to CPUs — all over the standard IP/Ethernet estate. Which protocol trio fits?",
     ["iSCSI, VoIP and CXL", "FCoE, POTS and TFTP", "iSCSI, SIP and CHARGEN", "NFS, VoIP and SNMP"],
     "All three are converged protocols: iSCSI puts SAN storage on IP, VoIP replaces landlines, CXL is the high-speed CPU-to-accelerator interconnect used in AI/ML builds. TFTP, CHARGEN and POTS are the giveaways in the wrong options."),
    ("network",
     "After a firmware update on the edge router, staff can reach every internal system but no internet destinations. Which protocol's configuration should be examined FIRST?",
     ["BGP", "OSPF", "RIP", "IGRP"],
     "Internal routing still works, so the interior protocols (OSPF, RIP, IGRP) are doing their job — the break is at the border, where the router exchanges routes with external autonomous systems via BGP, the exterior gateway protocol."),
    ("network",
     "A wireless design calls for the frequency access method with the greatest throughput and the least interference. Which should be selected?",
     ["OFDM", "FHSS", "DSSS", "CSMA/CD"],
     "OFDM's orthogonal (perpendicular) subcarriers don't interfere with each other, giving it the throughput crown over frequency-hopping FHSS and chipping-code DSSS. CSMA/CD is Ethernet's collision handling, not a radio access method."),
    ("network",
     "During hardening, an admin configures a host utility that refuses or allows connections to local network services based on the connecting user and system identifiers. What is this?",
     ["A TCP Wrapper", "An 802.1Q trunk", "An IPsec policy", "An L2TP tunnel"],
     "ID-based allow/deny in front of host services is the TCP Wrapper — a basic host firewall. 802.1Q tags VLANs on switches, IPsec protects traffic across links, L2TP tunnels through non-IP networks."),
    ("network",
     "Recordings of confidential voice calls keep appearing outside the organization, and captures show the audio streams cross the LAN unencrypted. What fixes the transport?",
     ["SRTP", "DMARC", "DISA", "S/MIME"],
     "The media stream is plain RTP — SRTP adds encryption, authentication and replay protection to it. DMARC and S/MIME are email controls, and DISA guards PBX dial-in access, not VoIP streams."),
    ("network",
     "Network engineers manage routers through a TACACS+ server while a VPN concentrator authenticates users against RADIUS. Which firewall rules support both?",
     ["TCP 49 and UDP 1812", "UDP 49 and TCP 1812", "TCP 1812 and UDP 49", "TCP 389 and UDP 53"],
     "TACACS+ runs the whole AAA exchange over TCP 49 with the full payload encrypted; RADIUS authenticates on UDP 1812 (accounting on 1813). The transports are the trap — each protocol uses the one people guess for the other. 389 is LDAP, 53 is DNS."),
    ("network",
     "A monitoring station must receive unsolicited alerts sent by network devices the moment something fails. Which port must be open toward the station?",
     ["UDP 162", "UDP 161", "TCP 514", "UDP 123"],
     "Devices SEND traps to the manager on UDP 162; 161 is where agents LISTEN for the manager's polls — the direction is the whole question. 514 is syslog (also alerts, but the stem says SNMP-style traps from devices), 123 is NTP."),
    ("network",
     "A packet capture shows a client connecting from source port 51,844 to a server on port 443. What kind of port is the client using?",
     ["A dynamic (ephemeral) port", "A well-known port", "A registered port", "A reserved system port"],
     "Client source ports are drawn from the dynamic/ephemeral range 49152–65535. Well-known = 0–1023 (the server's 443 lives there), registered = 1024–49151."),
    ("network",
     "A monitoring appliance is connected to a switch SPAN port and must never be able to interrupt production traffic. Which technology matches this deployment?",
     ["IDS", "IPS", "WAF", "NAC"],
     "A SPAN/mirror port sees copies of traffic out-of-band — detection only. An IPS must sit inline to block, which contradicts the 'never interrupt traffic' constraint."),
    ("network",
     "An organization's public range is 203.0.113.0/24. Which OUTBOUND packet should its egress filter BLOCK?",
     ["One with source address 172.16.4.9", "One with source address 203.0.113.40", "One with source address 203.0.113.7", "One with source address 203.0.113.199"],
     "Egress filtering drops traffic leaving with source addresses that aren't yours — RFC 1918 or foreign sources indicate spoofing or misconfiguration. 172.16.0.0/12 is private and must never appear as a source on the internet."),
    ("network",
     "Finance and engineering hosts share the same physical switches, but finance traffic must be isolated into its own broadcast domain without new cabling. What should be configured?",
     ["VLANs", "A VPN", "NAC", "A WAF"],
     "Logical segmentation on shared switching hardware is exactly what VLANs do. A VPN protects traffic across untrusted networks; NAC decides admission, not segmentation."),
    ("network",
     "Customers of a SaaS product must be able to verify that DNS answers for its domain are authentic and untampered. Confidentiality of the lookups is not the goal. What should be deployed?",
     ["DNSSEC", "TLS on the website", "A VPN for customers", "SSH"],
     "DNSSEC signs DNS data — origin authentication and integrity, not encryption. TLS protects the web session but does nothing for the DNS resolution step before it."),
    ("network",
     "A retailer with 400 branches and a large remote workforce wants networking and security (SWG, ZTNA, firewalling) delivered together as a cloud edge service. Which architecture is this?",
     ["SASE", "SDN", "A VPN concentrator", "CASB"],
     "Converging WAN networking with cloud-delivered security functions at the edge is Secure Access Service Edge. SDN separates control/forwarding planes; a CASB governs cloud app usage only."),

    # --- Identity & Access Management ----------------------------------------
    ("iam",
     "A mobile app lets users sign in with their existing cloud account and needs to reliably learn WHO the user is. Which standard is designed for this?",
     ["OIDC", "OAuth 2.0 alone", "SAML", "SCIM"],
     "Knowing the user's identity is authentication — OIDC's purpose. OAuth alone is delegated AUTHORIZATION; treating an access token as proof of identity is the classic implementation mistake."),
    ("iam",
     "Records may be opened only when the user's department matches the record's region AND the request occurs during business hours from a managed device. Which access-control model supports this directly?",
     ["ABAC", "RBAC", "MAC", "DAC"],
     "Decisions built from attributes of the user, resource, and context (time, device) are attribute-based access control. Roles alone can't express the environmental conditions."),
    ("iam",
     "When HR marks an employee as terminated, their accounts across 30 SaaS applications should be disabled automatically. Which standard addresses this?",
     ["SCIM", "SAML", "OAuth 2.0", "LDAP"],
     "Automated provisioning and deprovisioning across domains is SCIM's job. SAML/OIDC handle the sign-in moment; they don't lifecycle the accounts."),
    ("iam",
     "Network engineers need per-command authorization and full accounting for administrative access to routers and switches. Which protocol is the BEST fit?",
     ["TACACS+", "RADIUS", "LDAP", "SSH alone"],
     "TACACS+ separates authentication/authorization/accounting and supports per-command authorization — the classic device-administration choice. RADIUS shines for network ACCESS authentication."),
    ("iam",
     "Which combination constitutes true multi-factor authentication?",
     ["A password plus a fingerprint", "A password plus a PIN", "A PIN plus a security question", "Two different passwords"],
     "MFA requires factors from DIFFERENT categories. Password, PIN and security questions are all 'something you know' — pairing them is still single-factor."),

    # --- Security Assessment & Testing ----------------------------------------
    ("assess",
     "An assessor must determine whether a US federal system's security and privacy controls are implemented appropriately. Which NIST publication guides the assessment itself?",
     ["SP 800-53A", "SP 800-53", "SP 800-171", "FIPS 199"],
     "The A suffix means Assess: 800-53A tells you how to evaluate the controls that 800-53 catalogs. 800-171 covers CUI on NONfederal systems, and FIPS 199 categorizes impact levels — neither guides a federal control assessment."),
    ("assess",
     "Security leadership wants continuous, automated verification that the IPS, EDR and SIEM detections actually fire when attack behavior occurs — not just an annual exercise. Which platform does this?",
     ["BAS", "IDS", "A vulnerability scanner", "An annual penetration test"],
     "Breach and attack simulation injects benign threat indicators on an ongoing basis specifically to trigger and validate other controls. A pentest is point-in-time, a vulnerability scanner finds flaws rather than testing detections, and the IDS is itself one of the controls under test."),
    ("assess",
     "A development team's review process runs six formal steps: planning, overview, preparation, inspection, rework and follow-up. What is this process called?",
     ["A Fagan inspection", "Agile development", "Pair programming", "A retrospective"],
     "Six formal named steps with roles and exit criteria is the Fagan inspection — the most formal end of the code-review spectrum. Pair programming is continuous informal review; a retrospective reviews the process, not the code."),
    ("assess",
     "A crypto exchange's proof of reserves shows on-chain assets exceeding the customer balances sealed in its published Merkle root. What does this attestation NOT establish?",
     ["That undisclosed liabilities do not exist", "That each customer's balance was counted in the total", "That the exchange controls the on-chain wallets", "That the counted balances were non-negative"],
     "PoR proves assets cover RECORDED liabilities at one snapshot — wallet ownership, inclusion and non-negative balances are exactly what the Merkle tree and ZK proof demonstrate. Debts outside the snapshot are invisible to it, which is why PoR is an attestation, not an audit."),
    ("assess",
     "A vulnerability report must express each finding's severity on a standardized 0–10 scale for prioritization. Which framework provides this?",
     ["CVSS", "CVE", "CWE", "SBOM"],
     "CVSS scores severity; CVE is the identifier of the vulnerability instance, CWE catalogs the weakness TYPE. The three are routinely confused on the exam."),
    ("assess",
     "During QA, an agent inside the running application observes code paths as functional tests execute and reports the vulnerable lines being exercised. Which testing approach is this?",
     ["IAST", "DAST", "SAST", "RASP"],
     "Instrumentation inside a RUNNING app during testing = interactive AST. DAST probes from outside; SAST never executes the code; RASP is production protection, not testing."),
    ("assess",
     "Management wants demonstrated proof that discovered flaws can actually be chained by an attacker to reach payroll data, under a signed authorization. What are they commissioning?",
     ["A penetration test", "A vulnerability assessment", "An SCA scan", "A CVSS review"],
     "Exploitation to demonstrate practical impact is a penetration test. A vulnerability assessment identifies and rates weaknesses but stops short of exploiting them."),
    ("assess",
     "A popular open-source library is found to be backdoored. Which artifact lets each product team answer 'do we ship this component?' within minutes?",
     ["The SBOM", "A fresh DAST scan", "The CVE feed", "The WAF logs"],
     "A software bill of materials is the standing inventory of components per product — exposure is a lookup. Rescanning everything works eventually; the SBOM answers immediately."),
    ("assess",
     "Which control lives INSIDE the application in production and can block an injection attempt while the code is running?",
     ["RASP", "A WAF", "IAST", "SAST"],
     "Runtime application self-protection is embedded in the app in production. The WAF is the external sibling (it filters HTTP before the app); IAST is the testing-time twin of the same instrumentation idea."),

    # --- Security Operations ----------------------------------------------------
    ("ops",
     "After malware on an engineer's everyday laptop led to unauthorized transactions in production, the post-incident review recommends that privileged operations never again be performed from a device that also runs email and a browser. What is being recommended?",
     ["A privileged access workstation", "A bastion host", "Full-disk encryption on all laptops", "An EDR agent on the engineer's laptop"],
     "A hardened, single-purpose PAW keeps privileged sessions off phishable daily-driver machines. A bastion/jump host controls the network path — valuable, but the recommendation targets the DEVICE the admin types on; FDE protects data at rest, and EDR detects rather than prevents the exposure."),
    ("risk",
     "Rather than buying cyber insurance, a firm maintains a dedicated, pre-funded reserve earmarked to make customers whole after a security incident. Which risk response is this?",
     ["Retention, with explicit risk financing", "Transfer", "Avoidance", "Mitigation"],
     "The firm keeps the risk and pre-funds the impact — retention backed by a financing vehicle. Insurance would transfer it; mitigation would reduce likelihood or impact; avoidance would exit the activity entirely."),
    ("ops",
     "A SOC drowning in repetitive alerts wants enrichment, ticketing and containment steps executed automatically from playbooks. Which capability should be added?",
     ["SOAR", "A second SIEM", "UEBA", "NDR"],
     "Orchestrating and automating response workflows is SOAR. The SIEM aggregates and correlates — it raises the alerts that SOAR then handles."),
    ("ops",
     "A service account that has logged in from one server for years suddenly authenticates at 03:00 from a new country. Which technology is DESIGNED to flag this?",
     ["UEBA", "An IDS signature", "DLP", "NAC"],
     "Deviation from a learned behavioral baseline is exactly user and entity behavior analytics. Signature-based tools can't flag activity that is individually well-formed."),
    ("ops",
     "An incident team has just isolated the affected servers from the network. According to the standard incident-response lifecycle, what comes NEXT?",
     ["Eradication", "Recovery", "Lessons learned", "Detection"],
     "The order is Detection/Analysis → Containment → Eradication → Recovery → Lessons Learned. After containing, you remove the adversary and artifacts before restoring service."),
    ("ops",
     "A threat-intel report lists file hashes, C2 IP addresses and malicious domain names from a recent campaign. What are these?",
     ["IOCs", "TTPs", "CVEs", "KRIs"],
     "Observable artifacts of compromise are indicators (IOCs). TTPs describe the adversary's METHODS — the distinction is 'evidence you can match' versus 'behavior you must understand'."),
    ("ops",
     "A security team wants one vendor-integrated layer that correlates detections and drives response across endpoints, email, identity and cloud workloads. What are they describing?",
     ["XDR", "EDR", "NDR", "A SIEM"],
     "Extending detection AND response across multiple integrated telemetry layers is XDR. A SIEM aggregates logs broadly but is analytics-first; EDR/NDR cover single layers."),

    # --- Software & Cloud Security ----------------------------------------------
    ("cloud",
     "In the IDEAL process-improvement model, during which phase does the organization develop, test, refine and implement its solutions?",
     ["Acting", "Establishing", "Diagnosing", "Learning"],
     "Acting is where talk becomes work: build, test, refine, deploy. Diagnosing assessed the current state, Establishing planned and resourced the changes, and Learning closes the loop afterwards. The model's name spells its five phases."),
    ("cloud",
     "A developer notes that calling .render() on a Chart, a Table and a Map object produces three different results from the identical call. Which OOP term names this property?",
     ["Polymorphism", "Inheritance", "Cohesion", "Instantiation"],
     "One message, different behaviors depending on the receiving object = polymorphism — it is a property you observe, never a container of methods. Inheritance passes methods DOWN a hierarchy; cohesion rates a module's internal focus; instantiation creates objects from a class."),
    ("cloud",
     "A code reviewer praises a module because everything in it serves one purpose and it barely depends on other modules. Which combination is being described?",
     ["High cohesion and low coupling", "Low cohesion and high coupling", "High cohesion and high coupling", "Low cohesion and low coupling"],
     "One purpose per module = HIGH cohesion; few dependencies on other modules = LOW coupling. That pairing is the textbook definition of good design — and the exam loves flipping one of the two words in the distractors."),
    ("cloud",
     "A defence logistics database returns an unclassified cargo manifest to ordinary users and a classified one to cleared users — for the same primary key. Which technique is in use?",
     ["Polyinstantiation", "Polymorphism", "Database views", "Noise and perturbation"],
     "Multiple rows for one key at different classification levels is polyinstantiation: the cover story defeats inference, because an error or empty row would itself leak that something classified exists. Views filter columns/rows but can't present two truths for one key; polymorphism is OOP, not databases."),
    ("cloud",
     "In which cloud service model is the CUSTOMER responsible for patching the guest operating system?",
     ["IaaS", "PaaS", "SaaS", "None — the CSP always patches the OS"],
     "IaaS hands you infrastructure; everything from the guest OS up is yours. In PaaS the platform (and OS) is managed for you; in SaaS the entire stack is."),
    ("cloud",
     "At which point in the SDLC is a security flaw CHEAPEST to correct?",
     ["During requirements and design", "During implementation", "During testing", "After release, via patching"],
     "Cost to fix rises steeply through the lifecycle — the premise behind threat modeling at design time and 'shift left' generally."),
    ("cloud",
     "A team wants automated security gates on every merge request, before code is deployed by the pipeline. Which tool pairing belongs in that gate?",
     ["SAST and SCA", "DAST and RASP", "WAF and EDR", "CVSS and CVE"],
     "Static analysis and dependency scanning run on code and build artifacts — perfect for merge-time gates. DAST needs a running app and RASP/WAF/EDR are runtime protections, not pipeline checks."),
    ("cloud",
     "Developers need the community's canonical, regularly updated list of the most critical web-application risks to prioritize secure-coding training. Where should they start?",
     ["The OWASP Top 10", "NIST SP 800-53", "The CWE database", "PCI DSS"],
     "OWASP maintains the Top 10 web-app risk list. CWE is the exhaustive weakness catalog (reference, not a priority list); 800-53 is a control catalog; PCI DSS is a payment-card standard."),
    ("cloud",
     "A public partner-facing API is being launched. Which control should be treated as the FIRST line of defense?",
     ["Strong authentication and authorization on every endpoint", "Keeping endpoint URLs undocumented", "Relying on TLS to protect the interface", "Rate limiting alone"],
     "APIs are direct doors to data: authn/authz per endpoint is foundational. Obscurity is not access control, TLS only protects data in transit, and rate limiting throttles abuse but doesn't decide WHO may act."),

    # --- Batch 1 from Wiley-miss review (original questions, 2026-09-26) -----
    ("risk",
     "A consultancy runs a threat-modeling exercise that starts from business objectives, walks seven defined stages including attack simulation, and ends with countermeasures proportionate to the value of the assets protected. Which methodology is this?",
     ["PASTA", "STRIDE", "DREAD", "VAST"],
     "Seven stages + risk-centric + countermeasures weighted by asset value = PASTA. STRIDE categorizes threats into six classes, DREAD rates found threats on five factors, and VAST integrates threat modeling into Agile at scale."),
    ("cloud",
     "An engineering organization has documented, organization-wide development processes but has not yet begun measuring them quantitatively. Which SW-CMM level has it reached?",
     ["Defined", "Repeatable", "Managed", "Optimizing"],
     "Level 3 Defined = processes documented org-wide. Level 4 Managed adds quantitative measurement — the classic trap pair. Repeatable (2) is project-level discipline; Optimizing (5) is continuous improvement."),
    ("crypto",
     "In the protection ring model, where does the operating-system kernel execute?",
     ["Ring 0", "Ring 3", "Ring 2", "The outermost ring"],
     "Ring 0 is the innermost, most privileged ring — the kernel. User applications run in Ring 3, the least privileged, outermost ring."),
    ("crypto",
     "Arranging multiple DIFFERENT security controls in series, so that an asset remains protected when any single control fails, describes which principle?",
     ["Defense in depth", "Zero Trust", "Least privilege", "Separation of duties"],
     "Layered controls in series = defense in depth (related vocabulary: layering, zones, compartments, protection rings). Zero Trust removes implicit network trust, least privilege minimizes rights, and SoD divides duties between people."),

    # --- Security models (deep-dive companion questions) ---------------------
    ("crypto",
     "A classified system must prevent users from reading documents above their clearance AND prevent high-level processes from writing into lower-classification files. Which model enforces exactly this?",
     ["Bell-LaPadula", "Biba", "Clark-Wilson", "Brewer-Nash"],
     "No read up + no write down protecting CONFIDENTIALITY = Bell-LaPadula. Biba is the integrity mirror image (no read down / no write up); Clark-Wilson uses transactions; Brewer-Nash handles conflicts of interest."),
    ("crypto",
     "Under the Biba model, which action is a subject FORBIDDEN to perform?",
     ["Reading data at a lower integrity level", "Reading data at a higher integrity level", "Writing to a lower integrity level", "Accessing data at its own integrity level"],
     "Biba protects integrity: no read DOWN (don't consume less-trustworthy data) and no write UP. Reading up and writing down are both allowed — the arrows are Bell-LaPadula's inverted."),
    ("crypto",
     "An accounting platform requires that users never modify ledger data directly — every change must pass through certified programs, with duties split across roles. Which model describes this design?",
     ["Clark-Wilson", "Biba", "Bell-LaPadula", "Take-Grant"],
     "Subject → Transformation Procedure → Constrained Data Item (the access triple), well-formed transactions and separation of duties = Clark-Wilson. Biba also protects integrity but through levels, not vetted transactions."),
    ("crypto",
     "A consultancy's document system automatically blocks an analyst from opening Bank B's files once they have accessed files from competing Bank A. Which model is at work?",
     ["Brewer-Nash", "Bell-LaPadula", "Graham-Denning", "Noninterference"],
     "Access decided dynamically by prior history within conflict-of-interest classes is Brewer-Nash (the Chinese Wall). It is the only classic model whose permissions change based on what the user already touched."),

    # --- Batch 2: physical security (Domain 3), from Wiley-miss review -------
    ("crypto",
     "Before siting a new data center, the design team documents every dependency that mission-critical operations rely on — power feeds, HVAC, carrier connectivity, water. Which method are they performing?",
     ["Critical path analysis", "Risk analysis", "Business impact analysis", "Asset inventory"],
     "Mapping mission-critical processes to ALL supporting elements during facility design is critical path analysis. Risk analysis weighs threats against consequences, a BIA quantifies disruption impact on the business, and inventory merely catalogs assets."),
    ("crypto",
     "Which of the following is NOT one of first-generation CPTED's core strategies?",
     ["Natural reinforcement training", "Natural surveillance", "Natural access control", "Territorial control"],
     "First-generation CPTED has four strategies: natural access control, natural surveillance, territorial control, and image/milieu. “Natural reinforcement training” is an invented distractor — plausible-sounding non-terms are the pattern in CPTED questions."),
    ("crypto",
     "A server room requires water-based fire suppression, but an accidental discharge would be nearly as damaging as a fire. Which system should be installed?",
     ["Preaction", "Wet pipe", "Dry pipe", "Deluge"],
     "Preaction systems arm in two stages — a detector must first charge the pipes, then a sprinkler head must trigger — so a single false alarm releases nothing. Wet, dry and deluge systems all discharge on a single trigger."),
    ("crypto",
     "In the functional order of physical security controls, what should a control layer do IMMEDIATELY AFTER an intrusion has been detected?",
     ["Delay the intruder until response is possible", "Deny further access", "Deter the intruder", "Decide on a response"],
     "The order is Deter → Deny → Detect → Delay → Determine → Decide. After detection, controls buy time (Delay) while the situation is assessed (Determine) and a response is chosen (Decide); deterrence and denial precede detection."),

    # --- Batch 3: network & endpoint defense (Domains 4/7) -------------------
    ("ops",
     "A security team wants endpoint agents that record process activity, stream events to a cloud machine-learning engine, and catch malware that slips past traditional antivirus — with automated response actions. Which technology matches?",
     ["EDR", "NGFW", "WAF", "SIEM"],
     "Endpoint agents + central/cloud ML analysis + “beyond antivirus” + response = EDR. An NGFW protects the network path, a WAF filters web-app traffic, and a SIEM aggregates logs but has no endpoint agent doing response."),
    ("network",
     "Which characteristic of multilayer protocol stacks is BOTH a core benefit AND a recognized security risk?",
     ["Encapsulation", "Throughput", "Logical addressing", "Header checksums"],
     "Encapsulation gives flexibility and lets protection like TLS wrap traffic — but it also enables covert channels, filter bypass and tunneling across segmentation boundaries. The other options are benefits without that dual edge."),
    ("network",
     "A high-value database server is isolated in its own microsegment, and every transaction crossing the zone boundary is filtered. Which device class enforces this INSIDE the LAN?",
     ["An internal segmentation firewall", "A perimeter NGFW", "A WAF", "A NAC appliance"],
     "Microsegmentation is enforced by internal segmentation firewalls (ISFWs) — physical or virtual — filtering east-west traffic between internal zones. Perimeter devices face north-south traffic; NAC decides admission, not inter-zone filtering."),
    ("network",
     "A media company deploys replica servers in dozens of data centers worldwide so customers stream video with low latency and high availability. What are they building?",
     ["A CDN", "A VPN mesh", "An SDN", "A SASE deployment"],
     "Distributed replicas serving content near users = content delivery network. VPNs tunnel traffic, SDN separates control from forwarding, SASE delivers security at the edge — none of them replicate content."),
    ("network",
     "An attacker on the office LAN sends unsolicited, gratuitous replies so that hosts update their IP-to-hardware-address tables and route traffic through the attacker's machine. Which attack is this?",
     ["ARP poisoning", "MAC spoofing", "MAC flooding", "DNS poisoning"],
     "Gratuitous replies corrupting IP→MAC mappings = ARP poisoning. MAC spoofing falsifies the attacker's own hardware address, MAC flooding overloads the switch's CAM table, and DNS poisoning corrupts name resolution, not layer-2 mappings."),
    ("network",
     "Public-facing web and mail servers must be reachable from the internet, but a compromise of those hosts must not expose the internal network. Where should they be placed?",
     ["In a screened subnet (DMZ)", "On the intranet", "On an extranet", "In a honeynet"],
     "A screened subnet/DMZ buffers the private network from the internet while hosting public services. The intranet IS the private network, an extranet serves selected partners, and a honeynet is a decoy — you never put production services in it."),

    # --- Batch 4: remote access & IAM attacks (Domains 4/5) ------------------
    ("network",
     "A compliance audit flags a legacy telecommuting link because logon credentials cross the wire with no encryption or protection whatsoever. Which authentication protocol is in use?",
     ["PAP", "CHAP", "EAP-TLS", "RADIUS"],
     "PAP transmits usernames and passwords in cleartext. CHAP never sends the password (challenge/response), EAP-TLS uses certificates, and RADIUS is a AAA service that supports credential protection."),
    ("network",
     "Which of the following is NOT a real EAP method?",
     ["EAP-VPN", "PEAP", "EAP-TTLS", "EAP-FAST"],
     "More than 40 EAP methods exist — PEAP, EAP-TLS, EAP-TTLS, EAP-FAST, EAP-SIM, EAP-MD5, LEAP, EAP-POTP among them. “EAP-VPN” is an invented name; plausible-sounding fakes are the pattern in EAP questions."),
    ("network",
     "A carrier provisions a logical circuit that always exists and simply waits for the customer to transmit data. What is this?",
     ["A PVC", "An SVC", "A VPN", "A VLAN"],
     "Permanent virtual circuit = always established, like a virtual leased line. An SVC is built for each session and torn down afterwards; VPNs tunnel over untrusted networks; VLANs segment broadcast domains."),
    ("iam",
     "Users on three workstations suddenly cannot authenticate to Kerberos, while other machines are fine. Their system clocks are found to be 20 minutes off. What is the BEST fix?",
     ["Synchronize all hosts to an NTP server", "Deploy NAC health checks", "Reissue machine certificates", "Migrate the realm to SAML"],
     "Kerberos tolerates roughly five minutes of clock skew; drifted clocks fail authentication. NTP synchronization fixes the root cause — the other options address problems this scenario doesn't have."),
    ("iam",
     "An attacker captures an NTLM credential artifact and uses it to authenticate to remote servers as an administrator — without ever learning the password. Which attack is this?",
     ["Pass the hash", "Golden ticket", "Pass the ticket", "Rainbow table"],
     "Reusing an NTLM hash directly = pass the hash. Golden and pass-the-ticket attacks manipulate KERBEROS tickets, and rainbow tables crack password hashes offline — they don't reuse them live."),
    ("iam",
     "Investigators find forged ticket-granting tickets minted after the attackers compromised the KRBTGT service account. Which authentication system was exploited?",
     ["Kerberos", "RADIUS", "SAML", "OIDC"],
     "TGTs and the KRBTGT account exist only in Kerberos — a golden-ticket attack. RADIUS, SAML and OIDC have no ticket-granting machinery."),
    ("iam",
     "A cloud provider's single sign-on issues JSON Web Tokens that carry authentication results and user-profile claims. Which standard is this?",
     ["OIDC", "SAML", "RADIUS", "TLS"],
     "JWTs carrying identity claims = OpenID Connect. SAML uses XML assertions, RADIUS is a AAA protocol, and TLS protects transport — it doesn't do SSO."),

    # --- Batch 5: governance & threat-modeling enumerations ------------------
    ("risk",
     "During reduction analysis (decomposition) of an application, which of the following is NOT one of the five key concepts to identify?",
     ["Patch and update versions", "Trust boundaries", "Dataflow paths", "Privileged operations"],
     "Decomposition identifies trust boundaries, dataflow paths, input points, privileged operations, and details about security stance and approach. Patch management matters — it just isn't a decomposition component, which is exactly how the exam traps you."),
    ("risk",
     "Which of the following is one of COBIT's six key principles for the governance of enterprise IT?",
     ["End-to-End Governance System", "Maintaining Authenticity and Accountability", "Defense in Depth", "Least Privilege"],
     "The six COBIT principles: Provide Stakeholder Value, Holistic Approach, Dynamic Governance System, Governance Distinct from Management, Tailored to Enterprise Needs, and End-to-End Governance System. Generic security virtues phrased plausibly are the standard distractors."),

    # --- Batch 6: US laws, baselines, DRM -------------------------------------
    ("risk",
     "The new compliance lead at a credit union must govern how the institution collects, shares and protects customers' personal financial information. Which law applies MOST directly?",
     ["GLBA", "SOX", "HIPAA", "FISMA"],
     "Financial institution + customer personal information = Gramm-Leach-Bliley. SOX governs public-company financial reporting integrity, HIPAA covers health information, and FISMA covers federal agencies."),
    ("data",
     "Before hardening a new application server, an engineer works through the full baseline catalog and keeps only the controls that apply to this system. What is this activity called?",
     ["Scoping", "Tailoring", "Standards selection", "Imaging"],
     "Selecting the applicable subset of baseline controls is scoping. Tailoring then aligns those controls to the organization's mission; standards selection adopts an externally mandated baseline; imaging clones a finished configuration."),
    ("data",
     "Which of the following is NOT a technique used by digital rights management (DRM) solutions?",
     ["Virtual licensing", "Persistent online authentication", "Automatic expiration", "Continuous audit trail"],
     "DRM's real techniques are persistent online authentication, automatic expiration, and continuous audit trails. “Virtual licensing” is an invented term — the plausible-fake pattern again."),

    # --- Batch 7: PKI standards, tools, DoS, incident steps, SOC --------------
    ("crypto",
     "Which signature algorithm is NOT approved by the Digital Signature Standard under FIPS 186-5?",
     ["ElGamal", "RSA", "ECDSA", "EdDSA"],
     "FIPS 186-5 approves exactly three: RSA, ECDSA and EdDSA. ElGamal never made the standard, and even the original DSA was dropped in 186-5 — RSA feels like the odd one out but is approved."),
    ("crypto",
     "A Windows administrator exports a certificate TOGETHER WITH its private key into a password-protected binary file. Which format is she using?",
     ["PFX", "PEM", "P7B", "CER"],
     "PFX/P12 is the Windows binary format that bundles certificate + private key under a password. PEM and P7B are text formats, and P7B never contains private keys."),
    ("assess",
     "A tester's FIRST step is finding live hosts and their open ports across a subnet, before any vulnerability scanning begins. Which tool fits?",
     ["Nmap", "Nessus", "Metasploit", "Wireshark"],
     "Discovery is Nmap's job. Nessus rates vulnerabilities on hosts you've already found, Metasploit exploits them, and Wireshark passively captures traffic — four tools, four distinct verbs."),
    ("ops",
     "A SOC analyst hunting for evidence of a Smurf attack should filter the logs on which protocol?",
     ["ICMP", "UDP", "TCP", "SNMP"],
     "Smurf = spoofed ICMP echo to broadcast addresses. Its UDP sibling is Fraggle, and SYN floods abuse TCP — the attack-to-protocol mapping is the entire question."),
    ("ops",
     "In ISC2's seven incident-management steps, what comes IMMEDIATELY AFTER Mitigation?",
     ["Reporting", "Recovery", "Remediation", "Lessons Learned"],
     "ISC2's order: Detection → Response → Mitigation → Reporting → Recovery → Remediation → Lessons Learned. After containing the damage (Mitigation), you report to stakeholders before restoring and fixing root causes."),
    ("assess",
     "A prospective customer wants evidence that your controls actually OPERATED effectively over the past year, not merely that they were well designed. Which report should they request?",
     ["SOC 2 Type II", "SOC 2 Type I", "SOC 1 Type II", "SOC 3"],
     "Type II attests operating effectiveness over a period; Type I only evaluates design at a point in time. SOC 2 covers security (Trust Services Criteria); SOC 1 is for financial-reporting controls; SOC 3 is the public summary."),
    ("assess",
     "A payroll service's customers need assurance for THEIR OWN financial-statement audits. Which report covers the payroll provider's relevant controls?",
     ["SOC 1", "SOC 2", "SOC 3", "An SBOM"],
     "Controls that affect customers' financial reporting = SOC 1. SOC 2 addresses security and availability concerns, SOC 3 is the public seal, and an SBOM is a software inventory — different world."),

    # --- Batch 8: TCB & models design machinery (Chapter 8 / Domain 3) -------
    ("crypto",
     "Within the trusted computing base, which component validates every access to every object BEFORE the access is granted?",
     ["The reference monitor", "The security kernel", "The security perimeter", "A TCB partition"],
     "Validation-before-access is the reference monitor — the concept. The security kernel is that concept implemented in code; the perimeter is the TCB's boundary; “TCB partition” is invented."),
    ("crypto",
     "The access-validation concept carries one name in theory but takes a different name once implemented in an operating system. What is the implementation called?",
     ["The security kernel", "The reference monitor", "The trusted path", "Ring 0"],
     "Theory: reference monitor. Implementation: security kernel — the TCB components that actually perform the validation. Ring 0 is where it typically runs, not what it is called."),
    ("crypto",
     "Which pair of security models is built directly on the state machine model?",
     ["Bell-LaPadula and Biba", "Bell-LaPadula and Take-Grant", "Biba and Clark-Wilson", "Clark-Wilson and Brewer-Nash"],
     "BLP and Biba are both state-machine (and information-flow) models — secure in every state and transition. Clark-Wilson works through transactions and Take-Grant through graph rules; neither is state-machine based."),
    ("crypto",
     "Biba's simple integrity property forbids reading down. Which action does it IMPLICITLY permit?",
     ["Reading up", "Writing up", "Writing down", "Reading at any level"],
     "The “implied meaning” trick: flip the forbidden direction, keep the verb. No read DOWN implies read UP is allowed. (Writing is the ★ property's business, not the simple property's.)"),
    ("crypto",
     "Which of the following is NOT one of the four authorization decisions an authorizing official can issue under the RMF?",
     ["Mutual authorization", "Authorization to operate", "Authorization to use", "Denial of authorization"],
     "The four real decisions: authorization to operate, common control authorization, authorization to use, and denial of authorization. “Mutual”, “verified” and “transfer” authorizations are invented."),
    ("crypto",
     "A policy review lists candidate secure design principles. Which of the following is NOT a secure design principle?",
     ["People are the weakest link", "Least privilege", "Secure defaults", "Separation of duties"],
     "People can cause breaches, but they are also a key component of a successful security solution — “weakest link” is a slogan, not a design principle. The same goes for “security is always top priority” (business objectives bound security) and “risk should be eliminated” (it can only be reduced, transferred, avoided or accepted)."),
    ("crypto",
     "An organization is evaluating containerization products. Which of the following is a feature or capability of SOME containerization solutions?",
     ["Running multiple concurrent applications within a single container", "Operating a full guest OS within each instance", "Automating the processes of network monitoring and response", "Installing a hypervisor onto the bare metal of the host"],
     "Containerization eliminates OS duplication — some products allow several concurrent apps per container and tunable interaction between containers. A full guest OS per instance and a bare-metal hypervisor describe virtual machines; automated network monitoring and response is software-defined visibility (SDV)."),
    ("crypto",
     "A new burglar-alarm system detects perimeter breaches and internal movement. Which of the following is NOT a typical type of alarm?",
     ["Preventive", "Deterrent", "Repellent", "Notification"],
     "Alarms are triggered in RESPONSE to a detected intrusion, so a “preventive alarm” cannot exist. The real trio: deterrent (engages locks and barriers), repellent (sirens and lights drive the intruder off) and notification (silently alerts responders while recording)."),
    ("network",
     "Remote workers' connections must be protected by a standard VPN solution. Which of the following protocols can be used as a VPN?",
     ["IPsec", "Kerberos", "Signal", "S-RPC"],
     "IPsec — along with TLS and SSH — can carry general traffic in a protected tunnel. Kerberos is ticket-based authentication/SSO, Signal is end-to-end encrypted messaging and voice, and S-RPC authenticates remote procedure calls; all secure, none a VPN."),
    ("network",
     "Which of the following technologies is NOT specifically defined as part of 802.11 wireless networking?",
     ["802.1X", "WPA3", "SAE", "WPS"],
     "802.1X is an IEEE PORT-authentication standard used as widely on wired networks as wireless — it underpins enterprise (ENT) authentication but is not an 802.11 technology. WPA3, SAE, 802.11i and WPS are all defined as part of wireless networking."),
    ("network",
     "You must build a capture filter that collects only IPsec negotiations. At which OSI layer does IPsec operate?",
     ["Network (Layer 3)", "Session (Layer 5)", "Transport (Layer 4)", "Data Link (Layer 2)"],
     "IPsec protects IP itself, so it lives at Layer 3. L2TP and PPTP are the Data Link VPNs, TLS and SSH work at the Transport layer, and TCP/IP networks have no actual Session layer — that function, when performed at all, is handled by TCP."),
    ("iam",
     "Before opening an online account, a bank asks the applicant about past addresses and current loan payment amounts drawn from their credit file. What is this process?",
     ["Knowledge-based authentication", "A cognitive password", "Registration", "Two-factor authentication"],
     "Questions built from AUTHORITATIVE RECORDS of the person's history = KBA, used for identity proofing at account creation. A cognitive password asks questions the user previously answered themselves; registration is internal enrollment (often collecting biometrics); 2FA combines two factor types."),
    ("iam",
     "Firewalls apply a set of administrator-defined filters to all traffic. Which access control model does this describe?",
     ["Rule-based access control", "Mandatory access control (MAC)", "Role-based access control (RBAC)", "Attribute-based access control (ABAC)"],
     "Global rules applied to every subject alike — a firewall ACL — is RULE-based access control. MAC decides from classification labels, RBAC from role membership, ABAC from attributes and context; a filter set has none of those."),
    ("assess",
     "A tester lists the ways an attacker might exploit an application, then works through each scenario attacking the application. What type of testing is this?",
     ["Misuse case testing", "Fagan inspection", "Synthetic transactions", "Test coverage analysis"],
     "Enumerate the abuse cases, then attempt each exploit = misuse case testing. Fagan inspection is a formal six-step code review with no execution, synthetic transactions are scripted benign operations, and coverage analysis measures how much code the tests touch."),
    ("cloud",
     "A security engineer is building a security awareness and training programme for developers. Under SAMM, which business function is this?",
     ["Governance", "Operations", "Verification", "Design"],
     "Education and guidance — training, awareness, organization and culture — sit under GOVERNANCE in the Software Assurance Maturity Model. Operations covers incident and environment management of the running software; Verification is testing; Design is requirements and architecture."),
    ("crypto",
     "A department of eight people is implementing an asymmetric encryption algorithm. How many keys are required to fully implement it?",
     ["16", "28", "56", "8"],
     "Asymmetric = one key PAIR per participant: 2n = 2 × 8 = 16. The classic wrong answer is 28 — that's n(n−1)/2, the SYMMETRIC formula (a shared key per pair). Read which system the stem names before picking a formula."),
    ("crypto",
     "Encryption workload must be distributed across multiple processors in parallel. Which cryptographic mode best supports this?",
     ["Galois/Counter Mode (GCM)", "Cipher Block Chaining (CBC)", "Cipher Feedback (CFB)", "Electronic Codebook (ECB)"],
     "Counter modes break the operation into independent per-block steps, and GCM adds authentication on top — parallel AND secure. CBC and CFB chain each block to the previous one, which forbids parallel encryption; ECB parallelizes but leaks patterns (identical blocks encrypt identically)."),
    ("crypto",
     "Before relying on a server's digital certificate, which of the following does a client NOT need to verify?",
     ["That the sender's public key is valid", "That the CA's digital signature on the certificate is authentic", "That the certificate has not expired", "That the certificate has not been revoked"],
     "The three real checks are CA signature, expiry and revocation status. The public key is the PAYLOAD — once the certificate is trusted, the key inside it is accepted; you never validate it separately first."),
    ("crypto",
     "Which of the following is NOT an element defined under the Clark-Wilson model?",
     ["Redundant commit statement", "Constrained data item", "Transformation procedure", "Integrity verification procedure"],
     "Clark-Wilson defines CDIs, UDIs, TPs and IVPs, connected by the subject→TP→CDI access triple. A “redundant commit statement” is database-replication vocabulary — it only sounds at home in an integrity model."),
    ("crypto",
     "Three applications run on a dual-core single-processor multitasking system; one manages two threads, the others one each. How many application threads are RUNNING on the processor at any given time?",
     ["Two", "One", "Three", "Four"],
     "Simultaneously executing threads = number of cores. A dual-core chip runs exactly two threads at any instant — one per core — regardless of how many threads exist (four here) or how many applications are open. Single-core would be one."),
    ("crypto",
     "Which of the following is an example of a DCE interface definition language (IDL) framework?",
     ["CORBA", "SAML", "OCSP", "SQL"],
     "The IDL family — RPC, CORBA, DCOM — defines how clients invoke code across a distributed system. SAML is authentication federation, OCSP checks certificate revocation, and SQL queries databases; none defines distributed interfaces."),
    ("network",
     "An encapsulation protocol lets switch-created network segments be stretched across subnets and geographic distances to connect satellite offices. What technology is this?",
     ["VXLAN", "SD-WAN", "SDN", "VPN"],
     "Virtual eXtensible LAN encapsulates Layer-2 segments so a VLAN can span sites. SD-WAN manages connectivity between distant locations over WAN links, SDN is centrally programmable networking, and a VPN is a secured tunnel — none of them stretches switch-created segments."),
    ("network",
     "Which of the following statements about network access control (NAC) is TRUE?",
     ["A dissolvable NAC agent can be set to run once and then terminate", "An agentless NAC can automatically quarantine and resolve security issues on hosts", "NAC requires that all systems authenticate using IEEE 802.1X", "Preadmission NAC evaluates device behaviour after it has connected"],
     "Dissolvable agents are downloaded per session, run once and vanish. Agentless NAC only scans from the network — an administrator must resolve issues manually. 802.1X is commonly USED by NAC but never required. Preadmission checks happen BEFORE the device may communicate; behaviour-after-connection is postadmission."),
    ("network",
     "Which component of IPsec enables a host to maintain multiple simultaneous VPNs?",
     ["ISAKMP", "AH", "ESP", "SKEME"],
     "ISAKMP manages the negotiated keys through SECURITY ASSOCIATIONS — each SA is an agreed method of authentication and encryption, and having several SAs is what supports multiple simultaneous VPNs. AH gives integrity, ESP confidentiality, SKEME exchanges keys; none of them organizes SAs."),
    ("risk",
     "A risk assessment evaluates third-party connectivity. Which of the following is NOT a third-party connectivity area of concern?",
     ["Business branch VPN links", "Business partnerships", "Cloud services", "Telecommuting"],
     "Third-party concern areas are where an actual OUTSIDER connects to your on-premises network: partners, cloud providers, teleworkers. VPN links between your own branches connect you to yourself — however the tunnel is built, no third party is involved."),
    ("crypto",
     "A CISO tracks KPIs for physical security. Which of the following is NOT a relevant physical-security KPI?",
     ["Number of compromised accounts", "Number of successful intrusions", "Time to detect incidents", "Number of false positive alarms"],
     "Compromised accounts measure LOGICAL security. The physical list: successful intrusions and disruptions, unsuccessful incidents, time to detect, time to respond, organizational impact, and false positives. Session disconnects, transmission errors and transactions-per-minute are network statistics — same trap, different clothes."),
    ("iam",
     "An administrator reviews the HR server's log files looking for malicious activity. What is the PURPOSE of this activity?",
     ["Accountability", "Audit trails", "Authentication", "Identification"],
     "Reviewing logs and tracking user activity holds people responsible — accountability. The audit trails are the body of DATA the review works through, not its purpose; identification and authentication happened long before the log was written."),
    ("iam",
     "Benefit-plan management is outsourced, and management wants minimal administrative workload for user access. Which solution fits?",
     ["Just-in-time provisioning", "Sending a database of accounts to the provider", "Duplicating the accounts internally", "Creating a trust between the organizations"],
     "JIT provisioning creates each account automatically the first time the employee reaches the benefits site — near-zero admin. Database exports need both sides to work, duplication grants no access to the other site, and a trust alone creates no accounts either."),
    ("iam",
     "A company provides online training to employees of many different organizations, who log on at their own sites and reach the training without logging on again. What system is this?",
     ["Cloud-based identity management", "On-premises identity management", "Hybrid identity management", "Credential management"],
     "Serving users from MULTIPLE organizations through one shared sign-on service is cloud-based identity management (IDaaS). On-premises serves one organization, hybrid combines both, and credential management merely stores credentials."),
    ("iam",
     "An access control model assigns access based on a user's need to know combined with organizational policies. Which model is this?",
     ["Mandatory access control (MAC)", "Attribute-based access control (ABAC)", "Discretionary access control (DAC)", "Risk-based access control"],
     "Need-to-know enforced under central organizational policy is MAC — clearances and labels decide, owners cannot override. ABAC decides from attributes and context, DAC from the owner's wishes, risk-based from the evaluated environment and situation."),
    ("assess",
     "Which application security testing technique uses scripts of routine activity with known results and compares actual outcomes against them?",
     ["Synthetic transactions", "Fuzzing", "Static testing", "Mutation testing"],
     "Scripted routine activity with KNOWN expected results = synthetic transactions, a dynamic verification technique. Fuzzing also executes, but feeds random/invalid input with no expectations script; mutation testing alters the code; static testing never runs the application."),
    ("assess",
     "What is the FINAL step of the Fagan inspection process?",
     ["Follow-up", "Rework", "Inspection", "Overview"],
     "The six steps end with follow-up — verifying the fixes from rework and deciding whether re-inspection is needed. Full order: Planning, Overview, Preparation, Inspection, Rework, Follow-up."),
    ("risk",
     "A CPA conducting an administrative investigation of an ISC2-certified professional at another organization uncovers possible ethics violations. Under which Code of Ethics canons does the CPA have standing to complain?",
     ["I, II and IV", "I and II only", "III and IV only", "All four canons"],
     "Canons I and II accept complaints from any member of the public; Canon IV accepts them from other professionals, which a CPA is. Canon III is reserved for an employer or contracted organization — an outside investigator is neither."),
    ("network",
     "A sniffer shows unfamiliar TFTP and IGMP packets working together. Which communications concept links the two?",
     ["Multicasting", "Simplex", "Analog transmission", "Broadband"],
     "IGMP registers a host's multicast group membership, and TFTP can host or cache the datasets a multicast stream delivers to multiple specific recipients. Simplex is one-way direction, and analog/broadband describe the transmission medium — none of them connects these two protocols."),
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

# Official CISSP domains (current ISC2 exam outline) mapped onto our category
# keys — the shared source for glossary tags, flashcard filters and the mind map.
DOMAINS = [
    {"number": 1, "key": "risk",    "name": "Security and Risk Management",          "weight": 16},
    {"number": 2, "key": "data",    "name": "Asset Security",                        "weight": 10},
    {"number": 3, "key": "crypto",  "name": "Security Architecture and Engineering", "weight": 13},
    {"number": 4, "key": "network", "name": "Communication and Network Security",    "weight": 13},
    {"number": 5, "key": "iam",     "name": "Identity and Access Management (IAM)",  "weight": 13},
    {"number": 6, "key": "assess",  "name": "Security Assessment and Testing",       "weight": 12},
    {"number": 7, "key": "ops",     "name": "Security Operations",                   "weight": 13},
    {"number": 8, "key": "cloud",   "name": "Software Development Security",         "weight": 10},
]
assert {d["key"] for d in DOMAINS} == set(_cat_labels), "domain keys must match categories"

_data = {
    "version": 1,
    "generated": _dt.now(_tz.utc).isoformat(timespec="seconds"),
    "categories": _cat_labels,
    "domains": DOMAINS,
    "terms": _json_terms,
    "scenarios": _json_scenarios,
    "quiz": _json_quiz,
}
_out = (_Path(_settings.BASE_DIR) / "output" / "sites" / site.slug
        / "assets" / "data" / "cissp-glossary.json")
_out.parent.mkdir(parents=True, exist_ok=True)
_out.write_text(_json.dumps(_data, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", _out, "| terms:", len(_json_terms), "| scenarios:", len(_json_scenarios),
      "| quiz:", len(_json_quiz))
