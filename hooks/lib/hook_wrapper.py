"""hook_wrapper.py — Error-handling wrapper for all meta-skills hooks.

Usage in any hook:
    from lib.hook_wrapper import safe_hook

    @safe_hook("my_hook_name")
    def main():
        # ... hook logic ...
        return {"systemMessage": "..."}  # optional

Catches all exceptions, logs to hook-errors.log, never blocks Claude Code.
"""

import json
import os
import sys
import traceback
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path

LOG_DIR = Path(
    os.environ.get(
        "CLAUDE_PLUGIN_DATA",
        Path.home() / ".claude" / "plugins" / "data" / "meta-skills",
    )
)
LOG_FILE = LOG_DIR / "hook-errors.log"
MAX_LOG_SIZE = 512 * 1024  # 512 KB, then rotate


def _rotate_log():
    """Rotate log if too large."""
    try:
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > MAX_LOG_SIZE:
            backup = LOG_FILE.with_suffix(".log.1")
            if backup.exists():
                backup.unlink()
            LOG_FILE.rename(backup)
    except Exception:
        pass


def _log_error(hook_name: str, error: Exception, context: str = ""):
    """Append error to hook-errors.log."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        _rotate_log()
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        tb = traceback.format_exception(type(error), error, error.__traceback__)
        entry = (
            f"[{ts}] HOOK={hook_name} ERROR={type(error).__name__}: {error}\n"
            f"  CONTEXT: {context}\n"
            f"  TRACEBACK: {''.join(tb[-3:]).strip()}\n"
        )
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass  # logging must never fail


def safe_hook(hook_name: str):
    """Decorator that wraps a hook function with error handling.

    The wrapped function can:
    - Return a dict → printed as JSON (for systemMessage hooks)
    - Return None → exits silently
    - Raise any exception → caught, logged, exits cleanly
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                if result and isinstance(result, dict):
                    print(json.dumps(result))
                sys.exit(0)
            except SystemExit:
                raise  # let sys.exit() through
            except Exception as e:
                _log_error(hook_name, e, f"args={args}")
                sys.exit(0)  # never block Claude Code

        return wrapper

    return decorator


def get_recent_errors(limit: int = 10) -> list[str]:
    """Read recent errors from log file. Used by meta-status command."""
    try:
        if not LOG_FILE.exists():
            return []
        lines = (
            LOG_FILE.read_text(encoding="utf-8", errors="replace").strip().split("\n")
        )
        # Each entry is ~3 lines, get last N entries
        entries = []
        current = []
        for line in lines:
            if line.startswith("[") and current:
                entries.append("\n".join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            entries.append("\n".join(current))
        return entries[-limit:]
    except Exception:
        return []
