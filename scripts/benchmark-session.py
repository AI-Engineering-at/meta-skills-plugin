#!/usr/bin/env python3
"""benchmark-session.py — Standalone token efficiency benchmark.

Runs a standardized workload in ANY Claude Code session — with or without
the meta-skills plugin. Produces comparable metrics for before/after analysis.

ZERO dependencies beyond Python stdlib. Works on Windows, macOS, Linux.
Copy this single file into any project and run it.

Usage:
  python benchmark-session.py                # Full benchmark
  python benchmark-session.py --quick        # Quick version (30s)
  python benchmark-session.py --export FILE  # Save results as JSON
  python benchmark-session.py --compare A B  # Compare two result files

The benchmark does NOT modify anything. Read-only operations only.

How to use for before/after comparison:
  1. BEFORE: Run in vanilla Claude Code session, save results
     python benchmark-session.py --export baseline-vanilla.json
  2. AFTER: Run in session with meta-skills plugin, save results
     python benchmark-session.py --export baseline-plugin.json
  3. COMPARE:
     python benchmark-session.py --compare baseline-vanilla.json baseline-plugin.json
"""
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SYSTEM = platform.system()
CWD = os.getcwd()

# ── token estimation ──────────────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """Estimate LLM tokens. ~4 chars per token (conservative)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def measure_command(cmd: str, label: str, timeout: int = 30) -> dict:
    """Execute a command and measure its output cost."""
    start = time.time()
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=CWD,
        )
        elapsed = time.time() - start
        stdout = r.stdout or ""
        stderr = r.stderr or ""
        output = stdout + stderr

        return {
            "label": label,
            "command": cmd,
            "exit_code": r.returncode,
            "stdout_bytes": len(stdout.encode("utf-8", errors="replace")),
            "stderr_bytes": len(stderr.encode("utf-8", errors="replace")),
            "output_bytes": len(output.encode("utf-8", errors="replace")),
            "output_lines": output.count("\n"),
            "estimated_tokens": estimate_tokens(output),
            "elapsed_s": round(elapsed, 3),
        }
    except subprocess.TimeoutExpired:
        return {
            "label": label, "command": cmd, "exit_code": -1,
            "stdout_bytes": 0, "stderr_bytes": 0, "output_bytes": 0,
            "output_lines": 0, "estimated_tokens": 0,
            "elapsed_s": timeout, "error": "timeout",
        }
    except Exception as e:
        return {
            "label": label, "command": cmd, "exit_code": -1,
            "stdout_bytes": 0, "stderr_bytes": 0, "output_bytes": 0,
            "output_lines": 0, "estimated_tokens": 0,
            "elapsed_s": 0, "error": str(e),
        }


def measure_file_read(path: str, label: str) -> dict:
    """Measure cost of reading a file (simulates Claude's Read tool)."""
    start = time.time()
    try:
        content = Path(path).read_text(encoding="utf-8", errors="replace")
        elapsed = time.time() - start
        return {
            "label": label,
            "command": f"Read({path})",
            "exit_code": 0,
            "output_bytes": len(content.encode("utf-8", errors="replace")),
            "output_lines": content.count("\n"),
            "estimated_tokens": estimate_tokens(content),
            "elapsed_s": round(elapsed, 3),
        }
    except Exception as e:
        return {
            "label": label, "command": f"Read({path})", "exit_code": -1,
            "output_bytes": 0, "output_lines": 0, "estimated_tokens": 0,
            "elapsed_s": 0, "error": str(e),
        }


# ── workload definition ──────────────────────────────────────────────────────

def detect_project() -> dict:
    """Detect what kind of project we're in."""
    info = {"name": Path(CWD).name, "type": "unknown", "files": 0}

    if Path(CWD, "package.json").exists():
        info["type"] = "node"
    elif Path(CWD, "pyproject.toml").exists() or Path(CWD, "setup.py").exists():
        info["type"] = "python"
    elif Path(CWD, "Cargo.toml").exists():
        info["type"] = "rust"
    elif Path(CWD, "go.mod").exists():
        info["type"] = "go"

    info["has_git"] = Path(CWD, ".git").exists()
    info["has_claude"] = Path(CWD, "CLAUDE.md").exists() or Path(CWD, ".claude").exists()

    return info


