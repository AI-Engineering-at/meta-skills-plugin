#!/usr/bin/env python3
"""Evaluate a skill's token efficiency and quality.

Usage:
  python eval-skill.py path/to/SKILL.md              # Single skill
  python eval-skill.py path/to/SKILL.md --baseline    # Save as baseline for before/after
  python eval-skill.py path/to/SKILL.md --compare     # Compare against saved baseline
  python eval-skill.py --all                           # All local skills
  python eval-skill.py --report                        # Full report with baselines

Output: JSON with token estimates, quality scores, and delta if comparing.

Token estimation: ~1.3 tokens per English word, ~1.5 per German word.
Each tool in allowed-tools adds ~200 tokens of context overhead.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCHEMA_VERSION = 1
MAX_HISTORY_LINES = 10000


def count_tokens_estimate(text: str) -> int:
    """Estimate token count for mixed EN/DE text under Opus 4.7 tokenizer.

    Multiplier 2.0 = legacy 1.4 (Claude 4.6 era) times ~1.46 measured shift
    to the Opus 4.7 tokenizer. Rounded from 2.04 for a single defensible constant.
    """
    return int(len(text.split()) * 2.0)


def extract_frontmatter(path: Path) -> tuple[dict, str, str]:
    """Extract frontmatter dict, body text, and raw frontmatter text."""
    text = path.read_text(encoding="utf-8", errors="replace")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text, ""
    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" in line and not line.startswith("  "):
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip().strip('"').strip("'")
    return meta, parts[2], parts[1]


def get_churn(path: Path) -> int:
    """Count git commits that touched this file."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--follow", "--", str(path)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return len(result.stdout.strip().splitlines()) if result.returncode == 0 else 0
    except Exception:
        return 0


def eval_skill(path: Path) -> dict:
    """Evaluate a single skill file."""
    if not path.exists():
        return {"error": f"File not found: {path}", "schema_version": SCHEMA_VERSION}

    meta, body, raw_fm = extract_frontmatter(path)
    name = meta.get("name", path.parent.name)

    # Token costs
    fm_tokens = count_tokens_estimate(raw_fm)
    body_tokens = count_tokens_estimate(body)
    total_content_tokens = fm_tokens + body_tokens

    # Description tokens (loaded for EVERY skill during routing)
    desc = meta.get("description", "")
    desc_tokens = count_tokens_estimate(desc)

    # Tool overhead
    tools_str = meta.get("allowed-tools", "")
    if tools_str.startswith("["):
        tools = [t.strip() for t in tools_str.strip("[]").split(",") if t.strip()]
    else:
        tools = []
    tool_overhead = len(tools) * 200  # ~200 tokens per tool description

    # Reference files (additional on-demand cost)
    ref_dir = path.parent / "references"
    ref_tokens = 0
    ref_files = 0
    if ref_dir.exists():
        for ref in ref_dir.glob("*.md"):
            ref_tokens += count_tokens_estimate(
                ref.read_text(encoding="utf-8", errors="replace")
            )
            ref_files += 1

    # Total costs
    invocation_cost = (
        total_content_tokens + tool_overhead
    )  # What's loaded when skill runs
    full_cost = invocation_cost + ref_tokens  # Worst case: all refs loaded

    # Quality metrics
    body_lines = len(body.strip().splitlines())
    has_budget = bool(meta.get("token-budget"))
    has_category = bool(meta.get("category"))
    has_type = bool(meta.get("type"))
    has_triggers = bool(re.search(r"[Tt]rigger", desc))
    model = meta.get("model", "unknown")

    # Progressive Disclosure ratio
    if ref_tokens > 0:
        disclosure_ratio = round(
            total_content_tokens / (total_content_tokens + ref_tokens), 2
        )
    else:
        disclosure_ratio = 1.0  # All content in SKILL.md, no references

    # Agent candidate detection (Rule A5)
    # Skills that don't need user interaction should be agents
    interactive_keywords = [
        "confirm",
        "bestaeti",
        "approve",
        "user",
        "frag",
        "ask",
        "warte auf",
        "wait for",
        "joe",
        "dialog",
        "interactive",
    ]
    body_lower = body.lower()
    has_interactive = any(kw in body_lower for kw in interactive_keywords)
    user_invocable = meta.get("user-invocable", "").lower() == "true"
    agent_candidate = not has_interactive and user_invocable

    # Quality score (0-100)
    quality = 0
    quality += 20 if body_lines <= 150 else (10 if body_lines <= 200 else 0)
    quality += 15 if len(tools) <= 4 else (8 if len(tools) <= 6 else 0)
    quality += 15 if has_budget else 0
    quality += 10 if has_category else 0
    quality += 10 if has_type else 0
    quality += 10 if has_triggers else 0
    quality += 10 if model in ("haiku", "sonnet") else (5 if model == "opus" else 0)
    quality += 10 if disclosure_ratio < 0.7 else (5 if ref_files > 0 else 0)

    return {
        "schema_version": SCHEMA_VERSION,
        "name": name,
        "path": str(path),
        "tokens": {
            "routing_cost": desc_tokens,
            "invocation_cost": invocation_cost,
            "reference_cost": ref_tokens,
            "full_cost": full_cost,
            "tool_overhead": tool_overhead,
            "breakdown": {
                "frontmatter": fm_tokens,
                "body": body_tokens,
                "tools": tool_overhead,
                "references": ref_tokens,
            },
        },
        "metrics": {
            "body_lines": body_lines,
            "tools_count": len(tools),
            "tools": tools,
            "ref_files": ref_files,
            "disclosure_ratio": disclosure_ratio,
            "model": model,
            "churn": get_churn(path),
            "skill_version": meta.get("version", "unknown"),
        },
        "quality": {
            "score": quality,
            "has_token_budget": has_budget,
            "has_category": has_category,
            "has_type": has_type,
            "has_triggers": has_triggers,
            "agent_candidate": agent_candidate,
            "body_under_150": body_lines <= 150,
            "tools_under_5": len(tools) <= 4,
        },
        "declared_budget": meta.get("token-budget", None),
    }


