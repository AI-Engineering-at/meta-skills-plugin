#!/usr/bin/env python3
"""eval.py v3 — Quality scoring for Skills, Agents, and Teams.

Type detection uses DECLARED complexity field (not body heuristics).
Misclassification detection moved to validate.py (deterministic).

Usage:
  python eval.py path/to/file.md                  # Single skill or agent
  python eval.py path/to/file.md --baseline        # Save as baseline
  python eval.py path/to/file.md --compare         # Compare against baseline
  python eval.py --all                             # All skills + agents
  python eval.py --skills-only                     # Only skills
  python eval.py --agents-only                     # Only agents
  python eval.py --report --report-md              # Full markdown report

v3 changes: complexity-aware scoring, no body-based type guessing.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCHEMA_VERSION = 3


def count_tokens(text: str) -> int:
    """Estimate token count for mixed EN/DE text.

    Multiplier 2.0 = legacy 1.4 (Claude 4.6 era) times ~1.46 measured shift
    to the Opus 4.7 tokenizer (Anthropic docs: 1.0-1.35x; Willison/claudecodecamp
    measured 1.46x real-world). Rounded to 2.0 for a single defensible constant.
    """
    return int(len(text.split()) * 2.0)


def extract_frontmatter(path: Path) -> tuple[dict, str, str]:
    """Extract frontmatter dict, body text, and raw frontmatter text."""
    text = path.read_text(encoding="utf-8", errors="replace")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text, ""
    meta = {}
    current_key = None
    current_val = ""
    for line in parts[1].strip().splitlines():
        # Continuation line (indented) for multi-line YAML values
        if line.startswith("  ") and current_key:
            current_val += " " + line.strip()
            meta[current_key] = current_val.strip()
            continue
        if ":" in line and not line.startswith("  "):
            current_key, _, val = line.partition(":")
            current_key = current_key.strip()
            val = val.strip().strip('"').strip("'")
            # Handle YAML folded scalar (>) — value comes on next lines
            if val == ">" or val == "|":
                current_val = ""
                meta[current_key] = ""
                continue
            current_val = val
            meta[current_key] = val
    return meta, parts[2], parts[1]


def parse_tools(meta: dict) -> list[str]:
    """Parse tools from frontmatter (supports both formats)."""
    # Skills use 'allowed-tools', agents use 'tools'
    tools_str = meta.get("allowed-tools", "") or meta.get("tools", "")
    if not tools_str:
        return []
    if tools_str.startswith("["):
        return [t.strip() for t in tools_str.strip("[]").split(",") if t.strip()]
    return [t.strip() for t in tools_str.split(",") if t.strip()]


def get_churn(path: Path) -> int:
    """Count git commits that touched this file."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--follow", "--", str(path)],
            capture_output=True, text=True, timeout=5
        )
        return len(result.stdout.strip().splitlines()) if result.returncode == 0 else 0
    except Exception:
        return 0


def detect_type(path: Path, meta: dict) -> str:
    """Detect if this is a skill or agent based on path and content."""
    path_str = str(path).replace("\\", "/")
    if "/agents/" in path_str and path.suffix == ".md":
        return "agent"
    if "SKILL.md" in path.name:
        return "skill"
    # Fallback: check frontmatter
    if meta.get("maxTurns"):
        return "agent"
    if meta.get("allowed-tools"):
        return "skill"
    return "unknown"


# --- Complexity-aware quality scoring ---


def eval_skill_quality(meta: dict, body: str, tools: list, body_lines: int,
                       ref_files: int, disclosure_ratio: float) -> dict:
    """Quality scoring for complexity=skill components (0-100)."""
    desc = meta.get("description", "")
    model = meta.get("model", "unknown")
    complexity = meta.get("complexity", "skill")
    has_budget = bool(meta.get("token-budget"))
    has_category = bool(meta.get("category"))
    has_complexity = bool(meta.get("complexity"))
    has_triggers = bool(re.search(r"[Tt]rigger", desc))
    has_version = bool(meta.get("version"))

    score = 0
    score += 15 if body_lines <= 150 else (8 if body_lines <= 200 else 0)  # Concise body
    score += 15 if len(tools) <= 4 else (8 if len(tools) <= 6 else 0)      # Minimal tools
    score += 15 if has_budget else 0                                        # Token budget
    score += 10 if has_complexity else 0                                    # Declared complexity
    score += 10 if has_triggers else 0                                      # Trigger words
    score += 10 if has_version else 0                                       # Version tracking
    score += 10 if model in ("haiku", "sonnet") else (5 if model == "opus" else 0)  # Model efficiency
    score += 10 if disclosure_ratio < 0.7 else (5 if ref_files > 0 else 0) # Progressive disclosure
    score += 5 if has_category else 0                                       # Category

    return {
        "score": score,
        "declared_complexity": complexity,
        "has_token_budget": has_budget,
        "has_complexity": has_complexity,
        "has_triggers": has_triggers,
        "has_version": has_version,
        "body_under_150": body_lines <= 150,
        "tools_under_5": len(tools) <= 4,
    }


