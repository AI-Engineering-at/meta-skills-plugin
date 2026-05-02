#!/usr/bin/env python3
"""validate.py — Deterministic schema validation for Skills, Agents, and Teams.

CI Gate: Returns exit code 1 if any ERRORS found. Warnings are advisory.

Usage:
  python validate.py                    # Validate all components
  python validate.py --errors-only      # Only show errors (CI mode)
  python validate.py --json             # JSON output
  python validate.py --fix-report       # Show what needs fixing

Schema:
  Every component MUST declare:
    - name, description (string)
    - complexity: skill | agent | team

  Skills (.claude/skills/):
    - token-budget (recommended)
    - user-invocable (recommended)

  Agents (.claude/agents/):
    - model: haiku | sonnet | opus | claude-haiku-4-5 | claude-sonnet-4-5 | claude-opus-4-7
    - maxTurns (recommended)
    - tools (recommended)

  Teams (complexity: team, either location):
    - workers (list of agent names)
"""

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
META_SKILLS_DIR = REPO_ROOT / "skills"
META_AGENTS_DIR = REPO_ROOT / "agents"
SERVICES_FILE = REPO_ROOT / ".claude" / "rules" / "03b-services-ports.md"
SKILL_REGISTRY = REPO_ROOT / ".claude" / "skill-registry.json"

VALID_COMPLEXITY = {"skill", "agent", "team"}
VALID_EXECUTION = {"main", "subagent"}
VALID_MODELS = {
    "haiku",
    "sonnet",
    "opus",
    "claude-haiku-4-5",
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-5",
    "claude-sonnet-4-6",
    "claude-opus-4-6",
    "claude-opus-4-7",
}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML-like frontmatter from markdown file."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end == -1:
        return {}, text
    fm_text = text[3:end].strip()
    body = text[end + 3 :].strip()

    meta = {}
    current_key = None
    current_val = ""
    for line in fm_text.split("\n"):
        if line.startswith("  ") and current_key:
            current_val += " " + line.strip()
            meta[current_key] = current_val.strip()
            continue
        match = re.match(r"^(\S[\w\-]*)\s*:\s*(.*)", line)
        if match:
            current_key = match.group(1)
            current_val = match.group(2).strip()
            if current_val.startswith(">"):
                current_val = ""
            elif current_val.startswith("["):
                try:
                    meta[current_key] = json.loads(current_val.replace("'", '"'))
                except json.JSONDecodeError:
                    items = current_val.strip("[]").split(",")
                    meta[current_key] = [
                        i.strip().strip("'\"") for i in items if i.strip()
                    ]
                current_key = None
                continue
            meta[current_key] = current_val
    return meta, body


def find_all_components() -> list[dict]:
    """Find all skills and agents (including meta-skills/)."""
    components = []

    # Skills (.claude/skills/ + meta-skills/skills/)
    for skills_dir in [SKILLS_DIR, META_SKILLS_DIR]:
        if not skills_dir.exists():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            if skill_dir.name.startswith(("_", ".")) or not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                text = skill_file.read_text(encoding="utf-8")
                meta, body = parse_frontmatter(text)
                components.append(
                    {
                        "name": meta.get("name", skill_dir.name),
                        "path": str(skill_file),
                        "location": "skills",
                        "meta": meta,
                        "body": body,
                        "body_lines": len(body.splitlines()),
                    }
                )

    # Agents (.claude/agents/ + meta-skills/agents/)
    for agents_dir in [AGENTS_DIR, META_AGENTS_DIR]:
        if not agents_dir.exists():
            continue
        for agent_file in sorted(agents_dir.glob("*.md")):
            if agent_file.name.startswith(("_", ".")):
                continue
            text = agent_file.read_text(encoding="utf-8")
            meta, body = parse_frontmatter(text)
            components.append(
                {
                    "name": meta.get("name", agent_file.stem),
                    "path": str(agent_file),
                    "location": "agents",
                    "meta": meta,
                    "body": body,
                    "body_lines": len(body.splitlines()),
                }
            )

    return components


