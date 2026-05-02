#!/usr/bin/env python3
"""session-watcher.py — Per-session guardian process.

Spawned by SessionStart hook. Monitors ONE session, not the whole system.
Cleans up when terminal dies. Warns on anomalies while running.

Lifecycle:
  Terminal opens → SessionStart hook → this script spawns (background)
  ├── Tracks parent PID (the claude process for this session)
  ├── Writes heartbeat to ~/.claude/watchers/{pid}.json
  ├── Monitors: RAM growth, age, parent alive
  ├── Warns: RAM spike, stuck session, orphan siblings
  └── Terminal dies → parent gone → cleanup children → remove heartbeat → exit

Cross-platform: Windows, macOS, Linux.

Usage (normally called by hook, not manually):
  python session-watcher.py --parent-pid 12345
  python session-watcher.py --list              # show all active watchers
  python session-watcher.py --cleanup-orphans   # remove stale heartbeats
"""

import argparse
import json
import logging
import os
import platform
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import psutil
except ImportError:
    print("psutil required: pip install psutil", file=sys.stderr)
    sys.exit(1)

SYSTEM = platform.system()
WATCHER_DIR = Path.home() / ".claude" / "watchers"
WATCHER_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = WATCHER_DIR / "watcher.log"

# ── thresholds ────────────────────────────────────────────────────────────────

POLL_INTERVAL_S = 10  # how often to check parent + metrics
RAM_WARN_MB = 4_000  # warn if session RSS > 4 GB
RAM_WARN_GROWTH_MB = 500  # warn if RAM grew > 500 MB in 5 min
RAM_WARN_COOLDOWN_S = 600  # don't warn again within 10 min
AGE_WARN_H = 24  # warn if session running > 24h
ORPHAN_GRACE_S = 30  # wait 30s after parent dies before cleanup
CHILD_KILL_TIMEOUT_S = 5  # wait for graceful shutdown before force kill

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger("session-watcher")


# ── notifications (cross-platform) ───────────────────────────────────────────


def notify(title: str, message: str):
    """Desktop notification — cross-platform."""
    try:
        if SYSTEM == "Darwin":
            os.system(
                f'osascript -e \'display notification "{message}" with title "{title}"\''
            )
        elif SYSTEM == "Linux":
            os.system(f'notify-send "{title}" "{message}" 2>/dev/null')
        elif SYSTEM == "Windows":
            import subprocess

            ps = (
                "Add-Type -AssemblyName System.Windows.Forms;"
                f"$n=New-Object System.Windows.Forms.NotifyIcon;"
                "$n.Icon=[System.Drawing.SystemIcons]::Warning;"
                "$n.Visible=$true;"
                f'$n.ShowBalloonTip(5000,"{title}","{message}",'
                "[System.Windows.Forms.ToolTipIcon]::Warning);"
                "Start-Sleep 6;$n.Dispose()"
            )
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            subprocess.Popen(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                creationflags=flags,
            )
    except Exception as e:
        log.warning("Notification failed: %s", e)


# ── heartbeat ─────────────────────────────────────────────────────────────────


def heartbeat_path(pid: int) -> Path:
    return WATCHER_DIR / f"{pid}.json"


def write_heartbeat(parent_pid: int, watcher_pid: int, rss_mb: int = 0):
    data = {
        "parent_pid": parent_pid,
        "watcher_pid": watcher_pid,
        "started": datetime.now().isoformat(),
        "last_seen": datetime.now().isoformat(),
        "rss_mb": rss_mb,
        "platform": SYSTEM,
    }
    heartbeat_path(parent_pid).write_text(json.dumps(data, indent=2), encoding="utf-8")


def update_heartbeat(parent_pid: int, rss_mb: int):
    hb = heartbeat_path(parent_pid)
    if hb.exists():
        data = json.loads(hb.read_text(encoding="utf-8"))
        data["last_seen"] = datetime.now().isoformat()
        data["rss_mb"] = rss_mb
        hb.write_text(json.dumps(data, indent=2), encoding="utf-8")


def remove_heartbeat(parent_pid: int):
    hb = heartbeat_path(parent_pid)
    hb.unlink(missing_ok=True)


# ── session monitoring ────────────────────────────────────────────────────────


def get_session_tree(parent_pid: int) -> list[psutil.Process]:
    """Get all child processes of the session parent."""
    try:
        parent = psutil.Process(parent_pid)
        return parent.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []


def kill_session_children(parent_pid: int):
    """Gracefully terminate all children, then force kill if needed."""
    children = get_session_tree(parent_pid)
    if not children:
        return

    log.info("Cleaning up %d child processes of PID %d", len(children), parent_pid)

    # First: graceful terminate
    for p in children:
        try:
            p.terminate()
            log.info("  TERM pid=%d name=%s", p.pid, p.name())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # Wait for graceful shutdown
    gone, alive = psutil.wait_procs(children, timeout=CHILD_KILL_TIMEOUT_S)

    # Force kill survivors
    for p in alive:
        try:
            p.kill()
            log.info("  KILL pid=%d name=%s (force)", p.pid, p.name())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    log.info("Cleanup done: %d terminated, %d force-killed", len(gone), len(alive))


