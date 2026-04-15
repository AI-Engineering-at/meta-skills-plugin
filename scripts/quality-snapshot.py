#!/usr/bin/env python3
"""Quality Snapshot — Lightweight quality measurement for session-end.

Runs eval.py + validate.py, computes aggregate stats, compares to baseline,
writes snapshot to oversight/snapshots/.

Usage:
  python3 quality-snapshot.py           # Verbose output
  python3 quality-snapshot.py --quiet   # One-line summary for hooks
  python3 quality-snapshot.py --json    # JSON output
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_ROOT = Path(os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    Path(__file__).parent.parent
))
SNAPSHOT_DIR = PLUGIN_ROOT / "oversight" / "snapshots"


def run_eval() -> list:
    """Run eval.py --all --json and return parsed results."""
    eval_script = PLUGIN_ROOT / "scripts" / "eval.py"
    if not eval_script.exists():
        return []
    try:
        result = subprocess.run(
            [sys.executable, str(eval_script), "--all", "--json"],
            capture_output=True, text=True, timeout=30,
            cwd=str(PLUGIN_ROOT.parent),  # Run from phantom-ai root so eval.py finds skills
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        pass
    return []


def run_validate() -> dict:
    """Run validate.py --json and return parsed results."""
    validate_script = PLUGIN_ROOT / "scripts" / "validate.py"
    if not validate_script.exists():
        return {"errors": 0, "warnings": 0}
    try:
        result = subprocess.run(
            [sys.executable, str(validate_script), "--json"],
            capture_output=True, text=True, timeout=15,
            cwd=str(PLUGIN_ROOT),
        )
        if result.returncode in (0, 1) and result.stdout.strip():
            data = json.loads(result.stdout)
            return {
                "errors": data.get("errors", 0),
                "warnings": data.get("warnings", 0),
            }
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        pass
    return {"errors": -1, "warnings": -1}


def load_baseline() -> dict | None:
    """Load latest baseline snapshot."""
    if not SNAPSHOT_DIR.exists():
        return None
    snapshots = sorted(SNAPSHOT_DIR.glob("*.json"), reverse=True)
    for sf in snapshots:
        try:
            data = json.loads(sf.read_text(encoding="utf-8"))
            if data.get("type") == "snapshot":
                return data
        except Exception:
            continue
    return None


def main():
    quiet = "--quiet" in sys.argv
    as_json = "--json" in sys.argv

    # Run evaluations
    eval_results = run_eval()
    validate_results = run_validate()

    # Compute stats
    scores = []
    for item in eval_results:
        if isinstance(item, dict) and "score" in item:
            scores.append(item["score"])

    total = len(scores)
    avg_score = sum(scores) / total if total else 0
    below_70 = sum(1 for s in scores if s < 70)
    above_90 = sum(1 for s in scores if s >= 90)

    # Load baseline for delta
    baseline = load_baseline()
    delta = 0
    if baseline and baseline.get("avg_score"):
        delta = avg_score - baseline["avg_score"]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    date_label = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    snapshot = {
        "type": "snapshot",
        "timestamp": now,
        "total_items": total,
        "avg_score": round(avg_score, 1),
        "below_70": below_70,
        "above_90": above_90,
        "validation_errors": validate_results.get("errors", -1),
        "validation_warnings": validate_results.get("warnings", -1),
        "delta_vs_baseline": round(delta, 1),
        "scores": scores,
    }

    # Save snapshot
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_file = SNAPSHOT_DIR / f"snapshot-{date_label}.json"
    snapshot_file.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")

    # Output
    if as_json:
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
    elif quiet:
        delta_str = f"+{delta:.0f}" if delta >= 0 else f"{delta:.0f}"
        print(f"Quality: avg {avg_score:.0f}/100 ({delta_str} vs baseline), "
              f"{below_70} below 70, {validate_results.get('errors', '?')} validation errors")
    else:
        print(f"QUALITY DASHBOARD ({date_label}):")
        print(f"  Items scored: {total}")
        print(f"  Avg Score: {avg_score:.0f}/100", end="")
        if baseline:
            print(f" ({'+' if delta >= 0 else ''}{delta:.0f} vs baseline)")
        else:
            print(" (no baseline)")
        print(f"  Below 70: {below_70}")
        print(f"  Above 90: {above_90}")
        print(f"  Validation: {validate_results.get('errors', '?')} errors, "
              f"{validate_results.get('warnings', '?')} warnings")
        print(f"  Snapshot: {snapshot_file}")


if __name__ == "__main__":
    main()
