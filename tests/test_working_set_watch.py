"""Tests for hooks/working-set-watch.py — Working-Set ohne Versionierung Mitigation.

SessionStart hook. Scans Downloads-style inboxes for strategy/concept/decision
files older than threshold (default: 7 days warn, 30 days critical), emits
advisory with migration suggestion (zeroth/decisions/ or zeroth/concepts/).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_FILE = REPO_ROOT / "hooks" / "working-set-watch.py"

sys.path.insert(0, str(REPO_ROOT / "hooks"))
_spec = importlib.util.spec_from_file_location("working_set_watch", HOOK_FILE)
wsw = importlib.util.module_from_spec(_spec)
sys.modules["working_set_watch"] = wsw
_spec.loader.exec_module(wsw)


# ---------------------------------------------------------------------------
# Pure-Function: filename pattern matching
# ---------------------------------------------------------------------------


class TestIsStrategyFile:
    def test_action_plan(self):
        assert wsw.is_strategy_file("Action_Plan_v1.0_post-session.md")
        assert wsw.is_strategy_file("Action_Plan_v2.md")

    def test_dec_records(self):
        assert wsw.is_strategy_file("DEC-001-naming-collision.md")
        assert wsw.is_strategy_file("DEC-042-foo.md")

    def test_concept_files(self):
        assert wsw.is_strategy_file("Zeroth_Concept_Update_v2026-04.md")
        assert wsw.is_strategy_file("Lineage_Engine_Concept_v0.1.md")
        assert wsw.is_strategy_file("Compliance_Pilot_Annex_IV_v0.1.md")

    def test_module_specs(self):
        assert wsw.is_strategy_file("M08_TTT-SI_Mini-Spec.md")
        assert wsw.is_strategy_file("M01-architecture.md")

    def test_neutral_files_not_matched(self):
        assert not wsw.is_strategy_file("README.md")
        assert not wsw.is_strategy_file("notes.txt")
        assert not wsw.is_strategy_file("photo.png")
        assert not wsw.is_strategy_file("Setup-v1.exe")
        assert not wsw.is_strategy_file("debug-log.json")
        assert not wsw.is_strategy_file("ChatGPT Image.png")

    def test_extension_filter(self):
        # Only .md / .py / .yaml / .yml / .json
        assert wsw.is_strategy_file("Action_Plan.md")
        assert wsw.is_strategy_file("DEC-001.yaml")
        assert not wsw.is_strategy_file("Action_Plan.exe")
        assert not wsw.is_strategy_file("DEC-001.png")


# ---------------------------------------------------------------------------
# Pure-Function: severity classification
# ---------------------------------------------------------------------------


class TestClassifyAge:
    def test_fresh(self):
        assert wsw.classify_age_days(0) == "ok"
        assert wsw.classify_age_days(6) == "ok"

    def test_warn(self):
        assert wsw.classify_age_days(7) == "warn"
        assert wsw.classify_age_days(29) == "warn"

    def test_critical(self):
        assert wsw.classify_age_days(30) == "critical"
        assert wsw.classify_age_days(365) == "critical"


# ---------------------------------------------------------------------------
# scan_inbox — lists stale strategy files
# ---------------------------------------------------------------------------


class TestScanInbox:
    def test_no_inbox_returns_empty(self, tmp_path):
        assert wsw.scan_inbox(str(tmp_path / "nonexistent")) == []

    def test_empty_inbox(self, tmp_path):
        assert wsw.scan_inbox(str(tmp_path)) == []

    def test_neutral_files_skipped(self, tmp_path):
        # File matches neither pattern nor extension whitelist
        (tmp_path / "Setup.exe").write_bytes(b"x")
        (tmp_path / "photo.png").write_bytes(b"x")
        # Old enough to be flagged if it matched
        old_time = time.time() - (10 * 86400)
        for f in tmp_path.iterdir():
            os.utime(f, (old_time, old_time))
        assert wsw.scan_inbox(str(tmp_path)) == []

    def test_strategy_file_recent_skipped(self, tmp_path):
        f = tmp_path / "Action_Plan_v1.0.md"
        f.write_text("plan", encoding="utf-8")
        # Default mtime = now → not stale
        assert wsw.scan_inbox(str(tmp_path)) == []

    def test_strategy_file_old_flagged(self, tmp_path):
        f = tmp_path / "DEC-099-test.md"
        f.write_text("decision", encoding="utf-8")
        old_time = time.time() - (10 * 86400)  # 10 days
        os.utime(f, (old_time, old_time))
        results = wsw.scan_inbox(str(tmp_path))
        assert len(results) == 1
        assert results[0]["name"] == "DEC-099-test.md"
        assert results[0]["age_days"] >= 9
        assert results[0]["severity"] == "warn"

    def test_critical_age_classified(self, tmp_path):
        f = tmp_path / "Lineage_Concept_v2.md"
        f.write_text("c", encoding="utf-8")
        old_time = time.time() - (45 * 86400)  # 45 days
        os.utime(f, (old_time, old_time))
        results = wsw.scan_inbox(str(tmp_path))
        assert len(results) == 1
        assert results[0]["severity"] == "critical"


# ---------------------------------------------------------------------------
# Subprocess Integration
# ---------------------------------------------------------------------------


def _run_hook(
    payload: dict, tmp_path: Path, inbox_override=None
) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path)}
    if inbox_override is not None:
        env["WORKING_SET_INBOXES"] = ",".join(inbox_override)
    return subprocess.run(
        [sys.executable, str(HOOK_FILE)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )


class TestSessionStartIntegration:
    def test_clean_inbox_silent(self, tmp_path):
        inbox = tmp_path / "clean-inbox"
        inbox.mkdir()
        payload = {"hook_event_name": "SessionStart", "session_id": "test-wsw-clean"}
        r = _run_hook(payload, tmp_path, inbox_override=[str(inbox)])
        assert r.returncode == 0
        assert r.stdout.strip() == ""

    def test_stale_strategy_file_emits_advisory(self, tmp_path):
        inbox = tmp_path / "downloads"
        inbox.mkdir()
        f = inbox / "Action_Plan_v1.0.md"
        f.write_text("plan", encoding="utf-8")
        old_time = time.time() - (10 * 86400)
        os.utime(f, (old_time, old_time))

        payload = {"hook_event_name": "SessionStart", "session_id": "test-wsw-stale"}
        r = _run_hook(payload, tmp_path, inbox_override=[str(inbox)])
        assert r.returncode == 0
        out = json.loads(r.stdout.strip())
        ctx = out.get("additionalContext", "")
        assert "Action_Plan_v1.0.md" in ctx
        assert (
            "zeroth" in ctx.lower()
            or "migration" in ctx.lower()
            or "decisions" in ctx.lower()
        )


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_non_session_start_event_silent(self, tmp_path):
        payload = {"hook_event_name": "UserPromptSubmit", "session_id": "x"}
        r = _run_hook(payload, tmp_path, inbox_override=[])
        assert r.returncode == 0
        assert r.stdout.strip() == ""

    def test_invalid_json_exits_0(self, tmp_path):
        env = {
            **os.environ,
            "CLAUDE_PLUGIN_DATA": str(tmp_path),
            "WORKING_SET_INBOXES": "",
        }
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
        env = {
            **os.environ,
            "CLAUDE_PLUGIN_DATA": str(tmp_path),
            "WORKING_SET_INBOXES": "",
        }
        r = subprocess.run(
            [sys.executable, str(HOOK_FILE)],
            input="",
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert r.returncode == 0
