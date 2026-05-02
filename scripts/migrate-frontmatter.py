#!/usr/bin/env python3
"""migrate-frontmatter.py — Add complexity field to all Skills and Agents.

Based on Rule A5 (23-agent-architecture.md):
  skill  = ONE process, ONE focused thing
  agent  = WORKFLOW — multiple steps SEQUENTIALLY
  team   = PARALLEL — multiple agents SIMULTANEOUSLY

Usage:
  python migrate-frontmatter.py --dry-run    # Show what would change
  python migrate-frontmatter.py --apply      # Apply changes
"""

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).parent.parent.parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"

# --- GROUND TRUTH: Human-reviewed complexity assignments ---
# Based on Meta-Engine Unified Plan + Rule A5 + Calibration review

COMPLEXITY_MAP = {
    # === Skills (.claude/skills/) — complexity: skill (single process) ===
    "deploy": "skill",  # SCP+Build+Update = 1 deploy process
    "agent-vault": "skill",  # Get credential = 1 process
    "agent-task": "skill",  # Manage task = 1 process
    "echo-log-learning": "skill",  # Send learning = 1 process
    "skill-router": "skill",  # Route request = 1 process
    "docs-navigator": "skill",  # Find docs = 1 process
    "red-team-analysis": "skill",  # Analyze text = 1 process
    "paperclip-mcp": "skill",  # API call = 1 process
    "design": "skill",  # Start dashboard = 1 process
    "openclaw-ops": "skill",  # Operate gateway = 1 process
    "openclaw-setup": "skill",  # Setup gateway = 1 process (deprecated)
    "delegate-task": "skill",  # Delegate = 1 process
    "echo-log-context": "skill",  # Stack snapshot = 1 process
    "kroki-diagrams": "skill",  # Generate diagram = 1 process
    "version-bump": "skill",  # Bump version = 1 process
    "turboquant-benchmark": "skill",  # Run benchmark = 1 process
    "big-reflect": "skill",  # Deep reflection = 1 process
    "doc-updater": "skill",  # Update docs = 1 process
    "feedback": "skill",  # Quick feedback = 1 process
    # === Skills (.claude/skills/) — complexity: agent (workflow, user dialog) ===
    "feedback-loop": "agent",  # Analyse -> Generate -> User review -> Persist -> Summary
    "creator": "agent",  # Phase 0-5: Check -> Position -> Build -> Write -> Reflect
    "n8n-workflow-ops": "agent",  # Key -> Fetch -> Modify -> PUT -> Verify
    "pve-operations": "agent",  # Check -> Plan -> Execute -> Verify
    "jim-manager": "agent",  # Scan -> Delegate -> Track
    "swarm-recovery": "agent",  # Diagnose -> Recover -> Verify
    "swarm-raft-recovery": "agent",  # Diagnose -> Recover -> Verify
    "full-sync": "agent",  # 10-step pipeline
    "dr-recovery": "agent",  # Diagnose -> Backup -> Recovery -> Verify -> Document
    "ollama-benchmark": "agent",  # Models -> Tests -> Analyse -> Report
    "hf-publish": "agent",  # Format -> Upload -> Verify -> Document
    # === Skills (.claude/skills/) — complexity: team (parallel) ===
    "war-consul": "team",  # 15 consul-agents parallel -> richter consolidates
    # === Agents (.claude/agents/) — complexity: skill (single process, autonomous) ===
    "ha-check": "skill",  # Check HA = 1 process
    "backup-check": "skill",  # Check backups = 1 process
    "infra-check": "skill",  # Check infra = 1 process
    "n8n-audit": "skill",  # Audit n8n = 1 process
    "dashboard-verifier": "skill",  # Verify dashboard = 1 process
    "audit-report": "skill",  # Generate report = 1 process
    "gap-check": "skill",  # Find gaps = 1 process
    "doc-generator": "skill",  # Generate docs = 1 process
    "integration-tester": "skill",  # Test skills = 1 process
    "skill-auditor": "skill",  # Audit skills = 1 process
    "security-reviewer": "skill",  # Review security = 1 process
    "session-analyst": "skill",  # Analyze session = 1 process
    "red-team-reviewer": "skill",  # Review for abuse = 1 process
    # === Agents (.claude/agents/) — complexity: agent (workflow, autonomous) ===
    "model-evaluator": "agent",  # Speed -> Quality -> Safety -> Report -> Document
    "turboquant-tester": "agent",  # Setup -> Baseline -> Turbo -> Compare -> Report
    "hf-publisher": "agent",  # Format -> Upload -> Verify -> Document
    "richter": "agent",  # Collect -> Dedup -> Severity -> Verdict
    "red-team-auditor": "agent",  # Scan -> Analyse -> Report
}


