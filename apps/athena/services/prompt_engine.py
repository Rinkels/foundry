# apps/athena/services/prompt_engine.py
from __future__ import annotations

from dataclasses import dataclass
from django.template import Context, Engine, TemplateSyntaxError


@dataclass(frozen=True)
class RenderResult:
    ok: bool
    rendered: str
    error: str = ""


_engine = Engine(debug=False)  # no file loading, pure string templates


def render_prompt(template_text: str, variables: dict) -> RenderResult:
    try:
        tpl = _engine.from_string(template_text)
        rendered = tpl.render(Context(variables or {}))
        return RenderResult(ok=True, rendered=rendered)
    except TemplateSyntaxError as e:
        return RenderResult(ok=False, rendered="", error=f"TemplateSyntaxError: {e}")
    except Exception as e:
        return RenderResult(ok=False, rendered="", error=f"RenderError: {e}")
