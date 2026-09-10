# Using Athena

Athena is Foundry's **prompt-governance + code-generation** app. It has two
halves — a versioned **prompt library** and a **Studio** where those prompts run
against a real app's context — plus the **Claude Code seam** that carries a
design doc all the way into code in an isolated git worktree.

See also: [the seam brief](briefs/2026-09-10-athena-claude-code-seam.md).

---

## 1. The prompt library (governance)

Dashboard: `/athena/`.

- **PromptTemplate** — a stable, keyed prompt (e.g. `impl_generator`) with a
  **role**: `feature_designer`, `app_builder`, or `impl_generator`. The role is
  how the Studio pipeline selects the right prompt — not fuzzy name matching.
- **PromptVersion** — every edit is a new immutable version. Approve the version
  you trust as canonical (Admin action *“Approve current version”*, or the
  prompt-detail page). **The Studio only runs approved/canonical versions**, so
  experiments never leak into real runs.

Loop: create a template → set its role → write/edit the body → approve a version.

---

## 2. App Context snapshots (grounding)

The Studio runs against an **AppContextSnapshot**: a versioned, diff-friendly
description of a real app, produced by Code Analyzer and posted to Athena:

```
POST /athena/api/snapshots/ingest/
```

A snapshot must be **approved** before anything downstream can use it
(Admin → *“Approve selected snapshots”*). Approval is the gate: unapproved
context cannot be exported or fed to the agent.

---

## 3. Studio — the pipeline

Studio: `/athena/studio/`. A **thread** is one working session. In the sidebar
you pick an approved App Context snapshot and model settings, then run the
pipeline top to bottom:

- **🎨 Feature Designer** — takes the app context and produces a **design doc**
  (a Patch Plan following the Implementation Generator output contract: Models,
  Migrations, Admin, Views/URLs/Templates, Services, Tests, Rollout Notes, Open
  Questions). Saved on the thread as `last_design_doc`.
- **🛠 Create Implementation Generator** — turns that design doc into a concrete
  implementation prompt.
- **App Builder** — the greenfield variant, for a brand-new app (no snapshot
  required).

Each execution is recorded as an **AthenaStudioRun** (prompt version + inputs +
output), so every output is traceable to the exact prompt version that produced
it.

---

## 4. The Claude Code seam

The bridge from “a design doc in Athena” to “code in a repo.” Two steps, both
available as Studio buttons.

### 📤 Export context to repo

Writes the approved snapshot into the target repo's `CLAUDE.md` as an
**idempotent managed block** (hand-written content in the file survives), and —
when a run is passed — its design doc into `docs/design/`. Every export is a
sha256-audited **ContextExport** row.

Destinations are **allowlisted**: a `CloudProject.source_path`, `ATLAS_WORK_ROOT`,
or an entry in `ATHENA_EXPORT_ROOTS`. It refuses to write outside the allowlist
or into Foundry itself, and `..` traversal is collapsed and rejected.

Headless equivalent:

```bash
python manage.py athena_export_context --key demo_app --design-doc
# --version N     export a specific approved version (default: latest approved)
# --target PATH   explicit destination (default: resolve from CloudProject)
```

### 🤖 Run agent

Runs Claude Code headlessly against the exported design doc, in an **isolated
git worktree** — branch `foundry/agent/<run-pk>` off HEAD.

**Isolation is non-negotiable and enforced:**

- refuses to run on a **dirty working tree**;
- arg-list invocation with a **narrow `--allowedTools` allowlist**
  (`ATHENA_AGENT_ALLOWED_TOOLS`); **never** `--dangerously-skip-permissions`;
- **never** `git push`, never merges, never triggers a deploy;
- keeps the branch + worktree afterward (success *or* failure) for inspection.

Everything is recorded as an **AgentRun**: prompt version, snapshot, design doc,
branch, base/result commit, diff stat, token usage, and estimated cost
(`apps/common/services/ai_pricing`). Review runs at `/athena/agent-runs/`
(the 📜 button), with the full log and diff per run.

**Prerequisite for the button:** the design doc must already have been exported
*from a Studio run* (that is what carries the prompt-version provenance).
Otherwise “Run agent” returns a clear *“export a design doc first”* message.

---

## Golden path

1. Approve a prompt version (library).
2. Ingest **and approve** an App Context snapshot for your app.
3. Studio: pick the snapshot → run **Feature Designer** → get a design doc.
4. **📤 Export** context + design doc into the repo.
5. **Commit** those exported files (the agent needs a clean tree).
6. **🤖 Run agent** → inspect the resulting branch/diff at **📜 Agent runs**.
7. **Merge the agent's branch yourself** if you like the diff — Athena
   deliberately stops short of merging.

---

## Production / operations

In dev, exports and agent runs process **inline** in a background thread
(zero-setup). In production, disable the inline worker and run the drainer as a
long-lived process:

```bash
# .env
ATHENA_INLINE_WORKER=False
```

```bash
python manage.py athena_agent_worker                 # loop, poll every 5s
python manage.py athena_agent_worker --once           # drain pending then exit
python manage.py athena_agent_worker --reclaim 1800   # requeue runs stuck >30m
```

### Settings reference (`foundry/settings.py`)

| Setting | Purpose | Default |
| --- | --- | --- |
| `ATHENA_EXPORT_ROOTS` | Extra allowed export destinations (`os.pathsep`-separated) | *(empty)* |
| `ATHENA_AGENT_WORKTREE_ROOT` | Where per-run worktrees are created (sibling of the project) | `../_athena_agent_worktrees` |
| `ATHENA_AGENT_TIMEOUT` | Max seconds for a single headless run | `1800` |
| `ATHENA_INLINE_WORKER` | Process runs inline in dev; `False` in prod | mirrors `ATLAS_INLINE_WORKER` |
| `ATHENA_AGENT_ALLOWED_TOOLS` | Tools the agent may use without approval | `Read, Edit, Write, Grep, Glob, Bash(git status:*), Bash(git diff:*)` |
| `ATHENA_AGENT_MODEL` | Model name used for cost estimation only | `claude-opus-4-8` |

> **Note:** `ATHENA_AGENT_MODEL` is used only for cost estimation via
> `ai_pricing`; set it to whatever model the installed `claude` CLI actually
> uses. Token/cost parsing is best-effort from `claude -p --output-format json` —
> if the CLI's JSON shape differs, the token/cost fields simply stay blank and
> everything else still records.
