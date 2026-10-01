# -*- coding: utf-8 -*-
"""CISSP Chapter Score Tracker — map question-bank chapter scores onto the
eight CISSP domains.

Creates/updates the EvergreenArticle at /insights/cissp-score-tracker.html.
The 21-chapter structure mirrors the common study-guide layout (shortened,
paraphrased labels); scores live ONLY in the browser:
localStorage "mg_cissp_wiley_v1" -> {version:1, chapters:{"<n>":{c,t}}, updated}.
Flashcard-progress column reads mg_cissp_flashcards_v1 + the shared JSON.

Run:
  python manage.py shell -c "exec(open(r'C:\\Projects\\foundry\\scripts\\generate_cissp_score_tracker.py', encoding='utf-8').read())"
Then build_site.
"""

SLUG = "cissp-score-tracker"
TITLE = "CISSP Chapter Score Tracker: Roll Your Practice Scores Up to the 8 Domains"
META_DESCRIPTION = ("Track your CISSP practice-test chapter scores and see them rolled up to the "
                    "eight exam domains — with exam weights, weak-domain flags and flashcard "
                    "progress side by side. Free, no sign-up, data stays in your browser.")
DISCLAIMER = ("Independent CISSP study aid. CISSP is a registered trademark of ISC2. "
              "This resource is not affiliated with or endorsed by ISC2, Wiley or Sybex. "
              "Scores are your own study data and never leave your browser.")

# (chapter number, short paraphrased label, domain key)
CHAPTERS = [
    (1, "Security governance & policies", "risk"),
    (2, "Personnel security & risk concepts", "risk"),
    (3, "Business continuity planning", "risk"),
    (4, "Laws, regulations & compliance", "risk"),
    (5, "Protecting security of assets", "data"),
    (6, "Cryptography & symmetric algorithms", "crypto"),
    (7, "PKI & cryptographic applications", "crypto"),
    (8, "Security models, design & capabilities", "crypto"),
    (9, "Vulnerabilities, threats & countermeasures", "crypto"),
    (10, "Physical security requirements", "crypto"),
    (11, "Secure network architecture & components", "network"),
    (12, "Secure communications & network attacks", "network"),
    (13, "Managing identity & authentication", "iam"),
    (14, "Controlling & monitoring access", "iam"),
    (15, "Security assessment & testing", "assess"),
    (16, "Managing security operations", "ops"),
    (17, "Preventing & responding to incidents", "ops"),
    (18, "Disaster recovery planning", "ops"),
    (19, "Investigations & ethics", "ops"),
    (20, "Software development security", "cloud"),
    (21, "Malicious code & application attacks", "cloud"),
]

CSS = """
<style>
.wt-links{display:flex;gap:22px;flex-wrap:wrap;margin:10px 0 0}
.wt-links a{color:var(--site-gold,#d9b36b);font-weight:600;text-decoration:none;border-bottom:1px solid var(--site-gold,#d9b36b)}
.wt-dash{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0 22px}
.wt-dash__cell{border:1px solid var(--site-border,rgba(148,163,199,.2));border-radius:10px;padding:10px 12px;background:var(--site-surface,rgba(255,255,255,.03))}
.wt-dash__v{font-size:1.3rem;font-weight:700;color:var(--site-heading,#f4f6f9)}
.wt-dash__l{font-size:.74rem;color:var(--site-muted,#8b93a7);text-transform:uppercase;letter-spacing:.05em}
.wt-table{width:100%;border-collapse:collapse;font-size:.9rem}
.wt-table th{text-align:left;color:var(--site-gold,#d9b36b);font-size:.74rem;letter-spacing:.06em;text-transform:uppercase;
  padding:8px 10px;border-bottom:1px solid var(--site-border,rgba(148,163,199,.25))}
.wt-table td{padding:9px 10px;border-bottom:1px solid var(--site-border,rgba(148,163,199,.12));color:var(--site-text,#dfe4ee)}
.wt-tablewrap{overflow-x:auto}
.wt-st{font-weight:700}
.wt-st--strong{color:var(--site-accent,#5dd6c6)}
.wt-st--prog{color:var(--site-gold,#d9b36b)}
.wt-st--weak{color:#e5484d}
.wt-st--none{color:var(--site-muted,#8b93a7);font-weight:400}
.wt-dgroup{margin:22px 0 8px;font-family:var(--site-heading-font,'Space Grotesk',sans-serif);font-weight:700;
  color:var(--site-heading,#f4f6f9);font-size:1rem}
.wt-dgroup .wt-w{color:var(--site-muted,#8b93a7);font-weight:400;font-size:.85rem}
.wt-row{display:flex;align-items:center;gap:12px;padding:7px 0;border-bottom:1px solid var(--site-border,rgba(148,163,199,.1));flex-wrap:wrap}
.wt-row__n{min-width:4.4rem;font-weight:700;color:var(--site-muted,#8b93a7);font-size:.85rem}
.wt-row__t{flex:1;min-width:200px}
.wt-in{width:64px;padding:7px 9px;border-radius:8px;font:inherit;text-align:center;
  border:1px solid var(--site-border,rgba(148,163,199,.25));background:var(--site-surface,rgba(255,255,255,.03));
  color:var(--site-text,#dfe4ee)}
.wt-in:focus{outline:none;border-color:var(--site-accent,#5dd6c6);box-shadow:0 0 0 3px rgba(93,214,198,.16)}
.wt-of{color:var(--site-muted,#8b93a7);font-size:.85rem}
.wt-pct{min-width:3.4rem;text-align:right;font-weight:700}
.wt-mgmt{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}
.wt-chip{font:inherit;font-size:.82rem;font-weight:600;padding:7px 14px;border-radius:999px;cursor:pointer;
  border:1px solid var(--site-border,rgba(148,163,199,.25));color:var(--site-text,#dfe4ee);
  background:var(--site-surface,rgba(255,255,255,.03))}
.wt-chip:hover{border-color:var(--site-accent,#5dd6c6)}
.wt-chip:focus-visible,.wt-in:focus-visible{outline:2px solid var(--site-accent,#5dd6c6);outline-offset:2px}
.wt-foot{font-size:.85rem;color:var(--site-muted,#8b93a7);margin-top:14px}
</style>
"""


