# -*- coding: utf-8 -*-
"""CISSP Flashcards — interactive study tool article generator.

Creates/updates the EvergreenArticle at /insights/cissp-flashcards.html.
The page is a self-contained vanilla-JS app (inline CSS/JS, no libraries)
that consumes the SHARED data source written by generate_cissp_glossary.py:
    assets/data/cissp-glossary.json   (terms + original scenario cards)

Spaced repetition (SM-2-lite, per card): Again resets the interval and re-queues
the card ~3 positions later; Hard ~= interval x1.2 (min 1 day); Good x2.5;
Easy x4 (unseen: 1d / 3d), capped at 120 days. Confidence 0-5 moves -2/-1/+1/+2.
Progress lives ONLY in the browser: localStorage key "mg_cissp_flashcards_v1"
-> {version:1, cards:{<id>:{r,c,m,conf,iv,due,last}}, updated}. Export/Import
round-trips that object as a JSON download; imports are validated first.

Run:
  python manage.py shell -c "exec(open(r'C:\\Projects\\foundry\\scripts\\generate_cissp_flashcards.py', encoding='utf-8').read())"
Then build_site. (Run generate_cissp_glossary.py first so the JSON exists.)
"""

SLUG = "cissp-flashcards"
TITLE = "CISSP Flashcards: Security Acronyms & Concepts"
META_DESCRIPTION = ("Interactive CISSP flashcards for studying cybersecurity acronyms, IAM, "
                    "cryptography, networking, security operations, risk management and "
                    "secure software development.")
DISCLAIMER = ("Independent CISSP study aid. CISSP is a registered trademark of ISC2. "
              "This resource is not affiliated with or endorsed by ISC2.")

CSS = """
<style>
.fc-wrap{max-width:860px}
.fc-dash{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin:16px 0}
.fc-dash__cell{border:1px solid var(--site-border,rgba(148,163,199,.2));border-radius:10px;padding:10px 12px;background:var(--site-surface,rgba(255,255,255,.03))}
.fc-dash__v{font-size:1.25rem;font-weight:700;color:var(--site-heading,#f4f6f9)}
.fc-dash__l{font-size:.75rem;color:var(--site-muted,#8b93a7);text-transform:uppercase;letter-spacing:.05em}
.fc-label{font-size:.8rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--site-muted,#8b93a7);margin:18px 0 8px}
.fc-chips{display:flex;flex-wrap:wrap;gap:8px}
.fc-chip{font:inherit;font-size:.85rem;font-weight:600;padding:7px 14px;border-radius:999px;cursor:pointer;
  border:1px solid var(--site-border,rgba(148,163,199,.25));color:var(--site-text,#dfe4ee);
  background:var(--site-surface,rgba(255,255,255,.03))}
.fc-chip:hover{border-color:var(--site-accent,#5dd6c6)}
.fc-chip.is-on{border-color:var(--site-accent,#5dd6c6);color:var(--site-accent,#5dd6c6)}
.fc-chip:focus-visible,.fc-btn:focus-visible,.fc-card:focus-visible{outline:2px solid var(--site-accent,#5dd6c6);outline-offset:2px}
.fc-start{margin-top:18px}
.fc-btn{font:inherit;font-weight:700;padding:12px 22px;border-radius:10px;cursor:pointer;border:1px solid transparent}
.fc-btn--primary{background:var(--site-accent,#5dd6c6);color:var(--site-on-accent,#07120f)}
.fc-btn--primary:hover{filter:brightness(1.08)}
.fc-btn[disabled]{opacity:.4;cursor:not-allowed}
.fc-card{border:1px solid var(--site-border,rgba(148,163,199,.25));border-radius:16px;margin-top:18px;
  background:var(--site-surface,rgba(255,255,255,.03));padding:26px 26px 22px;min-height:240px;
  display:flex;flex-direction:column}
.fc-card__meta{display:flex;gap:8px;flex-wrap:wrap;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--site-muted,#8b93a7);margin-bottom:14px}
.fc-tag{border:1px solid var(--site-border,rgba(148,163,199,.25));border-radius:999px;padding:2px 10px}
.fc-tag--scenario{color:var(--site-gold,#d9b36b);border-color:var(--site-gold,#d9b36b)}
.fc-front{font-size:1.5rem;line-height:1.35;font-weight:700;color:var(--site-heading,#f4f6f9);margin:auto 0}
.fc-front--small{font-size:1.12rem;font-weight:500}
.fc-back{border-top:1px solid var(--site-border,rgba(148,163,199,.2));margin-top:18px;padding-top:16px}
.fc-back__answer{font-size:1.2rem;font-weight:700;color:var(--site-accent,#5dd6c6);margin:0 0 8px}
.fc-back__def{margin:0 0 8px;color:var(--site-text,#dfe4ee)}
.fc-back__tip{margin:0;font-size:.92rem;color:var(--site-muted,#8b93a7)}
.fc-back__tip strong{color:var(--site-gold,#d9b36b)}
.fc-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}
.fc-rate{flex:1;min-width:110px;text-align:center;background:transparent;color:var(--site-text,#dfe4ee)}
.fc-rate small{display:block;font-weight:400;font-size:.72rem;color:var(--site-muted,#8b93a7)}
.fc-rate--again{border-color:#e5484d}.fc-rate--again:hover{background:rgba(229,72,77,.12)}
.fc-rate--hard{border-color:var(--site-gold,#d9b36b)}.fc-rate--hard:hover{background:rgba(217,179,107,.12)}
.fc-rate--good{border-color:var(--site-accent,#5dd6c6)}.fc-rate--good:hover{background:rgba(93,214,198,.12)}
.fc-rate--easy{border-color:#7c8cf8}.fc-rate--easy:hover{background:rgba(124,140,248,.12)}
.fc-session{margin-top:12px;font-size:.9rem;color:var(--site-muted,#8b93a7)}
.fc-mgmt{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}
.fc-mgmt .fc-chip{font-size:.8rem}
.fc-note{font-size:.85rem;color:var(--site-muted,#8b93a7);margin-top:10px}
.fc-disclaimer{font-size:.85rem;color:var(--site-muted,#8b93a7);border-top:1px solid var(--site-border,rgba(148,163,199,.14));padding-top:14px;margin-top:24px}
.fc-glosslink a{color:var(--site-gold,#d9b36b);font-weight:600;text-decoration:none;border-bottom:1px solid var(--site-gold,#d9b36b)}
@media (max-width:640px){.fc-front{font-size:1.25rem}.fc-rate{min-width:46%}}
@media (prefers-reduced-motion:no-preference){.fc-card{transition:border-color .2s ease}}
</style>
"""

