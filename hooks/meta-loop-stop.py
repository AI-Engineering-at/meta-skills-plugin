#!/usr/bin/env python3
"""Hook: Meta-Loop Stop (Stop event)

Intercepts session exit when a meta-loop is active.
Runs objective quality gates (pytest, ruff, eval) to determine completion.
Blocks exit and re-feeds prompt if any gate fails.

Based on Ralph-Loop pattern but with REAL verification instead of text promises.

Output: JSON with decision="block" to prevent exit, or exit 0 to allow.
"""

import contextlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HOOK_NAME = "meta_loop_stop"
PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT", "")


def find_state_file() -> Path | None:
    """Find .claude/meta-loop.local.md in CWD or parents."""
    cwd = Path.cwd()
    for d in [cwd, *list(cwd.parents)[:5]]:
        candidate = d / ".claude" / "meta-loop.local.md"
        if candidate.exists():
            return candidate
    return None


def parse_state(path: Path) -> dict | None:
    """Parse YAML-like frontmatter from state file."""
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return None

    # Split frontmatter and body
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    frontmatter_text = parts[1].strip()
    body = parts[2].strip()

    # Simple YAML-like parser (no pyyaml dependency)
    state = {"_body": body, "_path": str(path)}
    current_list_key = None

    for line in frontmatter_text.split("\n"):
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue

        # List item
        if line.startswith("  - ") and current_list_key:
            item_text = line[4:].strip()
            # Try to parse as inline dict: {key: val, key: val}
            if item_text.startswith("{") and item_text.endswith("}"):
                try:
                    # Convert YAML-like to JSON
                    json_text = item_text.replace("'", '"')
                    item = json.loads(json_text)
                    state[current_list_key].append(item)
                    continue
                except json.JSONDecodeError:
                    pass
            state[current_list_key].append(item_text)
            continue

        # Key-value
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()

            if not val:
                # Start of list
                state[key] = []
                current_list_key = key
            elif val.lower() in ("true", "false"):
                state[key] = val.lower() == "true"
                current_list_key = None
            elif val.isdigit():
                state[key] = int(val)
                current_list_key = None
            else:
                # Remove quotes
                state[key] = val.strip("'\"")
                current_list_key = None

    return state


def run_gate(gate: dict, cwd: str) -> dict:
    """Run a single quality gate. Returns {name, passed, output}."""
    name = gate.get("name", "unknown")
    gate_type = gate.get("type", "command")
    cmd = gate.get("cmd", "")

    if gate_type == "eval":
        # Special: run eval.py and check min_score
        min_score = int(gate.get("min_score", 70))
        eval_script = Path(PLUGIN_ROOT) / "scripts" / "eval.py"
        if not eval_script.exists():
            return {
                "name": name,
                "passed": False,
                "output": f"eval.py not found at {eval_script}",
            }
        cmd = f'{sys.executable} "{eval_script}" --all --json'

    if not cmd:
        return {"name": name, "passed": False, "output": "No command specified"}

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd,
        )

        if gate_type == "eval":
            # Parse eval JSON output for average score
            try:
                eval_data = json.loads(result.stdout)
                scores = [
                    item.get("score", 0) for item in eval_data if isinstance(item, dict)
                ]
                avg = sum(scores) / len(scores) if scores else 0
                passed = avg >= min_score
                return {
                    "name": name,
                    "passed": passed,
                    "output": f"avg={avg:.0f}/{min_score} ({len(scores)} items)",
                }
            except (json.JSONDecodeError, TypeError):
                return {
                    "name": name,
                    "passed": False,
                    "output": f"eval parse error: {result.stdout[:200]}",
                }
        else:
            passed = result.returncode == 0
            output = (result.stdout + result.stderr)[-500:] if not passed else "OK"
            return {"name": name, "passed": passed, "output": output}

    except subprocess.TimeoutExpired:
        return {"name": name, "passed": False, "output": "TIMEOUT (30s)"}
    except Exception as e:
        return {"name": name, "passed": False, "output": str(e)[:200]}


def main():
    # --- Find state file ---
    state_path = find_state_file()
    if state_path is None:
        # No active meta-loop — allow exit
        sys.exit(0)

    # --- Parse state ---
    state = parse_state(state_path)
    if state is None or not state.get("active", False):
        sys.exit(0)

    # --- Session ID check ---
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    current_session = data.get("session_id", "")
    state_session = state.get("session_id", "")
    if state_session and current_session and state_session != current_session:
        # Different session — not our loop
        sys.exit(0)

    # --- Check max iterations ---
    iteration = state.get("iteration", 1)
    max_iter = state.get("max_iterations", 10)
    if max_iter > 0 and iteration > max_iter:
        # Max reached — allow exit, clean up
        with contextlib.suppress(Exception):
            state_path.unlink()
        sys.exit(0)

    # --- Run gates ---
    gates = state.get("gates", [])
    if not gates:
        # No gates configured — allow exit
        with contextlib.suppress(Exception):
            state_path.unlink()
        sys.exit(0)

    cwd = str(Path.cwd())
    results = []
    all_passed = True

    for gate in gates:
        if isinstance(gate, str):
            gate = {"type": "command", "cmd": gate, "name": gate}
        result = run_gate(gate, cwd)
        results.append(result)
        if not result["passed"]:
            all_passed = False

    # --- Build gate summary ---
    gate_summary = ", ".join(
        f"{r['name']}={'PASS' if r['passed'] else 'FAIL'}" for r in results
    )

    # --- All passed? Allow exit ---
    if all_passed:
        with contextlib.suppress(Exception):
            state_path.unlink()
        sys.exit(0)

    # --- Gates failed — block exit, iterate ---
    new_iteration = iteration + 1

    # Update state file
    try:
        content = state_path.read_text(encoding="utf-8")
        content = re.sub(r"iteration:\s*\d+", f"iteration: {new_iteration}", content)
        state_path.write_text(content, encoding="utf-8")
    except Exception:
        pass

    # Build failure details
    failure_details = []
    for r in results:
        if not r["passed"]:
            failure_details.append(f"{r['name']}: {r['output'][:300]}")

    prompt_text = state.get("_body", "Continue fixing issues.")

    system_msg = (
        f"Meta-Loop Iteration {new_iteration}/{max_iter}. "
        f"Gates: {gate_summary}. "
        f"Failures:\n"
        + "\n".join(failure_details)
        + "\n\nFix failing gates before completion."
    )

    # Output block decision
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": prompt_text,
                "systemMessage": system_msg,
            }
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
