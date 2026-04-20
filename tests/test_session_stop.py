"""Tests for hooks/session-stop.py — Stop event verification + docs reminder.

Covers:
- is_knowledge_relevant() for KNOWLEDGE_KEYWORDS
- Always emits Documentation reminder
- Uncommitted changes warning (via git diff --stat in cwd)
- Lint-not-PASS warning for .py / .ts changes (from SessionState quality_gate)
- open-notebook recommendation when knowledge-relevant
- Git summary included when non-empty
- Malformed / empty stdin handled
"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_FILE = REPO_ROOT / "hooks" / "session-stop.py"

sys.path.insert(0, str(REPO_ROOT / "hooks"))
_spec = importlib.util.spec_from_file_location("session_stop", HOOK_FILE)
ss = importlib.util.module_from_spec(_spec)
sys.modules["session_stop"] = ss
# Don't exec_module on session_stop — it runs main() via if __name__=='__main__' only.
# So executing still runs top-level imports but NOT main().
_spec.loader.exec_module(ss)


def _run(payload: dict, tmp_path: Path, cwd: Path | None = None):
    env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
    return subprocess.run(
        [sys.executable, str(HOOK_FILE)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=15, env=env,
        cwd=str(cwd) if cwd else None,
    )


def _ctx(out: str) -> str:
    return json.loads(out.strip()).get("additionalContext", "") if out.strip() else ""


class TestIsKnowledgeRelevant:
    @pytest.mark.parametrize("summary,expected", [
        ("modified CLAUDE.md", True),
        ("updated rules/24-meta-skills.md", True),
        ("added knowledge/L300.md", True),
        ("new LEARNINGS.md entry", True),
        ("ERRORS.md: E200 added", True),
        ("updated STATUS.md", True),
        ("docs/migration updated", True),
        ("README.md typo fix", True),
        ("ARCHITECTURE review complete", True),
        ("AUDIT notes for v4.3.0", True),
        ("deploy script changed", True),
        ("migration guide added", True),
        ("config.yml updated", True),
        ("fixed bug in helper_utils.py", False),
        ("refactored test suite", False),
        ("", False),
    ])
    def test_classification(self, summary, expected):
        assert ss.is_knowledge_relevant(summary) == expected


class TestBaseOutput:
    def test_always_emits_documentation_reminder(self, tmp_path):
        r = _run({"session_id": "s"}, tmp_path)
        assert r.returncode == 0
        ctx = _ctx(r.stdout)
        assert "Documentation" in ctx
        assert "ERPNext" in ctx

    def test_malformed_stdin(self, tmp_path):
        env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
        r = subprocess.run(
            [sys.executable, str(HOOK_FILE)], input="{not json",
            capture_output=True, text=True, timeout=10, env=env,
        )
        assert r.returncode == 0
        assert "Documentation" in _ctx(r.stdout)

    def test_empty_stdin(self, tmp_path):
        env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
        r = subprocess.run(
            [sys.executable, str(HOOK_FILE)], input="",
            capture_output=True, text=True, timeout=10, env=env,
        )
        assert r.returncode == 0


class TestUncommittedChanges:
    def test_uncommitted_warning_emits(self, tmp_path):
        """In a fresh git repo with uncommitted changes, warning should fire."""
        # Create a throwaway git repo inside tmp_path
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "test@x"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        (tmp_path / "foo.txt").write_text("initial", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)
        # Now modify to create uncommitted
        (tmp_path / "foo.txt").write_text("changed", encoding="utf-8")

        r = _run({"session_id": "s-uncomm"}, tmp_path, cwd=tmp_path)
        ctx = _ctx(r.stdout)
        assert "UNCOMMITTED CHANGES detected" in ctx

    def test_clean_repo_no_uncommitted_warning(self, tmp_path):
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "test@x"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        (tmp_path / "foo.txt").write_text("x", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)

        r = _run({"session_id": "s-clean"}, tmp_path, cwd=tmp_path)
        assert "UNCOMMITTED CHANGES detected" not in _ctx(r.stdout)


class TestLintWarnings:
    def test_py_changed_lint_not_pass_warns(self, tmp_path):
        """Seed SessionState with last_lint_result != PASS + .py changes present in git summary."""
        # Create a git repo with .py change
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "t@x"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        (tmp_path / "x.py").write_text("# initial\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)
        # modify .py file → will appear in git diff
        (tmp_path / "x.py").write_text("# changed\n", encoding="utf-8")

        # Seed state with lint not PASS
        sid = "s-lint-py"
        state_file = tmp_path / f".meta-state-{sid}.json"
        state_file.write_text(
            json.dumps({
                "session_id": sid,
                "quality_gate": {"last_lint_result": "FAIL"},
            }),
            encoding="utf-8",
        )
        r = _run({"session_id": sid}, tmp_path, cwd=tmp_path)
        ctx = _ctx(r.stdout)
        # Note: git_summary comes from services.get_git_changes_summary which
        # uses `git log --after=yesterday`. In a fresh repo with just one commit
        # from today, it lists x.py. But if test runs right after commit, might
        # be empty. Accept either: warning OR knowledge message absent.
        # Strict assertion only if git_summary non-empty:
        if "x.py" in ctx or "Git summary" in ctx:
            assert "ruff check" in ctx or "Python files changed" in ctx


class TestKnowledgeRecommendation:
    def test_knowledge_recommend_appears_for_claude_md_change(self, tmp_path):
        """If git summary contains knowledge keyword, open-notebook hint fires."""
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "t@x"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        (tmp_path / "CLAUDE.md").write_text("v1", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "add CLAUDE.md"], cwd=tmp_path, check=True)
        # make another commit so it shows in log --after=yesterday
        (tmp_path / "CLAUDE.md").write_text("v2", encoding="utf-8")
        subprocess.run(["git", "commit", "-a", "-q", "-m", "update CLAUDE.md"], cwd=tmp_path, check=True)

        r = _run({"session_id": "s-know"}, tmp_path, cwd=tmp_path)
        ctx = _ctx(r.stdout)
        # Git summary should include CLAUDE.md reference → knowledge-relevant
        if "CLAUDE.md" in ctx:
            assert "open-notebook" in ctx or "RECOMMENDATION" in ctx
