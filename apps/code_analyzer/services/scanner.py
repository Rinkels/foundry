from __future__ import annotations

import ast
import json
import os
import re
import tomllib
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


EXCLUDE_DIRS = {
    "venv", "venv37", ".venv", ".venv310", "venv13","venv313", "env", "envs",
    "__pycache__", ".git", ".idea",
    "node_modules", "dist", "build",
    ".mypy_cache", ".pytest_cache"
}
PUBLIC_VIEW_NAME_HINTS = {
    "login", "logout", "signup", "register",
    "password_reset", "password_change",
    "health", "ping", "status",
    "webhook", "callback",
}
BUCKETS = [
    "models",
    "views",
    "urls",
    "forms",
    "serializers",
    "settings",
    "pages",
    "components",
    "hooks",
    "contexts",
    "routes",
    "layouts",
    "utils",
    "types",
    "config",
    "api",
    "supabase",
    "migrations",
    "sql",
    "env",
    "classes",
    "functions",
    "security",
    "warnings",
    "other",
]

TS_EXTS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
SQL_EXTS = {".sql"}
ENV_FILE_NAMES = {
    ".env", ".env.local", ".env.development", ".env.production",
    ".env.test", ".env.example"
}
CONFIG_FILE_NAMES = {
    "package.json", "components.json", "tsconfig.json", "tsconfig.app.json",
    "tsconfig.node.json", "vite.config.ts", "vite.config.js", "vite.config.mts",
    "tailwind.config.ts", "tailwind.config.js", "postcss.config.js", "eslint.config.js",
    "supabase/config.toml",
}


def _node_loc(node: ast.AST) -> int:
    """
    Best-effort LOC calculation using end_lineno if available.
    """
    end = getattr(node, "end_lineno", None)
    if end is None:
        return 1
    return max(1, end - node.lineno + 1)


@dataclass
class Component:
    name: str
    file: str       # path relative to project root
    lineno: int | None = None
    loc: int | None = None
    kind: str | None = None       # "class" / "function" / "method" / "security"


@dataclass
class ProjectIndex:
    name: str
    path: str
    type: str
    components: Dict[str, List[Component]] = field(
        default_factory=lambda: {b: [] for b in BUCKETS}
    )
    apps: List[dict] = field(default_factory=list)  # ✅ add this


def find_django_apps(project_path: Path, max_depth: int = 3) -> list[dict]:
    """
    Find Django app folders inside a project, even when apps live under
    <project>/<project_name>/apps (e.g. nurbai/nurbai/apps).

    Strategy:
      1) Check common roots:
         - <project>/apps
         - <project>/<project_name>/apps
      2) Fallback: hunt for any */apps folders within max_depth (excluding EXCLUDE_DIRS)

    Heuristics for "app folder":
      - contains __init__.py
      - contains apps.py OR models.py
    """
    project_path = Path(project_path)
    candidates: list[Path] = []
    seen_apps_roots: set[str] = set()

    def add_apps_root(apps_root: Path):
        if not apps_root.exists() or not apps_root.is_dir():
            return
        key = str(apps_root.resolve()).lower()
        if key in seen_apps_roots:
            return
        seen_apps_roots.add(key)
        for d in apps_root.iterdir():
            if d.is_dir() and d.name not in EXCLUDE_DIRS:
                candidates.append(d)

    # 1) Common locations
    add_apps_root(project_path / "apps")
    add_apps_root(project_path / project_path.name / "apps")  # e.g. nurbai/nurbai/apps

    # 2) Hunt for */apps roots within max_depth
    # Only walk directories up to max_depth, skip EXCLUDE_DIRS aggressively.
    def hunt_for_apps_roots(base: Path, depth: int = 0):
        if depth > max_depth:
            return
        try:
            children = list(base.iterdir())
        except Exception:
            return

        for c in children:
            if not c.is_dir():
                continue
            if c.name in EXCLUDE_DIRS:
                continue

            if c.name == "apps":
                add_apps_root(c)
                # Don't go deeper into apps/ itself; it’s handled by add_apps_root
                continue

            hunt_for_apps_roots(c, depth + 1)

    hunt_for_apps_roots(project_path, depth=0)

    apps: list[dict] = []
    for d in candidates:
        try:
            if (d / "__init__.py").exists() and ((d / "apps.py").exists() or (d / "models.py").exists()):
                apps.append({"name": d.name, "path": str(d)})
        except Exception:
            # ignore filesystem edge cases
            pass

    # Deduplicate by path
    dedup: dict[str, dict] = {}
    for a in apps:
        dedup[a["path"].lower()] = a

    return sorted(dedup.values(), key=lambda x: x["name"].lower())


