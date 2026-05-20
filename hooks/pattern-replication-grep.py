#!/usr/bin/env python3
"""Hook: Pattern Replication Grep (PreToolUse — Edit/Write)

When the user is about to fix a bug-pattern in a security-sensitive file,
this hook proactively greps for the same pattern across the codebase and
warns about replicated instances that the user might want to fix in one
batch instead of waiting for the next Codex review to surface them.

Pattern source: L335 + L331 (phantom-ai/.claude/knowledge/LEARNINGS.md)
Derived from: DocForge PR #30 — X-Forwarded-Proto bug existed in 5 files,
5 separate Codex review iterations to find them all.

Behaviour:
- Triggers on Edit/Write to files matching: auth*.py, *middleware*.py,
  *provider*.py, *security*.py, *consent*.py, *dsr*.py, *_security*.py
- Extracts the `old_string` (for Edit) and looks for distinctive
  multi-token patterns (header.get, ==, sentinel-strings, helper-names)
- If pattern is found in >=2 OTHER files in services/ or frontend/,
  warns with the list of locations.

Exit 0 + additionalContext. NEVER blocks; informational only.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

HOOK_NAME = "pattern_replication_grep"

# File-path triggers
SECURITY_MODULE_PATTERNS = [
    re.compile(r"/auth[^/]*\.py$", re.IGNORECASE),
    re.compile(r"/middleware\.py$", re.IGNORECASE),
    re.compile(r"/main\.py$", re.IGNORECASE),
    re.compile(r"/security[^/]*\.py$", re.IGNORECASE),
    re.compile(r"/consent[^/]*\.py$", re.IGNORECASE),
    re.compile(r"/dsr[^/]*\.py$", re.IGNORECASE),
    re.compile(r"/llm_providers?\.py$", re.IGNORECASE),
    re.compile(r"/dependencies\.py$", re.IGNORECASE),
]

# Patterns worth surfacing (regex-matched against old_string)
HOT_PATTERNS = [
    # Header exact-equality (X-Forwarded-Proto / X-Real-IP)
    (re.compile(r'X-Forwarded-Proto[^"]*"\)\.lower\(\)\s*=='),
     'X-Forwarded-Proto exact-equality (comma-list not handled)'),
    (re.compile(r'\.get\("X-Forwarded-Proto"[^)]*\)\.lower\(\)\s*=='),
     'X-Forwarded-Proto exact-equality (comma-list not handled)'),
    # _extract_token single-candidate
    (re.compile(r'\b_extract_token\s*\('),
     '_extract_token single-candidate (use _extract_candidate_tokens for Bearer+Cookie)'),
    # "system" sentinel fallback in consent path
    (re.compile(r'or\s+"system"'),
     '"system" sentinel fallback (fail-closed instead)'),
    # except: pass with no logging
    (re.compile(r'except\s+\w+(?:\s+as\s+\w+)?:\s*$'),
     'broad except (verify logging/fail-loud in next lines)'),
]


def _ripgrep(pattern_regex):
    """Run rg or grep -r, fall back to Python-side filesystem scan.

    Hook-validator P0 fix 2026-05-20: pre-fix called subprocess with
    rg/grep argv-form which is broken on Windows (no shell). When both
    subprocess paths failed, the hook silently returned [] -- making
    this an effective NO-OP across the entire pattern-replication-guard
    workflow on Windows hosts. Now: subprocess first, Python-fallback
    if both fail. Diagnostic to stderr on subprocess error so silent-
    failure becomes visible.
    """
    # Try rg / grep via subprocess (faster on large repos)
    candidates = [
        ["rg", "-l", "--type", "py", pattern_regex, "services/", "frontend/", "scripts/"],
        ["grep", "-rlE", "--include=*.py", pattern_regex, "services/", "frontend/", "scripts/"],
    ]
    for cmd in candidates:
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10
            )
            if proc.returncode in (0, 1):
                # 0 = match found, 1 = no match (grep convention)
                files = [f.strip() for f in proc.stdout.splitlines() if f.strip()]
                return files[:8]
            # else: returncode > 1 = real error -> diagnostic + try next
            sys.stderr.write(
                f"pattern-replication-grep: {cmd[0]} rc={proc.returncode}: {proc.stderr[:200]}\n"
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            sys.stderr.write(f"pattern-replication-grep: {cmd[0]} unavailable ({exc})\n")
            continue

    # Python-side fallback (slower but cross-platform)
    try:
        prog = re.compile(pattern_regex)
    except re.error:
        return []
    from pathlib import Path as _Path
    hits = []
    for base in ("services", "frontend", "scripts"):
        root = _Path(base)
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            try:
                if prog.search(path.read_text(encoding="utf-8", errors="ignore")):
                    hits.append(str(path).replace("\\", "/"))
                    if len(hits) >= 8:
                        return hits
            except (OSError, UnicodeDecodeError):
                continue
    return hits


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

    # Check if this is a security-sensitive module
    normalized = file_path.replace("\\", "/")
    if not any(p.search(normalized) for p in SECURITY_MODULE_PATTERNS):
        sys.exit(0)

    # Extract patterns from old_string (Edit) or content (Write)
    edit_payload = tool_input.get("old_string") or tool_input.get("content") or ""
    if not edit_payload:
        sys.exit(0)

    warnings = []
    for regex, label in HOT_PATTERNS:
        if regex.search(edit_payload):
            # Find replications
            pattern_str = regex.pattern
            matches = _ripgrep(pattern_str)
            # Filter out the file being edited
            self_basename = Path(file_path).name
            others = [m for m in matches if not m.endswith(self_basename)]
            if others:
                location_list = "\n  - ".join(others)
                warnings.append(
                    f"PATTERN-REPLICATION '{label}' found in {len(others)} other file(s):\n"
                    f"  - {location_list}\n"
                    f"Consider fixing all instances in one commit (L335: Codex iterates -- "
                    f"proactive grep saves 1-3 review-iterations)."
                )

    if not warnings:
        sys.exit(0)

    msg = "\n\n".join(warnings)
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
