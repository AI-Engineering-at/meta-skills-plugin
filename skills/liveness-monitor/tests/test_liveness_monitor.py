"""Tests for liveness-monitor check.py.

Run with: cd skills/liveness-monitor && python -m pytest tests/ -v
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Add parent dir to path so we can import check
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check  # noqa: E402


@pytest.fixture
def fake_meta_skills_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a fake meta-skills root with self-improving/ subdir."""
    root = tmp_path / "meta-skills"
    (root / "self-improving").mkdir(parents=True)
    (root / ".claude" / "credentials").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(root))
    return root


def _write_heartbeat(root: Path, age_hours: float) -> Path:
    """Write heartbeat-state.md with mtime = now - age_hours."""
    heartbeat = root / "self-improving" / "heartbeat-state.md"
    heartbeat.write_text("# Self-Improving Heartbeat State\nlast_heartbeat: test\n")
    target_mtime = time.time() - (age_hours * 3600)
    os.utime(heartbeat, (target_mtime, target_mtime))
    return heartbeat


def test_live_case_under_24h(fake_meta_skills_root: Path) -> None:
    """heartbeat 1h old → status=live, exit=0."""
    _write_heartbeat(fake_meta_skills_root, age_hours=1)
    result = check.check_heartbeat(threshold_hours=24)
    assert result["status"] == "live"
    assert result["age_hours"] < 24
    assert result["threshold_hours"] == 24


def test_stale_case_48h(fake_meta_skills_root: Path) -> None:
    """heartbeat 48h old (between 24h and 7d) → status=stale."""
    _write_heartbeat(fake_meta_skills_root, age_hours=48)
    result = check.check_heartbeat(threshold_hours=24)
    assert result["status"] == "stale"
    assert 47 < result["age_hours"] < 49


def test_dead_case_over_7d(fake_meta_skills_root: Path) -> None:
    """heartbeat 30d old → status=dead."""
    _write_heartbeat(fake_meta_skills_root, age_hours=24 * 30)
    result = check.check_heartbeat(threshold_hours=24)
    assert result["status"] == "dead"
    assert result["age_hours"] > 24 * 7


def test_missing_case(fake_meta_skills_root: Path) -> None:
    """No heartbeat file → status=missing."""
    result = check.check_heartbeat(threshold_hours=24)
    assert result["status"] == "missing"
    assert result["last_modified"] is None
    assert "heartbeat-state.md" in result["heartbeat_path"]


def test_threshold_override(fake_meta_skills_root: Path) -> None:
    """heartbeat 12h old with threshold=6h → stale."""
    _write_heartbeat(fake_meta_skills_root, age_hours=12)
    result = check.check_heartbeat(threshold_hours=6)
    assert result["status"] == "stale"


def test_exit_codes_live(
    fake_meta_skills_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """main() returns 0 for live."""
    _write_heartbeat(fake_meta_skills_root, age_hours=1)
    rc = check.main(["--max-age-hours", "24"])
    assert rc == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["status"] == "live"


def test_exit_codes_stale(
    fake_meta_skills_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """main() returns 1 for stale."""
    _write_heartbeat(fake_meta_skills_root, age_hours=48)
    rc = check.main(["--max-age-hours", "24"])
    assert rc == 1


def test_exit_codes_dead(
    fake_meta_skills_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """main() returns 2 for dead."""
    _write_heartbeat(fake_meta_skills_root, age_hours=24 * 30)
    rc = check.main(["--max-age-hours", "24"])
    assert rc == 2


def test_exit_codes_missing(
    fake_meta_skills_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """main() returns 2 for missing."""
    rc = check.main([])
    assert rc == 2


def test_idempotency_dedup(
    fake_meta_skills_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Second alert within 24h should be deduped."""
    _write_heartbeat(fake_meta_skills_root, age_hours=48)
    payload = check.check_heartbeat()
    # Simulate first alert was recorded
    check.record_alert(fake_meta_skills_root, payload)
    assert check.already_alerted_recently(fake_meta_skills_root)


def test_idempotency_after_24h(fake_meta_skills_root: Path) -> None:
    """Alert from >24h ago should NOT trigger dedup."""
    state_file = fake_meta_skills_root / check.DEDUP_STATE_FILE
    state_file.parent.mkdir(parents=True, exist_ok=True)
    old_alert_time = (datetime.now(tz=timezone.utc) - timedelta(hours=25)).isoformat()
    state_file.write_text(
        json.dumps({"last_alert_iso": old_alert_time, "last_payload": {}})
    )
    assert not check.already_alerted_recently(fake_meta_skills_root)


def test_payload_format(fake_meta_skills_root: Path) -> None:
    """Output JSON has all required keys."""
    _write_heartbeat(fake_meta_skills_root, age_hours=1)
    result = check.check_heartbeat()
    for key in (
        "status",
        "heartbeat_path",
        "last_modified",
        "age_hours",
        "threshold_hours",
    ):
        assert key in result, f"Missing key: {key}"
