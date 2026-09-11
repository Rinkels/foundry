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

At the top of the sidebar you choose the thread's **mode** — **Enhancement**
(work on an existing app; the flow above, snapshot-based) or **New App**
(greenfield; see the next section). Each execution is recorded as an
**AthenaStudioRun** (prompt version + inputs + output), so every output is
traceable to the exact prompt version that produced it.

---

## 3b. Creating a brand-new app (greenfield)

Use this when there is no existing codebase yet — you're designing an app from a
description rather than enhancing one. It needs **no App Context snapshot**.

**Prerequisite (one-time):** a prompt with the **App Builder** role, with an
approved/canonical version (Admin → assign role *App Builder*, then *“Approve
current version”*). The Studio finds it by role, not by name.

Steps in the Studio (`/athena/studio/`):

1. Open or start a thread and switch the mode toggle to **New App** (next to
   **Enhancement**). Your mode is saved per thread.
2. In the **User message** box, describe what you want to build — app name plus
   requirements (entities, workflows, roles, UI, constraints). This is the whole
   input; there's no snapshot to select.
3. Click **🧱 Run App Builder**. It runs the canonical App Builder prompt against
   your description and produces an **App Blueprint** (core entities, workflows,
   roles, UI, constraints, non-functional notes). The output is stored as the
   thread's **design doc** (`last_design_doc`), and the thread is auto-renamed
   from your description. Recorded as an **AthenaStudioRun**, same as any run.
4. Iterate: edit the requirements and re-run until the blueprint reads right.
5. Click **🛠 Create Implementation Generator** to turn that blueprint into a
   concrete implementation-generator prompt you can run like any other prompt.

**Where greenfield stops today.** The New App step produces a design doc and an
implementation prompt, but the **📤 Export / 🤖 Run agent** buttons (the headless
Claude Code seam) live in the *Enhancement* step and are **snapshot-based**, so
they are not wired for snapshot-less New App threads. To hand a brand-new app to
the headless agent: scaffold the initial repo (e.g. from the implementation
prompt's output), then treat it as an **existing** app — run Code Analyzer to
produce and approve an App Context snapshot, and follow the Enhancement +
Claude Code seam flow from there.

> Rule of thumb: **New App** designs the shape of something that doesn't exist
> yet; **Enhancement** (+ the agent seam) changes code that already does.

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

- refuses to run on a **dirty working tree** — *except* for this run's own
  exported brief / `CLAUDE.md` (see below); any **other** uncommitted change
  still blocks the run;
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

#### What about committing the exports?

You **don't** have to. 📤 Export writes `CLAUDE.md` + the design doc into the
target repo's working tree but doesn't commit them. When you 🤖 Run agent, the
run:

1. lets the preflight pass even though those two files are uncommitted — but
   *only* those two; any unrelated uncommitted change still blocks the run;
2. creates the worktree off HEAD, **copies the exported files into it, and
   commits them there** as a separate `Athena context export (run #<pk>)`
   commit — so the agent finds its brief and starts from a clean tree;
3. leaves your main checkout exactly as it was (the exports stay uncommitted
   there; commit or discard them at your leisure).

Because the export is committed separately in the worktree, it never pollutes
the agent's own diff.

---

## Golden path

**Enhancement (existing app):**

1. Approve a prompt version (library).
2. Ingest **and approve** an App Context snapshot for your app.
3. Studio: pick the snapshot → run **Feature Designer** → get a design doc.
4. **📤 Export** context + design doc into the repo.
5. **🤖 Run agent** → inspect the resulting branch/diff at **📜 Agent runs**.
   (No need to commit the exports first — the agent seeds them into its own
   worktree; see *“What about committing the exports?”* below.)
6. **Adopt the diff** — click **🔀 Merge branch** on the run detail page to
   merge the result branch into the target repo's current branch (the *agent*
   never merges itself; a reviewer does). Or merge from the command line.

**New app (greenfield):**

