#!/usr/bin/env python3
"""oversight.py — External Validator for the eval system.

Three layers:
  Layer 1: eval.py (internal scanner) — scores, misclassification
  Layer 2: Calibration (human ground truth) — precision/recall of eval
  Layer 3: External metrics (errors, learnings, corrections) — is the SYSTEM improving?

Usage:
  python oversight.py baseline              # Save current snapshot as baseline
  python oversight.py calibrate             # Show calibration set for human review
  python oversight.py check                 # Run full oversight check
  python oversight.py delta                 # Compare current state to baseline
  python oversight.py report [--md]         # Full oversight report
"""
import json
import os
import subprocess
import sys
import re
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
OVERSIGHT_DIR = SCRIPT_DIR.parent / "oversight"
CALIBRATION_FILE = OVERSIGHT_DIR / "calibration.jsonl"
SNAPSHOTS_DIR = OVERSIGHT_DIR / "snapshots"
ERROR_REGISTRY = REPO_ROOT / ".claude" / "knowledge" / "ERROR_REGISTRY.md"
LEARNINGS_REGISTRY = REPO_ROOT / ".claude" / "knowledge" / "LEARNINGS_REGISTRY.md"
REPORTS_DIR = REPO_ROOT / "docs" / "reports"


def ensure_dirs():
    OVERSIGHT_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)


# --- Layer 1: Run eval.py ---

def run_eval() -> dict:
    """Run eval.py --all and return parsed JSON."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "eval.py"), "--all"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(REPO_ROOT),
    )
    return json.loads(result.stdout)


def run_validate() -> dict:
    """Run validate.py --json and return parsed JSON."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "validate.py"), "--json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(REPO_ROOT),
    )
    return json.loads(result.stdout)


# --- Layer 2: Calibration ---

def load_calibration() -> list[dict]:
    """Load human calibration judgments."""
    if not CALIBRATION_FILE.exists():
        return []
    entries = []
    for line in CALIBRATION_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.append(json.loads(line))
    return entries


def compute_calibration_metrics(calibration: list[dict], validate_data: dict) -> dict:
    """Compare validate.py warnings against human ground truth.

    Returns precision, recall, F1, and lists of false positives/negatives.
    """
    if not calibration:
        return {"error": "No calibration data. Run: python oversight.py calibrate"}

    # Validate flagged items (items with errors or warnings)
    validate_flagged = {r["name"] for r in validate_data.get("results", [])
                        if r["error_count"] > 0 or r["warning_count"] > 0}

    # Human ground truth
    human_flagged = {c["name"] for c in calibration if c.get("joe_agrees")}
    human_ok = {c["name"] for c in calibration if c.get("joe_agrees") is False}

    calibrated_names = {c["name"] for c in calibration}
    validate_flagged_calibrated = validate_flagged & calibrated_names

    true_positives = validate_flagged_calibrated & human_flagged
    false_positives = validate_flagged_calibrated & human_ok
    false_negatives = human_flagged - validate_flagged_calibrated

    tp = len(true_positives)
    fp = len(false_positives)
    fn = len(false_negatives)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "total_calibrated": len(calibration),
        "true_positives": sorted(true_positives),
        "false_positives": sorted(false_positives),
        "false_negatives": sorted(false_negatives),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }


# --- Layer 3: External Metrics ---

def count_registry_entries(filepath: Path, pattern: str) -> int:
    """Count lines matching pattern in a registry file."""
    if not filepath.exists():
        return 0
    count = 0
    for line in filepath.read_text(encoding="utf-8").splitlines():
        if re.match(pattern, line):
            count += 1
    return count


def count_session_misunderstandings() -> dict:
    """Count misunderstandings from session retrospectives."""
    results = {}
    if not REPORTS_DIR.exists():
        return results
    for f in sorted(REPORTS_DIR.glob("session-retrospective-*.md")):
        date = f.stem.replace("session-retrospective-", "")
        count = 0
        in_table = False
        for line in f.read_text(encoding="utf-8").splitlines():
            if "Missverstaendnisse" in line:
                in_table = True
                continue
            if in_table and re.match(r"^\| \d", line):
                count += 1
            if in_table and line.strip() and not line.startswith("|"):
                in_table = False
        results[date] = count
    return results


