"""Run external CLI tools (gcloud, docker, git) and capture their output.

Kept deliberately small: every command is a list of args (never a shell
string, so there's no shell-injection surface), output is captured
combined (stdout+stderr) for the DeploymentRun log, and a timeout guards
against hung builds.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Sequence


class ToolNotFound(RuntimeError):
    """Raised when a required CLI (gcloud/docker/git) isn't on PATH."""


@dataclass
class CommandResult:
    returncode: int
    output: str
    command: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def resolve_tool(name: str) -> str:
    """Return the absolute path to a CLI tool, accounting for Windows .cmd shims."""
    found = shutil.which(name)
    if not found and name == "gcloud":
        # On Windows the SDK installs gcloud.cmd
        found = shutil.which("gcloud.cmd")
    if not found:
        raise ToolNotFound(f"`{name}` was not found on PATH. Install it or fix PATH.")
    return found


def run(
    args: Sequence[str],
    *,
    cwd: Optional[Path | str] = None,
    timeout: int = 1800,
    env: Optional[Mapping[str, str]] = None,
) -> CommandResult:
    """Run a command, capturing combined stdout/stderr.

    `args[0]` is resolved via `resolve_tool` so callers can pass the bare
    tool name (e.g. "gcloud") and get the right executable on any OS.

    `env`, if given, is merged over the current environment (not a full
    replacement), so callers can inject per-invocation credentials without
    losing PATH etc.
    """
    args = list(args)
    args[0] = resolve_tool(args[0])
    printable = " ".join(args)

    proc_env = None
    if env:
        proc_env = {**os.environ, **env}

    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=proc_env,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            returncode=124,
            output=f"{printable}\n\nTIMEOUT after {timeout}s\n{exc.stdout or ''}{exc.stderr or ''}",
            command=printable,
        )

    output = (proc.stdout or "") + (proc.stderr or "")
    return CommandResult(returncode=proc.returncode, output=output, command=printable)
