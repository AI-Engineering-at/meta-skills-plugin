"""Tests for hooks/exploration-first.py — Write-Before-Read detection + write-time QA.

Covers:
- Read tools (Read/Grep/Glob/Agent) increment read_count
- Transition to implementation phase after MIN_READS + 2 reads
- Write tools (Write/Edit) trigger warnings when read_count < MIN_READS
- Only warns once per session (warned flag)
- Write-time quality checks: Python print(), SKILL.md frontmatter, rules title
- Edge: malformed stdin, empty stdin, missing tool_name, implementation-phase skip
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_FILE = REPO_ROOT / "hooks" / "exploration-first.py"


def _run(payload: dict, tmp_path: Path):
    env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
    return subprocess.run(
        [sys.executable, str(HOOK_FILE)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )


def _state(tmp_path: Path, sid: str) -> dict:
    p = tmp_path / f".meta-state-{sid}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


class TestReadTracking:
    @pytest.mark.parametrize("tool", ["Read", "Grep", "Glob", "Agent"])
    def test_read_tool_increments_count(self, tool, tmp_path):
        r = _run({"session_id": "s", "tool_name": tool}, tmp_path)
        assert r.returncode == 0
        assert _state(tmp_path, "s")["exploration_first"]["read_count"] == 1

    def test_five_reads_transition_to_implementation(self, tmp_path):
        sid = "s-trans"
        for _ in range(5):
            _run({"session_id": sid, "tool_name": "Read"}, tmp_path)
        assert _state(tmp_path, sid)["exploration_first"]["phase"] == "implementation"

    def test_fewer_reads_stay_in_exploration(self, tmp_path):
        sid = "s-explore"
        for _ in range(2):
            _run({"session_id": sid, "tool_name": "Read"}, tmp_path)
        assert _state(tmp_path, sid)["exploration_first"]["phase"] == "exploration"


class TestWriteWarning:
    def test_write_without_reads_warns(self, tmp_path):
        r = _run({
            "session_id": "s-warn",
            "tool_name": "Write",
            "tool_input": {"file_path": "foo.txt", "content": "hello"},
        }, tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip(), "expected warning stdout"
        ctx = json.loads(r.stdout.strip())["additionalContext"]
        assert "WRITING BEFORE READING" in ctx

    def test_write_after_enough_reads_no_warn(self, tmp_path):
        sid = "s-goodflow"
        for _ in range(3):
            _run({"session_id": sid, "tool_name": "Read"}, tmp_path)
        r = _run({
            "session_id": sid,
            "tool_name": "Write",
            "tool_input": {"file_path": "foo.txt", "content": "hello"},
        }, tmp_path)
        # No WRITING-BEFORE-READING warning (but may have other checks that don't fire)
        out = r.stdout.strip()
        if out:
            ctx = json.loads(out)["additionalContext"]
            assert "WRITING BEFORE READING" not in ctx

    def test_warn_only_once_per_session(self, tmp_path):
        sid = "s-once"
        _run({
            "session_id": sid, "tool_name": "Write",
            "tool_input": {"file_path": "a.txt", "content": "x"},
        }, tmp_path)
        r2 = _run({
            "session_id": sid, "tool_name": "Write",
            "tool_input": {"file_path": "b.txt", "content": "y"},
        }, tmp_path)
        # Second write: warned flag already True → no WRITING-BEFORE-READING warn
        out = r2.stdout.strip()
        if out:
            assert "WRITING BEFORE READING" not in json.loads(out)["additionalContext"]


class TestWriteTimeQualityChecks:
    def test_python_print_flagged(self, tmp_path):
        """P5 QA: print() in .py files (non-test) → warning."""
        sid = "s-pyprint"
        # First make enough reads so WRITING-BEFORE-READING doesn't also fire
        for _ in range(3):
            _run({"session_id": sid, "tool_name": "Read"}, tmp_path)
        r = _run({
            "session_id": sid,
            "tool_name": "Write",
            "tool_input": {
                "file_path": "module.py",
                "content": "def foo():\n    print('debug')",
            },
        }, tmp_path)
        ctx = json.loads(r.stdout.strip())["additionalContext"]
        assert "print()" in ctx
        assert "structured logging" in ctx

    def test_python_print_in_test_file_not_flagged(self, tmp_path):
        sid = "s-pytest-ok"
        for _ in range(3):
            _run({"session_id": sid, "tool_name": "Read"}, tmp_path)
        r = _run({
            "session_id": sid,
            "tool_name": "Write",
            "tool_input": {"file_path": "test_x.py", "content": "def test_foo(): print('ok')"},
        }, tmp_path)
        # May or may not emit output; if it does, no print() warning
        out = r.stdout.strip()
        if out:
            ctx = json.loads(out)["additionalContext"]
            assert "print()" not in ctx

    def test_skill_md_missing_version_flagged(self, tmp_path):
        sid = "s-skill"
        for _ in range(3):
            _run({"session_id": sid, "tool_name": "Read"}, tmp_path)
        r = _run({
            "session_id": sid,
            "tool_name": "Write",
            "tool_input": {
                "file_path": "skills/foo/SKILL.md",
                "content": "---\nname: foo\n---\nbody\n",
            },
        }, tmp_path)
        ctx = json.loads(r.stdout.strip())["additionalContext"]
        assert "version:" in ctx
        assert "token-budget:" in ctx

    def test_skill_md_with_frontmatter_fields_not_flagged(self, tmp_path):
        sid = "s-skill-ok"
        for _ in range(3):
            _run({"session_id": sid, "tool_name": "Read"}, tmp_path)
        r = _run({
            "session_id": sid,
            "tool_name": "Write",
            "tool_input": {
                "file_path": "skills/foo/SKILL.md",
                "content": "---\nname: foo\nversion: 1.0\ntoken-budget: 500\n---\nbody\n",
            },
        }, tmp_path)
        out = r.stdout.strip()
        if out:
            ctx = json.loads(out)["additionalContext"]
            assert "version:" not in ctx
            assert "token-budget:" not in ctx

    def test_rules_md_no_title_flagged(self, tmp_path):
        sid = "s-rules"
        for _ in range(3):
            _run({"session_id": sid, "tool_name": "Read"}, tmp_path)
        r = _run({
            "session_id": sid,
            "tool_name": "Write",
            "tool_input": {
                "file_path": ".claude/rules/25-new.md",
                "content": "body without title",
            },
        }, tmp_path)
        ctx = json.loads(r.stdout.strip())["additionalContext"]
        assert "No title" in ctx


class TestImplementationPhaseSkip:
    def test_implementation_phase_exits_immediately(self, tmp_path):
        sid = "s-impl"
        # Seed state with phase=implementation
        (tmp_path / f".meta-state-{sid}.json").write_text(
            json.dumps({
                "session_id": sid,
                "exploration_first": {
                    "read_count": 10, "write_count": 0,
                    "phase": "implementation", "warned": False,
                },
            }),
            encoding="utf-8",
        )
        r = _run({
            "session_id": sid, "tool_name": "Write",
            "tool_input": {"file_path": "foo.py", "content": "print('x')"},
        }, tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip() == "", "implementation phase must skip all checks"


class TestEdgeCases:
    def test_malformed_stdin_exits_0(self, tmp_path):
        r = _run_raw("{not valid", tmp_path)
        assert r.returncode == 0

    def test_empty_stdin_exits_0(self, tmp_path):
        r = _run_raw("", tmp_path)
        assert r.returncode == 0

    def test_missing_tool_name_exits_0(self, tmp_path):
        r = _run({"session_id": "s"}, tmp_path)  # no tool_name
        assert r.returncode == 0


def _run_raw(raw: str, tmp_path: Path):
    env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
    return subprocess.run(
        [sys.executable, str(HOOK_FILE)],
        input=raw, capture_output=True, text=True, timeout=10, env=env,
    )