def validate_component(comp: dict) -> dict:
    """Validate a single component. Returns errors and warnings."""
    meta = comp["meta"]
    location = comp["location"]
    name = comp["name"]
    body = comp["body"]
    errors = []
    warnings = []

    # --- REQUIRED FIELDS (errors) ---

    if not meta.get("name"):
        errors.append("missing required field: name")

    if not meta.get("description"):
        errors.append("missing required field: description")

    complexity = meta.get("complexity", "").lower()
    if not complexity:
        # Backwards compat: infer from location if not set
        warnings.append(
            "missing field: complexity (skill|agent|team) — inferred from location"
        )
        complexity = "skill"
    elif complexity not in VALID_COMPLEXITY:
        errors.append(f"invalid complexity: '{complexity}' — must be skill|agent|team")

    # --- LOCATION-SPECIFIC (errors) ---

    if location == "agents":
        model = meta.get("model", "")
        if not model:
            errors.append("agent missing required field: model")
        elif model.lower() not in VALID_MODELS:
            warnings.append(f"unusual model: '{model}' — expected haiku|sonnet|opus")

    # --- RECOMMENDED FIELDS (warnings) ---

    if not meta.get("version"):
        warnings.append("missing recommended field: version")

    if location == "skills":
        if not meta.get("token-budget"):
            warnings.append("missing recommended field: token-budget")
        if meta.get("user-invocable") is None:
            warnings.append("missing recommended field: user-invocable")

    if location == "agents":
        if not meta.get("maxTurns"):
            warnings.append("missing recommended field: maxTurns")
        if not meta.get("tools"):
            warnings.append("missing recommended field: tools")

    # --- CONSISTENCY CHECKS (warnings) ---

    if complexity == "team":
        workers = meta.get("team-workers", "")
        consolidator = meta.get("team-consolidator", "")
        if not workers:
            errors.append(
                "complexity=team requires team-workers field (list of parallel agents)"
            )
        if not consolidator:
            warnings.append(
                "complexity=team missing recommended field: team-consolidator"
            )

    if complexity == "agent" and location == "agents":
        # Agent-workflow as sub-agent — should be autonomous
        user_dialog = meta.get("user-dialog", "").lower()
        if user_dialog == "true":
            warnings.append(
                "complexity=agent + location=agents + user-dialog=true — why not in skills/?"
            )

    if complexity == "skill" and location == "skills":
        # Check if body suggests more complexity than declared
        body_lower = body.lower()
        phase_count = len(re.findall(r"##\s+phase\s+\d", body_lower))
        if phase_count >= 4:
            warnings.append(
                f"complexity=skill but body has {phase_count} phases — consider complexity=agent"
            )

    # --- REFERENCE CHECKS (warnings) ---

    # Check for references to files that should exist
    ref_paths = re.findall(r"`([.\w/\-]+\.(?:md|py|yaml|yml|json))`", body)
    for ref in ref_paths[:5]:  # limit to 5 to avoid noise
        full_path = REPO_ROOT / ref
        if not full_path.exists() and not ref.startswith("http"):
            # Could be relative — try from component dir
            comp_dir = Path(comp["path"]).parent
            if not (comp_dir / ref).exists():
                warnings.append(f"referenced file may not exist: {ref}")

    # --- STALENESS (warnings) ---

    last_verified = meta.get("last-verified", "")
    if last_verified:
        try:
            from datetime import datetime

            verified_date = datetime.strptime(last_verified, "%Y-%m-%d")
            days_old = (datetime.now() - verified_date).days
            if days_old > 30:
                warnings.append(
                    f"last-verified is {days_old} days old — consider re-verifying"
                )
        except ValueError:
            warnings.append(f"invalid last-verified format: {last_verified}")

    return {
        "name": name,
        "path": comp["path"],
        "location": location,
        "complexity": complexity or "unknown",
        "errors": errors,
        "warnings": warnings,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }


