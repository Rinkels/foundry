# Brief: Close the Athena → Claude Code seam

Status: proposed, not yet approved
Author: drafted with Claude (Cowork session), 2026-09-10
Target: the Foundry repo (`C:\Projects\foundry`)

---

## Why

Foundry governs everything on both sides of code generation and nothing at the
join. Athena versions prompts, requires approval, lints, and records every run.
Atlas provisions, deploys, backs up, and logs every action. Between them sits a
manual copy-paste: a human moves the design doc from the Studio into a Claude
Code terminal, and the resulting code has no recorded link back to the prompt
version, snapshot version, or design doc that produced it.

That gap is the only unaudited step in the pipeline, and it is the step that
writes the code.

Two phases close it. Phase 1 is useful on its own and ships first.

- **Phase 1 — push context down.** Render approved `AppContextSnapshot` rows and
  design docs into the *target* repo as files Claude Code reads natively, so an
  agent session starts from Foundry's reviewed description of the app instead of
  re-deriving it.
- **Phase 2 — invoke the agent.** Run Claude Code headlessly from Foundry
  against that exported context, and record the run against the prompt version,
  snapshot version, and design doc that produced it.

## Existing code you must build on (read these first)

| Path | What it gives you |
|---|---|
| `apps/athena/models.py` | `AppContextSnapshot` (versioned, `is_approved`, `snapshot_json`, `description_md`), `AthenaThread.last_design_doc`, `AthenaStudioRun`, `PromptTemplate`/`PromptVersion` |
| `apps/athena/views.py` | `studio_run_feature_designer`, `studio_run_app_builder`, `studio_create_impl_prompt`, `ingest_snapshot` |
| `apps/athena/services/runtime.py` | `get_template_by_role`, `get_canonical_version`, `athena_prompt` |
| `apps/atlas/services/shell.py` | `run(args, cwd, timeout, env)` — injection-safe subprocess runner, `resolve_tool` already handles Windows `.cmd` shims, returns `CommandResult` |
| `apps/atlas/services/provisioner.py` | `enqueue_deploy` / `process_pending` / `_async_worker` / `reclaim_stale` — the existing async-job pattern. **Mirror it. Do not invent a second one.** |
| `apps/atlas/models.py` | `CloudProject.source_path`, `DeploymentRun` (the audit-log shape to copy) |

## Non-goals

- Do not replace or modify the Implementation Generator prompt. Its output
  contract is the agent brief and stays as-is.
- Do not touch Atlas deploy behaviour. An agent run never triggers a deploy.
- Do not add Celery, Redis, or any new infrastructure dependency. Use the
  threading pattern already in `provisioner.py`.
- No changes to `sites_builder`, `okr`, `task`, `hermes`, `janus`, `argus`.

---

# Phase 1 — Context export

## Goal

An approved snapshot and an approved design doc become files inside the target
project's working tree, in the places Claude Code already looks.

## Requirements

**1. New service: `apps/athena/services/context_export.py`**

- `render_context_md(snapshot: AppContextSnapshot) -> str`
  Prefer `snapshot.description_md`. When blank, render `snapshot_json` into
  readable Markdown (do not dump raw JSON into `CLAUDE.md`).
  Include a provenance header: snapshot key, version, approved-at, approved-by.

- `export_context(snapshot, target_dir: Path, *, user=None) -> ContextExport`
  Writes the rendered context into `<target_dir>/CLAUDE.md`.

- `export_design_doc(studio_run_or_thread, target_dir: Path, *, user=None) -> ContextExport`
  Writes to `<target_dir>/docs/design/<snapshot-key>-<run-id>.md` and returns the
  path. Phase 2 depends on this path existing.

**2. Managed-block semantics — this is the important detail.**

`CLAUDE.md` in a target repo may be hand-authored. Never clobber it. Write only
between markers, and replace idempotently on re-export:

```
<!-- BEGIN FOUNDRY CONTEXT: <key> v<version> -->
...rendered context...
<!-- END FOUNDRY CONTEXT -->
```

