#!/usr/bin/env python3
"""Setup script for /meta-loop command.

Creates .claude/meta-loop.local.md state file with configured gates.
The meta-loop-stop.py hook reads this file to decide whether to block exit.

Usage:
  python3 setup-meta-loop.py "task prompt" --gates ruff,pytest --max-iterations 10
  python3 setup-meta-loop.py "task prompt" --gates "ruff,pytest,eval:80" --max 5
"""
import argparse
import contextlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


def find_claude_dir() -> Path:
    """Find or create .claude/ directory in project root."""
    cwd = Path.cwd()
    # Check for existing .claude/
    for d in [cwd, *list(cwd.parents)[:5]]:
        if (d / ".claude").is_dir():
            return d / ".claude"
    # Create in CWD
    claude_dir = cwd / ".claude"
    claude_dir.mkdir(exist_ok=True)
    return claude_dir


def parse_gates(gates_str: str) -> list:
    """Parse comma-separated gate definitions.

    Formats:
      ruff           → {type: command, cmd: "ruff check .", name: ruff}
      pytest         → {type: command, cmd: "pytest -x -q", name: pytest}
      eslint         → {type: command, cmd: "npm run lint", name: eslint}
      build          → {type: command, cmd: "npm run build", name: build}
      eval           → {type: eval, min_score: 70, name: eval}
      eval:80        → {type: eval, min_score: 80, name: eval}
      custom:CMD     → {type: command, cmd: CMD, name: custom}
    """
    PRESETS = {  # noqa: N806 — acts as a module-local constant
        "ruff": {"type": "command", "cmd": "ruff check .", "name": "lint"},
        "pytest": {"type": "command", "cmd": "pytest -x -q", "name": "test"},
        "eslint": {"type": "command", "cmd": "npm run lint", "name": "lint"},
        "build": {"type": "command", "cmd": "npm run build", "name": "build"},
        "mypy": {"type": "command", "cmd": "mypy .", "name": "typecheck"},
        "tsc": {"type": "command", "cmd": "tsc --noEmit", "name": "typecheck"},
    }

    gates = []
    for part in gates_str.split(","):
        part = part.strip()
        if not part:
            continue

        if part.startswith("eval"):
            min_score = 70
            if ":" in part:
                _, _, score_str = part.partition(":")
                with contextlib.suppress(ValueError):
                    min_score = int(score_str)
            gates.append({"type": "eval", "min_score": min_score, "name": "eval"})
        elif part.startswith("custom:"):
            cmd = part[7:]
            gates.append({"type": "command", "cmd": cmd, "name": "custom"})
        elif part in PRESETS:
            gates.append(PRESETS[part].copy())
        else:
            # Treat as raw command
            gates.append({"type": "command", "cmd": part, "name": part})

    return gates


def check_ralph_loop(claude_dir: Path) -> bool:
    """Check if a ralph-loop is already active."""
    ralph_state = claude_dir / "ralph-loop.local.md"
    return ralph_state.exists()


def main():
    parser = argparse.ArgumentParser(description="Setup meta-loop")
    parser.add_argument("prompt", nargs="?", default="", help="Task prompt")
    parser.add_argument("--gates", "-g", required=True, help="Comma-separated gates: ruff,pytest,eval:80")
    parser.add_argument("--max-iterations", "--max", "-m", type=int, default=10, help="Max iterations (default: 10)")
    parser.add_argument("--session-id", "-s", default="", help="Session ID for isolation")

    args = parser.parse_args()

    if not args.prompt:
        print("ERROR: Task prompt required. Usage: /meta-loop \"Fix all lint errors\" --gates ruff,pytest")
        sys.exit(1)

    claude_dir = find_claude_dir()

    # Check for active ralph-loop
    if check_ralph_loop(claude_dir):
        print("WARNING: ralph-loop already active (.claude/ralph-loop.local.md exists). "
              "Running both simultaneously is not recommended. Cancel ralph first with /cancel-ralph.")
        sys.exit(1)

    # Check for existing meta-loop
    state_file = claude_dir / "meta-loop.local.md"
    if state_file.exists():
        print("WARNING: meta-loop already active. Cancel with /cancel-meta-loop first.")
        sys.exit(1)

    gates = parse_gates(args.gates)
    if not gates:
        print("ERROR: No valid gates found. Use: --gates ruff,pytest,eval:80")
        sys.exit(1)

    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build gates YAML
    gates_yaml = ""
    for g in gates:
        gates_yaml += f'  - {json.dumps(g, ensure_ascii=False)}\n'

    # Write state file
    content = f"""---
active: true
iteration: 1
max_iterations: {args.max_iterations}
session_id: {args.session_id}
started_at: {now}
gates:
{gates_yaml}---

{args.prompt}
"""
    state_file.write_text(content, encoding="utf-8")

    # Report
    gate_names = [g["name"] for g in gates]
    print("Meta-Loop ACTIVATED")
    print(f"  Gates: {', '.join(gate_names)}")
    print(f"  Max iterations: {args.max_iterations}")
    print(f"  State file: {state_file}")
    print("  Cancel with: /cancel-meta-loop")
    print("")
    print("Session will not end until ALL gates pass.")
    print(f"Now work on: {args.prompt[:200]}")


if __name__ == "__main__":
    main()