1. Approve an **App Builder** prompt version (library).
2. Studio: switch the thread to **New App** → describe the app in the User
   message → **🧱 Run App Builder** → get a blueprint (the thread's design doc).
3. **🛠 Create Implementation Generator** and run it to generate the initial
   code; scaffold the repo from that output.
4. To continue with the agent seam, snapshot the new repo (Code Analyzer) and
   switch to the **Enhancement** golden path above.

---

## Worked example — add a “Wishlist” to `bookstore`

Say you want to add a **Wishlist** feature to an existing app called
`bookstore`, which is a `CloudProject` in Atlas whose `source_path` is
`C:\Projects\bookstore`. *(IDs below are illustrative.)*

### 0. One-time: an approved prompt exists

In the library you already have a `feature_designer` prompt with an **approved**
version — say `feature_designer@v4`. If not: open the template, edit the body,
then Admin → *“Approve current version”*.

### 1. Get an approved App Context for `bookstore`

Code Analyzer scans the repo and posts a snapshot:

```
POST /athena/api/snapshots/ingest/    # body: the analyzed bookstore context
```

That creates `AppContextSnapshot(key="bookstore", version=1, is_approved=False)`.
Review it, then Admin → *“Approve selected snapshots”* → `is_approved=True`.
**Snapshot id = 12.**

### 2. Studio: design the feature

Open `/athena/studio/`, start a thread (“Bookstore wishlist”). In the sidebar
pick App Context → **bookstore v1** and your model settings. Click
**🎨 Feature Designer**. It renders `feature_designer@v4` against the context
and produces a design doc:

```markdown
## Patch Plan
Add a Wishlist so a customer can save books for later.

## New/Updated Models
- Wishlist(customer FK, created_at)
- WishlistItem(wishlist FK, book FK, added_at) — unique (wishlist, book)

## Migrations
- 0007_wishlist ...
## Views/URLs/Templates
- wishlist_detail, add_to_wishlist (POST) ...
## Tests
- add/remove item, dedupe, login-required ...
```

Saved on the thread (`last_design_doc`) and recorded as **AthenaStudioRun #45**,
which pins `feature_designer@v4` + snapshot 12 together.

### 3. Export context + design doc into the repo

Click **📤 Export context to repo** (posts `snapshot_id=12`, `run_id=45`). Two
files are written into `C:\Projects\bookstore`:

```
CLAUDE.md                          # managed block with the bookstore context
docs/design/bookstore-45.md        # the wishlist design doc
```

plus two sha256-audited `ContextExport` rows (`context` + `design_doc`, the
latter linked to StudioRun #45). Re-exporting is byte-identical, and notes you
hand-wrote in `CLAUDE.md` outside the managed block are untouched. CLI
equivalent:

```bash
python manage.py athena_export_context --key bookstore --design-doc
```

### 4. Run the agent

No manual commit needed — the two exported files can stay uncommitted in the
bookstore working tree; the agent seeds them into its worktree itself.

Click **🤖 Run agent**. It finds the latest design-doc export for snapshot 12
and enqueues **AgentRun #7**:

1. **Preflight** — git tree ✓, `claude` on PATH ✓, and the tree is clean *apart
   from* `CLAUDE.md` + `docs/design/bookstore-45.md` (allowed); any other
   uncommitted change would block here.
2. **Isolate + seed** — record base commit, then
   `git worktree add -b foundry/agent/7 ..\_athena_agent_worktrees\7 HEAD`, copy
   `CLAUDE.md` + `docs/design/bookstore-45.md` into the worktree and commit them
   there (`Athena context export (run #7)`) so the tree is clean and the brief
   is present.
3. **Run headless** (arg-list, narrow tools, never `--dangerously-skip-permissions`):
   ```
   claude -p "Read docs/design/bookstore-45.md and implement it. Follow CLAUDE.md.
              Do not commit, push, merge, or run any deploy commands."
          --allowedTools Read,Edit,Write,Grep,Glob,Bash(git status:*),Bash(git diff:*)
          --output-format json
   ```
   Claude writes the models, migration, views, and tests into the **worktree**
   — not your main checkout.
4. **Record** — commit the work onto `foundry/agent/7`; capture result commit,
   `diff --stat`, tokens, and estimated cost.

You are redirected to `/athena/agent-runs/7/`.

### 5. Review the run

`/athena/agent-runs/7/` shows, from stored fields alone:

| Field | Value |
| --- | --- |
| Status | `success` (exit 0) |
| Prompt | `feature_designer @ v4` |
| Snapshot | `bookstore v1` |
| Design doc | `…\bookstore\docs\design\bookstore-45.md` |
| Branch | `foundry/agent/7` |
| Base → result | `a1b2c3d` → `9f8e7d6` |
| Diff stat | `models.py \| 18 ++`, `migrations/0007… \| 30 ++`, `tests/test_wishlist.py \| 46 ++` … |
| Cost | ~`$0.14` (100k in / 40k out) |

plus the full agent log.

### 6. Adopt the work (you, not Athena)

Athena stops at an isolated branch — *you* decide whether to take it.

**From the UI:** on `/athena/agent-runs/7/`, click **🔀 Merge branch**. It merges
`foundry/agent/7` into the target repo's **current** branch, after committing the
still-uncommitted exported files (`CLAUDE.md`, the design doc) for you. It
refuses if the tree has other uncommitted changes, aborts cleanly on a conflict
(leaving the repo untouched), and **never pushes**. The run detail page then
shows a **merged** badge with the merge commit. The agent itself never merges —
this is always a human action.

**From the command line**, equivalently:

```bash
git -C C:/Projects/bookstore diff main..foundry/agent/7   # inspect
git -C C:/Projects/bookstore checkout main
git -C C:/Projects/bookstore merge foundry/agent/7        # if you like it
```

If the diff is wrong, throw the branch away and rerun — `main` was never
touched.

> **The point in one line:** AgentRun #7 permanently answers *which prompt
> version, which app snapshot, which design doc, and which commits produced this
> code* — the governance seam between Athena's prompts and Claude Code's edits.

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
