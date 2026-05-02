#!/usr/bin/env python3
"""Validate a SKILL.md for AgentSkills.io cross-platform conformance.

Usage:
  python validate-agentskills.py path/to/SKILL.md
  python validate-agentskills.py path/to/SKILL.md --strict

Output: JSON with pass/fail + specific issues.
"""

import json
import re
import sys
from pathlib import Path

SCHEMA_VERSION = 1


def extract_frontmatter(path: Path) -> tuple[dict, str]:
    """Extract frontmatter dict and body text."""
    text = path.read_text(encoding="utf-8", errors="replace")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" in line and not line.startswith("  "):
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip().strip('"').strip("'")
    return meta, parts[2]


def validate(path: Path, strict: bool = False) -> dict:
    """Run all validation checks."""
    issues = []
    warnings = []

    if not path.exists():
        return {"pass": False, "issues": [f"File not found: {path}"], "warnings": []}

    meta, body = extract_frontmatter(path)

    if not meta:
        return {"pass": False, "issues": ["No YAML frontmatter found"], "warnings": []}

    # Required fields
    if not meta.get("name"):
        issues.append("Missing required field: name")
    elif not re.match(r"^[a-z][a-z0-9-]*$", meta["name"]):
        warnings.append(
            f"name '{meta['name']}' should be lowercase-kebab (active verb: deploy-service, not ServiceDeployment)"
        )

    if not meta.get("description"):
        issues.append("Missing required field: description")
    else:
        desc_lines = len(meta["description"].strip().splitlines())
        if desc_lines > 5:
            warnings.append(
                f"Description is {desc_lines} lines (recommend <=3 for token efficiency)"
            )

    if not meta.get("model"):
        warnings.append("No model specified (will use default, may waste tokens)")

    if not meta.get("version"):
        warnings.append("No version specified")

    # Portability checks
    body.lower()

    # Hardcoded absolute paths
    abs_paths = re.findall(r"(?:/home/\w+|/Users/\w+|C:\\Users\\\w+|~/.claude/)", body)
    if abs_paths:
        issues.append(
            f"Hardcoded absolute paths found: {abs_paths[:3]}. Use relative paths or ${{CLAUDE_PLUGIN_ROOT}}"
        )

    # Platform-specific shebangs
    shebangs = re.findall(r"#!(/usr/local/bin/\w+|/bin/\w+)", body)
    for s in shebangs:
        if "/usr/bin/env" not in s:
            warnings.append(f"Non-portable shebang: {s}. Use #!/usr/bin/env python3")

    # Hardcoded tool references that only work in Claude Code
    claude_only = re.findall(
        r"\b(EnterPlanMode|ExitPlanMode|NotebookEdit|TodoWrite)\b", body
    )
    if claude_only:
        warnings.append(
            f"Claude-Code-specific tools used: {claude_only}. May not work in Cursor/ChatGPT"
        )

    # Check for trigger words in description
    desc = meta.get("description", "")
    if not re.search(r"[Tt]rigger|[Uu]se when|[Aa]usloeser", desc):
        warnings.append("No trigger words in description (helps skill routing)")

    # Strict mode: additional checks
    if strict:
        if not meta.get("allowed-tools"):
            issues.append("[strict] Missing allowed-tools field")

        tools_str = meta.get("allowed-tools", "")
        if tools_str.startswith("["):
            tools = [t.strip() for t in tools_str.strip("[]").split(",")]
            if len(tools) > 6:
                warnings.append(
                    f"[strict] {len(tools)} tools — each costs ~200 tokens context. Reduce if possible."
                )

        if not meta.get("user-invocable"):
            warnings.append("[strict] user-invocable not set")

    passed = len(issues) == 0

    return {
        "pass": passed,
        "file": str(path),
        "name": meta.get("name", "unknown"),
        "issues": issues,
        "warnings": warnings,
        "fields_present": list(meta.keys()),
        "body_lines": len(body.strip().splitlines()),
    }


def main():
    try:
        if len(sys.argv) < 2:
            print(
                json.dumps(
                    {
                        "error": "Usage: validate-agentskills.py <SKILL.md> [--strict]",
                        "schema_version": SCHEMA_VERSION,
                    }
                )
            )
            sys.exit(1)

        path = Path(sys.argv[1])
        strict = "--strict" in sys.argv

        result = validate(path, strict)
        result["schema_version"] = SCHEMA_VERSION
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["pass"] else 1)
    except Exception as e:
        print(
            json.dumps(
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "script": Path(__file__).name,
                    "schema_version": SCHEMA_VERSION,
                }
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
