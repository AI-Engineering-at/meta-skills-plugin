"""Tests for hooks/lib/state.py — SessionState unified state manager.

Covers:
- Roundtrip (save/load)
- Defaults merging for missing namespaces
- prompt_count + is_initialized properties
- Corruption recovery (malformed JSON)
- Missing file handling
- cleanup_stale (keep N most recent)
- cleanup_legacy (remove old scattered state files)
- _deep_copy semantics (no shared references)
- Unknown namespace returns None
"""
import json
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "hooks"))


@pytest.fixture
def state_env(monkeypatch, tmp_path):
    """Isolate each test with its own state dir."""
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
    # Re-import to pick up env change
    import importlib

    from lib import state as state_mod
    importlib.reload(state_mod)
    return state_mod, tmp_path


class TestRoundtrip:
    def test_save_load_preserves_custom_values(self, state_env):
        state_mod, tmp_path = state_env
        s = state_mod.SessionState("sess-1")
        pc = s.get("prompt_count")
        s.set("prompt_count", 42)
        qg = s.get("quality_gate")
        qg["consecutive_failures"] = 7
        s.set("quality_gate", qg)
        s.save()

        s2 = state_mod.SessionState("sess-1")
        assert s2.get("prompt_count") == 42
        assert s2.get("quality_gate")["consecutive_failures"] == 7

    def test_file_path_per_session(self, state_env):
        state_mod, tmp_path = state_env
        s1 = state_mod.SessionState("sess-a")
        s2 = state_mod.SessionState("sess-b")
        assert s1.path != s2.path
        assert s1.path.name == ".meta-state-sess-a.json"
        assert s2.path.name == ".meta-state-sess-b.json"

    def test_save_creates_file_on_disk(self, state_env):
        state_mod, tmp_path = state_env
        s = state_mod.SessionState("sess-disk")
        s.save()
        assert s.path.exists()
        data = json.loads(s.path.read_text(encoding="utf-8"))
        assert data["session_id"] == "sess-disk"


class TestDefaultsMerging:
    def test_missing_namespace_gets_default(self, state_env):
        state_mod, _ = state_env
        s = state_mod.SessionState("defaults")
        qg = s.get("quality_gate")
        assert qg == state_mod.DEFAULTS["quality_gate"]

    def test_unknown_namespace_returns_none(self, state_env):
        state_mod, _ = state_env
        s = state_mod.SessionState("unknown-ns")
        assert s.get("not_a_real_namespace") is None

    def test_partial_file_merges_missing_keys(self, state_env):
        state_mod, tmp_path = state_env
        # Write a partial state file (only has session_id + prompt_count)
        sess_file = tmp_path / ".meta-state-partial.json"
        sess_file.write_text(json.dumps({"session_id": "partial", "prompt_count": 5}), encoding="utf-8")

        s = state_mod.SessionState("partial")
        assert s.get("prompt_count") == 5
        # Missing namespaces get defaults
        assert s.get("quality_gate") == state_mod.DEFAULTS["quality_gate"]
        assert s.get("scope_tracker") == state_mod.DEFAULTS["scope_tracker"]

    def test_defaults_are_deep_copied_not_shared(self, state_env):
        state_mod, _ = state_env
        s1 = state_mod.SessionState("deep-1")
        s2 = state_mod.SessionState("deep-2")
        qg1 = s1.get("quality_gate")
        qg1["consecutive_failures"] = 999
        # s2's default must be untouched
        assert s2.get("quality_gate")["consecutive_failures"] == 0


class TestPromptCountProperty:
    def test_prompt_count_default_0(self, state_env):
        state_mod, _ = state_env
        s = state_mod.SessionState("pc-default")
        assert s.prompt_count == 0

    def test_prompt_count_setter_and_getter(self, state_env):
        state_mod, _ = state_env
        s = state_mod.SessionState("pc-set")
        s.prompt_count = 13
        assert s.prompt_count == 13

    def test_prompt_count_persists(self, state_env):
        state_mod, _ = state_env
        s = state_mod.SessionState("pc-persist")
        s.prompt_count = 99
        s.save()

        s2 = state_mod.SessionState("pc-persist")
        assert s2.prompt_count == 99


class TestIsInitialized:
    def test_default_false(self, state_env):
        state_mod, _ = state_env
        s = state_mod.SessionState("init-default")
        assert s.is_initialized is False

    def test_setter_and_persist(self, state_env):
        state_mod, _ = state_env
        s = state_mod.SessionState("init-set")
        s.is_initialized = True
        s.save()

        s2 = state_mod.SessionState("init-set")
        assert s2.is_initialized is True