APP_HTML = """
<div class="fc-wrap" id="fc-app">
  <p id="fc-nojs">The interactive flashcards need JavaScript. All of the underlying terms are
  readable in the <a href="cissp-security-glossary.html">CISSP security glossary</a>.</p>

  <div id="fc-ui" hidden>
    <div class="fc-dash" id="fc-dash" aria-label="Study progress summary"></div>

    <div class="fc-label" id="fc-mode-label">Study mode</div>
    <div class="fc-chips" role="group" aria-labelledby="fc-mode-label" id="fc-modes">
      <button type="button" class="fc-chip is-on" data-mode="daily" aria-pressed="true">Daily Review</button>
      <button type="button" class="fc-chip" data-mode="quick" aria-pressed="false">Quick 10</button>
      <button type="button" class="fc-chip" data-mode="weak" aria-pressed="false">Weak Cards</button>
      <button type="button" class="fc-chip" data-mode="new" aria-pressed="false">New Cards</button>
      <button type="button" class="fc-chip" data-mode="all" aria-pressed="false">All Cards</button>
      <button type="button" class="fc-chip" data-mode="core" aria-pressed="false">Core CISSP Terms</button>
    </div>

    <div class="fc-label" id="fc-dir-label">Direction</div>
    <div class="fc-chips" role="group" aria-labelledby="fc-dir-label" id="fc-dirs">
      <button type="button" class="fc-chip is-on" data-dir="a2d" aria-pressed="true">Acronym → Definition</button>
      <button type="button" class="fc-chip" data-dir="d2a" aria-pressed="false">Definition → Acronym</button>
      <button type="button" class="fc-chip" data-dir="mix" aria-pressed="false">Mixed</button>
    </div>

    <div class="fc-label" id="fc-cat-label">Categories (multi-select)</div>
    <div class="fc-chips" role="group" aria-labelledby="fc-cat-label" id="fc-cats"></div>

    <div class="fc-start">
      <button type="button" class="fc-btn fc-btn--primary" id="fc-start">Start studying</button>
      <p class="fc-note" id="fc-pool-note"></p>
    </div>

    <div class="fc-card" id="fc-card" hidden aria-live="polite">
      <div class="fc-card__meta" id="fc-meta"></div>
      <div class="fc-front" id="fc-front"></div>
      <div class="fc-back" id="fc-back" hidden></div>
      <div class="fc-actions" id="fc-reveal-row">
        <button type="button" class="fc-btn fc-btn--primary" id="fc-reveal">Reveal answer <small>(Space)</small></button>
      </div>
      <div class="fc-actions" id="fc-rate-row" hidden>
        <button type="button" class="fc-btn fc-chip fc-rate fc-rate--again" data-rate="1">Again <small>1 · right away</small></button>
        <button type="button" class="fc-btn fc-chip fc-rate fc-rate--hard" data-rate="2">Hard <small>2 · short interval</small></button>
        <button type="button" class="fc-btn fc-chip fc-rate fc-rate--good" data-rate="3">Good <small>3 · normal interval</small></button>
        <button type="button" class="fc-btn fc-chip fc-rate fc-rate--easy" data-rate="4">Easy <small>4 · long interval</small></button>
      </div>
    </div>
    <p class="fc-session" id="fc-session" role="status" aria-live="polite"></p>

    <div class="fc-mgmt">
      <button type="button" class="fc-chip" id="fc-export">Export progress</button>
      <button type="button" class="fc-chip" id="fc-import">Import progress</button>
      <input type="file" id="fc-import-file" accept="application/json" hidden aria-label="Import progress file">
      <button type="button" class="fc-chip" id="fc-reset">Reset study progress</button>
    </div>
    <p class="fc-note">Progress is stored only in this browser (localStorage). Export it to move
    between machines or protect against cleared browser data.</p>
  </div>
</div>
"""

