# -*- coding: utf-8 -*-
"""CISSP Domain Mind Map — interactive syllabus overview + navigation layer.

Creates/updates the EvergreenArticle at /insights/cissp-mind-map.html.

Architecture (consistent with the glossary/flashcards pipeline):
- The full hierarchy is SERVER-RENDERED as nested semantic lists, so the page
  is a complete text/tree fallback with JavaScript disabled and for screen
  readers. JS only adds collapse/expand, domain filtering, zoom and progress.
- Concept leaves that exist in the shared glossary render as deep links to
  cissp-security-glossary.html#t-<term id> (the glossary scrolls + highlights).
  "g:ACR" entries below are validated against assets/data/cissp-glossary.json
  at generation time — run generate_cissp_glossary.py FIRST.
- Domain nodes link to cissp-flashcards.html?domain=<n> (the flashcards page
  reads ?domain= / ?cat= and preselects the category).
- Study-status chips read the flashcards' localStorage (mg_cissp_flashcards_v1)
  purely locally; framed as activity, never exam readiness.

Run:
  python manage.py shell -c "exec(open(r'C:\\Projects\\foundry\\scripts\\generate_cissp_mindmap.py', encoding='utf-8').read())"
Then build_site.
"""
import json
import re
from html import escape
from pathlib import Path

from django.conf import settings

SLUG = "cissp-mind-map"
TITLE = "CISSP Domain Mind Map: The Whole Syllabus on One Page"
META_DESCRIPTION = ("Interactive CISSP mind map of all eight domains with exam weights — expand "
                    "topics, jump to glossary definitions, and launch domain-filtered flashcards "
                    "for risk, cryptography, IAM, networking, security operations and secure "
                    "software development.")
ISC2_OUTLINE_URL = "https://www.isc2.org/certifications/cissp/cissp-certification-exam-outline"
DISCLAIMER = ("Independent CISSP study aid. CISSP is a registered trademark of ISC2. "
              "This resource is not affiliated with or endorsed by ISC2.")

# --- load the shared data source (single source of truth) -------------------
DATA_PATH = (Path(settings.BASE_DIR) / "output" / "sites" / "mindsgate-redesign"
             / "assets" / "data" / "cissp-glossary.json")
SHARED = json.loads(DATA_PATH.read_text(encoding="utf-8"))
TERM_BY_ID = {t["id"]: t for t in SHARED["terms"]}
DOMAINS = SHARED["domains"]  # [{number,key,name,weight}]


def slug_id(acr):
    return re.sub(r"[^a-z0-9]+", "-", acr.lower()).strip("-")