def watch_session(parent_pid: int):
    """Main watch loop for one session."""
    watcher_pid = os.getpid()
    log.info(
        "Watcher started: parent=%d watcher=%d platform=%s",
        parent_pid,
        watcher_pid,
        SYSTEM,
    )

    # Verify parent exists
    try:
        parent = psutil.Process(parent_pid)
        log.info("Parent process: %s (pid=%d)", parent.name(), parent_pid)
    except psutil.NoSuchProcess:
        log.error("Parent PID %d does not exist — exiting", parent_pid)
        return

    write_heartbeat(parent_pid, watcher_pid)

    last_rss_mb = 0
    last_warn_time = 0
    session_start = time.time()

    while True:
        time.sleep(POLL_INTERVAL_S)

        # ── 1. Parent still alive? ──
        if not psutil.pid_exists(parent_pid):
            log.info(
                "Parent %d is gone — waiting %ds grace period",
                parent_pid,
                ORPHAN_GRACE_S,
            )
            time.sleep(ORPHAN_GRACE_S)

            if not psutil.pid_exists(parent_pid):
                log.info("Parent confirmed dead — cleaning up")
                kill_session_children(parent_pid)
                remove_heartbeat(parent_pid)
                log.info("Watcher exiting (parent %d died)", parent_pid)
                return

            log.info("Parent %d came back (false alarm)", parent_pid)

        # ── 2. Monitor session health ──
        try:
            parent = psutil.Process(parent_pid)
            mem = parent.memory_info()
            rss_mb = round(mem.rss / 1024 / 1024)

            update_heartbeat(parent_pid, rss_mb)

            now = time.time()
            age_h = (now - session_start) / 3600

            # RAM absolute warning
            if rss_mb > RAM_WARN_MB and (now - last_warn_time) > RAM_WARN_COOLDOWN_S:
                msg = f"Session PID {parent_pid}: {rss_mb} MB RAM"
                log.warning(msg)
                notify("Claude RAM Warning", msg)
                last_warn_time = now

            # RAM growth warning (sudden spike)
            if last_rss_mb > 0:
                growth = rss_mb - last_rss_mb
                if (
                    growth > RAM_WARN_GROWTH_MB
                    and (now - last_warn_time) > RAM_WARN_COOLDOWN_S
                ):
                    msg = (
                        f"Session PID {parent_pid}: +{growth} MB in {POLL_INTERVAL_S}s"
                    )
                    log.warning(msg)
                    notify("Claude RAM Spike", msg)
                    last_warn_time = now

            # Age warning
            if age_h > AGE_WARN_H and (now - last_warn_time) > RAM_WARN_COOLDOWN_S:
                msg = f"Session PID {parent_pid}: running {age_h:.1f}h"
                log.warning(msg)
                notify("Claude Long Session", msg)
                last_warn_time = now

            last_rss_mb = rss_mb

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            log.info("Lost access to parent %d — treating as dead", parent_pid)
            kill_session_children(parent_pid)
            remove_heartbeat(parent_pid)
            return


# ── list watchers ─────────────────────────────────────────────────────────────


def list_watchers():
    """Show all active watcher heartbeats."""
    hbs = sorted(WATCHER_DIR.glob("*.json"))
    if not hbs:
        print("No active watchers.")
        return

    print(f"{'Parent':>8}  {'Watcher':>8}  {'RSS MB':>7}  {'Last Seen':>20}  Status")
    print("-" * 70)

    for hb in hbs:
        try:
            data = json.loads(hb.read_text(encoding="utf-8"))
            ppid = data["parent_pid"]
            wpid = data["watcher_pid"]
            rss = data.get("rss_mb", 0)
            last = data.get("last_seen", "?")[:19]

            parent_alive = psutil.pid_exists(ppid)
            watcher_alive = psutil.pid_exists(wpid)

            if parent_alive and watcher_alive:
                status = "ACTIVE"
            elif not parent_alive and watcher_alive:
                status = "ORPHAN-WATCHER"
            elif parent_alive and not watcher_alive:
                status = "UNWATCHED"
            else:
                status = "STALE"

            print(f"{ppid:>8}  {wpid:>8}  {rss:>6}M  {last:>20}  {status}")
        except Exception:
            print(f"  {hb.name}: corrupt")


def cleanup_orphans():
    """Remove stale heartbeat files."""
    removed = 0
    for hb in WATCHER_DIR.glob("*.json"):
        try:
            data = json.loads(hb.read_text(encoding="utf-8"))
            ppid = data["parent_pid"]
            wpid = data["watcher_pid"]
            if not psutil.pid_exists(ppid) and not psutil.pid_exists(wpid):
                hb.unlink()
                removed += 1
                print(f"  Removed stale: {hb.name}")
        except Exception:
            pass
    print(f"Cleaned up {removed} stale heartbeats.")


# ── main ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Per-session watcher process")
    parser.add_argument("--parent-pid", type=int, help="PID of the session to watch")
    parser.add_argument("--list", action="store_true", help="List all active watchers")
    parser.add_argument(
        "--cleanup-orphans", action="store_true", help="Remove stale heartbeats"
    )
    args = parser.parse_args()

    if args.list:
        list_watchers()
        return

    if args.cleanup_orphans:
        cleanup_orphans()
        return

    if not args.parent_pid:
        # Try to detect parent automatically
        ppid = os.getppid()
        if ppid and ppid > 1:
            log.info("Auto-detected parent PID: %d", ppid)
            args.parent_pid = ppid
        else:
            print("Usage: session-watcher.py --parent-pid <PID>", file=sys.stderr)
            sys.exit(1)

    watch_session(args.parent_pid)


if __name__ == "__main__":
    main()
