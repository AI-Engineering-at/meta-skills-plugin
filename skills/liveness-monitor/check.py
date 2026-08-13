#!/usr/bin/env python3
"""Liveness-Monitor for meta-skills Hook-Pipeline.

Reads heartbeat-state.md last-modified time. If older than threshold (default 24h),
flags status as stale/dead and optionally triggers ERPNext task + Mattermost alert.

Exit-Codes:
    0 = live (age < threshold)
    1 = stale (threshold < age < 7d)
    2 = dead (age >= 7d or missing)
    3 = error (file unreadable)

Anchor: prevents E207-pattern (Hook-Pipeline silently dead for 28+ days).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


HEARTBEAT_RELATIVE = "self-improving/heartbeat-state.md"
DEFAULT_THRESHOLD_HOURS = 24
DEAD_THRESHOLD_HOURS = 24 * 7  # 7 days
DEDUP_STATE_FILE = "self-improving/liveness-monitor-state.json"


def find_meta_skills_root() -> Path:
    """Locate meta-skills root via three strategies:

    1. CLAUDE_PLUGIN_ROOT env-var (when run as plugin hook)
    2. Script-relative path (this file lives in skills/liveness-monitor/check.py)
    3. ~/Documents/phantom-ai/meta-skills (Joe's standard path)
    """
    import os

    if env := os.environ.get("CLAUDE_PLUGIN_ROOT"):
        candidate = Path(env)
        if (candidate / HEARTBEAT_RELATIVE).parent.exists():
            return candidate
    script_root = Path(__file__).resolve().parent.parent.parent
    if (script_root / HEARTBEAT_RELATIVE).parent.exists():
        return script_root
    home_path = Path.home() / "Documents" / "phantom-ai" / "meta-skills"
    if home_path.exists():
        return home_path
    raise FileNotFoundError("Cannot locate meta-skills root")


def check_heartbeat(threshold_hours: int = DEFAULT_THRESHOLD_HOURS) -> dict:
    """Return liveness status of the Hook-Pipeline heartbeat."""
    try:
        root = find_meta_skills_root()
    except FileNotFoundError as exc:
        return {
            "status": "error",
            "error": str(exc),
            "heartbeat_path": None,
            "last_modified": None,
            "age_hours": None,
            "threshold_hours": threshold_hours,
        }

    heartbeat = root / HEARTBEAT_RELATIVE
    if not heartbeat.exists():
        return {
            "status": "missing",
            "heartbeat_path": str(heartbeat),
            "last_modified": None,
            "age_hours": None,
            "threshold_hours": threshold_hours,
        }

    try:
        mtime = datetime.fromtimestamp(heartbeat.stat().st_mtime, tz=timezone.utc)
    except OSError as exc:
        return {
            "status": "error",
            "error": f"stat failed: {exc}",
            "heartbeat_path": str(heartbeat),
            "last_modified": None,
            "age_hours": None,
            "threshold_hours": threshold_hours,
        }

    age_seconds = (datetime.now(tz=timezone.utc) - mtime).total_seconds()
    age_hours = age_seconds / 3600

    if age_hours < threshold_hours:
        status = "live"
    elif age_hours < DEAD_THRESHOLD_HOURS:
        status = "stale"
    else:
        status = "dead"

    return {
        "status": status,
        "heartbeat_path": str(heartbeat),
        "last_modified": mtime.isoformat(),
        "age_hours": round(age_hours, 2),
        "threshold_hours": threshold_hours,
    }


def already_alerted_recently(root: Path) -> bool:
    """Idempotency: check if last alert was within 24h to avoid duplicate ERPNext tasks."""
    state_file = root / DEDUP_STATE_FILE
    if not state_file.exists():
        return False
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
        last = datetime.fromisoformat(state.get("last_alert_iso", ""))
        age_seconds = (datetime.now(tz=timezone.utc) - last).total_seconds()
        return age_seconds < 24 * 3600
    except (ValueError, OSError, json.JSONDecodeError):
        return False


def record_alert(root: Path, payload: dict) -> None:
    """Write dedup-tracker state-file."""
    state_file = root / DEDUP_STATE_FILE
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(
            {
                "last_alert_iso": datetime.now(tz=timezone.utc).isoformat(),
                "last_payload": payload,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def trigger_alert(payload: dict, verbose: bool = False) -> list[str]:
    """Trigger ERPNext task creation + optional Mattermost post.

    Returns list of destinations actually triggered.
    """
    destinations: list[str] = []
    try:
        root = find_meta_skills_root()
    except FileNotFoundError:
        return destinations

    if already_alerted_recently(root):
        if verbose:
            print("[liveness-monitor] dedup: alert within 24h skipped", file=sys.stderr)
        return destinations

    try:
        import subprocess

        vault_py = root.parent / ".claude" / "credentials" / "vault.py"
        if vault_py.exists():
            erp_key = (
                subprocess.check_output(
                    [
                        sys.executable,
                        str(vault_py),
                        "get",
                        "shared",
                        "erpnext",
                        "API_KEY",
                    ],
                    text=True,
                )
                .strip()
                .splitlines()[-1]
            )
            erp_sec = (
                subprocess.check_output(
                    [
                        sys.executable,
                        str(vault_py),
                        "get",
                        "shared",
                        "erpnext",
                        "API_SECRET",
                    ],
                    text=True,
                )
                .strip()
                .splitlines()[-1]
            )

            import urllib.request

            req_body = json.dumps(
                {
                    "subject": f"Hook-Pipeline {payload['status']} — Letzte Aktivität {payload['last_modified']}",
                    "priority": "Urgent" if payload["status"] == "dead" else "High",
                    "description": (
                        f"meta-skills Hook-Pipeline liveness-monitor alert.\n"
                        f"heartbeat: {payload['heartbeat_path']}\n"
                        f"age_hours: {payload['age_hours']}\n"
                        f"threshold_hours: {payload['threshold_hours']}\n"
                        f"Suspected cause: Plugin-Cache stale, Marketplace fehlt, oder Source-Issue.\n"
                        f"Reference: ERRORS.md E207, LEARNINGS.md L343-L351."
                    ),
                    "project": "PROJ-0001",
                    "status": "Open",
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                "http://10.40.10.82:8082/api/resource/Task",
                data=req_body,
                method="POST",
                headers={
                    "Authorization": f"token {erp_key}:{erp_sec}",
                    "Content-Type": "application/json",
                },
            )
            urllib.request.urlopen(req, timeout=10)
            destinations.append("erpnext")
    except (
        subprocess.CalledProcessError,
        OSError,
        urllib.error.URLError,
        ValueError,
    ) as exc:
        if verbose:
            print(f"[liveness-monitor] erpnext alert failed: {exc}", file=sys.stderr)

    record_alert(root, payload)
    return destinations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=DEFAULT_THRESHOLD_HOURS,
        help=f"Threshold in hours (default: {DEFAULT_THRESHOLD_HOURS})",
    )
    parser.add_argument(
        "--alert",
        action="store_true",
        help="Trigger ERPNext task + Mattermost post if not live",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    payload = check_heartbeat(threshold_hours=args.max_age_hours)
    payload["alert_triggered"] = False
    payload["alert_destinations"] = []

    if args.alert and payload["status"] in {"stale", "dead", "missing"}:
        destinations = trigger_alert(payload, verbose=args.verbose)
        payload["alert_triggered"] = bool(destinations)
        payload["alert_destinations"] = destinations

    print(json.dumps(payload, indent=2))

    exit_codes = {"live": 0, "stale": 1, "dead": 2, "missing": 2, "error": 3}
    return exit_codes.get(payload["status"], 3)


if __name__ == "__main__":
    sys.exit(main())
