#!/usr/bin/env python3
"""Hook: Silent-Except Lint (PostToolUse — Edit/Write)

Detects the `except: pass` / `except <broad>: <silent>` anti-pattern in
Python files post-edit. 3 of 13 Codex findings in DocForge PR #30 traced
back to this class (E207-class: silent cascade-failures masquerading as
graceful degradation).

Pattern source: Anti-Pattern A from session-analyst output
(phantom-ai/.claude/knowledge/LEARNINGS.md L326)
Derived from: DocForge PR #30 (E207 + E210 + DSR partial-failure)

Behaviour:
- Triggers on PostToolUse(Edit|Write) for *.py files
- Searches for `except (...): pass|continue|return|...` patterns
  WITHOUT a `logger.` call in the next 3 lines and WITHOUT a
  `# SECURITY-INVARIANT:` or `# noqa: BLE001` comment
- Warns with file:line list + suggested fix

Exit 0 + additionalContext. Informational; never blocks (some silent
excepts ARE intentional — e.g. cleanup-paths or hooks themselves).
"""

import json
import re
import sys
from pathlib import Path

HOOK_NAME = "silent_except_lint"

# Hook-validator P0 fix 2026-05-20: pre-fix required `\s+` after `except`,
# which FAILED to match bare `except:` -- the WORST-CASE pattern this hook
# is supposed to catch. Now `\s*` so bare except matches too.
EXCEPT_LINE = re.compile(
    r'^(\s*)except(?:\s+(?:\w+(?:\s*,\s*\w+)*|\([^)]+\)))?(?:\s+as\s+\w+)?\s*:\s*(.*)$'
)
SILENT_BODY_INLINE = re.compile(r'^(?:pass|continue|return(?:\s|$)|\.\.\.)')


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
    if not file_path or not file_path.endswith(".py"):
        sys.exit(0)

    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        sys.exit(0)

    lines = content.splitlines()
    hits = []
    for idx, line in enumerate(lines):
        m = EXCEPT_LINE.match(line)
        if not m:
            continue
        indent = m.group(1)
        inline_body = m.group(2).strip()

        # Allowlist: explicit invariant marker means the silent-except is documented
        if (
            "# SECURITY-INVARIANT:" in line
            or "# noqa: BLE001" in line
            or "# best-effort" in line.lower()
            or "# safe-silent" in line.lower()
        ):
            continue

        # Detect silent body — either inline (e.g. `except Foo: pass`) or
        # on next line(s) with no `logger.` call within 3 lines.
        silent = False
        if inline_body and SILENT_BODY_INLINE.match(inline_body):
            silent = True
        else:
            # Multi-line body: look at next 1-3 lines
            for body_idx in range(idx + 1, min(idx + 4, len(lines))):
                bl = lines[body_idx].rstrip()
                if not bl.startswith(indent + "    "):
                    break  # outside this except-block
                stripped = bl.strip()
                if not stripped:
                    continue
                if SILENT_BODY_INLINE.match(stripped):
                    # Now check: is there a `logger.` call in the same block?
                    has_log = False
                    for log_idx in range(idx + 1, min(idx + 6, len(lines))):
                        if not lines[log_idx].rstrip().startswith(indent + "    "):
                            break
                        if "logger." in lines[log_idx] or "log." in lines[log_idx]:
                            has_log = True
                            break
                    if not has_log:
                        silent = True
                break

        if silent:
            hits.append(f"  L{idx+1}: {line.strip()[:100]}")
            if len(hits) >= 5:
                break

    if not hits:
        sys.exit(0)

    msg = (
        f"SILENT-EXCEPT-LINT (L326, E207-class) in {Path(file_path).name}:\n"
        + "\n".join(hits)
        + "\n\nThis is a Codex-bait pattern. Either:\n"
        '  (a) add `logger.exception(...)` or `logger.warning(...)` to the except body, or\n'
        '  (b) raise a specific exception type (fail-loud) for security-class errors, or\n'
        '  (c) annotate with `# SECURITY-INVARIANT: <reason>` / `# noqa: BLE001`\n'
        "to make the silent-degradation intentional and reviewable."
    )
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        }
    }
    print(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
