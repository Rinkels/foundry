# python manage.py build_live_sites
import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from django.core.management.base import BaseCommand

# Playwright is the engine that can actually render pages to pixels
from playwright.async_api import async_playwright


@dataclass
class LiveSite:
    name: str
    url: str


DEFAULT_SITES: List[LiveSite] = [
    LiveSite("TrustBIX", "https://www.trustbix.com/"),
    LiveSite("Alberta Food Security", "https://albertafoodsecurity.com/"),
    LiveSite("ViewTrak", "https://www.viewtrak.com/"),
    LiveSite("ZenCyber", "https://zencyber.ca/"),
    LiveSite("Hire Output (Tools)", "https://www.hireoutput.tools/"),
    LiveSite("Hire Output", "https://www.hireoutput.com/"),
    LiveSite("Goal Zero", "https://goalzero.app/"),
    LiveSite("HireJack", "https://www.hirejack.work/"),
    LiveSite("HireJack Today", "https://www.hirejack.today/"),
]


def slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "site"


LIVE_SITES_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Live Websites</title>
  <meta name="description" content="Live sites dashboard with homepage previews." />
  <style>
    :root{
      --bg:#0b0f17; --card:rgba(255,255,255,.06); --text:rgba(255,255,255,.92);
      --muted:rgba(255,255,255,.65); --border:rgba(255,255,255,.14); --shadow:0 16px 50px rgba(0,0,0,.45);
      --r:18px; --gap:18px;
    }
    body{ margin:0; font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;
      background: radial-gradient(900px 600px at 15% -10%, rgba(90,120,255,.25), transparent 55%),
                  radial-gradient(900px 600px at 90% 0%, rgba(0,220,255,.18), transparent 60%),
                  var(--bg);
      color:var(--text);
    }
    .wrap{ max-width:1220px; margin:0 auto; padding:26px 18px 42px; }
    header{ display:flex; align-items:flex-end; justify-content:space-between; gap:14px; margin-bottom:18px; flex-wrap:wrap; }
    h1{ margin:0; font-size:clamp(22px,3vw,32px); letter-spacing:.2px; }
    .sub{ margin-top:6px; color:var(--muted); font-size:14px; line-height:1.35; }
    .controls{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
    .pill{ display:flex; align-items:center; gap:8px; padding:10px 12px; border-radius:999px;
      background:rgba(255,255,255,.06); border:1px solid var(--border); box-shadow:0 10px 30px rgba(0,0,0,.25);
    }
    .pill input{ width:min(320px,55vw); background:transparent; border:none; outline:none; color:var(--text); font-size:14px; }
    .btn{ appearance:none; border:1px solid var(--border);
      background:linear-gradient(180deg, rgba(255,255,255,.10), rgba(255,255,255,.04));
      color:var(--text); padding:10px 12px; border-radius:12px; cursor:pointer;
      box-shadow:0 12px 28px rgba(0,0,0,.25); transition:transform .12s ease, border-color .12s ease;
      user-select:none; font-size:14px;
    }
    .btn:hover{ transform:translateY(-1px); border-color:rgba(255,255,255,.22); }
    .grid{ display:grid; grid-template-columns:repeat(12,1fr); gap:var(--gap); margin-top:18px; }
    .card{ grid-column:span 6; border-radius:var(--r); overflow:hidden;
      background:linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,.04));
      border:1px solid var(--border); box-shadow:var(--shadow); min-height:310px;
    }
    @media (max-width:960px){ .card{ grid-column:span 12; } }
    .thumb{ aspect-ratio:16/9; background:rgba(0,0,0,.28); border-bottom:1px solid rgba(255,255,255,.10); position:relative; }
    .thumb img{ width:100%; height:100%; object-fit:cover; display:block; }
    .badge{ position:absolute; top:12px; left:12px; display:flex; align-items:center; gap:8px;
      padding:8px 10px; border-radius:999px; background:rgba(10,14,22,.62); border:1px solid rgba(255,255,255,.14);
      backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px); font-size:13px; max-width:calc(100% - 24px);
    }
    .favicon{ width:18px; height:18px; border-radius:4px; background:rgba(255,255,255,.12); }
    .meta{ padding:14px 14px 16px; display:flex; flex-direction:column; gap:10px; }
    .title{ font-weight:700; letter-spacing:.2px; font-size:16px; margin:0; line-height:1.25; }
    .url{ color:var(--muted); font-size:13px; word-break:break-word; }
    .actions{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
    .mini{ padding:9px 10px; border-radius:12px; font-size:13px; background:rgba(255,255,255,.06); }
    .toast{ position:fixed; bottom:16px; left:50%; transform:translateX(-50%);
      background:rgba(10,14,22,.78); border:1px solid rgba(255,255,255,.16); color:var(--text);
      padding:10px 12px; border-radius:999px; backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px);
      box-shadow:0 20px 60px rgba(0,0,0,.45); opacity:0; pointer-events:none; transition:opacity .18s ease;
      font-size:13px; max-width:min(700px, calc(100vw - 24px)); text-align:center;
    }
    .toast.show{ opacity:1; }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div>
        <h1>Live Websites</h1>
        <div class="sub">Local thumbnails generated by Fractals (Playwright) 🧪</div>
      </div>
      <div class="controls">
        <div class="pill" title="Filter sites">🔎 <input id="filter" type="text" placeholder="Filter (trustbix, cyber, hire…)" /></div>
        <button class="btn" id="reload">↻ Reload manifest</button>
      </div>
    </header>

    <div class="grid" id="grid"></div>
  </div>

  <div class="toast" id="toast">Copied ✅</div>

