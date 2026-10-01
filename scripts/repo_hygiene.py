"""Weekly repo-hygiene check: find local work that isn't safely on GitHub.

Scans every git repo directly under the project roots and reports:
  * uncommitted changes whose OLDEST modification is more than N days old
    (fresh work-in-progress is fine; stale uncommitted work is the risk);
  * commits on a branch that are ahead of its upstream (not pushed);
  * branches with NO upstream whose commits exist on no remote branch at all.

Exit code 1 when anything is flagged (so the wrapper can raise a toast).
Written after 2026-10-01, when ten weeks of Foundry work turned out to exist
on one laptop only.

    python scripts/repo_hygiene.py            # report to stdout + file
    python scripts/repo_hygiene.py --days 3   # stricter
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOTS = [Path(r"C:\Projects"), Path(r"C:\projects")]
REPORT = Path(os.environ.get("LOCALAPPDATA", ".")) / "Foundry" / "repo_hygiene.txt"
SKIP = {"SampleApp-QuickBooksV3API-Python"}  # vendor samples, not our work


def git(repo: Path, *args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                              timeout=60, encoding="utf-8", errors="replace").stdout
    except (subprocess.TimeoutExpired, OSError):
        return ""


def repos() -> list[Path]:
    seen: dict[str, Path] = {}
    for root in ROOTS:
        if not root.exists():
            continue
        for d in root.iterdir():
            if d.is_dir() and (d / ".git").exists() and d.name not in SKIP:
                seen.setdefault(d.name.lower(), d)   # C:\Projects and C:\projects are the same drive
    return sorted(seen.values(), key=lambda p: p.name.lower())


def stale_uncommitted(repo: Path, days: int) -> tuple[int, int]:
    """(count of dirty files, age in days of the oldest one)."""
    out = git(repo, "status", "--porcelain", "--untracked-files=all")
    paths = []
    for line in out.splitlines():
        p = line[3:]
        if " -> " in p:
            p = p.split(" -> ", 1)[1]
        paths.append(repo / p.strip().strip('"'))
    if not paths:
        return 0, 0
    now = time.time()
    oldest = 0.0
    for p in paths:
        try:
            oldest = max(oldest, now - p.stat().st_mtime)
        except OSError:
            continue
    return len(paths), int(oldest // 86400)


def unpushed(repo: Path) -> list[str]:
    """Lines describing branches with unpushed work."""
    git(repo, "fetch", "--quiet", "--all")
    findings = []
    refs = git(repo, "for-each-ref", "--format=%(refname:short)|%(upstream:short)", "refs/heads/")
    for line in refs.splitlines():
        branch, upstream = (line.split("|") + [""])[:2]
        if upstream:
            ahead = git(repo, "rev-list", "--count", f"{upstream}..{branch}").strip()
            if ahead and ahead != "0":
                findings.append(f"{branch}: {ahead} commit(s) not pushed to {upstream}")
        else:
            # Commits reachable from this branch but from no remote branch at all.
            only_local = git(repo, "rev-list", "--count", branch, "--not", "--remotes").strip()
            if only_local and only_local != "0":
                findings.append(f"{branch}: {only_local} commit(s) on no remote (branch has no upstream)")
    return findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7, help="flag uncommitted work older than this")
    args = ap.parse_args()

    flagged: list[str] = []
    clean: list[str] = []
    for repo in repos():
        issues = []
        n, age = stale_uncommitted(repo, args.days)
        if n and age >= args.days:
            issues.append(f"{n} uncommitted file(s), oldest {age} days")
        issues += unpushed(repo)
        if not git(repo, "remote").strip():
            issues.append("no remote configured")
        (flagged if issues else clean).append(repo.name)
        for i in issues:
            flagged.append(f"    - {i}")

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"Repo hygiene - {stamp} (threshold {args.days} days)", ""]
    if any(not l.startswith("    ") for l in flagged):
        lines.append("NEEDS ATTENTION:")
        lines += ["  " + l if not l.startswith("    ") else l for l in flagged]
    else:
        lines.append("All repos committed and pushed.")
    lines += ["", "Clean: " + (", ".join(clean) or "—")]
    text = "\n".join(lines)
    print(text)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(text + "\n", encoding="utf-8")
    return 1 if any(not l.startswith("    ") for l in flagged) else 0


if __name__ == "__main__":
    sys.exit(main())
