"""Sweep orchestration: scope -> queries -> detect -> deduplicated Exposures.

One `WatchProfile` in, one `WatchRun` out. Everything the run did (including
what it *didn't* get to) lands in `WatchRun.log`, because a report that quietly
covered less than it claims is worse than no report.
"""
from __future__ import annotations

import traceback
from itertools import zip_longest

from django.db import transaction
from django.utils import timezone

from ..models import Exposure, WatchProfile, WatchRun
from . import code_search, detect

DEFAULT_MAX_QUERIES = 40


def build_queries(profile: WatchProfile, *, max_queries: int) -> tuple[list[str], int]:
    """Build the query plan, ordered by signal-to-noise.

    GitHub code search ANDs its terms, which gives us the single most valuable
    query shape available: `"acme.com" "AKIA"` finds files that contain the
    customer's identifier *and* a credential marker. That pairing is what makes
    unscoped searching viable at all — a bare keyword search across all of
    GitHub returns crawler datasets, while the paired form returns almost
    nothing that isn't worth reading.

    Order matters because `max_queries` truncates the tail. The two
    high-value families are **interleaved** rather than concatenated: a global
    sweep can produce hundreds of paired queries, and if those all ran first a
    capped run would never reach the customer's own org at all.

        A. global paired      — company identifier + credential marker
        B. scoped credential  — every credential marker inside known repos
           (A and B round-robin, so truncation costs both evenly)
        C. scoped keyword     — identifier mentions inside known repos
        D. global bare        — identifier anywhere (noisy; last on purpose)

    Returns (queries, skipped_count).
    """
    scopes = profile.scope_qualifiers
    keywords = profile.keyword_list
    cred_terms = detect.search_terms_for()  # credential markers only
    go_global = profile.search_globally and bool(keywords)

    bucket_a = (
        [f'"{kw}" "{term}"' for term in cred_terms for kw in keywords] if go_global else []
    )
    bucket_b = [f'"{term}" {scope}' for term in cred_terms for scope in scopes]
    bucket_c = [f'"{kw}" {scope}' for kw in keywords for scope in scopes]
    bucket_d = [f'"{kw}"' for kw in keywords] if go_global else []

    queries: list[str] = []
    seen: set[str] = set()

    def add(q: str) -> None:
        if q not in seen:
            seen.add(q)
            queries.append(q)

    for a, b in zip_longest(bucket_a, bucket_b):
        if a:
            add(a)
        if b:
            add(b)
    for q in bucket_c + bucket_d:
        add(q)

    if len(queries) <= max_queries:
        return queries, 0
    return queries[:max_queries], len(queries) - max_queries


@transaction.atomic
def _record_finding(
    profile: WatchProfile,
    run: WatchRun,
    finding: detect.Finding,
    *,
    repo_full_name: str,
    file_path: str,
    url: str,
) -> bool:
    """Upsert one finding. Returns True if it was new."""
    fp = detect.fingerprint(repo_full_name, file_path, finding.detector, finding.fingerprint_value)
    now = timezone.now()

    severity, path_note = detect.adjust_for_path(finding.severity, file_path)
    note = " ".join(n for n in (finding.note, path_note) if n)

    existing = Exposure.objects.select_for_update().filter(profile=profile, fingerprint=fp).first()
    if existing:
        existing.last_seen = now
        existing.times_seen += 1
        # A finding we'd marked resolved but can still see is not resolved.
        if existing.status == Exposure.STATUS_RESOLVED:
            existing.status = Exposure.STATUS_NEW
            existing.resolved_at = None
        existing.save(update_fields=["last_seen", "times_seen", "status", "resolved_at"])
        return False

    Exposure.objects.create(
        profile=profile,
        first_run=run,
        fingerprint=fp,
        repo_full_name=repo_full_name,
        file_path=file_path,
        url=url,
        source=WatchRun.SOURCE_CODE_SEARCH,
        detector=finding.detector,
        detector_label=finding.detector_label,
        severity=severity,
        matched_keyword=finding.matched_keyword,
        redacted_snippet=finding.redacted[:500],
        note=note[:400],
        first_seen=now,
        last_seen=now,
    )
    return True


def run_scan(
    profile: WatchProfile,
    *,
    triggered_by=None,
    max_queries: int | None = None,
) -> WatchRun:
    """Execute a point-in-time exposure check for one profile."""
    from django.conf import settings

    if max_queries is None:
        max_queries = int(getattr(settings, "AEGIS_MAX_QUERIES", DEFAULT_MAX_QUERIES))

    run = WatchRun.objects.create(
        profile=profile,
        source=WatchRun.SOURCE_CODE_SEARCH,
        triggered_by=triggered_by,
    )

    try:
        queries, skipped = build_queries(profile, max_queries=max_queries)
        run.queries_skipped = skipped

        if not queries:
            run.append_log(
                "Nothing to search — add a GitHub org/repo, or add keywords and "
                "tick 'search globally'."
            )
            run.status = WatchRun.STATUS_OK
            run.finished_at = timezone.now()
            run.save()
            return run

        if skipped:
            run.append_log(
                f"NOTE: query cap {max_queries} reached — {skipped} lower-priority "
                f"queries were not run. Raise AEGIS_MAX_QUERIES for full coverage."
            )

        token = code_search.resolve_token(profile)
        client = code_search.CodeSearchClient(token)
        keywords = profile.keyword_list

        seen_files: set[tuple[str, str]] = set()
        new_count = 0
        repeat_count = 0
        denied_repos: set[str] = set()

        for query in queries:
            try:
                items = client.search(query)
            except code_search.RateLimited as exc:
                run.append_log(f"STOPPED at '{query}': {exc}")
                run.append_log(
                    f"Coverage incomplete — {len(queries) - queries.index(query)} queries not run."
                )
                break
            except code_search.CodeSearchError as exc:
                run.append_log(f"SKIP '{query}': {exc}")
                continue

            run.queries_run += 1
            run.append_log(f"{query} -> {len(items)} file(s)")

            for item in items:
                repo_full_name = (item.get("repository") or {}).get("full_name", "")
                file_path = item.get("path", "")
                url = item.get("html_url", "")

                # Crawler/dataset repos mention every domain that exists; one of
                # them can bury a genuine finding under hundreds of rows.
                if profile.is_denied(repo_full_name):
                    denied_repos.add(repo_full_name)
                    continue

                key = (repo_full_name, file_path)
                if key not in seen_files:
                    seen_files.add(key)

                text = code_search.fragments_from_item(item)
                if not text:
                    continue

                for finding in detect.scan_text(text, keywords):
                    if _record_finding(
                        profile, run, finding,
                        repo_full_name=repo_full_name, file_path=file_path, url=url,
                    ):
                        new_count += 1
                    else:
                        repeat_count += 1

        if denied_repos:
            run.append_log(
                f"Denylist filtered {len(denied_repos)} repo(s): "
                f"{', '.join(sorted(denied_repos)[:10])}"
                f"{' …' if len(denied_repos) > 10 else ''}"
            )

        run.files_examined = len(seen_files)
        run.findings_new = new_count
        run.findings_seen = repeat_count
        run.status = WatchRun.STATUS_OK
        run.append_log(
            f"Done: {run.queries_run} queries, {run.files_examined} files, "
            f"{new_count} new / {repeat_count} repeat findings."
        )

    except Exception as exc:  # noqa: BLE001 - the run record is the error report
        run.status = WatchRun.STATUS_FAILED
        run.append_log(f"FAILED: {exc}\n{traceback.format_exc()}")

    run.finished_at = timezone.now()
    run.save()
    return run
