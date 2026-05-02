"""Centralized Session State Manager (Phase 3, v4.0)

Replaces 7 scattered state file patterns with one `.meta-state-{session_id}.json`
per session. Each hook gets its own namespace within the unified state dict.

Old patterns eliminated:
  .session-init-{id}          → state["session_init"]
  .prompt-counter-{id}        → state["prompt_count"]
  .quality-gate-{id}.json     → state["quality_gate"]
  .scope-tracker-{id}.json    → state["scope_tracker"]
  .escalation-state.json      → state["correction_detect"]  (was global — now per-session)
  .approach-guard-{id}.json   → state["approach_guard"]
  .exploration-first-{id}.json → state["exploration_first"]
  .session-state-{id}.json    → state["session_meta"]

Usage:
    from lib.state import SessionState

    state = SessionState(session_id)
    qg = state.get("quality_gate")
    qg["consecutive_failures"] += 1
    state.set("quality_gate", qg)
    state.save()
"""

import contextlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

STATE_DIR = Path(
    os.environ.get(
        "CLAUDE_PLUGIN_DATA",
        Path.home() / ".claude" / "plugins" / "data" / "meta-skills",
    )
)

# session_id whitelist: alphanumeric + dash + underscore, 1-64 chars.
# Covers UUIDs ("a533d28d-ce6e-4c3d-b6b2-9fac4bb7268f") and short test IDs.
# Rejects path-traversal segments, control chars, shell metachars (TASK-2026-00679).
_SAFE_SESSION_ID = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

# Default state per hook namespace
DEFAULTS = {
    "session_init": {
        "initialized": False,
    },
    "prompt_count": 0,
    "quality_gate": {
        "consecutive_failures": 0,
        "suggested_debugging": False,
        "last_lint_result": "NOT_RUN",
        "last_test_result": "NOT_RUN",
    },
    "scope_tracker": {
        "initial_domains": [],
        "seen_domains": [],
        "prompt_count": 0,
        "task_switches": 0,
        "warned": False,
    },
    "correction_detect": {
        "correction_count": 0,
        "last_severity": None,
    },
    "approach_guard": {
        "bash_count": 0,
        "scope_confirmed": False,
    },
    "exploration_first": {
        "read_count": 0,
        "write_count": 0,
        "phase": "exploration",
        "warned": False,
    },
    "session_meta": {
        "project": "",
        "cwd": "",
        "timestamp": "",
        "git_summary": "",
        "uncommitted": False,
        "lint_status": "unknown",
        "open_items": "none",
    },
}


def _deep_copy(obj):
    """Deep copy without importing copy module."""
    if isinstance(obj, dict):
        return {k: _deep_copy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_copy(item) for item in obj]
    return obj


class SessionState:
    """Unified per-session state. One JSON file per session."""

    def __init__(self, session_id: str):
        if not isinstance(session_id, str) or not _SAFE_SESSION_ID.fullmatch(session_id):
            raise ValueError(f"invalid session_id: {session_id!r} (must match {_SAFE_SESSION_ID.pattern})")
        self.session_id = session_id
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.path = STATE_DIR / f".meta-state-{session_id}.json"
        # Defense-in-depth: resolved path must stay inside STATE_DIR even if
        # the regex above were ever loosened (catches symlink edge-cases).
        if STATE_DIR.resolve() not in self.path.resolve().parents:
            raise ValueError(f"session_id path escape: {self.path}")
        self._data = self._load()

    def _load(self) -> dict:
        """Load state from disk, merging with defaults for missing keys."""
        state = {"session_id": self.session_id}
        if self.path.exists():
            try:
                state = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                state = {"session_id": self.session_id}
        # Ensure all default namespaces exist
        for key, default in DEFAULTS.items():
            if key not in state:
                state[key] = _deep_copy(default)
        return state

    def get(self, namespace: str):
        """Get state for a hook namespace. Returns default if missing."""
        if namespace not in self._data:
            if namespace in DEFAULTS:
                self._data[namespace] = _deep_copy(DEFAULTS[namespace])
            else:
                return None
        return self._data[namespace]

    def set(self, namespace: str, value) -> None:
        """Set state for a hook namespace."""
        self._data[namespace] = value

    @property
    def prompt_count(self) -> int:
        """Shortcut for prompt counter (most frequently accessed)."""
        return self._data.get("prompt_count", 0)

    @prompt_count.setter
    def prompt_count(self, value: int) -> None:
        self._data["prompt_count"] = value

    @property
    def is_initialized(self) -> bool:
        """Whether session-init has already run."""
        init = self._data.get("session_init", {})
        return init.get("initialized", False)

    @is_initialized.setter
    def is_initialized(self, value: bool) -> None:
        if "session_init" not in self._data:
            self._data["session_init"] = _deep_copy(DEFAULTS["session_init"])
        self._data["session_init"]["initialized"] = value

    def save(self) -> None:
        """Persist state to disk atomically (TASK-2026-00680).

        Writes to a tempfile in STATE_DIR, then os.replace into place. Atomic
        on POSIX and Windows since Py3.3 when src+dst are on the same fs;
        same-fs is guaranteed by tempfile.mkstemp(dir=STATE_DIR).

        Best-effort: failures are logged to stderr but never raise — preserves
        prior behavior where save() never breaks the host hook.
        """
        payload = json.dumps(self._data, ensure_ascii=False, indent=2)
        tmp_fd, tmp_path = -1, ""
        try:
            tmp_fd, tmp_path = tempfile.mkstemp(
                prefix=f".meta-state-{self.session_id}.",
                suffix=".tmp",
                dir=STATE_DIR,
            )
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                tmp_fd = -1  # ownership transferred to fdopen's context
                f.write(payload)
            # os.replace + os.unlink intentional (not Path.replace/.unlink):
            # tests mock `lib.state.os.replace` to spy on atomicity contract.
            os.replace(tmp_path, self.path)  # noqa: PTH105
            tmp_path = ""  # consumed by replace
        except OSError as e:
            print(f"[state.save] OSError: {e}", file=sys.stderr)
        finally:
            if tmp_fd != -1:
                with contextlib.suppress(OSError):
                    os.close(tmp_fd)
            if tmp_path:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)  # noqa: PTH108

    def to_dict(self) -> dict:
        """Return full state as dict (for session-stop serialization)."""
        return _deep_copy(self._data)

    @staticmethod
    def cleanup_stale(keep: int = 5) -> None:
        """Remove old session state files, keeping the most recent N."""
        try:
            state_files = sorted(
                STATE_DIR.glob(".meta-state-*.json"),
                key=lambda f: f.stat().st_mtime,
            )
            for f in state_files[:-keep]:
                f.unlink(missing_ok=True)
        except OSError:
            pass

    @staticmethod
    def cleanup_legacy() -> None:
        """Remove old scattered state files from pre-v4.0 patterns."""
        legacy_patterns = [
            ".session-init-*",
            ".prompt-counter-*",
            ".quality-gate-*.json",
            ".scope-tracker-*.json",
            ".approach-guard-*.json",
            ".exploration-first-*.json",
            ".escalation-state.json",
            ".session-state-*.json",
        ]
        try:
            for pattern in legacy_patterns:
                for f in STATE_DIR.glob(pattern):
                    f.unlink(missing_ok=True)
        except OSError:
            pass
