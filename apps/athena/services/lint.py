# apps/athena/services/lint.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from apps.athena.models import PromptTemplate, PromptVersion


VAR_PATTERN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")  # simple Django template var refs


@dataclass(frozen=True)
class LintIssue:
    level: str  # "warn" | "error"
    code: str
    message: str


def extract_referenced_vars(text: str) -> set[str]:
    if not text:
        return set()
    return set(VAR_PATTERN.findall(text))


def lint_version(template: PromptTemplate, version: PromptVersion) -> list[LintIssue]:
    issues: list[LintIssue] = []

    defined = set(template.variables.values_list("name", flat=True))
    referenced = extract_referenced_vars(version.body)

    undefined = sorted(referenced - defined)
    unused = sorted(defined - referenced)

    if undefined:
        issues.append(LintIssue(
            level="error",
            code="UNDEFINED_VARS",
            message=f"Prompt references undefined variables: {undefined}",
        ))

    if unused:
        issues.append(LintIssue(
            level="warn",
            code="UNUSED_VARS",
            message=f"Template defines variables not used in prompt body: {unused}",
        ))

    # Hygiene checks
    if not (version.output_contract or "").strip():
        issues.append(LintIssue(
            level="warn",
            code="MISSING_OUTPUT_CONTRACT",
            message="No output contract specified. Prompts without a contract tend to drift.",
        ))

    if not (version.instructions or "").strip():
        issues.append(LintIssue(
            level="warn",
            code="MISSING_INSTRUCTIONS_BLOCK",
            message="Instructions block is empty. Consider moving key constraints out of the body into structured fields.",
        ))

    if len((version.body or "").strip()) < 40:
        issues.append(LintIssue(
            level="warn",
            code="VERY_SHORT_BODY",
            message="Prompt body is very short; may be under-specified.",
        ))

    return issues


def lint_passes(issues: Iterable[LintIssue]) -> bool:
    return all(i.level != "error" for i in issues)
