#!/usr/bin/env python3
"""Hook: false-positive-guard (UserPromptSubmit + PreToolUse Edit)

Mitigates Opus 4.7 confidence-drift pattern: claim a bug, then edit without
visible evidence. Tracks "bug evidence" timestamps in session state.

Two events:
- UserPromptSubmit: scan prompt for bug-evidence keywords (DE+EN). If found,
  store timestamp in state with source="user_prompt". No output.
- PreToolUse (Edit): check state for recent evidence (default: <10 min).
  If evidence is fresh: silent pass. If stale or missing: emit advisory.

Never blocks. Always exit 0. Advisory tells Claude to read the file + verify
the bug exists before editing.

Background: Opus 4.7 audit-2 trend +21% Wrong-Approach + new "false-positive
bug invention" pattern after 4.6→4.7 swap. This hook is the structural
mitigation (vs prompt-level guidance which 4.7's higher confidence overrides).
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

# Add hooks dir to path for lib import
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.state import SessionState

HOOK_NAME = "false_positive_guard"
EVIDENCE_WINDOW_SECONDS = 600  # 10 minutes — recent evidence threshold
MAX_PROMPT_LEN = 100_000  # 100 KB — pathological-input DoS guard

# Bug-evidence patterns in user prompts (DE + EN)
BUG_PATTERNS = [
    # English bug words (word boundaries to avoid "debugger" etc. — but allow "bug" itself)
    re.compile(r"\bbug(s|gy)?\b", re.IGNORECASE),
    re.compile(r"\bbroken\b", re.IGNORECASE),
    re.compile(r"\bcrash(ed|es|ing)?\b", re.IGNORECASE),
    re.compile(r"\bdoesn'?t\s+work\b", re.IGNORECASE),
    re.compile(r"\bnot\s+working\b", re.IGNORECASE),
    re.compile(r"\berror\s+(in|on|when|while|at)\b", re.IGNORECASE),
    re.compile(r"\bexception\b", re.IGNORECASE),
    re.compile(r"\bstack\s*trace\b", re.IGNORECASE),
    re.compile(r"\btraceback\b", re.IGNORECASE),
    re.compile(
        r"\bfix(es|ed|ing)?\s+(the|a|this)?\s*(typo|bug|crash|error|issue|problem)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bfailing\b", re.IGNORECASE),
    re.compile(r"\bfailure\b", re.IGNORECASE),
    re.compile(r"\bregression\b", re.IGNORECASE),
    # German bug words
    re.compile(r"\bfehler\b", re.IGNORECASE),
    re.compile(r"\bkaputt\b", re.IGNORECASE),
    re.compile(r"\bcras(c)?ht\b", re.IGNORECASE),  # "crasht" common DE-EN mix
    re.compile(r"\bgeht\s+nicht\b", re.IGNORECASE),
    re.compile(r"\bfunktioniert\s+nicht\b", re.IGNORECASE),
    re.compile(r"\bproblem\s+(mit|bei|in)\b", re.IGNORECASE),
    re.compile(r"\babsturz\b", re.IGNORECASE),
]

# Failure markers in tool output (Bash/test output)
FAILURE_PATTERNS = [
    re.compile(r"\bFAIL(ED|URE|ING)?\b"),
    re.compile(r"\bTraceback\b"),
    re.compile(r"\bError(:|\s+at|\s+in|\s+on)\b"),
    re.compile(r"\b\d+\s+failed\b", re.IGNORECASE),
    re.compile(r"\bAssertionError\b"),
    re.compile(r"\bruff\s+check\s+found\s+\d+\s+errors?\b", re.IGNORECASE),
]


def detect_bug_evidence(prompt: str | None) -> bool:
    """Return True if the prompt contains a bug-evidence keyword (DE/EN).

    Truncates input to MAX_PROMPT_LEN as DoS-guard against pathological inputs.
    """
    if not prompt:
        return False
    # DoS-guard: truncate pathological inputs before regex (Judge B finding)
    sample = prompt[:MAX_PROMPT_LEN] if len(prompt) > MAX_PROMPT_LEN else prompt
    return any(p.search(sample) for p in BUG_PATTERNS)


def detect_failure_in_tool_output(output: str | None) -> bool:
    """Return True if a tool output text contains a failure marker."""
    if not output:
        return False
    return any(p.search(output) for p in FAILURE_PATTERNS)


def is_evidence_recent(
    timestamp: float | None, threshold_seconds: int = EVIDENCE_WINDOW_SECONDS
) -> bool:
    """Return True if timestamp is within threshold from now.

    Inclusive at the boundary: timestamp - now <= threshold.
    Future timestamps (clock skew) are treated as NOT recent (Judge A finding).
    """
    if not timestamp:
        return False
    try:
        age = time.time() - float(timestamp)
    except (TypeError, ValueError):
        return False
    return 0 <= age <= threshold_seconds


def _handle_user_prompt(data: dict, session_state: SessionState) -> None:
    """Detect bug evidence in user prompt; update state if found."""
    prompt = data.get("prompt") or ""
    if not detect_bug_evidence(prompt):
        return

    ns = session_state.get(HOOK_NAME) or {}
    ns["last_evidence_seen_at"] = time.time()
    ns["last_evidence_source"] = "user_prompt"
    ns["evidence_total"] = int(ns.get("evidence_total", 0)) + 1
    session_state.set(HOOK_NAME, ns)
    session_state.save()


def _handle_pre_edit(data: dict, session_state: SessionState) -> None:
    """Check for recent evidence; emit advisory if missing/stale."""
    tool_name = data.get("tool_name", "")
    if tool_name != "Edit":
        return  # Defensive — only Edit is in scope

    ns = session_state.get(HOOK_NAME) or {}
    last_at = ns.get("last_evidence_seen_at")

    if is_evidence_recent(last_at):
        return  # Evidence is fresh — silent pass

    # No recent evidence → emit advisory
    file_path = (data.get("tool_input") or {}).get("file_path", "<unknown>")
    advisory = (
        "⚠️ Edit without visible bug-evidence in recent context. "
        "Opus 4.7 confidence-drift risk: false-positive bug invention. "
        f"File: {file_path}. "
        "Before editing: (1) READ the file, (2) cite the source/line that "
        "demonstrates the bug, (3) if no source exists, ASK Joe what to fix. "
        "Do NOT edit on speculation. (Hook: false-positive-guard)"
    )
    print(json.dumps({"additionalContext": advisory}))

    ns["advisories_emitted"] = int(ns.get("advisories_emitted", 0)) + 1
    ns["last_advisory_at"] = time.time()
    session_state.set(HOOK_NAME, ns)
    session_state.save()


def main() -> None:
    # Read stdin JSON
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    if not isinstance(data, dict):
        sys.exit(0)

    event = data.get("hook_event_name", "")
    session_id = data.get("session_id", "unknown")

    if not event:
        sys.exit(0)

    try:
        session_state = SessionState(session_id)
    except Exception:
        sys.exit(0)

    try:
        if event == "UserPromptSubmit":
            _handle_user_prompt(data, session_state)
        elif event == "PreToolUse":
            _handle_pre_edit(data, session_state)
    except Exception:
        # Never block; never raise
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
