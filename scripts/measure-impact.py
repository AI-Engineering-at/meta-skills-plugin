#!/usr/bin/env python3
"""Measure v4.0 Impact — Compare session metrics against 31-session baseline.

Reads all .meta-state-*.json files and produces a comparison report.

Usage:
    python scripts/measure-impact.py              # Full report
    python scripts/measure-impact.py --json        # JSON output
    python scripts/measure-impact.py --session ID  # Single session detail

Baseline (31-Session Report, 2026-04-13):
    Wrong Approach:    43 incidents (1.39/session)
    Buggy Code:        37 incidents (1.19/session)
    Multi-Task:        19/31 sessions (61%)
    Corrections:       14 total (0.45/session)
    Total Friction:    55+ events
"""

import json
import os
import sys
from pathlib import Path

STATE_DIR = Path(os.environ.get(
    "CLAUDE_PLUGIN_DATA",
    Path.home() / ".claude" / "plugins" / "data" / "meta-skills",
))

# --- Baseline from 31-session report (2026-04-13) ---
BASELINE = {
    "sessions": 31,
    "wrong_approach_total": 43,
    "wrong_approach_per_session": 1.39,
    "buggy_code_total": 37,
    "buggy_code_per_session": 1.19,
    "multi_task_sessions": 19,
    "multi_task_pct": 61.3,
    "corrections_total": 14,
    "corrections_per_session": 0.45,
    "friction_total": 55,
}


def load_sessions() -> list[dict]:
    """Load all session state files."""
    sessions = []
    for f in sorted(STATE_DIR.glob(".meta-state-*.json"), key=lambda p: p.stat().st_mtime):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("prompt_count", 0) > 0:
                sessions.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return sessions


def extract_metrics(session: dict) -> dict:
    """Extract measurable metrics from a session state."""
    sid = session.get("session_id", "?")[:12]
    qg = session.get("quality_gate", {})
    sc = session.get("scope_tracker", {})
    cd = session.get("correction_detect", {})
    ag = session.get("approach_guard", {})
    ef = session.get("exploration_first", {})
    meta = session.get("session_meta", {})

    return {
        "session_id": sid,
        "prompts": session.get("prompt_count", 0),
        "project": meta.get("project", "?"),
        # Quality
        "consecutive_failures": qg.get("consecutive_failures", 0),
        "lint_result": qg.get("last_lint_result", "NOT_RUN"),
        "test_result": qg.get("last_test_result", "NOT_RUN"),
        # Scope
        "topic_switches": sc.get("task_switches", 0),
        "domains_seen": len(sc.get("seen_domains", [])),
        "is_multi_task": sc.get("task_switches", 0) >= 3,
        # Corrections
        "corrections": cd.get("correction_count", 0),
        "last_severity": cd.get("last_severity"),
        # Approach
        "bash_commands": ag.get("bash_count", 0),
        "scope_confirmed": ag.get("scope_confirmed", False),
        # Exploration
        "reads_before_write": ef.get("read_count", 0),
        "write_before_read_warned": ef.get("warned", False),
    }


def compare_with_baseline(metrics_list: list[dict]) -> dict:
    """Compare aggregated metrics against baseline."""
    n = len(metrics_list)
    if n == 0:
        return {"error": "No sessions found"}

    total_corrections = sum(m["corrections"] for m in metrics_list)
    total_failures = sum(m["consecutive_failures"] for m in metrics_list)
    multi_task = sum(1 for m in metrics_list if m["is_multi_task"])
    write_before_read = sum(1 for m in metrics_list if m["write_before_read_warned"])

    return {
        "v4_sessions": n,
        "corrections": {
            "total": total_corrections,
            "per_session": round(total_corrections / n, 2),
            "baseline_per_session": BASELINE["corrections_per_session"],
            "delta": round(total_corrections / n - BASELINE["corrections_per_session"], 2),
        },
        "quality_failures": {
            "total": total_failures,
            "per_session": round(total_failures / n, 2),
            "baseline_per_session": BASELINE["buggy_code_per_session"],
            "delta": round(total_failures / n - BASELINE["buggy_code_per_session"], 2),
        },
        "multi_task": {
            "count": multi_task,
            "pct": round(multi_task / n * 100, 1),
            "baseline_pct": BASELINE["multi_task_pct"],
            "delta": round(multi_task / n * 100 - BASELINE["multi_task_pct"], 1),
        },
        "write_before_read": {
            "count": write_before_read,
            "pct": round(write_before_read / n * 100, 1),
        },
    }


