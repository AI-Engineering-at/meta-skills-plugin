#!/usr/bin/env python3
"""session-end-sync.py — Automatic open-notebook sync on Claude Code session end.

Called by Claude Code SessionEnd hook. Reads session context from stdin,
generates a summary, and posts it to open-notebook KB.

Cross-platform: Windows, macOS, Linux.

Usage (manual):
  python session-end-sync.py

Usage (automatic via hook):
  Configured in ~/.claude/settings.json → hooks.SessionEnd
"""
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# ── config ────────────────────────────────────────────────────────────────────

OPEN_NOTEBOOK_BASE = os.environ.get("OPEN_NOTEBOOK_API", "http://open-notebook.local:5055")
OPEN_NOTEBOOK_API = OPEN_NOTEBOOK_BASE + "/api/sources"
NOTEBOOK_ID = "notebook:zkxy9fiwelrolgbr2upc"  # AI Engineering KB
HEALTH_TIMEOUT_S = 2  # fail-fast: Devstral finding #4

# Vault path for ERPNext (optional — sync note there too)
REPO_ROOT = Path(__file__).parent.parent.parent
VAULT_PY = REPO_ROOT / ".claude" / "credentials" / "vault.py"

LOG_DIR = Path.home() / ".claude" / "sync-logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def git_session_summary() -> str:
    """Get git changes made during this session (last N commits today)."""
    try:
        # Use --after with yesterday to avoid timezone edge cases
        from datetime import timedelta
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        r = subprocess.run(
            ["git", "log", f"--after={yesterday}", "--oneline", "--no-merges"],
            capture_output=True, text=True, timeout=10, cwd=str(REPO_ROOT)
        )
        commits = r.stdout.strip()
        if not commits:
            return "Keine neuen Commits heute."
        return f"## Commits heute\n```\n{commits}\n```"
    except Exception as e:
        return f"Git-Info nicht verfuegbar: {e}"


def git_diff_stat() -> str:
    """Get diff stat for today's changes."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        r = subprocess.run(
            ["git", "diff", "--stat", f"HEAD@{{{today}}}..HEAD"],
            capture_output=True, text=True, timeout=10, cwd=str(REPO_ROOT)
        )
        return r.stdout.strip() if r.stdout.strip() else "Kein diff stat verfuegbar."
    except Exception:
        return ""


def post_to_open_notebook(title: str, content: str) -> bool:
    """Post a source to open-notebook KB via multipart form-data."""
    try:
        # open-notebook requires multipart form-data with type=text
        boundary = "----SessionEndSync9f8a7b"
        fields = [
            ("title", title),
            ("content", content),
            ("type", "text"),
            ("notebook_id", NOTEBOOK_ID),
        ]
        body_parts = []
        for name, value in fields:
            body_parts.append(f"--{boundary}\r\n")
            body_parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n')
            body_parts.append(f"{value}\r\n")
        body_parts.append(f"--{boundary}--\r\n")
        body = "".join(body_parts).encode("utf-8")

        req = urllib.request.Request(
            OPEN_NOTEBOOK_API,
            data=body,
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.status in (200, 201)
    except Exception as e:
        log(f"open-notebook POST failed: {e}")
        return False


def log(msg: str):
    """Append to sync log."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = LOG_DIR / f"sync-{datetime.now().strftime('%Y-%m-%d')}.log"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def validate_endpoint() -> None:
    """Probe OPEN_NOTEBOOK_BASE reachability; fail-fast with clear message.

    Devstral external review finding #4: silent DNS/connection failures made
    session-end-sync appear successful while nothing was synced. Fail-fast
    surfaces misconfiguration at the first user-visible opportunity.
    """
    health_url = OPEN_NOTEBOOK_BASE.rstrip("/") + "/health"
    try:
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=HEALTH_TIMEOUT_S) as resp:
            if resp.status not in (200, 204):
                raise RuntimeError(f"unexpected status {resp.status}")
    except (urllib.error.URLError, OSError, RuntimeError) as e:
        sys.stderr.write(
            f"session-end-sync: OPEN_NOTEBOOK_API unreachable at {health_url}\n"
            f"  reason: {e}\n"
            f"  set env: OPEN_NOTEBOOK_API=http://<host>:5055 (production: 10.40.10.82)\n"
        )
        log(f"validate_endpoint FAILED: {health_url} ({e})")
        sys.exit(2)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    log("Session-End Sync gestartet")
    validate_endpoint()

    # Read session context from stdin (if provided by hook)
    session_ctx = ""
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read(8192)  # max 8KB
            if raw.strip():
                session_ctx = f"\n## Session-Kontext (Hook)\n```json\n{raw[:2000]}\n```\n"
    except Exception:
        pass

    # Collect git info
    commits = git_session_summary()
    diff_stat = git_diff_stat()

    # Build content
    content = f"""## Session Sync {date_str} {time_str}

{commits}

## Aenderungen (diff stat)
```
{diff_stat}
```
{session_ctx}
## Automatisch
Dieser Eintrag wurde automatisch vom SessionEnd-Hook erstellt.
"""

    title = f"Session Sync {date_str} {time_str}"

    # Check if there are any commits today — skip sync if nothing happened
    if "Keine neuen Commits" in commits and not session_ctx:
        log("Keine Aenderungen heute — Sync uebersprungen")
        print("No changes today — sync skipped")
        return

    # Post to open-notebook
    ok = post_to_open_notebook(title, content)
    if ok:
        log(f"open-notebook Source erstellt: {title}")
        print(f"Synced to open-notebook: {title}")
    else:
        log(f"open-notebook Sync FEHLGESCHLAGEN: {title}")
        print(f"Sync failed — check {LOG_DIR}")


if __name__ == "__main__":
    main()
