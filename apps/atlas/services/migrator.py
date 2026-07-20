"""Migration helpers for bringing externally-built apps under Atlas management.

Initial target: projects exported/cloned from Loveable.com (typically a
Vite/React frontend, sometimes with a Supabase backend) that need to be
re-platformed onto the "Adorable Architecture" (Django app server on Cloud
Run, Cloud SQL for Postgres, GCP Secret Manager, etc.).

This is intentionally a thin skeleton: `register_external_project` just
creates the tracking record so it shows up in the Atlas dashboard and can
move through the normal provisioning/deploy flow. The actual source-code
transformation steps (e.g. swapping a Supabase client for Django REST
endpoints) are project-specific and should be added incrementally.
"""
from __future__ import annotations

from django.utils.text import slugify

from ..models import CloudProject


def register_external_project(
    *,
    name: str,
    origin: str = "loveable",
    source_path: str = "",
    repo_url: str = "",
    notes: str = "",
) -> CloudProject:
    """Create (or fetch) a CloudProject tracking record for an externally-built app."""
    slug = slugify(name)
    project, _ = CloudProject.objects.get_or_create(
        slug=slug,
        defaults={
            "name": name,
            "origin": origin,
            "source_path": source_path,
            "repo_url": repo_url,
            "notes": notes,
            "status": "planning",
        },
    )
    return project