def collect_external_metrics() -> dict:
    """Gather all external metrics that eval.py doesn't measure."""
    errors = count_registry_entries(ERROR_REGISTRY, r"^\| E\d")
    learnings = count_registry_entries(LEARNINGS_REGISTRY, r"^\| L\d")
    misunderstandings = count_session_misunderstandings()

    return {
        "error_registry_entries": errors,
        "learnings_registry_entries": learnings,
        "session_misunderstandings": misunderstandings,
        "total_misunderstandings": sum(misunderstandings.values()),
        "sessions_tracked": len(misunderstandings),
    }


# --- Snapshots ---

def take_snapshot(label: str = "current") -> dict:
    """Take a full snapshot of all three layers."""
    eval_data = run_eval()
    validate_data = run_validate()
    calibration = load_calibration()
    external = collect_external_metrics()

    scores = [r["quality"]["score"] for r in eval_data["results"]]
    skill_scores = [r["quality"]["score"] for r in eval_data["results"] if r["type"] == "skill"]
    agent_scores = [r["quality"]["score"] for r in eval_data["results"] if r["type"] == "agent"]

    # Complexity distribution
    complexity_dist = {}
    for r in eval_data["results"]:
        c = r.get("quality", {}).get("declared_complexity", "unknown")
        complexity_dist[c] = complexity_dist.get(c, 0) + 1

    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "label": label,
        "script_versions": {"eval": 3, "validate": 1, "oversight": 2},
        "layer1_eval": {
            "total_items": eval_data["total"],
            "skills": eval_data["skills"],
            "agents": eval_data["agents"],
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "avg_skill_score": round(sum(skill_scores) / len(skill_scores), 1) if skill_scores else 0,
            "avg_agent_score": round(sum(agent_scores) / len(agent_scores), 1) if agent_scores else 0,
            "below_70": len([s for s in scores if s < 70]),
            "above_90": len([s for s in scores if s >= 90]),
            "complexity_distribution": complexity_dist,
            "schema_errors": validate_data["errors"],
            "schema_warnings": validate_data["warnings"],
            "schema_clean": validate_data["clean"],
            "score_distribution": {r["name"]: r["quality"]["score"] for r in eval_data["results"]},
        },
        "layer2_calibration": compute_calibration_metrics(calibration, validate_data),
        "layer3_external": external,
    }
    return snapshot


def save_snapshot(snapshot: dict, name: str):
    ensure_dirs()
    path = SNAPSHOTS_DIR / f"{name}.json"
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_snapshot(name: str) -> dict | None:
    path = SNAPSHOTS_DIR / f"{name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# --- Delta Report ---

def compute_delta(before: dict, after: dict) -> dict:
    """Compute improvement delta between two snapshots."""
    b1 = before["layer1_eval"]
    a1 = after["layer1_eval"]
    b3 = before["layer3_external"]
    a3 = after["layer3_external"]

    delta = {
        "before_label": before["label"],
        "after_label": after["label"],
        "before_timestamp": before["timestamp"],
        "after_timestamp": after["timestamp"],
        "score_delta": round(a1["avg_score"] - b1["avg_score"], 1),
        "skill_score_delta": round(a1["avg_skill_score"] - b1["avg_skill_score"], 1),
        "agent_score_delta": round(a1["avg_agent_score"] - b1["avg_agent_score"], 1),
        "schema_errors_delta": a1.get("schema_errors", 0) - b1.get("schema_errors", 0),
        "schema_warnings_delta": a1.get("schema_warnings", 0) - b1.get("schema_warnings", 0),
        "below_70_delta": a1["below_70"] - b1["below_70"],
        "above_90_delta": a1["above_90"] - b1["above_90"],
        "items_delta": a1["total_items"] - b1["total_items"],
        "error_delta": a3["error_registry_entries"] - b3["error_registry_entries"],
        "learnings_delta": a3["learnings_registry_entries"] - b3["learnings_registry_entries"],
        "misunderstanding_delta": a3["total_misunderstandings"] - b3["total_misunderstandings"],
    }

    # Calibration improvement
    b2 = before.get("layer2_calibration", {})
    a2 = after.get("layer2_calibration", {})
    if "precision" in b2 and "precision" in a2:
        delta["precision_delta"] = round(a2["precision"] - b2["precision"], 3)
        delta["recall_delta"] = round(a2["recall"] - b2["recall"], 3)
        delta["f1_delta"] = round(a2["f1"] - b2["f1"], 3)

    # Verdict
    improvements = 0
    regressions = 0
    if delta["score_delta"] > 0:
        improvements += 1
    elif delta["score_delta"] < 0:
        regressions += 1
    if delta["schema_errors_delta"] < 0:
        improvements += 1
    elif delta["schema_errors_delta"] > 0:
        regressions += 1
    if delta["schema_warnings_delta"] < 0:
        improvements += 1
    elif delta["schema_warnings_delta"] > 0:
        regressions += 1
    if delta["below_70_delta"] < 0:
        improvements += 1
    elif delta["below_70_delta"] > 0:
        regressions += 1

    if improvements > regressions:
        delta["verdict"] = "IMPROVED"
    elif regressions > improvements:
        delta["verdict"] = "REGRESSED"
    else:
        delta["verdict"] = "NEUTRAL"

    return delta


