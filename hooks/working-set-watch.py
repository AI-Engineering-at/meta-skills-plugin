#!/usr/bin/env python3
"""Hook: working-set-watch (SessionStart)

Mitigates "Source-Files in Downloads/ ohne Versionierung" pattern (audit:
Action Plan v1.0 + 4 DECs lebten unversioniert in Downloads/ bis zur
Migration in Session A2).

On SessionStart, scans configurable inboxes (default: ~/Downloads,
~/Documents/Downloads if exists) for strategy/concept/decision files
older than threshold (warn ≥7 days, critical ≥30 days). Emits an advisory
listing stale files with migration suggestion.

Strategy-file patterns (filename):
  - Action_Plan*  Compliance_*  Lineage_*
  - DEC-*         M0*           *_Concept_*

Extension whitelist: .md .py .yaml .yml .json (no .png/.exe/.pdf).
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.state import SessionState

HOOK_NAME = "working_set_watch"
WARN_AGE_DAYS = 7
CRITICAL_AGE_DAYS = 30
ALLOWED_EXTENSIONS = {".md", ".py", ".yaml", ".yml", ".json"}
MAX_FILES_REPORTED = 20

STRATEGY_PATTERNS = [
    re.compile(r"^Action_Plan", re.IGNORECASE),
    re.compile(r"^DEC-\d+", re.IGNORECASE),
    re.compile(r"_Concept_", re.IGNORECASE),
    re.compile(r"^Compliance_", re.IGNORECASE),
    re.compile(r"^Lineage_", re.IGNORECASE),
    re.compile(r"^M\d{2}[_-]", re.IGNORECASE),
]


def is_strategy_file(name: str | None) -> bool:
    """Return True if filename is a strategy/concept/decision file."""
    if not name:
        return False
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return False
    return any(p.search(name) for p in STRATEGY_PATTERNS)


def classify_age_days(age_days: float) -> str:
    """Return 'ok' | 'warn' | 'critical'."""
    if age_days >= CRITICAL_AGE_DAYS:
        return "critical"
    if age_days >= WARN_AGE_DAYS:
        return "warn"
    return "ok"


def scan_inbox(inbox: str) -> list[dict]:
    """List stale strategy files in `inbox`.

    Returns list of {name, path, age_days, severity}, capped at MAX_FILES_REPORTED.
    Skips fresh files, non-strategy files, dirs, missing inboxes.
    """
    results: list[dict] = []
    base = Path(inbox)
    if not base.is_dir():
        return results
    now = time.time()
    try:
        entries = list(base.iterdir())
    except OSError:
        return results
    for path in entries:
        if not path.is_file():
            continue
        if not is_strategy_file(path.name):
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        age_days = (now - mtime) / 86400
        severity = classify_age_days(age_days)
        if severity == "ok":
            continue
        results.append(
            {
                "name": path.name,
                "path": str(path),
                "age_days": int(age_days),
                "severity": severity,
            }
        )
        if len(results) >= MAX_FILES_REPORTED:
            break
    return results


def _resolve_inboxes() -> list[str]:
    """Resolve inbox paths from env or defaults."""
    env_value = os.environ.get("WORKING_SET_INBOXES", "").strip()
    if env_value:
        return [p.strip() for p in env_value.split(",") if p.strip()]
    home = Path.home()
    candidates = [
        home / "Downloads",
        home / "Documents" / "Downloads",
    ]
    return [str(p) for p in candidates if p.is_dir()]


def _build_advisory(findings: list[dict]) -> str:
    lines = [
        "⚠️ Strategy/concept files in Downloads/ are stale (working-set-watch):",
    ]
    has_critical = any(f["severity"] == "critical" for f in findings)
    for f in findings:
        marker = "🔴" if f["severity"] == "critical" else "🟡"
        lines.append(f"  {marker} {f['name']} ({f['age_days']} days, {f['severity']})")
    if has_critical:
        lines.append(
            "  → CRITICAL: ≥30 days unversioned. Migrate now to "
            "`zeroth/decisions/` (DECs, Action Plans) or `zeroth/concepts/` "
            "(Module specs, Compliance docs)."
        )
    else:
        lines.append(
            "  → Migrate to `zeroth/decisions/` or `zeroth/concepts/` to prevent "
            "loss. Audit pattern: Action Plan v1.0 lived unversioned in Downloads/."
        )
    lines.append(f"(Hook: working-set-watch. Threshold: warn≥{WARN_AGE_DAYS}d, critical≥{CRITICAL_AGE_DAYS}d.)")
    return "\n".join(lines)


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    if not isinstance(data, dict):
        sys.exit(0)
    if data.get("hook_event_name") != "SessionStart":
        sys.exit(0)

    inboxes = _resolve_inboxes()
    findings: list[dict] = []
    for inbox in inboxes:
        findings.extend(scan_inbox(inbox))
        if len(findings) >= MAX_FILES_REPORTED:
            findings = findings[:MAX_FILES_REPORTED]
            break

    if not findings:
        sys.exit(0)  # Silent pass when inbox is clean

    advisory = _build_advisory(findings)
    print(json.dumps({"additionalContext": advisory}))

    try:
        session_id = data.get("session_id", "unknown")
        state = SessionState(session_id)
        ns = state.get(HOOK_NAME) or {}
        ns["last_scan_at"] = time.time()
        ns["stale_files_count"] = len(findings)
        state.set(HOOK_NAME, ns)
        state.save()
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
