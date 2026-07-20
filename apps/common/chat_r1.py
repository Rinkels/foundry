#/apps/common/chat_r1.py
import json
import re
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("OPENAI_API_KEY is not set")

def chat_with_gpt(prompt, model="gpt-3.5-turbo", temperature=0.7, max_tokens=150):
    """
    Send a prompt to GPT and receive a response.

    Parameters:
    - prompt: The input text to send to GPT.
    - model: The model to use. Defaults to "text-davinci-003".
    - temperature: Controls randomness. Lower values make the output more deterministic.
    - max_tokens: The maximum number of tokens to generate in the output.

    Returns:
    - The text response from GPT.
    """
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user","content": prompt}],
        temperature=temperature,
        model="gpt-4o"
    )
    return chat_completion

import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def chat_with_gpt_text(prompt, model="gpt-4o", temperature=0.2):
    resp = client.responses.create(
        model=model,
        input=prompt,
        temperature=temperature,
    )
    return resp.output_text

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)

def _extract_json(text: str) -> str:
    """
    Extract the first JSON object block from a string.
    Handles raw JSON, fenced JSON, or JSON embedded in other text.
    """
    if not text:
        return ""
    t = text.strip()
    t = _FENCE_RE.sub("", t).strip()
    m = _JSON_BLOCK_RE.search(t)
    return m.group(0).strip() if m else ""

def chat_with_gpt_json(
    prompt: str,
    model: str = "gpt-4o",
    temperature: float = 0.2,
    max_output_tokens: int = 1200,
    retries: int = 2,
) -> dict:
    """
    Robust JSON helper that does NOT rely on response_format support.
    - Forces "JSON only" in the prompt
    - Extracts/parses the first JSON object
    - Retries once with a stricter prompt if parsing fails
    """
    base_prompt = prompt.strip()
    if "STRICT JSON" not in base_prompt.upper():
        base_prompt = (
            "Return STRICT JSON only. No markdown, no code fences, no commentary.\n\n"
            + base_prompt
        )

    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = client.responses.create(
                model=model,
                input=base_prompt if attempt == 0 else (
                        "Return STRICT JSON only.\n"
                        "- Output MUST start with '{' and end with '}'.\n"
                        "- Do NOT use ellipses like '...' anywhere.\n"
                        "- Do NOT truncate body_md.\n"
                        "- Escape all quotes inside strings.\n\n"
                        + base_prompt
                ),
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )

            raw = (getattr(resp, "output_text", "") or "").strip()
            if not raw:
                raise ValueError("OpenAI returned empty output_text.")

            json_str = _extract_json(raw)
            if not json_str:
                snippet = raw[:250].replace("\n", "\\n")
                raise ValueError(f"No JSON object found in response. Snippet: {snippet}")

            return json.loads(json_str)

        except Exception as e:
            last_err = e

    raise ValueError(f"Model did not return valid JSON after retries. Last error: {last_err}")


def rewrite_objective_description(description_text):
    prompt = f"Rewrite the following business objective description to be more concise and impactful: {description_text}."
    response = chat_with_gpt(prompt=prompt)
    return response.choices[0].message.content