# --- hierarchy ---------------------------------------------------------------
# Children syntax:  "g:ACR" = glossary-linked leaf (validated);  "text" = plain
# leaf;  ("s", "label", [kids]) = collapsible sub-branch;
# ("!", "label", ["line", ...]) = always-visible study callout card.
TOPICS = {
    1: [
        ("Security principles and ethics", ["g:CIA", "Authenticity", "Non-repudiation", "ISC2 Code of Ethics"]),
        ("Security governance", ["Alignment with business strategy", "Roles and accountability", "g:GRC"]),
        ("Security frameworks", ["g:NIST", "g:COBIT", "g:SABSA", "ISO/IEC 27001"]),
        ("Legal, regulatory, privacy and compliance", ["g:GDPR", "g:PCI DSS", "g:PII",
            "g:GLBA", "g:HIPAA", "g:SOX", "g:FERPA", "g:FISMA",
            "Criminal vs civil vs administrative law", "Intellectual property",
            ("!", "US law cheat line", ["HIPAA = health · GLBA = financial privacy",
                                        "SOX = public-company reporting · FERPA = education",
                                        "FISMA = federal systems · GDPR = EU personal data",
                                        "Criminal penalties: HIPAA & SOX (not FERPA, not PCI DSS)"]),
        ]),
        ("Policies, standards, procedures and guidelines", ["Policy (mandatory, high level)", "Standard (mandatory, specific)", "Procedure (step by step)", "Guideline (recommended)"]),
        ("Business continuity and BIA", ["g:BIA", "g:BC", "g:BCP", "g:MTD", "g:RTO", "g:RPO"]),
        ("Personnel security", ["Screening", "Onboarding / offboarding", "g:SoD", "Job rotation", "NDAs"]),
        ("Risk management", [
            ("s", "Identify", ["Threats", "Vulnerabilities", "Asset valuation"]),
            ("s", "Analyze", ["Qualitative vs quantitative", "g:SLE", "g:ARO", "g:ALE"]),
            ("s", "Treat", ["Risk acceptance", "Risk avoidance", "Risk mitigation", "Risk transfer"]),
            ("s", "Monitor", ["g:KRI", "g:KPI", "Risk register"]),
            ("!", "Quantitative risk", ["SLE = Asset Value × Exposure Factor", "ALE = SLE × ARO"]),
        ]),
        ("Controls and control assessment", ["Preventive / detective / corrective", "Administrative / technical / physical", "Compensating controls"]),
        ("Threat modelling", ["g:STRIDE", "g:PASTA", "g:VAST", "g:DREAD", "Attack trees", "g:Decomposition",
            ("!", "Four methodologies", ["STRIDE = categorize (6 threat classes)",
                                         "DREAD = rate (5 scoring questions)",
                                         "PASTA = 7-stage, risk/asset-centric",
                                         "VAST = Agile-integrated, scalable"]),
        ]),
        ("Supply Chain Risk Management", ["g:SCRM", "Third-party assessments", "g:SLA"]),
        ("Security awareness and training", ["Phishing simulations", "Role-based training", "Culture"]),
    ],
    2: [
        ("Information and asset classification", ["Classification levels", "Labelling and marking"]),
        ("Asset ownership and inventory", ["Asset ownership", "Asset inventory", "Handling requirements"]),
        ("Data lifecycle", ["Create → store → use → share → archive → destroy"]),
        ("Data roles", [
            ("!", "Who is who", ["Owner — accountable for the data", "Controller — decides purpose & means",
                                 "Custodian — day-to-day care", "Processor — handles data for a controller",
                                 "Subject/user — the person the data is about"]),
        ]),
        ("Data retention and destruction", ["Data retention", "Data remanence", "Secure destruction (purge, crypto-erase, destroy)", "g:EOL", "g:EOS"]),
        ("Data states", ["Data at rest", "Data in transit", "Data in use"]),
        ("Data protection controls", ["g:DLP", "g:DRM", "g:CASB", "g:FDE", "g:Scoping", "Tokenization and masking"]),
    ],
    3: [
        ("Secure design principles", ["Least privilege", "g:DiD", "Secure defaults", "Fail secure",
                                      "g:SoD", "Zero Trust", "Privacy by design", "Shared responsibility", "Keep it simple",
            ("!", "Defense-in-depth vocabulary", ["Related terms: layering · classifications · zones · realms",
                                                  "compartments · silos · segmentations",
                                                  "lattice structure · protection rings"]),
        ]),
        ("Security models", [
            ("a", "Bell-LaPadula (confidentiality)", "cissp-security-models.html#blp"),
            ("a", "Biba (integrity)", "cissp-security-models.html#biba"),
            ("a", "Clark-Wilson (transactions)", "cissp-security-models.html#cw"),
            ("a", "Brewer-Nash (Chinese Wall)", "cissp-security-models.html#bn"),
            "g:Rings",
            ("a", "All models compared →", "cissp-security-models.html"),
        ]),
        ("System security capabilities", ["g:TPM", "g:HSM", "Memory protection", "Trusted execution"]),
        ("Architecture vulnerabilities", ["Single points of failure", "Covert channels", "Emanations"]),
        ("Cloud and distributed architecture", ["g:SaaS", "g:PaaS", "g:IaaS", "Containers", "Microservices",
                                                "Serverless", "Virtualization", "IoT", "Edge computing"]),
        ("Cryptography", [
            ("s", "Symmetric", ["g:AES", "Fast bulk encryption", "Key distribution problem"]),
            ("s", "Asymmetric", ["g:RSA", "g:ECC", "g:DH", "g:ECDH", "Digital signatures"]),
            ("s", "Integrity", ["g:SHA", "g:HMAC", "Hashing vs encryption"]),
            ("s", "PKI", ["g:PKI", "g:CA", "g:RA", "g:CSR", "g:CRL", "g:OCSP"]),
            ("s", "Attacks", ["g:MITM", "Brute force", "Side channel", "Birthday attack"]),
            "g:PFS",
            ("!", "Encryption at a glance", ["AES = symmetric = fast bulk encryption",
                                             "RSA/ECC = asymmetric = keys & signatures",
                                             "SHA = hashing = integrity"]),
        ]),
        ("Physical and site security", ["g:CPTED", "g:CPA", "g:Cable plant", "g:Sprinklers", "g:6 Ds",
                                        "Perimeter and zones", "Environmental controls", "Motion detection",
            ("!", "Six Ds in order", ["Deter → Deny → Detect → Delay → Determine → Decide"]),
        ]),
        ("Information-system lifecycle", ["Acquire → implement → operate → retire"]),
    ],
    4: [
        ("OSI and TCP/IP models", ["g:OSI", "g:TCP/IP", "Encapsulation", "IPv4 and IPv6", "g:RFC 1918", "g:APIPA", "g:NTP"]),
        ("Secure network protocols", ["g:TLS", "g:SSL", "g:SSH", "g:DNSSEC", "g:SNMP", "g:DHCP", "g:DNS",
            ("s", "IPsec", ["g:IPSec", "AH — authentication/integrity", "ESP — encryption/confidentiality", "IKE — key exchange"]),
            ("!", "AH vs ESP", ["AH = authentication and integrity only",
                                "ESP = encryption/confidentiality plus security services"]),
        ]),
        ("Network architecture and segmentation", ["g:VLAN", "Segmentation", "Microsegmentation", "g:ISFW", "g:DMZ", "VPC"]),
        ("Traffic flows", ["North-south traffic", "East-west traffic"]),
        ("Wireless and mobile", ["WPA3", "g:CCMP", "g:Zigbee", "Enterprise vs PSK", "Captive portals",
            ("!", "Wireless crypto lineage", ["WEP → TKIP (WPA) → CCMP/AES (WPA2) → SAE (WPA3)"]),
        ]),
        ("SDN and virtual networking", ["g:SDN", "g:SASE", "g:CDN", "Overlay networks"]),
        ("Network monitoring and defense", ["g:IDS", "g:IPS", "g:IDPS", "g:WAF", "g:NGFW", "g:NAC", "g:QoS",
            ("s", "Layer-2 attacks", ["g:ARP", "g:MAC spoofing", "MAC flooding (CAM overflow)"]),
        ]),
        ("Secure communication channels", ["g:VPN", "g:EAP", "g:PAP", "g:CHAP", "g:PVC", "Voice and collaboration",
            ("!", "PPP authentication", ["PAP = plaintext (no protection)",
                                         "CHAP = challenge/response, password never sent",
                                         "EAP = extensible framework (40+ methods)"]),
        ]),
    ],
    5: [
        ("Access control fundamentals", ["Physical and logical access", "Identification", "Authentication",
                                         "Authorization", "Accounting", "g:AAA"]),
        ("Authentication", ["g:MFA", "Something you know / have / are", "Session management", "Identity proofing"]),
        ("Federation and SSO", ["g:SSO", "g:FIM", "g:SAML", "g:OAuth", "g:OIDC",
            ("!", "Federation standards", ["SAML = enterprise federation / browser SSO",
                                           "OAuth = delegated authorization",
                                           "OIDC = authentication & identity on OAuth 2.0",
                                           "SCIM = provisioning / deprovisioning"]),
        ]),
        ("Privileged access", ["g:PAM", "g:JIT", "Break-glass accounts", "Service accounts"]),
        ("Authorization models", ["g:RBAC", "g:ABAC", "g:MAC", "g:DAC", "Rule-based"]),
        ("Provisioning and lifecycle", ["g:SCIM", "Joiner / mover / leaver", "Access reviews"]),
        ("Authentication systems", ["g:LDAP", "g:Kerberos", "g:RADIUS", "g:TACACS+",
            ("s", "Credential attacks", ["g:PtH", "Pass the ticket / golden ticket (Kerberos)", "Rainbow tables (offline)"]),
        ]),
    ],
    6: [
        ("Assessment strategies", ["Internal assessment", "External assessment", "Third-party assessment"]),
        ("Security control testing", ["Control effectiveness", "g:CVE", "g:CVSS", "g:CWE"]),
        ("Vulnerability assessment and pen testing", ["g:VA", "g:PT", "Red / Blue / Purple teams", "Breach and attack simulation",
            ("!", "VA vs PT", ["Vulnerability Assessment = identify and evaluate weaknesses",
                               "Penetration Test = authorized exploitation to demonstrate impact"]),
        ]),
        ("Code and interface testing", ["g:SAST", "g:DAST", "g:IAST", "g:SCA", "Interface / API testing", "Fuzzing"]),
        ("Log review and monitoring tests", ["Log review", "Synthetic transactions"]),
        ("Compliance and audits", ["Security audits", "SSAE-18 / SOC reports", "Compliance testing"]),
        ("Metrics and remediation", ["g:KPI", "g:KRI", "Security metrics", "Test-result analysis", "Remediation", "Exceptions"]),
    ],
    7: [
        ("Investigations and forensics", ["Evidence handling", "Chain of custody", "Digital forensics", "eDiscovery"]),
        ("Logging and monitoring", ["g:SIEM", "g:UEBA", "Threat intelligence", "Threat hunting", "g:IOC", "g:TTP"]),
        ("Detection and prevention technologies", ["g:IDS", "g:IPS", "Firewalls", "g:WAF", "g:EDR", "g:XDR", "g:NDR", "g:SOAR"]),
        ("Incident management", ["g:IR", "g:CSIRT",
            ("!", "Incident-response sequence", ["Detection / Analysis", "→ Containment", "→ Eradication / Remediation",
                                                 "→ Recovery", "→ Lessons Learned"]),
        ]),
        ("Operational security", ["Configuration management", "Change management", "Patch and vulnerability management",
                                  "Resource protection", "Need to know / least privilege"]),
        ("Backup, recovery and resilience", ["Backup strategies", "g:HA", "g:RTO", "g:RPO", "g:DRP", "g:BCP",
                                             "Hot site", "Warm site", "Cold site"]),
        ("Physical and personnel security", ["Guards and access controls", "Duress", "Travel security"]),
    ],
    8: [
        ("Secure SDLC", ["g:SDLC", "g:SSDLC", "Security in requirements and design", "Threat modelling"]),
        ("Development methodologies", ["Agile", "Waterfall", "DevOps / DevSecOps", "g:SW-CMM"]),
        ("CI/CD and configuration management", ["g:CI/CD", "Repositories", "Code signing", "Change management"]),
        ("Application security testing", ["g:SAST", "g:DAST", "g:IAST", "g:SCA", "g:RASP",
            ("!", "Testing at a glance", ["SAST = analyze code without executing it",
                                          "DAST = test the running application externally",
                                          "IAST = instrument the app while it runs",
                                          "SCA = analyze third-party components"]),
        ]),
        ("Software supply chain", ["g:SBOM", "g:COTS", "Open source", "Libraries and dependencies"]),
        ("Secure coding and APIs", ["g:OWASP", "Input validation", "g:API", "API authentication and authorization", "g:XSRF"]),
        ("Software security effectiveness", ["Auditing and logging of changes", "Risk analysis of acquired software", "g:CSP"]),
    ],
}

