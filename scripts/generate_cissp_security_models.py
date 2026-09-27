# -*- coding: utf-8 -*-
"""CISSP Security Models Compared — deep-dive article generator.

First of the "concept cluster" deep-dive pages (topics that don't fit the
acronym-glossary format). Original explanatory content; static page, no JS.
Creates/updates the EvergreenArticle at /insights/cissp-security-models.html.

Run:
  python manage.py shell -c "exec(open(r'C:\\Projects\\foundry\\scripts\\generate_cissp_security_models.py', encoding='utf-8').read())"
Then build_site.
"""

SLUG = "cissp-security-models"
TITLE = "CISSP Security Models Compared: Bell-LaPadula, Biba, Clark-Wilson & Brewer-Nash"
META_DESCRIPTION = ("Plain-English comparison of the CISSP security models — Bell-LaPadula, Biba, "
                    "Clark-Wilson, Brewer-Nash, Graham-Denning, HRU, Take-Grant and lattice-based "
                    "models — with the rules, directionality traps and exam tells.")
ISC2_OUTLINE_URL = "https://www.isc2.org/certifications/cissp/cissp-certification-exam-outline"
DISCLAIMER = ("Independent CISSP study aid. CISSP is a registered trademark of ISC2. "
              "This resource is not affiliated with or endorsed by ISC2.")

CSS = """
<style>
.sm-links{display:flex;gap:22px;flex-wrap:wrap;margin:10px 0 0}
.sm-links a{color:var(--site-gold,#d9b36b);font-weight:600;text-decoration:none;border-bottom:1px solid var(--site-gold,#d9b36b)}
.sm-links a:hover{opacity:.85}
.sm-model{border:1px solid var(--site-border,rgba(148,163,199,.2));border-top:3px solid var(--sm-c,#5dd6c6);
  border-radius:14px;padding:20px 22px;margin:18px 0}
.sm-model h3{margin:0 0 4px;font-size:1.15rem;color:var(--site-heading,#f4f6f9)}
.sm-model .sm-k{font-size:.75rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--sm-c,#5dd6c6)}
.sm-rules{margin:12px 0 0;padding:0;list-style:none}
.sm-rules li{margin:6px 0;padding-left:18px;position:relative;color:var(--site-text,#dfe4ee)}
.sm-rules li::before{content:"→";position:absolute;left:0;color:var(--sm-c,#5dd6c6)}
.sm-tell{margin:12px 0 0;font-size:.92rem;color:var(--site-muted,#8b93a7)}
.sm-tell strong{color:var(--site-gold,#d9b36b)}
.sm-note{border:1px solid var(--site-gold,#d9b36b);border-radius:10px;padding:12px 16px;margin:18px 0;
  background:rgba(217,179,107,.06);font-size:.92rem}
.sm-note .sm-note__t{font-weight:700;color:var(--site-gold,#d9b36b);font-size:.78rem;letter-spacing:.08em;
  text-transform:uppercase;margin-bottom:6px}
.sm-table{width:100%;border-collapse:collapse;margin:14px 0;font-size:.9rem}
.sm-table th{text-align:left;color:var(--site-gold,#d9b36b);font-size:.78rem;letter-spacing:.06em;
  text-transform:uppercase;padding:8px 10px;border-bottom:1px solid var(--site-border,rgba(148,163,199,.25))}
.sm-table td{padding:9px 10px;border-bottom:1px solid var(--site-border,rgba(148,163,199,.12));
  color:var(--site-text,#dfe4ee);vertical-align:top}
.sm-table td:first-child{font-weight:700;color:var(--site-heading,#f4f6f9);white-space:nowrap}
.sm-tablewrap{overflow-x:auto}
.sm-foot{font-size:.85rem;color:var(--site-muted,#8b93a7)}
@media (max-width:640px){.sm-table td:first-child{white-space:normal}}
</style>
"""


def model(anchor, color, kind, name, intro, rules, tell):
    lis = "".join("<li>" + r + "</li>" for r in rules)
    return ('<div class="sm-model" id="' + anchor + '" style="--sm-c:' + color + '">'
            '<div class="sm-k">' + kind + "</div><h3>" + name + "</h3>"
            "<p>" + intro + "</p>"
            '<ul class="sm-rules">' + lis + "</ul>"
            '<p class="sm-tell"><strong>Exam tell:</strong> ' + tell + "</p></div>")


