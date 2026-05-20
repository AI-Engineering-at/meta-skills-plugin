#!/usr/bin/env python3
"""Hook: Bulk-Edit Verification (PostToolUse — Edit)

After an Edit completes on a >500-LoC file, if the edited `new_string`
contains a recognizable "fix-marker" (e.g. a new comment-block, a new
function call, or a new error-type), grep the rest of the file to see
if the same pattern was supposed to apply elsewhere. Catches the
"pattern bulk-edit landed at the wrong block" anti-pattern.

Pattern source: L334 from DocForge PR #30 session-analyst.
Derived from: PR #30 IDOR-Gate landed on preview-block instead of
export-block because both had `state = _get_e2e_fixture_state(...)`.

Behaviour:
- Triggers on PostToolUse(Edit) only (not Write -- bulk-edit semantics)
- Reads the file post-edit
- If file > 500 LoC AND the new_string contains an audit-marker
  (`SEC-P1`, `AUDIT-`, `Codex P1`, `# fix:`, `_owner_can_see_job(`)
  searches for similar-pattern blocks (`state = _get_e2e_fixture_state`,
  `state = get_job_state`, etc) elsewhere in the file
- If found, warn "verify all matching blocks were patched"

Exit 0 + additionalContext.
"""

import json
import re
import sys
from pathlib import Path

HOOK_NAME = "bulk_edit_verify"

# Audit-fix-marker patterns that suggest this is a security/audit fix
AUDIT_MARKERS = [
    re.compile(r'AUDIT-\d{4}-\d{2}-\d{2}', re.IGNORECASE),
    re.compile(r'\bSEC-P[12]', re.IGNORECASE),
    re.compile(r'Codex\s+P[12]', re.IGNORECASE),
    re.compile(r'_owner_can_see_job\s*\('),
    re.compile(r'fail-closed', re.IGNORECASE),
    re.compile(r'fail-loud', re.IGNORECASE),
]

# Patterns that often repeat in larger files (state-loading, validation)
REPEAT_PATTERNS = [
    re.compile(r'\bstate\s*=\s*_get_e2e_fixture_state\s*\('),
    re.compile(r'\bstate\s*=\s*get_job_state\s*\('),
    re.compile(r'\bif\s+not\s+state\s*:'),
    re.compile(r'\braise\s+HTTPException\s*\(\s*status_code\s*=\s*404'),
    re.compile(r'\bvalidate_registry_file_access\s*\('),
]


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name != "Edit":
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    new_string = tool_input.get("new_string", "")
    if not file_path or not new_string:
        sys.exit(0)

    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        sys.exit(0)

    line_count = content.count("\n") + 1
    if line_count < 500:
        sys.exit(0)  # only meaningful on large files

    # Did this edit contain an audit-marker? (= likely security fix)
    has_marker = any(p.search(new_string) for p in AUDIT_MARKERS)
    if not has_marker:
        sys.exit(0)

    # Find repeat-patterns elsewhere in the file
    repeat_hits = {}
    for pat in REPEAT_PATTERNS:
        matches = list(pat.finditer(content))
        if len(matches) >= 2:
            # Multiple instances of same pattern -- bulk-edit target
            label = pat.pattern[:60]
            line_nums = []
            for m in matches:
                line_no = content[:m.start()].count("\n") + 1
                line_nums.append(line_no)
            repeat_hits[label] = line_nums

    if not repeat_hits:
        sys.exit(0)

    lines_out = [
        f"BULK-EDIT-VERIFY (L334) in {Path(file_path).name} ({line_count} LoC):",
        "Detected audit-fix marker in this Edit. Similar code-patterns appear "
        "multiple times in the file -- verify all instances were patched:",
        "",
    ]
    for label, lns in list(repeat_hits.items())[:3]:
        lines_out.append(f"  {label!r}:")
        lines_out.append(f"    {len(lns)} occurrences at lines: {lns[:10]}")
    lines_out.extend([
        "",
        "Verification: `grep '<fix-marker>' <file> | wc -l` -- count must "
        "match the number of intended fix-sites.",
        "Pre-fix experience (PR #30 E212): IDOR-Gate landed at preview-block "
        "instead of export-block. Codex caught it on next review.",
    ])
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "\n".join(lines_out),
        }
    }
    print(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