# Domain accent colors (dark-theme friendly, one hue per domain)
COLORS = {1: "#D9B36B", 2: "#4FD8C4", 3: "#7C8CF8", 4: "#56A8F5",
          5: "#7BC77E", 6: "#E7A15A", 7: "#E57373", 8: "#C98BD9"}


def leaf_html(item):
    if isinstance(item, str) and item.startswith("g:"):
        acr = item[2:]
        tid = slug_id(acr)
        assert tid in TERM_BY_ID, "unknown glossary ref: " + acr
        t = TERM_BY_ID[tid]
        return ('<li class="mm-leaf"><a class="mm-term" href="cissp-security-glossary.html#t-' + tid
                + '" title="' + escape(t["full_term"]) + ' — open in glossary">'
                + escape(t["acronym"]) + "</a></li>")
    return '<li class="mm-leaf"><span class="mm-plain">' + escape(item) + "</span></li>"


def children_html(kids, depth):
    parts = []
    for k in kids:
        if isinstance(k, tuple) and k[0] == "!":
            lines = "".join("<div>" + escape(x) + "</div>" for x in k[2])
            parts.append('<li class="mm-noteli"><div class="mm-note"><div class="mm-note__t">'
                         + escape(k[1]) + "</div>" + lines + "</div></li>")
        elif isinstance(k, tuple) and k[0] == "a":
            parts.append('<li class="mm-leaf"><a class="mm-term" href="' + k[2] + '">'
                         + escape(k[1]) + "</a></li>")
        elif isinstance(k, tuple) and k[0] == "s":
            parts.append(branch_html(k[1], k[2], depth + 1))
        else:
            parts.append(leaf_html(k))
    return "".join(parts)


