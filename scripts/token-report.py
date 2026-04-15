#!/usr/bin/env python3
"""token-report.py — Analyze token usage from audit data.

Reads token-audit.jsonl and generates efficiency reports.
Shows where tokens flow, which tools cost the most, and
quantifies savings after optimizations are applied.

Usage:
  python token-report.py                  # Full report (current data)
  python token-report.py --session        # Current session only
  python token-report.py --compare A B    # Compare two sessions
  python token-report.py --top 10         # Top 10 token consumers
  python token-report.py --json           # Machine-readable output
  python token-report.py --export FILE    # Export to markdown file
"""
import json
import sys
import os
import argparse
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PLUGIN_DATA = Path(os.environ.get(
    "CLAUDE_PLUGIN_DATA",
    Path.home() / ".claude" / "plugins" / "data" / "meta-skills"
))
AUDIT_FILE = PLUGIN_DATA / "token-audit.jsonl"


def load_audit(path: Path = AUDIT_FILE) -> list[dict]:
    """Load all audit records."""
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8", errors="replace").strip().splitlines():
        try:
            records.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            pass
    return records


def filter_session(records: list[dict], session_id: str) -> list[dict]:
    return [r for r in records if r.get("session", "").startswith(session_id[:12])]


# ── analysis ──────────────────────────────────────────────────────────────────

