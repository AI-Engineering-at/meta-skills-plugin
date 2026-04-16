#!/usr/bin/env python3
"""plugin-setup.py — First-run and reconfigure for meta-skills plugin.

Called automatically by session-init.py on first run (--auto),
or interactively by user via /statusbar setup.

Cross-platform: Windows, macOS, Linux.

Usage:
  python plugin-setup.py              # Interactive setup
  python plugin-setup.py --auto       # Silent with defaults (for hooks)
  python plugin-setup.py --show       # Show current config
  python plugin-setup.py --reset      # Reset to defaults
"""
import json
import os
import platform
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SYSTEM = platform.system()  # Windows, Darwin, Linux

# Plugin data directory (persistent across updates)
PLUGIN_DATA = Path(os.environ.get(
    "CLAUDE_PLUGIN_DATA",
    Path.home() / ".claude" / "plugins" / "data" / "meta-skills"
))
PLUGIN_DATA.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = PLUGIN_DATA / "config.json"
SETUP_MARKER = PLUGIN_DATA / ".setup-done-v2"

# Plugin root (where scripts live)
PLUGIN_ROOT = Path(__file__).parent.parent

# Default config
DEFAULT_CONFIG = {
    "version": 2,
    "platform": SYSTEM,
    "setup_date": datetime.now().strftime("%Y-%m-%d"),
    "features": {
        "statusline": True,
        "watcher": True,
        "sync_on_stop": True,
        "correction_detect": True,
        "honcho_context": True,
        "notebook_search": True,
        "process_watchdog": False,
    },
    "thresholds": {
        "ram_warn_mb": 4000,
        "ram_spike_mb": 500,
        "age_warn_h": 24,
        "watcher_poll_s": 10,
    },
    "services": {
        "honcho_url": "http://10.40.10.82:8055",
        "notebook_api": "http://10.40.10.82:5055",
        "notebook_id": "notebook:zkxy9fiwelrolgbr2upc",
    },
}


def load_config() -> dict:
    """Load existing config or return defaults."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """Save config to plugin data directory."""
    CONFIG_FILE.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def is_setup_done() -> bool:
    return SETUP_MARKER.exists()


def mark_setup_done():
    SETUP_MARKER.write_text(
        datetime.now().isoformat(),
        encoding="utf-8",
    )


# ── platform detection ────────────────────────────────────────────────────────

def detect_environment() -> dict:
    """Detect what's available on this system."""
    env = {
        "platform": SYSTEM,
        "python": sys.executable,
        "home": str(Path.home()),
        "has_psutil": False,
        "has_git": False,
        "plugin_root": str(PLUGIN_ROOT),
    }

    try:
        import psutil  # noqa: F401 — availability probe
        env["has_psutil"] = True
    except ImportError:
        pass

    try:
        import subprocess
        r = subprocess.run(["git", "--version"], capture_output=True, timeout=3)
        env["has_git"] = r.returncode == 0
    except Exception:
        pass

    return env


# ── statusline snippet ────────────────────────────────────────────────────────

def statusline_snippet() -> str:
    """Generate the settings.json snippet for statusline."""
    script = PLUGIN_ROOT / "scripts" / "statusline.py"
    return json.dumps({
        "statusLine": {
            "type": "command",
            "command": f"python3 {str(script).replace(chr(92), '/')}"
        }
    }, indent=2)


# ── interactive setup ─────────────────────────────────────────────────────────

def ask(question: str, default: str = "y") -> bool:
    """Ask yes/no question. Default on empty input."""
    d = "[Y/n]" if default.lower() == "y" else "[y/N]"
    try:
        answer = input(f"  {question} {d}: ").strip().lower()
        if not answer:
            return default.lower() == "y"
        return answer in ("y", "yes", "ja", "j")
    except (EOFError, KeyboardInterrupt):
        return default.lower() == "y"


def ask_int(question: str, default: int) -> int:
    """Ask for integer input."""
    try:
        answer = input(f"  {question} [{default}]: ").strip()
        if not answer:
            return default
        return int(answer)
    except (EOFError, KeyboardInterrupt, ValueError):
        return default