JS = """
<script>
(function () {
  "use strict";
  var LS_KEY = "mg_cissp_flashcards_v1";
  var DATA_URL = "../assets/data/cissp-glossary.json";
  var DAY = 86400000;
  var app = document.getElementById("fc-app");
  if (!app) return;

  var data = null, cards = [], byId = {};
  var progress = load();
  var sel = { mode: "daily", dir: "a2d", cats: {} };
  var session = null;

  function today() { return Math.floor(Date.now() / DAY); }
  function load() {
    try {
      var raw = localStorage.getItem(LS_KEY);
      if (raw) { var v = JSON.parse(raw); if (v && v.version === 1 && v.cards) return v; }
    } catch (e) {}
    return { version: 1, cards: {}, updated: null };
  }
  function save() {
    progress.updated = new Date().toISOString();
    try { localStorage.setItem(LS_KEY, JSON.stringify(progress)); } catch (e) {}
  }
  function st(id) { return progress.cards[id]; }
  function isWeak(s) { return s && s.r > 0 && (s.conf <= 1 || s.m * 2 >= s.r); }
  function isStrong(s) { return s && s.r > 0 && s.conf >= 4; }
  function isDue(s) { return s && s.r > 0 && s.due <= today(); }
  function shuffle(a) {
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1)), t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  // ---- spaced repetition -------------------------------------------------
  function rate(card, g) {
    var s = progress.cards[card.id];
    if (!s) s = progress.cards[card.id] = { r: 0, c: 0, m: 0, conf: 0, iv: 0, due: today(), last: 0 };
    s.r++;
    if (g === 1) { s.m++; s.conf = Math.max(0, s.conf - 2); s.iv = 0; }
    else if (g === 2) { s.c++; s.conf = Math.max(1, s.conf - 1); s.iv = s.iv < 1 ? 1 : Math.max(1, Math.round(s.iv * 1.2)); }
    else if (g === 3) { s.c++; s.conf = Math.min(5, s.conf + 1); s.iv = s.iv < 1 ? 1 : Math.round(s.iv * 2.5); }
    else { s.c++; s.conf = Math.min(5, s.conf + 2); s.iv = s.iv < 1 ? 3 : Math.round(s.iv * 4); }
    s.iv = Math.min(s.iv, 120);
    s.due = today() + s.iv;
    s.last = Date.now();
    save();
  }

  // ---- pools & modes -----------------------------------------------------
  function pool() {
    return cards.filter(function (c) {
      if (!sel.cats[c.category]) return false;
      if (sel.mode === "core") return c.type !== "scenario" && c.priority === "Core";
      return true;
    });
  }
  function buildQueue() {
    var p = pool(), q = [];
    if (sel.mode === "daily") {
      var due = p.filter(function (c) { return isDue(st(c.id)); })
                 .sort(function (a, b) { return st(a.id).due - st(b.id).due; });
      q = due.slice(0, 10);
      if (q.length < 10) {
        var fresh = shuffle(p.filter(function (c) { return !st(c.id); })).slice(0, 10 - q.length);
        q = q.concat(fresh);
      }
    } else if (sel.mode === "quick") { q = shuffle(p.slice()).slice(0, 10); }
    else if (sel.mode === "weak") { q = shuffle(p.filter(function (c) { return isWeak(st(c.id)); })); }
    else if (sel.mode === "new") { q = shuffle(p.filter(function (c) { return !st(c.id); })); }
    else { q = shuffle(p.slice()); }
    return q;
  }

  // ---- dashboard ---------------------------------------------------------
  function dash() {
    var seen = 0, due = 0, strong = 0, weak = 0, sumR = 0, sumC = 0;
    cards.forEach(function (c) {
      var s = st(c.id);
      if (s && s.r > 0) {
        seen++; sumR += s.r; sumC += s.c;
        if (isDue(s)) due++;
        if (isStrong(s)) strong++;
        if (isWeak(s)) weak++;
      }
    });
    var recall = sumR ? Math.round(100 * sumC / sumR) : 0;
    var cells = [
      [data.terms.length + " + " + data.scenarios.length, "Terms + scenarios"],
      [seen, "Reviewed"], [cards.length - seen, "Not yet studied"], [due, "Due today"],
      [strong, "Strong"], [weak, "Weak"], [recall + "%", "Recall rate"]
    ];
    document.getElementById("fc-dash").innerHTML = cells.map(function (c) {
      return '<div class="fc-dash__cell"><div class="fc-dash__v">' + c[0] +
             '</div><div class="fc-dash__l">' + c[1] + "</div></div>";
    }).join("");
    var note = document.getElementById("fc-pool-note");
    note.textContent = pool().length + " cards match the current mode and categories.";
  }

  // ---- rendering ---------------------------------------------------------
  var esc = function (s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  };
  function cardDir(card) {
    if (card.type === "scenario") return "scenario";
    if (sel.dir === "mix") return Math.random() < 0.5 ? "a2d" : "d2a";
    return sel.dir;
  }
  function show() {
    var cardEl = document.getElementById("fc-card");
    if (session.idx >= session.queue.length) { return finish(); }
    var item = session.queue[session.idx];
    session.current = item;
    item.dirNow = cardDir(item);
    cardEl.hidden = false;
    document.getElementById("fc-back").hidden = true;
    document.getElementById("fc-rate-row").hidden = true;
    document.getElementById("fc-reveal-row").hidden = false;
    session.revealed = false;

    var meta = '<span class="fc-tag">' + esc(item.category_label) + "</span>";
    if (item.type === "scenario") meta += '<span class="fc-tag fc-tag--scenario">Scenario</span>';
    else meta += '<span class="fc-tag">' + esc(item.priority) + "</span>";
    document.getElementById("fc-meta").innerHTML = meta;

    var front = document.getElementById("fc-front");
    if (item.dirNow === "scenario") { front.className = "fc-front fc-front--small"; front.textContent = item.question; }
    else if (item.dirNow === "a2d") { front.className = "fc-front"; front.textContent = item.acronym; }
    else { front.className = "fc-front fc-front--small"; front.textContent = item.definition; }
    sessionStatus();
  }
  function reveal() {
    if (!session || session.revealed) return;
    var item = session.current, back = document.getElementById("fc-back"), h = "";
    if (item.type === "scenario") {
      var t = byId[item.term_id];
      h = '<p class="fc-back__answer">' + esc(item.answer_acronym) + " — " + esc(item.answer_term) + "</p>" +
          (t ? '<p class="fc-back__def">' + esc(t.definition) + "</p>" : "") +
          (t && t.study_tip ? '<p class="fc-back__tip"><strong>Study tip:</strong> ' + esc(t.study_tip) + "</p>" : "");
    } else if (item.dirNow === "a2d") {
      h = '<p class="fc-back__answer">' + esc(item.full_term) + "</p>" +
          '<p class="fc-back__def">' + esc(item.definition) + "</p>" +
          (item.study_tip ? '<p class="fc-back__tip"><strong>Study tip:</strong> ' + esc(item.study_tip) + "</p>" : "");
    } else {
      h = '<p class="fc-back__answer">' + esc(item.acronym) + " — " + esc(item.full_term) + "</p>" +
          (item.study_tip ? '<p class="fc-back__tip"><strong>Study tip:</strong> ' + esc(item.study_tip) + "</p>" : "");
    }
    back.innerHTML = h;
    back.hidden = false;
    document.getElementById("fc-reveal-row").hidden = true;
    document.getElementById("fc-rate-row").hidden = false;
    session.revealed = true;
  }
  function onRate(g) {
    if (!session || !session.revealed) return;
    var item = session.current;
    rate(item, g);
    session.done++;
    if (g === 1) {
      session.again++;
      session.queue.splice(Math.min(session.idx + 3, session.queue.length), 0, item);
    }
    session.idx++;
    dash();
    show();
  }
  function sessionStatus() {
    document.getElementById("fc-session").textContent =
      "Card " + (session.idx + 1) + " of " + session.queue.length +
      (session.again ? " (" + session.again + " re-queued)" : "");
  }
  function finish() {
    document.getElementById("fc-card").hidden = true;
    var acc = session.done ? Math.round(100 * (session.done - session.again) / session.done) : 0;
    document.getElementById("fc-session").textContent =
      "Session complete: " + session.done + " reviews, " + acc + "% rated Hard or better. " +
      "Pick a mode and press Start studying to go again.";
    session = null;
  }
  function start() {
    var q = buildQueue();
    if (!q.length) {
      document.getElementById("fc-session").textContent =
        "No cards match this mode and category selection right now.";
      document.getElementById("fc-card").hidden = true;
      return;
    }
    session = { queue: q, idx: 0, done: 0, again: 0, revealed: false, current: null };
    show();
  }

  // ---- controls ----------------------------------------------------------
  function bindChips(rootId, key, cb) {
    var root = document.getElementById(rootId);
    root.addEventListener("click", function (ev) {
      var chip = ev.target.closest(".fc-chip");
      if (!chip) return;
      Array.prototype.forEach.call(root.querySelectorAll(".fc-chip"), function (c) {
        var on = c === chip;
        c.classList.toggle("is-on", on);
        c.setAttribute("aria-pressed", on ? "true" : "false");
      });
      sel[key] = chip.dataset[cb];
      dash();
    });
  }
  function buildCatChips() {
    var root = document.getElementById("fc-cats"), h = "";
    Object.keys(data.categories).forEach(function (k) {
      sel.cats[k] = true;
      h += '<button type="button" class="fc-chip is-on" data-cat="' + k +
           '" aria-pressed="true">' + esc(data.categories[k]) + "</button>";
    });
    root.innerHTML = h;
    root.addEventListener("click", function (ev) {
      var chip = ev.target.closest(".fc-chip");
      if (!chip) return;
      var k = chip.dataset.cat, on = !sel.cats[k];
      var onCount = Object.keys(sel.cats).filter(function (x) { return sel.cats[x]; }).length;
      if (!on && onCount === 1) return; // keep at least one category selected
      sel.cats[k] = on;
      chip.classList.toggle("is-on", on);
      chip.setAttribute("aria-pressed", on ? "true" : "false");
      dash();
    });
  }

  // ---- data management ---------------------------------------------------
  function doExport() {
    var blob = new Blob([JSON.stringify(progress, null, 1)], { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "cissp-flashcards-progress.json";
    document.body.appendChild(a); a.click(); a.remove();
  }
  function validImport(v) {
    if (!v || v.version !== 1 || typeof v.cards !== "object" || v.cards === null) return false;
    return Object.keys(v.cards).every(function (k) {
      var s = v.cards[k];
      return s && ["r", "c", "m", "conf", "iv", "due"].every(function (f) {
        return typeof s[f] === "number" && isFinite(s[f]);
      });
    });
  }
  function doImport(file) {
    var rd = new FileReader();
    rd.onload = function () {
      var v = null;
      try { v = JSON.parse(rd.result); } catch (e) {}
      if (!validImport(v)) { alert("That file is not a valid flashcards progress export."); return; }
      if (!confirm("Replace your current study progress with the imported file?")) return;
      progress = v; save(); dash();
      document.getElementById("fc-session").textContent = "Progress imported.";
    };
    rd.readAsText(file);
  }
  function doReset() {
    if (!confirm("Reset ALL flashcard study progress in this browser? This cannot be undone.")) return;
    progress = { version: 1, cards: {}, updated: null };
    try { localStorage.removeItem(LS_KEY); } catch (e) {}
    session = null;
    document.getElementById("fc-card").hidden = true;
    document.getElementById("fc-session").textContent = "Study progress has been reset.";
    dash();
  }

  // ---- keyboard ----------------------------------------------------------
  document.addEventListener("keydown", function (ev) {
    if (!session) return;
    var tag = (document.activeElement && document.activeElement.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (ev.key === " " && !session.revealed) { ev.preventDefault(); reveal(); }
    else if (session.revealed && ev.key >= "1" && ev.key <= "4") {
      ev.preventDefault(); onRate(parseInt(ev.key, 10));
    }
  });

  // ---- init --------------------------------------------------------------
  fetch(DATA_URL).then(function (r) {
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }).then(function (d) {
    data = d;
    cards = d.terms.concat(d.scenarios);
    cards.forEach(function (c) { byId[c.id] = c; });
    document.getElementById("fc-nojs").hidden = true;
    document.getElementById("fc-ui").hidden = false;
    bindChips("fc-modes", "mode", "mode");
    bindChips("fc-dirs", "dir", "dir");
    buildCatChips();
    document.getElementById("fc-start").addEventListener("click", start);
    document.getElementById("fc-reveal").addEventListener("click", reveal);
    document.getElementById("fc-rate-row").addEventListener("click", function (ev) {
      var b = ev.target.closest("[data-rate]");
      if (b) onRate(parseInt(b.dataset.rate, 10));
    });
    document.getElementById("fc-export").addEventListener("click", doExport);
    document.getElementById("fc-reset").addEventListener("click", doReset);
    var fileInput = document.getElementById("fc-import-file");
    document.getElementById("fc-import").addEventListener("click", function () { fileInput.click(); });
    fileInput.addEventListener("change", function () {
      if (fileInput.files && fileInput.files[0]) doImport(fileInput.files[0]);
      fileInput.value = "";
    });
    dash();
  }).catch(function (e) {
    document.getElementById("fc-nojs").textContent =
      "The flashcard data could not be loaded (" + e.message + "). " +
      "Please refresh, or browse the glossary instead.";
  });
})();
</script>
"""


def build_body():
    return (
        "<section>" + CSS
        + "<section>"
        "<p>Flashcards force <em>active recall</em> — retrieving an answer from memory instead "
        "of recognizing it on a page — and a light spaced-repetition schedule brings each card "
        "back just as you're about to forget it. This tool runs both over the full "
        "Mindsgate CISSP glossary: every acronym, definition and study tip, plus original "
        "scenario questions, in standard and reverse directions.</p>"
        '<p class="fc-glosslink"><a href="cissp-security-glossary.html">Browse the full CISSP '
        "glossary →</a></p>"
        "</section>"
        "<section>" + APP_HTML + "</section>"
        "<section>"
        '<p class="fc-disclaimer">' + DISCLAIMER + " Study-progress data never leaves your "
        "browser.</p>"
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
article.excerpt = ("Interactive flashcards with active recall and spaced repetition, built on "
                   "the Mindsgate CISSP glossary — standard, reverse and scenario cards.")
article.body_md = body
article.meta_title = TITLE
article.meta_description = META_DESCRIPTION
article.save()
print(("created" if created else "updated"), "article", SLUG, "| body bytes:", len(body))
