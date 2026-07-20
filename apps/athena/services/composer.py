# apps/athena/services/composer.py
from __future__ import annotations

from typing import Any

DEFAULT_TEMPLATE = """\
# Goal
{goal}

# Context
{context}

# Instructions
{instructions}

# Output Contract
{output_contract}

# Tone
{tone}

# Guardrails
{guardrails}
""".strip() + "\n"


def compose_body(version_like: Any, template: str = DEFAULT_TEMPLATE) -> str:
    """
    Composes the final body from PromptVersion structured fields.
    IMPORTANT: template uses Python {placeholders}, not Django {{ vars }}.
    """
    def norm(x: Any) -> str:
        s = x if isinstance(x, str) else ("" if x is None else str(x))
        s = s.strip()
        return s if s else "(none)"

    return template.format(
        goal=norm(getattr(version_like, "goal", "")),
        context=norm(getattr(version_like, "context", "")),
        instructions=norm(getattr(version_like, "instructions", "")),
        output_contract=norm(getattr(version_like, "output_contract", "")),
        tone=norm(getattr(version_like, "tone", "")),
        guardrails=norm(getattr(version_like, "guardrails", "")),
    )
