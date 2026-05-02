"""Tests for hooks/false-positive-guard.py — Opus 4.7 confidence-drift mitigation.

Two-event hook:
- UserPromptSubmit: scan prompt for bug-evidence keywords, update state with timestamp
- PreToolUse (Edit): if no recent bug-evidence in state, emit advisory; else silent pass

Covers:
- Bug-evidence pattern detection (DE+EN)
- Tool-output failure detection (FAIL, Traceback, Error)
- State persistence across invocations
- Time-window logic (recent vs stale evidence)
- Edge cases (empty/malformed JSON, missing fields)
- Subprocess integration with both event types
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_FILE = REPO_ROOT / "hooks" / "false-positive-guard.py"

# Load dash-named hook module via importlib (same pattern as test_correction_detect)
sys.path.insert(0, str(REPO_ROOT / "hooks"))
_spec = importlib.util.spec_from_file_location("false_positive_guard", HOOK_FILE)
fpg = importlib.util.module_from_spec(_spec)
sys.modules["false_positive_guard"] = fpg
_spec.loader.exec_module(fpg)


# ---------------------------------------------------------------------------
# Pure-Function Tests: bug-evidence detection
# ---------------------------------------------------------------------------


class TestDetectBugEvidenceGerman:
    @pytest.mark.parametrize(
        "prompt",
        [
            "es gibt einen bug in der API",
            "diese Funktion ist kaputt",
            "ich bekomme einen fehler beim start",
            "es crasht beim Import",
            "das geht nicht mehr",
            "exception in main loop",
            "stack trace zeigt eine NullPointerException",
        ],
    )
    def test_german_bug_keywords(self, prompt):
        assert fpg.detect_bug_evidence(prompt), f"failed for: {prompt}"


class TestDetectBugEvidenceEnglish:
    @pytest.mark.parametrize(
        "prompt",
        [
            "there's a bug in the parser",
            "the function is broken",
            "it crashes on startup",
            "it doesn't work anymore",
            "I'm getting an error in the logger",
            "fix the typo on line 42",
            "exception thrown when calling foo()",
            "this is failing my tests",
        ],
    )
    def test_english_bug_keywords(self, prompt):
        assert fpg.detect_bug_evidence(prompt), f"failed for: {prompt}"


class TestDetectBugEvidenceFromToolOutput:
    @pytest.mark.parametrize(
        "output",
        [
            "FAILED tests/test_x.py::test_foo - AssertionError",
            "Traceback (most recent call last):",
            "ERROR: AssertionError: expected 5, got 3",
            "1 failed, 0 passed",
            "ruff check found 3 errors",
        ],
    )
    def test_failure_in_tool_output(self, output):
        assert fpg.detect_failure_in_tool_output(output), f"failed for: {output}"


class TestNoBugEvidence:
    @pytest.mark.parametrize(
        "prompt",
        [
            "bitte schreibe eine neue Funktion für X",
            "kannst du den Code refactoren?",
            "add a new feature for parsing",
            "make this class more readable",
            "ich möchte eine neue Datei anlegen",
            "let's implement the new endpoint",
            "documentation update",
        ],
    )
    def test_neutral_prompts_no_evidence(self, prompt):
        assert not fpg.detect_bug_evidence(prompt), f"false positive for: {prompt}"

    def test_empty_prompt(self):
        assert not fpg.detect_bug_evidence("")

    def test_none_prompt(self):
        assert not fpg.detect_bug_evidence(None)


# ---------------------------------------------------------------------------
# Pure-Function Tests: time-window logic
# ---------------------------------------------------------------------------


class TestEvidenceWindowLogic:
    def test_recent_evidence_is_recent(self):
        now = time.time()
        assert fpg.is_evidence_recent(now - 60, threshold_seconds=600)

    def test_stale_evidence_is_not_recent(self):
        now = time.time()
        assert not fpg.is_evidence_recent(now - 3600, threshold_seconds=600)

    def test_no_evidence_timestamp_is_not_recent(self):
        assert not fpg.is_evidence_recent(0, threshold_seconds=600)
        assert not fpg.is_evidence_recent(None, threshold_seconds=600)

    def test_threshold_boundary(self):
        now = time.time()
        # Exactly at threshold should be considered recent (inclusive)
        assert fpg.is_evidence_recent(now - 599, threshold_seconds=600)
        # Past threshold is stale
        assert not fpg.is_evidence_recent(now - 601, threshold_seconds=600)

    def test_future_timestamp_clock_skew_not_recent(self):
        """Clock-skew defense: future timestamps must NOT count as recent."""
        now = time.time()
        assert not fpg.is_evidence_recent(now + 60, threshold_seconds=600)
        assert not fpg.is_evidence_recent(now + 3600, threshold_seconds=600)

    def test_invalid_timestamp_type_not_recent(self):
        assert not fpg.is_evidence_recent("not-a-number", threshold_seconds=600)
        assert not fpg.is_evidence_recent([1, 2, 3], threshold_seconds=600)


class TestDoSGuard:
    def test_long_prompt_truncated_still_finds_evidence(self):
        """Long prompts are truncated to MAX_PROMPT_LEN; bug-keyword in prefix still matches."""
        long_prompt = "bug detected " + "x" * 200_000
        start = time.time()
        result = fpg.detect_bug_evidence(long_prompt)
        elapsed = time.time() - start
        assert result, "expected match for 'bug' in prefix"
        assert elapsed < 0.5, f"DoS-guard too slow: {elapsed:.3f}s"

    def test_long_prompt_no_match_still_fast(self):
        """Pathological no-match input must not DoS due to backtracking."""
        long_prompt = "x" * 200_000
        start = time.time()
        result = fpg.detect_bug_evidence(long_prompt)
        elapsed = time.time() - start
        assert not result
        assert elapsed < 0.5, f"DoS-guard too slow: {elapsed:.3f}s"


# ---------------------------------------------------------------------------
# Subprocess Integration: UserPromptSubmit
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


class TestUserPromptSubmitEvent:
    def test_bug_keyword_in_prompt_updates_state(self, tmp_path):
        session_id = "test-fpg-prompt-bug"
        payload = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": session_id,
            "prompt": "fix the bug in the parser",
        }
        r = _run_hook(payload, tmp_path)
        assert r.returncode == 0
        # UserPromptSubmit never emits advisory — only updates state
        assert r.stdout.strip() == ""

        state_path = tmp_path / f".meta-state-{session_id}.json"
        assert state_path.exists()
        state = json.loads(state_path.read_text(encoding="utf-8"))
        ns = state.get("false_positive_guard", {})
        assert ns.get("last_evidence_seen_at"), f"timestamp missing: {ns}"
        assert ns.get("last_evidence_source") == "user_prompt"

    def test_neutral_prompt_does_not_set_evidence(self, tmp_path):
        session_id = "test-fpg-prompt-neutral"
        payload = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": session_id,
            "prompt": "please add a new feature for parsing",
        }
        r = _run_hook(payload, tmp_path)
        assert r.returncode == 0

        state_path = tmp_path / f".meta-state-{session_id}.json"
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding="utf-8"))
            ns = state.get("false_positive_guard", {})
            assert not ns.get("last_evidence_seen_at"), (
                f"evidence set for neutral prompt: {ns}"
            )


# ---------------------------------------------------------------------------
# Subprocess Integration: PreToolUse Edit
# ---------------------------------------------------------------------------


class TestPreToolUseEditAdvisory:
    def test_edit_without_recent_evidence_emits_advisory(self, tmp_path):
        session_id = "test-fpg-edit-no-evidence"
        payload = {
            "hook_event_name": "PreToolUse",
            "session_id": session_id,
            "tool_name": "Edit",
            "tool_input": {"file_path": "/some/file.py"},
        }
        r = _run_hook(payload, tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip(), "expected additionalContext output"
        out = json.loads(r.stdout.strip())
        ctx = out.get("additionalContext", "")
        assert (
            "confidence" in ctx.lower()
            or "evidence" in ctx.lower()
            or "beleg" in ctx.lower()
        )

    def test_edit_with_recent_evidence_passes_silent(self, tmp_path):
        session_id = "test-fpg-edit-with-evidence"
        # First, create evidence via UserPromptSubmit
        prompt_payload = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": session_id,
            "prompt": "there's a bug in the parser",
        }
        _run_hook(prompt_payload, tmp_path)

        # Then trigger PreToolUse Edit — should be silent because evidence is fresh
        edit_payload = {
            "hook_event_name": "PreToolUse",
            "session_id": session_id,
            "tool_name": "Edit",
            "tool_input": {"file_path": "/some/file.py"},
        }
        r = _run_hook(edit_payload, tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip() == "", f"unexpected output: {r.stdout!r}"

    def test_edit_with_non_edit_tool_passes(self, tmp_path):
        # Hook is registered with matcher: Edit, but defensively test other tool_name
        session_id = "test-fpg-non-edit-tool"
        payload = {
            "hook_event_name": "PreToolUse",
            "session_id": session_id,
            "tool_name": "Bash",  # not Edit
            "tool_input": {"command": "ls"},
        }
        r = _run_hook(payload, tmp_path)
        assert r.returncode == 0
        # Should not emit advisory for non-Edit tools (defensive)
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

    def test_missing_event_name_exits_0(self, tmp_path):
        # No hook_event_name → can't dispatch, exit 0 silent
        payload = {"session_id": "x", "prompt": "bug here"}
        r = _run_hook(payload, tmp_path)
        assert r.returncode == 0
        assert r.stdout.strip() == ""

    def test_advisory_json_valid_and_bounded(self, tmp_path):
        """Advisory JSON must parse cleanly and stay <2KB (UI-budget)."""
        session_id = "test-fpg-json-format"
        payload = {
            "hook_event_name": "PreToolUse",
            "session_id": session_id,
            "tool_name": "Edit",
            "tool_input": {"file_path": "/some/file.py"},
        }
        r = _run_hook(payload, tmp_path)
        assert r.returncode == 0
        out = json.loads(r.stdout.strip())
        assert "additionalContext" in out
        assert isinstance(out["additionalContext"], str)
        assert len(out["additionalContext"]) < 2000, "advisory too long for UI"

    def test_state_persistence_across_invocations(self, tmp_path):
        session_id = "test-fpg-persist"
        # First UserPromptSubmit with bug
        _run_hook(
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": session_id,
                "prompt": "bug in foo",
            },
            tmp_path,
        )
        # Second UserPromptSubmit (neutral) — should NOT clear evidence
        _run_hook(
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": session_id,
                "prompt": "okay let's continue",
            },
            tmp_path,
        )
        # PreToolUse Edit — should still see fresh evidence
        r = _run_hook(
            {
                "hook_event_name": "PreToolUse",
                "session_id": session_id,
                "tool_name": "Edit",
                "tool_input": {"file_path": "/x.py"},
            },
            tmp_path,
        )
        assert r.returncode == 0
        assert r.stdout.strip() == "", (
            "evidence should persist, advisory should NOT fire"
        )