def branch_html(label, kids, depth):
    has_kids = bool(kids)
    btn = ('<button type="button" class="mm-toggle" aria-expanded="true">'
           '<span class="mm-caret" aria-hidden="true"></span>'
           + escape(label) + "</button>") if has_kids else escape(label)
    inner = ('<ul class="mm-kids">' + children_html(kids, depth) + "</ul>") if has_kids else ""
    return '<li class="mm-branch mm-d' + str(depth) + '">' + btn + inner + "</li>"


def domain_html(d):
    n, key = d["number"], d["key"]
    topics = "".join(branch_html(lbl, kids, 1) for lbl, kids in TOPICS[n])
    return (
        '<li class="mm-domain" data-domain="' + str(n) + '" data-cat="' + key
        + '" style="--mm-c:' + COLORS[n] + '">'
        '<div class="mm-dcard">'
        '<button type="button" class="mm-toggle mm-dtoggle" aria-expanded="true">'
        '<span class="mm-caret" aria-hidden="true"></span>'
        '<span class="mm-dnum">D' + str(n) + '</span>'
        '<span class="mm-dname">' + escape(d["name"]) + "</span>"
        '<span class="mm-dweight">' + str(d["weight"]) + "%</span>"
        "</button>"
        '<div class="mm-dmeta">'
        '<span class="mm-progress" data-progress="' + key + '"></span>'
        '<a class="mm-study" href="cissp-flashcards.html?domain=' + str(n) + '">Study D' + str(n)
        + " flashcards →</a>"
        "</div></div>"
        '<ul class="mm-kids mm-topics">' + topics + "</ul></li>"
    )


