"""Tests for hooks/ahead-of-remote-warning.py — Datenverlust-Risiko Mitigation.

SessionStart hook. Iterates a watch-list of repos, runs `git rev-list --count
origin/<branch>..HEAD` to count unpushed commits, and emits an advisory if
any repo is ≥ threshold (default: 5 ahead, 20 critical).

Pure subprocess call (no git fetch) — won't update remote refs.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_FILE = REPO_ROOT / "hooks" / "ahead-of-remote-warning.py"

sys.path.insert(0, str(REPO_ROOT / "hooks"))
_spec = importlib.util.spec_from_file_location("ahead_of_remote_warning", HOOK_FILE)
arw = importlib.util.module_from_spec(_spec)
sys.modules["ahead_of_remote_warning"] = arw
_spec.loader.exec_module(arw)


# ---------------------------------------------------------------------------
# Pure-Function: severity classification
# ---------------------------------------------------------------------------


class TestClassifySeverity:
    def test_below_warn_threshold(self):
        assert arw.classify_severity(0) == "ok"
        assert arw.classify_severity(4) == "ok"

    def test_warn_threshold(self):
        assert arw.classify_severity(5) == "warn"
        assert arw.classify_severity(19) == "warn"

    def test_critical_threshold(self):
        assert arw.classify_severity(20) == "critical"
        assert arw.classify_severity(100) == "critical"

    def test_unknown_count(self):
        assert arw.classify_severity(None) == "unknown"
        assert arw.classify_severity(-1) == "unknown"


# ---------------------------------------------------------------------------
# Pure-Function: count_ahead via subprocess (real git, fast)
# ---------------------------------------------------------------------------


def _make_git_repo(path: Path) -> None:
    """Initialize a git repo with origin pointing to itself for self-test."""
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "README.md").write_text("init", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=path, check=True)


class TestCountAhead:
    def test_invalid_repo_returns_none(self, tmp_path):
        # Not a git repo at all
        assert arw.count_ahead(str(tmp_path / "nonexistent"), "main") is None

    def test_repo_without_origin_returns_none(self, tmp_path):
        repo = tmp_path / "repo-no-origin"
        repo.mkdir()
        _make_git_repo(repo)
        # No origin configured → can't compute origin/main..HEAD → None
        assert arw.count_ahead(str(repo), "main") is None

    def test_count_with_synthetic_origin(self, tmp_path):
        # Create source repo, clone it, make commits in clone → ahead count > 0
        src = tmp_path / "src"
        src.mkdir()
        _make_git_repo(src)
        clone = tmp_path / "clone"
        subprocess.run(["git", "clone", "-q", str(src), str(clone)], check=True)
        # Repo has 1 commit (init), clone is sync. Make 3 new commits in clone.
        for i in range(3):
            (clone / f"f{i}.txt").write_text(str(i), encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=clone, check=True)
            subprocess.run(["git", "commit", "-q", "-m", f"c{i}"], cwd=clone, check=True)

        # Detect default branch — git init may use "main" or "master"
        head = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            cwd=clone,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert arw.count_ahead(str(clone), head) == 3


# ---------------------------------------------------------------------------
# Subprocess Integration
# ---------------------------------------------------------------------------


def _run_hook(payload: dict, tmp_path: Path, watch_list_override=None) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
    if watch_list_override is not None:
        env["AHEAD_WARN_WATCH"] = ",".join(watch_list_override)
    return subprocess.run(
        [sys.executable, str(HOOK_FILE)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )


class TestSessionStartIntegration:
    def test_no_repos_at_risk_silent(self, tmp_path):
        # Override watch-list to a non-existent repo → all return None → no warning
        payload = {"hook_event_name": "SessionStart", "session_id": "test-arw-clean"}
        r = _run_hook(payload, tmp_path, watch_list_override=[str(tmp_path / "nonexistent")])
        assert r.returncode == 0
        assert r.stdout.strip() == "", "expected silent pass when no repos at risk"

    def test_repo_with_5_ahead_emits_warn(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        _make_git_repo(src)
        clone = tmp_path / "watched-repo"
        subprocess.run(["git", "clone", "-q", str(src), str(clone)], check=True)
        # 5 commits ahead → warn threshold
        for i in range(5):
            (clone / f"f{i}.txt").write_text(str(i), encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=clone, check=True)
            subprocess.run(["git", "commit", "-q", "-m", f"c{i}"], cwd=clone, check=True)

        payload = {"hook_event_name": "SessionStart", "session_id": "test-arw-5ahead"}
        r = _run_hook(payload, tmp_path, watch_list_override=[str(clone)])
        assert r.returncode == 0
        assert r.stdout.strip(), "expected advisory output"
        out = json.loads(r.stdout.strip())
        ctx = out.get("additionalContext", "")
        assert "5" in ctx
        assert "ahead" in ctx.lower()

    def test_repo_with_20_ahead_critical(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        _make_git_repo(src)
        clone = tmp_path / "critical-repo"
        subprocess.run(["git", "clone", "-q", str(src), str(clone)], check=True)
        for i in range(20):
            (clone / f"f{i}.txt").write_text(str(i), encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=clone, check=True)
            subprocess.run(["git", "commit", "-q", "-m", f"c{i}"], cwd=clone, check=True)

        payload = {"hook_event_name": "SessionStart", "session_id": "test-arw-critical"}
        r = _run_hook(payload, tmp_path, watch_list_override=[str(clone)])
        assert r.returncode == 0
        out = json.loads(r.stdout.strip())
        ctx = out.get("additionalContext", "").lower()
        assert "critical" in ctx or "20" in ctx


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_non_session_start_event_silent(self, tmp_path):
        payload = {"hook_event_name": "UserPromptSubmit", "session_id": "x"}
        r = _run_hook(payload, tmp_path, watch_list_override=[])
        assert r.returncode == 0
        assert r.stdout.strip() == ""

    def test_invalid_json_exits_0(self, tmp_path):
        env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path), "AHEAD_WARN_WATCH": ""}
        r = subprocess.run(
            [sys.executable, str(HOOK_FILE)],
            input="{not valid",
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert r.returncode == 0
        assert r.stdout.strip() == ""

    def test_empty_stdin_exits_0(self, tmp_path):
        env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path), "AHEAD_WARN_WATCH": ""}
        r = subprocess.run(
            [sys.executable, str(HOOK_FILE)],
            input="",
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert r.returncode == 0