<script>
  const grid = document.getElementById("grid");
  const filter = document.getElementById("filter");
  const toast = document.getElementById("toast");
  const reloadBtn = document.getElementById("reload");

  function showToast(msg){
    toast.textContent = msg;
    toast.classList.add("show");
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => toast.classList.remove("show"), 1300);
  }

  async function copyText(text){
    try{
      await navigator.clipboard.writeText(text);
      showToast("Copied ✅ " + text);
    }catch(e){
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
      showToast("Copied ✅ " + text);
    }
  }

  async function loadSites(){
    const res = await fetch("./assets/sites.json?v=" + Date.now());
    if(!res.ok) throw new Error("Failed to load sites.json");
    return await res.json();
  }

  function render(sites){
    const q = (filter.value || "").trim().toLowerCase();
    grid.innerHTML = "";

    const filtered = sites.filter(s => {
      const hay = (s.name + " " + s.url).toLowerCase();
      return !q || hay.includes(q);
    });

    for(const s of filtered){
      const card = document.createElement("div");
      card.className = "card";

      const thumb = s.thumb || "";
      const fav = s.favicon || "";

      card.innerHTML = `
        <div class="thumb">
          <img loading="lazy" src="${thumb}" alt="Homepage preview for ${s.name}" />
          <div class="badge" title="${s.url}">
            <img class="favicon" src="${fav}" alt="" />
            <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${s.name}</span>
          </div>
        </div>
        <div class="meta">
          <p class="title">${s.name}</p>
          <div class="url">${s.url}</div>
          <div class="actions">
            <a class="btn mini" href="${s.url}" target="_blank" rel="noopener">Open ↗</a>
            <button class="btn mini" data-copy="${s.url}">Copy URL</button>
          </div>
        </div>
      `;

      grid.appendChild(card);
    }

    grid.querySelectorAll("[data-copy]").forEach(btn => {
      btn.addEventListener("click", () => copyText(btn.getAttribute("data-copy")));
    });
  }

  let SITES = [];
  async function boot(){
    try{
      SITES = await loadSites();
      render(SITES);
    }catch(e){
      grid.innerHTML = '<div style="grid-column:span 12; color: rgba(255,255,255,.75); border:1px dashed rgba(255,255,255,.2); padding:16px; border-radius:12px;">Could not load assets/sites.json. Run the build_live_sites command first.</div>';
      console.error(e);
    }
  }

  filter.addEventListener("input", () => render(SITES));
  reloadBtn.addEventListener("click", boot);

  boot();
</script>
</body>
</html>
"""


class Command(BaseCommand):
    help = "Generate homepage thumbnails + a local 'Live Websites' dashboard page into fractals/output."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-root",
            default=r"C:\Projects\fractals\fractals\output",
            help="Root output directory (default: C:\\Projects\\fractals\\fractals\\output)",
        )
        parser.add_argument(
            "--timeout-ms",
            type=int,
            default=45000,
            help="Navigation timeout per site in ms (default: 45000)",
        )
        parser.add_argument(
            "--wait-ms",
            type=int,
            default=1200,
            help="Extra settle wait after load in ms (default: 1200)",
        )
        parser.add_argument(
            "--full-page",
            action="store_true",
            help="Capture full page screenshots (default: false = viewport only)",
        )

    def handle(self, *args, **opts):
        output_root = Path(opts["output_root"])
        timeout_ms = int(opts["timeout_ms"])
        wait_ms = int(opts["wait_ms"])
        full_page = bool(opts["full_page"])

        out_base = output_root / "_live_sites"
        assets_dir = out_base / "assets"
        thumbs_dir = assets_dir / "thumbs"
        thumbs_dir.mkdir(parents=True, exist_ok=True)

        # Write the dashboard HTML
        (out_base / "index.html").write_text(LIVE_SITES_HTML_TEMPLATE, encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"Dashboard page: {out_base / 'index.html'}"))
        self.stdout.write("Generating thumbnails...")

        manifest = asyncio.run(
            self._generate_thumbs(
                sites=DEFAULT_SITES,
                thumbs_dir=thumbs_dir,
                timeout_ms=timeout_ms,
                wait_ms=wait_ms,
                full_page=full_page,
            )
        )

        # Write sites.json manifest
        (assets_dir / "sites.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Manifest: {assets_dir / 'sites.json'}"))
        self.stdout.write(self.style.SUCCESS("Done ✅"))

    async def _generate_thumbs(
        self,
        sites: List[LiveSite],
        thumbs_dir: Path,
        timeout_ms: int,
        wait_ms: int,
        full_page: bool,
    ):
        manifest = []

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context(
                viewport={"width": 1200, "height": 800},
                user_agent="FractalsLiveSitesBot/1.0",
            )

            for s in sites:
                slug = slugify(s.name)
                thumb_file = thumbs_dir / f"{slug}.png"

                page = await context.new_page()
                ok = True
                err: Optional[str] = None

                try:
                    await page.goto(s.url, wait_until="domcontentloaded", timeout=timeout_ms)
                    await page.wait_for_timeout(wait_ms)
                    await page.screenshot(path=str(thumb_file), full_page=full_page)
                except Exception as e:
                    ok = False
                    err = str(e)
                finally:
                    await page.close()

                # favicon helper (no JS needed)
                favicon = f"https://www.google.com/s2/favicons?domain={s.url}&sz=64"

                manifest.append(
                    {
                        "name": s.name,
                        "url": s.url,
                        "slug": slug,
                        "thumb": f"./assets/thumbs/{slug}.png",
                        "favicon": favicon,
                        "ok": ok,
                        "error": err,
                    }
                )

            await context.close()
            await browser.close()

        return manifest
