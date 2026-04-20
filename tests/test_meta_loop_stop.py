"""Tests for hooks/meta-loop-stop.py — Stop event with objective gates.

Covers:
- find_state_file: walks up from cwd to .claude/meta-loop.local.md
- parse_state: YAML-like frontmatter → dict (strings, ints, bools, lists, inline dicts)
- parse_state returns None for missing/invalid files
- No state file → allow exit (exit 0, no output)
- Inactive state (active: false) → allow exit
- Max iterations reached → allow exit + delete state file
- All gates pass → allow exit + delete state
- Any gate fails → block + iteration++ + state updated
- session_id mismatch → allow (not our loop)
- Gate type "command": runs shell cmd, rc==0 = pass
- Gate type "eval": skipped (no eval.py in test env) — gracefully fails
"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_FILE = REPO_ROOT / "hooks" / "meta-loop-stop.py"

sys.path.insert(0, str(REPO_ROOT / "hooks"))
_spec = importlib.util.spec_from_file_location("meta_loop_stop", HOOK_FILE)
mls = importlib.util.module_from_spec(_spec)
sys.modules["meta_loop_stop"] = mls
_spec.loader.exec_module(mls)


def _run(payload: dict, tmp_path: Path, cwd: Path | None = None):
    env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
    return subprocess.run(
        [sys.executable, str(HOOK_FILE)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=60, env=env,
        cwd=str(cwd) if cwd else None,
    )


def _make_state_file(cwd: Path, active: bool = True, iteration: int = 1,
                     max_iter: int = 10, gates: list | None = None,
                     session_id: str = "") -> Path:
    """Create a .claude/meta-loop.local.md in cwd."""
    claude_dir = cwd / ".claude"
    claude_dir.mkdir(exist_ok=True)
    state_file = claude_dir / "meta-loop.local.md"

    lines = ["---"]
    lines.append(f"active: {'true' if active else 'false'}")
    lines.append(f"iteration: {iteration}")
    lines.append(f"max_iterations: {max_iter}")
    if session_id:
        lines.append(f"session_id: {session_id}")
    if gates is not None:
        lines.append("gates:")
        for g in gates:
            if isinstance(g, dict):
                lines.append(f"  - {json.dumps(g)}")
            else:
                lines.append(f"  - {g}")
    lines.append("---")
    lines.append("Continue fixing until all gates pass.")

    state_file.write_text("\n".join(lines), encoding="utf-8")
    return state_file


class TestParseState:
    def test_valid_state_parsed(self, tmp_path):
        state_file = _make_state_file(tmp_path, active=True, iteration=3, max_iter=5,
                                       gates=[{"type": "command", "cmd": "true", "name": "t1"}])
        state = mls.parse_state(state_file)
        assert state is not None
        assert state.get("active") is True
        assert state.get("iteration") == 3
        assert state.get("max_iterations") == 5
        assert len(state["gates"]) == 1
        assert state["gates"][0]["name"] == "t1"

    def test_bool_parsing(self, tmp_path):
        f = _make_state_file(tmp_path, active=False)
        assert mls.parse_state(f)["active"] is False

    def test_int_parsing(self, tmp_path):
        f = _make_state_file(tmp_path, iteration=42)
        assert mls.parse_state(f)["iteration"] == 42

    def test_string_values_unquoted(self, tmp_path):
        f = tmp_path / "state.md"
        f.write_text("---\nname: 'my value'\nother: \"q val\"\n---\nbody\n", encoding="utf-8")
        s = mls.parse_state(f)
        assert s["name"] == "my value"
        assert s["other"] == "q val"

    def test_missing_frontmatter_delimiter_returns_none(self, tmp_path):
        f = tmp_path / "bad.md"
        f.write_text("no frontmatter here", encoding="utf-8")
        assert mls.parse_state(f) is None

    def test_missing_file_returns_none(self, tmp_path):
        assert mls.parse_state(tmp_path / "nonexistent.md") is None


class TestFindStateFile:
    def test_find_in_cwd(self, tmp_path, monkeypatch):
        _make_state_file(tmp_path)
        monkeypatch.chdir(tmp_path)
        found = mls.find_state_file()
        assert found is not None
        assert found.name == "meta-loop.local.md"

    def test_find_in_parent(self, tmp_path, monkeypatch):
        _make_state_file(tmp_path)
        sub = tmp_path / "src" / "deep"
        sub.mkdir(parents=True)
        monkeypatch.chdir(sub)
        assert mls.find_state_file() is not None

    def test_no_state_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert mls.find_state_file() is None


class TestHookBehavior:
    def test_no_state_file_allows_exit(self, tmp_path):
        """No meta-loop.local.md anywhere → exit 0 silently."""
        r = _run({"session_id": "s"}, tmp_path, cwd=tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip() == ""

    def test_inactive_state_allows_exit(self, tmp_path):
        _make_state_file(tmp_path, active=False)
        r = _run({"session_id": "s"}, tmp_path, cwd=tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip() == ""

    def test_max_iterations_reached_allows_exit(self, tmp_path):
        state_file = _make_state_file(tmp_path, iteration=15, max_iter=10,
                                       gates=[{"type": "command", "cmd": "false", "name": "g"}])
        r = _run({"session_id": "s"}, tmp_path, cwd=tmp_path)
        assert r.returncode == 0
        # State file should be deleted
        assert not state_file.exists()

    def test_no_gates_allows_exit(self, tmp_path):
        state_file = _make_state_file(tmp_path, gates=[])
        r = _run({"session_id": "s"}, tmp_path, cwd=tmp_path)
        assert r.returncode == 0
        assert not state_file.exists()

    def test_all_gates_pass_allows_exit(self, tmp_path):
        # Gate that definitely passes: printing hello
        state_file = _make_state_file(tmp_path, gates=[
            {"type": "command", "cmd": "echo hello", "name": "echo-gate"},
        ])
        r = _run({"session_id": "s"}, tmp_path, cwd=tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip() == "", f"expected no decision output; got {r.stdout!r}"
        # State cleaned up
        assert not state_file.exists()

    def test_failing_gate_blocks_and_iterates(self, tmp_path):
        """A gate that fails (rc != 0) blocks exit + increments iteration."""
        state_file = _make_state_file(tmp_path, iteration=1, max_iter=5, gates=[
            {"type": "command", "cmd": "exit 1", "name": "failing-gate"},
        ])
        r = _run({"session_id": "s"}, tmp_path, cwd=tmp_path)
        assert r.returncode == 0
        # Should emit decision:block
        out = r.stdout.strip()
        assert out, "expected decision output"
        payload = json.loads(out)
        assert payload.get("decision") == "block"
        assert "Iteration" in payload.get("systemMessage", "")
        assert "failing-gate=FAIL" in payload.get("systemMessage", "")
        # State file should be updated to iteration=2 and still exist
        assert state_file.exists()
        updated = state_file.read_text(encoding="utf-8")
        assert "iteration: 2" in updated

    def test_session_mismatch_allows_exit(self, tmp_path):
        _make_state_file(tmp_path, session_id="other-session")
        r = _run({"session_id": "current-session"}, tmp_path, cwd=tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip() == ""


class TestRunGate:
    def test_command_gate_passes(self, tmp_path):
        result = mls.run_gate(
            {"type": "command", "cmd": "echo ok", "name": "t"},
            str(tmp_path),
        )
        assert result["passed"] is True
        assert result["name"] == "t"

    def test_command_gate_fails(self, tmp_path):
        result = mls.run_gate(
            {"type": "command", "cmd": "exit 1", "name": "t"},
            str(tmp_path),
        )
        assert result["passed"] is False

    def test_no_command_returns_fail(self, tmp_path):
        result = mls.run_gate({"type": "command", "name": "t"}, str(tmp_path))
        assert result["passed"] is False
        assert "No command" in result["output"]

    def test_eval_without_plugin_root_fails(self, tmp_path, monkeypatch):
        """PLUGIN_ROOT is captured at module-import time. Patch it directly."""
        monkeypatch.setattr(mls, "PLUGIN_ROOT", str(tmp_path))  # no eval.py there
        result = mls.run_gate({"type": "eval", "name": "ev", "min_score": 70}, str(tmp_path))
        assert result["passed"] is False
        assert "eval.py not found" in result["output"]
