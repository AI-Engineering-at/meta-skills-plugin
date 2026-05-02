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


class TestSharedSessionLostUpdate:
    """Codex-Finding 2026-05-02 (PR #3 review): multiple hooks writing the
    SAME session_id must not lose each other's namespace updates.

    Real-world trigger: Claude Code spawns 4 UserPromptSubmit hooks in parallel
    (session-init, correction-detect, scope-tracker, false-positive-guard),
    each owning its own DEFAULTS namespace. Without lock + read-modify-write,
    last-writer wipes the others' updates.
    """

    def test_disjoint_namespace_writers_no_lost_update(self, state_env):
        state_mod, tmp_path = state_env
        sid = "shared-session"

        # Each worker owns a DIFFERENT namespace (real-world hook pattern)
        namespaces = [
            ("correction_detect", {"correction_count": 7, "last_severity": "high"}),
            ("scope_tracker", {"task_switches": 4, "warned": True}),
            ("approach_guard", {"bash_count": 11, "scope_confirmed": True}),
            ("exploration_first", {"read_count": 3, "write_count": 1}),
        ]

        barrier = threading.Barrier(len(namespaces))
        errors: list[Exception] = []

        def worker(ns: str, value: dict):
            try:
                s = state_mod.SessionState(sid)
                # Coordinate so all threads race the read-modify-write window
                barrier.wait(timeout=5)
                s.set(ns, value)
                s.save()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(ns, v)) for ns, v in namespaces]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == [], f"workers failed: {errors}"

        # All 4 namespace updates must be on disk
        f = tmp_path / f".meta-state-{sid}.json"
        data = json.loads(f.read_text(encoding="utf-8"))
        for ns, expected in namespaces:
            assert ns in data, f"missing namespace after concurrent saves: {ns}"
            for k, v in expected.items():
                assert data[ns][k] == v, f"lost update on {ns}.{k}: expected {v}, got {data[ns].get(k)}"

    def test_repeated_disjoint_writes_converge(self, state_env):
        """Stress: each thread saves N times to its own namespace."""
        state_mod, tmp_path = state_env
        sid = "stress-session"
        n_iters = 10

        errors: list[Exception] = []

        def worker(tid: int):
            try:
                s = state_mod.SessionState(sid)
                ns = ["correction_detect", "scope_tracker", "approach_guard", "exploration_first"][tid]
                # Mutable counter inside this thread's namespace
                for i in range(n_iters):
                    val = s.get(ns)
                    val["_test_counter"] = i
                    s.set(ns, val)
                    s.save()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert errors == [], f"workers failed: {errors}"

        # Final disk state must show last-iter value for all 4 namespaces
        f = tmp_path / f".meta-state-{sid}.json"
        data = json.loads(f.read_text(encoding="utf-8"))
        for ns in ["correction_detect", "scope_tracker", "approach_guard", "exploration_first"]:
            assert data[ns]["_test_counter"] == n_iters - 1, (
                f"lost final update on {ns}: got {data[ns].get('_test_counter')}"
            )


class TestLockFile:
    """File-lock pattern (Phase 1.5): a sentinel .lock file coordinates
    cross-process writers. Lock-files must be created on save(), and cleaned
    up by cleanup_stale.
    """

    def test_lock_file_created_alongside_state(self, state_env):
        state_mod, tmp_path = state_env
        s = state_mod.SessionState("lock-create")
        s.save()
        lock = tmp_path / ".meta-state-lock-create.lock"
        assert lock.exists(), f"lock file not created: {lock}"

    def test_cleanup_stale_removes_lock_files(self, state_env):
        state_mod, tmp_path = state_env
        # Create 7 (state, lock) pairs with staggered mtime
        for i in range(7):
            sf = tmp_path / f".meta-state-old-{i}.json"
            lf = tmp_path / f".meta-state-old-{i}.lock"
            sf.write_text(json.dumps({"session_id": f"old-{i}"}), encoding="utf-8")
            lf.write_text("", encoding="utf-8")
            ts = 1_700_000_000 + i  # monotone ascending
            os.utime(sf, (ts, ts))
            os.utime(lf, (ts, ts))

        state_mod.SessionState.cleanup_stale(keep=3)

        state_files = sorted(tmp_path.glob(".meta-state-*.json"))
        lock_files = sorted(tmp_path.glob(".meta-state-*.lock"))
        assert len(state_files) == 3, f"expected 3 state files, got {len(state_files)}"
        assert len(lock_files) == 3, f"expected 3 lock files, got {len(lock_files)}"