MODEL_TIERS = {"haiku": 1, "sonnet": 2, "opus": 3}
COMPLEX_KEYWORDS = ["architecture", "architektur", "design", "security", "adversarial",
                     "red.team", "multi.step", "complex"]


def eval_agent_quality(meta: dict, body: str, tools: list, body_lines: int) -> dict:
    """Quality scoring for components in .claude/agents/ (0-100)."""
    desc = meta.get("description", "")
    model = meta.get("model", "unknown")
    complexity = meta.get("complexity", "skill")
    has_max_turns = bool(meta.get("maxTurns"))
    has_triggers = bool(re.search(r"[Tt]rigger|triggers?:", desc, re.IGNORECASE))
    has_version = bool(meta.get("version"))
    has_complexity = bool(meta.get("complexity"))

    # Body autonomy: does the agent have enough detail to work alone?
    body_lower = body.lower()
    has_steps = bool(re.search(r"(schritt|step|##)\s+\d", body_lower))
    has_commands = bool(re.search(r"```(bash|python|sh)", body_lower))
    has_output_format = bool(re.search(r"(output|format|ergebnis|report)", body_lower))
    autonomy_score = sum([has_steps, has_commands, has_output_format])

    # Model efficiency: is the model appropriate for declared complexity?
    model_key = model.lower().split("-")[0] if model else "unknown"
    is_complex = any(re.search(kw, desc.lower()) for kw in COMPLEX_KEYWORDS)
    model_tier = MODEL_TIERS.get(model_key, 2)
    model_efficient = True
    if model_tier == 3 and not is_complex:
        model_efficient = False
    if complexity == "skill" and model_tier >= 2 and not is_complex:
        model_efficient = False  # Simple skill sub-agent should use haiku

    score = 0
    score += 15 if has_triggers else 0                          # Trigger words
    score += 15 if model_efficient else 5                       # Model appropriateness
    score += 10 if has_max_turns else 0                         # maxTurns set
    score += 15 if autonomy_score >= 2 else (8 if autonomy_score >= 1 else 0)  # Body autonomy
    score += 10 if len(tools) <= 4 else (5 if len(tools) <= 6 else 0)  # Tool scope
    score += 10 if has_complexity else 0                        # Declared complexity
    score += 10 if has_version else 0                           # Version tracking
    score += 15 if body_lines >= 20 else (8 if body_lines >= 10 else 0)  # Sufficient detail

    return {
        "score": score,
        "declared_complexity": complexity,
        "has_triggers": has_triggers,
        "model_efficient": model_efficient,
        "has_max_turns": has_max_turns,
        "has_complexity": has_complexity,
        "autonomy_score": autonomy_score,
        "tools_under_5": len(tools) <= 4,
        "has_version": has_version,
    }


def eval_team_quality(meta: dict, body: str, tools: list, body_lines: int) -> dict:
    """Quality scoring for complexity=team components (0-100)."""
    desc = meta.get("description", "")
    complexity = meta.get("complexity", "team")
    has_workers = bool(meta.get("team-workers"))
    has_consolidator = bool(meta.get("team-consolidator"))
    has_triggers = bool(re.search(r"[Tt]rigger|triggers?:", desc, re.IGNORECASE))
    has_version = bool(meta.get("version"))
    has_complexity = bool(meta.get("complexity"))
    has_budget = bool(meta.get("token-budget"))

    # Workers quality: how many parallel agents?
    workers_str = meta.get("team-workers", "")
    if isinstance(workers_str, list):
        worker_count = len(workers_str)
    elif workers_str.startswith("["):
        worker_count = len([w.strip() for w in workers_str.strip("[]").split(",") if w.strip()])
    else:
        worker_count = 0

    # Body should describe orchestration, presets, flow
    body_lower = body.lower()
    has_presets = bool(re.search(r"preset|konfiguration|mode", body_lower))
    has_flow = bool(re.search(r"(step|schritt|flow|execution)\s+\d", body_lower))

    score = 0
    score += 25 if has_workers and worker_count >= 2 else (10 if has_workers else 0)  # Workers
    score += 15 if has_consolidator else 0                    # Consolidator
    score += 10 if has_triggers else 0                        # Trigger words
    score += 10 if has_complexity else 0                      # Declared complexity
    score += 10 if has_version else 0                         # Version
    score += 10 if has_budget else 0                          # Token budget
    score += 10 if has_presets else 0                         # Preset/mode support
    score += 10 if has_flow and body_lines >= 30 else (5 if body_lines >= 20 else 0)  # Orchestration detail

    return {
        "score": score,
        "declared_complexity": complexity,
        "has_workers": has_workers,
        "worker_count": worker_count,
        "has_consolidator": has_consolidator,
        "has_triggers": has_triggers,
        "has_version": has_version,
        "has_complexity": has_complexity,
    }