def format_delta_sign(val) -> str:
    if isinstance(val, (int, float)):
        if val > 0:
            return f"+{val}"
        return str(val)
    return str(val)


# --- Report ---

def format_report(snapshot: dict, delta: dict | None = None, markdown: bool = False) -> str:
    lines = []
    ts = snapshot["timestamp"][:19]
    label = snapshot["label"]

    if markdown:
        lines.append(f"# Oversight Report — {label}")
        lines.append(f"\n> Generated: {ts}\n")
    else:
        lines.append(f"=== Oversight Report: {label} ({ts}) ===\n")

    # Layer 1
    e = snapshot["layer1_eval"]
    if markdown:
        lines.append("## Layer 1: eval.py (Internal Scanner)\n")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
    else:
        lines.append("--- Layer 1: eval.py ---")

    metrics_l1 = [
        ("Total Items", e["total_items"]),
        ("Skills / Agents", f"{e['skills']} / {e['agents']}"),
        ("Avg Score", e["avg_score"]),
        ("Avg Skill Score", e["avg_skill_score"]),
        ("Avg Agent Score", e["avg_agent_score"]),
        ("Below 70", e["below_70"]),
        ("Above 90", e["above_90"]),
        ("Complexity", " | ".join(f"{k}: {v}" for k, v in sorted(e.get("complexity_distribution", {}).items()))),
        ("Schema Errors", e.get("schema_errors", "N/A")),
        ("Schema Warnings", e.get("schema_warnings", "N/A")),
        ("Schema Clean", e.get("schema_clean", "N/A")),
    ]
    for name, val in metrics_l1:
        if markdown:
            lines.append(f"| {name} | {val} |")
        else:
            lines.append(f"  {name}: {val}")

    # Layer 2
    c = snapshot["layer2_calibration"]
    if markdown:
        lines.append("\n## Layer 2: Calibration (Human Ground Truth)\n")
    else:
        lines.append("\n--- Layer 2: Calibration ---")

    if "error" in c:
        lines.append(f"  {c['error']}")
    else:
        cal_metrics = [
            ("Calibrated Items", c["total_calibrated"]),
            ("True Positives (eval correct)", c["tp"]),
            ("False Positives (eval wrong: flagged OK items)", c["fp"]),
            ("False Negatives (eval missed real issues)", c["fn"]),
            ("Precision", f"{c['precision']:.1%}"),
            ("Recall", f"{c['recall']:.1%}"),
            ("F1 Score", f"{c['f1']:.1%}"),
        ]
        if markdown:
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
        for name, val in cal_metrics:
            if markdown:
                lines.append(f"| {name} | {val} |")
            else:
                lines.append(f"  {name}: {val}")

        if c["false_positives"]:
            lines.append(f"\n  False Positives (eval says wrong, Joe says OK): {', '.join(c['false_positives'])}")
        if c["false_negatives"]:
            lines.append(f"  False Negatives (eval missed): {', '.join(c['false_negatives'])}")

    # Layer 3
    x = snapshot["layer3_external"]
    if markdown:
        lines.append("\n## Layer 3: External Metrics\n")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
    else:
        lines.append("\n--- Layer 3: External Metrics ---")

    ext_metrics = [
        ("Error Registry Entries", x["error_registry_entries"]),
        ("Learnings Registry Entries", x["learnings_registry_entries"]),
        ("Sessions Tracked", x["sessions_tracked"]),
        ("Total Misunderstandings", x["total_misunderstandings"]),
    ]
    for name, val in ext_metrics:
        if markdown:
            lines.append(f"| {name} | {val} |")
        else:
            lines.append(f"  {name}: {val}")

    if x["session_misunderstandings"]:
        lines.append("")
        for date, count in sorted(x["session_misunderstandings"].items()):
            lines.append(f"  Session {date}: {count} misunderstandings")

    # Delta
    if delta:
        if markdown:
            lines.append(f"\n## Delta: {delta['before_label']} -> {delta['after_label']}\n")
            lines.append("| Metric | Change |")
            lines.append("|--------|--------|")
        else:
            lines.append(f"\n--- Delta: {delta['before_label']} -> {delta['after_label']} ---")

        delta_metrics = [
            ("Score", delta["score_delta"]),
            ("Skill Score", delta["skill_score_delta"]),
            ("Agent Score", delta["agent_score_delta"]),
            ("Schema Errors", delta.get("schema_errors_delta", 0)),
            ("Schema Warnings", delta.get("schema_warnings_delta", 0)),
            ("Below 70", delta["below_70_delta"]),
            ("Above 90", delta["above_90_delta"]),
            ("Items", delta["items_delta"]),
            ("Errors (Registry)", delta["error_delta"]),
            ("Learnings", delta["learnings_delta"]),
        ]
        if "precision_delta" in delta:
            delta_metrics.extend([
                ("Precision", delta["precision_delta"]),
                ("Recall", delta["recall_delta"]),
                ("F1", delta["f1_delta"]),
            ])

        for name, val in delta_metrics:
            formatted = format_delta_sign(val)
            if markdown:
                lines.append(f"| {name} | {formatted} |")
            else:
                lines.append(f"  {name}: {formatted}")

        if markdown:
            lines.append(f"\n**Verdict: {delta['verdict']}**")
        else:
            lines.append(f"\n  VERDICT: {delta['verdict']}")

    return "\n".join(lines)