def interactive_setup() -> dict:
    """Run interactive setup. Returns config dict."""
    config = DEFAULT_CONFIG.copy()
    env = detect_environment()

    print("\n" + "=" * 60)
    print("  Meta-Skills Plugin Setup")
    print(f"  Platform: {SYSTEM} | Python: {sys.version.split()[0]}")
    print("=" * 60)

    # Features
    print("\n-- Features --")
    config["features"]["statusline"] = ask("Statusline aktivieren? (Model, Costs, Context, Limits)")
    config["features"]["watcher"] = ask("Session Watcher? (RAM-Warnungen, Ghost-Cleanup bei Terminal-Tod)")
    config["features"]["sync_on_stop"] = ask("Auto-Sync bei Session-Ende? (Honcho + open-notebook)")
    config["features"]["correction_detect"] = ask("Korrektur-Erkennung? (S10 Compliance)")
    config["features"]["honcho_context"] = ask("Honcho Context bei Session-Start laden?")
    config["features"]["notebook_search"] = ask("open-notebook Suche bei Session-Start?")

    if env["has_psutil"]:
        config["features"]["process_watchdog"] = ask(
            "Process Watchdog als Scheduled Task? (prueft alle 30min)", default="n"
        )
    else:
        print("  Process Watchdog: uebersprungen (psutil nicht installiert)")
        config["features"]["process_watchdog"] = False

    # Thresholds (only if watcher enabled)
    if config["features"]["watcher"]:
        print("\n-- Watcher Schwellenwerte --")
        config["thresholds"]["ram_warn_mb"] = ask_int("RAM-Warnung ab (MB)", 4000)
        config["thresholds"]["ram_spike_mb"] = ask_int("RAM-Spike Warnung ab (MB)", 500)
        config["thresholds"]["age_warn_h"] = ask_int("Session-Alter Warnung ab (Stunden)", 24)

    # Services
    print("\n-- Services (Enter fuer Defaults) --")
    try:
        val = input(f"  Honcho URL [{config['services']['honcho_url']}]: ").strip()
        if val:
            config["services"]["honcho_url"] = val
        val = input(f"  open-notebook API [{config['services']['notebook_api']}]: ").strip()
        if val:
            config["services"]["notebook_api"] = val
    except (EOFError, KeyboardInterrupt):
        pass

    config["platform"] = SYSTEM
    config["setup_date"] = datetime.now().strftime("%Y-%m-%d")

    return config


# ── auto setup (silent) ──────────────────────────────────────────────────────

def auto_setup() -> dict:
    """Silent setup with platform-appropriate defaults."""
    config = DEFAULT_CONFIG.copy()
    config["platform"] = SYSTEM

    env = detect_environment()
    config["features"]["process_watchdog"] = False  # Never auto-enable scheduled tasks
    config["features"]["watcher"] = env["has_psutil"]  # Only if psutil available

    return config


# ── install watchdog (optional) ───────────────────────────────────────────────

def install_watchdog():
    """Install process-monitor as scheduled task (platform-specific)."""
    import subprocess
    monitor = PLUGIN_ROOT / "scripts" / "process-monitor.py"

    if SYSTEM == "Windows":
        cmd = (
            f'schtasks /Create /F /RL HIGHEST '
            f'/TN "MetaSkillsProcessMonitor" '
            f'/TR "\"{sys.executable}\" \"{monitor}\" --cleanup" '
            f'/SC MINUTE /MO 30'
        )
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return r.returncode == 0, "Windows Task Scheduler"

    elif SYSTEM == "Darwin":
        plist_path = Path.home() / "Library/LaunchAgents/com.meta-skills.process-monitor.plist"
        plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
    <key>Label</key><string>com.meta-skills.process-monitor</string>
    <key>ProgramArguments</key><array>
        <string>{sys.executable}</string>
        <string>{monitor}</string>
        <string>--cleanup</string>
    </array>
    <key>StartInterval</key><integer>1800</integer>
    <key>RunAtLoad</key><true/>
