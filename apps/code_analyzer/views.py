from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.text import slugify

from collections import defaultdict
from pathlib import Path

from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from .services.persistence import persist_scan
from .services.scanner import compute_stats, scan_path, scan_projects
from .services import ai_triage
from .models import ScanRun
from apps.athena.models import AppContextSnapshot


@login_required
def ai_review(request, run_id):
    """Triaged report for a saved scan: security findings + AI verdicts."""
    from .services import ranking, deploy_gate
    run = get_object_or_404(ScanRun, pk=run_id)
    items = ai_triage.security_items(run)
    buckets = defaultdict(list)
    for it in items:
        buckets[it.scan_project.name].append(it)
    groups = []
    for name, its in buckets.items():
        its = ranking.annotate_and_sort(its)
        sp = its[0].scan_project if its else None
        d = deploy_gate.diff_scanned(sp) if sp else {"new_fps": set(), "new_count": 0,
                                                     "resolved_count": 0, "baseline": True}
        for it in its:
            it.is_new = deploy_gate._fp(it) in d["new_fps"]
        groups.append({"name": name, "items": its, "top": its[0].priority if its else 0,
                       "new_count": d["new_count"], "resolved_count": d["resolved_count"],
                       "baseline": d["baseline"]})
    # projects with new findings first, then by top risk
    groups.sort(key=lambda g: (-int(bool(g["new_count"])), -g["top"]))
    return render(request, "code_analyzer/ai_review.html", {
        "run": run,
        "groups": groups,
        "estimate": ai_triage.estimate(run),
        "total": items.count(),
        "reviewed": items.exclude(ai_verdict="").count(),
        "new_total": sum(g["new_count"] for g in groups),
    })


@login_required
@require_POST
def ai_verify(request, run_id):
    run = get_object_or_404(ScanRun, pk=run_id)
    raw_limit = request.POST.get("limit", "")
    limit = int(raw_limit) if raw_limit.isdigit() else None
    s = ai_triage.run_triage(run, user=request.user, limit=limit)
    messages.success(
        request,
        f"AI review complete — {s['reviewed']} findings: {s['real']} real, "
        f"{s['false_positive']} false-positive, {s['uncertain']} uncertain "
        f"(${s['cost_usd']})."
    )
    return redirect("code_analyzer:ai_review", run_id=run.id)


BUCKET_LABELS = {
    "models": "Models",
    "views": "Views",
    "urls": "URLs",
    "forms": "Forms",
    "serializers": "Serializers",
    "settings": "Settings",
    "pages": "Pages",
    "components": "Components",
    "hooks": "Hooks",
    "contexts": "Contexts",
    "routes": "Routes",
    "layouts": "Layouts",
    "utils": "Utilities",
    "types": "Types",
    "config": "Config",
    "api": "API",
    "supabase": "Supabase",
    "migrations": "Migrations",
    "sql": "SQL",
    "env": "Environment",
    "classes": "Classes",
    "functions": "Functions",
    "security": "Security",
    "warnings": "Warnings",
    "duplicates": "Duplicates",
    "large": "Large",
    "other": "Other",
}


FRONTEND_TYPE_MARKERS = ["lovable", "vite", "typescript", "react", "supabase", "frontend"]


def _is_frontendish_project_type(project_type: str) -> bool:
    text = (project_type or "").lower()
    return any(marker in text for marker in FRONTEND_TYPE_MARKERS)


def _project_targets(project):
    """
    Generic Athena-send targets.
    Django projects can expose child apps.
    Frontend/Lovable projects just expose the project root.
    """
    targets = [{
        "name": getattr(project, "name", "Project"),
        "path": getattr(project, "path", ""),
        "kind": "project",
    }]

    for app in (getattr(project, "apps", None) or []):
        targets.append({
            "name": getattr(app, "name", "App"),
            "path": getattr(app, "path", ""),
            "kind": "app",
        })

    return targets


def _decorate_projects(projects):
    for project in projects or []:
        project.targets = _project_targets(project)
        project.is_frontendish = _is_frontendish_project_type(getattr(project, "type", ""))
        project.component_groups = [
            {
                "key": bucket,
                "label": BUCKET_LABELS.get(bucket, bucket.replace("_", " ").title()),
                "items": components,
            }
            for bucket, components in (getattr(project, "components", {}) or {}).items()
            if components
        ]
    return projects


