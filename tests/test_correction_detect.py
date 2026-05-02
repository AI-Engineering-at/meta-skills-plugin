"""Tests for hooks/correction-detect.py — detect_correction + severity logic.

Covers:
- DE+EN correction patterns (correction / frustration / stop)
- False-positive patterns ("nein danke", "ja oder nein", questions)
- Empty/short prompts
- S10 escalation at count >= 2
- Severity → context message building
- Integration: subprocess invocation with stdin JSON
"""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_FILE = REPO_ROOT / "hooks" / "correction-detect.py"

# Load dash-named module via importlib (same pattern as test_hardening_run)
sys.path.insert(0, str(REPO_ROOT / "hooks"))
_spec = importlib.util.spec_from_file_location("correction_detect", HOOK_FILE)
cd = importlib.util.module_from_spec(_spec)
sys.modules["correction_detect"] = cd
_spec.loader.exec_module(cd)


class TestDetectCorrectionStop:
    @pytest.mark.parametrize(
        "prompt",
        [
            "stop",
            "STOP",
            "Stopp!",
            "halt",
            "bitte halt das",
            "abbruch jetzt",
        ],
    )
    def test_stop_severity(self, prompt):
        severity, matched = cd.detect_correction(prompt)
        assert severity == "stop"
        assert matched


class TestDetectCorrectionGerman:
    @pytest.mark.parametrize(
        "prompt",
        [
            "nein, so nicht",
            "das ist falsch",
            "nicht so machen",
            "ich meinte eigentlich X",
            "ich will das anders",
            "andersrum bitte",
            "genau das gegenteil",
        ],
    )
    def test_german_corrections(self, prompt):
        severity, matched = cd.detect_correction(prompt)
        assert severity == "correction", f"failed for: {prompt}"
        assert matched


class TestDetectCorrectionEnglish:
    @pytest.mark.parametrize(
        "prompt",
        [
            "that's wrong",
            "no, that's not what I asked",
            "not what I asked for",
            "I said something else",
            "I meant the other thing",
            "you're doing it wrong",
            "that's incorrect",
        ],
    )
    def test_english_corrections(self, prompt):
        severity, matched = cd.detect_correction(prompt)
        assert severity == "correction", f"failed for: {prompt}"
        assert matched


class TestDetectFrustration:
    @pytest.mark.parametrize(
        "prompt",
        [
            "schon wieder der gleiche fehler",
            "immer noch nicht",
            "wie oft noch muss ich das sagen",
            "hab ich dir gesagt",
            "again the same thing",
            "already told you",
            "how many times do I have to say",
            "still not working",
            "same problem keeps happening",
        ],
    )
    def test_frustration_severity(self, prompt):
        severity, matched = cd.detect_correction(prompt)
        assert severity == "frustration", f"failed for: {prompt}"
        assert matched


class TestFalsePositives:
    @pytest.mark.parametrize(
        "prompt",
        [
            "nein danke",
            "nein, passt",
            "ja oder nein?",
            "entweder ja oder nein",
            "ist das wrong?",
            "what's wrong with X?",
            "was stimmt nicht mit Y?",
            "nicht so schlimm",
            "nicht so wichtig",
        ],
    )
    def test_false_positives_not_detected(self, prompt):
        severity, _ = cd.detect_correction(prompt)
        assert severity is None, f"false positive fired for: {prompt}"


class TestEdgeCases:
    def test_empty_returns_none(self):
        assert cd.detect_correction("") == (None, None)

    def test_too_short_returns_none(self):
        assert cd.detect_correction("no") == (None, None)

    def test_none_input_returns_none(self):
        assert cd.detect_correction(None) == (None, None)

    def test_unrelated_prompt_returns_none(self):
        severity, _ = cd.detect_correction(
            "Bitte analysiere diese Datei und erkläre den Code."
        )
        assert severity is None

    def test_mixed_case_still_matches(self):
        severity, _ = cd.detect_correction("NEIN, das ist FALSCH")
        assert severity == "correction"

    def test_question_with_wrong_is_false_positive(self):
        # "is that wrong?" asks a diagnostic, not correcting
        severity, _ = cd.detect_correction("is that wrong?")
        assert severity is None


class TestScopeCorrections:
    @pytest.mark.parametrize(
        "prompt",
        [
            "bleib beim thema",
            "nicht abschweifen",
            "fokus bitte",
            "focus on the main task",
            "only do the one thing",
            "one thing at a time",
        ],
    )
    def test_scope_corrections(self, prompt):
        severity, _ = cd.detect_correction(prompt)
        assert severity == "correction", f"failed for: {prompt}"