BODY = (
    "<section>" + CSS
    + "<section>"
    "<p>Security models turn a policy (\u201ckeep secrets secret\u201d, \u201ckeep data trustworthy\u201d) "
    "into formal rules a system can enforce and evaluators can prove. The exam almost never asks for the "
    "math — it describes a <em>property or rule</em> and asks which model it belongs to. This page is "
    "built for exactly that move: the big four in detail, the supporting cast, and the directionality "
    "traps spelled out.</p>"
    '<p class="sm-links"><a href="cissp-security-glossary.html">CISSP Glossary →</a>'
    '<a href="cissp-flashcards.html">CISSP Flashcards →</a>'
    '<a href="cissp-mind-map.html">Syllabus Mind Map →</a></p>'
    "</section>"

    "<section><h2>The big four</h2>"
    + model("blp", "#7C8CF8", "Confidentiality · mandatory access control",
            "Bell-LaPadula (BLP)",
            "Built for military classification systems: stop information flowing from high "
            "classifications to low ones. Subjects and objects carry labels; the model constrains "
            "reads and writes by label.",
            ["<strong>Simple Security Property</strong> — no read <em>up</em> (a Secret-cleared user "
             "cannot read Top Secret).",
             "<strong>★ (Star) Property</strong> — no write <em>down</em> (a Top Secret process cannot "
             "write into a Secret file, or secrets would leak downward).",
             "<strong>Strong ★ Property</strong> — read/write only at your own level.",
             "Discretionary access on top via an access matrix (the ds-property)."],
            "any mention of \u201cno read up / no write down\u201d, classifications, or protecting "
            "<em>confidentiality</em> with labels = Bell-LaPadula.")
    + model("biba", "#4FD8C4", "Integrity · mandatory access control",
            "Biba",
            "Bell-LaPadula flipped upside down, protecting <em>integrity</em> instead of secrecy: stop "
            "bad (low-integrity) data contaminating good (high-integrity) data.",
            ["<strong>Simple Integrity Property</strong> — no read <em>down</em> (don't consume data "
             "less trustworthy than you).",
             "<strong>★ Integrity Property</strong> — no write <em>up</em> (don't let less trustworthy "
             "processes modify more trustworthy data).",
             "Invocation property — can't invoke services at a higher integrity level."],
            "\u201cno read down / no write up\u201d or any question about protecting data "
            "<em>trustworthiness</em> = Biba. If the rules look like BLP inverted, it IS Biba.")
    + model("cw", "#E7A15A", "Integrity · commercial",
            "Clark-Wilson",
            "Commercial integrity without labels: users never touch data directly. All changes go "
            "through vetted programs, so integrity comes from <em>how</em> data is changed, not who "
            "outranks whom.",
            ["<strong>Access triple</strong> — subject → Transformation Procedure (TP) → Constrained "
             "Data Item (CDI); never subject → data directly.",
             "<strong>Well-formed transactions</strong> — TPs move CDIs from one valid state to another.",
             "<strong>IVPs</strong> — Integrity Verification Procedures confirm data validity.",
             "<strong>Separation of duties</strong> is enforced by certifying who may run which TP.",
             "UDIs — unconstrained (unvetted) inputs that TPs must sanitize."],
            "\u201cwell-formed transactions\u201d, \u201caccess triple\u201d, or integrity + "
            "<em>separation of duties</em> = Clark-Wilson.")
    + model("bn", "#E57373", "Conflict of interest · dynamic",
            "Brewer-Nash (Chinese Wall)",
            "Built for consultancies and brokerages: prevent conflicts of interest. Access rights "
            "change <em>dynamically</em> based on what a user has already accessed.",
            ["Data is grouped into conflict-of-interest classes (e.g. competing banks).",
             "Touch Bank A's dataset and the wall goes up: Bank B's dataset in the same class "
             "becomes off-limits.",
             "The only classic model whose permissions depend on a user's access <em>history</em>."],
            "\u201cconflict of interest\u201d, \u201cconsultants serving competitors\u201d, or access "
            "that changes based on prior activity = Brewer-Nash.")
    + '<div class="sm-note"><div class="sm-note__t">The trap the exam loves</div>'
    "Bell-LaPadula and Biba are mirror images. BLP protects <strong>confidentiality</strong>: "
    "no read UP, no write DOWN. Biba protects <strong>integrity</strong>: no read DOWN, no write UP. "
    "Fix the pair \u201cBLP = secrets, Biba = trust\u201d and derive the arrows — never memorize four "
    "rules separately.</div>"
    "</section>"

    "<section><h2>The supporting cast</h2>"
    '<div class="sm-tablewrap"><table class="sm-table">'
    "<tr><th>Model</th><th>Protects / does</th><th>Remember it by</th></tr>"
    "<tr><td>State machine</td><td>Foundation: system is secure if every state and transition is secure.</td>"
    "<td>The parent idea under BLP and Biba.</td></tr>"
    "<tr><td>Information flow</td><td>Controls <em>where data may move</em>, not just who reads it.</td>"
    "<td>BLP/Biba restated as flow rules.</td></tr>"
    "<tr><td>Noninterference</td><td>Actions at a high level must be invisible at lower levels.</td>"
    "<td>Stops covert signalling, not just direct reads.</td></tr>"
    "<tr><td>Lattice-based</td><td>Every subject/object gets a position in a lattice of labels; access "
    "follows least upper / greatest lower bounds.</td><td>The mathematical scaffolding of MAC.</td></tr>"
    "<tr><td>Graham-Denning</td><td>How subjects, objects and rights are managed — eight rules: create/delete "
    "subject, create/delete object, and grant/transfer/delete/read access rights.</td>"
    "<td>Eight administrative rules.</td></tr>"
    "<tr><td>Harrison-Ruzzo-Ullman (HRU)</td><td>Extends Graham-Denning: is there any sequence of operations that "
    "leaks a right? (Generally undecidable.)</td><td>Rights-amendment analysis.</td></tr>"
    "<tr><td>Take-Grant</td><td>Directed graph with four rules — take, grant, create, revoke — showing how "
    "rights can propagate between subjects.</td><td>Four verbs on a graph.</td></tr>"
    "</table></div>"
    '<div class="sm-note"><div class="sm-note__t">Don\u2019t confuse models with evaluation criteria</div>'
    "TCSEC (the Orange Book), ITSEC and the Common Criteria (EAL 1\u20137) are frameworks for "
    "<em>evaluating</em> systems — they use models, but they are not security models themselves. "
    "If the question mentions assurance levels or certification, it\u2019s asking about evaluation "
    "criteria, not a model.</div>"
    "</section>"

    "<section><h2>Cheat table</h2>"
    '<div class="sm-tablewrap"><table class="sm-table">'
    "<tr><th>If the question says\u2026</th><th>Answer</th></tr>"
    "<tr><td>No read up / no write down</td><td>Bell-LaPadula</td></tr>"
    "<tr><td>No read down / no write up</td><td>Biba</td></tr>"
    "<tr><td>Well-formed transactions, access triples, IVPs</td><td>Clark-Wilson</td></tr>"
    "<tr><td>Conflict of interest, access based on history</td><td>Brewer-Nash</td></tr>"
    "<tr><td>Eight rules for managing rights</td><td>Graham-Denning</td></tr>"
    "<tr><td>Take, grant, create, revoke</td><td>Take-Grant</td></tr>"
    "<tr><td>High-level actions invisible below</td><td>Noninterference</td></tr>"
    "<tr><td>Assurance / EAL levels</td><td>Evaluation criteria (Common Criteria), not a model</td></tr>"
    "</table></div>"
    "<p>Drill these as questions in <a href=\"cissp-flashcards.html?domain=3\">Domain 3 flashcards "
    "and exam practice</a>.</p>"
    "</section>"

    "<section>"
    '<p class="sm-foot">Further study: the official <a href="' + ISC2_OUTLINE_URL + '" target="_blank" '
    'rel="noopener">ISC2 CISSP Exam Outline</a>. This page is an independently written study summary.</p>'
    '<p class="sm-foot">' + DISCLAIMER + "</p>"
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
article.excerpt = ("Bell-LaPadula vs Biba vs Clark-Wilson vs Brewer-Nash — the rules, the "
                   "directionality traps, and the exam tells, in plain English.")
article.body_md = BODY
article.meta_title = TITLE
article.meta_description = META_DESCRIPTION
article.save()
print(("created" if created else "updated"), "article", SLUG, "| body bytes:", len(BODY))