CSS = """
<style>
.mm-controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 6px}
.mm-label{font-size:.78rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--site-muted,#8b93a7);width:100%;margin:12px 0 2px}
.mm-chip{font:inherit;font-size:.84rem;font-weight:600;padding:7px 13px;border-radius:999px;cursor:pointer;
  border:1px solid var(--site-border,rgba(148,163,199,.25));color:var(--site-text,#dfe4ee);
  background:var(--site-surface,rgba(255,255,255,.03))}
.mm-chip:hover{border-color:var(--site-accent,#5dd6c6)}
.mm-chip.is-on{border-color:var(--site-accent,#5dd6c6);color:var(--site-accent,#5dd6c6)}
.mm-chip:focus-visible,.mm-toggle:focus-visible,.mm-term:focus-visible,.mm-study:focus-visible{outline:2px solid var(--site-accent,#5dd6c6);outline-offset:2px}
.mm-chip .mm-w{color:var(--site-muted,#8b93a7);font-weight:400}
.mm-viewport{overflow:auto;border:1px solid var(--site-border,rgba(148,163,199,.14));border-radius:14px;
  padding:20px;background:rgba(0,0,0,.14)}
.mm-scale{transform-origin:top left}
.mm-root{display:inline-block;font-family:var(--site-heading-font,'Space Grotesk',sans-serif);font-weight:700;
  font-size:1.35rem;color:var(--site-on-accent,#07120f);background:var(--site-accent,#5dd6c6);
  border-radius:12px;padding:10px 22px;margin-bottom:6px}
.mm-rootnote{font-size:.82rem;color:var(--site-muted,#8b93a7);margin:0 0 10px}
.mm-tree,.mm-kids{list-style:none;margin:0;padding:0}
.mm-tree>li,.mm-kids>li{position:relative;padding:4px 0 0 26px}
.mm-kids{padding-left:14px;position:relative}
.mm-kids::before{content:"";position:absolute;left:2px;top:0;bottom:10px;border-left:2px solid var(--mm-c,rgba(148,163,199,.3));opacity:.35}
.mm-kids>li::before{content:"";position:absolute;left:-12px;top:1.15em;width:22px;border-top:2px solid var(--mm-c,rgba(148,163,199,.3));opacity:.35}
.mm-domain{margin:14px 0 0;padding-left:0!important}
.mm-domain::before{display:none}
.mm-dcard{display:flex;flex-wrap:wrap;gap:6px 16px;align-items:center}
.mm-dtoggle{font-family:var(--site-heading-font,'Space Grotesk',sans-serif);font-size:1.02rem;font-weight:700;
  border:1px solid var(--mm-c);border-radius:12px;padding:9px 16px;background:transparent;color:var(--site-heading,#f4f6f9)}
.mm-dnum{color:var(--mm-c);margin-right:10px}
.mm-dweight{margin-left:12px;font-size:.85rem;color:var(--site-on-accent,#07120f);background:var(--mm-c);
  border-radius:999px;padding:2px 10px}
.mm-dmeta{display:flex;gap:14px;align-items:center;font-size:.82rem}
.mm-progress{color:var(--site-muted,#8b93a7)}
.mm-progress .mm-st{font-weight:700}
.mm-progress .mm-st--strong{color:var(--site-accent,#5dd6c6)}
.mm-progress .mm-st--weak{color:#e5484d}
.mm-progress .mm-st--prog{color:var(--site-gold,#d9b36b)}
.mm-study{color:var(--mm-c);font-weight:600;text-decoration:none;border-bottom:1px solid var(--mm-c)}
.mm-study:hover{opacity:.85}
.mm-toggle{font:inherit;background:none;border:none;color:var(--site-text,#dfe4ee);cursor:pointer;
  padding:2px 4px 2px 0;text-align:left;font-weight:600}
.mm-toggle:hover{color:var(--site-heading,#fff)}
.mm-caret{display:inline-block;width:.62em;height:.62em;margin-right:9px;border-right:2px solid var(--mm-c,#8b93a7);
  border-bottom:2px solid var(--mm-c,#8b93a7);transform:rotate(45deg);transition:transform .15s ease;vertical-align:.12em}
.mm-toggle[aria-expanded="false"] .mm-caret{transform:rotate(-45deg)}
.mm-toggle[aria-expanded="false"]+.mm-kids{display:none}
.mm-leaf{font-size:.92rem;color:var(--site-text,#dfe4ee)}
.mm-plain{color:var(--site-muted,#a8b3c9)}
.mm-term{color:var(--site-heading,#eef2fa);font-weight:600;text-decoration:none;
  border-bottom:1px dashed var(--mm-c,#5dd6c6)}
.mm-term:hover{color:var(--mm-c,#5dd6c6)}
.mm-noteli::before{display:none!important}
.mm-note{border:1px solid var(--site-gold,#d9b36b);border-radius:10px;padding:10px 14px;margin:8px 0 4px;
  font-size:.88rem;color:var(--site-text,#dfe4ee);max-width:520px;background:rgba(217,179,107,.06)}
.mm-note__t{font-weight:700;color:var(--site-gold,#d9b36b);font-size:.78rem;letter-spacing:.08em;
  text-transform:uppercase;margin-bottom:5px}
.mm-domain.mm-dim{opacity:.22}
.mm-domain.mm-dim .mm-kids{display:none}
.mm-foot{font-size:.85rem;color:var(--site-muted,#8b93a7);margin-top:14px}
.mm-links{display:flex;gap:22px;flex-wrap:wrap;margin-top:8px}
.mm-links a{color:var(--site-gold,#d9b36b);font-weight:600;text-decoration:none;border-bottom:1px solid var(--site-gold,#d9b36b)}
@media (max-width:640px){
  .mm-viewport{padding:12px}
  .mm-kids{padding-left:8px}
  .mm-tree>li,.mm-kids>li{padding-left:16px}
  .mm-dcard{align-items:flex-start;flex-direction:column}
}
@media (prefers-reduced-motion:reduce){.mm-caret{transition:none}}
</style>
"""