@login_required
def dashboard(request):
    code_root = getattr(settings, "CODE_ANALYZER_ROOT", r"C:\Projects")
    large_loc = getattr(settings, "CODE_ANALYZER_LARGE_LOC", 50)

    projects = None
    stats = None
    saved_run_id = None

    if request.method == "POST":
        start = timezone.now()

        projects = scan_projects(code_root)
        projects = _decorate_projects(projects)
        stats = compute_stats(projects, large_threshold=large_loc)

        duration_ms = int((timezone.now() - start).total_seconds() * 1000)

        run = persist_scan(
            root_path=code_root,
            large_loc_threshold=large_loc,
            projects=projects,
            stats=stats,
            duration_ms=duration_ms,
        )
        saved_run_id = run.id

    context = {
        "code_root": code_root,
        "projects": projects,
        "stats": stats,
        "large_loc": large_loc,
        "saved_run_id": saved_run_id,
    }
    return render(request, "code_analyzer/dashboard.html", context)


@login_required
def _build_snapshot_json(idx) -> dict:
    snapshot = {
        "summary": {
            "name": idx.name,
            "path": idx.path,
            "type": idx.type,
        },
        "buckets": {},
    }

    for bucket, comps in (idx.components or {}).items():
        snapshot["buckets"][bucket] = [
            {
                "name": c.name,
                "file": c.file,
                "lineno": c.lineno,
                "loc": c.loc,
                "kind": c.kind,
            }
            for c in comps
        ]

    return snapshot


@login_required
def _read_excerpt(file_path: str, max_lines: int = 140) -> str:
    try:
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            return ""
        with p.open("r", encoding="utf-8", errors="replace") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                lines.append(line.rstrip("\n"))
        return "\n".join(lines).strip()
    except Exception:
        return ""


