#!/usr/bin/env python3
"""Hook: Session End (SessionEnd event)

Fires when the session fully terminates. Handles cleanup and persistence
that was previously embedded in session-stop.py.

1. Persists final session state (for next session's context recovery).
2. Writes rich summary to Honcho.
3. Cleans up stale state files.

session-stop.py remains for user-facing guidance (additionalContext).
session-end.py handles backend persistence (no user-visible output needed).

Exit 0. Never blocks.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- Add hooks dir to path for lib import ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.services import (
    HonchoClient,
    detect_peer_id,
    detect_project_name,
    get_git_changes_summary,
    log_error,
)
from lib.state import SessionState

HOOK_NAME = "session_end"


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    session_id = data.get("session_id", "unknown")
    cwd = os.getcwd()
    peer_id = detect_peer_id(cwd)
    project = detect_project_name(cwd)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # --- Load session state ---
    state = SessionState(session_id)

    # --- Generate git summary ---
    git_summary = ""
    try:
        git_summary = get_git_changes_summary(max_lines=15)
    except Exception:
        pass

    # --- Write to Honcho ---
    try:
        honcho = HonchoClient(timeout=10.0)
        if honcho.is_healthy():
            honcho.create_session(
                session_id=session_id,
                peer_id=peer_id,
                metadata={"event": "session-end", "project": project},
            )

            qg = state.get("quality_gate")
            scope = state.get("scope_tracker")

            honcho_parts = [
                f"Session {session_id[:12]}... ended.",
                f"Project: {project} | CWD: {cwd}",
                f"Time: {now} | Prompts: {state.prompt_count}",
            ]
            if git_summary:
                honcho_parts.append(f"Git changes:\n{git_summary}")
            if qg.get("consecutive_failures", 0) > 0:
                honcho_parts.append(
                    f"Quality: {qg['consecutive_failures']} failures, "
                    f"lint={qg.get('last_lint_result', '?')}, "
                    f"tests={qg.get('last_test_result', '?')}"
                )
            if scope.get("task_switches", 0) > 0:
                honcho_parts.append(
                    f"Scope: {scope['task_switches']} switches across "
                    f"{', '.join(scope.get('seen_domains', []))}"
                )

            honcho.add_message(
                session_id=session_id,
                peer_id=peer_id,
                content="\n".join(honcho_parts),
            )
    except Exception as e:
        log_error(HOOK_NAME, f"Honcho write failed: {e}", f"session={session_id}")

    # --- Persist final state ---
    state.set("session_meta", {
        "project": project,
        "cwd": cwd,
        "timestamp": now,
        "prompt_count_at_save": state.prompt_count,
        "git_summary": git_summary[:500] if git_summary else "",
        "uncommitted": False,
        "lint_status": state.get("quality_gate").get("last_lint_result", "unknown"),
        "open_items": "session ended",
    })
    state.save()

    # --- Cleanup stale state ---
    SessionState.cleanup_stale(keep=5)

    # --- Auto-regenerate network diagram if infra changed ---
    if git_summary and any(
        kw in git_summary.lower()
        for kw in ["03-infrastructure", "03b-services", "vault", "swarm", "node"]
    ):
        try:
            import subprocess
            diagram_script = Path(cwd) / "tools" / "generate-network-diagram.py"
            if diagram_script.exists():
                subprocess.run(
                    [sys.executable, str(diagram_script)],
                    capture_output=True, timeout=15, cwd=cwd,
                )
        except Exception:
            pass

    sys.exit(0)


if __name__ == "__main__":
    main()
