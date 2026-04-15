#!/usr/bin/env python3
"""Hook: Stop Validator v3 (Stop event)

Simplified for v4.0: User-facing guidance only.
Backend persistence (Honcho write, state save, diagram regen) moved to
session-end.py (SessionEnd event).

Provides:
1. Uncommitted changes warning
2. Lint status check
3. Documentation reminder
4. open-notebook suggestion for knowledge-relevant changes

Exit 0 + additionalContext. Never hard-blocks.
"""
import json
import os
import sys
from pathlib import Path

# --- Add hooks dir to path for lib import ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.services import get_git_changes_summary
from lib.state import SessionState, STATE_DIR

HOOK_NAME = "stop_validator"

KNOWLEDGE_KEYWORDS = [
    "CLAUDE.md", "rules/", "knowledge/", "LEARNINGS", "ERRORS",
    "STATUS.md", "docs/", "README", "ARCHITECTURE", "AUDIT",
    "services", "deploy", "migration", "config", "infrastructure",
]


def is_knowledge_relevant(summary: str) -> bool:
    summary_lower = summary.lower()
    return any(kw.lower() in summary_lower for kw in KNOWLEDGE_KEYWORDS)


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    session_id = data.get("session_id", "unknown")
    cwd = os.getcwd()

    git_summary = get_git_changes_summary(max_lines=15)

    # --- Verification checks ---
    verification_warnings = []

    # Check for uncommitted changes
    try:
        import subprocess
        diff_result = subprocess.run(
            ["git", "diff", "--stat"], capture_output=True, text=True,
            timeout=5, cwd=cwd,
        )
        staged_result = subprocess.run(
            ["git", "diff", "--cached", "--stat"], capture_output=True, text=True,
            timeout=5, cwd=cwd,
        )
        if diff_result.stdout.strip() or staged_result.stdout.strip():
            verification_warnings.append(
                "UNCOMMITTED CHANGES detected! Commit before ending session?"
            )
    except Exception:
        pass

    # Check lint status from session state
    try:
        state = SessionState(session_id)
        qg = state.get("quality_gate")
        if qg.get("last_lint_result", "NOT_RUN") != "PASS":
            if git_summary:
                py_changed = any(f.endswith(".py") for f in git_summary.split("\n"))
                ts_changed = any(f.endswith((".ts", ".tsx", ".js")) for f in git_summary.split("\n"))
                if py_changed:
                    verification_warnings.append(
                        "Python files changed but lint not PASS this session. "
                        "Rule 05: `ruff check` REQUIRED before commit."
                    )
                if ts_changed:
                    verification_warnings.append(
                        "TypeScript/JS files changed but lint not PASS. "
                        "Rule 05: `npm run lint` REQUIRED before commit."
                    )
    except Exception:
        pass

    # --- Build additionalContext ---
    ctx_parts = ["Session ending. Documentation:"]

    if verification_warnings:
        ctx_parts.append("VERIFICATION: " + " | ".join(verification_warnings))

    ctx_parts.append(
        "Check: (1) Git — all changes committed? "
        "(2) ERPNext — task updated?"
    )

    if git_summary and is_knowledge_relevant(git_summary):
        ctx_parts.append(
            "RECOMMENDATION: Changes affect knowledge-relevant files. "
            "Create an open-notebook source: "
            "curl -s -X POST 'http://10.40.10.82:5055/api/sources/json' "
            "-H 'Content-Type: application/json' "
            "-d '{\"type\":\"text\",\"title\":\"Session YYYY-MM-DD — Topic\","
            "\"content\":\"...\",\"notebooks\":[\"notebook:zkxy9fiwelrolgbr2upc\"],"
            "\"embed\":true}'"
        )

    if git_summary:
        ctx_parts.append(f"Git summary this session:\n{git_summary[:400]}")

    print(json.dumps({"additionalContext": " ".join(ctx_parts)}))
    sys.exit(0)


if __name__ == "__main__":
    main()