</dict></plist>"""
        plist_path.write_text(plist)
        os.system(f"launchctl load {plist_path}")
        return True, "macOS LaunchAgent"

    else:  # Linux
        cron_line = f"*/30 * * * * {sys.executable} {monitor} --cleanup"
        existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        lines = existing.stdout.strip().split("\n") if existing.returncode == 0 else []
        lines = [l for l in lines if "meta-skills" not in l.lower() and "process-monitor" not in l]
        lines.append(cron_line)
        proc = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
        proc.communicate("\n".join(lines) + "\n")
        return True, "Linux crontab"


# ── show config ───────────────────────────────────────────────────────────────

def show_config():
    """Display current configuration."""
    config = load_config()

    print("\n" + "=" * 60)
    print("  Meta-Skills Plugin Configuration")
    print("=" * 60)
    print(f"\n  Platform:   {config.get('platform', '?')}")
    print(f"  Setup Date: {config.get('setup_date', '?')}")
    print(f"  Version:    {config.get('version', '?')}")

    print("\n  Features:")
    for k, v in config.get("features", {}).items():
        status = "ON" if v else "OFF"
        print(f"    {k:25s} {status}")

    print("\n  Thresholds:")
    for k, v in config.get("thresholds", {}).items():
        print(f"    {k:25s} {v}")

    print("\n  Services:")
    for k, v in config.get("services", {}).items():
        print(f"    {k:25s} {v}")

    if not config.get("features", {}).get("statusline"):
        print("\n  Statusline: DEAKTIVIERT")
    else:
        print("\n  Statusline Snippet (in ~/.claude/settings.json einfuegen):")
        print(f"  {statusline_snippet()}")


# ── summary (for systemMessage) ──────────────────────────────────────────────

def config_summary(config: dict) -> str:
    """One-line summary for hook systemMessage."""
    features = config.get("features", {})
    on = [k for k, v in features.items() if v]
    return f"Meta-Skills Setup: {len(on)}/{len(features)} Features aktiv ({', '.join(on)})"


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if "--show" in args:
        show_config()
        return

    if "--reset" in args:
        SETUP_MARKER.unlink(missing_ok=True)
        CONFIG_FILE.unlink(missing_ok=True)
        print("Config und Setup-Marker zurueckgesetzt. Naechster Sessionstart fuehrt Setup erneut aus.")
        return

    if "--auto" in args:
        # Silent setup with defaults — called by session-init.py
        config = auto_setup()
        save_config(config)
        mark_setup_done()
        # Output summary for systemMessage integration
        print(json.dumps({"setup_done": True, "summary": config_summary(config)}))
        return

    # Interactive setup
    config = interactive_setup()

    # Save
    save_config(config)
    mark_setup_done()

    # Install watchdog if requested
    if config["features"]["process_watchdog"]:
        print("\nProcess Watchdog installieren...")
        ok, method = install_watchdog()
        print(f"  {method}: {'OK' if ok else 'FEHLER'}")

    # Summary
    print("\n" + "=" * 60)
    print("  Setup abgeschlossen!")
    print("=" * 60)

    on = [k for k, v in config["features"].items() if v]
    print(f"\n  {len(on)} Features aktiviert: {', '.join(on)}")
    print(f"  Config: {CONFIG_FILE}")

    if config["features"]["statusline"]:
        print("\n  WICHTIG: Statusline muss manuell in ~/.claude/settings.json eingefuegt werden:")
        print(f"  {statusline_snippet()}")

    if not config["features"]["watcher"]:
        print("\n  HINWEIS: Session Watcher ist deaktiviert.")
        print("  Ohne Watcher werden Ghost-Prozesse bei Terminal-Absturz NICHT aufgeraeumt.")

    print(f"\n  Reconfigure: python {__file__}")
    print(f"  Anzeigen:    python {__file__} --show")
    print(f"  Zuruecksetzen: python {__file__} --reset")


if __name__ == "__main__":
    main()
