#!/usr/bin/env python3
"""Hook: Quality Gate (PostToolUse — Bash)

After every Bash command: detects test/lint/build failures and git commits
without prior lint. Injects corrective context.

Addresses: Buggy Code (37 incidents), Premature Success Declaration.

Exit 0 + additionalContext. Never blocks.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HOOK_NAME = "quality_gate"
STATE_DIR = Path(
    os.environ.get(
        "CLAUDE_PLUGIN_DATA",
        Path.home() / ".claude" / "plugins" / "data" / "meta-skills",
    )
)

# --- Add hooks dir to path for lib import ---
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.state import SessionState  # noqa: E402 — sibling import after path setup

# Load from centralized config
try:
    from lib.config import load_config as _load_config

    _cfg = _load_config()
    CONSECUTIVE_FAILURES_WARN = _cfg.get("thresholds", {}).get(
        "consecutive_failures_warn", 3
    )
    BLOCK_COMMIT = _cfg.get("quality_gate", {}).get("block_commit_on_lint_fail", False)
    BLOCK_PUSH = _cfg.get("quality_gate", {}).get("block_push_on_ci_fail", False)
except Exception:
    CONSECUTIVE_FAILURES_WARN = 3
    BLOCK_COMMIT = False
    BLOCK_PUSH = False

# --- Command classification patterns ---
TEST_PATTERNS = [
    re.compile(r"\bpytest\b", re.IGNORECASE),
    re.compile(r"\bnpm\s+test\b", re.IGNORECASE),
    re.compile(r"\bcargo\s+test\b", re.IGNORECASE),
    re.compile(r"\bgo\s+test\b", re.IGNORECASE),
    re.compile(r"\bvitest\b", re.IGNORECASE),
    re.compile(r"\bjest\b", re.IGNORECASE),
]

LINT_PATTERNS = [
    re.compile(r"\bruff\s+(?:check|format\s+--check)\b", re.IGNORECASE),
    re.compile(r"\beslint\b", re.IGNORECASE),
    re.compile(r"\bnpm\s+run\s+lint\b", re.IGNORECASE),
    re.compile(r"\bmypy\b", re.IGNORECASE),
    re.compile(r"\btsc\s+--noEmit\b", re.IGNORECASE),
]

BUILD_PATTERNS = [
    re.compile(r"\bnpm\s+run\s+build\b", re.IGNORECASE),
    re.compile(r"\bcargo\s+build\b", re.IGNORECASE),
    re.compile(r"\bdocker\s+build\b", re.IGNORECASE),
    re.compile(r"\bgo\s+build\b", re.IGNORECASE),
]

COMMIT_PATTERN = re.compile(r"\bgit\s+commit\b", re.IGNORECASE)

# --- Failure detection in output ---
FAILURE_INDICATORS = [
    re.compile(r"\bFAILED\b"),
    re.compile(r"\bfailed\b"),
    re.compile(r"\berror\b", re.IGNORECASE),
    re.compile(r"\bError:\b"),
    re.compile(r"exit\s+code\s+[1-9]"),
    re.compile(r"FAILURES"),
    re.compile(r"\d+\s+(?:error|failure)s?\s+found", re.IGNORECASE),
]

# --- False positive exclusions for failure detection ---
FAILURE_FALSE_POSITIVES = [
    re.compile(r"0\s+errors?", re.IGNORECASE),
    re.compile(r"no\s+errors?\s+found", re.IGNORECASE),
    re.compile(r"All\s+checks\s+passed", re.IGNORECASE),
    re.compile(r"\bpassed\b.*\b0\s+failed\b", re.IGNORECASE),
]


def classify_command(command: str) -> str:
    """Classify a bash command. Returns: test|lint|build|commit|other."""
    for p in TEST_PATTERNS:
        if p.search(command):
            return "test"
    for p in LINT_PATTERNS:
        if p.search(command):
            return "lint"
    for p in BUILD_PATTERNS:
        if p.search(command):
            return "build"
    if COMMIT_PATTERN.search(command):
        return "commit"
    if re.search(r"\bgit\s+push\b", command, re.IGNORECASE):
        return "push"
    return "other"


def detect_failure(output: str) -> bool:
    """Detect if command output indicates failure.

    Fixed order: check failure indicators FIRST, then false-positives
    only override if the SAME line contains both (e.g. "0 errors found").
    Previous bug: false-positive check ran first and could mask real failures
    from a different tool/line in the same output.
    """
    if not output:
        return False
    # Check if ANY failure indicator exists
    has_failure = False
    for indicator in FAILURE_INDICATORS:
        if indicator.search(output):
            has_failure = True
            break
    if not has_failure:
        return False
    # Failure found — but check if ALL failures are actually false positives
    # Split by lines: a line with "0 errors" is fine, but "FAILED" on another line is real
    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Check if this line has a failure indicator
        line_has_failure = any(ind.search(line) for ind in FAILURE_INDICATORS)
        if not line_has_failure:
            continue
        # This line has a failure — is it a false positive?
        line_is_fp = any(fp.search(line) for fp in FAILURE_FALSE_POSITIVES)
        if not line_is_fp:
            return True  # Real failure on this line
    return False  # All failure-lines were false positives


def check_lint_before_commit(session_id: str) -> bool:
    """Check token-audit.jsonl for lint commands before this commit."""
    audit_log = STATE_DIR / "token-audit.jsonl"
    if not audit_log.exists():
        return False
    try:
        lines = audit_log.read_text(encoding="utf-8").strip().split("\n")[-100:]
        for line in reversed(lines):
            try:
                entry = json.loads(line)
                if entry.get("session") != session_id:
                    continue
                cat = entry.get("category", "")
                if cat in ("lint", "test"):
                    return True
            except (json.JSONDecodeError, KeyError):
                continue
    except Exception:
        pass
    return False


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    tool_output = data.get("tool_output", "")
    session_id = data.get("session_id", "unknown")

    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    output_text = tool_output if isinstance(tool_output, str) else str(tool_output)

    if not command:
        sys.exit(0)

    cmd_type = classify_command(command)

    if cmd_type == "other":
        sys.exit(0)

    session_state = SessionState(session_id)
    state = session_state.get("quality_gate")
    warnings = []

    if cmd_type in ("test", "lint", "build"):
        is_failure = detect_failure(output_text)

        if is_failure:
            state["consecutive_failures"] += 1
            count = state["consecutive_failures"]
            # Track result per type
            if cmd_type == "test":
                state["last_test_result"] = "FAIL"
            elif cmd_type == "lint":
                state["last_lint_result"] = "FAIL"
            warnings.append(
                f"{cmd_type.upper()} FAILED ({count} consecutive). "
                "Fix before continuing. Do not declare success."
            )
            if count >= CONSECUTIVE_FAILURES_WARN and not state["suggested_debugging"]:
                state["suggested_debugging"] = True
                warnings.append(
                    f"{CONSECUTIVE_FAILURES_WARN}+ consecutive failures. Recommendation: "
                    "Use /meta-skills:systematic-debugging for "
                    "systematic root-cause analysis."
                )
        else:
            # Success — reset counter, track result
            state["consecutive_failures"] = 0
            state["suggested_debugging"] = False
            if cmd_type == "test":
                state["last_test_result"] = "PASS"
            elif cmd_type == "lint":
                state["last_lint_result"] = "PASS"

    elif cmd_type == "commit":
        # Check both lint AND test status
        lint_status = state.get("last_lint_result", "NOT_RUN")
        test_status = state.get("last_test_result", "NOT_RUN")

        status_parts = []
        if lint_status != "PASS":
            status_parts.append(f"Lint: {lint_status}")
        if test_status != "PASS":
            status_parts.append(f"Tests: {test_status}")

        if status_parts:
            warnings.append(
                f"GIT COMMIT — {', '.join(status_parts)}. "
                "Rule 05 required: ruff check + pytest BEFORE commit."
            )

        # Commit message format check
        commit_msg_match = re.search(r'git\s+commit\s+-m\s+["\'](.+?)["\']', command)
        if commit_msg_match:
            msg = commit_msg_match.group(1)
            # Check type(scope): description format
            valid_format = re.match(
                r"^(feat|fix|refactor|docs|chore|test|ci|style|perf)\([\w./-]+\):\s+.+",
                msg,
            )
            if not valid_format:
                warnings.append(
                    f"Commit-Message Format: type(scope): description (Rule 17). "
                    f"Aktuell: '{msg[:60]}'"
                )

    elif cmd_type == "push":
        import platform

        is_windows = platform.system() == "Windows"

        # 1. Check last CI run status
        try:
            ci_result = subprocess.run(
                ["gh", "run", "list", "--limit", "1", "--json", "conclusion,name"],
                capture_output=True,
                text=True,
                timeout=10,
                shell=is_windows,
            )
            if ci_result.returncode == 0 and ci_result.stdout.strip():
                ci_runs = json.loads(ci_result.stdout)
                if ci_runs and ci_runs[0].get("conclusion") == "failure":
                    warnings.append(
                        f"PRE-PUSH WARNING: Last CI run FAILED "
                        f"({ci_runs[0].get('name', '?')}). "
                        "Pushing may compound the failure."
                    )
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass

        # 2. Check local lint/test status
        lint_status = state.get("last_lint_result", "NOT_RUN")
        test_status = state.get("last_test_result", "NOT_RUN")
        if lint_status != "PASS":
            warnings.append(
                f"Pre-push: Lint is {lint_status}. Run lint before pushing."
            )
        if test_status != "PASS":
            warnings.append(
                f"Pre-push: Tests are {test_status}. Run tests before pushing."
            )

        # 3. Post-push reminder
        warnings.append(
            "After push: check CI with `gh run list --limit 1` or `/meta-ci`."
        )

    session_state.set("quality_gate", state)
    session_state.save()

    if warnings:
        print(json.dumps({"additionalContext": " | ".join(warnings)}))

    sys.exit(0)


if __name__ == "__main__":
    main()
