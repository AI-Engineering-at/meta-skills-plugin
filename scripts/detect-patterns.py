#!/usr/bin/env python3
"""Detect repeated patterns from session analysis and suggest skills.

Usage:
  python analyze-sessions.py | python detect-patterns.py
  python detect-patterns.py < analysis.json
  python detect-patterns.py --file analysis.json

Output: JSON with top suggestions (type, description, confidence, reason).
"""

import json
import sys
from pathlib import Path


def detect(data: dict) -> list[dict]:
    """Apply heuristics to find skill-worthy patterns."""
    suggestions = []

    # H1: Repeated bash commands → automation skill
    for cmd, count in data.get("repeated_commands", {}).items():
        if count >= 3:
            suggestions.append({
                "type": "automation",
                "description": f"Automate '{cmd}' (executed {count}x across sessions)",
                "confidence": min(0.9, 0.5 + count * 0.1),
                "reason": f"Bash pattern '{cmd}' repeated {count}x — candidate for a Bash-wrapping skill",
                "suggested_name": cmd.replace(" ", "-").replace("/", "-")[:30],
            })

    # H2: Files accessed across multiple sessions → context skill
    for filepath, session_count in data.get("top_files", {}).items():
        if session_count >= 3:
            name = Path(filepath).stem
            suggestions.append({
                "type": "context",
                "description": f"Quick-access for '{name}' (read in {session_count} sessions)",
                "confidence": min(0.8, 0.4 + session_count * 0.1),
                "reason": f"File '{filepath}' accessed in {session_count} sessions — context skill candidate",
                "suggested_name": f"read-{name}"[:30],
            })

    # H3: High correction rate → debugging/process skill
    total_turns = data.get("total_turns", 0)
    corrections = data.get("total_corrections", 0)
    if total_turns > 10 and corrections / total_turns > 0.15:
        suggestions.append({
            "type": "process",
            "description": f"High correction rate ({corrections}/{total_turns} turns = {corrections/total_turns:.0%}) — review workflow",
            "confidence": 0.6,
            "reason": "Frequent corrections suggest unclear instructions or missing context — meta:feedback or a checklist skill could help",
            "suggested_name": "pre-check",
        })

    # H4: Skill sequences → workflow candidate (v2.0 meta:flow prep)
    sequences = data.get("skill_sequences", [])
    if len(sequences) >= 2:
        # Find common subsequences
        from collections import Counter
        seq_strs = [" → ".join(s) for s in sequences if len(s) >= 2]
        seq_counts = Counter(seq_strs)
        for seq_str, count in seq_counts.most_common(3):
            if count >= 2:
                suggestions.append({
                    "type": "workflow",
                    "description": f"Workflow detected: {seq_str} (repeated {count}x)",
                    "confidence": min(0.85, 0.5 + count * 0.15),
                    "reason": f"Skill sequence '{seq_str}' repeated across sessions — meta:flow candidate",
                    "suggested_name": "flow-" + seq_str.split(" → ")[0][:20],
                })

    # H5: Underutilized tools → knowledge gap (low confidence suggestion)
    tools = data.get("top_tools", {})
    if tools.get("Bash", 0) > 20 and tools.get("Grep", 0) < 3:
        suggestions.append({
            "type": "knowledge",
            "description": "Heavy Bash usage, low Grep — custom search skill could help",
            "confidence": 0.4,
            "reason": "Using Bash for searches that Grep handles more efficiently",
            "suggested_name": "search-helper",
        })

    # Sort by confidence descending
    suggestions.sort(key=lambda x: x["confidence"], reverse=True)
    return suggestions[:5]  # Top 5


def main():
    # Read from stdin or file
    if len(sys.argv) > 2 and sys.argv[1] == "--file":
        with open(sys.argv[2]) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    suggestions = detect(data)

    output = {
        "sessions_analyzed": data.get("sessions_analyzed", 0),
        "suggestions": suggestions,
        "suggestion_count": len(suggestions),
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
