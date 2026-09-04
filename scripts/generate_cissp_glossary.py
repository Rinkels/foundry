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
from html import escape

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
    ("crypto", "HSM", "Hardware Security Module",
     "Dedicated secure hardware for generating, protecting and using cryptographic keys.", "core", None),
    ("crypto", "PFS", "Perfect Forward Secrecy",
     "Session-key design ensuring compromise of long-term keys does not expose previously encrypted sessions.", "ext",
     "Ephemeral session keys: yesterday's traffic stays safe even if today's private key leaks."),
    ("crypto", "MITM", "Man-in-the-Middle",
     "Attack in which an adversary intercepts and potentially alters communications between parties.", "core", None),
    # ---- Communication & Network Security ----------------------------------
    ("network", "OSI", "Open Systems Interconnection",
     "Seven-layer conceptual networking model.", "core", None),
    ("network", "TCP/IP", "Transmission Control Protocol / Internet Protocol",
     "Core protocol suite underlying IP networks and the Internet.", "core", None),
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
     "Control plane and data plane are split — the controller is the crown jewel to protect."),
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
     "Trust arrangement allowing identities to be recognized across security domains.", "ext", None),
    ("iam", "RBAC", "Role-Based Access Control",
     "Assigns permissions according to organizational roles.", "core",
     "Roles decide (RBAC); attributes and context decide (ABAC)."),
    ("iam", "ABAC", "Attribute-Based Access Control",
     "Makes authorization decisions using attributes of users, resources and context.", "core", None),
    ("iam", "MAC", "Mandatory Access Control",
     "Centrally enforced access decisions based on classifications and labels.", "core",
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
     "Identity and authentication layer built on OAuth 2.0.", "core",
     "OIDC adds the \u201cwho are you?\u201d answer on top of OAuth."),
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
     "Endpoint-focused monitoring, detection, investigation and response.", "core",
     "EDR = endpoints; NDR = network telemetry; XDR correlates across layers."),
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
     "Know the lifecycle order cold — see the callout below."),
    ("ops", "CSIRT", "Computer Security Incident Response Team",
     "Team responsible for coordinating response to cybersecurity incidents.", "core", None),
    ("ops", "HA", "High Availability",
     "Architecture intended to minimize service outages and increase resilience.", "ext", None),
    # ---- Software & Cloud Security ------------------------------------------
    ("cloud", "SDLC", "Software Development Life Cycle",
     "Processes through which software is planned, designed, built, tested, operated and retired.", "core", None),
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
.gl-flash{margin:14px 0 0}
.gl-flash a{color:var(--site-gold,#d9b36b);font-weight:600;text-decoration:none;border-bottom:1px solid var(--site-gold,#d9b36b)}
.gl-flash a:hover{opacity:.85}
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
})();
</script>
"""


def entry_html(cat, acr, term, definition, pri, tip):
    hay = escape((acr + " " + term + " " + definition).lower(), quote=True)
    pri_label = "Core" if pri == "core" else "Extended"
    tip_html = ""
    if tip:
        tip_html = ('<p class="gl-entry__tip"><strong>Study tip:</strong> '
                    + escape(tip) + "</p>")
    return (
        '<div class="gl-entry" data-cat="' + cat + '" data-pri="' + pri
        + '" data-hay="' + hay + '">'
        + '<div class="gl-entry__head">'
        + '<span class="gl-entry__acr">' + escape(acr) + "</span>"
        + '<span class="gl-entry__term">' + escape(term) + "</span>"
        + '<span class="gl-entry__pri gl-entry__pri--' + pri + '">' + pri_label + "</span>"
        + "</div>"
        + '<div class="gl-entry__body">'
        + '<p class="gl-entry__def">' + escape(definition) + "</p>"
        + tip_html
        + "</div></div>"
    )


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
        '<p class="gl-flash"><a href="cissp-flashcards.html">Study these terms with flashcards →</a></p>'
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
     "study_tip": tip or "", "priority": ("Core" if p == "core" else "Extended")}
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

_data = {
    "version": 1,
    "generated": _dt.now(_tz.utc).isoformat(timespec="seconds"),
    "categories": _cat_labels,
    "terms": _json_terms,
    "scenarios": _json_scenarios,
}
_out = (_Path(_settings.BASE_DIR) / "output" / "sites" / site.slug
        / "assets" / "data" / "cissp-glossary.json")
_out.parent.mkdir(parents=True, exist_ok=True)
_out.write_text(_json.dumps(_data, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", _out, "| terms:", len(_json_terms), "| scenarios:", len(_json_scenarios))
