#!/usr/bin/env python3
"""Hook: Exploration First (PreToolUse — Write|Edit)

Checks if Claude has read enough code before writing.
If the first Write/Edit happens before 3+ Read/Grep/Glob calls,
injects advisory context encouraging exploration first.

Addresses: Report finding "Sessions that explored first had least friction."

Exit 0 + additionalContext. Never blocks.
"""
import json
import re
import sys
from pathlib import Path

HOOK_NAME = "exploration_first"

# --- Add hooks dir to path for lib import ---
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.state import SessionState  # noqa: E402 — sibling import after path setup

READ_TOOLS = {"Read", "Grep", "Glob", "Agent"}
WRITE_TOOLS = {"Write", "Edit"}
# Load from centralized config (default: 3)
try:
    from lib.config import load_config as _load_config
    _cfg = _load_config()
    MIN_READS_BEFORE_WRITE = _cfg.get("thresholds", {}).get("min_reads_before_write", 3)
except Exception:
    MIN_READS_BEFORE_WRITE = 3


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

    session_state = SessionState(session_id)
    state = session_state.get("exploration_first")

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
        session_state.set("exploration_first", state)
        session_state.save()
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
            if (file_path.endswith(".py")
                    and "test" not in file_path.lower()
                    and re.search(r"\bprint\(", new_content)
                    and not re.search(r"#.*\bprint\b", new_content)):
                warnings.append(
                    "Python: print() detected. Rule 05: Use structured logging instead of print() in production."
                )

            # SKILL.md checks
            if file_path.endswith("SKILL.md") and "---" in new_content:
                if not re.search(r"^version:", new_content, re.MULTILINE):
                    warnings.append(
                        "SKILL.md: Missing 'version:' field in frontmatter. eval.py: +10 points with version."
                    )
                if not re.search(r"^token-budget:", new_content, re.MULTILINE):
                    warnings.append(
                        "SKILL.md: Missing 'token-budget:' field. eval.py: +15 points with token-budget."
                    )

            # Rules .md checks (in .claude/rules/)
            if ("/rules/" in file_path and file_path.endswith(".md")
                    and not re.search(r"^#\s+\S", new_content, re.MULTILINE)):
                warnings.append(
                    "Rules file: No title (# ...) found. Every rule file needs a title."
                )

        # --- Existing: exploration-first check ---
        if state["read_count"] < MIN_READS_BEFORE_WRITE and not state["warned"]:
            state["warned"] = True
            warnings.append(
                f"WRITING BEFORE READING ({state['read_count']} reads before first write). "
                "Exploration before implementation."
            )

        # After warning or if enough reads, mark as implementation
        if state["read_count"] >= MIN_READS_BEFORE_WRITE:
            state["phase"] = "implementation"

        session_state.set("exploration_first", state)
        session_state.save()

        if warnings:
            print(json.dumps({"additionalContext": " | ".join(warnings)}))

    sys.exit(0)


if __name__ == "__main__":
    main()
