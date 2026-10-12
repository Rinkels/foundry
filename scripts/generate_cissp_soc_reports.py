# -*- coding: utf-8 -*-
"""SOC 1 vs SOC 2 (vs SOC 3, Type I vs Type II) — deep-dive article generator.

Second "concept cluster" page (after security models). Original content.
Creates/updates the EvergreenArticle at /insights/cissp-soc-reports.html.

Run via manage.py shell exec, then build_site.
"""

SLUG = "cissp-soc-reports"
TITLE = "SOC 1 vs SOC 2: Which Report Says What (and What Type I vs Type II Means)"
META_DESCRIPTION = ("Plain-English guide to SOC 1, SOC 2 and SOC 3 reports and the Type I / "
                    "Type II distinction — who asks for each, what they attest, and the CISSP "
                    "exam tells, with the SSAE-18 context.")
ISC2_OUTLINE_URL = "https://www.isc2.org/certifications/cissp/cissp-certification-exam-outline"
DISCLAIMER = ("Independent CISSP study aid. CISSP is a registered trademark of ISC2. "
              "This resource is not affiliated with or endorsed by ISC2.")

CSS = """
<style>
.sr-links{display:flex;gap:22px;flex-wrap:wrap;margin:10px 0 0}
.sr-links a{color:var(--site-gold,#d9b36b);font-weight:600;text-decoration:none;border-bottom:1px solid var(--site-gold,#d9b36b)}
.sr-links a:hover{opacity:.85}
.sr-card{border:1px solid var(--site-border,rgba(148,163,199,.2));border-top:3px solid var(--sr-c,#5dd6c6);
  border-radius:14px;padding:20px 22px;margin:18px 0}
.sr-card h3{margin:0 0 4px;font-size:1.15rem;color:var(--site-heading,#f4f6f9)}
.sr-card .sr-k{font-size:.75rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--sr-c,#5dd6c6)}
.sr-card ul{margin:12px 0 0;padding:0;list-style:none}
.sr-card li{margin:6px 0;padding-left:18px;position:relative;color:var(--site-text,#dfe4ee)}
.sr-card li::before{content:"→";position:absolute;left:0;color:var(--sr-c,#5dd6c6)}
.sr-tell{margin:12px 0 0;font-size:.92rem;color:var(--site-muted,#8b93a7)}
.sr-tell strong{color:var(--site-gold,#d9b36b)}
.sr-note{border:1px solid var(--site-gold,#d9b36b);border-radius:10px;padding:12px 16px;margin:18px 0;
  background:rgba(217,179,107,.06);font-size:.92rem}
.sr-note .sr-note__t{font-weight:700;color:var(--site-gold,#d9b36b);font-size:.78rem;letter-spacing:.08em;
  text-transform:uppercase;margin-bottom:6px}
.sr-table{width:100%;border-collapse:collapse;margin:14px 0;font-size:.9rem}
.sr-table th{text-align:left;color:var(--site-gold,#d9b36b);font-size:.78rem;letter-spacing:.06em;
  text-transform:uppercase;padding:8px 10px;border-bottom:1px solid var(--site-border,rgba(148,163,199,.25))}
.sr-table td{padding:9px 10px;border-bottom:1px solid var(--site-border,rgba(148,163,199,.12));
  color:var(--site-text,#dfe4ee);vertical-align:top}
.sr-table td:first-child{font-weight:700;color:var(--site-heading,#f4f6f9);white-space:nowrap}
.sr-tablewrap{overflow-x:auto}
.sr-foot{font-size:.85rem;color:var(--site-muted,#8b93a7)}
@media (max-width:640px){.sr-table td:first-child{white-space:normal}}
</style>
"""

