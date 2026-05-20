#!/usr/bin/env python3
"""Hook: Webhook Stale Detection (PreToolUse — Bash)

Detects when `gh run view <id>` or `gh api .../actions/runs/<id>` is about to
investigate a CI run on a STALE commit (i.e. a SHA that's not HEAD or a
recent ancestor). In webhook-heavy sessions (DocForge PR #30: 40-60% of
events were stale) this guard saves 5-10 min per stale-investigation.

Pattern source: L328 (phantom-ai/.claude/knowledge/LEARNINGS.md)
Derived from: DocForge PR #30 final hardening (2026-05-20)

Behaviour:
- Triggers on `gh run view <id>` / `gh api repos/.../actions/runs/<id>`
- Resolves headSha via `gh run view <id> --json headSha`
- Compares against `git rev-parse HEAD`
- If headSha is in recent log but != HEAD: WARN with stale marker
- If headSha is unknown (not in last 50 commits): inform "very old"
- If headSha == HEAD: silent pass

Exit 0 + additionalContext. NEVER blocks (user may legitimately want to
inspect an old run; we just flag it).
"""

import json
import re
import subprocess
import sys

HOOK_NAME = "webhook_stale_detect"

# Detect gh-cli calls that load a specific run by ID
RUN_ID_PATTERNS = [
    re.compile(r"\bgh\s+run\s+(?:view|rerun|watch|cancel)\s+(\d{8,})", re.IGNORECASE),
    re.compile(r"\bgh\s+api\s+\S*?actions/(?:runs|jobs)/(\d{8,})", re.IGNORECASE),
]


def _git(args):
    try:
        out = subprocess.check_output(
            ["git"] + args, stderr=subprocess.DEVNULL, text=True, timeout=5
        )
        return out.strip()
    except Exception:
        return ""


def _gh_head_sha(run_id):
    try:
        out = subprocess.check_output(
            ["gh", "run", "view", run_id, "--json", "headSha", "-q", ".headSha"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=10,
        )
        return out.strip()
    except Exception:
        return ""


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    if not command:
        sys.exit(0)

    # Find run ID in command
    run_id = None
    for pat in RUN_ID_PATTERNS:
        m = pat.search(command)
        if m:
            run_id = m.group(1)
            break
    if not run_id:
        sys.exit(0)

    head_sha = _git(["rev-parse", "HEAD"])
    if not head_sha:
        sys.exit(0)

    run_sha = _gh_head_sha(run_id)
    if not run_sha:
        # gh failed or no access; don't block, don't warn
        sys.exit(0)

    # Compare full SHAs
    if run_sha == head_sha:
        # fresh run — no warning needed
        sys.exit(0)

    # Stale: check how far back
    recent = _git(["log", "--format=%H", "-50"])
    recent_shas = set(recent.split("\n")) if recent else set()
    short_run = run_sha[:7]
    short_head = head_sha[:7]
    if run_sha in recent_shas:
        # Stale but within last 50 commits
        ancestor_pos = recent.split("\n").index(run_sha) if run_sha in recent.split("\n") else -1
        msg = (
            f"WEBHOOK-STALE-DETECT: run {run_id} is on commit {short_run} "
            f"(HEAD={short_head}, {ancestor_pos} commit(s) behind). "
            "Likely a pre-fix CI event whose failures have since been "
            "addressed. Verify with: `git log --oneline HEAD~"
            f"{ancestor_pos + 2}..HEAD` to see if the failure was already "
            "resolved before investigating."
        )
    else:
        msg = (
            f"WEBHOOK-STALE-DETECT: run {run_id} is on commit {short_run} "
            f"which is NOT in the last 50 commits of this branch "
            f"(HEAD={short_head}). Very old or different branch. "
            "Investigate cautiously."
        )

    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": msg,
        }
    }
    print(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