class TestCorruptionRecovery:
    def test_malformed_json_returns_defaults(self, state_env):
        state_mod, tmp_path = state_env
        sess_file = tmp_path / ".meta-state-corrupt.json"
        sess_file.write_text("{not valid json", encoding="utf-8")

        s = state_mod.SessionState("corrupt")
        # Falls back to fresh state with session_id + defaults
        assert s.session_id == "corrupt"
        assert s.get("prompt_count") == 0
        assert s.get("quality_gate") == state_mod.DEFAULTS["quality_gate"]

    def test_missing_file_returns_defaults(self, state_env):
        state_mod, _ = state_env
        s = state_mod.SessionState("never-existed")
        assert s.session_id == "never-existed"
        assert s.get("correction_detect")["correction_count"] == 0

    def test_save_when_dir_missing_creates_dir(self, state_env):
        state_mod, tmp_path = state_env
        # Remove the state dir
        import shutil
        shutil.rmtree(tmp_path, ignore_errors=True)
        s = state_mod.SessionState("recreate-dir")
        # Directory is re-created in __init__ — save() must work
        s.save()
        assert s.path.exists()


class TestToDict:
    def test_returns_deep_copy(self, state_env):
        state_mod, _ = state_env
        s = state_mod.SessionState("tdict")
        d = s.to_dict()
        # Mutating the returned dict must not touch internal state
        d["prompt_count"] = 9999
        assert s.get("prompt_count") == 0

    def test_contains_session_id(self, state_env):
        state_mod, _ = state_env
        s = state_mod.SessionState("tdict-id")
        assert s.to_dict()["session_id"] == "tdict-id"


class TestCleanupStale:
    def test_keeps_most_recent_n(self, state_env):
        state_mod, tmp_path = state_env
        # Create 7 files with staggered mtime
        for i in range(7):
            f = tmp_path / f".meta-state-old-{i}.json"
            f.write_text(json.dumps({"session_id": f"old-{i}"}), encoding="utf-8")
            # Space out mtimes so sort is stable
            import os as _os
            ts = time.time() - (7 - i) * 10
            _os.utime(f, (ts, ts))

        state_mod.SessionState.cleanup_stale(keep=3)
        remaining = sorted(tmp_path.glob(".meta-state-*.json"))
        assert len(remaining) == 3
        # Most recent 3 should remain (old-4, old-5, old-6)
        names = {f.name for f in remaining}
        assert ".meta-state-old-6.json" in names
        assert ".meta-state-old-5.json" in names
        assert ".meta-state-old-4.json" in names

    def test_cleanup_stale_no_files(self, state_env):
        state_mod, _ = state_env
        # No files present → must not raise
        state_mod.SessionState.cleanup_stale(keep=5)

    def test_cleanup_stale_fewer_than_keep(self, state_env):
        state_mod, tmp_path = state_env
        for i in range(2):
            (tmp_path / f".meta-state-few-{i}.json").write_text("{}", encoding="utf-8")
        state_mod.SessionState.cleanup_stale(keep=5)
        # All 2 files must still exist
        assert len(list(tmp_path.glob(".meta-state-*.json"))) == 2


class TestCleanupLegacy:
    def test_removes_all_legacy_patterns(self, state_env):
        state_mod, tmp_path = state_env
        legacy_files = [
            ".session-init-abc",
            ".prompt-counter-xyz",
            ".quality-gate-123.json",
            ".scope-tracker-456.json",
            ".approach-guard-789.json",
            ".exploration-first-abc.json",
            ".escalation-state.json",
            ".session-state-def.json",
        ]
        for name in legacy_files:
            (tmp_path / name).write_text("{}", encoding="utf-8")

        # Also create a new-pattern file that MUST survive
        keep = tmp_path / ".meta-state-survivor.json"
        keep.write_text("{}", encoding="utf-8")

        state_mod.SessionState.cleanup_legacy()

        # All legacy gone
        for name in legacy_files:
            assert not (tmp_path / name).exists(), f"not removed: {name}"
        # New-pattern survives
        assert keep.exists()

    def test_cleanup_legacy_no_files(self, state_env):
        state_mod, _ = state_env
        state_mod.SessionState.cleanup_legacy()  # must not raise
