"""Phase 2 — run Claude Code headlessly against an exported brief, in an
ISOLATED git worktree, and record the run against its prompt version / snapshot
/ design doc.

Isolation is non-negotiable (see docs/briefs/2026-09-10-athena-claude-code-seam.md):
  * a dedicated branch + worktree per run: `foundry/agent/<agent-run-pk>` off HEAD;
  * NEVER run on a dirty working tree — preflight refuses one, EXCEPT for this
    run's own exported brief / CLAUDE.md (which Athena wrote and then seeds into
    the isolated worktree itself, so you don't have to commit them by hand). Any
    OTHER uncommitted change still blocks the run;
  * NEVER `git push`, never merge, never trigger an Atlas deploy;
  * NEVER `--dangerously-skip-permissions` — the agent gets an explicit, narrow
    `--allowedTools` list from settings and nothing more.

Worktrees and branches are kept after the run (success OR failure) so a human can
inspect / diff / cherry-pick the agent's work. The async lifecycle (enqueue →
pending row → inline thread or `athena_agent_worker`) mirrors atlas.provisioner.
"""
from __future__ import annotations

import json
import shutil
import threading
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import connections
from django.utils import timezone

from apps.common.services.ai_pricing import estimate_cost_usd

from apps.atlas.services import shell

from ..models import AgentRun, ContextExport


class AgentRunError(RuntimeError):
    """Preflight / resolution failure — safe to surface to the user."""


# --------------------------------------------------------------------------- #
# Log helpers (mirror provisioner._append / _finish_run)
# --------------------------------------------------------------------------- #

def _append(run: AgentRun, text: str) -> None:
    run.log = (run.log + "\n" + text).strip()
    run.save(update_fields=["log"])


def _finish(run: AgentRun, status: str, log: str = "") -> AgentRun:
    run.status = status
    if log:
        run.log = (run.log + "\n" + log).strip()
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "log", "finished_at"])
    return run


def _git(repo: Path, *args: str, timeout: int = 120) -> shell.CommandResult:
    return shell.run(["git", "-C", str(repo), *args], timeout=timeout)


def _worktree_root() -> Path:
    root = Path(getattr(settings, "ATHENA_AGENT_WORKTREE_ROOT",
                        Path(settings.BASE_DIR).parent / "_athena_agent_worktrees"))
    root.mkdir(parents=True, exist_ok=True)
    return root


CLAUDE_FILE = "CLAUDE.md"


def _export_rels(run: AgentRun) -> list[str]:
    """Repo-relative (posix) paths of THIS run's exported context — the only
    uncommitted files the preflight tolerates, and the files seeded into the
    worktree. Deterministic: the design-doc brief + the CLAUDE.md context block."""
    rels: list[str] = []
    if run.brief_path:
        rels.append(run.brief_path)
    rels.append(CLAUDE_FILE)
    return rels


def _dirty_paths(porcelain_output: str) -> list[str]:
    """Parse `git status --porcelain` into repo-relative posix paths. git emits
    forward slashes on every platform; a rename shows as 'old -> new'."""
    paths: list[str] = []
    for line in porcelain_output.splitlines():
        if not line.strip():
            continue
        p = line[3:] if len(line) > 3 else line
        if " -> " in p:
            p = p.split(" -> ", 1)[1]
        paths.append(p.strip().strip('"'))
    return paths


# --------------------------------------------------------------------------- #
# Enqueue
# --------------------------------------------------------------------------- #

def _resolve_cloud_project(repo: Path):
    """Best-effort: link the CloudProject whose source_path IS this repo."""
    try:
        from apps.atlas.models import CloudProject
        for cp in CloudProject.objects.exclude(source_path=""):
            try:
                if Path(cp.source_path).resolve() == repo:
                    return cp
            except (OSError, ValueError, RuntimeError):
                continue
    except Exception:  # atlas import/db issues must never block enqueue
        pass
    return None