- File missing → create it with the block.
- File exists without markers → append the block, leave existing content untouched.
- File exists with markers → replace only the block's interior.
- Re-exporting the same snapshot version must be a no-op byte-for-byte.

**3. New model: `ContextExport` (in `apps/athena/models.py`)**

FK to `AppContextSnapshot` (nullable), FK to `AthenaStudioRun` (nullable),
`kind` (`context` | `design_doc`), `target_path`, `bytes_written`,
`sha256`, `created_by`, `created_at`. This is the audit record; follow the field
conventions of `atlas.DeploymentRun`.

**4. Safety rules (enforce in code, not by convention)**

- Refuse to export a snapshot where `is_approved` is False.
- Resolve `target_dir` and refuse to write outside an allowlist:
  `CloudProject.source_path` values, plus `ATLAS_WORK_ROOT`, plus an explicit
  `ATHENA_EXPORT_ROOTS` setting. Reject `..` traversal after resolution.
- Never write into `foundry/` itself unless the target genuinely is Foundry.

**5. Entry points**

- Management command:
  `python manage.py athena_export_context --key <snapshot-key> [--version N] [--target <path>] [--design-doc <run-id>]`
  When `--target` is omitted, resolve via a matching `CloudProject.source_path`;
  error clearly if ambiguous or unresolvable.
- A POST view + Studio button: "Export context to repo", shown when the selected
  snapshot is approved and a target resolves. Returns JSON in the same shape as
  the existing Studio endpoints.

## Phase 1 acceptance criteria

- Exporting twice produces an identical file (no diff on the second run).
- A `CLAUDE.md` with pre-existing hand-written content survives export intact.
- An unapproved snapshot cannot be exported.
- A target path outside the allowlist is rejected with a clear error.
- Every successful export has a `ContextExport` row with a correct sha256.

---

# Phase 2 — Agent invocation

## Goal

Foundry runs Claude Code headlessly against an exported brief, in an isolated
branch, and records the run against the prompt version, snapshot version, and
design doc that produced it.

## Requirements

**1. New model: `AgentRun` (in `apps/athena/models.py`)**

Audit chain — all of these are the point of the feature, none are optional:

- FK `thread`, FK `studio_run` (the impl-generator run that produced the brief),
  FK `template` + FK `version` (PROTECT, as `AthenaStudioRun` does),
  FK `snapshot`, FK `context_export` (the design-doc export from Phase 1)
- `cloud_project` (nullable FK to `atlas.CloudProject`), `target_path`
- `status`: `pending` | `running` | `success` | `failed` | `cancelled`
- `brief_path` (the exported design doc the agent was told to read)
- `command` (the resolved arg list, joined, for the log)
- `log` (combined stdout/stderr — same as `DeploymentRun.log`)
- `exit_code`, `branch`, `base_commit`, `result_commit`, `diff_stat`
- `input_tokens` / `output_tokens` / `cost_usd` if parseable from output;
  reuse `apps/common/services/ai_pricing.py` rather than hardcoding rates
- `triggered_by`, `started_at`, `finished_at`

**2. Execution**

- Invoke through `apps.atlas.services.shell.run` with an **arg list**. Do not
  build a shell string, and do not extend `shell.py` with `shell=True`.
- **Pass the brief by file reference, not as an argument.** Windows has a hard
  command-line length limit and a design doc will exceed it. The prompt should be
  short and point at the Phase 1 export, e.g.
  `["claude", "-p", "Read <brief_path> and implement it. Follow CLAUDE.md.", ...]`.
  If you find you need to pass long text on stdin, add an optional `input_text`
  parameter to `shell.run` — additive, default `None`, no behaviour change for
  existing callers.
- `resolve_tool("claude")` already handles the Windows `.cmd` shim; verify this
  and raise `ToolNotFound` with an actionable message if the CLI is absent.
- Set an explicit timeout (default 1800s, configurable per run).

**3. Isolation — non-negotiable**

- Create a dedicated branch or git worktree per run
  (`foundry/agent/<agent-run-pk>`) off the current HEAD. **Never run the agent on
  `main` or on a dirty working tree.**
