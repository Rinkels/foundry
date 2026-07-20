# apps/athena/services/checks.py
from __future__ import annotations

import json


def check_require_substrings(output_text: str, substrings: list[str]) -> tuple[bool, str]:
    missing = [s for s in (substrings or []) if s not in (output_text or "")]
    if missing:
        return False, f"Missing required substrings: {missing}"
    return True, "OK"


def check_is_json(output_text: str) -> tuple[bool, str]:
    try:
        json.loads(output_text or "")
        return True, "OK"
    except Exception as e:
        return False, f"Not valid JSON: {e}"