def enqueue_agent_run(
    context_export: ContextExport,
    target_dir: Path | str,
    *,
    user=None,
    timeout_seconds: int | None = None,
) -> AgentRun:
    """Persist a pending AgentRun for a design-doc export and (optionally) kick
    it off inline. The design doc must come from a studio run so the prompt
    version is recorded — that IS the point of the seam.

    `target_dir` is the repo working tree the brief was exported into; the design
    doc must live inside it (that is how the agent finds the brief)."""
    if context_export.kind != ContextExport.KIND_DESIGN_DOC:
        raise AgentRunError("An agent run needs a design-doc export as its brief.")
    studio_run = context_export.studio_run
    if studio_run is None:
        raise AgentRunError(
            "This design-doc export has no linked studio run, so the prompt "
            "version can't be recorded. Re-export from a Studio run."
        )

    try:
        repo = Path(target_dir).resolve()
    except (OSError, ValueError, RuntimeError) as exc:
        raise AgentRunError(f"Invalid target path: {target_dir} ({exc})")

    brief = Path(context_export.target_path).resolve()
    if not (brief == repo or brief.is_relative_to(repo)):
        raise AgentRunError(
            f"Design doc {brief} is not inside the target repo {repo}."
        )
    brief_rel = brief.relative_to(repo).as_posix()

    run = AgentRun.objects.create(
        thread=studio_run.thread,
        studio_run=studio_run,
        template=studio_run.template,
        version=studio_run.version,
        snapshot=context_export.snapshot,
        context_export=context_export,
        cloud_project=_resolve_cloud_project(repo),
        target_path=str(repo),
        brief_path=brief_rel,
        status=AgentRun.STATUS_PENDING,
        timeout_seconds=timeout_seconds,
        triggered_by=user,
    )
    if getattr(settings, "ATHENA_INLINE_WORKER", getattr(settings, "ATLAS_INLINE_WORKER", True)):
        _process_async(run.pk)
    return run


# --------------------------------------------------------------------------- #
# Core run (preflight → worktree → headless claude → record)
# --------------------------------------------------------------------------- #

def _preflight(run: AgentRun, repo: Path) -> None:
    """Raise AgentRunError unless it is safe to run. Never mutates the repo."""
    if not repo.exists() or not repo.is_dir():
        raise AgentRunError(f"Target repo does not exist: {repo}")

    # Must be a git working tree.
    res = _git(repo, "rev-parse", "--is-inside-work-tree")
    if not res.ok or res.output.strip() != "true":
        raise AgentRunError(f"Not a git working tree: {repo}")

    # NON-NEGOTIABLE: refuse a dirty tree — EXCEPT for this run's own exported
    # brief / CLAUDE.md, which are seeded into the isolated worktree below. Any
    # OTHER uncommitted change still blocks the run.
    res = _git(repo, "status", "--porcelain")
    if not res.ok:
        raise AgentRunError(f"`git status` failed in {repo}:\n{res.output}")
    allowed = set(_export_rels(run))
    stray = [p for p in _dirty_paths(res.output) if p not in allowed]
    if stray:
        raise AgentRunError(
            "Refusing to run: the target working tree has uncommitted changes "
            "beyond Athena's exported context. Commit or stash them first.\n"
            + "\n".join(stray[:40])
        )

    # The CLI must be installed (fail fast with a clear message).
    shell.resolve_tool("claude")


def _parse_usage(output: str) -> tuple[int | None, int | None, str | None]:
    """Best-effort extract (input_tokens, output_tokens, reported_cost) from the
    JSON that `claude -p --output-format json` prints. Tolerant of extra text
    around the JSON and of missing fields."""
    if not output:
        return None, None, None
    text = output.strip()
    obj = None
    try:
        obj = json.loads(text)
    except (ValueError, TypeError):
        # Fall back to the last {...} block in mixed output.
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                obj = json.loads(text[start:end + 1])
            except (ValueError, TypeError):
                obj = None
    if not isinstance(obj, dict):
        return None, None, None
    usage = obj.get("usage") if isinstance(obj.get("usage"), dict) else {}
    in_tok = usage.get("input_tokens")
    out_tok = usage.get("output_tokens")
    cost = obj.get("total_cost_usd", obj.get("cost_usd"))
    return (
        int(in_tok) if isinstance(in_tok, (int, float)) else None,
        int(out_tok) if isinstance(out_tok, (int, float)) else None,
        str(cost) if cost is not None else None,
    )


