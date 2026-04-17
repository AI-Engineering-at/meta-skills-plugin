"""Tests for scripts/hardening-run.py.

Covers the pure parsing/sanitization units:
- CheckResult dataclass
- parse_ruff / parse_validate / parse_eval / parse_pycompile / parse_json_schema
- _sanitize (PII removal for committed markdown reports)

subprocess-driven units (run_check, run_all_checks) are covered by the
end-to-end hardening-run.py --ci gate in CI and are intentionally NOT
unit-tested here (they shell out).
"""
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"

# hardening-run.py has a dash in the filename, so regular import doesn't work.
_spec = importlib.util.spec_from_file_location("hardening_run", SCRIPT_DIR / "hardening-run.py")
hr = importlib.util.module_from_spec(_spec)
sys.modules["hardening_run"] = hr
_spec.loader.exec_module(hr)


class TestCheckResult:
    def test_log_filename_from_slug(self):
        r = hr.CheckResult(name="Foo", slug="01-foo", cmd=["echo"], cwd=Path("."))
        assert r.log_filename == "01-foo.log"

    def test_defaults(self):
        r = hr.CheckResult(name="Bar", slug="bar", cmd=[], cwd=Path("."))
        assert r.returncode == 0
        assert r.stdout == ""
        assert r.stderr == ""
        assert r.duration_s == 0.0
        assert r.metrics == {}
        assert r.critical is False


class TestParseRuff:
    def _mk(self, stdout="", stderr=""):
        return hr.CheckResult(name="ruff", slug="03-ruff", cmd=[], cwd=Path("."), stdout=stdout, stderr=stderr)

    def test_found_n_errors(self):
        r = self._mk(stdout="Found 42 errors.\n")
        assert hr.parse_ruff(r) == {"errors": 42, "clean": False}

    def test_zero_errors(self):
        r = self._mk(stdout="All checks passed! Found 0 errors.\n")
        assert hr.parse_ruff(r) == {"errors": 0, "clean": True}

    def test_no_found_line(self):
        r = self._mk(stdout="All checks passed!\n")
        assert hr.parse_ruff(r) == {"errors": 0, "clean": True}

    def test_singular_error_word(self):
        r = self._mk(stdout="Found 1 error.\n")
        assert hr.parse_ruff(r) == {"errors": 1, "clean": False}

    def test_reads_stderr_too(self):
        r = self._mk(stdout="", stderr="Found 7 errors.\n")
        assert hr.parse_ruff(r) == {"errors": 7, "clean": False}


class TestParseValidate:
    def _mk(self, stdout="", stderr=""):
        return hr.CheckResult(name="validate", slug="04-validate", cmd=[], cwd=Path("."), stdout=stdout, stderr=stderr)

    def test_total_errors_warnings(self):
        r = self._mk(stdout="Total:   72\nErrors:  0\nWarnings: 3\n")
        assert hr.parse_validate(r) == {"total": 72, "errors": 0, "warnings": 3}

    def test_empty_output(self):
        r = self._mk(stdout="")
        assert hr.parse_validate(r) == {"total": 0, "errors": 0, "warnings": 0}

    def test_only_total_present(self):
        r = self._mk(stdout="Total: 10\n")
        assert hr.parse_validate(r) == {"total": 10, "errors": 0, "warnings": 0}