def build_workload(quick: bool = False) -> list[dict]:
    """Build standardized workload based on project type."""
    project = detect_project()
    tasks = []

    # ── Git operations (if git repo) ──
    if project["has_git"]:
        tasks.append({"type": "cmd", "cmd": "git status", "label": "git-status-full"})
        tasks.append({"type": "cmd", "cmd": "git status --short", "label": "git-status-short"})
        tasks.append({"type": "cmd", "cmd": "git log --oneline -20", "label": "git-log-short"})
        tasks.append({"type": "cmd", "cmd": "git log -20", "label": "git-log-full"})
        tasks.append({"type": "cmd", "cmd": "git diff --stat HEAD~5..HEAD", "label": "git-diff-stat"})
        if not quick:
            tasks.append({"type": "cmd", "cmd": "git diff HEAD~3..HEAD", "label": "git-diff-full"})
            tasks.append({"type": "cmd", "cmd": "git branch -a", "label": "git-branches"})

    # ── Directory listing ──
    tasks.append({"type": "cmd", "cmd": "ls -la", "label": "ls-full"})
    tasks.append({"type": "cmd", "cmd": "ls -1", "label": "ls-compact"})
    if not quick:
        tasks.append({"type": "cmd", "cmd": "find . -maxdepth 2 -type f | head -100", "label": "find-files"})

    # ── File reads (common files) ──
    for fname in ["CLAUDE.md", "README.md", "package.json", "pyproject.toml", "Cargo.toml"]:
        fpath = Path(CWD, fname)
        if fpath.exists():
            tasks.append({"type": "read", "path": str(fpath), "label": f"read-{fname}"})

    # ── Search operations ──
    tasks.append({"type": "cmd", "cmd": "grep -r 'TODO' --include='*.py' --include='*.ts' --include='*.js' -l . 2>/dev/null | head -20", "label": "grep-todos"})
    tasks.append({"type": "cmd", "cmd": "grep -rn 'import' --include='*.py' . 2>/dev/null | head -50", "label": "grep-imports"})
    if not quick:
        tasks.append({"type": "cmd", "cmd": "grep -rn 'error\\|Error\\|ERROR' --include='*.py' --include='*.ts' . 2>/dev/null | head -50", "label": "grep-errors"})

    # ── Project-specific ──
    if project["type"] == "python":
        tasks.append({"type": "cmd", "cmd": "python --version 2>&1", "label": "python-version"})
        if not quick:
            tasks.append({"type": "cmd", "cmd": "pip list 2>/dev/null | head -30", "label": "pip-list"})

    if project["type"] == "node":
        tasks.append({"type": "cmd", "cmd": "node --version 2>&1", "label": "node-version"})
        if not quick:
            tasks.append({"type": "cmd", "cmd": "npm ls --depth=0 2>/dev/null | head -30", "label": "npm-list"})

    # ── Docker (if available) ──
    tasks.append({"type": "cmd", "cmd": "docker ps 2>/dev/null", "label": "docker-ps-full"})
    tasks.append({"type": "cmd", "cmd": "docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null", "label": "docker-ps-compact"})

    # ── System info ──
    tasks.append({"type": "cmd", "cmd": "uname -a 2>/dev/null || ver 2>/dev/null", "label": "system-info"})

    return tasks


# ── benchmark runner ──────────────────────────────────────────────────────────

def run_benchmark(quick: bool = False) -> dict:
    """Execute the full benchmark workload."""
    project = detect_project()
    tasks = build_workload(quick=quick)
    results = []

    print("\nMeta-Skills Token Benchmark")
    print(f"{'=' * 60}")
    print(f"Project: {project['name']} ({project['type']})")
    print(f"Platform: {SYSTEM}")
    print(f"Tasks: {len(tasks)}")
    print(f"Mode: {'quick' if quick else 'full'}")
    print(f"{'=' * 60}\n")

    for i, task in enumerate(tasks):
        label = task["label"]
        sys.stdout.write(f"  [{i + 1}/{len(tasks)}] {label:30s} ... ")
        sys.stdout.flush()

        if task["type"] == "cmd":
            result = measure_command(task["cmd"], label)
        elif task["type"] == "read":
            result = measure_file_read(task["path"], label)
        else:
            continue

        results.append(result)
        tokens = result["estimated_tokens"]
        elapsed = result["elapsed_s"]
        print(f"{tokens:>8,} tok  {elapsed:>5.1f}s")

    # ── Analysis ──
    total_tokens = sum(r["estimated_tokens"] for r in results)
    total_bytes = sum(r["output_bytes"] for r in results)
    total_time = sum(r["elapsed_s"] for r in results)

    # Pair analysis: full vs compact commands
    pairs = [
        ("git-status-full", "git-status-short"),
        ("git-log-full", "git-log-short"),
        ("ls-full", "ls-compact"),
        ("docker-ps-full", "docker-ps-compact"),
    ]
    pair_savings = []
    results_by_label = {r["label"]: r for r in results}
    for full_label, compact_label in pairs:
        full = results_by_label.get(full_label)
        compact = results_by_label.get(compact_label)
        if full and compact and full["estimated_tokens"] > 0:
            saving_pct = round(
                (1 - compact["estimated_tokens"] / full["estimated_tokens"]) * 100
            )
            pair_savings.append({
                "full": full_label,
                "compact": compact_label,
                "full_tokens": full["estimated_tokens"],
                "compact_tokens": compact["estimated_tokens"],
                "saving_pct": saving_pct,
            })

    # ── Output ──
    print(f"\n{'=' * 60}")
    print("RESULTS")
    print(f"{'=' * 60}")
    print(f"  Total estimated tokens: {total_tokens:>10,}")
    print(f"  Total output bytes:     {total_bytes:>10,}")
    print(f"  Total time:             {total_time:>10.1f}s")
    print(f"  Avg tokens/operation:   {total_tokens // len(results):>10,}")

    if pair_savings:
        print("\n  Compact vs Full Comparison:")
        for p in pair_savings:
            print(f"    {p['full']:25s} {p['full_tokens']:>6,} tok -> "
                  f"{p['compact']:25s} {p['compact_tokens']:>6,} tok  "
                  f"({p['saving_pct']}% saved)")

    avg_saving = 0
    if pair_savings:
        avg_saving = round(sum(p["saving_pct"] for p in pair_savings) / len(pair_savings))
        print(f"\n  Average compact saving: {avg_saving}%")

    return {
        "benchmark_version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "platform": SYSTEM,
        "project": project,
        "mode": "quick" if quick else "full",
        "tasks": len(tasks),
        "total_tokens": total_tokens,
        "total_bytes": total_bytes,
        "total_time_s": round(total_time, 2),
        "avg_tokens_per_op": total_tokens // len(results) if results else 0,
        "pair_savings": pair_savings,
        "avg_compact_saving_pct": avg_saving,
        "results": results,
        "has_meta_skills": Path(CWD, "meta-skills").exists(),
        "plugin_active": bool(os.environ.get("CLAUDE_PLUGIN_DATA")),
    }


