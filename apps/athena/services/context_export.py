"""Export approved Athena context + design docs into a target repo's working
tree, where Claude Code reads them natively (CLAUDE.md + docs/design/).

READ from the DB, WRITE only into an allowlist of directories
(CloudProject.source_path values + ATLAS_WORK_ROOT + ATHENA_EXPORT_ROOTS).
Unapproved snapshots cannot be exported. All path handling is pathlib-based
(Windows host). Writes are idempotent: re-exporting the same snapshot version
produces a byte-for-byte identical file.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from apps.athena.models import (
    AppContextSnapshot,
    AthenaStudioRun,
    AthenaThread,
    ContextExport,
)

CLAUDE_FILE = "CLAUDE.md"
BEGIN_TPL = "<!-- BEGIN FOUNDRY CONTEXT: {key} v{version} -->"
END_MARK = "<!-- END FOUNDRY CONTEXT -->"
# Matches a managed block of ANY key/version so re-exports replace in place.
_BLOCK_RE = re.compile(
    r"<!-- BEGIN FOUNDRY CONTEXT:.*?-->.*?<!-- END FOUNDRY CONTEXT -->",
    re.DOTALL,
)


class ExportError(RuntimeError):
    """Approval / allowlist / resolution failure — safe to surface to the user."""


# --------------------------------------------------------------- allowlist ---

def _allowed_roots() -> list[Path]:
    roots: list[Path] = []
    try:
        from apps.atlas.models import CloudProject
        for sp in (CloudProject.objects.exclude(source_path="")
                   .values_list("source_path", flat=True)):
            try:
                roots.append(Path(sp).resolve())
            except (OSError, ValueError, RuntimeError):
                pass
    except Exception:  # atlas import/db issues must never crash an export attempt
        pass
    work_root = getattr(settings, "ATLAS_WORK_ROOT", None)
    if work_root:
        roots.append(Path(work_root).resolve())
    for extra in getattr(settings, "ATHENA_EXPORT_ROOTS", []) or []:
        try:
            roots.append(Path(extra).resolve())
        except (OSError, ValueError, RuntimeError):
            pass
    seen: set[str] = set()
    out: list[Path] = []
    for r in roots:
        if str(r) not in seen:
            seen.add(str(r))
            out.append(r)
    return out


def _foundry_root() -> Path:
    return Path(settings.BASE_DIR).resolve()


def _resolve_target(target_dir: Path | str) -> Path:
    """Resolve `target_dir` and refuse anything outside the allowlist. `..` is
    collapsed by resolve(), so traversal that escapes an allowed root is rejected."""
    try:
        resolved = Path(target_dir).resolve()
    except (OSError, ValueError, RuntimeError) as exc:
        raise ExportError(f"Invalid target path: {target_dir} ({exc})")

    roots = _allowed_roots()
    if not roots:
        raise ExportError(
            "No export destinations configured. Set ATHENA_EXPORT_ROOTS, or add a "
            "CloudProject.source_path, or ATLAS_WORK_ROOT."
        )

    matched = next(
        (root for root in roots if resolved == root or resolved.is_relative_to(root)),
        None,
    )
    if matched is None:
        raise ExportError(f"Refusing to write outside the allowlist: {resolved}")

    foundry = _foundry_root()
    inside_foundry = resolved == foundry or resolved.is_relative_to(foundry)
    matched_is_foundry = matched == foundry or matched.is_relative_to(foundry)
    if inside_foundry and not matched_is_foundry:
        raise ExportError(f"Refusing to write into Foundry itself: {resolved}")
    return resolved


# ---------------------------------------------------------------- rendering ---

def _provenance_header(s: AppContextSnapshot) -> str:
    approved_at = s.approved_at.isoformat() if s.approved_at else "unknown"
    approved_by = "unknown"
    if s.approved_by is not None:
        approved_by = s.approved_by.get_username() or getattr(s.approved_by, "email", "") or "unknown"
    return (
        f"# {s.title}\n\n"
        f"> Foundry app context · `{s.key}` v{s.version} · "
        f"approved {approved_at} by {approved_by}\n"
    )


def _json_to_markdown(data, level: int = 2) -> str:
    hp = "#" * min(level, 6)
    if isinstance(data, dict):
        lines: list[str] = []
        for key, value in data.items():
            title = str(key).replace("_", " ").strip().title()
            if isinstance(value, dict) and value:
                lines.append(f"{hp} {title}\n")
                lines.append(_json_to_markdown(value, level + 1))
            elif isinstance(value, (list, tuple)) and value:
                lines.append(f"{hp} {title}\n")
                for item in value:
                    if isinstance(item, (dict, list, tuple)):
                        lines.append(_json_to_markdown(item, level + 1))
                    else:
                        lines.append(f"- {item}")
                lines.append("")
            else:
                lines.append(f"- **{title}:** {value}")
        return "\n".join(lines).strip() + "\n"
    if isinstance(data, (list, tuple)):
        return "\n".join(f"- {item}" for item in data) + "\n"
    return str(data)


def render_context_md(snapshot: AppContextSnapshot) -> str:
    """Prefer the reviewed description_md; otherwise render snapshot_json to
    readable Markdown (never dump raw JSON). Always carries a provenance header."""
    header = _provenance_header(snapshot)
    if (snapshot.description_md or "").strip():
        body = snapshot.description_md.strip()
    else:
        body = _json_to_markdown(snapshot.snapshot_json or {}).strip()
    return f"{header}\n{body}\n"


def _upsert_block(existing: str | None, key: str, version: int, rendered: str) -> str:
    """Insert/replace the managed block, leaving hand-authored content intact."""
    existing = existing or ""
    block = f"{BEGIN_TPL.format(key=key, version=version)}\n{rendered.rstrip()}\n{END_MARK}"
    if _BLOCK_RE.search(existing):
        return _BLOCK_RE.sub(lambda _m: block, existing, count=1)
    if existing.strip() == "":
        return block + "\n"
    sep = "\n" if existing.endswith("\n") else "\n\n"
    if existing.endswith("\n\n"):
        sep = ""
    return f"{existing}{sep}{block}\n"


# ------------------------------------------------------------ snapshot resolve ---

def _snapshot_for(run: AthenaStudioRun | None, thread: AthenaThread | None):
    sid = None
    if run is not None and isinstance(run.inputs_json, dict):
        sid = run.inputs_json.get("snapshot_id") or run.inputs_json.get("app_context_id")
    if not sid and thread is not None and isinstance(thread.ui_state, dict):
        sid = thread.ui_state.get("snapshot_id")
    if sid:
        return AppContextSnapshot.objects.filter(pk=sid).first()
    return None


def resolve_target_for_snapshot(snapshot: AppContextSnapshot) -> Path:
    """Best-effort map a snapshot to a deployed repo via CloudProject.source_path.
    Raises ExportError (asking for --target) if zero or multiple match."""
    from apps.atlas.models import CloudProject
    key = snapshot.key.lower()
    cands: list[str] = []
    for cp in CloudProject.objects.exclude(source_path=""):
        base = Path(cp.source_path).name.lower()
        if cp.slug.lower() == key or base == key:
            cands.append(cp.source_path)
    cands = list(dict.fromkeys(cands))
    if len(cands) == 1:
        return Path(cands[0])
    if not cands:
        raise ExportError(
            f"No CloudProject.source_path matches snapshot key '{snapshot.key}'. "
            f"Pass an explicit target."
        )
    raise ExportError(
        f"Multiple projects match '{snapshot.key}' ({cands}). Pass an explicit target."
    )


# ------------------------------------------------------------------ exports ---

def export_context(snapshot: AppContextSnapshot, target_dir: Path | str, *, user=None) -> ContextExport:
    if not snapshot.is_approved:
        raise ExportError(
            f"Snapshot '{snapshot.key}' v{snapshot.version} is not approved; refusing to export."
        )
    root = _resolve_target(target_dir)
    rendered = render_context_md(snapshot)
    claude_path = root / CLAUDE_FILE
    existing = claude_path.read_text(encoding="utf-8") if claude_path.exists() else ""
    data = _upsert_block(existing, snapshot.key, snapshot.version, rendered).encode("utf-8")

    if not (claude_path.exists() and claude_path.read_bytes() == data):
        claude_path.parent.mkdir(parents=True, exist_ok=True)
        claude_path.write_bytes(data)

    return ContextExport.objects.create(
        snapshot=snapshot,
        kind=ContextExport.KIND_CONTEXT,
        target_path=str(claude_path),
        bytes_written=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        created_by=user,
    )


def export_design_doc(studio_run_or_thread, target_dir: Path | str, *, user=None) -> ContextExport:
    root = _resolve_target(target_dir)
    if isinstance(studio_run_or_thread, AthenaStudioRun):
        run = studio_run_or_thread
        thread = run.thread
        text = run.response_text or ""
        run_ref = str(run.id)
    elif isinstance(studio_run_or_thread, AthenaThread):
        run = None
        thread = studio_run_or_thread
        text = thread.last_design_doc or ""
        run_ref = f"thread{thread.id}"
    else:
        raise ExportError("export_design_doc expects an AthenaStudioRun or AthenaThread.")

    if not text.strip():
        raise ExportError("No design-doc content to export.")

    snapshot = _snapshot_for(run, thread)
    key = snapshot.key if snapshot else "app"
    dest = root / "docs" / "design" / f"{key}-{run_ref}.md"
    data = text.strip().encode("utf-8") + b"\n"

    if not (dest.exists() and dest.read_bytes() == data):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

    return ContextExport.objects.create(
        snapshot=snapshot,
        studio_run=run,
        kind=ContextExport.KIND_DESIGN_DOC,
        target_path=str(dest),
        bytes_written=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        created_by=user,
    )
