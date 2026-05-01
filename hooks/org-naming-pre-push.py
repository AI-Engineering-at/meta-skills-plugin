#!/usr/bin/env python3
"""Hook: org-naming-pre-push (PreToolUse Bash, matcher: git push)

Mitigates Wrong-Folder/Repo friction (Audit pattern, +21% post-4.7).

Reads the repo's `.git/config` from cwd, extracts the origin URL, parses
the GitHub org/user, and emits an advisory if the org is NOT in the
allowlist (or is the known typo-org "AI-Engineerings-at").

Default mode: advisory (exit 0 + additionalContext). Never blocks.
A future config flag could enable strict block-mode after a soak period.

Allowlist: AI-Engineering-at, LEEI1337, FoxLabs-ai.
Typo-org explicitly flagged: AI-Engineerings-at (server-redirected, but
local remote URLs should be migrated — see Session B5 audit).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.state import SessionState

HOOK_NAME = "org_naming_pre_push"

ALLOWLIST = frozenset({"AI-Engineering-at", "LEEI1337", "FoxLabs-ai"})
KNOWN_TYPO = frozenset({"AI-Engineerings-at"})

# `git push` at a word boundary (not as substring of echoed text).
# Allow optional flags like `-C path` between `git` and `push`.
PUSH_PATTERN = re.compile(r"^\s*git(?:\s+-\S+\s+\S+)*\s+push\b")

# Parse GitHub org from https://github.com/ORG/repo or git@github.com:ORG/repo
HTTPS_URL_PATTERN = re.compile(r"^https?://github\.com/([A-Za-z0-9_.-]+)/")
SSH_URL_PATTERN = re.compile(r"^git@github\.com:([A-Za-z0-9_.-]+)/")


def is_git_push_command(command: str | None) -> bool:
    """Return True if the command is a real `git push` invocation.

    Excludes echoed text like `echo 'git push'`.
    """
    if not command:
        return False
    return bool(PUSH_PATTERN.match(command))


def parse_org_from_url(url: str | None) -> str | None:
    """Extract the GitHub org/user from a remote URL. None if not a GitHub URL."""
    if not url:
        return None
    url = url.strip()
    m = HTTPS_URL_PATTERN.match(url) or SSH_URL_PATTERN.match(url)
    if not m:
        return None
    org = m.group(1)
    if not org or "/" in org:
        return None
    return org


def classify_org(org: str | None) -> str:
    """Return one of: 'allow' | 'typo' | 'unknown' | 'none'."""
    if not org:
        return "none"
    if org in ALLOWLIST:
        return "allow"
    if org in KNOWN_TYPO:
        return "typo"
    return "unknown"


def _read_origin_url(cwd: str) -> str | None:
    """Read origin URL from .git/config in cwd. Returns None if missing/unreadable."""
    if not cwd:
        return None
    git_config = Path(cwd) / ".git" / "config"
    if not git_config.is_file():
        return None
    try:
        content = git_config.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    # Find the [remote "origin"] section + url line. Simple parser without configparser
    # (configparser dislikes the special `[remote "origin"]` syntax in some setups).
    in_origin = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_origin = stripped == '[remote "origin"]'
            continue
        if in_origin and stripped.lower().startswith("url"):
            # Format: `url = https://...` or `\turl=...`
            _, _, value = stripped.partition("=")
            return value.strip() or None
    return None


def _build_advisory(org: str, classification: str, command: str) -> str:
    if classification == "typo":
        return (
            f"⚠️ Push target uses TYPO-org '{org}' (should be 'AI-Engineering-at'). "
            f"Server-side migration is active, but local remote URL still points "
            f"to the old org. Consider: `git remote set-url origin "
            f"https://github.com/AI-Engineering-at/<repo>.git`. "
            f"Push may still work via redirect. (Hook: org-naming-pre-push)"
        )
    # unknown
    return (
        f"⚠️ Push target uses unknown org '{org}' (allowlist: AI-Engineering-at, "
        f"LEEI1337, FoxLabs-ai). If intentional (e.g., third-party fork), "
        f"silence-mark in state; otherwise re-check `git remote get-url origin`. "
        f"Command: {command[:80]}. (Hook: org-naming-pre-push)"
    )


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    if not isinstance(data, dict):
        sys.exit(0)

    if data.get("hook_event_name") != "PreToolUse":
        sys.exit(0)
    if data.get("tool_name") != "Bash":
        sys.exit(0)

    command = (data.get("tool_input") or {}).get("command", "")
    if not is_git_push_command(command):
        sys.exit(0)

    cwd = data.get("cwd", "")
    origin_url = _read_origin_url(cwd)
    org = parse_org_from_url(origin_url)
    classification = classify_org(org)

    if classification in ("allow", "none"):
        sys.exit(0)  # Silent pass

    # typo or unknown → emit advisory
    advisory = _build_advisory(org, classification, command)
    print(json.dumps({"additionalContext": advisory}))

    # Update state for telemetry
    try:
        session_id = data.get("session_id", "unknown")
        state = SessionState(session_id)
        ns = state.get(HOOK_NAME) or {}
        ns["push_count"] = int(ns.get("push_count", 0)) + 1
        ns["violations_warned"] = int(ns.get("violations_warned", 0)) + 1
        ns["last_org"] = org
        ns["last_classification"] = classification
        state.set(HOOK_NAME, ns)
        state.save()
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