# --- CLI ---

def cmd_baseline():
    """Save current state as baseline."""
    ensure_dirs()
    snapshot = take_snapshot("baseline")
    path = save_snapshot(snapshot, "baseline")
    print(f"Baseline saved: {path}")
    print(format_report(snapshot))


def cmd_calibrate():
    """Show validate.py warnings for human review."""
    ensure_dirs()
    val = run_validate()
    existing = {c["name"]: c for c in load_calibration()}

    flagged = [r for r in val["results"] if r["warning_count"] > 0 or r["error_count"] > 0]
    print("=== Calibration Set ===")
    print(f"validate.py flags {len(flagged)} items with warnings/errors.\n")
    print("Review each item. Edit calibration.jsonl to set joe_agrees: true/false.\n")

    items = []
    for r in flagged:
        name = r["name"]
        issues = r["errors"] + r["warnings"]
        if name in existing:
            status = "REVIEWED" if existing[name].get("joe_agrees") is not None else "PENDING"
            joe = existing[name].get("joe_agrees", "?")
        else:
            status = "NEW"
            joe = "?"
        print(f"  [{status}] {name} ({r['location']}/{r['complexity']}): {len(issues)} issues  joe_agrees={joe}")
        for issue in issues[:3]:
            print(f"           {issue}")
        if name not in existing:
            items.append({
                "name": name,
                "type": r["location"],
                "eval_issue": "; ".join(issues[:3]),
                "joe_agrees": None,
                "reason": "",
            })

    if items:
        with open(CALIBRATION_FILE, "a", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"\n{len(items)} new items added to {CALIBRATION_FILE}")
        print("Edit the file: set joe_agrees to true or false for each item.")


def cmd_check():
    """Run full oversight check."""
    snapshot = take_snapshot("check")
    baseline = load_snapshot("baseline")
    delta = compute_delta(baseline, snapshot) if baseline else None
    print(format_report(snapshot, delta))


def cmd_delta():
    """Compare current to baseline."""
    baseline = load_snapshot("baseline")
    if not baseline:
        print("ERROR: No baseline found. Run: python oversight.py baseline")
        return
    current = take_snapshot("current")
    delta = compute_delta(baseline, current)
    print(format_report(current, delta))


def cmd_report(markdown: bool = False):
    """Full report, optionally as markdown."""
    snapshot = take_snapshot("report")
    baseline = load_snapshot("baseline")
    delta = compute_delta(baseline, snapshot) if baseline else None
    report = format_report(snapshot, delta, markdown=markdown)
    if markdown:
        path = save_snapshot(snapshot, f"report-{datetime.now().strftime('%Y-%m-%d')}")
        print(report)
        print(f"\nSnapshot saved: {path}")
    else:
        print(report)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "check":
        cmd_check()
    elif args[0] == "baseline":
        cmd_baseline()
    elif args[0] == "calibrate":
        cmd_calibrate()
    elif args[0] == "delta":
        cmd_delta()
    elif args[0] == "report":
        cmd_report(markdown="--md" in args)
    else:
        print(__doc__)