def run_agent(run: AgentRun) -> AgentRun:
    """Execute the (already-persisted) AgentRun. Marks it running, isolates it in
    a worktree, runs the headless agent, records log/diff/cost, and finishes as
    success/failed. Keeps the worktree + branch either way for inspection."""
    run.status = AgentRun.STATUS_RUNNING
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at"])

    repo = Path(run.target_path)
    branch = f"foundry/agent/{run.pk}"
    worktree = _worktree_root() / str(run.pk)

    try:
        _preflight(run, repo)

        base = _git(repo, "rev-parse", "HEAD")
        if not base.ok:
            return _finish(run, AgentRun.STATUS_FAILED, f"Could not read HEAD:\n{base.output}")
        run.base_commit = base.output.strip().splitlines()[-1].strip()
        run.branch = branch
        run.save(update_fields=["base_commit", "branch"])

        # Isolated worktree off HEAD. If a stale one exists from a prior run with
        # this pk (shouldn't, pk is unique), refuse rather than clobber.
        if worktree.exists():
            return _finish(run, AgentRun.STATUS_FAILED, f"Worktree path already exists: {worktree}")
        add = _git(repo, "worktree", "add", "-b", branch, str(worktree), "HEAD")
        _append(run, add.command)
        _append(run, add.output)
        if not add.ok:
            return _finish(run, AgentRun.STATUS_FAILED, "Failed to create git worktree.")

        # Seed the isolated worktree with THIS run's exported brief / CLAUDE.md.
        # They may still be uncommitted in the main tree (the worktree is off
        # HEAD, which predates them), so we copy them in and commit them here —
        # the agent finds its brief without you committing exports by hand, and
        # the main checkout is left exactly as it was. Committing them separately
        # keeps them out of the agent's own diff.
        seeded: list[str] = []
        for rel in _export_rels(run):
            src = repo / rel
            if src.exists():
                dst = worktree / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                seeded.append(rel)
        seed_commit = ""
        if seeded:
            _git(worktree, "add", *seeded)
            staged = _git(worktree, "diff", "--cached", "--name-only")
            if staged.ok and staged.output.strip():
                _git(worktree, "-c", "user.name=Athena Agent",
                     "-c", "user.email=athena@foundry.local",
                     "commit", "-m", f"Athena context export (run #{run.pk})")
                head = _git(worktree, "rev-parse", "HEAD")
                if head.ok:
                    seed_commit = head.output.strip().splitlines()[-1].strip()
                _append(run, "Seeded worktree with exported context: " + ", ".join(seeded))

        # The brief MUST now be present in the worktree, or the agent has nothing
        # to implement.
        if not (worktree / run.brief_path).exists():
            return _finish(run, AgentRun.STATUS_FAILED,
                           f"Brief not found in worktree: {run.brief_path}. Export the design doc first.")

        # Headless agent. Arg-list only (no shell), explicit narrow tool allowlist,
        # NEVER --dangerously-skip-permissions.
        prompt = (
            f"Read {run.brief_path} and implement it. Follow the guidance in "
            f"CLAUDE.md. Do not commit, push, merge, or run any deploy commands."
        )
        cmd = [
            "claude", "-p", prompt,
            "--allowedTools", ",".join(settings.ATHENA_AGENT_ALLOWED_TOOLS),
            "--output-format", "json",
        ]
        run.command = " ".join(cmd)
        run.save(update_fields=["command"])

        timeout = run.timeout_seconds or getattr(settings, "ATHENA_AGENT_TIMEOUT", 1800)
        res = shell.run(cmd, cwd=worktree, timeout=timeout)
        run.exit_code = res.returncode
        _append(run, f"[claude exit {res.returncode}]")
        _append(run, res.output)
        run.save(update_fields=["exit_code"])

        # Cost / usage (best-effort).
        in_tok, out_tok, reported = _parse_usage(res.output)
        run.input_tokens, run.output_tokens = in_tok, out_tok
        if in_tok is not None or out_tok is not None:
            run.cost_usd = estimate_cost_usd(
                getattr(settings, "ATHENA_AGENT_MODEL", "claude-opus-4-8"),
                in_tok or 0, out_tok or 0,
            )
        run.save(update_fields=["input_tokens", "output_tokens", "cost_usd"])

        # Capture what the agent changed, committed to the isolated branch so
        # result_commit is meaningful. We NEVER push/merge/deploy.
        _git(worktree, "add", "-A")
        staged = _git(worktree, "diff", "--cached", "--name-only")
        if staged.ok and staged.output.strip():
            commit = _git(worktree, "-c", "user.name=Athena Agent",
                          "-c", "user.email=athena@foundry.local",
                          "commit", "-m", f"Athena agent run #{run.pk}")
            _append(run, commit.output)
            head = _git(worktree, "rev-parse", "HEAD")
            if head.ok:
                run.result_commit = head.output.strip().splitlines()[-1].strip()
            # Diff against the seed commit (if any) so the exported context does
            # not pollute the agent's own diff; else against the original base.
            diff_base = seed_commit or run.base_commit
            diff = _git(worktree, "diff", "--stat", f"{diff_base}..HEAD")
            run.diff_stat = diff.output.strip() if diff.ok else ""
        else:
            run.diff_stat = "(no changes)"
        run.save(update_fields=["result_commit", "diff_stat"])

        if res.returncode == 0:
            return _finish(run, AgentRun.STATUS_SUCCESS,
                           f"Agent finished. Branch {branch} kept at {worktree}.")
        return _finish(run, AgentRun.STATUS_FAILED,
                       f"Agent exited with code {res.returncode}. Worktree kept at {worktree}.")

    except AgentRunError as exc:
        return _finish(run, AgentRun.STATUS_FAILED, str(exc))
    except shell.ToolNotFound as exc:
        return _finish(run, AgentRun.STATUS_FAILED, str(exc))
    except Exception as exc:  # noqa: BLE001 — surface any error into the run log
        return _finish(run, AgentRun.STATUS_FAILED, f"Unexpected error: {exc}")


