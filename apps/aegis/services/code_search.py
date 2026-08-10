"""GitHub code search, throttled to the `code_search` rate-limit bucket.

Code search is its own bucket and it is *tight* — roughly 10 requests/minute,
against 5,000/hour for the core REST API. Everything here is built around that
constraint: pace requests, respect the reset header, and never burn a request
on a query we can't use.

Only the REST API is used. Scraping github.com/search is against GitHub's terms
of service; the API is explicitly fine within its limits.
"""
from __future__ import annotations

import time

import httpx
from django.conf import settings

from apps.atlas.services import github as atlas_github

GITHUB_API = "https://api.github.com"

# Text-match media type gives us the matching fragments, so we can run the
# detector regexes without fetching (and rate-limiting on) whole file contents.
_HEADERS = {
    "Accept": "application/vnd.github.text-match+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# Code search allows ~10 req/min. 7s spacing leaves headroom for clock skew.
DEFAULT_MIN_INTERVAL = 7.0
MAX_PER_PAGE = 100


class CodeSearchError(RuntimeError):
    """Raised for a non-recoverable search failure (bad auth, bad query)."""


class RateLimited(RuntimeError):
    """Raised when GitHub asks us to back off for longer than we'll wait."""


def resolve_token(profile=None) -> str:
    """Prefer the tenant's own GitHub App installation; fall back to a PAT.

    Using the installation token matters for multi-tenancy: each customer's
    searches then draw on their own rate-limit allowance rather than ours.
    """
    if profile is not None and getattr(profile, "github_installation_id", None):
        try:
            return atlas_github.installation_token(profile.github_installation.installation_id)
        except Exception as exc:  # noqa: BLE001 - fall through to the PAT
            if not getattr(settings, "AEGIS_GITHUB_TOKEN", ""):
                raise CodeSearchError(
                    f"Installation token failed and no AEGIS_GITHUB_TOKEN set: {exc}"
                ) from exc

    token = getattr(settings, "AEGIS_GITHUB_TOKEN", "") or getattr(settings, "GITHUB_TOKEN", "")
    if not token:
        raise CodeSearchError(
            "No GitHub credentials. Set AEGIS_GITHUB_TOKEN, or attach a "
            "GitHubInstallation to the watch profile."
        )
    return token


class CodeSearchClient:
    """Paced client for /search/code.

    Usage:
        client = CodeSearchClient(token)
        for item in client.search('AKIA org:acme'):
            ...
    """

    def __init__(self, token: str, *, min_interval: float | None = None, timeout: float = 30.0):
        self.token = token
        self.min_interval = (
            min_interval
            if min_interval is not None
            else float(getattr(settings, "AEGIS_SEARCH_MIN_INTERVAL", DEFAULT_MIN_INTERVAL))
        )
        self.timeout = timeout
        self._last_call = 0.0
        self.requests_made = 0

    # -- pacing -------------------------------------------------------------
    def _wait_turn(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if self._last_call and elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call = time.monotonic()

    def _handle_rate_limit(self, resp: httpx.Response) -> float | None:
        """Return seconds to sleep, or None if this isn't a rate-limit response."""
        if resp.status_code not in (403, 429):
            return None
        retry_after = resp.headers.get("retry-after")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass
        if resp.headers.get("x-ratelimit-remaining") == "0":
            reset = resp.headers.get("x-ratelimit-reset")
            if reset:
                try:
                    return max(0.0, float(reset) - time.time()) + 1.0
                except ValueError:
                    pass
        # Secondary rate limit with no hint — back off a fixed amount.
        if "secondary rate limit" in resp.text.lower():
            return 60.0
        return None

    # -- requests -----------------------------------------------------------
    def _get(self, params: dict, *, attempt: int = 0) -> dict:
        self._wait_turn()
        resp = httpx.get(
            f"{GITHUB_API}/search/code",
            params=params,
            headers={**_HEADERS, "Authorization": f"Bearer {self.token}"},
            timeout=self.timeout,
        )
        self.requests_made += 1

        backoff = self._handle_rate_limit(resp)
        if backoff is not None:
            max_wait = float(getattr(settings, "AEGIS_MAX_BACKOFF", 120))
            if backoff > max_wait or attempt >= 2:
                raise RateLimited(
                    f"GitHub asked for a {backoff:.0f}s backoff (limit {max_wait:.0f}s)."
                )
            time.sleep(backoff)
            return self._get(params, attempt=attempt + 1)

        if resp.status_code == 422:
            # Unprocessable query — usually a term GitHub refuses to index.
            raise CodeSearchError(f"Query rejected: {params.get('q')}")
        if resp.status_code == 401:
            raise CodeSearchError("GitHub rejected the credentials (401).")
        resp.raise_for_status()
        return resp.json()

    def search(self, query: str, *, max_pages: int = 1, per_page: int = MAX_PER_PAGE) -> list[dict]:
        """Run one code-search query, returning raw result items.

        Defaults to a single page: with a 10 req/min budget, breadth across
        queries beats depth within one. GitHub caps any query at 1,000 results
        regardless.
        """
        items: list[dict] = []
        for page in range(1, max_pages + 1):
            data = self._get({"q": query, "per_page": min(per_page, MAX_PER_PAGE), "page": page})
            batch = data.get("items", [])
            items.extend(batch)
            if len(batch) < per_page or len(items) >= data.get("total_count", 0):
                break
        return items


def fragments_from_item(item: dict) -> str:
    """Concatenate the text-match fragments GitHub returned for a hit.

    These are the few lines around each match, which is exactly what the
    detectors need — and avoids a second rate-limited call per file.
    """
    parts = []
    for tm in item.get("text_matches") or []:
        frag = tm.get("fragment")
        if frag:
            parts.append(frag)
    return "\n".join(parts)