def detect_project_type(project_dir: Path) -> str:
    """
    Light heuristics to tag Django/Python/Lovable/Vite/Supabase style projects.
    """
    if (project_dir / "manage.py").exists():
        return "Django"

    has_lovable = (project_dir / ".lovable").exists()
    has_package = (project_dir / "package.json").exists()
    has_vite = (project_dir / "vite.config.ts").exists() or (project_dir / "vite.config.js").exists() or (project_dir / "vite.config.mts").exists()
    has_ts = (project_dir / "tsconfig.json").exists() or (project_dir / "tsconfig.app.json").exists()
    has_supabase = (project_dir / "supabase").exists()

    if has_lovable and has_supabase:
        return "Lovable + Supabase"
    if has_lovable:
        return "Lovable"
    if has_vite and has_ts and has_supabase:
        return "Vite React TypeScript + Supabase"
    if has_vite and has_ts:
        return "Vite React TypeScript"
    if has_package and has_supabase:
        return "Node/Frontend + Supabase"
    if has_package:
        return "Node/Frontend"
    if (project_dir / "pyproject.toml").exists() or (project_dir / "setup.py").exists():
        return "Python"
    if (project_dir / ".git").exists():
        return "Python (git)"
    return "Unknown"


def scan_projects(root_path: str | Path) -> List[ProjectIndex]:
    root = Path(root_path)
    projects: List[ProjectIndex] = []

    if not root.exists() or not root.is_dir():
        return projects

    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        project = ProjectIndex(
            name=child.name,
            path=str(child),
            type=detect_project_type(child),
        )
        project.apps = find_django_apps(child)  # ✅ add this
        scan_single_project(child, project)
        projects.append(project)
    return projects


def scan_single_project(project_dir: Path, project: ProjectIndex) -> None:
    """
    Walk a project directory and dispatch file parsing by language/type.
    Everything is in-memory.
    """
    for dirpath, dirnames, filenames in os.walk(project_dir):
        current_dir = Path(dirpath)

        pruned = []
        for d in dirnames:
            if d in EXCLUDE_DIRS:
                continue
            pruned.append(d)
        dirnames[:] = pruned

        for filename in filenames:
            file_path = current_dir / filename
            rel = file_path.relative_to(project_dir).as_posix()
            suffix = file_path.suffix.lower()

            try:
                if suffix == ".py":
                    parse_python_file(project_dir, file_path, project)
                elif suffix in TS_EXTS:
                    parse_ts_like_file(project_dir, file_path, project)
                elif suffix in SQL_EXTS:
                    parse_sql_file(project_dir, file_path, project)
                elif filename in ENV_FILE_NAMES or filename.startswith(".env"):
                    parse_env_file(project_dir, file_path, project)
                elif filename in CONFIG_FILE_NAMES or rel in CONFIG_FILE_NAMES:
                    parse_config_file(project_dir, file_path, project)
            except Exception as exc:
                project.components["warnings"].append(
                    Component(
                        name=f"[WARN] Failed to parse {rel}: {exc}",
                        file=rel,
                        lineno=None,
                        loc=1,
                        kind="warning",
                    )
                )


def _bucket_from_filename(stem: str) -> str | None:
    stem = stem.lower()
    if stem == "models":
        return "models"
    if stem == "views":
        return "views"
    if stem == "urls":
        return "urls"
    if stem == "forms":
        return "forms"
    if stem == "serializers":
        return "serializers"
    if stem == "settings":
        return "settings"
    if stem in {"app", "main", "router", "routes"}:
        return "routes"
    if stem.startswith("use"):
        return "hooks"
    return None


# ----------------------------
# Security scanning helpers
# ----------------------------
def _has_django_markers(tree: ast.AST) -> bool:
    """
    Heuristic: confirm module looks like Django settings.
    Require at least 2 strong markers.
    """
    assigned = _collect_assigned_names(tree)
    markers = 0
    for k in ("SECRET_KEY", "INSTALLED_APPS", "MIDDLEWARE", "DATABASES", "ROOT_URLCONF"):
        if k in assigned:
            markers += 1
    return markers >= 2


def _file_is_probably_django_settings(file_path: Path, tree: ast.AST) -> bool:
    """
    Only treat as Django settings if:
      - file name is settings.py
      - and it has Django markers
    """
    if file_path.name.lower() != "settings.py":
        return False
    return _has_django_markers(tree)

def _record_parse_warnings(project, rel: str, warning_messages) -> None:
    """
    Persist warnings captured during ast.parse/compile to the project index.
    """
    for wm in warning_messages:
        try:
            msg = str(wm.message)
        except Exception:
            msg = "Unknown warning"

        # WarningMessage often has lineno, but not always
        lineno = getattr(wm, "lineno", None)

        project.components["warnings"].append(
            Component(
                name=f"[WARN] {wm.category.__name__}: {msg}",
                file=rel,
                lineno=lineno,
                loc=1,
                kind="warning",
            )
        )

_SECRET_NAME_RE = re.compile(
    r"(secret|password|passwd|pwd|api[_-]?key|token|private[_-]?key|access[_-]?key)",
    re.IGNORECASE,
)

