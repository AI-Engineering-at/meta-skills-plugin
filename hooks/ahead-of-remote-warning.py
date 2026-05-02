#!/usr/bin/env python3
"""Hook: ahead-of-remote-warning (SessionStart)

Mitigates "Ahead-of-Remote unentdeckt" pattern (audit: nomos had 97
unpushed commits before today's audit forced a push).

On SessionStart, iterates a configurable watch-list of repos and runs
`git rev-list --count origin/<branch>..HEAD` (NO fetch — uses local refs)
for each. Emits an advisory if any repo is ≥ warn threshold (5 ahead),
escalates if ≥ critical threshold (20).

Watch-list resolution order:
  1. Env var AHEAD_WARN_WATCH (comma-separated absolute paths)
  2. Default: phantom-ai, nomos, zeroth, Playbook01, wiki under
     ~/Documents/

Pure-local operation: no network calls, no `git fetch`. Won't update
remote refs. Hook exit 0 always; advisory only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.state import SessionState

HOOK_NAME = "ahead_of_remote_warning"
WARN_THRESHOLD = 5
CRITICAL_THRESHOLD = 20
GIT_TIMEOUT_SECONDS = 5

DEFAULT_WATCH_DIRS = [
    "phantom-ai",
    "nomos",
    "zeroth",
    "Playbook01",
    "wiki",
]


def classify_severity(count: int | None) -> str:
    """Return 'ok' | 'warn' | 'critical' | 'unknown'."""
    if count is None or count < 0:
        return "unknown"
    if count >= CRITICAL_THRESHOLD:
        return "critical"
    if count >= WARN_THRESHOLD:
        return "warn"
    return "ok"


def _current_branch(repo: str) -> str | None:
    """Return current branch name, or None."""
    try:
        result = subprocess.run(
            ["git", "-C", repo, "symbolic-ref", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def count_ahead(repo: str, branch: str | None = None) -> int | None:
    """Count commits in `branch` that are not in `origin/<branch>`.

    Returns None when the repo is invalid, has no origin, or the count
    cannot be determined within the timeout.
    """
    if not repo or not Path(repo, ".git").exists():
        return None
    if branch is None:
        branch = _current_branch(repo)
        if not branch:
            return None
    try:
        result = subprocess.run(
            ["git", "-C", repo, "rev-list", "--count", f"origin/{branch}..HEAD"],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            return None
        return int(result.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _resolve_watch_list() -> list[str]:
    """Resolve watch-list of repo paths from env or defaults."""
    env_value = os.environ.get("AHEAD_WARN_WATCH", "").strip()
    if env_value:
        return [p.strip() for p in env_value.split(",") if p.strip()]
    home = Path.home()
    base = home / "Documents"
    return [str(base / name) for name in DEFAULT_WATCH_DIRS]


def _build_advisory(findings: list[dict]) -> str:
    """Build a single advisory string from the list of {repo, count, severity}."""
    lines = [
        "⚠️ Repos with unpushed commits (ahead-of-remote-warning):",
    ]
    has_critical = any(f["severity"] == "critical" for f in findings)
    for f in findings:
        marker = "🔴" if f["severity"] == "critical" else "🟡"
        repo_name = Path(f["repo"]).name
        lines.append(
            f"  {marker} {repo_name}: {f['count']} commits ahead ({f['severity']})"
        )
    if has_critical:
        lines.append(
            "  → CRITICAL: ≥20 commits unpushed = data-loss risk on disk crash. "
            "Push now (audit pattern: nomos had 97 unpushed before today's recovery)."
        )
    else:
        lines.append("  → Run `git push` in each warned repo to clear advisory.")
    lines.append("(Hook: ahead-of-remote-warning. Threshold: warn≥5, critical≥20.)")
    return "\n".join(lines)


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    if not isinstance(data, dict):
        sys.exit(0)
    if data.get("hook_event_name") != "SessionStart":
        sys.exit(0)

    watch_list = _resolve_watch_list()
    findings = []
    for repo in watch_list:
        count = count_ahead(repo)
        severity = classify_severity(count)
        if severity in ("warn", "critical"):
            findings.append({"repo": repo, "count": count, "severity": severity})

    if not findings:
        sys.exit(0)  # No repo at risk → silent

    advisory = _build_advisory(findings)
    print(json.dumps({"additionalContext": advisory}))

    try:
        session_id = data.get("session_id", "unknown")
        state = SessionState(session_id)
        ns = state.get(HOOK_NAME) or {}
        import time as _time

        ns["last_check_at"] = _time.time()
        ns["repos_at_risk"] = [
            {
                "repo": Path(f["repo"]).name,
                "count": f["count"],
                "severity": f["severity"],
            }
            for f in findings
        ]
        state.set(HOOK_NAME, ns)
        state.save()
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
