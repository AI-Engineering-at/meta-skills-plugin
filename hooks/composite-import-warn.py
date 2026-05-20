#!/usr/bin/env python3
"""Hook: Composite-Import Try-Except Warn (PostToolUse — Edit/Write)

Detects the `try: import A, B, C; ... except: log` anti-pattern in
main.py / app.py / __init__.py / router-registration files. One failing
import kills all dependent registrations silently -- the E207 class.

Pattern source: Anti-Pattern C from session-analyst output
(phantom-ai/.claude/knowledge/LEARNINGS.md L326)
Derived from: DocForge PR #30 main.py:370 (auth+dsr+consent one-shot import)

Behaviour:
- Triggers on PostToolUse(Edit|Write) for files matching:
  main.py, app.py, __init__.py, *_router.py, *_routes.py
- Searches for `try:` blocks containing >=2 `from app.api import X`
  or `import` statements with a broad `except` swallowing them
- Warns with file:line + suggested per-module loop pattern

Exit 0 + additionalContext. Informational.
"""

import json
import re
import sys
from pathlib import Path

HOOK_NAME = "composite_import_warn"

TRIGGER_FILES = re.compile(
    r"/(?:main|app|__init__|[\w-]+_router(?:s)?|[\w-]+_routes)\.py$",
    re.IGNORECASE,
)
TRY_HEADER = re.compile(r'^(\s*)try\s*:\s*$')
IMPORT_LINE = re.compile(r'^\s+(?:from\s+\S+\s+import\s+|import\s+)')
EXCEPT_HEADER = re.compile(r'^(\s*)except')


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
    if not TRIGGER_FILES.search(normalized):
        sys.exit(0)

    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        sys.exit(0)

    lines = content.splitlines()
    hits = []
    i = 0
    while i < len(lines):
        m = TRY_HEADER.match(lines[i])
        if not m:
            i += 1
            continue
        indent = m.group(1)
        # Walk through try-block body counting imports
        import_count = 0
        body_idx = i + 1
        while body_idx < len(lines):
            bl = lines[body_idx]
            if not bl.strip():
                body_idx += 1
                continue
            # Outside the try-block? (less indent than body, but check for except)
            if EXCEPT_HEADER.match(bl):
                em = EXCEPT_HEADER.match(bl)
                if em and em.group(1) == indent:
                    # Found except at same level — count imports
                    if import_count >= 2:
                        hits.append(f"  L{i+1}: composite try wraps {import_count} imports + except at L{body_idx+1}")
                    break
            if IMPORT_LINE.match(bl):
                import_count += 1
            body_idx += 1
        i = body_idx + 1
        if len(hits) >= 3:
            break

    if not hits:
        sys.exit(0)

    msg = (
        f"COMPOSITE-IMPORT-TRY (L326, E207-class) in {Path(file_path).name}:\n"
        + "\n".join(hits)
        + "\n\nOne failing import kills ALL dependent registrations silent.\n"
        "Refactor to per-module loop:\n\n"
        "  for spec in [('auth', '/api/auth', 'Auth'), ('dsr', '/api/dsr', 'DSR'), ...]:\n"
        "      try:\n"
        "          mod = __import__(f'app.api.{spec[0]}', fromlist=['router'])\n"
        "          app.include_router(mod.router, prefix=spec[1], tags=[spec[2]])\n"
        "      except Exception as exc:\n"
        "          logger.error('Failed to register %s: %s', spec[0], exc)\n\n"
        "Identity-critical routes (auth/dsr/consent/audit) should ERROR-log,\n"
        "not warning -- they're launch-blockers if missing."
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
