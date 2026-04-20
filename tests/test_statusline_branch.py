"""Unit tests for statusline_lib.current_branch — git branch detection via .git/HEAD.

Covers the C-BRANCH01 soft-prevention signal (Track H from Session 2026-04-20).
No git subprocess — pure file read of .git/HEAD or gitdir-file-redirect.
"""
import sys
from pathlib import Path

import pytest

# Tests sit one level under meta-skills/, scripts/ is a sibling.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from statusline_lib import current_branch, _find_git_head  # noqa: E402


class TestFindGitHead:
    def test_plain_git_head_found(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/mybranch\n", encoding="utf-8")
        head = _find_git_head(tmp_path)
        assert head == tmp_path / ".git" / "HEAD"

    def test_git_head_found_from_subdir(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
        sub = tmp_path / "src" / "deep"
        sub.mkdir(parents=True)
        head = _find_git_head(sub)
        assert head == tmp_path / ".git" / "HEAD"

    def test_submodule_gitdir_redirect(self, tmp_path):
        """Submodule: .git is a file with 'gitdir:' pointing to parent's .git/modules/X."""
        repo = tmp_path / "parent-repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        modules_dir = repo / ".git" / "modules" / "sub"
        modules_dir.mkdir(parents=True)
        (modules_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

        sub = repo / "sub"
        sub.mkdir()
        (sub / ".git").write_text("gitdir: ../.git/modules/sub\n", encoding="utf-8")

        head = _find_git_head(sub)
        assert head is not None, "submodule .git file redirect should be resolved"
        assert head.is_file()
        assert head.name == "HEAD"


class TestCurrentBranch:
    def test_main_branch_returns_main_severity(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
        assert current_branch(str(tmp_path)) == ("main", "main")

    def test_master_branch_returns_main_severity(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/master\n", encoding="utf-8")
        assert current_branch(str(tmp_path)) == ("master", "main")

    def test_feature_branch_returns_feature_severity(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/feature/xyz-work\n", encoding="utf-8")
        assert current_branch(str(tmp_path)) == ("feature/xyz-work", "feature")

    def test_deep_slashed_branch_name(self, tmp_path):
        """feat/area/sub-name must be preserved intact (not split at first /)."""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/feat/area/sub-name\n", encoding="utf-8")
        assert current_branch(str(tmp_path)) == ("feat/area/sub-name", "feature")

    def test_detached_head_returns_detached_severity(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "HEAD").write_text("abc1234567890def1234567890deadbeefcafe01\n", encoding="utf-8")
        branch, sev = current_branch(str(tmp_path))
        assert branch == "@abc1234"
        assert sev == "detached"

    def test_nonheads_ref_treated_as_detached(self, tmp_path):
        """refs/tags/X (rare) or any non-refs/heads/ prefix → detached-like."""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "HEAD").write_text("ref: refs/tags/v1.0\n", encoding="utf-8")
        _, sev = current_branch(str(tmp_path))
        assert sev == "detached"

    def test_empty_cwd_falls_back_to_cwd(self, tmp_path, monkeypatch):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        assert current_branch("") == ("main", "main")

    def test_nonexistent_path_returns_none(self):
        # Path that definitely doesn't exist — walks up to non-git ancestors or fails
        branch, sev = current_branch("/definitely/not/a/real/path/here-12345abc")
        # Either "none" (no git) or valid (if running under a real repo) — no crash.
        assert sev in {"none", "main", "feature", "detached"}

    def test_malformed_empty_head_returns_none(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "HEAD").write_text("", encoding="utf-8")
        assert current_branch(str(tmp_path)) == (None, "none")

    def test_submodule_on_main_detected(self, tmp_path):
        """End-to-end: submodule layout with .git file redirect on main branch."""
        repo = tmp_path / "outer"
        repo.mkdir()
        (repo / ".git").mkdir()
        mod = repo / ".git" / "modules" / "inner"
        mod.mkdir(parents=True)
        (mod / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
        inner = repo / "inner"
        inner.mkdir()
        (inner / ".git").write_text("gitdir: ../.git/modules/inner\n", encoding="utf-8")

        assert current_branch(str(inner)) == ("main", "main")