JS = """
<script>
(function () {
  var app = document.getElementById("mm-app");
  if (!app) return;
  document.getElementById("mm-controls").hidden = false;

  var domains = Array.prototype.slice.call(document.querySelectorAll(".mm-domain"));
  var toggles = Array.prototype.slice.call(document.querySelectorAll(".mm-toggle"));
  var scaleEl = document.getElementById("mm-scale");
  var scale = 1;

  toggles.forEach(function (t) {
    t.addEventListener("click", function () {
      t.setAttribute("aria-expanded", t.getAttribute("aria-expanded") === "true" ? "false" : "true");
    });
  });

  function setAll(expanded, includeDomains) {
    toggles.forEach(function (t) {
      if (!includeDomains && t.classList.contains("mm-dtoggle")) { t.setAttribute("aria-expanded", "true"); return; }
      t.setAttribute("aria-expanded", expanded ? "true" : "false");
    });
  }
  function defaultView() { setAll(false, false); }  // domains open, topics collapsed

  function setScale(s) {
    scale = Math.min(1.6, Math.max(0.6, s));
    scaleEl.style.transform = scale === 1 ? "" : "scale(" + scale + ")";
    scaleEl.style.width = scale < 1 ? (100 / scale) + "%" : "";
  }

  var chips = Array.prototype.slice.call(document.querySelectorAll("#mm-domsel .mm-chip"));
  function selectDomain(val) {
    chips.forEach(function (c) {
      var on = c.dataset.dom === val;
      c.classList.toggle("is-on", on);
      c.setAttribute("aria-pressed", on ? "true" : "false");
    });
    domains.forEach(function (d) {
      var dim = val !== "all" && d.dataset.domain !== val;
      d.classList.toggle("mm-dim", dim);
      if (!dim && val !== "all") {
        d.querySelector(".mm-dtoggle").setAttribute("aria-expanded", "true");
      }
    });
  }
  chips.forEach(function (c) {
    c.addEventListener("click", function () { selectDomain(c.dataset.dom); });
  });

  document.getElementById("mm-expand").addEventListener("click", function () { setAll(true, true); });
  document.getElementById("mm-collapse").addEventListener("click", function () { setAll(false, true); });
  document.getElementById("mm-reset").addEventListener("click", function () {
    defaultView(); selectDomain("all"); setScale(1);
    document.getElementById("mm-viewport").scrollTo(0, 0);
  });
  document.getElementById("mm-zin").addEventListener("click", function () { setScale(scale + 0.15); });
  document.getElementById("mm-zout").addEventListener("click", function () { setScale(scale - 0.15); });

  // Study-status chips from local flashcard activity (never a readiness claim).
  fetch("../assets/data/cissp-glossary.json").then(function (r) { return r.json(); })
    .then(function (data) {
      var prog = null;
      try { prog = JSON.parse(localStorage.getItem("mg_cissp_flashcards_v1")); } catch (e) {}
      var cards = prog && prog.cards ? prog.cards : {};
      var byCat = {};
      data.terms.forEach(function (t) {
        var b = byCat[t.category] || (byCat[t.category] = { total: 0, seen: 0, strong: 0, weak: 0 });
        b.total++;
        var s = cards[t.id];
        if (s && s.r > 0) {
          b.seen++;
          if (s.conf >= 4) b.strong++;
          if (s.conf <= 1 || s.m * 2 >= s.r) b.weak++;
        }
      });
      Array.prototype.forEach.call(document.querySelectorAll(".mm-progress"), function (el) {
        var b = byCat[el.dataset.progress];
        if (!b) return;
        var st, cls;
        if (!b.seen) { st = "Not studied"; cls = ""; }
        else if (b.weak > 0 && b.weak >= b.strong) { st = "Needs review"; cls = "mm-st--weak"; }
        else if (b.strong * 2 >= b.seen) { st = "Strong"; cls = "mm-st--strong"; }
        else { st = "In progress"; cls = "mm-st--prog"; }
        el.innerHTML = b.seen + " / " + b.total + " terms reviewed · " +
          '<span class="mm-st ' + cls + '">' + st + "</span>";
      });
    }).catch(function () {});

  defaultView();
})();
</script>
"""