# --------------------------------------------------------------------------- #
# Durable queue (DB-backed) — mirrors atlas.provisioner
# --------------------------------------------------------------------------- #

def process_pending(limit: int | None = None) -> int:
    """Drain pending agent runs synchronously. Returns the number processed."""
    qs = AgentRun.objects.filter(status=AgentRun.STATUS_PENDING).order_by("started_at")
    if limit:
        qs = qs[:limit]
    processed = 0
    for run in list(qs):
        claimed = AgentRun.objects.filter(
            pk=run.pk, status=AgentRun.STATUS_PENDING
        ).update(status=AgentRun.STATUS_RUNNING)
        if not claimed:
            continue
        run.refresh_from_db()
        run_agent(run)
        processed += 1
    return processed


def reclaim_stale(older_than_seconds: int = 3600) -> int:
    """Reset runs stuck in 'running' (crashed worker) back to pending."""
    cutoff = timezone.now() - timedelta(seconds=older_than_seconds)
    return AgentRun.objects.filter(
        status=AgentRun.STATUS_RUNNING, started_at__lt=cutoff
    ).update(status=AgentRun.STATUS_PENDING)


def _process_async(run_pk: int) -> None:
    threading.Thread(target=_async_worker, args=(run_pk,), daemon=True).start()


def _async_worker(run_pk: int) -> None:
    try:
        claimed = AgentRun.objects.filter(
            pk=run_pk, status=AgentRun.STATUS_PENDING
        ).update(status=AgentRun.STATUS_RUNNING)
        if not claimed:
            return
        run = AgentRun.objects.get(pk=run_pk)
        run_agent(run)
    except AgentRun.DoesNotExist:
        pass
    finally:
        connections.close_all()
