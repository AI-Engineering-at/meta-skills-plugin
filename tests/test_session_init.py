"""Tests for hooks/session-init.py — prompt counter + P7 context recovery.

session-init executes top-level on import (reads stdin, increments state,
maybe prints additionalContext, exits). Test via subprocess with
controlled stdin + isolated CLAUDE_PLUGIN_DATA.

Covers:
- prompt counter increments on each call
- First prompt exits 0 with empty stdout
- Context recovery fires when gap > threshold AND session is initialized
- Context recovery NOT fired on first prompt
- Malformed stdin handled without crash
- Empty stdin handled without crash
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_FILE = REPO_ROOT / "hooks" / "session-init.py"

# Match session-init's state file convention.
sys.path.insert(0, str(REPO_ROOT / "hooks"))

from lib.state import SessionState  # noqa: E402


def _run(stdin_payload: str, tmp_path: Path, timeout: int = 10):
    env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
    return subprocess.run(
        [sys.executable, str(HOOK_FILE)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def _state(tmp_path: Path, session_id: str) -> dict:
    """Read the per-session state JSON after a hook run."""
    path = tmp_path / f".meta-state-{session_id}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


class TestPromptCounter:
    def test_first_prompt_increments_to_one(self, tmp_path):
        r = _run(json.dumps({"session_id": "init-sess-1"}), tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip() == ""  # no recovery on first prompt
        assert _state(tmp_path, "init-sess-1").get("prompt_count") == 1

    def test_second_prompt_increments_to_two(self, tmp_path):
        sid = "init-sess-2"
        _run(json.dumps({"session_id": sid}), tmp_path)
        _run(json.dumps({"session_id": sid}), tmp_path)
        assert _state(tmp_path, sid).get("prompt_count") == 2

    def test_separate_sessions_have_independent_counters(self, tmp_path):
        _run(json.dumps({"session_id": "sess-a"}), tmp_path)
        _run(json.dumps({"session_id": "sess-a"}), tmp_path)
        _run(json.dumps({"session_id": "sess-b"}), tmp_path)
        assert _state(tmp_path, "sess-a").get("prompt_count") == 2
        assert _state(tmp_path, "sess-b").get("prompt_count") == 1


class TestContextRecovery:
    def test_recovery_not_fired_on_first_prompt(self, tmp_path):
        r = _run(json.dumps({"session_id": "recov-first"}), tmp_path)
        assert r.stdout.strip() == "", "no recovery on first-ever prompt"

    def test_recovery_not_fired_when_session_not_initialized(self, tmp_path):
        """Even with a large prompt_count gap, if is_initialized is False,
        no recovery context should emit (session-init itself marks init later;
        session-start does it first). Simulate: manually set large gap in state
        without is_initialized."""
        sid = "recov-not-init"
        state = SessionState(sid)
        # Don't set is_initialized; set a big gap in session_meta.
        state.set("session_meta", {
            "prompt_count_at_save": 0,
            "project": "demo",
            "git_summary": "x",
            "open_items": "y",
        })
        state.prompt_count = 99
        state.save()
        # Move state file into tmp-scoped path for subprocess isolation
        import shutil
        real = state.path
        shutil.copy(real, tmp_path / real.name)

        r = _run(json.dumps({"session_id": sid}), tmp_path)
        assert r.stdout.strip() == "", "no recovery when is_initialized is False"

    def test_recovery_fires_when_initialized_and_gap_large(self, tmp_path, monkeypatch):
        """With is_initialized=True + prompt_count gap > RECOVERY_GAP (default 10),
        additionalContext is emitted."""
        sid = "recov-fires"
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        # Seed the state file directly
        state_file = tmp_path / f".meta-state-{sid}.json"
        state_file.write_text(json.dumps({
            "session_id": sid,
            "prompt_count": 50,  # current - will bump to 51
            "session_init": {"initialized": True},
            "session_meta": {
                "prompt_count_at_save": 20,  # saved_count -> gap = 51-20 = 31 > 10
                "project": "phantom-ai",
                "git_summary": "last: abc123 fix something",
                "open_items": "review PR #1",
            },
        }), encoding="utf-8")

        r = _run(json.dumps({"session_id": sid}), tmp_path)
        assert r.returncode == 0
        out = r.stdout.strip()
        assert out, f"expected recovery context; got empty stdout. stderr={r.stderr[:300]}"
        payload = json.loads(out)
        ctx = payload.get("additionalContext", "")
        assert "CONTEXT RECOVERY" in ctx
        assert "phantom-ai" in ctx
        assert "abc123" in ctx

    def test_recovery_not_fired_when_gap_small(self, tmp_path):
        """gap <= RECOVERY_GAP (10) means no recovery fires."""
        sid = "recov-small-gap"
        state_file = tmp_path / f".meta-state-{sid}.json"
        state_file.write_text(json.dumps({
            "session_id": sid,
            "prompt_count": 12,
            "session_init": {"initialized": True},
            "session_meta": {
                "prompt_count_at_save": 5,  # gap = 13-5 = 8 (after increment) — still <= 10
                "project": "demo",
                "git_summary": "x",
                "open_items": "y",
            },
        }), encoding="utf-8")
        r = _run(json.dumps({"session_id": sid}), tmp_path)
        assert r.stdout.strip() == ""


class TestEdgeCases:
    def test_malformed_stdin_exits_0(self, tmp_path):
        r = _run("{not valid json", tmp_path)
        assert r.returncode == 0

    def test_empty_stdin_exits_0(self, tmp_path):
        r = _run("", tmp_path)
        assert r.returncode == 0

    def test_missing_session_id_defaults_unknown(self, tmp_path):
        r = _run(json.dumps({}), tmp_path)  # no session_id
        assert r.returncode == 0
        assert _state(tmp_path, "unknown").get("prompt_count") == 1