class TestParseEval:
    def _mk(self, stdout=""):
        return hr.CheckResult(name="eval", slug="05-eval", cmd=[], cwd=Path("."), stdout=stdout)

    def test_valid_json_with_results(self):
        data = '{"total": 2, "skills": 1, "agents": 1, "results": [' \
            '{"name": "a", "quality": {"score": 90}},' \
            '{"name": "b", "quality": {"score": 70}}]}'
        r = self._mk(stdout=data)
        m = hr.parse_eval(r)
        assert m["total"] == 2
        assert m["skills"] == 1
        assert m["agents"] == 1
        assert m["avg_score"] == 80.0
        assert m["below_70_count"] == 0

    def test_below_70_identified(self):
        data = '{"total": 2, "results": [' \
            '{"name": "bad", "quality": {"score": 50}},' \
            '{"name": "good", "quality": {"score": 95}}]}'
        m = hr.parse_eval(self._mk(stdout=data))
        assert m["below_70_count"] == 1
        assert m["below_70_names"] == ["bad"]

    def test_parse_error_on_bad_json(self):
        r = self._mk(stdout="not json at all")
        assert hr.parse_eval(r) == {"parse_error": True}

    def test_empty_results_list(self):
        r = self._mk(stdout='{"total": 0, "results": []}')
        m = hr.parse_eval(r)
        assert m["total"] == 0
        assert m["avg_score"] == 0


class TestParsePyCompile:
    def _mk(self, stdout="", stderr="", rc=0):
        return hr.CheckResult(name="pc", slug="01-py_compile", cmd=[], cwd=Path("."),
                              stdout=stdout, stderr=stderr, returncode=rc)

    def test_clean_rc_zero(self):
        m = hr.parse_pycompile(self._mk(rc=0))
        assert m["clean"] is True
        assert m["failures"] == []

    def test_fail_keyword_flags_dirty(self):
        m = hr.parse_pycompile(self._mk(stdout="FAIL: foo.py\n", rc=1))
        assert m["clean"] is False
        assert "FAIL: foo.py" in m["failures"]

    def test_error_keyword_flags_dirty(self):
        m = hr.parse_pycompile(self._mk(stderr="SyntaxError: invalid\n", rc=1))
        assert m["clean"] is False
        assert any("Error" in line for line in m["failures"])

    def test_nonzero_rc_without_keywords(self):
        m = hr.parse_pycompile(self._mk(rc=2))
        assert m["clean"] is False


class TestParseJsonSchema:
    def _mk(self, stdout="", rc=0):
        return hr.CheckResult(name="js", slug="02-json-schema", cmd=[], cwd=Path("."),
                              stdout=stdout, returncode=rc)

    def test_ok_present_and_rc_zero(self):
        assert hr.parse_json_schema(self._mk(stdout="OK\n")) == {"clean": True}

    def test_missing_ok_token(self):
        assert hr.parse_json_schema(self._mk(stdout="nothing")) == {"clean": False}

    def test_nonzero_rc_even_with_ok(self):
        assert hr.parse_json_schema(self._mk(stdout="OK\n", rc=1)) == {"clean": False}


class TestSanitize:
    def test_plugin_root_replaced(self):
        plugin = str(hr.PLUGIN_ROOT).replace("\\", "/")
        s = hr._sanitize(f"cd {plugin}/scripts")
        assert "<plugin_root>" in s
        assert plugin not in s

    def test_repo_root_replaced(self):
        repo = str(hr.REPO_ROOT).replace("\\", "/")
        s = hr._sanitize(f"cd {repo}")
        assert "<repo_root>" in s

    def test_home_replaced(self):
        home = str(Path.home()).replace("\\", "/")
        s = hr._sanitize(f"config at {home}/.claude")
        assert "~" in s
        assert home not in s

    def test_python_executable_replaced(self):
        py = sys.executable.replace("\\", "/")
        s = hr._sanitize(f"{py} scripts/foo.py")
        assert s.startswith("python ")

    def test_empty_input(self):
        assert hr._sanitize("") == ""

    def test_none_input(self):
        assert hr._sanitize(None) is None

    def test_no_sensitive_data_passthrough(self):
        inp = "cd /app && python foo.py"
        # Note: /app isn't one of our substitution roots on this machine
        out = hr._sanitize(inp)
        assert "cd " in out
        assert "foo.py" in out

    def test_idempotent(self):
        plugin = str(hr.PLUGIN_ROOT).replace("\\", "/")
        once = hr._sanitize(f"cd {plugin}")
        twice = hr._sanitize(once)
        assert once == twice

    def test_multiple_substitutions_in_one_string(self):
        plugin = str(hr.PLUGIN_ROOT).replace("\\", "/")
        home = str(Path.home()).replace("\\", "/")
        s = hr._sanitize(f"cd {plugin} && ls {home}/.claude")
        assert "<plugin_root>" in s
        assert "~" in s


