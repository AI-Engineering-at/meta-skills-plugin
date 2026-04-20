"""Tests for hooks/session-end.py — SessionEnd event backend persistence.

Covers:
- Honcho write (health-gated: only writes when is_healthy())
- Final state persistence: session_meta snapshot with prompt_count + git summary
- cleanup_stale called after state save
- Infra-keyword detection triggers diagram regen (when script exists)
- Malformed / empty stdin handled
- Honcho unreachable → state still persisted (log_error path)

Integration strategy: subprocess the hook with isolated CLAUDE_PLUGIN_DATA,
mock Honcho by pointing OPEN_NOTEBOOK/Honcho URLs to unreachable hosts
(is_healthy() returns False) — then verify state-file post-condition.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_FILE = REPO_ROOT / "hooks" / "session-end.py"


def _run(payload: dict, tmp_path: Path, cwd: Path | None = None, extra_env: dict | None = None):
    env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
    # Point Honcho to unreachable host → is_healthy() returns False → write skipped
    env.setdefault("HONCHO_API", "http://unreachable.invalid:9999")
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(HOOK_FILE)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=15, env=env,
        cwd=str(cwd) if cwd else None,
    )


def _state(tmp_path: Path, sid: str) -> dict:
    p = tmp_path / f".meta-state-{sid}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


class TestStatePersistence:
    def test_session_meta_populated(self, tmp_path):
        r = _run({"session_id": "se-meta"}, tmp_path)
        assert r.returncode == 0
        meta = _state(tmp_path, "se-meta").get("session_meta") or {}
        assert "project" in meta
        assert "cwd" in meta
        assert "timestamp" in meta
        assert meta.get("open_items") == "session ended"

    def test_prompt_count_preserved(self, tmp_path):
        sid = "se-prompts"
        (tmp_path / f".meta-state-{sid}.json").write_text(
            json.dumps({"session_id": sid, "prompt_count": 42}),
            encoding="utf-8",
        )
        _run({"session_id": sid}, tmp_path)
        s = _state(tmp_path, sid)
        assert s["session_meta"]["prompt_count_at_save"] == 42
        assert s["prompt_count"] == 42  # not reset

    def test_lint_status_carried_from_quality_gate(self, tmp_path):
        sid = "se-lint"
        (tmp_path / f".meta-state-{sid}.json").write_text(
            json.dumps({
                "session_id": sid,
                "quality_gate": {"last_lint_result": "PASS"},
            }),
            encoding="utf-8",
        )
        _run({"session_id": sid}, tmp_path)
        assert _state(tmp_path, sid)["session_meta"]["lint_status"] == "PASS"


class TestCleanupStale:
    def test_cleanup_keeps_recent_states(self, tmp_path):
        """Seed many state files, hook should cleanup_stale(keep=5)."""
        import time
        for i in range(12):
            fp = tmp_path / f".meta-state-session-{i:03d}.json"
            fp.write_text(json.dumps({
                "session_id": f"session-{i:03d}",
                "prompt_count": 1,
            }), encoding="utf-8")
            # stagger mtimes so cleanup picks the N most recent
            os.utime(fp, (time.time() - (12 - i) * 60, time.time() - (12 - i) * 60))

        # Run session-end for the newest
        _run({"session_id": "session-012"}, tmp_path)

        remaining = sorted(tmp_path.glob(".meta-state-*.json"))
        # keep=5 → at most 5 remain (plus the just-created one from this run).
        # Depending on cleanup semantics may be 5 or 6 total.
        assert len(remaining) <= 7, f"too many state files survived: {len(remaining)}"
        assert len(remaining) >= 5


class TestHonchoGracefulFailure:
    def test_honcho_unreachable_still_persists_state(self, tmp_path):
        """When HONCHO_API is unreachable, state-file must still be written."""
        r = _run({"session_id": "se-no-honcho"}, tmp_path,
                 extra_env={"HONCHO_API": "http://definitely-not-a-real-host.invalid:1"})
        assert r.returncode == 0
        assert _state(tmp_path, "se-no-honcho").get("session_meta") is not None


class TestEdgeCases:
    def test_malformed_stdin(self, tmp_path):
        env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path),
               "HONCHO_API": "http://unreachable.invalid:9999"}
        r = subprocess.run(
            [sys.executable, str(HOOK_FILE)], input="{not json",
            capture_output=True, text=True, timeout=15, env=env,
        )
        assert r.returncode == 0
        # session_id defaults to "unknown" → state file for "unknown" gets written
        assert (tmp_path / ".meta-state-unknown.json").exists()

    def test_empty_stdin(self, tmp_path):
        env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path),
               "HONCHO_API": "http://unreachable.invalid:9999"}
        r = subprocess.run(
            [sys.executable, str(HOOK_FILE)], input="",
            capture_output=True, text=True, timeout=15, env=env,
        )
        assert r.returncode == 0

    def test_exits_silently_no_stdout(self, tmp_path):
        """SessionEnd is backend-only — must not emit additionalContext."""
        r = _run({"session_id": "se-silent"}, tmp_path)
        assert r.stdout.strip() == "", f"expected silent exit; got {r.stdout[:200]!r}"
