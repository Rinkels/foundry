"""Phase 2 — Athena agent invocation. All subprocess/git/CLI is MOCKED; no real
`claude`, `git`, network, or LLM is ever touched."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from apps.athena.models import (
    AgentRun,
    AppContextSnapshot,
    AthenaStudioRun,
    AthenaThread,
    ContextExport,
    PromptTemplate,
    PromptVersion,
)
from apps.athena.services import agent_runner
from apps.athena.services.agent_runner import AgentRunError
from apps.atlas.services.shell import CommandResult, ToolNotFound


def _cmd(args, out="", rc=0):
    return CommandResult(returncode=rc, output=out, command=" ".join(map(str, args)))


class _FakeGit:
    """A stand-in for shell.run that answers git/claude calls deterministically.

    `status_output` drives the dirty-tree check; `claude_rc`/`claude_out` drive
    the headless run; `is_worktree` drives the git-repo preflight."""

    def __init__(self, *, status_output="", claude_rc=0, claude_out="{}", is_worktree=True,
                 has_changes=True):
        self.status_output = status_output
        self.claude_rc = claude_rc
        self.claude_out = claude_out
        self.is_worktree = is_worktree
        self.has_changes = has_changes
        self.calls: list[list[str]] = []

    def __call__(self, args, *, cwd=None, timeout=1800, env=None, input_text=None):
        args = list(args)
        self.calls.append(args)
        tool = args[0]
        if tool == "git":
            sub = args[3] if len(args) > 3 else ""  # ["git","-C",repo,<sub>,...]
            if sub == "rev-parse" and "--is-inside-work-tree" in args:
                return _cmd(args, "true\n" if self.is_worktree else "false\n",
                            0 if self.is_worktree else 128)
            if sub == "status":
                return _cmd(args, self.status_output)
            if sub == "rev-parse":  # HEAD / result HEAD
                return _cmd(args, "a1b2c3d4\n")
            if sub == "worktree":
                return _cmd(args, "Preparing worktree\n")
            if sub == "diff" and "--cached" in args and "--name-only" in args:
                return _cmd(args, "apps/foo.py\n" if self.has_changes else "")
            if sub == "diff":
                return _cmd(args, " apps/foo.py | 2 +-\n" if self.has_changes else "")
            if "commit" in args:
                return _cmd(args, "[branch abc] msg\n")
            if sub == "add":
                return _cmd(args, "")
            return _cmd(args, "")
        if tool == "claude":
            return _cmd(args, self.claude_out, self.claude_rc)
        return _cmd(args, "")


class _Fixtures:
    def _make_export(self, *, kind=ContextExport.KIND_DESIGN_DOC, with_run=True):
        tmpl = PromptTemplate.objects.create(key="demo_app", name="Impl Gen")
        ver = PromptVersion.objects.create(template=tmpl, version=3)
        thread = AthenaThread.objects.create(title="t")
        snap = AppContextSnapshot.objects.create(
            key="demo_app", title="Demo", app_path="/demo", version=1,
            is_approved=True, approved_at=timezone.now(),
        )
        run = None
        if with_run:
            run = AthenaStudioRun.objects.create(
                thread=thread, template=tmpl, version=ver, response_text="## Patch Plan\n...",
            )
        brief = self.repo / "docs" / "design" / "demo_app-1.md"
        brief.parent.mkdir(parents=True, exist_ok=True)
        brief.write_text("brief", encoding="utf-8")
        export = ContextExport.objects.create(
            snapshot=snap, studio_run=run, kind=kind,
            target_path=str(brief), bytes_written=5, sha256="x" * 64,
        )
        return export


class EnqueueTests(TestCase, _Fixtures):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        ov = self.settings(ATHENA_INLINE_WORKER=False)  # don't auto-run in enqueue tests
        ov.enable()
        self.addCleanup(ov.disable)

    def test_enqueue_creates_pending_with_provenance(self):
        export = self._make_export()
        run = agent_runner.enqueue_agent_run(export, self.repo)
        self.assertEqual(run.status, AgentRun.STATUS_PENDING)
        self.assertEqual(run.template, export.studio_run.template)
        self.assertEqual(run.version, export.studio_run.version)
        self.assertEqual(run.snapshot, export.snapshot)
        self.assertEqual(run.context_export, export)
        self.assertEqual(run.brief_path, "docs/design/demo_app-1.md")

    def test_enqueue_rejects_non_design_doc(self):
        export = self._make_export(kind=ContextExport.KIND_CONTEXT)
        with self.assertRaises(AgentRunError):
            agent_runner.enqueue_agent_run(export, self.repo)

    def test_enqueue_rejects_design_doc_without_studio_run(self):
        export = self._make_export(with_run=False)
        with self.assertRaises(AgentRunError):
            agent_runner.enqueue_agent_run(export, self.repo)

    def test_enqueue_rejects_brief_outside_repo(self):
        export = self._make_export()
        other = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, other, ignore_errors=True)
        with self.assertRaises(AgentRunError):
            agent_runner.enqueue_agent_run(export, other)


class RunAgentTests(TestCase, _Fixtures):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        self.wtroot = Path(tempfile.mkdtemp()).resolve()
        shutil.rmtree(self.wtroot, ignore_errors=True)  # let the runner create children
        self.addCleanup(shutil.rmtree, self.wtroot, ignore_errors=True)
        ov = self.settings(ATHENA_INLINE_WORKER=False, ATHENA_AGENT_WORKTREE_ROOT=self.wtroot)
        ov.enable()
        self.addCleanup(ov.disable)

    def _pending(self):
        return agent_runner.enqueue_agent_run(self._make_export(), self.repo)

    def test_success_records_diff_and_never_pushes(self):
        run = self._pending()
        fake = _FakeGit(claude_rc=0, claude_out='{"usage":{"input_tokens":100,"output_tokens":40}}')
        with mock.patch.object(agent_runner.shell, "run", fake), \
             mock.patch.object(agent_runner.shell, "resolve_tool", lambda n: n):
            agent_runner.run_agent(run)
        run.refresh_from_db()
        self.assertEqual(run.status, AgentRun.STATUS_SUCCESS)
        self.assertEqual(run.exit_code, 0)
        self.assertEqual(run.branch, f"foundry/agent/{run.pk}")
        self.assertEqual(run.input_tokens, 100)
        self.assertEqual(run.output_tokens, 40)
        self.assertIsNotNone(run.cost_usd)
        # NON-NEGOTIABLE: no git push / merge anywhere (check git subcommands,
        # not substrings — the claude prompt itself mentions "push"/"merge").
        git_subs = [c[3] for c in fake.calls if c and c[0] == "git" and len(c) > 3]
        self.assertNotIn("push", git_subs)
        self.assertNotIn("merge", git_subs)

    def test_claude_invocation_is_arglist_and_safe(self):
        run = self._pending()
        fake = _FakeGit(claude_rc=0)
        with mock.patch.object(agent_runner.shell, "run", fake), \
             mock.patch.object(agent_runner.shell, "resolve_tool", lambda n: n):
            agent_runner.run_agent(run)
        claude_calls = [c for c in fake.calls if c and c[0] == "claude"]
        self.assertEqual(len(claude_calls), 1)
        args = claude_calls[0]
        self.assertIsInstance(args, list)                       # arg list, never a shell string
        self.assertIn("--output-format", args)
        self.assertIn("--allowedTools", args)
        self.assertNotIn("--dangerously-skip-permissions", args)

    def test_dirty_with_only_exports_is_allowed(self):
        # The whole point of option 2: uncommitted CLAUDE.md + the exported
        # design doc must NOT block the run — they are seeded into the worktree.
        run = self._pending()
        fake = _FakeGit(status_output=" M CLAUDE.md\n?? docs/design/demo_app-1.md\n",
                        claude_rc=0)
        with mock.patch.object(agent_runner.shell, "run", fake), \
             mock.patch.object(agent_runner.shell, "resolve_tool", lambda n: n):
            agent_runner.run_agent(run)
        run.refresh_from_db()
        self.assertEqual(run.status, AgentRun.STATUS_SUCCESS)
        # It seeded the worktree and reached the agent.
        self.assertTrue(any(c and c[0] == "claude" for c in fake.calls))
        self.assertIn("seeded", run.log.lower())

    def test_dirty_tree_refused(self):
        run = self._pending()
        fake = _FakeGit(status_output=" M apps/foo.py\n")
        with mock.patch.object(agent_runner.shell, "run", fake), \
             mock.patch.object(agent_runner.shell, "resolve_tool", lambda n: n):
            agent_runner.run_agent(run)
        run.refresh_from_db()
        self.assertEqual(run.status, AgentRun.STATUS_FAILED)
        self.assertIn("uncommitted changes", run.log.lower())
        self.assertIn("apps/foo.py", run.log)
        # It must bail BEFORE creating a worktree or invoking claude.
        self.assertFalse(any(c and c[0] == "claude" for c in fake.calls))
        self.assertFalse(any("worktree" in c for c in fake.calls))

    def test_missing_cli_fails_cleanly(self):
        run = self._pending()
        fake = _FakeGit()

        def _no_claude(name):
            if name == "claude":
                raise ToolNotFound("`claude` was not found on PATH.")
            return name

        with mock.patch.object(agent_runner.shell, "run", fake), \
             mock.patch.object(agent_runner.shell, "resolve_tool", _no_claude):
            agent_runner.run_agent(run)
        run.refresh_from_db()
        self.assertEqual(run.status, AgentRun.STATUS_FAILED)
        self.assertIn("claude", run.log.lower())

    def test_agent_nonzero_exit_marks_failed(self):
        run = self._pending()
        fake = _FakeGit(claude_rc=2, has_changes=False)
        with mock.patch.object(agent_runner.shell, "run", fake), \
             mock.patch.object(agent_runner.shell, "resolve_tool", lambda n: n):
            agent_runner.run_agent(run)
        run.refresh_from_db()
        self.assertEqual(run.status, AgentRun.STATUS_FAILED)
        self.assertEqual(run.exit_code, 2)
        self.assertEqual(run.diff_stat, "(no changes)")


class MergeTests(TestCase, _Fixtures):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        ov = self.settings(ATHENA_INLINE_WORKER=False)
        ov.enable()
        self.addCleanup(ov.disable)

    def _success_run(self):
        run = agent_runner.enqueue_agent_run(self._make_export(), self.repo)
        run.status = AgentRun.STATUS_SUCCESS
        run.branch = f"foundry/agent/{run.pk}"
        run.result_commit = "9f8e7d6"
        run.save()
        return run

    class _MergeGit:
        """shell.run stand-in for merges. `on_branch` is the repo's current
        branch; `status_output` its dirtiness; `merge_ok` the merge outcome."""
        def __init__(self, *, on_branch="main", status_output="", merge_ok=True):
            self.on_branch = on_branch
            self.status_output = status_output
            self.merge_ok = merge_ok
            self.calls = []

        def __call__(self, args, *, cwd=None, timeout=1800, env=None, input_text=None):
            args = list(args); self.calls.append(args)
            sub = args[3] if len(args) > 3 else ""
            if sub == "rev-parse" and "--is-inside-work-tree" in args:
                return _cmd(args, "true\n")
            if sub == "rev-parse" and "--abbrev-ref" in args:
                return _cmd(args, self.on_branch + "\n")
            if sub == "status":
                return _cmd(args, self.status_output)
            if sub == "diff" and "--cached" in args:
                return _cmd(args, "docs/design/demo_app-1.md\n" if self.status_output else "")
            if sub == "merge" and "--abort" in args:
                return _cmd(args, "aborted\n")
            if sub == "merge":
                return _cmd(args, "Merge made\n" if self.merge_ok else "CONFLICT\n",
                            0 if self.merge_ok else 1)
            if sub == "rev-parse":
                return _cmd(args, "abc1234\n")
            return _cmd(args, "")

    def test_merge_success_records_and_never_pushes(self):
        run = self._success_run()
        fake = self._MergeGit(on_branch="main")
        with mock.patch.object(agent_runner.shell, "run", fake):
            agent_runner.merge_agent_run(run)
        run.refresh_from_db()
        self.assertIsNotNone(run.merged_at)
        self.assertEqual(run.merged_into, "main")
        self.assertEqual(run.merge_commit, "abc1234")
        subs = [c[3] for c in fake.calls if c and c[0] == "git" and len(c) > 3]
        self.assertNotIn("push", subs)

    def test_merge_conflict_aborts(self):
        run = self._success_run()
        fake = self._MergeGit(on_branch="main", merge_ok=False)
        with mock.patch.object(agent_runner.shell, "run", fake):
            with self.assertRaises(AgentRunError):
                agent_runner.merge_agent_run(run)
        run.refresh_from_db()
        self.assertIsNone(run.merged_at)
        subs = [" ".join(c) for c in fake.calls]
        self.assertTrue(any("merge --abort" in s for s in subs))

    def test_merge_refuses_when_on_result_branch(self):
        run = self._success_run()
        fake = self._MergeGit(on_branch=f"foundry/agent/{run.pk}")
        with mock.patch.object(agent_runner.shell, "run", fake):
            with self.assertRaises(AgentRunError):
                agent_runner.merge_agent_run(run)

    def test_merge_refuses_stray_dirty(self):
        run = self._success_run()
        fake = self._MergeGit(on_branch="main", status_output=" M apps/other.py\n")
        with mock.patch.object(agent_runner.shell, "run", fake):
            with self.assertRaises(AgentRunError):
                agent_runner.merge_agent_run(run)

    def test_merge_refuses_non_success(self):
        run = agent_runner.enqueue_agent_run(self._make_export(), self.repo)  # pending
        with self.assertRaises(AgentRunError):
            agent_runner.merge_agent_run(run)


class QueueTests(TestCase, _Fixtures):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        ov = self.settings(ATHENA_INLINE_WORKER=False)
        ov.enable()
        self.addCleanup(ov.disable)

    def test_process_pending_claims_and_runs(self):
        run = agent_runner.enqueue_agent_run(self._make_export(), self.repo)
        with mock.patch.object(agent_runner, "run_agent") as m:
            n = agent_runner.process_pending()
        self.assertEqual(n, 1)
        m.assert_called_once()
        self.assertEqual(m.call_args.args[0].pk, run.pk)

    def test_reclaim_stale_requeues(self):
        run = agent_runner.enqueue_agent_run(self._make_export(), self.repo)
        AgentRun.objects.filter(pk=run.pk).update(
            status=AgentRun.STATUS_RUNNING,
            started_at=timezone.now() - timezone.timedelta(hours=2),
        )
        n = agent_runner.reclaim_stale(3600)
        self.assertEqual(n, 1)
        run.refresh_from_db()
        self.assertEqual(run.status, AgentRun.STATUS_PENDING)


class RunAgentViewTests(TestCase, _Fixtures):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        ov = self.settings(ATHENA_INLINE_WORKER=False)
        ov.enable()
        self.addCleanup(ov.disable)
        self.user = get_user_model().objects.create_user(username="tester", password="pw")
        self.client = Client()
        self.client.force_login(self.user)

    def test_run_agent_view_enqueues(self):
        export = self._make_export()
        thread = export.studio_run.thread
        resp = self.client.post(
            f"/athena/studio/{thread.id}/run-agent/",
            {"snapshot_id": export.snapshot_id, "target": str(self.repo)},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["ok"])
        self.assertEqual(AgentRun.objects.get(pk=body["agent_run_id"]).status, AgentRun.STATUS_PENDING)

    def test_run_agent_view_requires_design_doc_export(self):
        # A thread/snapshot with no design-doc export → clear 400.
        thread = AthenaThread.objects.create(title="t2")
        snap = AppContextSnapshot.objects.create(
            key="nope", title="N", app_path="/n", version=1, is_approved=True,
        )
        resp = self.client.post(
            f"/athena/studio/{thread.id}/run-agent/",
            {"snapshot_id": snap.id, "target": str(self.repo)},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["ok"])
