#!/usr/bin/env python3
"""reworker.py — Deterministic quality improver for Meta-Skills components.

Analyzes eval.py scores, identifies what's missing, generates fixes.
No AI/LLM needed — we KNOW the eval formula, so we can compute fixes.

Usage:
  python reworker.py --diagnose              # Show all issues
  python reworker.py --diagnose --top 5      # Top 5 improvable
  python reworker.py --fix                   # Generate fixes (show only)
  python reworker.py --apply                 # Apply fixes (with confirmation)
  python reworker.py --verify                # Before/after comparison
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).parent.parent.parent
META_ROOT = Path(__file__).parent.parent


def run_eval():
    """Run eval.py and return parsed results."""
    try:
        r = subprocess.run(
            ["python", str(META_ROOT / "scripts" / "eval.py"), "--all"],
            capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT)
        )
        if r.returncode == 0:
            return json.loads(r.stdout)
    except Exception:
        pass
    return None


def extract_frontmatter(path: Path) -> dict:
    """Parse frontmatter from a file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    meta = {}
    current_key = None
    current_val = ""
    for line in text[3:end].strip().splitlines():
        if line.startswith("  ") and current_key:
            current_val += " " + line.strip()
            meta[current_key] = current_val.strip()
            continue
        if ":" in line and not line.startswith("  "):
            current_key, _, val = line.partition(":")
            current_key = current_key.strip()
            val = val.strip().strip('"').strip("'")
            if val == ">" or val == "|":
                current_val = ""
                meta[current_key] = ""
                continue
            current_val = val
            meta[current_key] = val
    return meta


def diagnose_component(result: dict) -> list:
    """Diagnose what's wrong with a component and how to fix it."""
    quality = result.get("quality", {})
    metrics = result.get("metrics", {})
    quality.get("score", 0)
    path = Path(result.get("path", ""))
    item_type = result.get("type", "unknown")
    quality.get("declared_complexity", "skill")

    issues = []

    if item_type == "skill" or (item_type == "unknown" and "SKILL.md" in str(path)):
        # Skill scoring analysis
        if not quality.get("has_version"):
            issues.append({
                "field": "version",
                "fix": "version: 1.0.0",
                "points": 10,
                "auto": True,
                "reason": "Missing version field",
            })
        if not quality.get("has_triggers"):
            issues.append({
                "field": "description",
                "fix": "Add 'Trigger:' keyword to description",
                "points": 10,
                "auto": False,
                "reason": "No trigger words in description",
            })
        if not quality.get("has_token_budget"):
            issues.append({
                "field": "token-budget",
                "fix": "token-budget: 1000",
                "points": 15,
                "auto": True,
                "reason": "Missing token-budget",
            })
        if not quality.get("has_complexity"):
            issues.append({
                "field": "complexity",
                "fix": "complexity: skill",
                "points": 10,
                "auto": True,
                "reason": "Missing complexity declaration",
            })
        if metrics.get("body_lines", 0) > 150 and not quality.get("body_under_150", True):
            issues.append({
                "field": "body",
                "fix": "Move detail sections to references/ directory",
                "points": 15,
                "auto": False,
                "reason": f"Body too long ({metrics.get('body_lines', 0)} lines > 150)",
            })
        # Skill formula: ≤4=15pts, ≤6=8pts, >6=0pts — only flag >6 as blocking
        tc = metrics.get("tools_count", 0)
        if tc > 6:
            issues.append({
                "field": "tools",
                "fix": "Reduce to ≤6 tools (ideally ≤4)",
                "points": 15,
                "auto": False,
                "reason": f"Too many tools ({tc} > 6) — costs 15pts vs 8pts",
            })
        elif tc > 4:
            issues.append({
                "field": "tools",
                "fix": "Reduce to ≤4 tools for maximum score",
                "points": 7,
                "auto": False,
                "reason": f"Tools {tc} > 4 — gets 8pts instead of 15pts (+7 possible)",
            })
        cat = extract_frontmatter(path).get("category", "")
        if not cat:
            # Guess category from path
            path_str = str(path).lower()
            if "infra" in path_str or "deploy" in path_str:
                cat_guess = "infrastructure"
            elif "meta" in path_str or "eval" in path_str:
                cat_guess = "meta"
            elif "doc" in path_str or "wiki" in path_str:
                cat_guess = "documentation"
            else:
                cat_guess = "automation"
            issues.append({
                "field": "category",
                "fix": f"category: {cat_guess}",
                "points": 5,
                "auto": True,
                "reason": "Missing category field",
            })

    elif item_type == "agent":
        # Agent scoring analysis
        if not quality.get("has_version"):
            issues.append({
                "field": "version",
                "fix": "version: 1.0.0",
                "points": 10,
                "auto": True,
                "reason": "Missing version field",
            })
        if not quality.get("has_triggers"):
            issues.append({
                "field": "description",
                "fix": "Add 'Trigger:' keyword to description",
                "points": 15,
                "auto": False,
                "reason": "No trigger words in description",
            })
        if not quality.get("has_max_turns"):
            issues.append({
                "field": "maxTurns",
                "fix": "maxTurns: 30",
                "points": 10,
                "auto": True,
                "reason": "Missing maxTurns",
            })
        if not quality.get("has_complexity"):
            issues.append({
                "field": "complexity",
                "fix": "complexity: agent",
                "points": 10,
                "auto": True,
                "reason": "Missing complexity declaration",
            })
        if not quality.get("model_efficient", True):
            issues.append({
                "field": "model",
                "fix": "Consider downgrading to sonnet or haiku",
                "points": 10,
                "auto": False,
                "reason": "Model may be overpowered for this task",
            })
        if quality.get("autonomy_score", 0) < 2:
            issues.append({
                "field": "body",
                "fix": "Add ## Steps with numbered steps and ```bash commands",
                "points": 7,
                "auto": False,
                "reason": f"Low autonomy score ({quality.get('autonomy_score', 0)}/3) — needs steps, commands, or output format",
            })
        # Agent formula: ≤4=10pts, ≤6=5pts, >6=0pts
        tc = metrics.get("tools_count", 0)
        if tc > 6:
            issues.append({
                "field": "tools",
                "fix": "Reduce to ≤6 tools",
                "points": 5,
                "auto": False,
                "reason": f"Too many tools ({tc} > 6) — 0pts vs 5pts",
            })

    return issues


