#!/usr/bin/env python3
"""Hook: Approach Guard (PreToolUse — Bash)

Detects model/tool switching and approach changes in Bash commands.
Injects advisory context reminding Claude to ask Joe before switching.

Addresses: #1 Friction "Wrong Approach" (43 incidents in 31 sessions).

Exit 0 + additionalContext. Never blocks.
"""
import json
import os
import re
import sys
from pathlib import Path

HOOK_NAME = "approach_guard"
STATE_DIR = Path(os.environ.get(
    "CLAUDE_PLUGIN_DATA",
    Path.home() / ".claude" / "plugins" / "data" / "meta-skills"
))

# --- Model/approach switching patterns ---
MODEL_SWITCH_PATTERNS = [
    re.compile(r"ollama\s+run\s+(\S+)", re.IGNORECASE),
    re.compile(r"curl\s+.*(?:openai|anthropic|together|groq)\.com", re.IGNORECASE),
    re.compile(r"--model\s+\S+", re.IGNORECASE),
    re.compile(r"(?:llama|vllm|lmstudio).*(?:--model|serve)\s+\S+", re.IGNORECASE),
]

# --- Destructive / risky patterns (already covered by safety_gate, but reinforce) ---
RISKY_PATTERNS = [
    re.compile(r"docker\s+(?:service\s+)?(?:rm|remove|prune)", re.IGNORECASE),
    re.compile(r"rm\s+-rf?\s+/", re.IGNORECASE),
    re.compile(r"git\s+(?:push\s+--force|reset\s+--hard)", re.IGNORECASE),
]

# --- False positives: commands that look like switching but aren't ---
SAFE_PATTERNS = [
    re.compile(r"ollama\s+(?:list|ps|show|tags)", re.IGNORECASE),
    re.compile(r"curl\s+.*(?:api/tags|api/ps|health)", re.IGNORECASE),
    re.compile(r"--version", re.IGNORECASE),
]


def load_session_state(session_id: str) -> dict:
    """Load session state for scope tracking."""
    state_file = STATE_DIR / f".approach-guard-{session_id}.json"
    try:
        if state_file.exists():
            return json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"session_id": session_id, "bash_count": 0, "scope_confirmed": False}


def save_session_state(session_id: str, state: dict) -> None:
    """Persist session state."""
    state_file = STATE_DIR / f".approach-guard-{session_id}.json"
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    session_id = data.get("session_id", "unknown")

    if not command:
        sys.exit(0)

    # --- Check for safe patterns first ---
    for safe in SAFE_PATTERNS:
        if safe.search(command):
            sys.exit(0)

    # --- Load state ---
    state = load_session_state(session_id)
    state["bash_count"] += 1
    warnings = []

    # --- Check model switching ---
    for pattern in MODEL_SWITCH_PATTERNS:
        match = pattern.search(command)
        if match:
            model_name = match.group(1) if match.lastindex else "unknown"
            warnings.append(
                f"MODEL/APPROACH SWITCH DETECTED ('{model_name}'). "
                "Rule: NEVER switch model, tool, or strategy without asking Joe. "
                "If blocked: STOP and report the blocker."
            )
            break

    # --- Check risky patterns ---
    for pattern in RISKY_PATTERNS:
        if pattern.search(command):
            warnings.append(
                "RISKY ACTION DETECTED. S1: Show Joe and get confirmation first."
            )
            break

    # --- Scope contract reminder (first 2 bash commands) ---
    if state["bash_count"] <= 2 and not state["scope_confirmed"]:
        warnings.append(
            "Reminder: Have you agreed on a scope contract with Joe? "
            "(Documents/CLAUDE.md Step 2: define scope, 'done' criteria, "
            "what is NOT included)"
        )

    save_session_state(session_id, state)

    if warnings:
        context = " | ".join(warnings)
        print(json.dumps({"additionalContext": context}))

    sys.exit(0)


if __name__ == "__main__":
    main()