def analyze(records: list[dict]) -> dict:
    """Compute comprehensive token usage statistics."""
    if not records:
        return {"error": "No audit data available. Run a session with the token-audit hook active."}

    # Per-tool breakdown
    by_tool = defaultdict(lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
    for r in records:
        tool = r.get("tool", "unknown")
        by_tool[tool]["calls"] += 1
        by_tool[tool]["input_tokens"] += r.get("input_tokens", 0)
        by_tool[tool]["output_tokens"] += r.get("output_tokens", 0)
        by_tool[tool]["total_tokens"] += r.get("total_tokens", 0)

    # Per-category breakdown (Bash only)
    by_category = defaultdict(lambda: {"calls": 0, "total_tokens": 0, "avg_output_lines": 0})
    bash_records = [r for r in records if r.get("tool") == "Bash"]
    for r in bash_records:
        cat = r.get("category", "other")
        by_category[cat]["calls"] += 1
        by_category[cat]["total_tokens"] += r.get("total_tokens", 0)
        by_category[cat]["avg_output_lines"] += r.get("output_lines", 0)
    for cat in by_category:
        if by_category[cat]["calls"] > 0:
            by_category[cat]["avg_output_lines"] = round(
                by_category[cat]["avg_output_lines"] / by_category[cat]["calls"]
            )

    # Top expensive commands
    top_commands = sorted(
        [r for r in bash_records if r.get("command")],
        key=lambda x: x.get("total_tokens", 0),
        reverse=True,
    )[:20]

    # Session breakdown
    by_session = defaultdict(lambda: {"calls": 0, "total_tokens": 0})
    for r in records:
        sid = r.get("session", "unknown")[:12]
        by_session[sid]["calls"] += 1
        by_session[sid]["total_tokens"] += r.get("total_tokens", 0)

    # Totals
    total_tokens = sum(r.get("total_tokens", 0) for r in records)
    total_calls = len(records)
    total_input = sum(r.get("input_tokens", 0) for r in records)
    total_output = sum(r.get("output_tokens", 0) for r in records)

    # Time range
    timestamps = [r.get("ts", "") for r in records if r.get("ts")]
    first_ts = min(timestamps) if timestamps else "?"
    last_ts = max(timestamps) if timestamps else "?"

    return {
        "total_tokens": total_tokens,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_calls": total_calls,
        "tokens_per_call": round(total_tokens / total_calls) if total_calls else 0,
        "by_tool": dict(by_tool),
        "by_category": dict(by_category),
        "top_commands": [
            {"command": r.get("command", "")[:80], "tokens": r.get("total_tokens", 0),
             "category": r.get("category", ""), "output_lines": r.get("output_lines", 0)}
            for r in top_commands[:10]
        ],
        "sessions": len(by_session),
        "by_session": dict(by_session),
        "period": {"from": first_ts[:19], "to": last_ts[:19]},
    }


# ── formatting ────────────────────────────────────────────────────────────────

def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def format_report(stats: dict) -> str:
    """Format analysis as readable markdown report."""
    if "error" in stats:
        return stats["error"]

    lines = [
        "# Token Efficiency Report",
        f"Period: {stats['period']['from']} — {stats['period']['to']}",
        f"Sessions: {stats['sessions']}",
        "",
        "## Summary",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Tool Calls | {stats['total_calls']:,} |",
        f"| Total Tokens (est.) | {fmt_tokens(stats['total_tokens'])} |",
        f"| Input Tokens | {fmt_tokens(stats['total_input_tokens'])} |",
        f"| Output Tokens | {fmt_tokens(stats['total_output_tokens'])} |",
        f"| Avg Tokens/Call | {stats['tokens_per_call']:,} |",
        "",
        "## Token Distribution by Tool",
        "| Tool | Calls | Tokens | % of Total | Avg/Call |",
        "|------|-------|--------|------------|----------|",
    ]

    total = stats["total_tokens"] or 1
    for tool, data in sorted(stats["by_tool"].items(), key=lambda x: x[1]["total_tokens"], reverse=True):
        pct = round(data["total_tokens"] / total * 100, 1)
        avg = round(data["total_tokens"] / data["calls"]) if data["calls"] else 0
        lines.append(
            f"| {tool} | {data['calls']} | {fmt_tokens(data['total_tokens'])} | {pct}% | {avg:,} |"
        )

    # Bash category breakdown
    if stats["by_category"]:
        lines += [
            "",
            "## Bash Commands by Category",
            "| Category | Calls | Tokens | Avg Output Lines |",
            "|----------|-------|--------|------------------|",
        ]
        for cat, data in sorted(stats["by_category"].items(), key=lambda x: x[1]["total_tokens"], reverse=True):
            lines.append(
                f"| {cat} | {data['calls']} | {fmt_tokens(data['total_tokens'])} | {data['avg_output_lines']} |"
            )

    # Top expensive commands
    if stats["top_commands"]:
        lines += [
            "",
            "## Top 10 Most Expensive Commands",
            "| Command | Tokens | Lines | Category |",
            "|---------|--------|-------|----------|",
        ]
        for cmd in stats["top_commands"]:
            lines.append(
                f"| `{cmd['command'][:60]}` | {fmt_tokens(cmd['tokens'])} | {cmd['output_lines']} | {cmd['category']} |"
            )

    # Efficiency score
    lines += [
        "",
        "## Efficiency Indicators",
    ]
    bash_tokens = stats["by_tool"].get("Bash", {}).get("total_tokens", 0)
    bash_pct = round(bash_tokens / total * 100, 1) if total > 1 else 0
    read_tokens = stats["by_tool"].get("Read", {}).get("total_tokens", 0)
    agent_tokens = stats["by_tool"].get("Agent", {}).get("total_tokens", 0)

    lines.append(f"- **Bash Token Share**: {bash_pct}% of total (lower = more efficient, tools > bash)")
    if bash_pct > 40:
        lines.append("  - HIGH: Consider using Read/Grep/Glob instead of cat/grep/find in Bash")
    elif bash_pct > 20:
        lines.append("  - MODERATE: Some Bash commands could be replaced with dedicated tools")
    else:
        lines.append("  - GOOD: Most work uses dedicated tools (Read, Grep, Glob)")

    return "\n".join(lines)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Token efficiency report")
    parser.add_argument("--session", type=str, help="Filter to specific session ID")
    parser.add_argument("--top", type=int, default=10, help="Top N expensive commands")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--export", type=str, help="Export to markdown file")
    parser.add_argument("--compare", nargs=2, metavar=("SESSION_A", "SESSION_B"),
                        help="Compare two sessions")
    args = parser.parse_args()

    records = load_audit()

    if not records:
        print("No audit data yet. The token-audit hook needs to run for at least one session.")
        print(f"Expected data at: {AUDIT_FILE}")
        return

    if args.session:
        records = filter_session(records, args.session)

    if args.compare:
        a_records = filter_session(records, args.compare[0])
        b_records = filter_session(records, args.compare[1])
        a_stats = analyze(a_records)
        b_stats = analyze(b_records)

        print(f"\n# Session Comparison")
        print(f"\n| Metric | Session A | Session B | Delta |")
        print(f"|--------|-----------|-----------|-------|")
        for key in ["total_tokens", "total_calls", "tokens_per_call"]:
            a_val = a_stats.get(key, 0)
            b_val = b_stats.get(key, 0)
            delta = b_val - a_val
            sign = "+" if delta > 0 else ""
            print(f"| {key} | {a_val:,} | {b_val:,} | {sign}{delta:,} |")
        return

    stats = analyze(records)

    if args.json:
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return

    report = format_report(stats)

    if args.export:
        Path(args.export).write_text(report, encoding="utf-8")
        print(f"Report exported to {args.export}")
    else:
        print(report)


if __name__ == "__main__":
    main()
