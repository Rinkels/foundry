"""Aegis detectors — what counts as an exposure, and how it's recorded.

Two hard rules, both about liability:

1. **A raw secret is never returned or persisted.** Every Finding carries a
   redacted preview plus a fingerprint derived from the value's hash. If the
   Aegis database leaks, it leaks nothing usable.
2. **Nothing here calls out to a third party to "verify" a key.** Validating a
   credential found in a stranger's repo means authenticating as them. That is
   a decision for the tenant contract, not for a scanner.

The detector set is deliberately weighted toward the Lovable/Supabase stack,
because that's the Iris migration funnel: those apps ship their Supabase
project URL and keys in client-side code, and the difference between an `anon`
key and a `service_role` key is the difference between "working as designed"
and "the entire database is readable by anyone."

Each detector carries `search_terms` — literal strings GitHub code search can
actually index. Regex is the confirmation step, not the search step: GitHub's
search API has no regex support, so we narrow with literals and confirm here.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Callable

# Severity constants mirror Exposure.SEV_* (kept as plain strings so this
# module stays importable without Django loaded).
CRITICAL = "critical"
HIGH = "high"
MEDIUM = "medium"
LOW = "low"
INFO = "info"


# --------------------------------------------------------------------------- #
# Redaction + fingerprinting
# --------------------------------------------------------------------------- #

def redact(value: str, keep: int = 4) -> str:
    """Mask a secret, keeping enough for a human to recognise which key it is."""
    value = (value or "").strip()
    if len(value) <= keep * 2 + 4:
        return "*" * len(value)
    return f"{value[:keep]}…{'*' * 8}…{value[-keep:]} ({len(value)} chars)"


def value_hash(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8", "replace")).hexdigest()


def fingerprint(repo: str, path: str, detector_key: str, value: str) -> str:
    """Stable identity for a finding.

    Includes the value hash so that rotating a key in place opens a *new*
    finding rather than silently reviving the old one.
    """
    raw = "\x00".join([repo or "", path or "", detector_key or "", value_hash(value)])
    return hashlib.sha256(raw.encode()).hexdigest()


# --------------------------------------------------------------------------- #
# Detector definitions
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Detector:
    key: str
    label: str
    severity: str
    pattern: re.Pattern
    search_terms: tuple[str, ...] = ()
    note: str = ""
    # Optional second pass: (matched_text) -> (severity, note) or None to drop.
    refine: Callable[[str], tuple[str, str] | None] | None = None
    # Which capture group holds the actual credential. Placeholder detection
    # runs against this group only — without it, a real password inside
    # `postgres://u:pw@db.example.com/x` gets discarded because the *hostname*
    # happens to contain "example".
    secret_group: int = 0


@dataclass
class Finding:
    detector: str
    detector_label: str
    severity: str
    redacted: str
    fingerprint_value: str  # the raw value, used ONLY to compute a fingerprint
    note: str = ""
    matched_keyword: str = ""


def _refine_supabase_jwt(matched: str) -> tuple[str, str] | None:
    """Decode a Supabase JWT payload to read its `role` claim.

    `service_role` bypasses row-level security entirely — in a public repo it is
    a full database compromise, not a misconfiguration. `anon` is meant to be
    public, but only if RLS is actually on, so it stays a medium.
    """
    parts = matched.split(".")
    if len(parts) < 2:
        return HIGH, "Malformed JWT — could not read role claim."
    payload_b64 = parts[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8", "replace"))
    except (ValueError, binascii.Error, UnicodeDecodeError):
        return HIGH, "JWT payload not decodable — treat as unknown-scope key."

    role = str(payload.get("role", "")).lower()
    ref = str(payload.get("ref", ""))
    where = f" (project {ref})" if ref else ""

    if role == "service_role":
        return CRITICAL, (
            f"Supabase service_role key{where}. Bypasses row-level security — "
            "grants full read/write to the database. Rotate immediately."
        )
    if role == "anon":
        return MEDIUM, (
            f"Supabase anon key{where}. Public by design, but only safe if RLS is "
            "enabled on every table — verify before dismissing."
        )
    return HIGH, f"Supabase JWT with role '{role or 'unknown'}'{where}."


DETECTORS: list[Detector] = [
    Detector(
        key="supabase_jwt",
        label="Supabase API key (JWT)",
        severity=HIGH,
        # Supabase keys are HS256 JWTs; the header segment is near-constant.
        pattern=re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"),
        search_terms=("supabase_anon_key", "service_role", "supabase.co"),
        refine=_refine_supabase_jwt,
    ),
    Detector(
        key="supabase_project_url",
        label="Supabase project URL",
        severity=LOW,
        pattern=re.compile(r"https://[a-z0-9]{16,24}\.supabase\.co"),
        search_terms=("supabase.co",),
        note="Identifies the backing project — pair with any leaked key to assess blast radius.",
    ),
    Detector(
        key="gcp_service_account",
        label="GCP service account key",
        severity=CRITICAL,
        pattern=re.compile(r'"type"\s*:\s*"service_account"'),
        search_terms=("service_account private_key", "-----BEGIN PRIVATE KEY-----"),
        note="A service-account JSON in a public repo grants whatever roles it holds. Revoke the key.",
    ),
    Detector(
        key="private_key_block",
        label="Private key block",
        severity=CRITICAL,
        # The PEM header alone is not a leak — it's the placeholder text in every
        # "paste your key here" form on the internet. Require actual key material
        # after it. Handles real newlines and JSON-escaped \n alike.
        pattern=re.compile(
            r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"
            r"(?:\\+[nr]|[\s\"'])+"
            r"[A-Za-z0-9+/=]{40,}"
        ),
        search_terms=("BEGIN RSA PRIVATE KEY", "BEGIN OPENSSH PRIVATE KEY"),
    ),
    Detector(
        key="aws_access_key",
        label="AWS access key ID",
        severity=CRITICAL,
        pattern=re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
        search_terms=("AKIA",),
    ),
    Detector(
        key="google_api_key",
        label="Google API key",
        severity=HIGH,
        pattern=re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
        search_terms=("AIzaSy",),
    ),
    Detector(
        key="openai_key",
        label="OpenAI API key",
        severity=CRITICAL,
        pattern=re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{20,}\b"),
        search_terms=("sk-proj-",),
    ),
    Detector(
        key="anthropic_key",
        label="Anthropic API key",
        severity=CRITICAL,
        pattern=re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b"),
        search_terms=("sk-ant-",),
    ),
    Detector(
        key="stripe_live_key",
        label="Stripe live secret key",
        severity=CRITICAL,
        pattern=re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{20,}\b"),
        search_terms=("sk_live_",),
    ),
    Detector(
        key="github_token",
        label="GitHub token",
        severity=CRITICAL,
        pattern=re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}\b"),
        search_terms=("ghp_", "github_pat_"),
    ),
    Detector(
        key="postgres_url_with_password",
        label="Database URL with password",
        severity=CRITICAL,
        pattern=re.compile(r"\b(?:postgres|postgresql|mysql|mongodb(?:\+srv)?)://[^\s:@/]+:([^\s:@/]+)@[^\s/]+"),
        search_terms=("postgresql://", "mongodb+srv://"),
        note="Connection string includes credentials.",
        secret_group=1,
    ),
    Detector(
        key="slack_webhook",
        label="Slack webhook URL",
        severity=MEDIUM,
        pattern=re.compile(r"https://hooks\.slack\.com/services/T[A-Za-z0-9_/]{20,}"),
        search_terms=("hooks.slack.com/services",),
    ),
]

DETECTORS_BY_KEY = {d.key: d for d in DETECTORS}

# False-positive guards: values that structurally match but are obviously
# placeholders. Cheap, and they matter a lot for a report we hand to a customer.
_PLACEHOLDER_RE = re.compile(
    r"(?i)("
    r"your[_-]?(key|token|secret|password|api)"   # YOUR-PASSWORD, your_api_key
    r"|example|placeholder|xxxx+|changeme|dummy|sample|todo|\bfake\b|000000|\.\.\."
    r"|<[^>]*>"                                    # <your-key>
    r"|\[[^\]]*\]"                                 # [YOUR-PASSWORD]  (docs style)
    r"|\{\{?[^}]*\}\}?"                            # {{ secret }} / ${VAR}
    r"|\$[A-Z_]{2,}"                               # $POSTGRES_PASSWORD
    r"|%[A-Z_]{2,}%"                               # %DB_PASS%
    r")"
)

# Values that are structurally valid but universally understood as dummies.
# Compared whole-string, so a real password merely *containing* "test" survives.
_DUMMY_VALUES = frozenset({
    "password", "passwd", "pass", "secret", "postgres", "postgresql", "mysql",
    "root", "admin", "test", "testing", "user", "username", "db", "database",
    "mysecretpassword", "your-password", "yourpassword", "your_password",
    "changeme", "letmein", "12345", "123456", "abc123", "foo", "bar", "baz",
})


def _is_placeholder(value: str) -> bool:
    value = (value or "").strip()
    if value.lower() in _DUMMY_VALUES:
        return True
    return bool(_PLACEHOLDER_RE.search(value))


# --------------------------------------------------------------------------- #
# Scanning
# --------------------------------------------------------------------------- #

def scan_text(text: str, keywords: list[str] | None = None) -> list[Finding]:
    """Run every detector (plus tenant keywords) over one blob of text.

    Returns at most one Finding per (detector, distinct value) so a key repeated
    across a file doesn't inflate the report.
    """
    findings: list[Finding] = []
    if not text:
        return findings

    seen: set[tuple[str, str]] = set()

    for det in DETECTORS:
        for match in det.pattern.finditer(text):
            value = match.group(0)
            # Placeholder-check the credential itself, not surrounding context.
            candidate = match.group(det.secret_group) if det.secret_group else value
            if _is_placeholder(candidate or value):
                continue
            dedupe = (det.key, value_hash(value))
            if dedupe in seen:
                continue
            seen.add(dedupe)

            severity, note = det.severity, det.note
            if det.refine:
                refined = det.refine(value)
                if refined is None:
                    continue
                severity, note = refined

            findings.append(
                Finding(
                    detector=det.key,
                    detector_label=det.label,
                    severity=severity,
                    redacted=redact(value),
                    fingerprint_value=value,
                    note=note,
                )
            )

    for kw in keywords or []:
        if not kw:
            continue
        if re.search(re.escape(kw), text, re.IGNORECASE):
            dedupe = ("keyword", kw.lower())
            if dedupe in seen:
                continue
            seen.add(dedupe)
            findings.append(
                Finding(
                    detector="tenant_keyword",
                    detector_label="Tenant keyword mention",
                    severity=INFO,
                    redacted=kw,
                    fingerprint_value=kw.lower(),
                    note="Public mention of a tracked term.",
                    matched_keyword=kw,
                )
            )

    return findings


# Paths where a credential-shaped string is overwhelmingly likely to be an
# illustration rather than a live secret.
_DOC_DIR_RE = re.compile(
    r"(?i)(^|/)(docs?|examples?|samples?|demos?|fixtures?|tests?|__tests__|spec|"
    r"snippets?|templates?)(/|$)"
)
_DOC_FILE_RE = re.compile(
    r"(?i)("
    r"\.(md|mdx|rst)$"
    r"|(^|/)(readme|changelog|contributing)[^/]*$"
    r"|\.(example|sample|template|dist)$"
    r"|\.(test|spec)\.[jt]sx?$"          # session-replay.test.ts
    r"|(^|/)test_[^/]+\.py$|_test\.(py|go|rb)$"
    r")"
)


def is_documentation_path(file_path: str) -> bool:
    path = (file_path or "").strip()
    return bool(_DOC_DIR_RE.search(path) or _DOC_FILE_RE.search(path))


# Down-ranking is one step short of suppression: a real key pasted into a
# README *is* a leak, so it stays in the report — just not in the "rotate now"
# tier that the customer reads first.
_DOWNRANK = {CRITICAL: LOW, HIGH: LOW, MEDIUM: INFO, LOW: INFO, INFO: INFO}
_DOC_NOTE = "Found in a docs/example path — likely illustrative. Confirm before acting."


def adjust_for_path(severity: str, file_path: str) -> tuple[str, str]:
    """Return (severity, extra_note) after accounting for where the hit lives."""
    if is_documentation_path(file_path):
        return _DOWNRANK.get(severity, severity), _DOC_NOTE
    return severity, ""


def search_terms_for(keywords: list[str] | None = None) -> list[str]:
    """Every literal term worth issuing as a GitHub code-search query.

    Ordered most-valuable-first so that a run truncated by the query cap still
    covers the findings that matter.
    """
    terms: list[str] = []
    for det in sorted(DETECTORS, key=lambda d: {CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3}.get(d.severity, 4)):
        for term in det.search_terms:
            if term not in terms:
                terms.append(term)
    for kw in keywords or []:
        if kw and kw not in terms:
            terms.append(kw)
    return terms