@login_required
def _render_description_md(target_path: str, snapshot_json: dict, stats: dict) -> str:
    """
    Human-readable canonical description to feed Athena.
    Stable enough for design/implementation context across Django and Lovable-style projects.
    """
    buckets = snapshot_json.get("buckets") or {}
    summary = snapshot_json.get("summary") or {}

    by_file = defaultdict(list)
    for bucket, items in buckets.items():
        for it in items or []:
            by_file[it.get("file")].append({**it, "bucket": bucket})

    views = buckets.get("views") or []
    urls = buckets.get("urls") or []
    warnings = buckets.get("warnings") or []
    security = buckets.get("security") or []
    large = buckets.get("large") or []
    duplicates = buckets.get("duplicates") or []

    models = buckets.get("models") or []
    classes = buckets.get("classes") or []

    pages = buckets.get("pages") or []
    components = buckets.get("components") or []
    hooks = buckets.get("hooks") or []
    routes = buckets.get("routes") or []
    supabase = buckets.get("supabase") or []
    migrations = buckets.get("migrations") or []
    config = buckets.get("config") or []
    env = buckets.get("env") or []

    project_type = (summary.get("type") or "").lower()
    is_frontendish = _is_frontendish_project_type(project_type)

    model_names = [m.get("name") for m in models if m.get("name")]
    if not model_names:
        model_names = [
            c.get("name") for c in classes
            if c.get("name") and (c.get("file") or "").replace("\\", "/").startswith("models/")
        ]

    view_names = [v.get("name") for v in views if v.get("name")]

    def _as_rel(f: str, root: str) -> str:
        f = (f or "").replace("\\", "/")
        if not f:
            return ""
        p = Path(f)
        if p.is_absolute():
            try:
                return str(p.relative_to(Path(root))).replace("\\", "/")
            except Exception:
                return f
        return f

    rel_files = sorted({_as_rel(f, target_path) for f in by_file.keys() if f})

    def section(title: str):
        lines.append("")
        lines.append(f"## {title}")

    def write_items(items, empty_text, limit=80):
        if items:
            for item in items[:limit]:
                lines.append(f"- `{item}`")
            if len(items) > limit:
                lines.append(f"- … plus {len(items) - limit} more")
        else:
            lines.append(f"- ({empty_text})")

    lines = []
    lines.append(f"# Canonical App Context: {summary.get('name')}")
    lines.append("")
    lines.append(f"- **Path:** `{target_path}`")
    lines.append(f"- **Type:** `{summary.get('type')}`")
    lines.append(f"- **Total components:** `{stats.get('total_components', 0)}`")
    lines.append(f"- **Security findings:** `{stats.get('security_findings_count', 0)}` (high: `{stats.get('security_high_count', 0)}`)")
    lines.append(f"- **Warnings:** `{stats.get('warnings_count', 0)}`")

    section("What this app contains (high level)")
    lines.append("- Treat the lists below as authoritative inventory of what exists in this folder.")
    lines.append("- If an item is not listed here, assume it does not exist unless the user provides more context.")

    if is_frontendish:
        section("Pages")
        write_items([it.get("name") for it in pages if it.get("name")], "No pages detected")

        section("React components")
        write_items([it.get("name") for it in components if it.get("name")], "No components detected", limit=120)

        section("Hooks")
        write_items([it.get("name") for it in hooks if it.get("name")], "No hooks detected")

        section("Routes")
        write_items([it.get("name") for it in routes if it.get("name")], "No routes detected")

        section("Supabase usage")
        write_items([it.get("name") for it in supabase if it.get("name")], "No Supabase usage detected", limit=120)

        section("SQL / migrations")
        write_items([it.get("name") for it in migrations if it.get("name")], "No migrations detected", limit=120)

        section("Config / environment")
        config_env_items = [it.get("name") for it in config if it.get("name")] + [it.get("name") for it in env if it.get("name")]
        write_items(config_env_items, "No config/env findings detected", limit=120)
    else:
        section("Domain entities (models)")
        write_items(model_names, "No models detected in this folder")

        section("Endpoints / views")
        write_items(view_names, "No views detected in this folder")

        section("URL patterns")
        if urls:
            for u in urls[:80]:
                lines.append(f"- `{u.get('file')}:{u.get('lineno')}` ({u.get('kind')})")
            if len(urls) > 80:
                lines.append(f"- … plus {len(urls) - 80} more")
        else:
            lines.append("- (No urls.py patterns detected in this folder)")

    section("Files in scope (relative)")
    for f in rel_files[:200]:
        lines.append(f"- `{f}`")
    if len(rel_files) > 200:
        lines.append(f"- … plus {len(rel_files) - 200} more")

    section("Key file excerpts (first ~140 lines)")
    if is_frontendish:
        key_files = [
            ("package.json", Path(target_path) / "package.json"),
            ("vite.config.ts", Path(target_path) / "vite.config.ts"),
            ("vite.config.js", Path(target_path) / "vite.config.js"),
            ("src/main.tsx", Path(target_path) / "src" / "main.tsx"),
            ("src/App.tsx", Path(target_path) / "src" / "App.tsx"),
            ("src/pages/index.tsx", Path(target_path) / "src" / "pages" / "index.tsx"),
            ("src/integrations/supabase/client.ts", Path(target_path) / "src" / "integrations" / "supabase" / "client.ts"),
            ("supabase/config.toml", Path(target_path) / "supabase" / "config.toml"),
        ]
        fence_lang = "tsx"
        no_excerpt_text = "No frontend key files found at the project root / src / supabase locations."
    else:
        key_files = [
            ("models.py", Path(target_path) / "models.py"),
            ("views.py", Path(target_path) / "views.py"),
            ("urls.py", Path(target_path) / "urls.py"),
            ("models/__init__.py", Path(target_path) / "models" / "__init__.py"),
            ("views/__init__.py", Path(target_path) / "views" / "__init__.py"),
            ("models/produce.py", Path(target_path) / "models" / "produce.py"),
            ("models/produce_knowledge.py", Path(target_path) / "models" / "produce_knowledge.py"),
            ("models/models_market.py", Path(target_path) / "models" / "models_market.py"),
            ("forms.py", Path(target_path) / "forms.py"),
            ("admin.py", Path(target_path) / "admin.py"),
        ]
        fence_lang = "python"
        no_excerpt_text = "No models.py / views.py / urls.py files found at the app root."

    any_found = False
    seen_paths = set()
    for label, p in key_files:
        normalized = str(p).replace("\\", "/")
        if normalized in seen_paths:
            continue
        seen_paths.add(normalized)

        excerpt = _read_excerpt(str(p), max_lines=140)
        if excerpt:
            any_found = True
            lines.append(f"### {label}")
            lines.append(f"```{fence_lang}")
            lines.append(excerpt)
            lines.append("```")
            lines.append("")

    if not any_found:
        lines.append(f"- ({no_excerpt_text})")

    section("Hot spots & signals")
    if large:
        lines.append("### Large functions/classes")
        for it in large[:40]:
            lines.append(f"- `{it.get('name')}` ({_as_rel(it.get('file',''), target_path)}:{it.get('lineno')}, {it.get('loc')} LOC)")
    if duplicates:
        lines.append("### Possible duplicates")
        for it in duplicates[:40]:
            lines.append(f"- `{it.get('name')}` ({_as_rel(it.get('file',''), target_path)}:{it.get('lineno')})")
    if not large and not duplicates:
        lines.append("- (No large/duplicate signals recorded)")

    section("Findings")
    if security:
        lines.append("### Security")
        for it in security[:60]:
            lines.append(f"- `{it.get('name')}` ({_as_rel(it.get('file',''), target_path)}:{it.get('lineno')})")
        if len(security) > 60:
            lines.append(f"- … plus {len(security) - 60} more")
    if warnings:
        lines.append("### Warnings")
        for it in warnings[:60]:
            lines.append(f"- `{it.get('name')}` ({_as_rel(it.get('file',''), target_path)}:{it.get('lineno')})")
        if len(warnings) > 60:
            lines.append(f"- … plus {len(warnings) - 60} more")
    if not security and not warnings:
        lines.append("- (No warnings/security findings recorded)")

    section("Design constraints for future changes")
    if is_frontendish:
        lines.append("- Prefer additive changes over breaking edits to routes, shared components, and Supabase contracts.")
        lines.append("- Keep data access centralized in existing integration/service layers where possible.")
        lines.append("- Preserve environment-variable driven configuration and avoid hardcoding secrets or URLs.")
        lines.append("- Keep schema / migration changes backward-compatible and default-safe.")
    else:
        lines.append("- Prefer additive changes (new models/services/views) over breaking edits.")
        lines.append("- Keep domain logic out of templates; use services or existing patterns.")
        lines.append("- Ensure migrations are backward-compatible and default-safe.")

    return "\n".join(lines).strip() + "\n"


