"""Tests for hooks/token-audit.py — PostToolUse audit logger.

Covers:
- estimate_tokens heuristic (len//4 lower bound, max(1, ...))
- classify_bash_command for 10+ categories
- Bash tool records command, category, output_lines
- Read tool records file path
- Grep/Glob record pattern
- Agent tool records subagent_type
- JSONL append: one record per call, appends across calls
- Log rotation at 10MB
- Malformed / empty stdin handled
- Unknown tool defaults to "unknown"
"""
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_FILE = REPO_ROOT / "hooks" / "token-audit.py"

# Import pure functions for unit tests
sys.path.insert(0, str(REPO_ROOT / "hooks"))
_spec = importlib.util.spec_from_file_location("token_audit", HOOK_FILE)
ta = importlib.util.module_from_spec(_spec)
# Isolate its module-level side-effect (mkdir PLUGIN_DATA) to a tmp path via env
_old_data = os.environ.get("CLAUDE_PLUGIN_DATA")
# Must set before exec_module because module-level code reads env:
import tempfile
_tmp_import_data = tempfile.mkdtemp()
os.environ["CLAUDE_PLUGIN_DATA"] = _tmp_import_data
sys.modules["token_audit"] = ta
_spec.loader.exec_module(ta)
if _old_data is None:
    os.environ.pop("CLAUDE_PLUGIN_DATA", None)
else:
    os.environ["CLAUDE_PLUGIN_DATA"] = _old_data


def _run(payload: dict, tmp_path: Path):
    env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
    return subprocess.run(
        [sys.executable, str(HOOK_FILE)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=10, env=env,
    )


def _read_audit(tmp_path: Path) -> list:
    """Read the JSONL audit log as list of records."""
    p = tmp_path / "token-audit.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


class TestEstimateTokens:
    @pytest.mark.parametrize("text,expected_min", [
        ("", 0),
        ("a", 1),        # max(1, 1//4) = 1
        ("aaaa", 1),     # 4//4 = 1
        ("a" * 100, 25), # 100//4 = 25
        ("a" * 400, 100),
    ])
    def test_estimate_tokens(self, text, expected_min):
        assert ta.estimate_tokens(text) == expected_min


class TestClassifyBashCommand:
    @pytest.mark.parametrize("cmd,expected", [
        ("git status", "git"),
        ("gh pr create", "git"),
        ("docker build .", "docker"),
        ("docker-compose up", "docker"),
        ("pytest tests/", "test"),
        ("python -m pytest tests/", "test"),
        ("npm test", "test"),
        ("ruff check .", "lint"),
        ("mypy foo.py", "lint"),
        ("ssh joe@host", "ssh"),
        ("scp file host:/", "ssh"),
        ("curl -X POST url", "http"),
        ("wget url", "http"),
        ("pip install foo", "package"),
        ("npm install", "package"),
        ("apt install foo", "package"),
        ("ls -la", "filesystem"),
        ("find . -name '*.py'", "filesystem"),
        ("cat file.txt", "read"),
        ("head -20 file", "read"),
        ("tail -f log", "read"),
        ("python script.py", "script"),
        ("node app.js", "script"),
        ("something random", "other"),
    ])
    def test_classify(self, cmd, expected):
        assert ta.classify_bash_command(cmd) == expected

    def test_case_insensitive(self):
        assert ta.classify_bash_command("GIT STATUS") == "git"


class TestAuditLogWrite:
    def test_bash_tool_records_command(self, tmp_path):
        r = _run({
            "session_id": "s1",
            "tool_name": "Bash",
            "tool_input": {"command": "git status"},
            "tool_output": "main branch clean",
        }, tmp_path)
        assert r.returncode == 0
        records = _read_audit(tmp_path)
        assert len(records) == 1
        assert records[0]["tool"] == "Bash"
        assert records[0]["command"] == "git status"
        assert records[0]["category"] == "git"
        assert records[0]["output_lines"] >= 1

    def test_read_tool_records_file_path(self, tmp_path):
        _run({
            "session_id": "s", "tool_name": "Read",
            "tool_input": {"file_path": "/long/path/to/some/file.py"},
            "tool_output": "content",
        }, tmp_path)
        records = _read_audit(tmp_path)
        assert records[0]["tool"] == "Read"
        assert records[0]["file"] == "/long/path/to/some/file.py"[-80:]

    def test_grep_tool_records_pattern(self, tmp_path):
        _run({
            "session_id": "s", "tool_name": "Grep",
            "tool_input": {"pattern": "def foo"},
            "tool_output": "",
        }, tmp_path)
        records = _read_audit(tmp_path)
        assert records[0]["pattern"] == "def foo"

    def test_agent_tool_records_subagent_type(self, tmp_path):
        _run({
            "session_id": "s", "tool_name": "Agent",
            "tool_input": {"subagent_type": "Explore"},
            "tool_output": "",
        }, tmp_path)
        records = _read_audit(tmp_path)
        assert records[0]["agent_type"] == "Explore"

    def test_multiple_calls_append(self, tmp_path):
        for i in range(3):
            _run({
                "session_id": "s", "tool_name": "Bash",
                "tool_input": {"command": f"ls {i}"},
                "tool_output": "",
            }, tmp_path)
        records = _read_audit(tmp_path)
        assert len(records) == 3

    def test_token_estimates_present(self, tmp_path):
        _run({
            "session_id": "s", "tool_name": "Bash",
            "tool_input": {"command": "a" * 40},
            "tool_output": "b" * 80,
        }, tmp_path)
        r = _read_audit(tmp_path)[0]
        assert r["input_tokens"] > 0
        assert r["output_tokens"] > 0
        assert r["total_tokens"] == r["input_tokens"] + r["output_tokens"]


class TestLogRotation:
    def test_rotation_at_10mb(self, tmp_path):
        """Seed an 11MB audit file; next hook call rotates."""
        audit = tmp_path / "token-audit.jsonl"
        audit.write_text("x" * (11 * 1024 * 1024), encoding="utf-8")
        _run({
            "session_id": "s", "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "tool_output": "",
        }, tmp_path)
        # After rotation, a timestamped rotated file should exist
        rotated = list(tmp_path.glob("token-audit.*.jsonl"))
        assert len(rotated) >= 1, f"expected rotated file; got {list(tmp_path.iterdir())}"


class TestEdgeCases:
    def test_malformed_stdin(self, tmp_path):
        env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
        r = subprocess.run(
            [sys.executable, str(HOOK_FILE)],
            input="{not json", capture_output=True, text=True, timeout=10, env=env,
        )
        assert r.returncode == 0

    def test_empty_stdin(self, tmp_path):
        env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
        r = subprocess.run(
            [sys.executable, str(HOOK_FILE)],
            input="", capture_output=True, text=True, timeout=10, env=env,
        )
        assert r.returncode == 0

    def test_unknown_tool_logged(self, tmp_path):
        _run({"session_id": "s", "tool_input": {}, "tool_output": ""}, tmp_path)
        records = _read_audit(tmp_path)
        assert records[0]["tool"] == "unknown"