def add_complexity_to_frontmatter(
    filepath: Path, complexity: str, dry_run: bool
) -> bool:
    """Add complexity field to frontmatter if missing. Returns True if changed."""
    text = filepath.read_text(encoding="utf-8")

    if not text.startswith("---"):
        return False

    end = text.find("---", 3)
    if end == -1:
        return False

    fm = text[3:end]

    # Already has complexity?
    if re.search(r"^complexity\s*:", fm, re.MULTILINE):
        return False

    # Find good insertion point: after description (or after name if no description)
    # Insert after the first complete field that isn't a continuation
    lines = fm.split("\n")
    insert_after = -1
    in_multiline = False

    for i, line in enumerate(lines):
        if line.startswith("  ") and in_multiline:
            continue
        if re.match(r"^(\S[\w\-]*)\s*:", line):
            key = re.match(r"^(\S[\w\-]*)", line).group(1)
            in_multiline = line.rstrip().endswith(">") or line.rstrip().endswith("|")
            if key == "description":
                # Find end of description (might be multi-line)
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith("  "):
                        insert_after = j
                    else:
                        break
                if insert_after == -1:
                    insert_after = i
                break
            insert_after = i

    if insert_after == -1:
        insert_after = 0

    # Insert complexity line
    new_line = f"complexity: {complexity}"
    lines.insert(insert_after + 1, new_line)
    new_fm = "\n".join(lines)
    new_text = f"---{new_fm}---{text[end + 3 :]}"

    if not dry_run:
        filepath.write_text(new_text, encoding="utf-8")

    return True


def run(dry_run: bool):
    changed = 0
    skipped = 0
    unknown = 0

    # Process skills
    if SKILLS_DIR.exists():
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            if skill_dir.name.startswith(("_", ".")) or not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue
            name = skill_dir.name
            complexity = COMPLEXITY_MAP.get(name)
            if not complexity:
                print(f"  UNKNOWN: {name} (not in mapping)")
                unknown += 1
                continue
            if add_complexity_to_frontmatter(skill_file, complexity, dry_run):
                action = "WOULD SET" if dry_run else "SET"
                print(f"  {action}: {name} -> complexity: {complexity}")
                changed += 1
            else:
                skipped += 1

    # Process agents
    if AGENTS_DIR.exists():
        for agent_file in sorted(AGENTS_DIR.glob("*.md")):
            if agent_file.name.startswith(("_", ".")):
                continue
            name = agent_file.stem
            complexity = COMPLEXITY_MAP.get(name)
            if not complexity:
                print(f"  UNKNOWN: {name} (not in mapping)")
                unknown += 1
                continue
            if add_complexity_to_frontmatter(agent_file, complexity, dry_run):
                action = "WOULD SET" if dry_run else "SET"
                print(f"  {action}: {name} -> complexity: {complexity}")
                changed += 1
            else:
                skipped += 1

    mode = "DRY RUN" if dry_run else "APPLIED"
    print(f"\n--- {mode} ---")
    print(f"  Changed: {changed}")
    print(f"  Skipped (already has complexity): {skipped}")
    print(f"  Unknown (not in mapping): {unknown}")


if __name__ == "__main__":
    if "--apply" in sys.argv:
        run(dry_run=False)
    else:
        print("=== DRY RUN (use --apply to write changes) ===\n")
        run(dry_run=True)