def chapter_rows():
    out, last_dom = [], None
    for num, label, dom in CHAPTERS:
        if dom != last_dom:
            out.append('<div class="wt-dgroup" data-dgroup="' + dom + '"></div>')
            last_dom = dom
        out.append(
            '<div class="wt-row" data-dom="' + dom + '">'
            '<span class="wt-row__n">Ch ' + str(num) + '</span>'
            '<span class="wt-row__t">' + label + "</span>"
            '<label class="wt-of" for="wt-c-' + str(num) + '">correct</label>'
            '<input class="wt-in" id="wt-c-' + str(num) + '" data-ch="' + str(num) + '" data-f="c" '
            'type="number" min="0" max="99" inputmode="numeric" aria-label="Chapter ' + str(num) + ' correct answers">'
            '<span class="wt-of">of</span>'
            '<input class="wt-in" data-ch="' + str(num) + '" data-f="t" type="number" min="1" max="99" '
            'inputmode="numeric" value="20" aria-label="Chapter ' + str(num) + ' total questions">'
            '<span class="wt-pct" data-pct="' + str(num) + '"></span>'
            "</div>")
    return "".join(out)


JS = """
<script>
(function () {
  "use strict";
  var LS = "mg_cissp_wiley_v1", FC = "mg_cissp_flashcards_v1";
  var DATA_URL = "../assets/data/cissp-glossary.json";
  var app = document.getElementById("wt-app");
  if (!app) return;
  document.getElementById("wt-nojs").hidden = true;
  document.getElementById("wt-ui").hidden = false;

  var CHAPTERS = JSON.parse(document.getElementById("wt-chapters").textContent);
  var store = load();
  var domains = null, fcByCat = null;

  function load() {
    try {
      var v = JSON.parse(localStorage.getItem(LS));
      if (v && v.version === 1 && v.chapters) return v;
    } catch (e) {}
    return { version: 1, chapters: {}, updated: null };
  }
  function save() {
    store.updated = new Date().toISOString();
    try { localStorage.setItem(LS, JSON.stringify(store)); } catch (e) {}
  }
  function pctCls(p) {
    return p >= 80 ? "wt-st--strong" : p >= 60 ? "wt-st--prog" : "wt-st--weak";
  }
  function pctWord(p) {
    return p >= 80 ? "Strong" : p >= 60 ? "In progress" : "Needs work";
  }

  function recompute() {
    var byDom = {}, doneCh = 0, sumC = 0, sumT = 0;
    CHAPTERS.forEach(function (ch) {
      var s = store.chapters[ch.n];
      var el = document.querySelector('[data-pct="' + ch.n + '"]');
      var b = byDom[ch.d] || (byDom[ch.d] = { c: 0, t: 0, done: 0, total: 0 });
      b.total++;
      if (s && s.t > 0 && s.c != null) {
        var p = Math.round(100 * s.c / s.t);
        el.textContent = p + "%";
        el.className = "wt-pct wt-st " + pctCls(p);
        b.c += s.c; b.t += s.t; b.done++;
        doneCh++; sumC += s.c; sumT += s.t;
      } else { el.textContent = ""; }
    });

    // domain rollup table
    var rows = "";
    var wSum = 0, wPct = 0, strongDomains = 0;
    (domains || []).forEach(function (d) {
      var b = byDom[d.key] || { c: 0, t: 0, done: 0, total: 0 };
      var pct = b.t ? Math.round(100 * b.c / b.t) : null;
      var st = pct == null ? '<span class="wt-st wt-st--none">Not started</span>'
        : '<span class="wt-st ' + pctCls(pct) + '">' + pctWord(pct) + "</span>";
      if (pct != null) { wSum += d.weight; wPct += d.weight * pct; if (pct >= 80) strongDomains++; }
      var fc = "";
      if (fcByCat && fcByCat[d.key]) fc = fcByCat[d.key].seen + " / " + fcByCat[d.key].total;
      rows += "<tr><td>D" + d.number + "</td><td>" + d.name + "</td><td>" + d.weight + "%</td>" +
        "<td>" + b.done + " / " + b.total + "</td>" +
        "<td>" + (pct == null ? "—" : b.c + " / " + b.t + " (" + pct + "%)") + "</td>" +
        "<td>" + st + "</td><td>" + fc + "</td></tr>";
    });
    document.getElementById("wt-dbody").innerHTML = rows;

    var raw = sumT ? Math.round(100 * sumC / sumT) : 0;
    var wa = wSum ? Math.round(wPct / wSum) : 0;
    var cells = [
      [doneCh + " / " + CHAPTERS.length, "Chapters entered"],
      [sumT ? raw + "%" : "—", "Raw average"],
      [wSum ? wa + "%" : "—", "Weight-adjusted (attempted)"],
      [strongDomains + " / 8", "Domains at 80%+"]
    ];
    document.getElementById("wt-dash").innerHTML = cells.map(function (c) {
      return '<div class="wt-dash__cell"><div class="wt-dash__v">' + c[0] +
             '</div><div class="wt-dash__l">' + c[1] + "</div></div>";
    }).join("");
  }

  // inputs
  Array.prototype.forEach.call(document.querySelectorAll(".wt-in"), function (inp) {
    var n = inp.dataset.ch, f = inp.dataset.f;
    var s = store.chapters[n];
    if (s) { if (f === "c" && s.c != null) inp.value = s.c; if (f === "t" && s.t) inp.value = s.t; }
    inp.addEventListener("input", function () {
      var s2 = store.chapters[n] || (store.chapters[n] = { c: null, t: 20 });
      var v = inp.value === "" ? null : Math.max(0, parseInt(inp.value, 10) || 0);
      if (f === "c") s2.c = v; else s2.t = v || 20;
      if (s2.c == null && f === "c") delete store.chapters[n].c;
      if (s2.c == null && (s2.t === 20 || !s2.t)) delete store.chapters[n];
      save(); recompute();
    });
  });

  // export / import / reset (same pattern as the flashcards)
  document.getElementById("wt-export").addEventListener("click", function () {
    var blob = new Blob([JSON.stringify(store, null, 1)], { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "cissp-chapter-scores.json";
    document.body.appendChild(a); a.click(); a.remove();
  });
  var fileInput = document.getElementById("wt-import-file");
  document.getElementById("wt-import").addEventListener("click", function () { fileInput.click(); });
  fileInput.addEventListener("change", function () {
    if (!fileInput.files || !fileInput.files[0]) return;
    var rd = new FileReader();
    rd.onload = function () {
      var v = null;
      try { v = JSON.parse(rd.result); } catch (e) {}
      var ok = v && v.version === 1 && typeof v.chapters === "object" && v.chapters !== null &&
        Object.keys(v.chapters).every(function (k) {
          var s = v.chapters[k];
          return s && (s.c == null || typeof s.c === "number") && typeof s.t === "number";
        });
      if (!ok) { alert("That file is not a valid chapter-score export."); return; }
      if (!confirm("Replace your current chapter scores with the imported file?")) return;
      store = v; save();
      Array.prototype.forEach.call(document.querySelectorAll(".wt-in"), function (inp) {
        var s = store.chapters[inp.dataset.ch];
        inp.value = inp.dataset.f === "c" ? (s && s.c != null ? s.c : "") : (s && s.t ? s.t : 20);
      });
      recompute();
    };
    rd.readAsText(fileInput.files[0]);
    fileInput.value = "";
  });
  document.getElementById("wt-reset").addEventListener("click", function () {
    if (!confirm("Reset ALL chapter scores stored in this browser?")) return;
    store = { version: 1, chapters: {}, updated: null };
    try { localStorage.removeItem(LS); } catch (e) {}
    Array.prototype.forEach.call(document.querySelectorAll(".wt-in"), function (inp) {
      inp.value = inp.dataset.f === "t" ? 20 : "";
    });
    recompute();
  });

  // shared data: domain names/weights + flashcard progress column
  fetch(DATA_URL).then(function (r) { return r.json(); }).then(function (data) {
    domains = data.domains;
    // group labels
    var byKey = {};
    domains.forEach(function (d) { byKey[d.key] = d; });
    Array.prototype.forEach.call(document.querySelectorAll("[data-dgroup]"), function (el) {
      var d = byKey[el.dataset.dgroup];
      if (d) el.innerHTML = "Domain " + d.number + " — " + d.name +
        ' <span class="wt-w">' + d.weight + "% of the exam</span>";
    });
    var prog = null;
    try { prog = JSON.parse(localStorage.getItem(FC)); } catch (e) {}
    var cards = prog && prog.cards ? prog.cards : {};
    fcByCat = {};
    data.terms.forEach(function (t) {
      var b = fcByCat[t.category] || (fcByCat[t.category] = { total: 0, seen: 0 });
      b.total++;
      if (cards[t.id] && cards[t.id].r > 0) b.seen++;
    });
    recompute();
  }).catch(function () { domains = []; recompute(); });
})();
</script>
"""