# --- Unified evaluator ---

def evaluate(path: Path) -> dict:
    """Evaluate a single skill or agent file."""
    if not path.exists():
        return {"error": f"File not found: {path}", "schema_version": SCHEMA_VERSION}

    meta, body, raw_fm = extract_frontmatter(path)
    item_type = detect_type(path, meta)
    name = meta.get("name", path.stem if item_type == "agent" else path.parent.name)
    tools = parse_tools(meta)
    desc = meta.get("description", "")
    model = meta.get("model", "unknown")

    # Token costs
    fm_tokens = count_tokens(raw_fm)
    body_tokens = count_tokens(body)
    total_content_tokens = fm_tokens + body_tokens
    desc_tokens = count_tokens(desc)
    tool_overhead = len(tools) * 200

    # Reference files (skills only — agents don't have references/)
    ref_dir = path.parent / "references"
    ref_tokens = 0
    ref_files = 0
    if item_type == "skill" and ref_dir.exists():
        for ref in ref_dir.glob("*.md"):
            ref_tokens += count_tokens(ref.read_text(encoding="utf-8", errors="replace"))
            ref_files += 1

    invocation_cost = total_content_tokens + tool_overhead
    routing_cost = desc_tokens
    full_cost = invocation_cost + ref_tokens

    body_lines = len(body.strip().splitlines())

    # Progressive Disclosure ratio (skills only)
    if ref_tokens > 0:
        disclosure_ratio = round(total_content_tokens / (total_content_tokens + ref_tokens), 2)
    else:
        disclosure_ratio = 1.0

    # Type-specific quality — use declared complexity for scoring selection
    declared_complexity = meta.get("complexity", "skill")
    if declared_complexity == "team":
        quality = eval_team_quality(meta, body, tools, body_lines)
    elif item_type == "agent":
        quality = eval_agent_quality(meta, body, tools, body_lines)
    else:
        quality = eval_skill_quality(meta, body, tools, body_lines, ref_files, disclosure_ratio)

    return {
        "schema_version": SCHEMA_VERSION,
        "type": item_type,
        "name": name,
        "path": str(path),
        "tokens": {
            "routing_cost": routing_cost,
            "invocation_cost": invocation_cost,
            "reference_cost": ref_tokens,
            "full_cost": full_cost,
            "tool_overhead": tool_overhead,
            "breakdown": {
                "frontmatter": fm_tokens,
                "body": body_tokens,
                "tools": tool_overhead,
                "references": ref_tokens,
            }
        },
        "metrics": {
            "body_lines": body_lines,
            "tools_count": len(tools),
            "tools": tools,
            "ref_files": ref_files,
            "disclosure_ratio": disclosure_ratio,
            "model": model,
            "churn": get_churn(path),
            "version": meta.get("version", "unknown"),
        },
        "quality": quality,
        "declared_budget": meta.get("token-budget"),
    }


# --- Discovery ---

def find_skills(cwd: Path) -> list[Path]:
    """Find all SKILL.md files (excluding _archive)."""
    results = []
    for d in [cwd / ".claude" / "skills", cwd / "meta-skills" / "skills"]:
        if d.exists():
            for p in d.rglob("SKILL.md"):
                if "_archive" not in str(p):
                    results.append(p)
    return sorted(results)


def find_agents(cwd: Path) -> list[Path]:
    """Find all agent .md files."""
    agents_dir = cwd / ".claude" / "agents"
    if not agents_dir.exists():
        return []
    # Also check meta-skills agents
    results = list(agents_dir.glob("*.md"))
    meta_agents = cwd / "meta-skills" / "agents"
    if meta_agents.exists():
        results.extend(meta_agents.glob("*.md"))
    return sorted(results)


# --- History (compatible with eval-skill.py) ---

