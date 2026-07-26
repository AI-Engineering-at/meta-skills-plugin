"""Regression test for the Sigma-token accumulator in statusline.py.

context_window.total_input/output_tokens is a snapshot of the CURRENT
context window, not cumulative session throughput — it resets on /compact.
Before this fix, statusline-alltime.json overwrote "tokens" with that raw
snapshot on every invocation, silently losing everything before the last
reset (found in the 2026-07-26 token-usage audit: local statusline-alltime.json
undercounted real transcript totals for long/compacted sessions).

The fix treats the raw snapshot as a monotonic counter and detects
wraparound (new raw < previous raw) as a reset, folding the pre-reset peak
into a persisted "tokens_baseline" so "tokens" is the true cumulative value.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATUSLINE_PY = REPO_ROOT / "scripts" / "statusline.py"
SUBPROCESS_TIMEOUT = 30


def _fake_stdin_payload(session_id: str, total_input_tokens: int, cost: float = 1.0) -> str:
    return json.dumps(
        {
            "session_id": session_id,
            "cost": {"total_cost_usd": cost, "total_duration_ms": 0},
            "context_window": {
                "used_percentage": 1,
                "context_window_size": 1_000_000,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": 0,
            },
            "model": {"id": "claude-sonnet-5"},
        }
    )


def _invoke_statusline(session_id: str, total_input_tokens: int, env: dict) -> None:
    r = subprocess.run(
        [sys.executable, str(STATUSLINE_PY)],
        input=_fake_stdin_payload(session_id, total_input_tokens),
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_TIMEOUT,
        env=env,
    )
    assert r.returncode == 0, f"statusline exited {r.returncode}; stderr={r.stderr[:500]}"


def _make_env(home: Path) -> dict:
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    return env


def _read_stats(home: Path) -> dict:
    stats_file = home / ".claude" / "statusline-alltime.json"
    return json.loads(stats_file.read_text(encoding="utf-8"))


class TestTokenAccumulator:
    def test_monotonic_growth_no_reset(self, tmp_path):
        """Normal session growth: tokens tracks the raw snapshot, baseline stays 0."""
        home = tmp_path
        (home / ".claude").mkdir(parents=True)
        env = _make_env(home)

        _invoke_statusline("growth-session", 1000, env)
        _invoke_statusline("growth-session", 5000, env)

        entry = _read_stats(home)["growth-session"]
        assert entry["tokens"] == 5000
        assert entry["tokens_baseline"] == 0
        assert entry["tokens_raw"] == 5000

    def test_compact_reset_is_folded_into_baseline(self, tmp_path):
        """A /compact-style drop must not lose the pre-reset peak."""
        home = tmp_path
        (home / ".claude").mkdir(parents=True)
        env = _make_env(home)

        _invoke_statusline("compact-session", 1000, env)
        _invoke_statusline("compact-session", 8000, env)  # peak before compact
        _invoke_statusline("compact-session", 500, env)  # /compact reset
        _invoke_statusline("compact-session", 800, env)  # growth resumes post-reset

        entry = _read_stats(home)["compact-session"]
        # Naive overwrite would show 800 here, losing the 8000-token peak.
        assert entry["tokens"] == 8000 + 800
        assert entry["tokens_baseline"] == 8000
        assert entry["tokens_raw"] == 800

    def test_legacy_entry_without_baseline_fields_migrates_without_loss(self, tmp_path):
        """Pre-fix entries only have a flat 'tokens' int; must upgrade cleanly."""
        home = tmp_path
        (home / ".claude").mkdir(parents=True)
        stats_file = home / ".claude" / "statusline-alltime.json"
        stats_file.write_text(
            json.dumps(
                {"legacy-session": {"cost": 1.0, "tokens": 3000, "time_ms": 0, "model": "x", "ts": time.time()}}
            ),
            encoding="utf-8",
        )
        env = _make_env(home)

        # A drop below the legacy "tokens" value must be treated as a reset
        # against that legacy value, not silently overwrite it.
        _invoke_statusline("legacy-session", 200, env)

        entry = _read_stats(home)["legacy-session"]
        assert entry["tokens"] == 3000 + 200
        assert entry["tokens_baseline"] == 3000
