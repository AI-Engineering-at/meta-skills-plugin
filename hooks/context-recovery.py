#!/usr/bin/env python3
"""Hook: Context Recovery (PreCompact event)

Fires BEFORE context compaction. Saves full session state so that
after compaction, session-init can detect the gap and inject recovery context.

This replaces the fragile prompt-counter gap detection with a proper
lifecycle event.

Exit 0 + additionalContext. Never blocks.
"""
import json
import os
import sys
from datetime import UTC, datetime

# --- Add hooks dir to path for lib import ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import contextlib

from lib.services import detect_project_name, get_git_changes_summary
from lib.state import SessionState

HOOK_NAME = "context_recovery"


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    session_id = data.get("session_id", "unknown")
    cwd = os.getcwd()
    project = detect_project_name(cwd)
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    # --- Save full state snapshot before compaction ---
    state = SessionState(session_id)

    git_summary = ""
    with contextlib.suppress(Exception):
        git_summary = get_git_changes_summary(max_lines=10)

    state.set("session_meta", {
        "project": project,
        "cwd": cwd,
        "timestamp": now,
        "prompt_count_at_save": state.prompt_count,
        "git_summary": git_summary[:500] if git_summary else "",
        "uncommitted": False,
        "lint_status": state.get("quality_gate").get("last_lint_result", "unknown"),
        "open_items": "pre-compaction save",
        "compaction_count": state.get("session_meta").get("compaction_count", 0) + 1,
    })
    state.save()

    # --- Inject recovery hints into the compacted context ---
    qg = state.get("quality_gate")
    scope = state.get("scope_tracker")

    recovery_parts = [
        f"PRE-COMPACTION STATE SAVE (prompt #{state.prompt_count}).",
        f"Project: {project}.",
    ]

    if qg.get("consecutive_failures", 0) > 0:
        recovery_parts.append(
            f"Quality: {qg['consecutive_failures']} consecutive failures, "
            f"lint={qg.get('last_lint_result', '?')}, tests={qg.get('last_test_result', '?')}."
        )

    if scope.get("task_switches", 0) > 0:
        recovery_parts.append(
            f"Scope: {scope['task_switches']} topic switches, "
            f"domains: {', '.join(scope.get('seen_domains', [])[:5])}."
        )

    if git_summary:
        recovery_parts.append(f"Recent git: {git_summary[:200]}")

    print(json.dumps({"additionalContext": " ".join(recovery_parts)}))
    sys.exit(0)


if __name__ == "__main__":
    main()