# ── comparison ────────────────────────────────────────────────────────────────

def compare_results(file_a: str, file_b: str):
    """Compare two benchmark result files."""
    a = json.loads(Path(file_a).read_text(encoding="utf-8"))
    b = json.loads(Path(file_b).read_text(encoding="utf-8"))

    print("\nBenchmark Comparison")
    print(f"{'=' * 70}")
    print(f"  A: {file_a} ({a.get('timestamp', '?')[:19]})")
    print(f"  B: {file_b} ({b.get('timestamp', '?')[:19]})")
    print(f"  Plugin active: A={a.get('plugin_active')}, B={b.get('plugin_active')}")
    print(f"{'=' * 70}\n")

    print(f"  {'Metric':30s} {'A':>12s} {'B':>12s} {'Delta':>12s}")
    print(f"  {'-' * 66}")

    metrics = [
        ("Total Tokens", "total_tokens"),
        ("Total Bytes", "total_bytes"),
        ("Total Time (s)", "total_time_s"),
        ("Avg Tokens/Op", "avg_tokens_per_op"),
        ("Avg Compact Saving %", "avg_compact_saving_pct"),
        ("Tasks", "tasks"),
    ]

    for label, key in metrics:
        va = a.get(key, 0)
        vb = b.get(key, 0)
        delta = vb - va
        sign = "+" if delta > 0 else ""
        pct = ""
        if va and va > 0:
            pct_val = round((delta / va) * 100)
            pct = f" ({'+' if pct_val > 0 else ''}{pct_val}%)"
        print(f"  {label:30s} {va:>12,} {vb:>12,} {sign}{delta:>11,}{pct}")

    # Per-operation comparison
    a_by_label = {r["label"]: r for r in a.get("results", [])}
    b_by_label = {r["label"]: r for r in b.get("results", [])}
    common = sorted(set(a_by_label) & set(b_by_label))

    if common:
        print(f"\n  {'Operation':30s} {'A tok':>8s} {'B tok':>8s} {'Delta':>8s}")
        print(f"  {'-' * 54}")
        for label in common:
            ta = a_by_label[label]["estimated_tokens"]
            tb = b_by_label[label]["estimated_tokens"]
            delta = tb - ta
            if delta != 0:
                print(f"  {label:30s} {ta:>8,} {tb:>8,} {delta:>+8,}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Token efficiency benchmark")
    parser.add_argument("--quick", action="store_true", help="Quick benchmark (~30s)")
    parser.add_argument("--export", type=str, help="Export results to JSON file")
    parser.add_argument("--compare", nargs=2, metavar=("A", "B"), help="Compare two result files")
    args = parser.parse_args()

    if args.compare:
        compare_results(args.compare[0], args.compare[1])
        return

    results = run_benchmark(quick=args.quick)

    if args.export:
        Path(args.export).write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\nResults exported to {args.export}")
    else:
        print(f"\nExport: python {__file__} --export results.json")
        print(f"Compare: python {__file__} --compare before.json after.json")


if __name__ == "__main__":
    main()
