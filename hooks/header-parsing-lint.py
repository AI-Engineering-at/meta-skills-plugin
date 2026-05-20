#!/usr/bin/env python3
"""Hook: HTTP-Header-Parsing Lint (PostToolUse — Edit/Write)

After an edit/write completes on a Python file, check if the NEW content
contains the X-Forwarded-Proto exact-equality anti-pattern (L325, E206).
Multi-proxy chains emit `https,http` as a comma-separated list -- exact
equality compare misses it -> Secure-Cookie + HSTS dropped on legitimate
HTTPS traffic.

Pattern source: L325 / E206 (phantom-ai/.claude/knowledge/{LEARNINGS,ERRORS}.md)
Derived from: DocForge PR #30 -- 5 callsites with identical bug.

Behaviour:
- Triggers on PostToolUse(Edit|Write) for files matching *.py
- Reads the resulting file content (post-edit)
- Searches for the anti-pattern regex
- If found, emits warning with the canonical fix snippet

Exit 0 + additionalContext. Informational; never blocks (the bug may
already be intentionally documented as legacy / mitigated elsewhere).
"""

import json
import re
import sys
from pathlib import Path

HOOK_NAME = "header_parsing_lint"

# The anti-pattern: exact-equality on X-Forwarded-* header
ANTI_PATTERNS = [
    re.compile(
        r'\.get\(\s*["\']X-Forwarded-(?:Proto|For|Host|Port|Prefix|Scheme)["\']'
        r'\s*,?\s*["\']?[^)]*\)\s*\.\s*lower\(\)\s*==\s*["\']\w+["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'\.get\(\s*["\']X-Forwarded-(?:Proto|For|Host|Port|Prefix|Scheme)["\']'
        r'\s*,?\s*["\']?[^)]*\)\s*==\s*["\']\w+["\']',
        re.IGNORECASE,
    ),
]

FIX_SNIPPET = """    # Forwarded-Header may be comma-separated in multi-proxy chains:
    forwarded_raw = request.headers.get("X-Forwarded-Proto", "")
    forwarded = forwarded_raw.split(",")[0].strip().lower()
    # ... compare forwarded == "https" instead of the raw header"""


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

    hits = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        for pat in ANTI_PATTERNS:
            if pat.search(line):
                # Skip if already inside a comment or docstring (rough heuristic)
                stripped = line.lstrip()
                if stripped.startswith(("#", '"""', "'''", "//")):
                    continue
                hits.append(f"  L{line_no}: {line.strip()[:120]}")
                break

    if not hits:
        sys.exit(0)

    msg = (
        "HEADER-PARSING-LINT (L325/E206): X-Forwarded-* header compared with "
        "exact-equality. Multi-proxy chains (CDN -> ingress -> nginx) emit "
        "comma-separated values (e.g. 'https,http') -- exact compare fails.\n"
        f"Hits in {Path(file_path).name}:\n"
        + "\n".join(hits)
        + "\n\nFix pattern:\n"
        + FIX_SNIPPET
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