# Not perfect, but catches the “oops I pasted a real key” cases.
_SECRET_VALUE_RE = re.compile(
    r"(?i)("
    r"sk-[A-Za-z0-9]{16,}"           # OpenAI-like
    r"|AKIA[0-9A-Z]{16}"             # AWS access key id
    r"|AIza[0-9A-Za-z\-_]{20,}"      # Google API key-ish
    r"|-----BEGIN [A-Z ]+PRIVATE KEY-----"
    r"|[A-Za-z0-9_\-]{32,}"          # generic long token
    r")"
)

def _collect_assigned_names(tree: ast.AST) -> dict:
    """
    Collect simple NAME = <expr> assignments at module level (best-effort).
    Returns {name: value_node}.
    """
    assigned = {}
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigned[target.id] = node.value
    return assigned


def _is_list_or_tuple_of_str(node: ast.AST) -> bool:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return False
    return all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in (node.elts or []))


def _list_contains_str(node: ast.AST, value: str) -> bool:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return False
    for e in node.elts or []:
        if isinstance(e, ast.Constant) and e.value == value:
            return True
    return False


def scan_django_settings(tree: ast.AST, rel: str, add_finding) -> None:
    """
    Run Django settings-specific security checks.
    `add_finding(title, lineno, severity)` is injected so this stays generic.
    """
    assigned = _collect_assigned_names(tree)

    # DEBUG
    debug_node = assigned.get("DEBUG")
    if debug_node is not None and _is_const_true(debug_node):
        add_finding("Django settings: DEBUG=True (do not use in production)", getattr(debug_node, "lineno", None), "HIGH")

    # SECRET_KEY hardcoded (or django-insecure)
    sk_node = assigned.get("SECRET_KEY")
    sk_val = _const_str(sk_node) if sk_node is not None else None
    if sk_val:
        sev = "HIGH" if "django-insecure" in sk_val.lower() else "MED"
        add_finding("Django settings: SECRET_KEY appears hardcoded (use env/secret manager)", getattr(sk_node, "lineno", None), sev)

    # ALLOWED_HOSTS wildcard
    ah_node = assigned.get("ALLOWED_HOSTS")
    if ah_node is not None and _list_contains_str(ah_node, "*"):
        add_finding('Django settings: ALLOWED_HOSTS contains "*" (overly permissive)', getattr(ah_node, "lineno", None), "HIGH")

    # SecurityMiddleware present? (we can only check if MIDDLEWARE is a literal list/tuple)
    mw_node = assigned.get("MIDDLEWARE")
    if mw_node is not None and _is_list_or_tuple_of_str(mw_node):
        middleware_values = [e.value for e in mw_node.elts]
        if "django.middleware.security.SecurityMiddleware" not in middleware_values:
            add_finding("Django settings: SecurityMiddleware not found in MIDDLEWARE", getattr(mw_node, "lineno", None), "MED")

    # SSL / cookies / HSTS: if missing, warn (prod-hardening checks)
    # These might be intentionally absent for dev, so severity is MED.
    recommended_flags = {
        "SECURE_SSL_REDIRECT": "Redirect HTTP→HTTPS",
        "SESSION_COOKIE_SECURE": "Session cookie over HTTPS only",
        "CSRF_COOKIE_SECURE": "CSRF cookie over HTTPS only",
        "SECURE_HSTS_SECONDS": "HSTS (strict transport security)",
        "SECURE_CONTENT_TYPE_NOSNIFF": "Stop MIME sniffing",
        "X_FRAME_OPTIONS": "Clickjacking protection",
        "SECURE_REFERRER_POLICY": "Referrer policy",
    }

    missing = [k for k in recommended_flags.keys() if k not in assigned]
    if missing:
        # one summary item instead of 7-10 items per file
        add_finding(
            f"Django settings: missing production-hardening flags ({', '.join(missing[:5])}{'...' if len(missing) > 5 else ''})",
            None,
            "LOW",
        )

    # If HSTS seconds is set but too low/zero, warn
    hsts = assigned.get("SECURE_HSTS_SECONDS")
    if hsts is not None and isinstance(hsts, ast.Constant) and isinstance(hsts.value, int):
        if hsts.value < 31536000:  # 1 year is common guidance
            add_finding("Django settings: SECURE_HSTS_SECONDS is set but below 31536000", getattr(hsts, "lineno", None), "LOW")

    # Database: sqlite warning (context dependent, but good to flag)
    db_node = assigned.get("DATABASES")
    if db_node is not None:
        # We avoid deep evaluation; just flag if sqlite3 literal appears in source via AST Constant scan.
        for n in ast.walk(db_node):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and "sqlite3" in n.value:
                add_finding("Django settings: sqlite3 configured (fine for dev; avoid for production workloads)", getattr(db_node, "lineno", None), "LOW")
                break

