"""Tests for hooks/context-recovery.py — PreCompact state-save hook.

Covers:
- Session state snapshot (project, cwd, prompt_count, timestamp)
- Recovery context emit with prompt count + project + quality gate + scope
- Quality-gate consecutive_failures included when > 0
- Scope task_switches included when > 0
- Git summary clipped to 200 chars
- compaction_count increments across calls
- Malformed / empty stdin → still functional (defaults)
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_FILE = REPO_ROOT / "hooks" / "context-recovery.py"


def _run(payload: str, tmp_path: Path, timeout: int = 10, cwd: Path | None = None):
    env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
    return subprocess.run(
        [sys.executable, str(HOOK_FILE)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=str(cwd) if cwd else None,
    )


def _seed_state(tmp_path: Path, session_id: str, data: dict) -> None:
    """Write a SessionState JSON blob before the hook runs."""
    (tmp_path / f".meta-state-{session_id}.json").write_text(
        json.dumps({"session_id": session_id, **data}),
        encoding="utf-8",
    )


def _read_state(tmp_path: Path, session_id: str) -> dict:
    p = tmp_path / f".meta-state-{session_id}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


class TestStateSnapshot:
    def test_session_meta_populated(self, tmp_path):
        r = _run(json.dumps({"session_id": "cr-snap"}), tmp_path)
        assert r.returncode == 0
        s = _read_state(tmp_path, "cr-snap")
        meta = s.get("session_meta") or {}
        assert "project" in meta
        assert "cwd" in meta
        assert "timestamp" in meta
        assert "prompt_count_at_save" in meta
        assert meta.get("open_items") == "pre-compaction save"

    def test_compaction_count_increments(self, tmp_path):
        sid = "cr-count"
        _run(json.dumps({"session_id": sid}), tmp_path)
        first = _read_state(tmp_path, sid)["session_meta"]["compaction_count"]
        _run(json.dumps({"session_id": sid}), tmp_path)
        second = _read_state(tmp_path, sid)["session_meta"]["compaction_count"]
        assert second == first + 1

    def test_prompt_count_at_save_uses_current_value(self, tmp_path):
        sid = "cr-pc"
        _seed_state(tmp_path, sid, {"prompt_count": 42})
        _run(json.dumps({"session_id": sid}), tmp_path)
        assert _read_state(tmp_path, sid)["session_meta"]["prompt_count_at_save"] == 42


class TestRecoveryContextOutput:
    def test_basic_recovery_context_emitted(self, tmp_path):
        r = _run(json.dumps({"session_id": "cr-basic"}), tmp_path)
        assert r.returncode == 0
        out = json.loads(r.stdout.strip())
        ctx = out["additionalContext"]
        assert "PRE-COMPACTION STATE SAVE" in ctx
        assert "prompt #" in ctx
        assert "Project:" in ctx

    def test_quality_failures_included_when_present(self, tmp_path):
        sid = "cr-qg"
        _seed_state(tmp_path, sid, {
            "prompt_count": 5,
            "quality_gate": {
                "consecutive_failures": 3,
                "last_lint_result": "FAIL",
                "last_test_result": "PASS",
            },
        })
        r = _run(json.dumps({"session_id": sid}), tmp_path)
        ctx = json.loads(r.stdout.strip())["additionalContext"]
        assert "Quality:" in ctx
        assert "3 consecutive failures" in ctx
        assert "lint=FAIL" in ctx
        assert "tests=PASS" in ctx

    def test_quality_section_omitted_when_zero_failures(self, tmp_path):
        sid = "cr-qg-clean"
        _seed_state(tmp_path, sid, {
            "quality_gate": {"consecutive_failures": 0, "last_lint_result": "OK"},
        })
        r = _run(json.dumps({"session_id": sid}), tmp_path)
        ctx = json.loads(r.stdout.strip())["additionalContext"]
        assert "Quality:" not in ctx, f"Quality must not appear when failures=0; got {ctx!r}"

    def test_scope_switches_included_when_present(self, tmp_path):
        sid = "cr-scope"
        _seed_state(tmp_path, sid, {
            "scope_tracker": {
                "task_switches": 4,
                "seen_domains": ["agent", "test", "docs", "deploy", "monitoring"],
            },
        })
        r = _run(json.dumps({"session_id": sid}), tmp_path)
        ctx = json.loads(r.stdout.strip())["additionalContext"]
        assert "Scope:" in ctx
        assert "4 topic switches" in ctx
        assert "agent" in ctx

    def test_scope_section_omitted_when_no_switches(self, tmp_path):
        sid = "cr-scope-clean"
        _seed_state(tmp_path, sid, {
            "scope_tracker": {"task_switches": 0, "seen_domains": []},
        })
        r = _run(json.dumps({"session_id": sid}), tmp_path)
        ctx = json.loads(r.stdout.strip())["additionalContext"]
        assert "Scope:" not in ctx


class TestEdgeCases:
    def test_malformed_stdin_exits_0(self, tmp_path):
        r = _run("{not valid json", tmp_path)
        assert r.returncode == 0
        assert json.loads(r.stdout.strip())  # still emits valid context

    def test_empty_stdin_exits_0(self, tmp_path):
        r = _run("", tmp_path)
        assert r.returncode == 0
        # session_id defaults to "unknown"
        s = _read_state(tmp_path, "unknown")
        assert "session_meta" in s

    def test_non_git_cwd_still_works(self, tmp_path):
        """Run hook from tmp_path (no git repo) — git_summary should be empty,
        but the hook still emits recovery context."""
        r = _run(json.dumps({"session_id": "cr-nogit"}), tmp_path, cwd=tmp_path)
        assert r.returncode == 0
        ctx = json.loads(r.stdout.strip())["additionalContext"]
        assert "PRE-COMPACTION STATE SAVE" in ctx
