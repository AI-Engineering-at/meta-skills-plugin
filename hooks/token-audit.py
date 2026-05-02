#!/usr/bin/env python3
"""Hook: Token Audit (PostToolUse)

Logs every tool call with estimated token cost.
Pure measurement — no filtering, no modification, just data.

Tracks: tool name, input size, output size, estimated tokens, duration.
Writes to ${CLAUDE_PLUGIN_DATA}/token-audit.jsonl (append-only).

This data proves:
- Where tokens flow (which tools cost the most)
- Session efficiency (tokens per useful action)
- Before/after comparison when optimizations are applied

Cross-platform. Zero overhead on tool execution (async-safe).
Exit 0 always — never blocks.
"""

import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# Plugin data directory
PLUGIN_DATA = Path(
    os.environ.get(
        "CLAUDE_PLUGIN_DATA",
        Path.home() / ".claude" / "plugins" / "data" / "meta-skills",
    )
)
PLUGIN_DATA.mkdir(parents=True, exist_ok=True)

AUDIT_FILE = PLUGIN_DATA / "token-audit.jsonl"


# Token estimation (same heuristic as eval.py: ~1.4 tokens per word, ~4 chars per token)
def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def classify_bash_command(command: str) -> str:
    """Classify a bash command into categories for analysis."""
    cmd = command.strip().lower()
    if cmd.startswith(("git ", "gh ")):
        return "git"
    if cmd.startswith(("docker ", "docker-compose")):
        return "docker"
    if cmd.startswith(
        ("pytest", "python -m pytest", "npm test", "cargo test", "go test")
    ):
        return "test"
    if cmd.startswith(("ruff ", "eslint", "mypy", "clippy")):
        return "lint"
    if cmd.startswith(("ssh ", "scp ", "rsync")):
        return "ssh"
    if cmd.startswith(("curl ", "wget ")):
        return "http"
    if cmd.startswith(("pip ", "npm ", "yarn ", "cargo ", "apt")):
        return "package"
    if cmd.startswith(("ls ", "find ", "tree", "dir ")):
        return "filesystem"
    if cmd.startswith(("cat ", "head ", "tail ", "wc ")):
        return "read"
    if cmd.startswith(("python", "node ", "ruby ", "bash ")):
        return "script"
    return "other"


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name", data.get("toolName", "unknown"))
    tool_input = data.get("tool_input", data.get("input", {}))
    tool_output = data.get("tool_output", data.get("output", ""))
    session_id = data.get("session_id", "unknown")

    # Serialize input for token estimation
    if isinstance(tool_input, dict):
        input_str = json.dumps(tool_input, ensure_ascii=False)
    else:
        input_str = str(tool_input)

    if isinstance(tool_output, dict):
        output_str = json.dumps(tool_output, ensure_ascii=False)
    else:
        output_str = str(tool_output)

    input_tokens = estimate_tokens(input_str)
    output_tokens = estimate_tokens(output_str)
    total_tokens = input_tokens + output_tokens

    # Extract useful metadata per tool type
    meta = {}
    if tool_name == "Bash":
        command = ""
        if isinstance(tool_input, dict):
            command = tool_input.get("command", "")
        elif isinstance(tool_input, str):
            command = tool_input
        meta["command"] = command[:200]
        meta["category"] = classify_bash_command(command)
        meta["output_lines"] = output_str.count("\n") + 1
    elif tool_name == "Read":
        if isinstance(tool_input, dict):
            meta["file"] = tool_input.get("file_path", "")[-80:]
    elif tool_name in ("Grep", "Glob"):
        if isinstance(tool_input, dict):
            meta["pattern"] = str(tool_input.get("pattern", ""))[:100]
    elif tool_name == "Agent":
        if isinstance(tool_input, dict):
            meta["agent_type"] = tool_input.get("subagent_type", "general")[:30]

    # Build audit record
    record = {
        "ts": datetime.now(UTC).isoformat(),
        "session": session_id[:20],
        "tool": tool_name,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "input_bytes": len(input_str),
        "output_bytes": len(output_str),
        **meta,
    }

    # Append to audit log
    try:
        with AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass

    # Rotate at 10MB
    try:
        if AUDIT_FILE.exists() and AUDIT_FILE.stat().st_size > 10 * 1024 * 1024:
            rotated = AUDIT_FILE.with_suffix(f".{int(time.time())}.jsonl")
            AUDIT_FILE.rename(rotated)
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