- Preflight: repo exists, is a git repo, working tree clean, `claude` resolvable.
  Fail the run before invoking anything if any check fails.
- Record `base_commit` before and `result_commit` + `git diff --stat` after.
- **Never** `git push`, never trigger an Atlas deploy, never merge.
- Do **not** use `--dangerously-skip-permissions`. Configure allowed tools
  explicitly and narrowly; put the setting in `settings.py` so it is reviewable.

**4. Concurrency — do not repeat the existing bug**

Agent runs take minutes. `studio_run_feature_designer` and
`studio_run_app_builder` currently hold `@transaction.atomic` open across a
synchronous LLM call; do not copy that. Follow `provisioner.enqueue_deploy`:
persist a `pending` row inside a short transaction, return immediately, and do
the work on a worker thread with `process_pending` / `reclaim_stale` equivalents
for crash recovery.

*Separately and optionally:* if it is a contained change, note in Open Questions
whether the two existing Studio handlers should be narrowed so the transaction
closes before the LLM call. Do not fold that refactor into this work uninvited.

**5. UI**

- Studio: "Run agent" action, enabled only when a design doc has been exported
  for the selected snapshot.
- An `AgentRun` list + detail view showing status, log, branch, diff stat, and
  links back to the prompt version, snapshot version, and studio run. Model it on
  the existing Atlas run views.

## Phase 2 acceptance criteria

- A completed `AgentRun` can answer, from stored fields alone: which prompt
  version, which snapshot version, which design doc, which branch, which commits.
- A run against a dirty working tree fails preflight and invokes nothing.
- A run never leaves `main` modified.
- A crashed worker leaves a row recoverable by the `reclaim_stale` equivalent.
- No request thread is held open for the duration of an agent run.

---

## Testing

Foundry has ~700 lines of tests, 695 of them in `sites_builder`. Athena and
Atlas have none. This work is load-bearing, so it ships with tests:

- `render_context_md` with and without `description_md`
- managed-block insert / replace / idempotency / preservation of hand-written content
- export allowlist rejection, including `..` traversal
- unapproved-snapshot rejection
- `AgentRun` preflight failures (missing CLI, dirty tree, bad target)
- the async lifecycle: enqueue → run → success/fail → reclaim stale
- `shell.run` argument construction (mock `subprocess.run`; assert an arg list,
  never a string, and assert no `--dangerously-skip-permissions`)

Mock all subprocess and network calls. No test may invoke the real `claude` CLI,
gcloud, or an LLM.

---

## Constraints

- Additive and backward-compatible. Do not remove or rename existing models,
  fields, endpoints, or prompt keys.
- Migrations safe for large datasets; sensible defaults; no destructive ops.
- Business logic in `services/`, not in views or templates.
- No secrets in the repo. `.gitignore` already covers `*.key`, `*.pem`, `.env`.
- Windows host: use `pathlib`, never assume POSIX separators.

## How to respond

Follow the repo's own Implementation Generator output contract — the one seeded
in `apps/athena/services/seeds.py`:

```
## Patch Plan
## New / Updated Models
## Migrations
## Admin Changes
## Views / URLs / Templates
## Services / Domain Logic
## Data Backfill (if applicable)
## Tests
## Rollout Notes
## Open Questions
```

**Plan first. Do not write code until the plan is approved.** Then implement
Phase 1 only, and stop for review before starting Phase 2.

Where a decision is ambiguous, put it in **Open Questions** rather than guessing.
Questions already known to be open:

1. Should exported context land in `CLAUDE.md`, a `.claude/skills/` entry, or
   both? (`CLAUDE.md` is assumed above as the smaller step.)
2. Is `CloudProject` the right owner of `target_path`, or should snapshots carry
   their own export target independent of whether the project is deployed?
3. Branch vs. git worktree for agent isolation — worktrees keep the main
   checkout untouched but complicate path resolution on Windows.
4. Should a failed `AgentRun` delete its branch, or leave it for inspection?
