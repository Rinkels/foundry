from __future__ import annotations

import time
from collections import Counter, defaultdict
from typing import List, Dict

from django.db import transaction

from ..models import ScanRun, ScannedProject, ScanItem


def _severity_from_name(name: str) -> str:
    if name.startswith("[HIGH]"):
        return "HIGH"
    if name.startswith("[MED]"):
        return "MED"
    if name.startswith("[LOW]"):
        return "LOW"
    return ""


@transaction.atomic
def persist_scan(
    *,
    root_path: str,
    large_loc_threshold: int,
    projects,  # List[ProjectIndex] from scanner.py
    stats: dict,
    duration_ms: int,
) -> ScanRun:
    scan_run = ScanRun.objects.create(
        root_path=root_path,
        large_loc_threshold=large_loc_threshold,
        total_projects=stats.get("total_projects", 0),
        total_components=stats.get("total_components", 0),
        duplicate_names_count=stats.get("duplicate_names_count", 0),
        large_components_count=stats.get("large_components_count", 0),
        security_findings_count=stats.get("security_findings_count", 0),
        security_high_count=stats.get("security_high_count", 0),
        warnings_count=stats.get("warnings_count", 0),
        duration_ms=duration_ms,
    )

    for p in projects:
        # Flatten components to compute per-project counts
        all_items = []
        for bucket, comps in p.components.items():
            for c in comps:
                all_items.append((bucket, c))

        proj = ScannedProject.objects.create(
            scan_run=scan_run,
            name=p.name,
            path=p.path,
            project_type=p.type,
            components_count=sum(len(v) for v in p.components.values()),
            security_findings_count=len(p.components.get("security", [])),
            security_high_count=sum(1 for c in p.components.get("security", []) if str(c.name).startswith("[HIGH]")),
            warnings_count=len(p.components.get("warnings", [])),
        )

        # Identify duplicates by component name within the project
        name_counter = Counter(str(c.name) for _, c in all_items)
        duplicate_names = {n for n, cnt in name_counter.items() if cnt > 1}

        bulk = []
        for bucket, c in all_items:
            nm = str(c.name)
            loc = c.loc if getattr(c, "loc", None) is not None else None

            kind = getattr(c, "kind", "") or ""
            severity = ""
            if kind == "security":
                severity = _severity_from_name(nm)
            elif kind == "warning":
                severity = "LOW"  # treat warnings as low by default

            is_large = bool(loc is not None and loc >= large_loc_threshold)

            bulk.append(
                ScanItem(
                    scan_project=proj,
                    bucket=bucket,
                    kind=kind,
                    severity=severity,
                    name=nm,
                    file=str(c.file),
                    lineno=getattr(c, "lineno", None),
                    loc=loc,
                    is_duplicate_name=nm in duplicate_names,
                    is_large=is_large,
                )
            )

        ScanItem.objects.bulk_create(bulk, batch_size=2000)

    return scan_run
