#!/usr/bin/env python3
"""Hook: Session Init v4 (UserPromptSubmit)

Simplified for v4.0: Only handles prompt counting and context recovery.
Heavy initialization (Honcho, open-notebook, CI, watcher) moved to
session-start.py (SessionStart event).

On every prompt:
1. Increment prompt counter
2. Check for context recovery (gap > threshold after compaction)
3. Exit fast (< 5ms on subsequent prompts)

Exit 0 + additionalContext (only if recovery needed). Never blocks.
"""
import json
import os
import sys

# --- Add hooks dir to path for lib import ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HOOK_NAME = "session_init"

from lib.state import SessionState  # noqa: E402 — sibling import after path setup

# Load recovery gap threshold from config
try:
    from lib.config import load_config as _load_config
    _cfg = _load_config()
    RECOVERY_GAP = _cfg.get("thresholds", {}).get("context_recovery_gap", 10)
except Exception:
    RECOVERY_GAP = 10

# Read stdin early
try:
    _raw_stdin = sys.stdin.read()
    _stdin_data = json.loads(_raw_stdin) if _raw_stdin.strip() else {}
except Exception:
    _stdin_data = {}

session_id = _stdin_data.get("session_id", "unknown")

# --- Increment prompt counter ---
_session_state = SessionState(session_id)
current_count = _session_state.prompt_count + 1
_session_state.prompt_count = current_count
_session_state.save()

# --- P7: Context recovery detection ---
recovery_context = ""
if _session_state.is_initialized and current_count > 1:
    try:
        meta = _session_state.get("session_meta")
        saved_count = meta.get("prompt_count_at_save", 0) if isinstance(meta, dict) else 0
        gap = current_count - saved_count
        if gap > RECOVERY_GAP and saved_count > 0:
            recovery_context = (
                f"CONTEXT RECOVERY: {gap} prompts since last state save. "
                f"Project: {meta.get('project', '?')}. "
                f"Last changes: {meta.get('git_summary', 'unknown')[:200]}. "
                f"Open items: {meta.get('open_items', 'none')}."
            )
    except Exception:
        pass

if recovery_context:
    print(json.dumps({"additionalContext": recovery_context}))

sys.exit(0)
