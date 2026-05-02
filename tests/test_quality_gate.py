"""Tests for hooks/quality-gate.py — PostToolUse test/lint/commit/push gate.

Covers:
- classify_command: test/lint/build/commit/push/other
- detect_failure: true failures, false-positive suppression, line-by-line
- Test/lint/build failure increments consecutive_failures + emits warning
- Success resets counter + tracks last_test/lint_result
- Systematic-debugging suggestion at CONSECUTIVE_FAILURES_WARN (default 3)
- Commit gate: warns if lint/test not PASS
- Commit gate: enforces type(scope): description format (Rule 17)
- Push gate: local lint/test status + CI check + post-push reminder
- Edge: empty command, malformed stdin
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_FILE = REPO_ROOT / "hooks" / "quality-gate.py"

# Import pure functions
sys.path.insert(0, str(REPO_ROOT / "hooks"))
_spec = importlib.util.spec_from_file_location("quality_gate", HOOK_FILE)
qg = importlib.util.module_from_spec(_spec)
os.environ.setdefault("CLAUDE_PLUGIN_DATA", tempfile.mkdtemp())
sys.modules["quality_gate"] = qg
_spec.loader.exec_module(qg)


def _run(payload: dict, tmp_path: Path, extra_env: dict | None = None):
    env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
    env["PATH"] = tempfile.gettempdir()  # no gh binary → skip CI check
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(HOOK_FILE)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )


def _ctx(out: str) -> str:
    return json.loads(out.strip()).get("additionalContext", "") if out.strip() else ""


def _state(tmp_path: Path, sid: str) -> dict:
    p = tmp_path / f".meta-state-{sid}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


class TestClassifyCommand:
    @pytest.mark.parametrize(
        "cmd,expected",
        [
            ("pytest tests/", "test"),
            ("npm test", "test"),
            ("cargo test --release", "test"),
            ("go test ./...", "test"),
            ("vitest run", "test"),
            ("jest --coverage", "test"),
            ("ruff check .", "lint"),
            ("ruff format --check src/", "lint"),
            ("eslint src/", "lint"),
            ("npm run lint", "lint"),
            ("mypy module.py", "lint"),
            ("tsc --noEmit", "lint"),
            ("npm run build", "build"),
            ("cargo build --release", "build"),
            ("docker build -t x .", "build"),
            ("go build -o bin/app", "build"),
            ("git commit -m 'msg'", "commit"),
            ("git push origin main", "push"),
            ("ls -la", "other"),
            ("echo hello", "other"),
        ],
    )
    def test_classify(self, cmd, expected):
        assert qg.classify_command(cmd) == expected


class TestDetectFailure:
    def test_plain_failure(self):
        assert qg.detect_failure("FAILED: test_foo") is True
        assert qg.detect_failure("Error: build broken") is True
        assert qg.detect_failure("exit code 1") is True
        assert qg.detect_failure("5 failures found") is True

    def test_clean_output_no_failure(self):
        assert qg.detect_failure("All tests passed") is False
        assert qg.detect_failure("=== 243 passed ===") is False
        assert qg.detect_failure("") is False

    def test_false_positive_zero_errors(self):
        """Output with '0 errors' should NOT trigger failure."""
        assert qg.detect_failure("Linting complete: 0 errors") is False

    def test_false_positive_all_checks_passed(self):
        assert qg.detect_failure("All checks passed") is False

    def test_mixed_fp_and_real_failure_detected(self):
        """If output has BOTH a false-positive line AND a real failure line,
        the real failure should still register."""
        out = "Linting: 0 errors found\nTests: FAILED test_xyz"
        assert qg.detect_failure(out) is True

    def test_no_error_keyword_but_no_failure(self):
        assert qg.detect_failure("Running 10 tests...") is False


class TestFailureIncrementsCounter:
    def test_test_failure_increments(self, tmp_path):
        r = _run(
            {
                "session_id": "s1",
                "tool_input": {"command": "pytest tests/"},
                "tool_output": "FAILED: test_x",
            },
            tmp_path,
        )
        assert r.returncode == 0
        ctx = _ctx(r.stdout)
        assert "TEST FAILED" in ctx
        assert _state(tmp_path, "s1")["quality_gate"]["consecutive_failures"] == 1

    def test_lint_failure_increments(self, tmp_path):
        _run(
            {
                "session_id": "s",
                "tool_input": {"command": "ruff check ."},
                "tool_output": "5 errors found",
            },
            tmp_path,
        )
        assert _state(tmp_path, "s")["quality_gate"]["last_lint_result"] == "FAIL"

    def test_success_resets_counter(self, tmp_path):
        sid = "s-reset"
        (tmp_path / f".meta-state-{sid}.json").write_text(
            json.dumps(
                {
                    "session_id": sid,
                    "quality_gate": {
                        "consecutive_failures": 2,
                        "suggested_debugging": False,
                        "last_lint_result": "FAIL",
                        "last_test_result": "FAIL",
                    },
                }
            ),
            encoding="utf-8",
        )
        _run(
            {
                "session_id": sid,
                "tool_input": {"command": "pytest tests/"},
                "tool_output": "All tests passed",
            },
            tmp_path,
        )
        s = _state(tmp_path, sid)["quality_gate"]
        assert s["consecutive_failures"] == 0
        assert s["last_test_result"] == "PASS"


class TestSystematicDebuggingSuggestion:
    def test_suggestion_at_three_failures(self, tmp_path):
        sid = "s-debug"
        (tmp_path / f".meta-state-{sid}.json").write_text(
            json.dumps(
                {
                    "session_id": sid,
                    "quality_gate": {
                        "consecutive_failures": 2,
                        "suggested_debugging": False,
                        "last_lint_result": "FAIL",
                        "last_test_result": "NOT_RUN",
                    },
                }
            ),
            encoding="utf-8",
        )
        r = _run(
            {
                "session_id": sid,
                "tool_input": {"command": "ruff check ."},
                "tool_output": "2 errors found in 3 files",  # matches \d+ errors found pattern
            },
            tmp_path,
        )
        ctx = _ctx(r.stdout)
        assert "systematic-debugging" in ctx
        assert "3+" in ctx or "3 " in ctx

    def test_suggestion_only_once(self, tmp_path):
        sid = "s-once"
        (tmp_path / f".meta-state-{sid}.json").write_text(
            json.dumps(
                {
                    "session_id": sid,
                    "quality_gate": {
                        "consecutive_failures": 2,
                        "suggested_debugging": True,
                        "last_lint_result": "FAIL",
                    },
                }
            ),
            encoding="utf-8",
        )
        r = _run(
            {
                "session_id": sid,
                "tool_input": {"command": "ruff check ."},
                "tool_output": "errors found",
            },
            tmp_path,
        )
        ctx = _ctx(r.stdout)
        assert "systematic-debugging" not in ctx


class TestCommitGate:
    def test_commit_without_lint_pass_warns(self, tmp_path):
        r = _run(
            {
                "session_id": "s",
                "tool_input": {"command": 'git commit -m "feat(x): y"'},
                "tool_output": "",
            },
            tmp_path,
        )
        ctx = _ctx(r.stdout)
        assert "GIT COMMIT" in ctx
        assert "Lint" in ctx

    def test_commit_message_format_rule17(self, tmp_path):
        r = _run(
            {
                "session_id": "s",
                "tool_input": {"command": 'git commit -m "wrong format"'},
                "tool_output": "",
            },
            tmp_path,
        )
        ctx = _ctx(r.stdout)
        assert "type(scope): description" in ctx
        assert "Rule 17" in ctx

    def test_commit_valid_format_no_format_warning(self, tmp_path):
        sid = "s-valid"
        # Seed PASS for both lint and test → only format check matters
        (tmp_path / f".meta-state-{sid}.json").write_text(
            json.dumps(
                {
                    "session_id": sid,
                    "quality_gate": {
                        "last_lint_result": "PASS",
                        "last_test_result": "PASS",
                        "consecutive_failures": 0,
                        "suggested_debugging": False,
                    },
                }
            ),
            encoding="utf-8",
        )
        r = _run(
            {
                "session_id": sid,
                "tool_input": {"command": 'git commit -m "feat(hooks): add coverage"'},
                "tool_output": "",
            },
            tmp_path,
        )
        ctx = _ctx(r.stdout)
        assert "Rule 17" not in ctx


class TestPushGate:
    def test_push_reminds_ci_check(self, tmp_path):
        r = _run(
            {
                "session_id": "s",
                "tool_input": {"command": "git push origin main"},
                "tool_output": "",
            },
            tmp_path,
        )
        ctx = _ctx(r.stdout)
        assert "After push" in ctx
        assert "gh run list" in ctx or "meta-ci" in ctx

    def test_push_warns_lint_not_pass(self, tmp_path):
        r = _run(
            {
                "session_id": "s",
                "tool_input": {"command": "git push origin feature"},
                "tool_output": "",
            },
            tmp_path,
        )
        ctx = _ctx(r.stdout)
        assert "Pre-push" in ctx
        assert "Lint is NOT_RUN" in ctx or "Lint is" in ctx


class TestEdgeCases:
    def test_empty_command(self, tmp_path):
        r = _run({"session_id": "s", "tool_input": {}, "tool_output": ""}, tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip() == ""

    def test_other_command_skipped(self, tmp_path):
        r = _run(
            {
                "session_id": "s",
                "tool_input": {"command": "ls -la"},
                "tool_output": "",
            },
            tmp_path,
        )
        assert r.returncode == 0
        assert r.stdout.strip() == ""

    def test_malformed_stdin(self, tmp_path):
        env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
        r = subprocess.run(
            [sys.executable, str(HOOK_FILE)],
            input="{not json",
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert r.returncode == 0