def _call_name(node: ast.AST) -> Optional[str]:
    """
    Best-effort dotted name for function calls, e.g.:
      eval -> "eval"
      yaml.load -> "yaml.load"
      subprocess.Popen -> "subprocess.Popen"
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = _call_name(node.value)
        if left:
            return f"{left}.{node.attr}"
        return node.attr
    return None

def _kwarg(node: ast.Call, key: str) -> Optional[ast.AST]:
    for kw in node.keywords or []:
        if kw.arg == key:
            return kw.value
    return None

def _is_const_true(n: ast.AST) -> bool:
    return isinstance(n, ast.Constant) and n.value is True

def _is_const_false(n: ast.AST) -> bool:
    return isinstance(n, ast.Constant) and n.value is False

def _const_str(n: ast.AST) -> Optional[str]:
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        return n.value
    return None


def parse_python_file(project_dir: Path, file_path: Path, project: ProjectIndex) -> None:
    try:
        source = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        source = file_path.read_text(errors="ignore")

    # Capture warnings raised by parsing/compiling the file (e.g., invalid escape sequences)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")  # record everything produced during parse
        try:
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, ValueError):
            # SyntaxError = invalid Python
            # ValueError = occasional edge cases in parsing/encoding
            return

    # Persist any warnings captured during parse
    rel = file_path.relative_to(project_dir).as_posix()
    _record_parse_warnings(project, rel, w)
    primary_bucket = _bucket_from_filename(file_path.stem)

    security_added = 0
    SECURITY_PER_FILE_CAP = 50

    def add_security_finding(title: str, lineno: int | None, severity: str = "MED") -> None:
        nonlocal security_added
        if security_added >= SECURITY_PER_FILE_CAP:
            return
        security_added += 1
        project.components["security"].append(
            Component(
                name=f"[{severity}] {title}",
                file=rel,
                lineno=lineno,
                loc=1,
                kind="security",
            )
        )


    def add_class(node: ast.ClassDef):
        bucket = primary_bucket or "classes"
        project.components[bucket].append(
            Component(
                name=node.name,
                file=rel,
                lineno=node.lineno,
                loc=_node_loc(node),
                kind="class",
            )
        )

        # methods inside the class
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                add_function(
                    item,
                    name_override=f"{node.name}.{item.name}",
                    kind="method",
                )

    def add_function(node: ast.FunctionDef, name_override: str | None = None,
                     kind: str = "function"):
        bucket = primary_bucket or "functions"
        project.components[bucket].append(
            Component(
                name=name_override or node.name,
                file=rel,
                lineno=node.lineno,
                loc=_node_loc(node),
                kind=kind,
            )
        )

    # ---- Component indexing (existing) ----
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            add_class(node)
        elif isinstance(node, ast.FunctionDef):
            add_function(node)

    # special case: urlpatterns in urls.py
    if file_path.stem.lower() == "urls":
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "urlpatterns":
                        project.components["urls"].append(
                            Component(
                                name="urlpatterns",
                                file=rel,
                                lineno=node.lineno,
                                loc=_node_loc(node),
                                kind="urls",
                            )
                        )

    # ---- Security scanning (NEW) ----
    # Settings-level checks (works best on settings.py but also catches config modules)
    # ---- Django settings-aware checks (NEW) ----
    if _file_is_probably_django_settings(file_path, tree):
        scan_django_settings(tree, rel, add_security_finding)

    # ---- Django view auth checks: ONE pass over top-level defs per file ----
    # NB: this must stay OUT of the ast.walk(tree) loop below. Inside it, each
    # finding was emitted once per AST node in the file (accumulating up to the
    # per-file cap), so a views.py reported N views x manyNodes duplicates.
    if file_path.stem.lower() == "views":
        for top in tree.body:
            # Function-based views
            if isinstance(top, ast.FunctionDef):
                if _is_probable_django_function_view(top) and not _has_login_required_decorator(top):
                    sev = "LOW" if top.name.lower() in PUBLIC_VIEW_NAME_HINTS else "MED"
                    add_security_finding(
                        f"View missing @login_required: {top.name}()",
                        getattr(top, "lineno", None),
                        sev,
                    )
            # Class-based views
            elif isinstance(top, ast.ClassDef):
                # Only flag likely CBVs: name ends with View OR inherits something named *View
                looks_like_view = top.name.endswith("View") or any(
                    (_decorator_name(b).endswith("View") or _decorator_name(b).endswith(".View"))
                    for b in (top.bases or [])
                )
                if looks_like_view:
                    has_guard = _class_uses_login_required_mixin(top) or _class_wrapped_with_login_required(top)
                    if not has_guard:
                        sev = "LOW" if top.name.lower().startswith(tuple(PUBLIC_VIEW_NAME_HINTS)) else "MED"
                        add_security_finding(
                            f"CBV missing LoginRequiredMixin / method_decorator(login_required): {top.name}",
                            getattr(top, "lineno", None),
                            sev,
                        )

    for node in ast.walk(tree):
        # DEBUG = True
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "DEBUG":
                    if _is_const_true(node.value):
                        add_security_finding("Django DEBUG=True (do not use in production)", getattr(node, "lineno", None), "HIGH")

                if isinstance(target, ast.Name) and target.id == "ALLOWED_HOSTS":
                    # ALLOWED_HOSTS = ["*"]
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        elts = node.value.elts or []
                        if any(isinstance(e, ast.Constant) and e.value == "*" for e in elts):
                            add_security_finding('Django ALLOWED_HOSTS contains "*"', getattr(node, "lineno", None), "HIGH")

                # Hardcoded secrets: NAME = "value"
                if isinstance(target, ast.Name):
                    name = target.id
                    sval = _const_str(node.value)
                    if sval and _SECRET_NAME_RE.search(name):
                        # If it looks like a real key/token, scream louder.
                        sev = "HIGH" if _SECRET_VALUE_RE.search(sval) else "MED"
                        add_security_finding(f"Possible hardcoded secret in variable '{name}'", getattr(node, "lineno", None), sev)

        # Dangerous calls + patterns
        if isinstance(node, ast.Call):
            fname = _call_name(node.func) or ""

            # eval / exec
            if fname in {"eval", "exec"}:
                add_security_finding(f"Use of {fname}()", getattr(node, "lineno", None), "HIGH")

            # pickle deserialization
            if fname in {"pickle.load", "pickle.loads"}:
                add_security_finding("pickle deserialization can lead to RCE if input is untrusted", getattr(node, "lineno", None), "HIGH")

            # yaml.load without SafeLoader
            if fname == "yaml.load":
                loader = _kwarg(node, "Loader") or _kwarg(node, "loader")
                if loader is None:
                    add_security_finding("yaml.load() without specifying SafeLoader (prefer yaml.safe_load)", getattr(node, "lineno", None), "HIGH")
                else:
                    # Still warn if not SafeLoader (best-effort)
                    loader_name = _call_name(loader) or ""
                    if "SafeLoader" not in loader_name:
                        add_security_finding("yaml.load() with non-SafeLoader (prefer yaml.safe_load / SafeLoader)", getattr(node, "lineno", None), "MED")

            # subprocess with shell=True
            if fname in {"subprocess.Popen", "subprocess.call", "subprocess.run", "os.system", "os.popen"}:
                shell = _kwarg(node, "shell")
                if shell is not None and _is_const_true(shell):
                    add_security_finding(f"{fname}(..., shell=True) can enable command injection", getattr(node, "lineno", None), "HIGH")
                if fname in {"os.system", "os.popen"}:
                    add_security_finding(f"Use of {fname}() (prefer subprocess with args list)", getattr(node, "lineno", None), "MED")

            # requests verify=False
            if fname.startswith("requests.") and fname in {"requests.get", "requests.post", "requests.put", "requests.delete", "requests.patch"}:
                verify = _kwarg(node, "verify")
                if verify is not None and _is_const_false(verify):
                    add_security_finding("requests.*(..., verify=False) disables TLS verification", getattr(node, "lineno", None), "HIGH")

            # ssl unverified context
            if fname in {"ssl._create_unverified_context"}:
                add_security_finding("ssl._create_unverified_context() disables TLS verification", getattr(node, "lineno", None), "HIGH")

            # tempfile.mktemp is unsafe
            if fname == "tempfile.mktemp":
                add_security_finding("tempfile.mktemp() is insecure (race condition). Use mkstemp/mkdtemp/NamedTemporaryFile", getattr(node, "lineno", None), "HIGH")

            # Potential SQL injection: cursor.execute(f"...{x}...") or "%s" formatting mishaps
            if fname.endswith(".execute"):
                if node.args:
                    arg0 = node.args[0]
                    if isinstance(arg0, ast.JoinedStr):
                        add_security_finding("SQL execute() with f-string; possible SQL injection (use params)", getattr(node, "lineno", None), "HIGH")
                    if isinstance(arg0, ast.BinOp) and isinstance(arg0.op, (ast.Mod, ast.Add)):
                        add_security_finding("SQL execute() with string formatting/concatenation; possible SQL injection (use params)", getattr(node, "lineno", None), "HIGH")




def _line_no(source: str, pos: int) -> int:
    return source.count("\n", 0, pos) + 1


def _bucket_from_ts_path(file_path: Path) -> str:
    rel_parts = [p.lower() for p in file_path.parts]
    stem = file_path.stem.lower()
    name = file_path.name.lower()

    if "pages" in rel_parts:
        return "pages"
    if "components" in rel_parts:
        return "components"
    if "hooks" in rel_parts or stem.startswith("use"):
        return "hooks"
    if "contexts" in rel_parts or stem.endswith("context"):
        return "contexts"
    if "layouts" in rel_parts or "layout" in stem:
        return "layouts"
    if "integrations" in rel_parts or "supabase" in rel_parts:
        return "supabase"
    if "utils" in rel_parts or "lib" in rel_parts:
        return "utils"
    if "types" in rel_parts or name.endswith('.d.ts'):
        return "types"
    if stem in {"app", "main", "router", "routes"} or "route" in stem:
        return "routes"
    return "functions"


TS_COMPONENT_RE = re.compile(r"(?:export\s+default\s+function|export\s+function|function|const)\s+([A-Z][A-Za-z0-9_]*)\s*(?:\(|=)")
TS_HOOK_RE = re.compile(r"(?:export\s+function|function|const)\s+(use[A-Z][A-Za-z0-9_]*)\s*(?:\(|=)")
TS_ROUTE_RE = re.compile(r"<Route[^>]*\s+path=[\"']([^\"']+)[\"']")
TS_SUPABASE_TABLE_RE = re.compile(r"\.from\(\s*[\"']([^\"']+)[\"']\s*\)")
TS_SUPABASE_RPC_RE = re.compile(r"\.rpc\(\s*[\"']([^\"']+)[\"']\s*")
TS_SUPABASE_CHANNEL_RE = re.compile(r"\.channel\(\s*[\"']([^\"']+)[\"']\s*\)")
TS_IMPORT_RE = re.compile(r"^\s*import\s+.*?from\s+[\"']([^\"']+)[\"']", re.M)
TS_ENV_RE = re.compile(r'import\.meta\.env\.([A-Z0-9_]+)')
TS_EXPORT_FUNC_RE = re.compile(r'export\s+(?:async\s+)?function\s+([a-zA-Z_][A-Za-z0-9_]*)\s*\(')
TS_ARROW_FUNC_RE = re.compile(r'const\s+([a-zA-Z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>')
TS_USE_QUERY_RE = re.compile(r'\buse(Query|Mutation|InfiniteQuery)\b')
TS_DANGEROUS_HTML_RE = re.compile(r'dangerouslySetInnerHTML')
TS_LOCALSTORAGE_RE = re.compile(r'\blocalStorage\b')
TS_CREATE_CLIENT_RE = re.compile(r'createClient\s*\(')
TS_PROTECTED_ROUTE_RE = re.compile(r'ProtectedRoute')

SQL_CREATE_TABLE_RE = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:public\.)?[\"']?([a-zA-Z0-9_]+)[\"']?", re.I)
SQL_CREATE_FUNCTION_RE = re.compile(r"CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+(?:public\.)?[\"']?([a-zA-Z0-9_]+)[\"']?", re.I)
SQL_CREATE_VIEW_RE = re.compile(r"CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+(?:public\.)?[\"']?([a-zA-Z0-9_]+)[\"']?", re.I)
SQL_CREATE_POLICY_RE = re.compile(r"CREATE\s+POLICY\s+[\"']?([^\"'\n]+)[\"']?\s+ON\s+(?:public\.)?[\"']?([a-zA-Z0-9_]+)[\"']?", re.I)
SQL_STORAGE_BUCKET_RE = re.compile(r'storage\.buckets', re.I)
SQL_SECURITY_DEFINER_RE = re.compile(r'SECURITY\s+DEFINER', re.I)
SQL_AUTH_UID_RE = re.compile(r'auth\.uid\s*\(', re.I)

ENV_SECRET_NAME_RE = re.compile(r'(SECRET|PASSWORD|TOKEN|KEY)', re.I)
ENV_SECRET_VALUE_RE = re.compile(r'(?i)(sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z\-_]{20,}|[A-Za-z0-9_\-]{32,})')


def _safe_read_text(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return file_path.read_text(errors="ignore")


def _add_component(project: ProjectIndex, bucket: str, name: str, rel: str,
                   lineno: int | None = None, loc: int | None = 1,
                   kind: str | None = None) -> None:
    if bucket not in project.components:
        project.components[bucket] = []
    project.components[bucket].append(
        Component(name=name, file=rel, lineno=lineno, loc=loc, kind=kind)
    )


def parse_ts_like_file(project_dir: Path, file_path: Path, project: ProjectIndex) -> None:
    source = _safe_read_text(file_path)
    rel = file_path.relative_to(project_dir).as_posix()
    bucket = _bucket_from_ts_path(file_path)

    for m in TS_COMPONENT_RE.finditer(source):
        _add_component(project, bucket, m.group(1), rel, _line_no(source, m.start()), 1, "component")

    for m in TS_HOOK_RE.finditer(source):
        _add_component(project, "hooks", m.group(1), rel, _line_no(source, m.start()), 1, "hook")

    for m in TS_EXPORT_FUNC_RE.finditer(source):
        _add_component(project, bucket, m.group(1), rel, _line_no(source, m.start()), 1, "function")

    for m in TS_ARROW_FUNC_RE.finditer(source):
        nm = m.group(1)
        target_bucket = "hooks" if nm.startswith("use") else bucket
        kind = "hook" if nm.startswith("use") else "function"
        _add_component(project, target_bucket, nm, rel, _line_no(source, m.start()), 1, kind)

    for m in TS_ROUTE_RE.finditer(source):
        _add_component(project, "routes", m.group(1), rel, _line_no(source, m.start()), 1, "route")

    for m in TS_SUPABASE_TABLE_RE.finditer(source):
        _add_component(project, "supabase", f"table:{m.group(1)}", rel, _line_no(source, m.start()), 1, "supabase")

    for m in TS_SUPABASE_RPC_RE.finditer(source):
        _add_component(project, "supabase", f"rpc:{m.group(1)}", rel, _line_no(source, m.start()), 1, "supabase")

    for m in TS_SUPABASE_CHANNEL_RE.finditer(source):
        _add_component(project, "supabase", f"channel:{m.group(1)}", rel, _line_no(source, m.start()), 1, "supabase")

    for m in TS_ENV_RE.finditer(source):
        _add_component(project, "env", m.group(1), rel, _line_no(source, m.start()), 1, "env")

    imports = []
    for m in TS_IMPORT_RE.finditer(source):
        mod = m.group(1)
        imports.append(mod)
        if mod.startswith("@/components"):
            _add_component(project, "components", f"import:{mod}", rel, _line_no(source, m.start()), 1, "import")
        elif "supabase" in mod:
            _add_component(project, "supabase", f"import:{mod}", rel, _line_no(source, m.start()), 1, "import")

    if TS_USE_QUERY_RE.search(source):
        _add_component(project, "api", "tanstack-query usage", rel, None, 1, "api")

    if TS_PROTECTED_ROUTE_RE.search(source):
        _add_component(project, "security", "[INFO] ProtectedRoute usage", rel, None, 1, "security")

    if TS_DANGEROUS_HTML_RE.search(source):
        _add_component(project, "security", "[MED] dangerouslySetInnerHTML usage", rel, None, 1, "security")

    if TS_LOCALSTORAGE_RE.search(source):
        _add_component(project, "security", "[LOW] localStorage usage", rel, None, 1, "security")

    if TS_CREATE_CLIENT_RE.search(source):
        _add_component(project, "supabase", "createClient(...) usage", rel, None, 1, "supabase")


def parse_sql_file(project_dir: Path, file_path: Path, project: ProjectIndex) -> None:
    source = _safe_read_text(file_path)
    rel = file_path.relative_to(project_dir).as_posix()

    for m in SQL_CREATE_TABLE_RE.finditer(source):
        _add_component(project, "migrations", f"table:{m.group(1)}", rel, _line_no(source, m.start()), 1, "sql")

    for m in SQL_CREATE_FUNCTION_RE.finditer(source):
        _add_component(project, "migrations", f"function:{m.group(1)}", rel, _line_no(source, m.start()), 1, "sql")

    for m in SQL_CREATE_VIEW_RE.finditer(source):
        _add_component(project, "migrations", f"view:{m.group(1)}", rel, _line_no(source, m.start()), 1, "sql")

    for m in SQL_CREATE_POLICY_RE.finditer(source):
        _add_component(project, "security", f"[INFO] policy:{m.group(1)} on {m.group(2)}", rel, _line_no(source, m.start()), 1, "security")

    if SQL_STORAGE_BUCKET_RE.search(source):
        _add_component(project, "supabase", "storage bucket config", rel, None, 1, "supabase")

    if SQL_SECURITY_DEFINER_RE.search(source):
        _add_component(project, "security", "[MED] SQL uses SECURITY DEFINER", rel, None, 1, "security")

    if SQL_AUTH_UID_RE.search(source):
        _add_component(project, "security", "[INFO] auth.uid() policy/function usage", rel, None, 1, "security")


def parse_env_file(project_dir: Path, file_path: Path, project: ProjectIndex) -> None:
    source = _safe_read_text(file_path)
    rel = file_path.relative_to(project_dir).as_posix()

    for lineno, raw in enumerate(source.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        _add_component(project, "env", key, rel, lineno, 1, "env")
        if ENV_SECRET_NAME_RE.search(key) and value:
            sev = "HIGH" if ENV_SECRET_VALUE_RE.search(value) else "MED"
            _add_component(project, "security", f"[{sev}] Possible secret in env variable '{key}'", rel, lineno, 1, "security")


def parse_config_file(project_dir: Path, file_path: Path, project: ProjectIndex) -> None:
    rel = file_path.relative_to(project_dir).as_posix()
    name = file_path.name

    if name == "package.json":
        data = json.loads(_safe_read_text(file_path))
        deps = {}
        deps.update(data.get("dependencies", {}) or {})
        deps.update(data.get("devDependencies", {}) or {})

        for dep in sorted(deps.keys()):
            _add_component(project, "config", f"dep:{dep}", rel, 1, 1, "config")

        scripts = data.get("scripts", {}) or {}
        for script_name in sorted(scripts.keys()):
            _add_component(project, "config", f"script:{script_name}", rel, 1, 1, "config")
        return

    if file_path.suffix.lower() == ".json":
        try:
            data = json.loads(_safe_read_text(file_path))
        except Exception:
            data = None
        if isinstance(data, dict):
            for key in sorted(data.keys()):
                _add_component(project, "config", f"{name}:{key}", rel, 1, 1, "config")
        return

    if file_path.suffix.lower() == ".toml":
        data = tomllib.loads(_safe_read_text(file_path))
        for key in sorted(data.keys()):
            _add_component(project, "config", f"{name}:{key}", rel, 1, 1, "config")

        functions = data.get("functions", {}) or {}
        if isinstance(functions, dict):
            for fn_name, fn_cfg in sorted(functions.items()):
                _add_component(project, "supabase", f"edge-function:{fn_name}", rel, 1, 1, "supabase")
                if isinstance(fn_cfg, dict) and str(fn_cfg.get("verify_jwt", "")).lower() == "false":
                    _add_component(project, "security", f"[MED] edge-function {fn_name} has verify_jwt=false", rel, 1, 1, "security")
        return

    source = _safe_read_text(file_path)
    if name.startswith("vite.config"):
        _add_component(project, "config", "vite-config", rel, 1, 1, "config")
        if "react(" in source or "react-swc" in source:
            _add_component(project, "config", "vite-react-plugin", rel, 1, 1, "config")
    elif name.startswith("tailwind.config"):
        _add_component(project, "config", "tailwind-config", rel, 1, 1, "config")
    else:
        _add_component(project, "config", name, rel, 1, 1, "config")


def compute_stats(projects: List[ProjectIndex],
                  large_threshold: int = 50) -> dict:
    bucket_counts = {b: 0 for b in BUCKETS}
    total_components = 0
    name_counts: Dict[str, int] = {}
    large_count = 0
    warnings_count = 0

    security_findings = 0
    security_high = 0

    for p in projects:
        for bucket, comps in p.components.items():
            bucket_counts[bucket] += len(comps)
            total_components += len(comps)
            for c in comps:
                name_counts[c.name] = name_counts.get(c.name, 0) + 1
                if c.loc is not None and c.loc >= large_threshold:
                    large_count += 1

                if c.kind == "security":
                    security_findings += 1
                    if c.name.startswith("[HIGH]"):
                        security_high += 1

                if c.kind == "warning":
                    warnings_count += 1

    duplicate_names_count = sum(1 for n, cnt in name_counts.items() if cnt > 1)

    return {
        "total_projects": len(projects),
        "total_components": total_components,
        "bucket_counts": bucket_counts,
        "large_components_count": large_count,
        "duplicate_names_count": duplicate_names_count,
        "security_findings_count": security_findings,
        "security_high_count": security_high,
        "warnings_count": warnings_count,
    }

def scan_path(path: str | Path) -> ProjectIndex:
    """
    Scan a single folder (project/app/subfolder) and return a ProjectIndex.
    Useful for scanning an app like /nurbai/apps/produce.
    """
    p = Path(path)
    name = p.name
    # Tagging: if it has manage.py, it's a Django project; otherwise treat as a Python folder
    ptype = detect_project_type(p) if p.is_dir() else "Unknown"

    idx = ProjectIndex(
        name=name,
        path=str(p),
        type=ptype,
    )
    if p.exists() and p.is_dir():
        scan_single_project(p, idx)
    return idx

def _decorator_name(d: ast.AST) -> str:
    """
    Return best-effort name for a decorator node.
    """
    if isinstance(d, ast.Name):
        return d.id
    if isinstance(d, ast.Attribute):
        left = _decorator_name(d.value)
        return f"{left}.{d.attr}" if left else d.attr
    if isinstance(d, ast.Call):
        return _decorator_name(d.func)
    return ""


def _has_login_required_decorator(node: ast.AST) -> bool:
    """
    True if a function/method has a decorator named login_required (any dotted path).
    """
    decos = getattr(node, "decorator_list", []) or []
    for d in decos:
        nm = _decorator_name(d)
        if nm == "login_required" or nm.endswith(".login_required"):
            return True
    return False


def _is_probable_django_function_view(fn: ast.FunctionDef) -> bool:
    """
    Heuristic: FBV typically has first arg named 'request'.
    """
    if not fn.args.args:
        return False
    return fn.args.args[0].arg == "request"


def _class_uses_login_required_mixin(cls: ast.ClassDef) -> bool:
    """
    Checks if class inherits LoginRequiredMixin (directly or via dotted attribute).
    """
    for b in cls.bases or []:
        if isinstance(b, ast.Name) and b.id == "LoginRequiredMixin":
            return True
        if isinstance(b, ast.Attribute):
            nm = _decorator_name(b)
            if nm.endswith(".LoginRequiredMixin") or nm == "LoginRequiredMixin":
                return True
    return False


def _class_wrapped_with_login_required(cls: ast.ClassDef) -> bool:
    """
    Checks for @method_decorator(login_required, name="dispatch") style usage.
    """
    for d in cls.decorator_list or []:
        # looking for method_decorator(...)
        if isinstance(d, ast.Call):
            nm = _decorator_name(d.func)
            if nm == "method_decorator" or nm.endswith(".method_decorator"):
                # args include login_required?
                for a in d.args or []:
                    an = _decorator_name(a)
                    if an == "login_required" or an.endswith(".login_required"):
                        return True
                # sometimes passed as kwarg decorator=login_required
                for kw in d.keywords or []:
                    if kw.arg in {"decorator", "decorators"}:
                        kn = _decorator_name(kw.value)
                        if kn == "login_required" or kn.endswith(".login_required"):
                            return True
    return False
