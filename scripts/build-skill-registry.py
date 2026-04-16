#!/usr/bin/env python3
"""Build Skill Registry — Generates .claude/skill-registry.md

Scans all meta-skills SKILL.md files and phantom-ai rules to produce
a flat Markdown registry with Compact Rules blocks (5-15 lines each).

Sub-agents receive these blocks as "Project Standards" in their prompts.
This is the FOUNDATION for Skill Resolver, Judgment Day, and SDD.

Usage:
  python3 build-skill-registry.py              # Generate registry
  python3 build-skill-registry.py --check      # Dry-run, show what would be generated
  python3 build-skill-registry.py --json        # JSON output for tooling
"""
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

PLUGIN_ROOT = Path(os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    Path(__file__).parent.parent
))
# phantom-ai root is parent of meta-skills
PHANTOM_ROOT = PLUGIN_ROOT.parent
RULES_DIR = PHANTOM_ROOT / ".claude" / "rules"
SKILLS_DIR = PLUGIN_ROOT / "skills"
OUTPUT_FILE = PHANTOM_ROOT / ".claude" / "skill-registry.md"


def parse_frontmatter(path: Path) -> dict:
    """Parse YAML-like frontmatter from a SKILL.md file."""
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return {}

    if not content.startswith("---"):
        return {}

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}

    fm = {}
    for line in parts[1].strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line and not line.startswith("-") and not line.startswith(" "):
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip("'\"")

    # Extract body first 5 meaningful lines for summary
    body_lines = []
    for line in parts[2].strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("---") and not line.startswith("```"):
            body_lines.append(line)
            if len(body_lines) >= 5:
                break

    fm["_body_summary"] = body_lines
    fm["_path"] = str(path)
    return fm


def extract_triggers(description: str) -> list:
    """Extract trigger words from description field."""
    # Look for "Trigger:" section
    trigger_match = re.search(r"[Tt]rigger:?\s*(.+?)(?:\n|$)", description)
    if trigger_match:
        triggers = [t.strip() for t in trigger_match.group(1).split(",")]
        return [t for t in triggers if t and len(t) > 2]
    return []


def scan_skills() -> list:
    """Scan all SKILL.md files in meta-skills/skills/."""
    skills = []
    if not SKILLS_DIR.exists():
        return skills

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        fm = parse_frontmatter(skill_file)
        if not fm.get("name"):
            continue

        name = fm.get("name", skill_dir.name)
        desc = fm.get("description", "")
        category = fm.get("category", fm.get("type", "general"))
        model = fm.get("model", "sonnet")
        triggers = extract_triggers(desc)

        # Build compact rules from body summary
        body_summary = fm.get("_body_summary", [])
        compact = []
        for line in body_summary[:3]:
            if len(line) > 120:
                line = line[:117] + "..."
            compact.append(f"- {line}")

        skills.append({
            "name": name,
            "category": category,
            "model": model,
            "triggers": triggers,
            "compact_rules": compact,
            "description_short": desc[:200].replace("\n", " ").strip(),
        })

    return skills


def scan_rules() -> list:
    """Scan phantom-ai/.claude/rules/*.md for project rules."""
    rules = []
    if not RULES_DIR.exists():
        return rules

    for rule_file in sorted(RULES_DIR.glob("*.md")):
        try:
            content = rule_file.read_text(encoding="utf-8")
        except Exception:
            continue

        lines = content.strip().split("\n")
        title = ""
        compact = []

        for line in lines:
            line = line.strip()
            if line.startswith("# ") and not title:
                title = line[2:].strip()
                # Remove "— ..." suffix for cleaner names
                if " — " in title:
                    title = title.split(" — ")[0].strip()
                continue
            if line and not line.startswith("#") and not line.startswith("```") and not line.startswith(">") and not line.startswith("---"):
                compact.append(f"- {line[:120]}")
                if len(compact) >= 5:
                    break

        if title and compact:
            # Derive a short ID from filename
            rule_id = rule_file.stem  # e.g., "05-code-conventions"
            rules.append({
                "id": rule_id,
                "title": title,
                "compact_rules": compact,
            })

    return rules


def build_registry(skills: list, rules: list) -> str:
    """Build the full registry Markdown content."""
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Skill Registry",
        f"<!-- auto-generated by build-skill-registry.py | {now} -->",
        "<!-- do not edit manually — re-run the script to update -->",
        "",
        "## Skills",
        "",
    ]

    for s in skills:
        triggers_str = ", ".join(s["triggers"][:8]) if s["triggers"] else "see description"
        lines.append(f"### {s['name']} [{s['category']}]")
        lines.append(f"Trigger: {triggers_str}")
        lines.append(f"Model: {s['model']}")
        for rule in s["compact_rules"]:
            lines.append(rule)
        lines.append("")

    lines.append("## Project Rules")
    lines.append("")

    for r in rules:
        lines.append(f"### {r['title']} (from {r['id']})")
        for rule in r["compact_rules"]:
            lines.append(rule)
        lines.append("")

    # P6: Routing Table (pattern -> skill, zero tokens for routing)
    lines.append("## Routing Table")
    lines.append("<!-- Pattern-match FIRST before using LLM for skill routing -->")
    lines.append("")
    lines.append("| Pattern | Skill | Model |")
    lines.append("|---------|-------|-------|")

    for s in skills:
        triggers = s.get("triggers", [])
        for trigger in triggers[:3]:  # Max 3 patterns per skill
            trigger_clean = trigger.strip().lower()
            if len(trigger_clean) > 3:
                lines.append(f"| {trigger_clean} | {s['name']} | {s['model']} |")

    # Add common task-type patterns
    lines.append("| *.py review | judgment-day | haiku |")
    lines.append("| *.ts review | judgment-day | haiku |")
    lines.append("| lint fix | refactor-loop | sonnet |")
    lines.append("| score improve | refactor-loop | sonnet |")
    lines.append("| parallel tasks | dispatch | sonnet |")
    lines.append("| new skill | creator | sonnet |")
    lines.append("")

    return "\n".join(lines)


def main():
    check_only = "--check" in sys.argv
    as_json = "--json" in sys.argv

    skills = scan_skills()
    rules = scan_rules()

    if as_json:
        print(json.dumps({
            "skills": skills,
            "rules": [{"id": r["id"], "title": r["title"]} for r in rules],
            "total_skills": len(skills),
            "total_rules": len(rules),
        }, indent=2, ensure_ascii=False))
        return

    registry_content = build_registry(skills, rules)

    if check_only:
        print(f"Would generate {OUTPUT_FILE}")
        print(f"Skills: {len(skills)}, Rules: {len(rules)}")
        print(f"Content length: {len(registry_content)} chars")
        print("---")
        print(registry_content[:1000])
        return

    # Write registry
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(registry_content, encoding="utf-8")

    print(f"Skill Registry generated: {OUTPUT_FILE}")
    print(f"  Skills: {len(skills)}")
    print(f"  Rules: {len(rules)}")
    print(f"  Size: {len(registry_content)} chars")


if __name__ == "__main__":
    main()
