"""GitHub App integration for Atlas.

Handles the three things a GitHub App webhook flow needs:

1. Verifying inbound webhook signatures (HMAC-SHA256 with the webhook secret).
2. Minting a short-lived App JWT (RS256, signed with the App private key).
3. Exchanging that JWT for a per-installation access token, used to clone
   private repos.

Implemented with `cryptography` + `httpx` (both already installed) so we
don't pull in PyJWT just for one RS256 signature.

Required config (settings / .env):
    GITHUB_APP_ID                 numeric App ID
    GITHUB_APP_PRIVATE_KEY_PATH   path to the App's .pem private key
    GITHUB_WEBHOOK_SECRET         the webhook secret configured on the App
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from pathlib import Path

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings

GITHUB_API = "https://api.github.com"
_API_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


class GitHubNotConfigured(RuntimeError):
    """Raised when GitHub App credentials are missing."""


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


# --------------------------------------------------------------------------- #
# Webhook signature verification
# --------------------------------------------------------------------------- #

def verify_signature(payload_bytes: bytes, signature_header: str | None) -> bool:
    """Constant-time check of the X-Hub-Signature-256 header."""
    secret = getattr(settings, "GITHUB_WEBHOOK_SECRET", "")
    if not secret or not signature_header:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


# --------------------------------------------------------------------------- #
# App JWT + installation tokens
# --------------------------------------------------------------------------- #

def _load_private_key():
    path = getattr(settings, "GITHUB_APP_PRIVATE_KEY_PATH", "")
    if not path:
        raise GitHubNotConfigured("GITHUB_APP_PRIVATE_KEY_PATH is not set.")
    pem = Path(path).read_bytes()
    return serialization.load_pem_private_key(pem, password=None)


def app_jwt() -> str:
    """Build a ~9-minute App JWT signed with the App private key (RS256)."""
    app_id = getattr(settings, "GITHUB_APP_ID", "")
    if not app_id:
        raise GitHubNotConfigured("GITHUB_APP_ID is not set.")

    key = _load_private_key()
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    payload = {"iat": now - 60, "exp": now + 540, "iss": str(app_id)}

    signing_input = f"{_b64url(json.dumps(header).encode())}.{_b64url(json.dumps(payload).encode())}"
    signature = key.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
    return f"{signing_input}.{_b64url(signature)}"


def installation_token(installation_id: int) -> str:
    """Exchange the App JWT for a short-lived installation access token."""
    headers = {**_API_HEADERS, "Authorization": f"Bearer {app_jwt()}"}
    resp = httpx.post(
        f"{GITHUB_API}/app/installations/{installation_id}/access_tokens",
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def authed_clone_url(repo_full_name: str, token: str) -> str:
    """Build an https clone URL that carries an installation token."""
    return f"https://x-access-token:{token}@github.com/{repo_full_name}.git"


def is_configured() -> bool:
    return bool(
        getattr(settings, "GITHUB_APP_ID", "")
        and getattr(settings, "GITHUB_APP_PRIVATE_KEY_PATH", "")
        and getattr(settings, "GITHUB_WEBHOOK_SECRET", "")
    )