BODY = (
    "<section>" + CSS
    + "<section>"
    "<p>SOC reports confuse people because the names say nothing about the scope — and the exam "
    "exploits exactly that. The untangling takes three sentences: <strong>SOC 1 is about your "
    "customers' money, SOC 2 is about your security, SOC 3 is SOC 2's public-relations cousin</strong> "
    "— and Type I vs Type II is a separate axis that applies to the first two. The rest of this page "
    "is detail and exam tells.</p>"
    '<p class="sr-links"><a href="cissp-security-glossary.html">CISSP Glossary →</a>'
    '<a href="cissp-flashcards.html">CISSP Flashcards →</a>'
    '<a href="cissp-mind-map.html">Syllabus Mind Map →</a></p>'
    "</section>"

    "<section><h2>The three reports</h2>"
    '<div class="sr-card" style="--sr-c:#D9B36B"><div class="sr-k">Financial reporting</div>'
    "<h3>SOC 1 — controls that touch your customers' financial statements</h3>"
    "<p>For service organizations whose work feeds into customers' books: payroll processors, "
    "claims administrators, custodians, billing platforms. The report attests ICFR-relevant "
    "controls — <em>internal control over financial reporting</em>.</p><ul>"
    "<li>Audience: the <strong>customers' financial auditors</strong>, not security teams.</li>"
    "<li>If the service fails, the customer's balance sheet could be wrong — that's the test for "
    "whether SOC 1 is the relevant report.</li></ul>"
    '<p class="sr-tell"><strong>Exam tell:</strong> “payroll provider”, “financial '
    "statements”, “user entities' auditors” → SOC 1.</p></div>"

    '<div class="sr-card" style="--sr-c:#4FD8C4"><div class="sr-k">Security &amp; operations</div>'
    "<h3>SOC 2 — controls over the Trust Services Criteria</h3>"
    "<p>The security due-diligence report. Scope is chosen from five Trust Services Criteria — "
    "<strong>Security is always included</strong>; Availability, Processing Integrity, "
    "Confidentiality and Privacy are added as relevant.</p><ul>"
    "<li>Audience: customers' security/risk teams and prospects under NDA — distribution is "
    "restricted because the report contains control detail.</li>"
    "<li>This is the report vendors mean when they say “we're SOC 2 compliant” (strictly: "
    "“we have a SOC 2 attestation” — it is not a certification).</li></ul>"
    '<p class="sr-tell"><strong>Exam tell:</strong> “security, availability, confidentiality” '
    "or “Trust Services Criteria” → SOC 2.</p></div>"

    '<div class="sr-card" style="--sr-c:#7C8CF8"><div class="sr-k">Public</div>'
    "<h3>SOC 3 — the public summary</h3>"
    "<p>A general-use, marketing-grade summary of a SOC 2 engagement: same examination, almost no "
    "detail, freely distributable (the web-site trust seal).</p>"
    '<p class="sr-tell"><strong>Exam tell:</strong> “publicly shareable” or '
    "“website seal” → SOC 3.</p></div>"

    '<div class="sr-note"><div class="sr-note__t">The second axis: Type I vs Type II</div>'
    "Independent of SOC 1 vs SOC 2: a <strong>Type I</strong> report examines whether controls are "
    "suitably <em>designed</em> at a single point in time; a <strong>Type II</strong> report tests "
    "whether they <em>operated effectively</em> over a period (commonly 6–12 months). Type II is the "
    "one that means something — a Type I says the blueprints look good, a Type II says the building "
    "stood through a year of weather. When procurement asks for “your SOC 2”, they almost "
    "always mean <strong>SOC 2 Type II</strong>.</div>"
    "</section>"

    "<section><h2>Where SSAE-18 fits</h2>"
    "<p>SSAE-18 is the AICPA <em>attestation standard</em> under which SOC engagements are performed "
    "— it doesn't mandate a specific control set; it governs how an independent auditor examines and "
    "reports on whatever controls are in scope. That's why the classic exam statements are: SSAE-18 "
    "<em>is</em> an attestation standard, <em>is</em> used for external audits, and <em>uses</em> the "
    "SOC 1/2/3 reporting framework — but does <em>not</em> prescribe the controls themselves.</p>"
    "</section>"

    "<section><h2>Cheat table</h2>"
    '<div class="sr-tablewrap"><table class="sr-table">'
    "<tr><th>If the question says…</th><th>Answer</th></tr>"
    "<tr><td>Affects customers' financial statements / payroll</td><td>SOC 1</td></tr>"
    "<tr><td>Security, availability, confidentiality, privacy / TSC</td><td>SOC 2</td></tr>"
    "<tr><td>Publicly distributable summary or seal</td><td>SOC 3</td></tr>"
    "<tr><td>Control design at a point in time</td><td>Type I</td></tr>"
    "<tr><td>Operating effectiveness over 6–12 months</td><td>Type II</td></tr>"
    "<tr><td>Attestation standard governing these audits</td><td>SSAE-18</td></tr>"
    "<tr><td>Facility full of analysts watching alerts</td><td>The other SOC — Security Operations Center</td></tr>"
    "</table></div>"
    "<p>Drill these in <a href=\"cissp-flashcards.html?domain=6\">Domain 6 flashcards and exam "
    "practice</a>.</p>"
    "</section>"

    "<section>"
    '<p class="sr-foot">Further study: the official <a href="' + ISC2_OUTLINE_URL + '" target="_blank" '
    'rel="noopener">ISC2 CISSP Exam Outline</a>. This page is an independently written study summary; '
    "authoritative SOC guidance is published by the AICPA.</p>"
    '<p class="sr-foot">' + DISCLAIMER + "</p>"
    "</section></section>"
)


from apps.sites_builder.models import Site, EvergreenArticle

site = Site.objects.get(slug="mindsgate-redesign")
article, created = EvergreenArticle.objects.get_or_create(
    site=site, slug=SLUG,
    defaults={"title": TITLE, "status": EvergreenArticle.STATUS_PUBLISHED},
)
article.title = TITLE
article.status = EvergreenArticle.STATUS_PUBLISHED
article.excerpt = ("SOC 1 is about your customers' money, SOC 2 is about your security, SOC 3 is "
                   "the public cousin — and Type II is the one that means something.")
article.body_md = BODY
article.meta_title = TITLE
article.meta_description = META_DESCRIPTION
article.save()
print(("created" if created else "updated"), "article", SLUG, "| body bytes:", len(BODY))
