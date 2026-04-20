"""Tests for hooks/approach-guard.py — Bash PreToolUse model/risk detection.

Covers:
- SAFE_PATTERNS short-circuit before anything else
- MODEL_SWITCH_PATTERNS detect ollama/curl/--model/vllm
- RISKY_PATTERNS detect docker rm/rm -rf /, git push --force, reset --hard
- Scope reminder appears for first 2 bash commands (unless scope_confirmed)
- No command → exits 0 silently
- Malformed / empty stdin handled
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_FILE = REPO_ROOT / "hooks" / "approach-guard.py"


def _run(payload: dict, tmp_path: Path):
    env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
    return subprocess.run(
        [sys.executable, str(HOOK_FILE)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=10, env=env,
    )


def _ctx(out: str) -> str:
    if not out.strip():
        return ""
    return json.loads(out.strip()).get("additionalContext", "")


def _bash(command: str, tmp_path: Path, sid: str = "s", scope_confirmed: bool = True):
    """Helper: invoke with scope_confirmed seeded (avoid scope reminder)."""
    if scope_confirmed:
        (tmp_path / f".meta-state-{sid}.json").write_text(
            json.dumps({
                "session_id": sid,
                "approach_guard": {
                    "bash_count": 5,  # >2 skips reminder
                    "scope_confirmed": True,
                },
            }),
            encoding="utf-8",
        )
    return _run({
        "session_id": sid,
        "tool_input": {"command": command},
    }, tmp_path)


class TestSafePatterns:
    @pytest.mark.parametrize("cmd", [
        "ollama list",
        "ollama ps",
        "ollama show gemma4",
        "ollama tags",
        "curl http://host/api/tags",
        "curl http://host/api/ps",
        "curl http://host/health",
        "python --version",
    ])
    def test_safe_commands_no_warning(self, cmd, tmp_path):
        r = _bash(cmd, tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip() == "", f"expected no warning for safe cmd {cmd!r}"


class TestModelSwitchDetection:
    @pytest.mark.parametrize("cmd", [
        "ollama run phi4-mini:3.8b",
        "ollama run qwen3:8b",
        "curl https://api.openai.com/v1/chat/completions",
        "curl https://api.anthropic.com/v1/messages",
        "curl https://api.together.com/v1/completions",
        "curl https://api.groq.com/v1/chat",
        "python scripts/foo.py --model claude-3",
        "llama-cli --model ./weights.gguf serve 8000",
        "vllm serve meta-llama/Llama-3-8B",
    ])
    def test_model_switch_detected(self, cmd, tmp_path):
        r = _bash(cmd, tmp_path)
        ctx = _ctx(r.stdout)
        assert "MODEL/APPROACH SWITCH DETECTED" in ctx, f"missed switch for {cmd!r}"
        assert "Rule: NEVER switch model" in ctx


class TestRiskyPatterns:
    @pytest.mark.parametrize("cmd", [
        "docker rm container-xyz",
        "docker service rm ai-stack_voice",
        "docker service remove ai-stack_voice",
        "docker prune",
        "rm -rf /",
        "rm -r /",
        "rm -rf /var",
        "git push --force origin main",
        "git reset --hard HEAD~3",
    ])
    def test_risky_detected(self, cmd, tmp_path):
        r = _bash(cmd, tmp_path)
        ctx = _ctx(r.stdout)
        assert "RISKY ACTION DETECTED" in ctx or "MODEL/APPROACH SWITCH" in ctx, (
            f"expected risky warning for {cmd!r}; got {ctx!r}"
        )


class TestScopeReminder:
    def test_scope_reminder_on_first_bash(self, tmp_path):
        """No seed — first bash_count=1, no scope_confirmed → reminder fires."""
        r = _run({
            "session_id": "s-scope", "tool_input": {"command": "ls -la"},
        }, tmp_path)
        ctx = _ctx(r.stdout)
        assert "scope contract" in ctx.lower()

    def test_scope_reminder_skipped_after_3_bashes(self, tmp_path):
        sid = "s-after3"
        # Run 3 commands to push bash_count past 2
        for _ in range(3):
            _run({"session_id": sid, "tool_input": {"command": "ls"}}, tmp_path)
        # 4th command: no reminder
        r = _run({"session_id": sid, "tool_input": {"command": "pwd"}}, tmp_path)
        ctx = _ctx(r.stdout)
        assert "scope contract" not in ctx.lower()

    def test_scope_reminder_skipped_when_confirmed(self, tmp_path):
        sid = "s-confirmed"
        (tmp_path / f".meta-state-{sid}.json").write_text(
            json.dumps({
                "session_id": sid,
                "approach_guard": {"bash_count": 0, "scope_confirmed": True},
            }),
            encoding="utf-8",
        )
        r = _run({"session_id": sid, "tool_input": {"command": "ls"}}, tmp_path)
        ctx = _ctx(r.stdout)
        assert "scope contract" not in ctx.lower()


class TestEdgeCases:
    def test_no_command_exits_0(self, tmp_path):
        r = _run({"session_id": "s", "tool_input": {}}, tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip() == ""

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

    def test_bash_count_increments(self, tmp_path):
        sid = "s-count"
        for _ in range(3):
            _run({"session_id": sid, "tool_input": {"command": "ls"}}, tmp_path)
        state = json.loads(
            (tmp_path / f".meta-state-{sid}.json").read_text(encoding="utf-8")
        )
        assert state["approach_guard"]["bash_count"] == 3