def save_snapshot(result: dict, data_dir: Path, label: str = ""):
    """Append eval snapshot to history."""
    history_file = data_dir / "eval-history.jsonl"
    existing = get_history(result["name"], data_dir)
    if existing:
        last = existing[-1]
        try:
            last_time = datetime.fromisoformat(last["timestamp"])
            if (datetime.now() - last_time).total_seconds() < 60:
                last_tokens = last.get("tokens", {}).get("invocation_cost", -1)
                curr_tokens = result.get("tokens", {}).get("invocation_cost", -2)
                if last_tokens == curr_tokens:
                    return "SKIPPED: identical snapshot within 60s"
        except (ValueError, KeyError):
            pass

    entry = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": datetime.now().isoformat(),
        "label": label or "snapshot",
        "type": result.get("type", "unknown"),
        "name": result["name"],
        "tokens": result.get("tokens", {}),
        "quality": result.get("quality", {}),
        "metrics": result.get("metrics", {}),
    }
    with history_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return str(history_file)


def get_history(name: str, data_dir: Path) -> list[dict]:
    """Get all snapshots for a skill/agent, oldest first."""
    results = []
    for fname in ["eval-history.jsonl", "skill-history.jsonl"]:  # check both for compat
        hf = data_dir / fname
        if not hf.exists():
            continue
        with hf.open(encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("name") == name:
                        results.append(entry)
                except json.JSONDecodeError:
                    continue
    return sorted(results, key=lambda x: x.get("timestamp", ""))


def compare_with_history(result: dict, data_dir: Path) -> dict | None:
    """Compare current eval against first snapshot."""
    history = get_history(result["name"], data_dir)
    if not history:
        return None

    first = history[0]

    def _d(before, after):
        b, a = before or 0, after or 0
        if b == 0:
            return {"before": b, "after": a, "delta": a, "pct": "N/A"}
        pct = round((a - b) / b * 100, 1)
        return {"before": b, "after": a, "delta": a - b, "pct": f"{pct:+.1f}%"}

    def _get(entry, *keys):
        val = entry
        for k in keys:
            val = val.get(k, 0) if isinstance(val, dict) else 0
        return val

    return {
        "baseline_date": first.get("timestamp"),
        "snapshots": len(history),
        "vs_original": {
            "invocation_cost": _d(_get(first, "tokens", "invocation_cost"), result["tokens"]["invocation_cost"]),
            "quality_score": _d(_get(first, "quality", "score"), result["quality"]["score"]),
        },
    }


# --- Report generation ---

def generate_report(results: list[dict], data_dir: Path) -> str:
    """Generate unified Markdown report for skills + agents."""
    skills = [r for r in results if r.get("type") == "skill"]
    agents = [r for r in results if r.get("type") == "agent"]

    lines = [
        f"# Unified Eval Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"> {len(skills)} skills + {len(agents)} agents = {len(results)} total",
        "",
        "## Summary",
        "",
        "| Metric | Skills | Agents | Total |",
        "|--------|--------|--------|-------|",
    ]

    def _sum_tok(items):
        return sum(r["tokens"]["invocation_cost"] for r in items if "tokens" in r)

    def _avg_q(items):
        scores = [r["quality"]["score"] for r in items if "quality" in r]
        return round(sum(scores) / len(scores)) if scores else 0

    s_tok, a_tok = _sum_tok(skills), _sum_tok(agents)
    s_q, a_q = _avg_q(skills), _avg_q(agents)

    lines.append(f"| Count | {len(skills)} | {len(agents)} | {len(results)} |")
    lines.append(f"| Total tokens | {s_tok:,} | {a_tok:,} | {s_tok + a_tok:,} |")
    lines.append(f"| Avg quality | {s_q}/100 | {a_q}/100 | {_avg_q(results)}/100 |")
    lines.append("")

    # Complexity distribution
    complexity_dist = {}
    for r in results:
        c = r.get("quality", {}).get("declared_complexity", "unknown")
        complexity_dist[c] = complexity_dist.get(c, 0) + 1
    lines.append(f"| Complexity | {' | '.join(f'{k}: {v}' for k, v in sorted(complexity_dist.items()))} |")
    lines.append("")

    # Skills table
    lines.append("## Skills (sorted by quality)")
    lines.append("")
    lines.append("| Skill | Complexity | Quality | Tokens | Tools | Model |")
    lines.append("|-------|-----------|---------|--------|-------|-------|")
    for r in sorted(skills, key=lambda x: x.get("quality", {}).get("score", 0)):
        if "error" in r:
            continue
        c = r.get("quality", {}).get("declared_complexity", "?")
        q = r["quality"]["score"]
        qi = "+" if q >= 70 else ("!" if q >= 50 else "!!")
        lines.append(f"| {r['name']} | {c} | {qi}{q}/100 | {r['tokens']['invocation_cost']:,} | {r['metrics']['tools_count']} | {r['metrics']['model']} |")

    # Agents table
    lines.append("")
    lines.append("## Agents (sorted by quality)")
    lines.append("")
    lines.append("| Agent | Complexity | Quality | Tokens | Tools | Model |")
    lines.append("|-------|-----------|---------|--------|-------|-------|")
    for r in sorted(agents, key=lambda x: x.get("quality", {}).get("score", 0)):
        if "error" in r:
            continue
        c = r.get("quality", {}).get("declared_complexity", "?")
        q = r["quality"]["score"]
        qi = "+" if q >= 70 else ("!" if q >= 50 else "!!")
        lines.append(f"| {r['name']} | {c} | {qi}{q}/100 | {r['tokens']['invocation_cost']:,} | {r['metrics']['tools_count']} | {r['metrics']['model']} |")

    # History deltas
    items_with_history = []
    for r in results:
        comp = compare_with_history(r, data_dir)
        if comp and isinstance(comp.get("vs_original"), dict):
            inv = comp["vs_original"].get("invocation_cost", {})
            if isinstance(inv, dict) and inv.get("delta", 0) != 0:
                items_with_history.append({
                    "name": r["name"],
                    "type": r.get("type", "?"),
                    "before": inv["before"],
                    "after": inv["after"],
                    "pct": inv["pct"],
                })

    if items_with_history:
        lines.append("")
        lines.append("## Changes vs Baseline")
        lines.append("")
        lines.append("| Name | Type | Before | After | Delta |")
        lines.append("|------|------|--------|-------|-------|")
        for s in items_with_history:
            lines.append(f"| {s['name']} | {s['type']} | {s['before']:,} | {s['after']:,} | {s['pct']} |")

    lines.append("")
    lines.append("---")
    lines.append(f"*Generated by meta-skills eval.py v{SCHEMA_VERSION}*")
    return "\n".join(lines)


# --- Main ---

def main():
    try:
        data_dir = Path(os.environ.get(
            "CLAUDE_PLUGIN_DATA",
            str(Path.home() / ".claude" / "plugins" / "data" / "meta-skills")
        ))
        data_dir.mkdir(parents=True, exist_ok=True)
        cwd = Path.cwd()

        args = sys.argv[1:]
        def flag(f):
            return f in args

        if flag("--history"):
            name = next((a for a in args if not a.startswith("--")), None)
            if not name:
                print(json.dumps({"error": "Usage: eval.py --history <name>"}))
                sys.exit(1)
            if Path(name).exists():
                meta, _, _ = extract_frontmatter(Path(name))
                name = meta.get("name", Path(name).stem)
            history = get_history(name, data_dir)
            print(json.dumps({"name": name, "snapshots": len(history), "history": history}, indent=2))
            return

        if flag("--all") or flag("--report") or flag("--skills-only") or flag("--agents-only"):
            results = []
            if not flag("--agents-only"):
                results.extend(evaluate(p) for p in find_skills(cwd))
            if not flag("--skills-only"):
                results.extend(evaluate(p) for p in find_agents(cwd))

            results.sort(key=lambda x: x.get("tokens", {}).get("invocation_cost", 0), reverse=True)

            if flag("--report-md"):
                md = generate_report(results, data_dir)
                report_path = data_dir / f"eval-report-{datetime.now().strftime('%Y-%m-%d')}.md"
                report_path.write_text(md, encoding="utf-8")
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                print(md)
                print(f"\nReport saved to: {report_path}", file=sys.stderr)
                return

            skills = [r for r in results if r.get("type") == "skill"]
            agents = [r for r in results if r.get("type") == "agent"]
            print(json.dumps({
                "schema_version": SCHEMA_VERSION,
                "total": len(results),
                "skills": len(skills),
                "agents": len(agents),
                "results": results,
            }, indent=2))
            return

        # Single file evaluation
        file_arg = next((a for a in args if not a.startswith("--")), None)
        if not file_arg:
            print(json.dumps({"error": "Usage: eval.py <file.md> [--baseline|--compare] | --all | --report --report-md"}))
            sys.exit(1)

        result = evaluate(Path(file_arg))

        if flag("--baseline"):
            result["baseline_saved"] = save_snapshot(result, data_dir, label="baseline")

        if flag("--compare"):
            comp = compare_with_history(result, data_dir)
            result["comparison"] = comp or "No baseline found. Run with --baseline first."

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e), "error_type": type(e).__name__, "schema_version": SCHEMA_VERSION}))
        sys.exit(1)


if __name__ == "__main__":
    main()
