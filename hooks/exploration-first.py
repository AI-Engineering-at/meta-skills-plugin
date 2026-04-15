#!/usr/bin/env python3
"""Hook: Exploration First (PreToolUse — Write|Edit)

Checks if Claude has read enough code before writing.
If the first Write/Edit happens before 3+ Read/Grep/Glob calls,
injects advisory context encouraging exploration first.

Addresses: Report finding "Sessions that explored first had least friction."

Exit 0 + additionalContext. Never blocks.
"""
import json
import os
import re
import sys
from pathlib import Path

HOOK_NAME = "exploration_first"
STATE_DIR = Path(os.environ.get(
    "CLAUDE_PLUGIN_DATA",
    Path.home() / ".claude" / "plugins" / "data" / "meta-skills"
))

READ_TOOLS = {"Read", "Grep", "Glob", "Agent"}
WRITE_TOOLS = {"Write", "Edit"}
# Load from centralized config (default: 3)
try:
    from lib.config import load_config as _load_config
    _cfg = _load_config()
    MIN_READS_BEFORE_WRITE = _cfg.get("thresholds", {}).get("min_reads_before_write", 3)
except Exception:
    MIN_READS_BEFORE_WRITE = 3


def load_state(session_id: str) -> dict:
    """Load exploration tracking state."""
    state_file = STATE_DIR / f".exploration-first-{session_id}.json"
    try:
        if state_file.exists():
            return json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {
        "session_id": session_id,
        "read_count": 0,
        "write_count": 0,
        "phase": "exploration",  # exploration -> implementation
        "warned": False,
    }


def save_state(session_id: str, state: dict) -> None:
    """Persist state."""
    state_file = STATE_DIR / f".exploration-first-{session_id}.json"
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

    tool_name = data.get("tool_name", "")
    session_id = data.get("session_id", "unknown")

    if not tool_name:
        sys.exit(0)

    state = load_state(session_id)

    # Already in implementation phase — stop checking
    if state["phase"] == "implementation":
        sys.exit(0)

    # Track reads (even though this hook only fires on Write|Edit,
    # we also get called for other tools if matcher matches)
    if tool_name in READ_TOOLS:
        state["read_count"] += 1
        # Transition to implementation after enough reads
        if state["read_count"] >= MIN_READS_BEFORE_WRITE + 2:  # 5+ reads = definitely explored
            state["phase"] = "implementation"
        save_state(session_id, state)
        sys.exit(0)

    # This is a Write or Edit call
    if tool_name in WRITE_TOOLS:
        state["write_count"] += 1
        warnings = []

        # --- P5: Write-Time Quality Checks (Plankton Pattern) ---
        tool_input = data.get("tool_input", {})
        file_path = tool_input.get("file_path", "") if isinstance(tool_input, dict) else ""
        new_content = tool_input.get("content", tool_input.get("new_string", "")) if isinstance(tool_input, dict) else ""

        if file_path and new_content:
            # Python file checks
            if file_path.endswith(".py"):
                # Check for print() in production code (not test files)
                if "test" not in file_path.lower() and re.search(r"\bprint\(", new_content):
                    if not re.search(r"#.*\bprint\b", new_content):  # Not in comment
                        warnings.append(
                            "Python: print() erkannt. Rule 05: Structured Logging statt print() in Production."
                        )

            # SKILL.md checks
            if file_path.endswith("SKILL.md") and "---" in new_content:
                if not re.search(r"^version:", new_content, re.MULTILINE):
                    warnings.append(
                        "SKILL.md: Kein 'version:' Feld im Frontmatter. eval.py: +10 Punkte mit version."
                    )
                if not re.search(r"^token-budget:", new_content, re.MULTILINE):
                    warnings.append(
                        "SKILL.md: Kein 'token-budget:' Feld. eval.py: +15 Punkte mit token-budget."
                    )

            # Rules .md checks (in .claude/rules/)
            if "/rules/" in file_path and file_path.endswith(".md"):
                if not re.search(r"^#\s+\S", new_content, re.MULTILINE):
                    warnings.append(
                        "Rules-Datei: Kein Titel (# ...) gefunden. Jede Rule braucht einen Titel."
                    )

        # --- Existing: exploration-first check ---
        if state["read_count"] < MIN_READS_BEFORE_WRITE and not state["warned"]:
            state["warned"] = True
            warnings.append(
                f"SCHREIBEN VOR LESEN ({state['read_count']} Reads vor erstem Write). "
                "Exploration vor Implementation."
            )

        # After warning or if enough reads, mark as implementation
        if state["read_count"] >= MIN_READS_BEFORE_WRITE:
            state["phase"] = "implementation"

        save_state(session_id, state)

        if warnings:
            print(json.dumps({"additionalContext": " | ".join(warnings)}))

    sys.exit(0)


if __name__ == "__main__":
    main()