def validate_registry_consistency() -> dict:
    """Validate that skill-registry.json matches actual SKILL.md files."""
    errors = []
    warnings = []

    if not SKILL_REGISTRY.exists():
        warnings.append(f"skill-registry.json not found at {SKILL_REGISTRY}")
        return {
            "errors": errors,
            "warnings": warnings,
            "error_count": 0,
            "warning_count": 1,
        }

    registry = json.loads(SKILL_REGISTRY.read_text(encoding="utf-8"))
    # Keys prefixed with '_' are metadata (e.g. '_generator' provenance), not skills.
    registry_names = {k for k in registry if not k.startswith("_")}

    # Find all actual skill names from meta-skills/skills/
    actual_names = set()
    if META_SKILLS_DIR.exists():
        for skill_dir in sorted(META_SKILLS_DIR.iterdir()):
            if (
                skill_dir.is_dir()
                and not skill_dir.name.startswith(("_", "."))
                and (skill_dir / "SKILL.md").exists()
            ):
                actual_names.add(skill_dir.name)
    else:
        warnings.append(f"META_SKILLS_DIR not found: {META_SKILLS_DIR}")

    # Check: registry entries without SKILL.md
    for name in sorted(registry_names - actual_names):
        errors.append(
            f"registry has '{name}' but no SKILL.md found in {META_SKILLS_DIR}"
        )

    # Check: SKILL.md without registry entry
    for name in sorted(actual_names - registry_names):
        errors.append(
            f"SKILL.md '{name}' exists but is missing from skill-registry.json"
        )

    # Check: required fields in each skill entry (skip metadata keys)
    for name, entry in registry.items():
        if name.startswith("_"):
            continue
        for field in ["version", "category", "token-budget"]:
            if field not in entry:
                errors.append(f"registry['{name}'] missing required field: {field}")

    return {
        "errors": errors,
        "warnings": warnings,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }


def validate_all() -> dict:
    """Validate all components and return summary."""
    components = find_all_components()
    results = [validate_component(c) for c in components]

    # Registry consistency check
    reg_result = validate_registry_consistency()
    if reg_result["errors"] or reg_result["warnings"]:
        results.append(
            {
                "name": "skill-registry",
                "path": str(SKILL_REGISTRY),
                "location": "registry",
                "complexity": "meta",
                "errors": reg_result["errors"],
                "warnings": reg_result["warnings"],
                "error_count": reg_result["error_count"],
                "warning_count": reg_result["warning_count"],
            }
        )

    total_errors = sum(r["error_count"] for r in results)
    total_warnings = sum(r["warning_count"] for r in results)
    clean = [r for r in results if r["error_count"] == 0 and r["warning_count"] == 0]

    return {
        "total": len(results),
        "errors": total_errors,
        "warnings": total_warnings,
        "clean": len(clean),
        "results": results,
    }


def format_text(data: dict, errors_only: bool = False) -> str:
    lines = []
    lines.append(f"=== Schema Validation: {data['total']} components ===\n")

    has_issues = False
    for r in data["results"]:
        if errors_only and r["error_count"] == 0:
            continue
        if r["error_count"] == 0 and r["warning_count"] == 0:
            continue

        has_issues = True
        status = "ERROR" if r["error_count"] > 0 else "WARN"
        lines.append(f"[{status}] {r['name']} ({r['location']}/{r['complexity']})")
        for e in r["errors"]:
            lines.append(f"  ERROR: {e}")
        if not errors_only:
            for w in r["warnings"]:
                lines.append(f"  WARN:  {w}")
        lines.append("")

    if not has_issues:
        lines.append("All components pass validation.")

    lines.append("--- Summary ---")
    lines.append(f"  Total:    {data['total']}")
    lines.append(f"  Clean:    {data['clean']}")
    lines.append(f"  Errors:   {data['errors']}")
    lines.append(f"  Warnings: {data['warnings']}")

    if data["errors"] > 0:
        lines.append("\n  EXIT CODE: 1 (errors found)")
    else:
        lines.append("\n  EXIT CODE: 0 (no errors)")

    return "\n".join(lines)


def format_fix_report(data: dict) -> str:
    """Show exactly what needs fixing."""
    lines = ["=== Fix Report ===\n"]
    for r in data["results"]:
        if r["error_count"] == 0:
            continue
        lines.append(f"{r['name']} ({r['path']}):")
        for e in r["errors"]:
            lines.append(f"  FIX: {e}")
        lines.append("")
    if not any(r["error_count"] > 0 for r in data["results"]):
        lines.append("Nothing to fix — all components pass.")
    return "\n".join(lines)


if __name__ == "__main__":
    args = sys.argv[1:]
    data = validate_all()

    if "--json" in args:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif "--fix-report" in args:
        print(format_fix_report(data))
    else:
        errors_only = "--errors-only" in args
        print(format_text(data, errors_only))

    sys.exit(1 if data["errors"] > 0 else 0)