def build_body():
    return (
        "<section>" + CSS
        + "<section>"
        "<p>Chapter-based question banks don't show you domain-level readiness — this tracker does "
        "the mapping. Enter your score after each chapter test and the 21 chapters roll up to the "
        "eight CISSP domains, weighted the way the exam weights them. A common community rule of "
        "thumb is to aim for roughly 80% per domain on practice banks before booking; treat that as "
        "a heuristic, not a guarantee.</p>"
        '<p class="wt-links"><a href="cissp-security-glossary.html">CISSP Glossary →</a>'
        '<a href="cissp-flashcards.html">CISSP Flashcards →</a>'
        '<a href="cissp-mind-map.html">Syllabus Mind Map →</a></p>'
        "</section>"
        '<section><div id="wt-app">'
        '<p id="wt-nojs">The score tracker needs JavaScript. The domain mapping itself is simple: '
        "chapters 1–4 → Domain 1, 5 → D2, 6–10 → D3, 11–12 → D4, 13–14 → D5, 15 → D6, "
        "16–19 → D7, 20–21 → D8.</p>"
        '<div id="wt-ui" hidden>'
        '<div class="wt-dash" id="wt-dash" aria-label="Overall readiness summary"></div>'
        '<div class="wt-tablewrap"><table class="wt-table" aria-label="Domain rollup">'
        "<thead><tr><th>Domain</th><th>Name</th><th>Weight</th><th>Chapters</th>"
        "<th>Score</th><th>Status</th><th>Flashcard terms reviewed</th></tr></thead>"
        '<tbody id="wt-dbody"></tbody></table></div>'
        '<h2 style="font-size:1.2rem;margin-top:26px">Enter your chapter scores</h2>'
        + chapter_rows() +
        '<div class="wt-mgmt">'
        '<button type="button" class="wt-chip" id="wt-export">Export scores</button>'
        '<button type="button" class="wt-chip" id="wt-import">Import scores</button>'
        '<input type="file" id="wt-import-file" accept="application/json" hidden aria-label="Import scores file">'
        '<button type="button" class="wt-chip" id="wt-reset">Reset scores</button>'
        "</div>"
        '<p class="wt-foot">Scores are stored only in this browser (localStorage) — export to move '
        "between machines. Practice-bank percentages are study feedback, not a prediction of exam "
        "readiness.</p>"
        "</div></div>"
        '<script type="application/json" id="wt-chapters">'
        + __import__("json").dumps([{"n": n, "d": d} for n, _l, d in CHAPTERS])
        + "</script>"
        "</section>"
        "<section>"
        '<p class="wt-foot">' + DISCLAIMER + "</p>"
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
article.excerpt = ("Enter chapter-test scores, see them rolled up to the eight CISSP domains with "
                   "exam weights and weak-domain flags — beside your flashcard progress.")
article.body_md = body
article.meta_title = TITLE
article.meta_description = META_DESCRIPTION
article.save()
print(("created" if created else "updated"), "article", SLUG, "| body bytes:", len(body),
      "| chapters:", len(CHAPTERS))