@login_required
def send_to_athena(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")

    target_path = (request.POST.get("target_path") or "").strip()
    if not target_path:
        messages.error(request, "Please select a project or app before sending to Athena.")
        return redirect("code_analyzer:dashboard")

    title = (request.POST.get("title") or "").strip() or f"App Context: {target_path}"

    idx = scan_path(target_path)
    large_loc = getattr(settings, "CODE_ANALYZER_LARGE_LOC", 50)
    stats = compute_stats([idx], large_threshold=large_loc)

    snapshot_json = _build_snapshot_json(idx)
    description_md = _render_description_md(target_path, snapshot_json, stats)

    base_key = slugify(idx.name) or "app"
    path_slug = slugify(target_path.replace("\\", "/"))[-24:] or "path"
    key = f"{base_key}-{path_slug}".replace("--", "-")[:80]

    latest = AppContextSnapshot.objects.filter(key=key).order_by("-version").first()
    next_version = (latest.version + 1) if latest else 1

    snap = AppContextSnapshot.objects.create(
        key=key,
        title=title,
        app_path=target_path,
        version=next_version,
        source="code_analyzer",
        snapshot_json=snapshot_json,
        description_md=description_md,
        created_by=request.user if request.user.is_authenticated else None,
        is_approved=False,
    )

    messages.success(request, f"Sent to Athena: {snap.title} v{snap.version} (needs approval)")
    return redirect("code_analyzer:dashboard")