def diagnose_all(eval_data: dict, top_n: int = 0, min_score: int = 0, max_score: int = 97) -> list:
    """Diagnose all components, sorted by improvement potential.

    Args:
        top_n: Limit to top N results (0 = all)
        min_score: Only show components with score >= min_score
        max_score: Skip components already at or above this score (default 97 = no false positives)
    """
    diagnostics = []

    for result in eval_data.get("results", []):
        score = result.get("quality", {}).get("score", 0)
        if score >= max_score:
            continue  # Already near-perfect — skip to avoid false positives
        if score < min_score:
            continue
        issues = diagnose_component(result)
        if not issues:
            continue

        total_potential = sum(i["points"] for i in issues)
        auto_potential = sum(i["points"] for i in issues if i["auto"])

        diagnostics.append({
            "name": result["name"],
            "path": result["path"],
            "type": result["type"],
            "score": result["quality"]["score"],
            "potential": total_potential,
            "auto_potential": auto_potential,
            "issues": issues,
        })

    # Sort by most potential first
    diagnostics.sort(key=lambda x: x["potential"], reverse=True)

    if top_n > 0:
        diagnostics = diagnostics[:top_n]

    return diagnostics


def apply_fix(path: Path, field: str, fix_value: str) -> bool:
    """Apply a single frontmatter fix to a file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False

    if not text.startswith("---"):
        return False

    end = text.find("---", 3)
    if end == -1:
        return False

    fm = text[3:end]
    rest = text[end:]

    # Check if field already exists
    pattern = rf"^{re.escape(field)}\s*:"
    if re.search(pattern, fm, re.MULTILINE):
        # Replace existing
        fm = re.sub(pattern + r".*$", f"{field}: {fix_value}", fm, count=1, flags=re.MULTILINE)
    else:
        # Add after name or description (whichever comes last)
        lines = fm.strip().splitlines()
        insert_after = 0
        for i, line in enumerate(lines):
            if line.startswith(("name:", "description")):
                insert_after = i
            # Also skip continuation lines
            if line.startswith("  ") and i > 0:
                insert_after = i
        lines.insert(insert_after + 1, f"{field}: {fix_value}")
        fm = "\n".join(lines) + "\n"

    new_text = "---\n" + fm.strip() + "\n" + rest
    path.write_text(new_text, encoding="utf-8")
    return True


def format_diagnosis(diagnostics: list) -> str:
    """Format diagnosis for display."""
    lines = ["# Reworker Diagnosis\n"]

    total_potential = sum(d["potential"] for d in diagnostics)
    auto_potential = sum(d["auto_potential"] for d in diagnostics)

    lines.append(f"**{len(diagnostics)} components** with improvement potential")
    lines.append(f"**Total: +{total_potential} points** possible (+{auto_potential} auto-fixable)\n")

    for d in diagnostics:
        auto_tag = f" (auto: +{d['auto_potential']})" if d["auto_potential"] > 0 else ""
        lines.append(f"## {d['name']} ({d['score']}/100) — Potential: +{d['potential']}{auto_tag}")
        lines.append(f"Path: {d['path']}")
        for issue in d["issues"]:
            auto = "AUTO" if issue["auto"] else "MANUAL"
            lines.append(f"  [{auto}] +{issue['points']:2d}pts | {issue['reason']}")
            lines.append(f"          Fix: {issue['fix']}")
        lines.append("")

    return "\n".join(lines)


def apply_auto_fixes(diagnostics: list, dry_run: bool = True) -> list:
    """Apply all auto-fixable issues. Returns list of applied fixes."""
    applied = []

    for d in diagnostics:
        path = Path(d["path"])
        for issue in d["issues"]:
            if not issue["auto"]:
                continue

            field = issue["field"]
            fix_value = issue["fix"].replace(f"{field}: ", "")

            if dry_run:
                applied.append(f"WOULD FIX: {d['name']} — {field}: {fix_value}")
            else:
                if apply_fix(path, field, fix_value):
                    applied.append(f"FIXED: {d['name']} — {field}: {fix_value}")
                else:
                    applied.append(f"FAILED: {d['name']} — {field}: {fix_value}")

    return applied


def verify(before_file: str = ".meta-cache/eval-before.json") -> str:
    """Compare current eval with baseline."""
    before_path = REPO_ROOT / before_file
    if not before_path.exists():
        return "No baseline found. Run eval.py --all first."

    with before_path.open() as f:
        before = json.load(f)

    after = run_eval()
    if not after:
        return "Failed to run eval.py"

    before_scores = {r["name"]: r["quality"]["score"] for r in before["results"]}
    after_scores = {r["name"]: r["quality"]["score"] for r in after["results"]}

    before_avg = sum(before_scores.values()) / len(before_scores)
    after_avg = sum(after_scores.values()) / len(after_scores)

    lines = ["# Reworker Verification\n"]
    lines.append("| Metric | Before | After | Delta |")
    lines.append("|--------|--------|-------|-------|")
    lines.append(f"| Avg Score | {before_avg:.1f} | {after_avg:.1f} | {after_avg - before_avg:+.1f} |")
    lines.append(f"| Below 70 | {sum(1 for s in before_scores.values() if s < 70)} | {sum(1 for s in after_scores.values() if s < 70)} | |")
    lines.append(f"| Above 90 | {sum(1 for s in before_scores.values() if s >= 90)} | {sum(1 for s in after_scores.values() if s >= 90)} | |")

    # Show changed components
    lines.append("\n## Changed Components\n")
    for name in sorted(set(list(before_scores.keys()) + list(after_scores.keys()))):
        b = before_scores.get(name, 0)
        a = after_scores.get(name, 0)
        if a != b:
            delta = a - b
            emoji = "+" if delta > 0 else ""
            lines.append(f"  {name}: {b} -> {a} ({emoji}{delta})")

    return "\n".join(lines)


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--verify" in args:
        print(verify())
        sys.exit(0)

    eval_data = run_eval()
    if not eval_data:
        print("ERROR: Could not run eval.py")
        sys.exit(1)

    top_n = 0
    if "--top" in args:
        idx = args.index("--top")
        if idx + 1 < len(args):
            top_n = int(args[idx + 1])

    min_score = 0
    if "--min-score" in args:
        idx = args.index("--min-score")
        if idx + 1 < len(args):
            min_score = int(args[idx + 1])

    max_score = 97  # Default: skip near-perfect components
    if "--max-score" in args:
        idx = args.index("--max-score")
        if idx + 1 < len(args):
            max_score = int(args[idx + 1])

    diagnostics = diagnose_all(eval_data, top_n, min_score, max_score)

    if "--diagnose" in args:
        print(format_diagnosis(diagnostics))

    elif "--fix" in args:
        # Show what would be fixed (dry run)
        fixes = apply_auto_fixes(diagnostics, dry_run=True)
        print("# Auto-Fix Preview (dry run)\n")
        for fix in fixes:
            print(f"  {fix}")
        print(f"\n{len(fixes)} fixes ready. Run with --apply to apply.")

    elif "--apply" in args:
        # Apply fixes for real
        fixes = apply_auto_fixes(diagnostics, dry_run=False)
        print("# Applied Fixes\n")
        for fix in fixes:
            print(f"  {fix}")
        print(f"\n{len(fixes)} fixes applied. Run --verify to check results.")

    else:
        print("Usage: reworker.py --diagnose [--top N] | --fix | --apply | --verify")
