#!/usr/bin/env python3
"""Hook: Identity-Sensitive Guard (PreToolUse — Edit/Write)

When editing auth/consent/dsr/audit modules, surface the Identity-Sensitive
Code Checklist (L323) so canonical-form + defensive-reads + sentinel-
reservation invariants don't slip.

Pattern source: L321-L323 (phantom-ai/.claude/knowledge/LEARNINGS.md)
Derived from: DocForge PR #30 Cluster A (6 consent/sentinel/canonical-form
findings: Project:abc vs project:abc, "local" sentinel collision, "system"
fallback, etc.)

Behaviour:
- Triggers on PreToolUse(Edit|Write) for files matching identity-sensitive paths
- Emits checklist as additionalContext
- Does NOT block; informational reminder

Exit 0 + additionalContext.
"""

import json
import re
import sys

HOOK_NAME = "identity_sensitive_guard"

IDENTITY_MODULE_PATTERNS = [
    re.compile(r"/auth/[^/]+\.py$", re.IGNORECASE),
    re.compile(r"/api/auth\.py$", re.IGNORECASE),
    re.compile(r"/api/consent\.py$", re.IGNORECASE),
    re.compile(r"/api/dsr\.py$", re.IGNORECASE),
    re.compile(r"/core/admin_auth\.py$", re.IGNORECASE),
    re.compile(r"/core/audit/[^/]+\.py$", re.IGNORECASE),
    re.compile(r"/compliance/[^/]+\.py$", re.IGNORECASE),
    re.compile(r"/llm_providers?\.py$", re.IGNORECASE),
]

CHECKLIST = (
    "IDENTITY-SENSITIVE EDIT DETECTED -- Auth/Consent/DSR/Audit/Compliance module.\n"
    "Pattern-Checklist (L321-L323):\n"
    "  [ ] L321 -- Auth-gate: explicit `if session is None: raise 401`\n"
    "             (no safe-default helper-return).\n"
    "  [ ] L322 -- Magic-sentinel ('local'/'system'/'anonymous') is in\n"
    "             RESERVED_USERNAMES + rejected at create_user + bootstrap.\n"
    "  [ ] L323 -- Identity-fields canonicalised AT GRANT/STORE TIME\n"
    "             (project:<id> lowercase prefix, username trimmed, etc.)\n"
    "             AND reads are defensive (case-insensitive, type-checked).\n"
    "  [ ] L333 -- update_user mutating role/is_active/password\n"
    "             MUST call delete_sessions_for_user(user_id).\n"
    "  [ ] E202 -- New identity field touches ALL layers in one commit:\n"
    "             Pydantic-models + dataclasses + to_dict + DB-schema +\n"
    "             API-shapes + frontend types.\n"
    "  [ ] L324 -- Helper-refactor: grep ALL callsites BEFORE commit.\n"
    "  [ ] L335 -- After fix: grep replication BEFORE pushing\n"
    "             (Codex iterates -- proactive grep saves review-iterations).\n"
    "Cross-ref: phantom-ai/.claude/knowledge/LEARNINGS.md L321-L335."
)


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    if not file_path:
        sys.exit(0)

    normalized = file_path.replace("\\", "/")
    if not any(p.search(normalized) for p in IDENTITY_MODULE_PATTERNS):
        sys.exit(0)

    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": CHECKLIST,
        }
    }
    print(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
