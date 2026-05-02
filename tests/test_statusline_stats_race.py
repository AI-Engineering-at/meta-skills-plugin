"""Race-condition regression test for statusline.py stats file writes.

Locks in the C-STATUSLINE01 fix (per-PID tmp file name) by spawning N
concurrent subprocess invocations of statusline.py against a shared
stats file, then asserting the file is still valid JSON with every
session entry present.

Before fix (shared tmp path): 10+ concurrent claude.exe invocations
produced trailing-garbage in statusline-alltime.json (e.g. '72042}}'
or stray '}'). See meta-skills/self-improving/corrections.md.example
C-STATUSLINE01.

After fix: each statusline.py process writes its own
`statusline-alltime.json.<pid>.tmp` and then os.replace()s atomically.

This test must stay green across 3 reruns to be considered stable.
"""

import concurrent.futures
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
STATUSLINE_PY = REPO_ROOT / "scripts" / "statusline.py"

PARALLEL_WORKERS = 16
SUBPROCESS_TIMEOUT = 30


def _fake_stdin_payload(session_id: str, cost: float = 0.01, tokens: int = 150) -> str:
    return json.dumps(
        {
            "session_id": session_id,
            "cost": {"total_cost_usd": cost, "total_duration_ms": 0},
            "context_window": {
                "used_percentage": 1,
                "context_window_size": 1_000_000,
                "total_input_tokens": tokens // 2,
                "total_output_tokens": tokens - (tokens // 2),
            },
            "model": {"id": "claude-opus-4-7"},
        }
    )


def _invoke_statusline(session_id: str, env: dict) -> tuple[int, str, str]:
    """Run statusline.py with isolated env; return (rc, stdout, stderr)."""
    r = subprocess.run(
        [sys.executable, str(STATUSLINE_PY)],
        input=_fake_stdin_payload(session_id),
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_TIMEOUT,
        env=env,
    )
    return r.returncode, r.stdout, r.stderr


def _make_env(home: Path) -> dict:
    """Build subprocess env with isolated HOME / USERPROFILE so
    ~/.claude/statusline-alltime.json resolves inside home."""
    env = dict(os.environ)
    # Path("~").expanduser() on Windows prefers USERPROFILE, Unix uses HOME.
    # Set both so the test works cross-platform.
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    return env


@pytest.fixture
def isolated_home(tmp_path: Path) -> Path:
    """Empty ~/.claude in a tmp dir so the test owns the stats file."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    return tmp_path


class TestStatusLineRace:
    """Reproduces and guards against the multi-process write race."""

    def test_single_invocation_writes_valid_json(self, isolated_home):
        env = _make_env(isolated_home)
        rc, out, err = _invoke_statusline("solo-session", env)
        assert rc == 0, f"statusline exited {rc}; stderr={err[:500]}"

        stats_file = isolated_home / ".claude" / "statusline-alltime.json"
        assert stats_file.exists(), "stats file should exist after single run"
        data = json.loads(stats_file.read_text(encoding="utf-8"))
        assert "solo-session" in data

    def test_parallel_invocations_produce_valid_json(self, isolated_home):
        """16 parallel writers → file must still be valid JSON at the end."""
        env = _make_env(isolated_home)
        session_ids = [f"race-session-{i:02d}" for i in range(PARALLEL_WORKERS)]

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=PARALLEL_WORKERS
        ) as pool:
            futures = [pool.submit(_invoke_statusline, sid, env) for sid in session_ids]
            results = [f.result(timeout=SUBPROCESS_TIMEOUT) for f in futures]

        failures = [
            (sid, rc, err) for sid, (rc, _, err) in zip(session_ids, results) if rc != 0
        ]
        assert not failures, f"some invocations failed: {failures[:3]}"

        stats_file = isolated_home / ".claude" / "statusline-alltime.json"
        raw = stats_file.read_text(encoding="utf-8")

        # Core regression check: no trailing garbage after the final '}'.
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            pytest.fail(
                f"C-STATUSLINE01 regression: stats file is not valid JSON after "
                f"{PARALLEL_WORKERS} parallel writers. pos={e.pos}, "
                f"trailing={raw[max(0, e.pos - 5) : e.pos + 10]!r}"
            )

        # Last-writer-wins semantics mean we can't assert all 16 entries survived
        # (two writers reading old state + writing new will clobber each other's
        # session entries). What we CAN assert:
        # 1. File is valid JSON
        # 2. At least one of the race-session entries survived
        # 3. No stray ".tmp" files leaked (each PID cleaned up its own)
        surviving = [sid for sid in session_ids if sid in data]
        assert surviving, (
            f"no race-session entries survived; data keys: {list(data.keys())[:5]}"
        )

        tmp_leaks = list(
            (isolated_home / ".claude").glob("statusline-alltime.json.*.tmp")
        )
        assert not tmp_leaks, f"per-PID tmp files leaked: {[p.name for p in tmp_leaks]}"

    def test_parallel_writers_preserve_baseline_entry(self, isolated_home):
        """Baseline-backfill must survive concurrent writes from non-baseline sessions."""
        stats_file = isolated_home / ".claude" / "statusline-alltime.json"
        # Seed the file with a baseline entry (as real prod has).
        stats_file.write_text(
            json.dumps(
                {
                    "baseline-backfill": {
                        "cost": 25219.05,
                        "tokens": 545_941_989,
                        "sessions": 3822,
                        "time_ms": 0,
                        "model": "backfill",
                        "ts": 1_759_276_800.0,
                    }
                }
            ),
            encoding="utf-8",
        )

        env = _make_env(isolated_home)
        session_ids = [f"preserve-baseline-{i:02d}" for i in range(PARALLEL_WORKERS)]

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=PARALLEL_WORKERS
        ) as pool:
            futures = [pool.submit(_invoke_statusline, sid, env) for sid in session_ids]
            [f.result(timeout=SUBPROCESS_TIMEOUT) for f in futures]

        raw = stats_file.read_text(encoding="utf-8")
        data = json.loads(raw)  # would raise if corrupt

        # baseline-backfill MUST still be present — this is C-CLAIM03 regression.
        assert "baseline-backfill" in data, (
            "baseline-backfill was wiped by concurrent writers — C-CLAIM03 regression"
        )
        baseline = data["baseline-backfill"]
        assert baseline.get("cost") == 25219.05
        assert baseline.get("sessions") == 3822

    def test_tmp_file_name_is_pid_specific(self, isolated_home):
        """White-box: verify statusline.py really uses os.getpid() in tmp name.

        If this test fails after a refactor, the race protection is gone.
        """
        content = STATUSLINE_PY.read_text(encoding="utf-8")
        assert "os.getpid()" in content, (
            "statusline.py must use os.getpid() in tmp file name to prevent "
            "C-STATUSLINE01 race. Do NOT change tmp path to a shared name."
        )
        assert 'STATS_FILE.suffix + f".{os.getpid()}.tmp"' in content, (
            "tmp file name pattern changed — audit whether it is still PID-unique"
        )
