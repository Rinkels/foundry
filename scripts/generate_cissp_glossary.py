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
     "ISACA framework for governance and management of enterprise information and technology.", "ext", None),
    ("risk", "SABSA", "Sherwood Applied Business Security Architecture",
     "Business-driven framework for security architecture.", "ext", None),
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
    ("risk", "GDPR", "General Data Protection Regulation",
     "European Union data-protection and privacy regulation.", "core", None),
    # ---- Data & Asset Security --------------------------------------------
    ("data", "PII", "Personally Identifiable Information",
     "Information that identifies, or can reasonably identify, an individual.", "core", None),
    ("data", "PHI", "Protected Health Information",
     "Individually identifiable health information subject to privacy and security protection.", "core", None),
    ("data", "DLP", "Data Loss Prevention",
     "Technologies and processes designed to detect and prevent unauthorized disclosure or movement of sensitive information.", "core",
     "DLP asks: \u201ccan the data leave?\u201d (NAC asks whether the device may enter.)"),
    ("data", "DRM", "Digital Rights Management",
     "Controls governing access to and use of protected digital content.", "ext", None),
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
    ("crypto", "PFS", "Perfect Forward Secrecy",
     "Session-key design ensuring compromise of long-term keys does not expose previously encrypted sessions.", "ext",
     "Ephemeral session keys: yesterday's traffic stays safe even if today's private key leaks."),
    ("crypto", "MITM", "Man-in-the-Middle",
     "Attack in which an adversary intercepts and potentially alters communications between parties.", "core", None),
    # ---- Communication & Network Security ----------------------------------
    ("network", "OSI", "Open Systems Interconnection",
     "Seven-layer conceptual networking model — 1 Physical, 2 Data Link, 3 Network, 4 Transport, 5 Session, 6 Presentation, 7 Application.", "core",
     "Know the seven layers in order (“Please Do Not Throw Sausage Pizza Away”) and which protocols and devices live at each."),
    ("network", "TCP/IP", "Transmission Control Protocol / Internet Protocol",
     "Core protocol suite underlying IP networks and the Internet; its four-layer model is Link, Internet, Transport, Application.", "core",
     "Mapping to OSI: Link ≈ 1–2, Internet ≈ 3, Transport ≈ 4, Application ≈ 5–7."),
    ("network", "IPSec", "Internet Protocol Security",
     "Suite of protocols for protecting IP communications.", "core", None),
    ("network", "VPN", "Virtual Private Network",
     "Protected logical connection across an untrusted network.", "core", None),
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
     "Secure protocol for remote system administration and related functions.", "core", None),
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
    ("iam", "JIT", "Just-In-Time Access",
     "Provides elevated access temporarily, only when required.", "ext", None),
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
    ("assess", "SBOM", "Software Bill of Materials",
     "Structured inventory of components contained in a software product.", "ext", None),
    # ---- Security Operations ------------------------------------------------
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
    # ---- Software & Cloud Security ------------------------------------------
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
DETAILS = {
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
    "IR": ["1 Detection / Analysis — recognize and triage the incident",
           "2 Containment — stop the spread before deeper action",
           "3 Eradication / Remediation — remove the adversary and artifacts",
           "4 Recovery — restore systems and service",
           "5 Lessons Learned — feed improvements back into controls"],
    "SDLC": ["Requirements — what must it do (start security HERE)",
             "Design — architecture and threat modeling",
             "Implementation — secure coding",
             "Testing — SAST/DAST, reviews, UAT",
             "Deployment / Operations — hardening, monitoring, patching",
             "Retirement — secure decommissioning and data disposal"],
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
    if not det:
        return ""
    lis = "".join("<li>" + escape(x) + "</li>" for x in det)
    return ('<details class="gl-more"><summary>In depth — the steps that get tested</summary>'
            "<ul>" + lis + "</ul></details>")


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
]

_terms_by_acr = {t[1]: t for t in TERMS}
_ids = [term_id(t[1]) for t in TERMS]
assert len(set(_ids)) == len(_ids), "term id collision"

_cat_labels = {k: label for k, label, _ in CATS}
_json_terms = [
    {"id": term_id(a), "acronym": a, "full_term": t, "definition": d,
     "category": c, "category_label": _cat_labels[c],
     "study_tip": tip or "", "priority": ("Core" if p == "core" else "Extended"),
     **({"detail": DETAILS[a]} if a in DETAILS else {})}
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
