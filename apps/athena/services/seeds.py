# apps/athena/services/seeds.py
"""
Canonical default prompts that ship with Athena.

These used to live as hardcoded string constants inside views.py, which meant
the prompt manager's own prompts were invisible to the prompt manager. They now
live here as data and are materialised into real PromptTemplate/PromptVersion
rows via `ensure_default_prompts` (called from a data migration and, defensively,
from the Studio view that exposes the implementation generator).

`ensure_default_prompts` is written to work with BOTH the real models and the
historical models passed in from a migration: it only uses generic ORM
operations and always sets `auto_compose=False` + an explicit `body`, so it does
not depend on PromptVersion's custom save().
"""
from __future__ import annotations


IMPLEMENTATION_GENERATOR_BODY = """# Goal
Generate a production-quality implementation plan (and code patches when explicitly requested) to extend an existing application with new functionality, while preserving backward compatibility and long-term maintainability.

# Context
You are working inside an existing codebase. The current system already has users, data, and workflows in production.

Treat the following as authoritative context about the application:

{{ app_description }}

# Approved Design (authoritative)
This section contains the approved feature or architecture design produced earlier.
Treat it as the source of truth for *what* must be built.

{{ design_doc }}

# Instructions
You are a senior software engineer with strong Django architecture experience.

Your task is to translate the approved design into an implementation plan that:
- Is additive and backward-compatible
- Fits naturally into the existing app structure
- Is easy to extend, test, and reason about

## 1. Implementation Plan (always required)
Produce a clear, step-by-step implementation plan that includes:
- Files to create or modify
- New or updated models and relationships
- Migrations (including defaults and data backfills if needed)
- Admin changes
- Views, URLs, templates, APIs, or background jobs
- Services or domain logic modules
- Permission, visibility, and publication considerations
- Rollout and deployment considerations

## 2. Code Generation (only when explicitly requested)
Only output code if the user explicitly asks for it.

When generating code:
- Group code blocks by file path
- Use one code block per file
- Assume the existing project structure and naming conventions
- Do not repeat unchanged code

## 3. Backward Compatibility Rules
- Do not remove or rename existing models, fields, or endpoints
- If introducing a replacement concept, provide safe defaults or fallbacks
- Ensure existing workflows continue to function unchanged

## 4. Maintainability Rules
- Keep business logic out of views and templates
- Prefer services or domain modules for complex logic
- Avoid tight coupling between unrelated concerns
- Prefer explicit, boring designs over clever abstractions

## 5. Data Safety
- Migrations must be safe for large datasets
- Defaults must be sensible
- Any destructive change must be opt-in and clearly documented

# User Request
{{ user_message }}

# Output Contract
Return Markdown with **exactly** the following sections, in this order:

## Patch Plan
## New / Updated Models
## Migrations
## Admin Changes
## Views / URLs / Templates
## Services / Domain Logic
## Data Backfill (if applicable)
## Tests
## Rollout Notes
## Open Questions

# Guardrails
- Do not invent models, fields, or APIs not implied by the app context or approved design
- If `design_doc` is missing or empty, respond with:
  "Missing design_doc. Please provide the approved design before implementation."
- If key decisions are ambiguous, list them in **Open Questions** instead of guessing
"""


# Each spec is materialised into one PromptTemplate + one approved v1 PromptVersion.
DEFAULT_PROMPTS = [
    {
        "key": "athena-impl-generator",
        "name": "Implementation Generator",
        "role": "impl_generator",
        "consumer": "general",
        "description": "Canonical implementation-plan generator used by Studio.",
        "tags": "implementation,generator,athena",
        "body": IMPLEMENTATION_GENERATOR_BODY,
    },
]


def ensure_default_prompts(PromptTemplate, PromptVersion):
    """
    Idempotently create the canonical default prompts. Safe to call repeatedly
    and from inside a data migration (pass the historical model classes).

    Returns the list of PromptTemplate rows for the default prompts.
    """
    result = []
    for spec in DEFAULT_PROMPTS:
        tpl, _ = PromptTemplate.objects.get_or_create(
            key=spec["key"],
            defaults={
                "name": spec["name"],
                "role": spec["role"],
                "consumer": spec["consumer"],
                "description": spec["description"],
                "tags": spec["tags"],
                "status": "approved",
            },
        )

        # Make sure the role is set even if the template predates this seeding.
        if tpl.role != spec["role"]:
            tpl.role = spec["role"]
            tpl.save(update_fields=["role"])

        if not tpl.versions.exists():
            v1 = PromptVersion.objects.create(
                template=tpl,
                version=1,
                auto_compose=False,  # body is authoritative, do not recompose
                body=spec["body"],
                changelog="Seeded default prompt.",
            )
            tpl.current_version = v1
            tpl.approved_version = v1
            tpl.save(update_fields=["current_version", "approved_version"])

        result.append(tpl)

    return result
