"""Public-footprint posture for a watched organisation.

Separate from exposure scanning on purpose. A credential leak is an incident;
a footprint is a governance question — how many repositories are public, how
many were abandoned years ago, how many are forks nobody reviews. Customers
with a perfectly clean credential report still have work to do here, and it's
the part of the report that survives the "we already run secret scanning"
objection.

Runs against the `core` REST bucket (5,000/hr), not `code_search` (10/min), so
it is effectively free compared to a sweep.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone as dt_timezone

import httpx
from django.utils import timezone

from . import code_search

GITHUB_API = "https://api.github.com"
_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

STALE_YEARS = 5


def _age_years(timestamp: str, now: datetime) -> float:
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return (now - parsed).days / 365.25


def fetch_org_repos(org: str, token: str, *, max_pages: int = 10) -> list[dict]:
    repos: list[dict] = []
    for page in range(1, max_pages + 1):
        resp = httpx.get(
            f"{GITHUB_API}/orgs/{org}/repos",
            params={"per_page": 100, "page": page},
            headers={**_HEADERS, "Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if resp.status_code == 404:
            # Might be a user account rather than an org.
            resp = httpx.get(
                f"{GITHUB_API}/users/{org}/repos",
                params={"per_page": 100, "page": page},
                headers={**_HEADERS, "Authorization": f"Bearer {token}"},
                timeout=30,
            )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
    return repos


def summarise(repos: list[dict], *, prefixes: list[str] | None = None) -> dict:
    """Turn a repo list into the handful of numbers worth putting in a report."""
    now = datetime.now(dt_timezone.utc)
    prefixes = [p.lower() for p in (prefixes or [])]

    stale = [r for r in repos if _age_years(r["pushed_at"], now) >= STALE_YEARS]
    archived = [r for r in repos if r.get("archived")]
    forks = [r for r in repos if r.get("fork")]

    # Public but not archived and not touched in years: the "no evident owner"
    # bucket, which is the number that actually prompts a decision.
    unowned = [r for r in stale if not r.get("archived")]

    prefixed = [
        r for r in repos
        if any(r["name"].lower().startswith(p) for p in prefixes)
    ] if prefixes else []

    langs = Counter(r["language"] for r in repos if r.get("language"))

    return {
        "total": len(repos),
        "archived": len(archived),
        "forks": len(forks),
        "stale": len(stale),
        "unowned": len(unowned),
        "stale_years": STALE_YEARS,
        "languages": dict(langs.most_common(6)),
        "top_language": langs.most_common(1)[0][0] if langs else "",
        "top_language_count": langs.most_common(1)[0][1] if langs else 0,
        "prefixed": [
            {
                "name": r["name"],
                "pushed_at": r["pushed_at"][:10],
                "archived": bool(r.get("archived")),
            }
            for r in sorted(prefixed, key=lambda x: x["name"])
        ],
        # Archived repos are excluded: the owner has already made a decision about
        # them, so citing one as evidence of neglect in a customer report is unfair.
        "oldest": [
            {"name": r["name"], "pushed_at": r["pushed_at"][:10]}
            for r in sorted(
                (r for r in repos if not r.get("archived")),
                key=lambda x: x["pushed_at"],
            )[:6]
        ],
    }


def collect(profile) -> dict:
    """Collect and persist posture for every org on the profile.

    Prefixes for the "internal-looking libraries" list are derived from the
    profile's own keywords (e.g. keyword `ama_layout` -> prefix `ama_`), so
    this stays tenant-agnostic instead of hardcoding one customer's convention.
    """
    orgs = profile.org_list
    if not orgs:
        return {}

    prefixes = sorted({
        kw.split("_")[0] + "_"
        for kw in profile.keyword_list
        if "_" in kw and not kw.startswith("_")
    })

    token = code_search.resolve_token(profile)
    combined: dict = {"orgs": {}, "prefixes": prefixes}

    for org in orgs:
        try:
            repos = fetch_org_repos(org, token)
        except httpx.HTTPError as exc:
            combined["orgs"][org] = {"error": str(exc)}
            continue
        combined["orgs"][org] = summarise(repos, prefixes=prefixes)

    profile.posture = combined
    profile.posture_updated_at = timezone.now()
    profile.save(update_fields=["posture", "posture_updated_at"])
    return combined
