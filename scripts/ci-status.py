#!/usr/bin/env python3
"""CI Status Monitor — Check GitHub Actions status via gh CLI.

Closes the CI/CD feedback loop: local hooks catch lint/test issues,
this script catches REMOTE CI failures.

Usage:
  python3 ci-status.py                 # Show last 5 runs
  python3 ci-status.py --watch         # Poll until current run completes
  python3 ci-status.py --json          # JSON output for hooks/scripts
  python3 ci-status.py --last-failure  # Show details of last failure
  python3 ci-status.py --quick         # One-liner status (for hooks)
"""

import json
import platform
import subprocess
import sys
import time

IS_WINDOWS = platform.system() == "Windows"


def gh_run(args: list, timeout: int = 15) -> dict | list | None:
    """Run gh CLI command and return parsed JSON output."""
    cmd = ["gh", *args]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=IS_WINDOWS,
        )
        if result.returncode != 0:
            if "not a git repository" in result.stderr:
                return None
            return None
        if result.stdout.strip():
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    return None


def get_runs(limit: int = 5) -> list:
    """Get recent CI runs."""
    runs = gh_run(
        [
            "run",
            "list",
            "--limit",
            str(limit),
            "--json",
            "status,conclusion,name,createdAt,url,databaseId,headBranch,event",
        ]
    )
    return runs if isinstance(runs, list) else []


def get_run_log(run_id: int) -> str:
    """Get failure log for a specific run."""
    try:
        result = subprocess.run(
            ["gh", "run", "view", str(run_id), "--log-failed"],
            capture_output=True,
            text=True,
            timeout=30,
            shell=IS_WINDOWS,
        )
        return result.stdout[:3000] if result.stdout else "No failure log available."
    except Exception:
        return "Could not retrieve failure log."


def format_run(run: dict) -> str:
    """Format a single run for display."""
    status = run.get("status", "?")
    conclusion = run.get("conclusion", "?")
    name = run.get("name", "?")
    branch = run.get("headBranch", "?")
    event = run.get("event", "?")
    created = run.get("createdAt", "?")[:19].replace("T", " ")

    if conclusion == "failure":
        icon = "FAIL"
    elif conclusion == "success":
        icon = "PASS"
    elif status == "in_progress":
        icon = "RUNNING"
    elif status == "queued":
        icon = "QUEUED"
    else:
        icon = conclusion.upper() if conclusion else status.upper()

    return f"  [{icon:8s}] {name:25s} {branch:15s} {event:6s} {created}"


def show_status(runs: list):
    """Display CI status dashboard."""
    if not runs:
        print("No CI runs found. Is this a GitHub repository?")
        return

    print("CI/CD Status Dashboard")
    print("=" * 80)

    failures = [r for r in runs if r.get("conclusion") == "failure"]
    in_progress = [r for r in runs if r.get("status") == "in_progress"]

    if failures:
        print(f"  FAILURES: {len(failures)} in last {len(runs)} runs")
    if in_progress:
        print(f"  IN PROGRESS: {len(in_progress)} runs")
    if not failures and not in_progress:
        print("  ALL CLEAR: No failures, no running jobs")

    print()
    for run in runs:
        print(format_run(run))

    if failures:
        latest_failure = failures[0]
        print(f"\n  Latest failure: {latest_failure.get('name', '?')}")
        print(f"  URL: {latest_failure.get('url', '?')}")
        print("  Fix: run `/meta-ci --last-failure` for failure logs")


def show_quick(runs: list) -> str:
    """One-liner status for hooks."""
    if not runs:
        return "CI: unknown (not a git repo or gh not configured)"

    latest = runs[0]
    conclusion = latest.get("conclusion", "")
    status = latest.get("status", "")
    name = latest.get("name", "?")

    if status == "in_progress":
        return f"CI: RUNNING ({name})"
    elif conclusion == "failure":
        return f"CI: FAILED ({name}) — fix before pushing"
    elif conclusion == "success":
        return f"CI: PASS ({name})"
    else:
        return f"CI: {conclusion or status} ({name})"


def watch_runs(poll_interval: int = 30, max_polls: int = 40):
    """Poll until all in-progress runs complete."""
    print("Watching CI runs (Ctrl+C to stop)...")
    for i in range(max_polls):
        runs = get_runs(5)
        in_progress = [r for r in runs if r.get("status") == "in_progress"]

        if not in_progress:
            print("\nAll runs complete:")
            for run in runs[:3]:
                print(format_run(run))
            failures = [r for r in runs if r.get("conclusion") == "failure"]
            if failures:
                print(f"\n  FAILURE detected: {failures[0].get('name', '?')}")
                print("  Run: /meta-ci --last-failure")
            else:
                print("\n  ALL PASS")
            return

        print(
            f"  [{i + 1}/{max_polls}] {len(in_progress)} run(s) in progress... (next check in {poll_interval}s)"
        )
        for r in in_progress:
            print(f"    - {r.get('name', '?')} ({r.get('headBranch', '?')})")

        time.sleep(poll_interval)

    print("Max polls reached. Check manually with: gh run list")


def show_last_failure(runs: list):
    """Show details of the last failure."""
    failures = [r for r in runs if r.get("conclusion") == "failure"]
    if not failures:
        print("No recent failures found.")
        return

    failure = failures[0]
    run_id = failure.get("databaseId", 0)
    print(f"Last Failure: {failure.get('name', '?')}")
    print(f"Branch: {failure.get('headBranch', '?')}")
    print(f"Event: {failure.get('event', '?')}")
    print(f"URL: {failure.get('url', '?')}")
    print(f"Created: {failure.get('createdAt', '?')}")
    print()
    print("Failure Log (truncated):")
    print("-" * 60)
    log = get_run_log(run_id)
    print(log)


def main():
    as_json = "--json" in sys.argv
    watch = "--watch" in sys.argv
    last_failure = "--last-failure" in sys.argv
    quick = "--quick" in sys.argv

    if watch:
        watch_runs()
        return

    runs = get_runs(5)

    if as_json:
        failures = [r for r in runs if r.get("conclusion") == "failure"]
        in_progress = [r for r in runs if r.get("status") == "in_progress"]
        print(
            json.dumps(
                {
                    "total_runs": len(runs),
                    "failures": len(failures),
                    "in_progress": len(in_progress),
                    "latest_conclusion": runs[0].get("conclusion", "?")
                    if runs
                    else "unknown",
                    "latest_name": runs[0].get("name", "?") if runs else "unknown",
                    "runs": runs,
                },
                indent=2,
            )
        )
        return

    if quick:
        print(show_quick(runs))
        return

    if last_failure:
        show_last_failure(runs)
        return

    show_status(runs)


if __name__ == "__main__":
    main()