class TestModuleConstants:
    def test_plugin_root_is_path(self):
        assert isinstance(hr.PLUGIN_ROOT, Path)

    def test_plugin_root_contains_scripts(self):
        # Structural invariant — survives directory renames.
        assert (hr.PLUGIN_ROOT / "scripts" / "hardening-run.py").exists()

    def test_repo_root_is_plugin_parent(self):
        assert hr.REPO_ROOT == hr.PLUGIN_ROOT.parent


class TestRunCheckSubprocess:
    """Exercises run_check's subprocess wrapper with real tiny commands.

    These guard the Pathlib migration (next task): cwd= must work with
    Path objects, timeouts must fire, missing tools must return rc=-1
    without raising. Cross-platform (Windows + Linux).
    """
    def test_success_captures_stdout(self, tmp_path):
        r = hr.run_check(
            "echo test", "test-echo",
            [sys.executable, "-c", "print('hello')"],
            tmp_path,
        )
        assert r.returncode == 0
        assert "hello" in r.stdout
        assert r.critical is False

    def test_nonzero_returncode_preserved(self, tmp_path):
        r = hr.run_check(
            "exit 3", "test-exit",
            [sys.executable, "-c", "import sys; sys.exit(3)"],
            tmp_path,
        )
        assert r.returncode == 3
        assert r.critical is False  # non-zero rc alone isn't critical

    def test_stderr_captured(self, tmp_path):
        r = hr.run_check(
            "stderr", "test-stderr",
            [sys.executable, "-c", "import sys; sys.stderr.write('err-line'); sys.exit(1)"],
            tmp_path,
        )
        assert "err-line" in r.stderr
        assert r.returncode == 1

    def test_file_not_found_returns_neg1_not_critical(self, tmp_path):
        r = hr.run_check(
            "missing tool", "test-missing",
            ["this-binary-does-not-exist-anywhere-really"],
            tmp_path,
        )
        assert r.returncode == -1
        assert "TOOL NOT FOUND" in r.stderr
        assert r.critical is False  # missing tool is noted, not critical

    def test_timeout_marks_critical(self, tmp_path):
        r = hr.run_check(
            "slow", "test-slow",
            [sys.executable, "-c", "import time; time.sleep(5)"],
            tmp_path,
            timeout=1,
        )
        assert r.returncode == -1
        assert "TIMEOUT" in r.stderr
        assert r.critical is True

    def test_cwd_is_respected(self, tmp_path):
        # Tiny guard for Pathlib-migration: cwd= accepts str(Path).
        r = hr.run_check(
            "pwd", "test-cwd",
            [sys.executable, "-c", "import os; print(os.getcwd())"],
            tmp_path,
        )
        assert r.returncode == 0
        # resolve() to normalize symlinks + short-name on Windows
        assert Path(r.stdout.strip()).resolve() == tmp_path.resolve()

    def test_duration_recorded(self, tmp_path):
        r = hr.run_check(
            "fast", "test-fast",
            [sys.executable, "-c", "pass"],
            tmp_path,
        )
        assert r.duration_s >= 0
        assert r.duration_s < 10  # sanity ceiling


class TestWriteLog:
    def test_creates_artifact_dir_and_writes_log(self, tmp_path):
        r = hr.CheckResult(
            name="Test Check", slug="99-test",
            cmd=["echo", "hi"], cwd=tmp_path,
            returncode=0, stdout="output", stderr="",
            duration_s=1.5,
        )
        artifact_dir = tmp_path / "artifacts"
        path = hr.write_log(artifact_dir, r)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Test Check" in content
        assert "echo hi" in content
        assert "output" in content
        assert "returncode: 0" in content
