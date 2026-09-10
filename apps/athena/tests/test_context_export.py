"""Phase 1 — Athena context export. All filesystem, no network/subprocess."""
from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path

from django.test import TestCase
from django.utils import timezone

from apps.athena.models import AppContextSnapshot, ContextExport
from apps.athena.services import context_export as ce
from apps.athena.services.context_export import (
    ExportError,
    export_context,
    render_context_md,
    _upsert_block,
)


def _snapshot(*, key="demo_app", version=1, approved=True, description_md="", snapshot_json=None):
    return AppContextSnapshot.objects.create(
        key=key, title="Demo App", app_path="/demo",
        version=version, is_approved=approved,
        approved_at=timezone.now() if approved else None,
        description_md=description_md, snapshot_json=snapshot_json or {},
    )


class RenderContextMdTests(TestCase):
    def test_prefers_description_md(self):
        snap = _snapshot(description_md="# Hand-authored\nThe reviewed description.")
        out = render_context_md(snap)
        self.assertIn("The reviewed description.", out)
        self.assertIn("`demo_app` v1", out)          # provenance header
        self.assertIn("approved", out)

    def test_renders_json_when_description_blank(self):
        snap = _snapshot(description_md="", snapshot_json={"models": ["Order", "Line"], "views": {"count": 3}})
        out = render_context_md(snap)
        self.assertIn("Models", out)                 # heading/label, humanised
        self.assertIn("Order", out)
        self.assertNotIn('{"models"', out)           # never raw JSON
        self.assertNotIn('"views":', out)


class ManagedBlockTests(TestCase):
    def test_insert_into_empty(self):
        out = _upsert_block("", "k", 2, "BODY")
        self.assertIn("<!-- BEGIN FOUNDRY CONTEXT: k v2 -->", out)
        self.assertIn("BODY", out)
        self.assertIn("<!-- END FOUNDRY CONTEXT -->", out)

    def test_append_preserves_handwritten(self):
        out = _upsert_block("hand-written notes\n", "k", 1, "BODY")
        self.assertTrue(out.startswith("hand-written notes"))
        self.assertIn("BEGIN FOUNDRY CONTEXT: k v1", out)

    def test_replace_in_place_across_versions(self):
        first = _upsert_block("intro\n", "k", 1, "OLD")
        second = _upsert_block(first, "k", 2, "NEW")
        self.assertIn("intro", second)
        self.assertIn("v2", second)
        self.assertIn("NEW", second)
        self.assertNotIn("v1", second)
        self.assertNotIn("OLD", second)
        self.assertEqual(second.count("BEGIN FOUNDRY CONTEXT"), 1)

    def test_idempotent(self):
        once = _upsert_block("", "k", 1, "BODY")
        twice = _upsert_block(once, "k", 1, "BODY")
        self.assertEqual(once, twice)


class ExportContextTests(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.override = self.settings(ATHENA_EXPORT_ROOTS=[str(self.root)])
        self.override.enable()
        self.addCleanup(self.override.disable)

    def _claude(self) -> Path:
        return self.root / "CLAUDE.md"

    def test_creates_file_and_row_with_sha256(self):
        snap = _snapshot(description_md="Body text.")
        export = export_context(snap, self.root)
        data = self._claude().read_bytes()
        self.assertEqual(export.sha256, hashlib.sha256(data).hexdigest())
        self.assertEqual(export.bytes_written, len(data))
        self.assertEqual(export.kind, ContextExport.KIND_CONTEXT)
        self.assertEqual(ContextExport.objects.count(), 1)

    def test_second_export_is_byte_identical(self):
        snap = _snapshot(description_md="Body text.")
        export_context(snap, self.root)
        first = self._claude().read_bytes()
        export_context(snap, self.root)
        second = self._claude().read_bytes()
        self.assertEqual(first, second)                       # no diff on re-export
        self.assertEqual(ContextExport.objects.count(), 2)    # but each call is audited

    def test_handwritten_content_survives(self):
        self._claude().write_text("# My own notes\nkeep me\n", encoding="utf-8")
        snap = _snapshot(description_md="Injected context.")
        export_context(snap, self.root)
        text = self._claude().read_text(encoding="utf-8")
        self.assertIn("# My own notes", text)
        self.assertIn("keep me", text)
        self.assertIn("Injected context.", text)

    def test_unapproved_snapshot_rejected(self):
        snap = _snapshot(approved=False, description_md="x")
        with self.assertRaises(ExportError) as ctx:
            export_context(snap, self.root)
        self.assertIn("not approved", str(ctx.exception).lower())
        self.assertFalse(self._claude().exists())

    def test_target_outside_allowlist_rejected(self):
        outside = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        snap = _snapshot(description_md="x")
        with self.assertRaises(ExportError) as ctx:
            export_context(snap, outside)                     # not in ATHENA_EXPORT_ROOTS
        self.assertIn("allowlist", str(ctx.exception).lower())

    def test_dotdot_traversal_rejected(self):
        snap = _snapshot(description_md="x")
        escaping = self.root / "sub" / ".." / ".." / "escape"
        with self.assertRaises(ExportError):
            export_context(snap, escaping)


from django.contrib.auth import get_user_model
from django.test import Client
from apps.athena.models import AthenaThread


class ExportViewTests(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        ov = self.settings(ATHENA_EXPORT_ROOTS=[str(self.root)])
        ov.enable()
        self.addCleanup(ov.disable)
        self.user = get_user_model().objects.create_user(username="tester", password="pw")
        self.client = Client()
        self.client.force_login(self.user)
        self.thread = AthenaThread.objects.create(title="t")

    def test_view_exports_and_returns_json(self):
        snap = _snapshot(description_md="Body.")
        resp = self.client.post(
            f"/athena/studio/{self.thread.id}/export-context/",
            {"snapshot_id": snap.id, "target": str(self.root)},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        self.assertTrue((self.root / "CLAUDE.md").exists())

    def test_view_rejects_unapproved(self):
        snap = _snapshot(approved=False, description_md="x")
        resp = self.client.post(
            f"/athena/studio/{self.thread.id}/export-context/",
            {"snapshot_id": snap.id, "target": str(self.root)},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["ok"])
