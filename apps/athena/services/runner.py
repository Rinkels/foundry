# apps/athena/services/runner.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional, Protocol

from apps.athena.models import AthenaModelSettings, LLMProviderType


@dataclass(frozen=True)
class LLMResult:
    ok: bool
    text: str
    error: str = ""
    # Usage / billing (zero for the Echo dev provider)
    model: str = ""
    input_tokens: int = 0          # includes cached read tokens (for cost math)
    output_tokens: int = 0
    cached_input_tokens: int = 0   # prompt-cache read tokens (subset of input_tokens)
    total_tokens: int = 0


# Callback invoked with a usage dict once a stream completes (or None if unavailable).
UsageSink = Optional[Callable[[dict], None]]


def _usage_dict(model: str, input_tokens: int, output_tokens: int, cached_input_tokens: int) -> dict:
    return {
        "model": model,
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "cached_input_tokens": int(cached_input_tokens or 0),
        "total_tokens": int(input_tokens or 0) + int(output_tokens or 0),
    }


def _uval(obj, key, default=0):
    """Safe getter for SDK usage objects (dict-like or attribute-like)."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class LLMProvider(Protocol):
    def run(self, prompt: str, settings: AthenaModelSettings) -> LLMResult: ...
    def stream(self, prompt: str, settings: AthenaModelSettings, on_usage: UsageSink = None) -> Iterable[str]: ...


class EchoProvider:
    """Dev provider: echoes the rendered prompt straight back. No token usage."""

    def run(self, prompt: str, settings: AthenaModelSettings) -> LLMResult:
        return LLMResult(ok=True, text=prompt, model="echo")

    def stream(self, prompt: str, settings: AthenaModelSettings, on_usage: UsageSink = None):
        yield prompt
        # No usage to report for echo.


class OpenAIProvider:
    """
    Uses the OpenAI Responses API via the official openai-python SDK.
    Reads OPENAI_API_KEY from the environment.
    """

    def run(self, prompt: str, settings: AthenaModelSettings) -> LLMResult:
        try:
            from openai import OpenAI

            client = OpenAI()  # reads OPENAI_API_KEY from env
            model = settings.model or "gpt-5.4-mini"

            resp = client.responses.create(
                model=model,
                input=prompt,
                temperature=settings.temperature,
                max_output_tokens=settings.max_tokens,
                top_p=settings.top_p,
            )

            usage = getattr(resp, "usage", None)
            in_tok = int(_uval(usage, "input_tokens", 0) or 0)
            out_tok = int(_uval(usage, "output_tokens", 0) or 0)
            cached = int(_uval(_uval(usage, "input_tokens_details", None), "cached_tokens", 0) or 0)
            total = int(_uval(usage, "total_tokens", in_tok + out_tok) or (in_tok + out_tok))

            return LLMResult(
                ok=True,
                text=getattr(resp, "output_text", "") or "",
                model=getattr(resp, "model", "") or model,
                input_tokens=in_tok,
                output_tokens=out_tok,
                cached_input_tokens=cached,
                total_tokens=total,
            )
        except Exception as e:
            return LLMResult(ok=False, text="", error=str(e))

    def stream(self, prompt: str, settings: AthenaModelSettings, on_usage: UsageSink = None):
        from openai import OpenAI

        client = OpenAI()
        model = settings.model or "gpt-4.1-mini"

        stream = client.responses.create(
            model=model,
            input=prompt,
            temperature=settings.temperature,
            max_output_tokens=settings.max_tokens,
            top_p=settings.top_p,
            stream=True,
        )

        final_model = model
        for event in stream:
            etype = getattr(event, "type", None) or (event.get("type") if isinstance(event, dict) else None)
            if etype == "response.output_text.delta":
                delta = getattr(event, "delta", None) or (event.get("delta") if isinstance(event, dict) else "")
                if delta:
                    yield delta
            elif etype == "response.completed" and on_usage:
                resp = getattr(event, "response", None)
                usage = _uval(resp, "usage", None)
                in_tok = int(_uval(usage, "input_tokens", 0) or 0)
                out_tok = int(_uval(usage, "output_tokens", 0) or 0)
                cached = int(_uval(_uval(usage, "input_tokens_details", None), "cached_tokens", 0) or 0)
                on_usage(_usage_dict(getattr(resp, "model", "") or final_model, in_tok, out_tok, cached))


class AnthropicProvider:
    """
    Uses the Anthropic Messages API via the official anthropic SDK.
    Reads ANTHROPIC_API_KEY from the environment.

    Requires `pip install anthropic`. The import is lazy so the rest of Athena
    works even when the SDK is not installed.

    Note on usage: Anthropic reports `input_tokens` as the *uncached* input,
    with cache reads/writes counted separately. We fold cache reads and writes
    back into `input_tokens` so the central pricing helper (which expects
    input_tokens to include cached) computes the cost correctly.
    """

    DEFAULT_MODEL = "claude-opus-4-8"

    def _usage_from_message(self, msg, fallback_model: str) -> dict:
        u = getattr(msg, "usage", None)
        in_tok = int(_uval(u, "input_tokens", 0) or 0)
        out_tok = int(_uval(u, "output_tokens", 0) or 0)
        cache_read = int(_uval(u, "cache_read_input_tokens", 0) or 0)
        cache_write = int(_uval(u, "cache_creation_input_tokens", 0) or 0)
        full_input = in_tok + cache_read + cache_write
        return _usage_dict(getattr(msg, "model", "") or fallback_model, full_input, out_tok, cache_read)

    def run(self, prompt: str, settings: AthenaModelSettings) -> LLMResult:
        try:
            from anthropic import Anthropic

            client = Anthropic()  # reads ANTHROPIC_API_KEY from env
            model = settings.model or self.DEFAULT_MODEL

            msg = client.messages.create(
                model=model,
                max_tokens=settings.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            text = "".join(
                getattr(block, "text", "") for block in (msg.content or [])
                if getattr(block, "type", None) == "text"
            )
            u = self._usage_from_message(msg, model)
            return LLMResult(
                ok=True,
                text=text,
                model=u["model"],
                input_tokens=u["input_tokens"],
                output_tokens=u["output_tokens"],
                cached_input_tokens=u["cached_input_tokens"],
                total_tokens=u["total_tokens"],
            )
        except Exception as e:
            return LLMResult(ok=False, text="", error=str(e))

    def stream(self, prompt: str, settings: AthenaModelSettings, on_usage: UsageSink = None):
        from anthropic import Anthropic

        client = Anthropic()
        model = settings.model or self.DEFAULT_MODEL

        with client.messages.stream(
            model=model,
            max_tokens=settings.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                if text:
                    yield text
            if on_usage:
                try:
                    on_usage(self._usage_from_message(stream.get_final_message(), model))
                except Exception:
                    pass  # never let usage accounting break the stream


def get_provider(settings: AthenaModelSettings) -> LLMProvider:
    if settings.provider == LLMProviderType.OPENAI:
        return OpenAIProvider()
    if settings.provider == LLMProviderType.ANTHROPIC:
        return AnthropicProvider()
    if settings.provider == LLMProviderType.ECHO:
        return EchoProvider()
    # azure/local not yet implemented -> safe dev fallback
    return EchoProvider()


def run_llm(prompt: str, settings: Optional[AthenaModelSettings]) -> LLMResult:
    if settings is None:
        return LLMResult(ok=True, text=prompt, model="echo")
    return get_provider(settings).run(prompt, settings)


def stream_llm(prompt: str, settings: Optional[AthenaModelSettings], on_usage: UsageSink = None):
    if settings is None:
        yield prompt
        return
    yield from get_provider(settings).stream(prompt, settings, on_usage=on_usage)
