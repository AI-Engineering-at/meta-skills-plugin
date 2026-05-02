"""Tests for hooks/lib/hook_wrapper.py — safe_hook decorator + error logging.

Covers:
- safe_hook exit-code guarantee (always 0, even on exceptions)
- Dict return → JSON stdout
- None return → silent exit
- SystemExit passthrough
- Log rotation at MAX_LOG_SIZE
- Error log format (timestamp, hook name, traceback)
- get_recent_errors parsing
- Integration: subprocess invocation of a real wrapped hook
"""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_LIB = REPO_ROOT / "hooks" / "lib"
sys.path.insert(0, str(REPO_ROOT / "hooks"))

from lib import hook_wrapper  # noqa: E402


class TestSafeHookDecorator:
    def test_returns_none_exits_0(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        # Re-import to pick up the new LOG_DIR
        import importlib

        importlib.reload(hook_wrapper)

        @hook_wrapper.safe_hook("test_none")
        def h():
            return None

        with pytest.raises(SystemExit) as exc:
            h()
        assert exc.value.code == 0

    def test_returns_dict_prints_json_exits_0(self, capsys, monkeypatch, tmp_path):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        import importlib

        importlib.reload(hook_wrapper)

        @hook_wrapper.safe_hook("test_dict")
        def h():
            return {"additionalContext": "hello"}

        with pytest.raises(SystemExit) as exc:
            h()
        assert exc.value.code == 0
        out = capsys.readouterr().out.strip()
        assert json.loads(out) == {"additionalContext": "hello"}

    def test_exception_caught_exits_0(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        import importlib

        importlib.reload(hook_wrapper)

        @hook_wrapper.safe_hook("test_boom")
        def h():
            raise RuntimeError("boom")

        with pytest.raises(SystemExit) as exc:
            h()
        assert exc.value.code == 0  # never block Claude

    def test_exception_writes_log(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        import importlib

        importlib.reload(hook_wrapper)

        @hook_wrapper.safe_hook("test_logged")
        def h():
            raise ValueError("expected-error-marker")

        with pytest.raises(SystemExit):
            h()

        log_file = tmp_path / "hook-errors.log"
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "test_logged" in content
        assert "ValueError" in content
        assert "expected-error-marker" in content

    def test_systemexit_passthrough(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        import importlib

        importlib.reload(hook_wrapper)

        @hook_wrapper.safe_hook("test_sysexit")
        def h():
            sys.exit(42)

        with pytest.raises(SystemExit) as exc:
            h()
        assert exc.value.code == 42  # own code preserved

    def test_non_dict_return_does_not_print(self, capsys, monkeypatch, tmp_path):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        import importlib

        importlib.reload(hook_wrapper)

        @hook_wrapper.safe_hook("test_str")
        def h():
            return "this is a string not a dict"

        with pytest.raises(SystemExit):
            h()
        assert capsys.readouterr().out == ""

    def test_decorator_preserves_function_name(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        import importlib

        importlib.reload(hook_wrapper)

        @hook_wrapper.safe_hook("test_name")
        def my_hook():
            return None

        assert my_hook.__name__ == "my_hook"


class TestLogRotation:
    def test_rotates_when_over_size(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        import importlib

        importlib.reload(hook_wrapper)

        log_file = tmp_path / "hook-errors.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        # Write > 512KB
        log_file.write_text("x" * (hook_wrapper.MAX_LOG_SIZE + 100), encoding="utf-8")

        hook_wrapper._rotate_log()

        backup = log_file.with_suffix(".log.1")
        assert backup.exists()
        assert not log_file.exists() or log_file.stat().st_size == 0

    def test_no_rotation_when_under_size(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        import importlib

        importlib.reload(hook_wrapper)

        log_file = tmp_path / "hook-errors.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text("small", encoding="utf-8")

        hook_wrapper._rotate_log()

        assert log_file.exists()
        assert not log_file.with_suffix(".log.1").exists()

    def test_rotate_overwrites_existing_backup(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        import importlib

        importlib.reload(hook_wrapper)

        log_file = tmp_path / "hook-errors.log"
        backup = log_file.with_suffix(".log.1")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        backup.write_text("old-backup-content", encoding="utf-8")
        log_file.write_text("x" * (hook_wrapper.MAX_LOG_SIZE + 100), encoding="utf-8")

        hook_wrapper._rotate_log()

        assert backup.exists()
        # Old backup replaced by recent log content
        assert "old-backup-content" not in backup.read_text(encoding="utf-8")

    def test_rotate_survives_missing_file(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        import importlib

        importlib.reload(hook_wrapper)

        # No log_file created
        hook_wrapper._rotate_log()  # must not raise


class TestLogError:
    def test_log_creates_dir(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path / "deep" / "nested"))
        import importlib

        importlib.reload(hook_wrapper)

        try:
            raise RuntimeError("x")
        except RuntimeError as e:
            hook_wrapper._log_error("h1", e, "ctx")

        assert (tmp_path / "deep" / "nested" / "hook-errors.log").exists()

    def test_log_format_has_timestamp_hook_traceback(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        import importlib

        importlib.reload(hook_wrapper)

        try:
            raise ValueError("UNIQUE-MSG")
        except ValueError as e:
            hook_wrapper._log_error("my_hook", e, "ctx_data=42")

        entry = (tmp_path / "hook-errors.log").read_text(encoding="utf-8")
        assert "[" in entry and "]" in entry  # timestamp bracket
        assert "HOOK=my_hook" in entry
        assert "ValueError" in entry
        assert "UNIQUE-MSG" in entry
        assert "ctx_data=42" in entry
        assert "TRACEBACK" in entry

    def test_log_error_never_raises(self, monkeypatch):
        """Even with unwritable log_dir, _log_error must silently swallow."""
        # Point at invalid path via monkeypatching module state
        monkeypatch.setattr(
            hook_wrapper,
            "LOG_DIR",
            Path("\x00invalid\x00"),
        )
        monkeypatch.setattr(
            hook_wrapper,
            "LOG_FILE",
            Path("\x00invalid\x00/hook-errors.log"),
        )
        try:
            raise RuntimeError("x")
        except RuntimeError as e:
            hook_wrapper._log_error("h", e, "ctx")  # must not raise


class TestGetRecentErrors:
    def test_no_log_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        import importlib

        importlib.reload(hook_wrapper)

        assert hook_wrapper.get_recent_errors() == []

    def test_parses_multi_line_entries(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        import importlib

        importlib.reload(hook_wrapper)

        (tmp_path / "hook-errors.log").write_text(
            "[2026-04-17 10:00:00] HOOK=a ERROR=X\n"
            "  CTX: one\n"
            "  TB: tb1\n"
            "[2026-04-17 10:01:00] HOOK=b ERROR=Y\n"
            "  CTX: two\n"
            "  TB: tb2\n",
            encoding="utf-8",
        )

        entries = hook_wrapper.get_recent_errors()
        assert len(entries) == 2
        assert "HOOK=a" in entries[0]
        assert "HOOK=b" in entries[1]

    def test_limit_respected(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        import importlib

        importlib.reload(hook_wrapper)

        lines = []
        for i in range(10):
            lines.append(f"[2026-04-17 10:{i:02d}:00] HOOK=h{i} ERROR=X")
            lines.append("  CTX: ctx")
        (tmp_path / "hook-errors.log").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

        entries = hook_wrapper.get_recent_errors(limit=3)
        assert len(entries) == 3
        assert "HOOK=h9" in entries[-1]

    def test_corrupt_log_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        import importlib

        importlib.reload(hook_wrapper)

        log_file = tmp_path / "hook-errors.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_bytes(b"\xff\xfe\x00\x00 binary gibberish")
        # Must not raise
        entries = hook_wrapper.get_recent_errors()
        assert isinstance(entries, list)


class TestIntegrationSubprocess:
    def test_safe_hook_in_subprocess_exits_0_on_exception(self, tmp_path):
        """End-to-end: run a script that uses @safe_hook and raises. Must exit 0."""
        script = tmp_path / "hook.py"
        hooks_dir = REPO_ROOT / "hooks"
        script.write_text(
            textwrap.dedent(f"""
            import sys
            sys.path.insert(0, r"{hooks_dir}")
            from lib.hook_wrapper import safe_hook

            @safe_hook("integration_test")
            def main():
                raise RuntimeError("integration-boom")

            main()
        """),
            encoding="utf-8",
        )

        env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
        r = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        # Log should have the error
        log = tmp_path / "hook-errors.log"
        assert log.exists()
        assert "integration-boom" in log.read_text(encoding="utf-8")

    def test_safe_hook_dict_return_prints_json(self, tmp_path):
        script = tmp_path / "hook.py"
        hooks_dir = REPO_ROOT / "hooks"
        script.write_text(
            textwrap.dedent(f"""
            import sys
            sys.path.insert(0, r"{hooks_dir}")
            from lib.hook_wrapper import safe_hook

            @safe_hook("integration_json")
            def main():
                return {{"systemMessage": "ok"}}

            main()
        """),
            encoding="utf-8",
        )

        env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
        r = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert r.returncode == 0
        assert json.loads(r.stdout.strip()) == {"systemMessage": "ok"}