class TestDetectCorrectionMixedLanguage:
    """Mixed DE+EN prompts (Devstral external review finding #1).

    Real-world user input often mixes German and English mid-sentence.
    The detector must handle these without false negatives.
    """

    @pytest.mark.parametrize(
        "prompt",
        [
            "nein, that's wrong",
            "no, das ist falsch",
            "stop, mach das anders",
            "halt! wrong direction",
            "actually I meant ich will X",
            "I said nicht so",
            "you're doing it falsch",
            "das ist incorrect",
        ],
    )
    def test_mixed_correction_or_stop_severity(self, prompt):
        """Any of correction/stop severity is acceptable — both are valid."""
        severity, matched = cd.detect_correction(prompt)
        assert severity in ("correction", "stop"), (
            f"expected correction/stop severity for mixed-language prompt "
            f"{prompt!r}, got {severity!r}"
        )
        assert matched is not None

    @pytest.mark.parametrize(
        "prompt",
        [
            "wie oft noch do I have to say this",
            "schon wieder the same problem",
            "already told you du sollst das anders machen",
            "immer noch not working",
        ],
    )
    def test_mixed_frustration_severity(self, prompt):
        severity, _ = cd.detect_correction(prompt)
        assert severity == "frustration", (
            f"expected frustration for mixed-language {prompt!r}, got {severity!r}"
        )

    @pytest.mark.parametrize(
        "prompt",
        [
            # Mixed-language questions should NOT fire (end with ?)
            "is das wrong?",
            "was ist incorrect hier?",
            # Polite mixed-language decline
            "nein thanks, das passt schon",
            # Diagnostic mixed
            "what's falsch with this code?",
        ],
    )
    def test_mixed_false_positives_not_detected(self, prompt):
        severity, _ = cd.detect_correction(prompt)
        assert severity is None, (
            f"false positive fired for mixed-language {prompt!r}: {severity!r}"
        )

    def test_mixed_preserves_severity_priority(self):
        """When both stop and correction patterns present, stop wins."""
        # "stop" is a stop-severity pattern; "falsch" is correction-severity.
        # Stop patterns come FIRST in the pattern list, so stop should win.
        severity, _ = cd.detect_correction("stop, das ist falsch")
        assert severity == "stop"


class TestIntegrationSubprocess:
    def test_invoke_with_stop_signal(self, tmp_path):
        payload = {
            "prompt": "stop das jetzt bitte",
            "session_id": "test-session-1",
        }
        env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
        r = subprocess.run(
            [sys.executable, str(HOOK_FILE)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert r.returncode == 0
        out = json.loads(r.stdout.strip())
        assert "additionalContext" in out
        assert "STOP" in out["additionalContext"].upper()

    def test_invoke_with_correction(self, tmp_path):
        payload = {
            "prompt": "nein das ist falsch",
            "session_id": "test-session-2",
        }
        env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
        r = subprocess.run(
            [sys.executable, str(HOOK_FILE)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert r.returncode == 0
        out = json.loads(r.stdout.strip())
        assert (
            "CORRECTION" in out["additionalContext"].upper()
            or "FRUSTRATION" in out["additionalContext"].upper()
        )

    def test_invoke_with_no_correction_exits_silently(self, tmp_path):
        payload = {"prompt": "hallo wie geht's", "session_id": "test-session-3"}
        env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
        r = subprocess.run(
            [sys.executable, str(HOOK_FILE)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert r.returncode == 0
        assert r.stdout.strip() == ""  # no additionalContext emitted

    def test_s10_escalation_after_2_corrections(self, tmp_path):
        """Two corrections same session → S10 warning in context + state persisted."""
        env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
        session_id = "test-s10-escalation"

        # First correction
        subprocess.run(
            [sys.executable, str(HOOK_FILE)],
            input=json.dumps({"prompt": "nein, falsch", "session_id": session_id}),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        # Second correction
        r2 = subprocess.run(
            [sys.executable, str(HOOK_FILE)],
            input=json.dumps({"prompt": "immer noch falsch", "session_id": session_id}),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert r2.returncode == 0
        out = json.loads(r2.stdout.strip())
        assert "S10" in out["additionalContext"]

        # State-file assertion (audit 7.7→8.5: close internal audit gap)
        # SessionState writes to STATE_DIR/.meta-state-{session_id}.json
        state_path = tmp_path / f".meta-state-{session_id}.json"
        assert state_path.exists(), f"state file missing at {state_path}"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        cd_state = state.get("correction_detect", {})
        assert cd_state.get("correction_count", 0) >= 2, (
            f"expected correction_count>=2 after 2 corrections, got {cd_state}"
        )
        assert cd_state.get("last_severity") is not None

    def test_invalid_json_stdin_exits_0(self, tmp_path):
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

    def test_missing_prompt_key_exits_0(self, tmp_path):
        env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
        r = subprocess.run(
            [sys.executable, str(HOOK_FILE)],
            input=json.dumps({"session_id": "x"}),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert r.returncode == 0
        assert r.stdout.strip() == ""