def format_delta(value: float, unit: str = "", lower_is_better: bool = True) -> str:
    """Format a delta value with improvement indicator."""
    if value == 0:
        return f"  0{unit} (=)"
    improved = value < 0 if lower_is_better else value > 0
    sign = "+" if value > 0 else ""
    indicator = "BETTER" if improved else "WORSE"
    return f"{sign}{value}{unit} ({indicator})"


def print_report(sessions: list[dict]) -> None:
    """Print human-readable impact report."""
    metrics = [extract_metrics(s) for s in sessions]
    comparison = compare_with_baseline(metrics)

    if "error" in comparison:
        print(f"ERROR: {comparison['error']}")
        sys.exit(1)

    n = comparison["v4_sessions"]
    print("=" * 60)
    print("  meta-skills v4.0 Impact Report")
    print(f"  {n} session(s) vs. 31-session baseline")
    print("=" * 60)

    # Corrections
    c = comparison["corrections"]
    print("\n  CORRECTIONS")
    print(f"    v4.0:     {c['per_session']}/session ({c['total']} total)")
    print(f"    Baseline: {c['baseline_per_session']}/session")
    print(f"    Delta:    {format_delta(c['delta'], '/session')}")

    # Quality failures
    q = comparison["quality_failures"]
    print("\n  QUALITY FAILURES (consecutive)")
    print(f"    v4.0:     {q['per_session']}/session ({q['total']} total)")
    print(f"    Baseline: {q['baseline_per_session']}/session (buggy code)")
    print(f"    Delta:    {format_delta(q['delta'], '/session')}")

    # Multi-task
    m = comparison["multi_task"]
    print("\n  MULTI-TASK SESSIONS")
    print(f"    v4.0:     {m['pct']}% ({m['count']}/{n})")
    print(f"    Baseline: {m['baseline_pct']}% (19/31)")
    print(f"    Delta:    {format_delta(m['delta'], '%')}")

    # Write before read
    w = comparison["write_before_read"]
    print("\n  WRITE-BEFORE-READ WARNINGS")
    print(f"    v4.0:     {w['pct']}% ({w['count']}/{n})")
    print("    Baseline: no data")

    # Per-session detail
    print(f"\n{'─' * 60}")
    print(f"  {'Session':<14} {'Prompts':>7} {'Corr':>5} {'Fails':>6} {'Switches':>9} {'Lint':>8}")
    print(f"  {'─' * 14} {'─' * 7} {'─' * 5} {'─' * 6} {'─' * 9} {'─' * 8}")
    for m in metrics:
        print(
            f"  {m['session_id']:<14} "
            f"{m['prompts']:>7} "
            f"{m['corrections']:>5} "
            f"{m['consecutive_failures']:>6} "
            f"{m['topic_switches']:>9} "
            f"{m['lint_result']:>8}"
        )

    # Verdict
    print(f"\n{'=' * 60}")
    deltas = [c["delta"], q["delta"], m["delta"]]
    improved = sum(1 for d in deltas if d < 0)
    worse = sum(1 for d in deltas if d > 0)

    if n < 5:
        print(f"  VERDICT: INSUFFICIENT DATA ({n}/5 sessions)")
        print(f"  Need {5 - n} more sessions for meaningful comparison.")
    elif improved > worse:
        print(f"  VERDICT: IMPROVEMENT ({improved}/3 metrics better)")
    elif worse > improved:
        print(f"  VERDICT: REGRESSION ({worse}/3 metrics worse)")
    else:
        print(f"  VERDICT: MIXED ({improved} better, {worse} worse)")
    print("=" * 60)


def print_json(sessions: list[dict]) -> None:
    """Print JSON output."""
    metrics = [extract_metrics(s) for s in sessions]
    comparison = compare_with_baseline(metrics)
    output = {
        "baseline": BASELINE,
        "comparison": comparison,
        "sessions": metrics,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def print_single_session(sessions: list[dict], session_id: str) -> None:
    """Print detail for a single session."""
    for s in sessions:
        if session_id in s.get("session_id", ""):
            m = extract_metrics(s)
            print(json.dumps(m, ensure_ascii=False, indent=2))
            return
    print(f"Session '{session_id}' not found.")
    sys.exit(1)


def main():
    args = sys.argv[1:]
    sessions = load_sessions()

    if "--json" in args:
        print_json(sessions)
    elif "--session" in args:
        idx = args.index("--session")
        if idx + 1 < len(args):
            print_single_session(sessions, args[idx + 1])
        else:
            print("Usage: --session SESSION_ID")
            sys.exit(1)
    else:
        print_report(sessions)


if __name__ == "__main__":
    main()
