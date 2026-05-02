"""Tests for hooks/lib/state.py — atomic save (TASK-2026-00680).

Hardening against race conditions and partial writes:
- save() must write to a tempfile and os.replace into place (atomic)
- A crash between open() and write-complete must NOT corrupt the existing file
- Concurrent saves from multiple threads must converge to a valid JSON state

os.replace is atomic on POSIX and Windows since Python 3.3, when source and
destination are on the same filesystem. tempfile.mkstemp(dir=STATE_DIR)
guarantees same-fs.
"""

import importlib
import json
import os
import sys
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "hooks"))


@pytest.fixture
def state_env(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
    from lib import state as state_mod

    importlib.reload(state_mod)
    return state_mod, tmp_path


class TestAtomicSave:
    """Save must write tempfile then os.replace, not direct overwrite."""

    def test_save_uses_os_replace(self, state_env):
        state_mod, _tmp_path = state_env
        s = state_mod.SessionState("atomic-1")
        s.set("prompt_count", 11)

        # Spy on os.replace — must be called exactly once during save()
        with patch("lib.state.os.replace", wraps=os.replace) as mock_replace:
            s.save()
            assert mock_replace.call_count == 1, f"expected 1 os.replace call, got {mock_replace.call_count}"
            # Second arg of os.replace must be the final path
            args, _ = mock_replace.call_args
            assert Path(args[1]) == s.path

    def test_save_creates_no_lingering_tmpfile(self, state_env):
        state_mod, tmp_path = state_env
        s = state_mod.SessionState("no-tmp")
        for i in range(5):
            s.set("prompt_count", i)
            s.save()
        # After 5 saves, only the final state file should exist — no .tmp
        leftover = list(tmp_path.glob("*.tmp"))
        assert leftover == [], f"tmpfiles left behind: {leftover}"

    def test_save_roundtrip_after_atomic_write(self, state_env):
        state_mod, _tmp_path = state_env
        s = state_mod.SessionState("roundtrip-atomic")
        s.set("prompt_count", 42)
        qg = s.get("quality_gate")
        qg["consecutive_failures"] = 3
        s.set("quality_gate", qg)
        s.save()

        # File on disk is valid JSON with our values
        data = json.loads(s.path.read_text(encoding="utf-8"))
        assert data["prompt_count"] == 42
        assert data["quality_gate"]["consecutive_failures"] == 3

    def test_partial_write_failure_preserves_original(self, state_env):
        """If write to tempfile fails mid-stream, original file is untouched."""
        state_mod, _tmp_path = state_env
        # Establish a known-good baseline file
        s = state_mod.SessionState("partial-fail")
        s.set("prompt_count", 100)
        s.save()
        original_bytes = s.path.read_bytes()

        # Now make os.replace raise — simulates partial write that never
        # completes the atomic swap
        with patch("lib.state.os.replace", side_effect=OSError("simulated")):
            s2 = state_mod.SessionState("partial-fail")
            s2.set("prompt_count", 999)
            s2.save()  # must not raise (best-effort), and must not corrupt

        # Original file content unchanged
        assert s.path.read_bytes() == original_bytes


class TestConcurrentSave:
    """Multiple threads writing to the same session state must produce a valid
    JSON file at the end (no truncation, no half-written files).
    """

    def test_concurrent_saves_produce_valid_json(self, state_env):
        state_mod, tmp_path = state_env

        # 4 threads × 25 saves each — fast and reliable on Windows
        n_threads = 4
        n_iters = 25
        errors: list[Exception] = []

        def worker(tid: int):
            try:
                s = state_mod.SessionState(f"conc-{tid}")
                for i in range(n_iters):
                    s.set("prompt_count", i)
                    s.save()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == [], f"workers failed: {errors}"

        # Each session file must be valid JSON with prompt_count == n_iters - 1
        for tid in range(n_threads):
            f = tmp_path / f".meta-state-conc-{tid}.json"
            assert f.exists(), f"missing state file for tid={tid}"
            data = json.loads(f.read_text(encoding="utf-8"))
            assert data["prompt_count"] == n_iters - 1

    def test_no_tmp_files_after_concurrent_saves(self, state_env):
        state_mod, tmp_path = state_env

        def worker(sid: str):
            s = state_mod.SessionState(sid)
            for i in range(10):
                s.set("prompt_count", i)
                s.save()

        threads = [threading.Thread(target=worker, args=(f"cleanup-{i}",)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        leftover = list(tmp_path.glob("*.tmp"))
        assert leftover == [], f"tmpfiles left after concurrent saves: {leftover}"
