#!/usr/bin/env python3
"""Promote Corrections — Self-Improvement Loop (P4)

Scans corrections.md for patterns that appear 3+ times.
Suggests promoting them to hard rules.

Inspired by sd0x-dev-flow: Correction -> Lesson -> after 3+ occurrences -> Rule.

Usage:
  python3 promote-corrections.py              # Show promotion candidates
  python3 promote-corrections.py --dry-run    # Same as default (never auto-writes)
  python3 promote-corrections.py --json       # JSON output for hooks
"""

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).parent.parent))
CORRECTIONS_FILE = PLUGIN_ROOT / "self-improving" / "corrections.md"
MEMORY_FILE = PLUGIN_ROOT / "self-improving" / "memory.md"
PROMOTION_THRESHOLD = 3


def extract_correction_patterns(content: str) -> list:
    """Extract correction entries and their categories from corrections.md."""
    corrections = []
    current_id = None
    current_text = []

    for line in content.split("\n"):
        # Match correction headers like "### C-QA01: quality-snapshot.py CWD Bug"
        header = re.match(r"^###\s+(C-\w+):\s+(.+)", line)
        if header:
            if current_id:
                corrections.append(
                    {
                        "id": current_id,
                        "text": " ".join(current_text).strip(),
                    }
                )
            current_id = header.group(1)
            current_text = [header.group(2)]
        elif current_id and line.strip() and not line.startswith("##"):
            current_text.append(line.strip())

    if current_id:
        corrections.append({"id": current_id, "text": " ".join(current_text).strip()})

    return corrections


def categorize_corrections(corrections: list) -> dict:
    """Group corrections by category pattern."""
    categories = Counter()
    category_examples = {}

    # Keyword-based categorization
    CATEGORY_KEYWORDS = {  # noqa: N806 — acts as a module-local constant
        "windows": ["windows", "shell=true", ".cmd", "path separator", "backslash"],
        "subprocess": ["subprocess", "timeout", "process", "cli", "command"],
        "file-io": ["file", "read", "write", "path", "cwd", "directory"],
        "api": ["api", "http", "curl", "endpoint", "auth", "token"],
        "hooks": ["hook", "stdin", "exit", "additionalcontext", "crash"],
        "eval": ["eval", "score", "validate", "frontmatter", "schema"],
        "git": ["git", "commit", "branch", "merge", "push"],
        "docker": ["docker", "container", "service", "swarm", "deploy"],
    }

    for c in corrections:
        text_lower = c["text"].lower()
        matched = False
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                categories[category] += 1
                if category not in category_examples:
                    category_examples[category] = []
                category_examples[category].append(c)
                matched = True
                break
        if not matched:
            categories["other"] += 1

    return {
        "counts": dict(categories),
        "examples": category_examples,
    }


def find_promotion_candidates(categories: dict) -> list:
    """Find categories that appear >= PROMOTION_THRESHOLD times."""
    candidates = []
    for category, count in categories["counts"].items():
        if count >= PROMOTION_THRESHOLD:
            examples = categories["examples"].get(category, [])
            candidates.append(
                {
                    "category": category,
                    "count": count,
                    "examples": [e["id"] for e in examples[:3]],
                    "suggestion": generate_rule_suggestion(category, examples),
                }
            )
    return candidates


def generate_rule_suggestion(category: str, examples: list) -> str:
    """Generate a rule suggestion from correction patterns."""
    suggestions = {
        "windows": "Bei subprocess.run auf Windows IMMER shell=True verwenden. platform.system() checken.",
        "subprocess": "Subprocess-Calls: IMMER timeout setzen. IMMER capture_output=True. IMMER Fehler abfangen.",
        "file-io": "Datei-Operationen: IMMER CWD pruefen. IMMER Path-Objekte statt Strings. IMMER encoding='utf-8'.",
        "api": "API-Calls: IMMER connect_timeout setzen. IMMER Fehler-Response pruefen. IMMER Retry-Logic.",
        "hooks": "Hooks: MUESSEN exit 0 als Default. MUESSEN stdin-Parsing in try/except. DUERFEN nie blocken.",
        "eval": "Eval/Validate: IMMER von der richtigen CWD ausfuehren. IMMER JSON-Output validieren.",
        "git": "Git: IMMER spezifische Files stagen. NIE git add -A. IMMER Lint vor Commit.",
        "docker": "Docker: IMMER Health-Check nach Deploy. IMMER Logs pruefen. IMMER Post-Deploy Verification.",
    }
    return suggestions.get(
        category, f"Pattern '{category}' kam {len(examples)}x vor. Regel formulieren."
    )


def main():
    as_json = "--json" in sys.argv

    if not CORRECTIONS_FILE.exists():
        if as_json:
            print(json.dumps({"candidates": [], "total_corrections": 0}))
        else:
            print("corrections.md nicht gefunden.")
        return

    content = CORRECTIONS_FILE.read_text(encoding="utf-8")
    corrections = extract_correction_patterns(content)
    categories = categorize_corrections(corrections)
    candidates = find_promotion_candidates(categories)

    if as_json:
        print(
            json.dumps(
                {
                    "total_corrections": len(corrections),
                    "categories": categories["counts"],
                    "promotion_candidates": candidates,
                    "threshold": PROMOTION_THRESHOLD,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    print("Correction Promotion Analysis")
    print(f"{'=' * 50}")
    print(f"Total corrections: {len(corrections)}")
    print(f"Promotion threshold: {PROMOTION_THRESHOLD}+ occurrences")
    print()

    print("Categories:")
    for cat, count in sorted(categories["counts"].items(), key=lambda x: -x[1]):
        marker = " ** PROMOTE **" if count >= PROMOTION_THRESHOLD else ""
        print(f"  {cat:15s} {count:3d}{marker}")

    if candidates:
        print(f"\nPromotion Candidates ({len(candidates)}):")
        for c in candidates:
            print(f"\n  [{c['category']}] ({c['count']}x)")
            print(f"  Examples: {', '.join(c['examples'])}")
            print(f"  Suggested Rule: {c['suggestion']}")
    else:
        print(
            f"\nKeine Promotion-Kandidaten (kein Pattern mit {PROMOTION_THRESHOLD}+ Vorkommen)."
        )


if __name__ == "__main__":
    main()
