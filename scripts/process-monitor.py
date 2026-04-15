#!/usr/bin/env python3
"""process-monitor.py — Cross-platform orphan/zombie CLI process monitor.

Tracks claude, copilot, codex, and other AI CLI processes.
Detects zombies safely and cleans up. Works on Windows, macOS, and Linux.

Kill rules — ALL must be true:
  1. Working Set < 50 MB          (not actively using RAM)
  2. cpu_percent < 0.5%           (measured over sample period — truly idle)
  3. threads < 20                 (no active worker pool)
  4. age > 15 min                 (not freshly spawned)

NEVER kill if:
  - WS > 100 MB                  (could be waiting for LLM response)
  - cpu_percent > 0.5%           (anything active right now)
  - age < 15 min

Usage:
  python process-monitor.py --status       show current state
  python process-monitor.py --cleanup      one-shot cleanup
  python process-monitor.py --dry-run      show what would be killed
  python process-monitor.py --report       write markdown report
  python process-monitor.py --json         machine-readable output for statusline
  python process-monitor.py                continuous mode (watcher + cleanup)
"""
import sys
import os
import time
import json
import platform
import logging
import argparse
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import psutil
except ImportError:
    print('{"error": "psutil not installed. Run: pip install psutil"}')
    sys.exit(1)

# ── config ────────────────────────────────────────────────────────────────────

SYSTEM = platform.system()  # "Windows", "Darwin", "Linux"

# Process name patterns per OS
if SYSTEM == "Windows":
    PROC_PATTERNS = ["claude.exe"]
    CMDLINE_PATTERNS = ["claude", "copilot", "codex"]
elif SYSTEM == "Darwin":
    PROC_PATTERNS = ["claude", "node"]
    CMDLINE_PATTERNS = ["claude", "copilot", "codex", "@anthropic"]
else:  # Linux
    PROC_PATTERNS = ["claude", "node"]
    CMDLINE_PATTERNS = ["claude", "copilot", "codex", "@anthropic"]

# Kill thresholds — ALL required
KILL_MAX_WS_MB = 50
KILL_MAX_CPU_PCT = 0.5
KILL_MAX_THREADS = 20
KILL_MIN_AGE_MIN = 15
KILL_SAFE_WS_MB = 100

# Warning thresholds
WARN_PRIV_MB = 8_000
WARN_AGE_H = 48

# Timing
CPU_SAMPLE_S = 3
CLEANUP_INTERVAL_S = 300

# Logs
LOG_DIR = Path.home() / ".claude" / "monitor-logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("process-monitor")


# ── cross-platform process detection ──────────────────────────────────────────

def is_cli_process(proc: psutil.Process) -> bool:
    """Check if a process is a CLI AI tool (claude, copilot, codex)."""
    try:
        name = proc.name().lower()
        if any(pat.lower() in name for pat in PROC_PATTERNS):
            # On Windows, claude.exe is definitive
            if SYSTEM == "Windows" and name == "claude.exe":
                return True
            # On Unix, "node" needs cmdline check
            if name == "node":
                cmdline = " ".join(proc.cmdline()).lower()
                return any(pat in cmdline for pat in CMDLINE_PATTERNS)
            # Direct match (e.g., "claude" binary on Unix)
            if name in ("claude", "copilot", "codex"):
                return True
        return False
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def find_cli_processes() -> list[psutil.Process]:
    """Find all AI CLI processes on any platform."""
    return [p for p in psutil.process_iter(["name"]) if is_cli_process(p)]


# ── process info ──────────────────────────────────────────────────────────────