def save_snapshot(result: dict, data_dir: Path, label: str = ""):
    """Append eval snapshot to history. Skips if identical within 60s."""
    history_file = data_dir / "skill-history.jsonl"

    # Idempotency: skip if identical snapshot exists within 60 seconds
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
        "name": result["name"],
        "tokens": result.get("tokens", {}),
        "quality": result.get("quality", {}),
        "metrics": result.get("metrics", {}),
    }
    with history_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    # Rotation warning
    try:
        with history_file.open(encoding="utf-8") as _hf:
            line_count = sum(1 for _ in _hf)
        if line_count > MAX_HISTORY_LINES:
            return f"WARNING: history has {line_count} entries (max recommended: {MAX_HISTORY_LINES}). Consider archiving."
    except Exception:
        pass

    return str(history_file)


def get_history(name: str, data_dir: Path) -> list[dict]:
    """Get all snapshots for a skill, oldest first."""
    history_file = data_dir / "skill-history.jsonl"
    if not history_file.exists():
        return []
    entries = []
    with history_file.open(encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get("name") == name:
                    entries.append(entry)
            except json.JSONDecodeError:
                continue
    return entries


def _delta(before_val, after_val) -> dict:
    """Calculate delta between two numeric values."""
    b = before_val or 0
    a = after_val or 0
    if b == 0:
        return {"before": b, "after": a, "delta": a, "pct": "N/A"}
    pct = round((a - b) / b * 100, 1)
    return {"before": b, "after": a, "delta": a - b, "pct": f"{pct:+.1f}%"}


def compare_with_history(result: dict, data_dir: Path) -> dict | None:
    """Compare current eval against FIRST snapshot (original baseline)."""
    history = get_history(result["name"], data_dir)
    if not history:
        return None

    first = history[0]  # Original baseline
    latest_before = (
        history[-1] if len(history) > 1 else first
    )  # Most recent before this

    def extract(entry: dict, *keys):
        val = entry
        for k in keys:
            val = val.get(k, 0) if isinstance(val, dict) else 0
        return val

    return {
        "baseline_date": first["timestamp"],
        "snapshots": len(history),
        "vs_original": {
            "invocation_cost": _delta(
                extract(first, "tokens", "invocation_cost"),
                result["tokens"]["invocation_cost"],
            ),
            "quality_score": _delta(
                extract(first, "quality", "score"), result["quality"]["score"]
            ),
            "tool_overhead": _delta(
                extract(first, "tokens", "tool_overhead"),
                result["tokens"]["tool_overhead"],
            ),
            "tools_count": _delta(
                extract(first, "metrics", "tools_count"),
                result["metrics"]["tools_count"],
            ),
            "body_lines": _delta(
                extract(first, "metrics", "body_lines"), result["metrics"]["body_lines"]
            ),
        },
        "vs_previous": {
            "invocation_cost": _delta(
                extract(latest_before, "tokens", "invocation_cost"),
                result["tokens"]["invocation_cost"],
            ),
            "quality_score": _delta(
                extract(latest_before, "quality", "score"), result["quality"]["score"]
            ),
        }
        if len(history) > 1
        else "first snapshot",
    }


# Legacy compat
def save_baseline(result: dict, data_dir: Path):
    """Save baseline = save first snapshot with label 'baseline'."""
    return save_snapshot(result, data_dir, label="baseline")


def compare_baseline(result: dict, data_dir: Path) -> dict | None:
    """Compare against history (legacy wrapper)."""
    return compare_with_history(result, data_dir)


def generate_report_md(results: list[dict], data_dir: Path) -> str:
    """Generate a readable Markdown report for all skills."""
    lines = [
        f"# Skill Eval Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"> {len(results)} skills evaluated",
        "",
    ]

    # Summary table
    total_tok = sum(r["tokens"]["invocation_cost"] for r in results if "tokens" in r)
    avg_tok = round(total_tok / len(results)) if results else 0
    avg_q = (
        round(
            sum(r["quality"]["score"] for r in results if "quality" in r) / len(results)
        )
        if results
        else 0
    )

    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total skills | {len(results)} |")
    lines.append(f"| Total invocation tokens | {total_tok:,} |")
    lines.append(f"| Avg tokens/skill | {avg_tok:,} |")
    lines.append(f"| Avg quality score | {avg_q}/100 |")
    lines.append("")

    # Per-skill table
    lines.append("## All Skills (sorted by token cost, highest first)")
    lines.append("")
    lines.append(
        "| Skill | Tokens | Quality | Tools | Lines | Model | Category | Budget |"
    )
    lines.append(
        "|-------|--------|---------|-------|-------|-------|----------|--------|"
    )

    for r in sorted(
        results,
        key=lambda x: x.get("tokens", {}).get("invocation_cost", 0),
        reverse=True,
    ):
        if "error" in r:
            continue
        t = r["tokens"]["invocation_cost"]
        q = r["quality"]["score"]
        tools = r["metrics"]["tools_count"]
        body = r["metrics"]["body_lines"]
        model = r["metrics"]["model"]
        r.get("declared_budget") or "-"
        budget = r.get("declared_budget") or "-"
        name = r["name"]
        # Quality color indicator
        qi = "!!" if q < 30 else "!" if q < 50 else "" if q < 70 else "+"
        lines.append(
            f"| {name} | {t:,} | {qi}{q}/100 | {tools} | {body} | {model} | {(r['quality'].get('has_category', False) and 'yes') or '-'} | {budget} |"
        )

    # History deltas if available
    skills_with_history = []
    for r in results:
        comp = compare_with_history(r, data_dir)
        if comp and isinstance(comp.get("vs_original"), dict):
            inv = comp["vs_original"].get("invocation_cost", {})
            if isinstance(inv, dict) and inv.get("delta", 0) != 0:
                skills_with_history.append(
                    {
                        "name": r["name"],
                        "before": inv["before"],
                        "after": inv["after"],
                        "pct": inv["pct"],
                        "q_before": comp["vs_original"]
                        .get("quality_score", {})
                        .get("before", 0),
                        "q_after": comp["vs_original"]
                        .get("quality_score", {})
                        .get("after", 0),
                    }
                )

    if skills_with_history:
        lines.append("")
        lines.append("## Improvements (vs original baseline)")
        lines.append("")
        lines.append(
            "| Skill | Tokens Before | Tokens After | Delta | Quality Before | Quality After |"
        )
        lines.append(
            "|-------|--------------|-------------|-------|---------------|--------------|"
        )
        for s in skills_with_history:
            lines.append(
                f"| {s['name']} | {s['before']:,} | {s['after']:,} | {s['pct']} | {s['q_before']}/100 | {s['q_after']}/100 |"
            )

    lines.append("")
    lines.append("---")
    lines.append("*Generated by meta-skills eval-skill.py*")
    return "\n".join(lines)


def find_local_skills() -> list[Path]:
    """Find all local SKILL.md files."""
    cwd = Path.cwd()
    local = cwd / ".claude" / "skills"
    results = []
    if local.exists():
        results.extend(local.rglob("SKILL.md"))
    # Also check meta-skills plugin
    meta = cwd / "meta-skills" / "skills"
    if meta.exists():
        results.extend(meta.rglob("SKILL.md"))
    return sorted(results)


def main():
    try:
        data_dir = Path(
            os.environ.get(
                "CLAUDE_PLUGIN_DATA",
                str(Path.home() / ".claude" / "plugins" / "data" / "meta-skills"),
            )
        )
        data_dir.mkdir(parents=True, exist_ok=True)

        if "--history" in sys.argv:
            # Show history for a specific skill
            if len(sys.argv) >= 3 and not sys.argv[1].startswith("--"):
                path = Path(sys.argv[1])
                meta, _, _ = extract_frontmatter(path)
                name = meta.get("name", path.parent.name)
            elif len(sys.argv) >= 3:
                name = sys.argv[2]
            else:
                print(
                    json.dumps(
                        {
                            "error": "Usage: eval-skill.py <SKILL.md> --history OR eval-skill.py --history <name>",
                            "schema_version": SCHEMA_VERSION,
                        }
                    )
                )
                sys.exit(1)
            history = get_history(name, data_dir)
            print(
                json.dumps(
                    {
                        "name": name,
                        "snapshots": len(history),
                        "history": history,
                        "schema_version": SCHEMA_VERSION,
                    },
                    indent=2,
                )
            )
            return

        if "--all" in sys.argv or "--report" in sys.argv:
            skills = find_local_skills()
            results = [eval_skill(p) for p in skills]
            results.sort(
                key=lambda x: x.get("tokens", {}).get("invocation_cost", 0),
                reverse=True,
            )

            total_routing = sum(
                r["tokens"]["routing_cost"] for r in results if "tokens" in r
            )
            total_invocation = sum(
                r["tokens"]["invocation_cost"] for r in results if "tokens" in r
            )

            report = {
                "schema_version": SCHEMA_VERSION,
                "total_skills": len(results),
                "total_routing_tokens": total_routing,
                "avg_invocation_tokens": round(total_invocation / len(results))
                if results
                else 0,
                "most_expensive": [
                    {
                        "name": r["name"],
                        "invocation": r["tokens"]["invocation_cost"],
                        "quality": r["quality"]["score"],
                    }
                    for r in results[:10]
                ],
                "lowest_quality": sorted(
                    [
                        {
                            "name": r["name"],
                            "quality": r["quality"]["score"],
                            "invocation": r["tokens"]["invocation_cost"],
                        }
                        for r in results
                        if "quality" in r
                    ],
                    key=lambda x: x["quality"],
                )[:10],
            }

            if "--report" in sys.argv:
                for r in results:
                    comp = compare_baseline(r, data_dir)
                    if comp:
                        r["comparison"] = comp

            if "--report-md" in sys.argv:
                md = generate_report_md(results, data_dir)
                # Save to file
                report_path = (
                    data_dir / f"eval-report-{datetime.now().strftime('%Y-%m-%d')}.md"
                )
                report_path.write_text(md, encoding="utf-8")
                print(md)
                print(f"\n\nReport saved to: {report_path}", file=sys.stderr)
                return

            print(json.dumps({"report": report, "skills": results}, indent=2))
            return

        if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
            print(
                json.dumps(
                    {
                        "error": "Usage: eval-skill.py <SKILL.md> [--baseline|--compare|--all|--report]",
                        "schema_version": SCHEMA_VERSION,
                    }
                )
            )
            sys.exit(1)

        path = Path(sys.argv[1])
        result = eval_skill(path)

        if "--baseline" in sys.argv:
            bf = save_baseline(result, data_dir)
            result["baseline_saved"] = bf

        if "--compare" in sys.argv:
            comp = compare_baseline(result, data_dir)
            if comp:
                result["comparison"] = comp
            else:
                result["comparison"] = "No baseline found. Run with --baseline first."

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(
            json.dumps(
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "script": "eval-skill.py",
                    "schema_version": SCHEMA_VERSION,
                }
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
