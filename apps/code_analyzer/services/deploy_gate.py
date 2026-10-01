"""Diff-aware findings + a deploy gate.

Compares a project's security findings in one scan to the *same project* in the
previous scan, so Atlas can see **new** findings (regressions) — not the whole
backlog — before a deploy.

Finding identity = (file, normalized message), NOT line number (lines shift), so
a finding that just moved isn't counted as new. The gate verdict:

- block — a NEW HIGH-severity, high-exposure finding appeared (a real regression)
- warn  — some NEW finding appeared (high-exposure or HIGH, or any new)
- pass  — no new findings vs the previous scan
- baseline / no_data — first scan (nothing to compare) / project never scanned
"""
from __future__ import annotations

import hashlib
import os

from ..models import ScanItem, ScannedProject
from . import ranking


def _fp(item) -> str:
    key = f"{(item.file or '').replace(chr(92), '/').lower()}|{(item.name or '').strip().lower()}"
    return hashlib.sha1(key.encode("utf-8", "ignore")).hexdigest()[:16]


def _sec_items(sp: ScannedProject | None) -> list:
    if sp is None:
        return []
    return list(ScanItem.objects.filter(scan_project=sp, bucket="security"))


def _prev_scanned(sp: ScannedProject) -> ScannedProject | None:
    """Same-named project in the most recent scan BEFORE this one."""
    return (ScannedProject.objects
            .filter(name=sp.name, scan_run__created_at__lt=sp.scan_run.created_at)
            .select_related("scan_run")
            .order_by("-scan_run__created_at", "-scan_run_id")
            .first())


def diff_scanned(sp: ScannedProject) -> dict:
    cur = _sec_items(sp)
    cur_by_fp = {_fp(i): i for i in cur}
    prev_sp = _prev_scanned(sp)
    prev_fps = {_fp(i) for i in _sec_items(prev_sp)}
    new = [i for fp, i in cur_by_fp.items() if fp not in prev_fps]
    resolved = len(prev_fps - set(cur_by_fp)) if prev_sp else 0
    return {
        "sp": sp, "prev_sp": prev_sp,
        "new": ranking.annotate_and_sort(new),
        "new_fps": {fp for fp in cur_by_fp if fp not in prev_fps},
        "new_count": len(new), "resolved_count": resolved,
        "total": len(cur), "baseline": prev_sp is None,
    }


def gate_scanned(sp: ScannedProject) -> dict:
    d = diff_scanned(sp)
    new = d["new"]
    new_high_exp = [i for i in new if i.severity_label == "HIGH" and i.exposure == "high"]
    new_high = [i for i in new if i.severity_label == "HIGH"]
    new_exposed = [i for i in new if i.exposure == "high"]

    if d["baseline"]:
        status = "baseline"
    elif new_high_exp:
        status = "block"
    elif new_high or new_exposed or d["new_count"]:
        status = "warn"
    else:
        status = "pass"

    return {
        "status": status, "scanned": True,
        "project": sp.name, "run_id": sp.scan_run_id,
        "prev_run_id": d["prev_sp"].scan_run_id if d["prev_sp"] else None,
        "new_count": d["new_count"], "resolved_count": d["resolved_count"],
        "new_high": len(new_high), "new_high_exposure": len(new_high_exp),
        "total": d["total"], "new": new,
    }


def _latest_scanned(name: str) -> ScannedProject | None:
    return (ScannedProject.objects
            .filter(name__iexact=name)
            .select_related("scan_run")
            .order_by("-scan_run__created_at", "-scan_run_id")
            .first())


def gate_for_name(name: str) -> dict:
    sp = _latest_scanned(name)
    if not sp:
        return {"status": "no_data", "scanned": False, "project": name, "new_count": 0}
    return gate_scanned(sp)


def gate_for_cloudproject(cp) -> dict:
    """Resolve an Atlas CloudProject to a scanned project by slug / source dir / name."""
    candidates = [cp.slug]
    if getattr(cp, "source_path", ""):
        candidates.append(os.path.basename(cp.source_path.rstrip("/\\")))
    candidates.append(cp.name)
    for c in candidates:
        if c and _latest_scanned(c):
            return gate_for_name(c)
    return {"status": "no_data", "scanned": False, "project": cp.name, "new_count": 0}
