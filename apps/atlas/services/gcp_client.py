"""Thin wrappers around the Google Cloud SDKs used by Atlas.

The `google-cloud-*` packages are optional dependencies — they're only
imported when a client is actually requested, so the rest of the app
(and `manage.py check`) keeps working on machines where they aren't
installed yet.

Install what you need, e.g.:
    pip install google-cloud-run google-cloud-sql-connector google-cloud-secret-manager google-cloud-storage
"""
from __future__ import annotations

import os
from functools import lru_cache


class GcpNotConfigured(RuntimeError):
    """Raised when a GCP client is requested but credentials/SDKs aren't available."""


def get_project_id() -> str:
    project_id = os.environ.get("GCP_PROJECT_ID", "")
    if not project_id:
        raise GcpNotConfigured("GCP_PROJECT_ID is not set in the environment/.env")
    return project_id


@lru_cache(maxsize=1)
def run_client():
    """Cloud Run Admin API client (google.cloud.run_v2.ServicesClient)."""
    try:
        from google.cloud import run_v2
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise GcpNotConfigured("google-cloud-run is not installed") from exc
    return run_v2.ServicesClient()


@lru_cache(maxsize=1)
def sql_admin_client():
    """Cloud SQL Admin API client (googleapiclient discovery)."""
    try:
        from googleapiclient import discovery
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise GcpNotConfigured("google-api-python-client is not installed") from exc
    return discovery.build("sqladmin", "v1")


@lru_cache(maxsize=1)
def secret_manager_client():
    """Secret Manager client (google.cloud.secretmanager)."""
    try:
        from google.cloud import secretmanager
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise GcpNotConfigured("google-cloud-secret-manager is not installed") from exc
    return secretmanager.SecretManagerServiceClient()


@lru_cache(maxsize=1)
def storage_client():
    """Cloud Storage client (google.cloud.storage)."""
    try:
        from google.cloud import storage
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise GcpNotConfigured("google-cloud-storage is not installed") from exc
    return storage.Client()
