"""Tests for hooks/org-naming-pre-push.py — Wrong-Folder/Repo mitigation.

Hook only fires on PreToolUse Bash with `git push` in command. Extracts the
repo's origin URL from cwd, parses the GitHub org/user, and emits an advisory
if the org is NOT in the allowlist (default: AI-Engineering-at, LEEI1337,
FoxLabs-ai). Special-case: warn explicitly on the typo-org "AI-Engineerings-at".

Default mode: advisory (exit 0 + additionalContext). Optional block-mode
gated by config flag (NOT enabled by default).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_FILE = REPO_ROOT / "hooks" / "org-naming-pre-push.py"

sys.path.insert(0, str(REPO_ROOT / "hooks"))
_spec = importlib.util.spec_from_file_location("org_naming_pre_push", HOOK_FILE)
ong = importlib.util.module_from_spec(_spec)
sys.modules["org_naming_pre_push"] = ong
_spec.loader.exec_module(ong)


# ---------------------------------------------------------------------------
# Pure-Function: command parsing
# ---------------------------------------------------------------------------


class TestIsGitPushCommand:
    @pytest.mark.parametrize(
        "command",
        [
            "git push",
            "git push origin main",
            "git push origin feature/x",
            "git push --force-with-lease origin main",
            "git -C /some/path push origin master",
            "git push origin HEAD:refs/heads/main",
        ],
    )
    def test_recognized_pushes(self, command):
        assert ong.is_git_push_command(command), f"missed: {command!r}"

    @pytest.mark.parametrize(
        "command",
        [
            "git status",
            "git pull",
            "git fetch origin",
            "git commit -m 'feat: x'",
            "echo 'git push'",  # not actually a push, just text
            "git log --oneline",
            "ls -la",
            "",
        ],
    )
    def test_non_push_commands(self, command):
        assert not ong.is_git_push_command(command), f"false-fire: {command!r}"


# ---------------------------------------------------------------------------
# Pure-Function: org parsing
# ---------------------------------------------------------------------------


class TestParseOrgFromUrl:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://github.com/AI-Engineering-at/nomos.git", "AI-Engineering-at"),
            ("https://github.com/AI-Engineering-at/nomos", "AI-Engineering-at"),
            ("https://github.com/LEEI1337/BBB000k-.git", "LEEI1337"),
            ("git@github.com:AI-Engineering-at/zeroth.git", "AI-Engineering-at"),
            ("git@github.com:LEEI1337/repo", "LEEI1337"),
            ("https://github.com/AI-Engineerings-at/typo.git", "AI-Engineerings-at"),
            ("https://github.com/FoxLabs-ai/proj.git", "FoxLabs-ai"),
            ("https://github.com/external-fork/repo.git", "external-fork"),
        ],
    )
    def test_extracts_org(self, url, expected):
        assert ong.parse_org_from_url(url) == expected

    @pytest.mark.parametrize(
        "url",
        [
            "",
            None,
            "not-a-git-url",
            "https://gitlab.com/foo/bar.git",  # not GitHub
            "https://github.com/",  # missing org
        ],
    )
    def test_unparseable_returns_none(self, url):
        assert ong.parse_org_from_url(url) is None


# ---------------------------------------------------------------------------
# Pure-Function: classify_org
# ---------------------------------------------------------------------------


class TestClassifyOrg:
    def test_allowlisted(self):
        assert ong.classify_org("AI-Engineering-at") == "allow"
        assert ong.classify_org("LEEI1337") == "allow"
        assert ong.classify_org("FoxLabs-ai") == "allow"

    def test_typo_org(self):
        assert ong.classify_org("AI-Engineerings-at") == "typo"

    def test_unknown_org(self):
        assert ong.classify_org("johndpope") == "unknown"
        assert ong.classify_org("random-fork") == "unknown"

    def test_none_org(self):
        assert ong.classify_org(None) == "none"
        assert ong.classify_org("") == "none"


# ---------------------------------------------------------------------------
# Subprocess Integration
# ---------------------------------------------------------------------------


def _run_hook(payload: dict, tmp_path: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
    return subprocess.run(
        [sys.executable, str(HOOK_FILE)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )


class TestNonPushCommandIsSilent:
    def test_git_status_silent(self, tmp_path):
        payload = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-ong-status",
            "tool_name": "Bash",
            "tool_input": {"command": "git status"},
        }
        r = _run_hook(payload, tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip() == ""

    def test_non_bash_tool_silent(self, tmp_path):
        payload = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-ong-non-bash",
            "tool_name": "Edit",
            "tool_input": {"file_path": "/x.py"},
        }
        r = _run_hook(payload, tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip() == ""


class TestPushAdvisoryBehavior:
    def _push_payload(self, session_id: str, cwd: str = ""):
        return {
            "hook_event_name": "PreToolUse",
            "session_id": session_id,
            "tool_name": "Bash",
            "tool_input": {"command": "git push origin main"},
            "cwd": cwd,
        }

    def test_push_in_typo_org_emits_warning(self, tmp_path, monkeypatch):
        """When cwd is in a repo with AI-Engineerings-at remote, hook warns."""
        # Create fake repo dir with .git/config containing typo-org URL
        repo = tmp_path / "fake-typo-repo"
        (repo / ".git").mkdir(parents=True)
        (repo / ".git" / "config").write_text(
            '[remote "origin"]\n\turl = https://github.com/AI-Engineerings-at/foo.git\n',
            encoding="utf-8",
        )
        payload = self._push_payload("test-ong-typo", str(repo))
        r = _run_hook(payload, tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip(), "expected advisory output"
        out = json.loads(r.stdout.strip())
        ctx = out.get("additionalContext", "")
        assert "Engineerings-at" in ctx or "typo" in ctx.lower()

    def test_push_in_allowed_org_silent(self, tmp_path):
        repo = tmp_path / "fake-allowed-repo"
        (repo / ".git").mkdir(parents=True)
        (repo / ".git" / "config").write_text(
            '[remote "origin"]\n\turl = https://github.com/AI-Engineering-at/foo.git\n',
            encoding="utf-8",
        )
        payload = self._push_payload("test-ong-allowed", str(repo))
        r = _run_hook(payload, tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip() == ""

    def test_push_in_unknown_org_emits_warning(self, tmp_path):
        repo = tmp_path / "fake-unknown-repo"
        (repo / ".git").mkdir(parents=True)
        (repo / ".git" / "config").write_text(
            '[remote "origin"]\n\turl = https://github.com/johndpope/llama-cpp.git\n',
            encoding="utf-8",
        )
        payload = self._push_payload("test-ong-unknown", str(repo))
        r = _run_hook(payload, tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip(), "expected advisory for unknown org"
        out = json.loads(r.stdout.strip())
        ctx = out.get("additionalContext", "")
        assert (
            "johndpope" in ctx or "unknown" in ctx.lower() or "allowlist" in ctx.lower()
        )

    def test_push_with_no_origin_silent(self, tmp_path):
        """Repo with no origin remote (Documents-parent case) → silent pass."""
        repo = tmp_path / "fake-no-origin"
        (repo / ".git").mkdir(parents=True)
        (repo / ".git" / "config").write_text(
            "[core]\n\trepositoryformatversion = 0\n", encoding="utf-8"
        )
        payload = self._push_payload("test-ong-no-origin", str(repo))
        r = _run_hook(payload, tmp_path)
        assert r.returncode == 0
        # No origin → can't classify → silent (don't fire on every Bash)
        assert r.stdout.strip() == ""


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_invalid_json_exits_0(self, tmp_path):
        env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
        r = subprocess.run(
            [sys.executable, str(HOOK_FILE)],
            input="{not valid json",
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert r.returncode == 0
        assert r.stdout.strip() == ""

    def test_empty_stdin_exits_0(self, tmp_path):
        env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
        r = subprocess.run(
            [sys.executable, str(HOOK_FILE)],
            input="",
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert r.returncode == 0

    def test_missing_command_silent(self, tmp_path):
        payload = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-ong-no-cmd",
            "tool_name": "Bash",
            "tool_input": {},
        }
        r = _run_hook(payload, tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip() == ""
