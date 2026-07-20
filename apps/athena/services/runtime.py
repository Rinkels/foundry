# apps/athena/services/runtime.py
"""Usage
from apps.athena.services.runtime import athena_prompt
prompt = athena_prompt("janus_gate_summary", ctx={"idea": idea_text, "evidence": evidence_blob})
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from django.core.cache import cache
from django.db import transaction

from apps.athena.models import PromptTemplate, PromptVersion, PromptStatus
from apps.athena.services.prompt_engine import render_prompt


@dataclass(frozen=True)
class AthenaPromptResult:
    ok: bool
    key: str
    version: int
    rendered: str
    error: str = ""


CACHE_TTL_SECONDS = 60  # keep short; prompts change during development


def _cache_key(key: str, approved_only: bool) -> str:
    return f"athena:prompt:{key}:approved={int(approved_only)}"


def get_canonical_version(template: PromptTemplate, approved_only: bool = True) -> Optional[PromptVersion]:
    """
    Returns:
      - template.approved_version if approved_only
      - template.current_version otherwise
    Falls back to newest version if those aren’t set.
    """
    qs = template.versions.all().order_by("-version")
    if approved_only:
        v = getattr(template, "approved_version", None)
        if v:
            return v
        # If you store an approved flag in PromptVersion, filter here.
    v = getattr(template, "current_version", None)
    if v:
        return v
    return qs.first()


def get_template_by_role(role: str) -> Optional[PromptTemplate]:
    """
    Return the template assigned to a Studio pipeline role (feature_designer,
    app_builder, impl_generator), or None. Replaces the old fuzzy key/name
    matching. If several share a role, the lowest-id (oldest) one wins.
    """
    return PromptTemplate.objects.filter(role=role).order_by("id").first()


def get_prompt_by_key(key: str, approved_only: bool = True) -> tuple[PromptTemplate, PromptVersion]:
    ck = _cache_key(key, approved_only)
    cached = cache.get(ck)
    if cached:
        return cached["template"], cached["version"]

    template = PromptTemplate.objects.get(key=key)
    version = get_canonical_version(template, approved_only=approved_only)
    if not version:
        raise PromptVersion.DoesNotExist(f"No canonical version found for '{key}' (approved_only={approved_only}).")

    cache.set(ck, {"template": template, "version": version}, CACHE_TTL_SECONDS)
    return template, version


def athena_render(key: str, ctx: dict[str, Any], *, approved_only: bool = True) -> AthenaPromptResult:
    template, version = get_prompt_by_key(key, approved_only=approved_only)
    rr = render_prompt(version.body, ctx or {})
    if not rr.ok:
        return AthenaPromptResult(ok=False, key=key, version=version.version, rendered="", error=rr.error)
    return AthenaPromptResult(ok=True, key=key, version=version.version, rendered=rr.rendered)


def athena_prompt(key: str, ctx: dict[str, Any], *, approved_only: bool = True) -> str:
    """
    Convenience function used by other modules.
    Raises ValueError if render fails.
    """
    res = athena_render(key, ctx, approved_only=approved_only)
    if not res.ok:
        raise ValueError(f"Athena render failed for '{key}' v{res.version}: {res.error}")
    return res.rendered


@transaction.atomic
def approve_current_version(key: str) -> PromptTemplate:
    """
    Approve the template's current version.
    Sets template.status=approved and template.approved_version=current_version.
    """
    template = PromptTemplate.objects.select_for_update().get(key=key)
    version = template.current_version or template.versions.order_by("-version").first()
    if not version:
        raise PromptVersion.DoesNotExist(f"Cannot approve '{key}': no versions exist.")

    template.approved_version = version
    template.status = PromptStatus.APPROVED
    template.save(update_fields=["approved_version", "status", "updated_at"])

    # bust cache
    cache.delete(_cache_key(key, True))
    cache.delete(_cache_key(key, False))
    return template