def build_body():
    dom_chips = '<button type="button" class="mm-chip is-on" data-dom="all" aria-pressed="true">All domains</button>'
    for d in DOMAINS:
        dom_chips += ('<button type="button" class="mm-chip" data-dom="' + str(d["number"])
                      + '" aria-pressed="false">D' + str(d["number"]) + " " + escape(d["name"])
                      + ' <span class="mm-w">' + str(d["weight"]) + "%</span></button>")

    tree = "".join(domain_html(d) for d in DOMAINS)

    return (
        "<section>" + CSS
        + "<section>"
        "<p>The whole CISSP syllabus on one page: eight domains with their current exam weights, "
        "the major topics inside each, and the key concepts underneath. Blue-dashed terms open the "
        "full definition in the glossary; every domain links straight into domain-filtered "
        "flashcards. Based on the current ISC2 CISSP Exam Outline, independently summarized.</p>"
        '<p class="mm-links"><a href="cissp-security-glossary.html">CISSP Glossary →</a>'
        '<a href="cissp-flashcards.html">CISSP Flashcards →</a>'
        '<a href="cissp-score-tracker.html">Chapter Score Tracker →</a></p>'
        "</section>"
        '<section><div id="mm-app">'
        '<div class="mm-controls" id="mm-controls" hidden>'
        '<div class="mm-label" id="mm-domsel-label">Focus on a domain</div>'
        '<div id="mm-domsel" role="group" aria-labelledby="mm-domsel-label" style="display:contents">' + dom_chips + "</div>"
        '<div class="mm-label">View</div>'
        '<button type="button" class="mm-chip" id="mm-expand">Expand all</button>'
        '<button type="button" class="mm-chip" id="mm-collapse">Collapse all</button>'
        '<button type="button" class="mm-chip" id="mm-reset">Reset view</button>'
        '<button type="button" class="mm-chip" id="mm-zout" aria-label="Zoom out">−</button>'
        '<button type="button" class="mm-chip" id="mm-zin" aria-label="Zoom in">+</button>'
        "</div>"
        '<div class="mm-viewport" id="mm-viewport">'
        '<div class="mm-scale" id="mm-scale">'
        '<div class="mm-root">CISSP</div>'
        '<p class="mm-rootnote">8 domains · weights from the current exam outline</p>'
        '<ul class="mm-tree">' + tree + "</ul>"
        "</div></div>"
        '<p class="mm-foot">Study-status markers reflect only your local flashcard activity in this '
        "browser — they are not a measure of CISSP exam readiness.</p>"
        "</div></section>"
        "<section>"
        '<p class="mm-foot">Further study: the official '
        '<a href="' + ISC2_OUTLINE_URL + '" target="_blank" rel="noopener">ISC2 CISSP Exam Outline</a> '
        "is the authoritative statement of the domains and their weights.</p>"
        '<p class="mm-foot">' + DISCLAIMER + "</p>"
        "</section>"
        + JS + "</section>"
    )


from apps.sites_builder.models import Site, EvergreenArticle

site = Site.objects.get(slug="mindsgate-redesign")
body = build_body()
article, created = EvergreenArticle.objects.get_or_create(
    site=site, slug=SLUG,
    defaults={"title": TITLE, "status": EvergreenArticle.STATUS_PUBLISHED},
)
article.title = TITLE
article.status = EvergreenArticle.STATUS_PUBLISHED
article.excerpt = ("Every CISSP domain, topic and key concept on one interactive map — with exam "
                   "weights, glossary deep links and domain-filtered flashcards.")
article.body_md = body
article.meta_title = TITLE
article.meta_description = META_DESCRIPTION
article.save()
print(("created" if created else "updated"), "article", SLUG, "| body bytes:", len(body),
      "| domains:", len(DOMAINS), "| topics:", sum(len(v) for v in TOPICS.values()))