def process_info(p: psutil.Process, sample_cpu: bool = False) -> dict | None:
    """Collect metadata. sample_cpu=True blocks for CPU_SAMPLE_S seconds."""
    try:
        with p.oneshot():
            mem = p.memory_info()
            cpu_t = p.cpu_times()
            create = datetime.fromtimestamp(p.create_time())
            age_s = (datetime.now() - create).total_seconds()

            try:
                cmdline = " ".join(p.cmdline())
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                cmdline = "<access denied>"

            try:
                parent = psutil.Process(p.ppid())
                parent_name = parent.name()
                parent_alive = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                parent_name = "unknown"
                parent_alive = False

        # cpu_percent outside oneshot
        if sample_cpu:
            p.cpu_percent(interval=None)
            time.sleep(CPU_SAMPLE_S)
            cpu_now = p.cpu_percent(interval=None)
        else:
            cpu_now = p.cpu_percent(interval=None)

        ws_mb = round(mem.rss / 1024 / 1024)
        priv_mb = round(mem.vms / 1024 / 1024)
        threads = p.num_threads()

        # Orphan detection (cross-platform)
        if SYSTEM == "Windows":
            parent_gone = not parent_alive
        else:
            # On Unix, orphaned processes get re-parented to PID 1 (init/launchd)
            parent_gone = p.ppid() in (0, 1) or not parent_alive

        safe_from_kill = ws_mb > KILL_SAFE_WS_MB or cpu_now > KILL_MAX_CPU_PCT
        is_zombie = (
            not safe_from_kill
            and ws_mb < KILL_MAX_WS_MB
            and cpu_now < KILL_MAX_CPU_PCT
            and threads < KILL_MAX_THREADS
            and age_s > KILL_MIN_AGE_MIN * 60
        )

        return {
            "pid": p.pid,
            "started": create.isoformat(),
            "age_min": round(age_s / 60, 1),
            "age_h": round(age_s / 3600, 1),
            "ws_mb": ws_mb,
            "priv_mb": priv_mb,
            "cpu_now_pct": round(cpu_now, 2),
            "threads": threads,
            "is_zombie": is_zombie,
            "safe_from_kill": safe_from_kill,
            "orphaned": parent_gone,
            "cmdline": cmdline[:120],
            "parent_name": parent_name,
            "parent_pid": p.ppid(),
            "parent_alive": parent_alive,
            "platform": SYSTEM,
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


# ── notifications (cross-platform) ───────────────────────────────────────────

def notify(title: str, message: str):
    """Send desktop notification — cross-platform."""
    try:
        if SYSTEM == "Darwin":
            os.system(f'osascript -e \'display notification "{message}" with title "{title}"\'')
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


# ── cleanup ───────────────────────────────────────────────────────────────────

def run_cleanup(dry_run: bool = False) -> dict:
    """Sample CPU, then decide who to kill."""
    procs = find_cli_processes()

    # Prime CPU counters
    for p in procs:
        try:
            p.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    time.sleep(CPU_SAMPLE_S)

    active, zombies = [], []
    for p in procs:
        info = process_info(p, sample_cpu=False)
        if not info:
            continue
        if info["is_zombie"]:
            zombies.append((p, info))
        else:
            active.append(info)

    killed, failed = [], []
    for p, info in zombies:
        reason = (f"ws={info['ws_mb']}MB cpu={info['cpu_now_pct']}% "
                  f"thr={info['threads']} age={info['age_min']:.0f}min")
        if dry_run:
            killed.append(info)
            continue
        try:
            p.kill()
            killed.append(info)
            _log_event("killed", info, reason)
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            failed.append({"pid": info["pid"], "error": str(e)})

    saved_mb = sum(i["priv_mb"] for _, i in zombies)
    return {
        "active": len(active),
        "zombies": len(zombies),
        "killed": len(killed),
        "failed": len(failed),
        "saved_mb": saved_mb,
        "dry_run": dry_run,
        "platform": SYSTEM,
    }


# ── JSON output for statusline ────────────────────────────────────────────────

def json_status() -> dict:
    """Quick status without CPU sampling — for statusline integration."""
    procs = find_cli_processes()
    infos = []
    for p in procs:
        try:
            with p.oneshot():
                mem = p.memory_info()
                ws_mb = round(mem.rss / 1024 / 1024)
                age_s = time.time() - p.create_time()
                threads = p.num_threads()
            is_zombie_guess = (
                ws_mb < KILL_MAX_WS_MB
                and threads < KILL_MAX_THREADS
                and age_s > KILL_MIN_AGE_MIN * 60
            )
            infos.append({
                "pid": p.pid,
                "ws_mb": ws_mb,
                "age_h": round(age_s / 3600, 1),
                "threads": threads,
                "likely_zombie": is_zombie_guess,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    total_ws = sum(i["ws_mb"] for i in infos)
    zombies = sum(1 for i in infos if i["likely_zombie"])

    return {
        "total": len(infos),
        "zombies": zombies,
        "active": len(infos) - zombies,
        "total_ws_mb": total_ws,
        "platform": SYSTEM,
    }


# ── report ────────────────────────────────────────────────────────────────────

def build_report() -> str:
    procs = find_cli_processes()

    # Prime + sample
    for p in procs:
        try:
            p.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    time.sleep(CPU_SAMPLE_S)

    infos = [i for p in procs if (i := process_info(p, sample_cpu=False))]
    infos.sort(key=lambda x: x["priv_mb"], reverse=True)

    zombies = [i for i in infos if i["is_zombie"]]
    total_ws = sum(i["ws_mb"] for i in infos)

    lines = [
        f"# Process Monitor Report ({SYSTEM})",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Platform | {SYSTEM} |",
        f"| Total processes | {len(infos)} |",
        f"| Active | {len(infos) - len(zombies)} |",
        f"| Zombies | {len(zombies)} |",
        f"| Total WS | {total_ws:,} MB |",
        "",
        "| PID | WS | CPU% | Threads | Age | Orphan | Status |",
        "|-----|-----|------|---------|-----|--------|--------|",
    ]

    for i in infos:
        age = f"{i['age_h']:.1f}h"
        status = "ZOMBIE" if i["is_zombie"] else ("WARN" if i["age_h"] > WARN_AGE_H else "ok")
        orphan = "yes" if i["orphaned"] else "no"
        lines.append(
            f"| {i['pid']} | {i['ws_mb']}M | {i['cpu_now_pct']}% | "
            f"{i['threads']} | {age} | {orphan} | {status} |"
        )

    return "\n".join(lines)


# ── logging ───────────────────────────────────────────────────────────────────

def _log_event(event: str, info: dict, reason: str = ""):
    log_file = LOG_DIR / "events.jsonl"
    record = {"event": event, "ts": datetime.now().isoformat(),
              "pid": info["pid"], "reason": reason, "platform": SYSTEM}
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ── install (cross-platform) ─────────────────────────────────────────────────

def install_scheduler():
    """Install periodic cleanup as platform-appropriate scheduler."""
    monitor_path = Path(__file__).resolve()
    python_exe = sys.executable

    if SYSTEM == "Windows":
        import subprocess
        cmd = (
            f'schtasks /Create /F /RL HIGHEST '
            f'/TN "ClaudeProcessMonitor" '
            f'/TR "\"{python_exe}\" \"{monitor_path}\" --cleanup" '
            f'/SC MINUTE /MO 30'
        )
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(f"Windows Task Scheduler: {'OK' if r.returncode == 0 else r.stderr.strip()}")

    elif SYSTEM == "Darwin":
        plist_path = Path.home() / "Library/LaunchAgents/com.claude.process-monitor.plist"
        plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.claude.process-monitor</string>
    <key>ProgramArguments</key><array>
        <string>{python_exe}</string>
        <string>{monitor_path}</string>
        <string>--cleanup</string>
    </array>
    <key>StartInterval</key><integer>1800</integer>
    <key>RunAtLoad</key><true/>
</dict>
</plist>"""
        plist_path.write_text(plist)
        os.system(f"launchctl load {plist_path}")
        print(f"macOS LaunchAgent: OK ({plist_path})")

    else:  # Linux
        cron_line = f"*/30 * * * * {python_exe} {monitor_path} --cleanup"
        import subprocess
        existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        lines = existing.stdout.strip().split("\n") if existing.returncode == 0 else []
        lines = [l for l in lines if "process-monitor" not in l]
        lines.append(cron_line)
        proc = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
        proc.communicate("\n".join(lines) + "\n")
        print(f"Linux crontab: OK (every 30 min)")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Cross-platform CLI process monitor")
    parser.add_argument("--status", action="store_true", help="Show current state")
    parser.add_argument("--cleanup", action="store_true", help="One-shot cleanup")
    parser.add_argument("--dry-run", action="store_true", help="Show kills, don't execute")
    parser.add_argument("--report", action="store_true", help="Markdown report")
    parser.add_argument("--json", action="store_true", help="JSON output for statusline")
    parser.add_argument("--install", action="store_true", help="Install as scheduled task")
    parser.add_argument("--uninstall", action="store_true", help="Remove scheduled task")
    args = parser.parse_args()

    if args.json:
        print(json.dumps(json_status()))
        return

    if args.install:
        install_scheduler()
        return

    if args.uninstall:
        if SYSTEM == "Windows":
            import subprocess
            subprocess.run('schtasks /Delete /TN "ClaudeProcessMonitor" /F', shell=True)
        elif SYSTEM == "Darwin":
            plist = Path.home() / "Library/LaunchAgents/com.claude.process-monitor.plist"
            os.system(f"launchctl unload {plist} 2>/dev/null")
            plist.unlink(missing_ok=True)
        else:
            import subprocess
            existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            lines = [l for l in existing.stdout.strip().split("\n")
                     if "process-monitor" not in l and l.strip()]
            proc = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
            proc.communicate("\n".join(lines) + "\n")
        print(f"Uninstalled on {SYSTEM}")
        return

    if args.report:
        report = build_report()
        path = LOG_DIR / f"report-{datetime.now().strftime('%Y-%m-%d')}.md"
        path.write_text(report, encoding="utf-8")
        print(report)
        return

    if args.status:
        procs = find_cli_processes()
        for p in procs:
            try:
                p.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(CPU_SAMPLE_S)

        for p in sorted(procs, key=lambda x: x.pid):
            info = process_info(p, sample_cpu=False)
            if not info:
                continue
            status = "ZOMBIE" if info["is_zombie"] else "ok"
            age = f"{info['age_h']:.1f}h" if info["age_h"] >= 2 else f"{info['age_min']:.0f}m"
            print(f"  {info['pid']:>7}  {info['ws_mb']:>5}M  cpu={info['cpu_now_pct']:>5}%  "
                  f"thr={info['threads']:>3}  {age:>7}  {status}")
        return

    if args.cleanup or args.dry_run:
        summary = run_cleanup(dry_run=args.dry_run)
        print(json.dumps(summary, indent=2))
        return

    # Continuous mode
    print(f"process-monitor running on {SYSTEM} (cleanup every {CLEANUP_INTERVAL_S}s)")
    while True:
        try:
            run_cleanup()
        except Exception as e:
            log.warning("Cleanup error: %s", e)
        time.sleep(CLEANUP_INTERVAL_S)


if __name__ == "__main__":
    main()
