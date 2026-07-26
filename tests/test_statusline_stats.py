"""Tests for statusline_lib.prune_stats + compute_sigma.

These cover the stats-file logic extracted from statusline.py (90-day
prune, baseline-backfill protection, sigma aggregation with declared
session counts).

The extraction itself is the fix for earlier C-CLAIM02 related drift:
the prune logic used to live inline in statusline.py and silently
dropped the baseline-backfill entry when old code was deployed to
cache. Tests here lock in the prune exception.
"""

import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from statusline_lib import (  # noqa: E402
    BASELINE_KEY,
    BASELINE_PREFIX,
    MIN_RATE_BASIS_DAYS,
    compute_dynamic_baseline,
    compute_sigma,
    prune_stats,
)

DAY = 86400.0


class TestPruneStats:
    def test_empty_stats_returns_empty(self):
        assert prune_stats({}, cutoff_ts=1000.0) == {}

    def test_fresh_entry_survives(self):
        stats = {"s1": {"ts": 2000.0, "cost": 1.0}}
        assert prune_stats(stats, cutoff_ts=1000.0) == stats

    def test_stale_entry_dropped(self):
        stats = {"s1": {"ts": 500.0, "cost": 1.0}}
        assert prune_stats(stats, cutoff_ts=1000.0) == {}

    def test_baseline_backfill_survives_even_when_stale(self):
        stats = {"baseline-backfill": {"ts": 500.0, "cost": 100.0, "sessions": 3000}}
        out = prune_stats(stats, cutoff_ts=1000.0)
        assert "baseline-backfill" in out

    def test_baseline_prefix_any_name_survives(self):
        # baseline-2025 or baseline-opus-migration etc. all survive.
        stats = {"baseline-2025": {"ts": 1.0, "cost": 0}, "s1": {"ts": 1.0}}
        out = prune_stats(stats, cutoff_ts=1000.0)
        assert "baseline-2025" in out
        assert "s1" not in out

    def test_missing_ts_treated_as_stale(self):
        stats = {"s1": {"cost": 1.0}}  # no 'ts' key
        assert prune_stats(stats, cutoff_ts=1000.0) == {}

    def test_null_ts_treated_as_stale(self):
        stats = {"s1": {"ts": None, "cost": 1.0}}
        assert prune_stats(stats, cutoff_ts=1000.0) == {}

    def test_does_not_mutate_input(self):
        stats = {"s1": {"ts": 500.0}, "baseline-backfill": {"ts": 500.0, "sessions": 5}}
        original = {k: dict(v) for k, v in stats.items()}
        prune_stats(stats, cutoff_ts=1000.0)
        assert stats == original

    def test_boundary_exactly_at_cutoff_is_dropped(self):
        # Entry ts == cutoff must be dropped (> cutoff is the contract).
        # Locks in the pre-extraction inline semantics from statusline.py
        # (`v.get("ts", 0) > cutoff`) so the refactor is provably behavior-
        # preserving. The new lib is a strict superset: it additionally
        # handles `ts == None` without crashing (old code would TypeError).
        stats = {"s1": {"ts": 1000.0}}
        assert prune_stats(stats, cutoff_ts=1000.0) == {}

    def test_boundary_one_second_after_cutoff_survives(self):
        stats = {"s1": {"ts": 1001.0}}
        assert prune_stats(stats, cutoff_ts=1000.0) == stats

    def test_mixed_old_new_baseline(self):
        stats = {
            "old": {"ts": 100.0, "cost": 1},
            "new": {"ts": 2000.0, "cost": 2},
            "baseline-backfill": {"ts": 50.0, "cost": 500, "sessions": 3000},
        }
        out = prune_stats(stats, cutoff_ts=1000.0)
        assert "old" not in out
        assert "new" in out
        assert "baseline-backfill" in out


class TestComputeSigma:
    def test_empty_stats(self):
        cost, tokens, sessions = compute_sigma({})
        assert cost == 0
        assert tokens == 0
        assert sessions == 0

    def test_single_session_no_baseline(self):
        stats = {"s1": {"cost": 1.5, "tokens": 100, "ts": 1.0}}
        cost, tokens, sessions = compute_sigma(stats)
        assert cost == 1.5
        assert tokens == 100
        assert sessions == 1

    def test_multiple_sessions_no_baseline(self):
        stats = {
            "s1": {"cost": 1.0, "tokens": 100},
            "s2": {"cost": 2.0, "tokens": 200},
            "s3": {"cost": 3.0, "tokens": 300},
        }
        cost, tokens, sessions = compute_sigma(stats)
        assert cost == 6.0
        assert tokens == 600
        assert sessions == 3

    def test_baseline_declared_sessions_replaces_self_count(self):
        stats = {
            BASELINE_KEY: {"cost": 1000.0, "tokens": 50_000_000, "sessions": 3000},
        }
        cost, tokens, sessions = compute_sigma(stats)
        assert cost == 1000.0
        assert tokens == 50_000_000
        # len(stats)=1, minus 1 for baseline, plus declared 3000
        assert sessions == 3000

    def test_baseline_plus_real_sessions(self):
        stats = {
            BASELINE_KEY: {"cost": 25000.0, "tokens": 545_000_000, "sessions": 3800},
            "s1": {"cost": 0.5, "tokens": 1000},
            "s2": {"cost": 0.25, "tokens": 500},
        }
        cost, tokens, sessions = compute_sigma(stats)
        assert cost == 25000.75
        assert tokens == 545_001_500
        # len(stats)=3 - 1 (baseline) + 3800 = 3802
        assert sessions == 3802

    def test_baseline_without_sessions_field_contributes_zero(self):
        # If a baseline entry exists but declares no `sessions`, it takes
        # the place of one real session without adding any.
        stats = {BASELINE_KEY: {"cost": 10.0, "tokens": 1000}}
        _, _, sessions = compute_sigma(stats)
        assert sessions == 0  # 1 - 1 + 0

    def test_none_values_handled_as_zero(self):
        stats = {"s1": {"cost": None, "tokens": None}}
        cost, tokens, sessions = compute_sigma(stats)
        assert cost == 0
        assert tokens == 0
        assert sessions == 1

    def test_missing_keys_handled_as_zero(self):
        stats = {"s1": {}, "s2": {"cost": 1.0}}
        cost, tokens, sessions = compute_sigma(stats)
        assert cost == 1.0
        assert tokens == 0
        assert sessions == 2

    def test_only_baseline_without_sessions_field(self):
        # baseline-backfill treated specially even without declared count.
        stats = {BASELINE_KEY: {"cost": 100.0, "tokens": 1000}}
        _, _, sessions = compute_sigma(stats)
        assert sessions == 0

    def test_non_backfill_baseline_is_plain_session(self):
        # "baseline-*" prefix survives pruning but only "baseline-backfill"
        # gets the special session-count treatment.
        stats = {"baseline-other": {"cost": 1.0, "tokens": 100}}
        _, _, sessions = compute_sigma(stats)
        assert sessions == 1  # counted as regular session


class TestConstants:
    def test_baseline_prefix_matches_key(self):
        assert BASELINE_KEY.startswith(BASELINE_PREFIX)

    def test_baseline_key_is_baseline_backfill(self):
        assert BASELINE_KEY == "baseline-backfill"


class TestComputeDynamicBaseline:
    """No manually-seeded baseline entry — computed fresh every run from
    whatever real local data exists, so it works on any machine logged into
    the same account. Must never extrapolate from too little real data
    (found 2026-07-26: a bare max(1.0, ...) day floor turned <2h of real
    data into a wildly inflated multi-month estimate)."""

    def test_no_real_entries_returns_zero(self):
        assert compute_dynamic_baseline({}, account_created_ts=1000.0, now_ts=2000.0) == (0.0, 0.0)

    def test_no_account_created_ts_returns_zero(self):
        stats = {"s1": {"cost": 10.0, "tokens": 100, "ts": 1000.0}}
        assert compute_dynamic_baseline(stats, account_created_ts=None, now_ts=1000.0 + 10 * DAY) == (0.0, 0.0)

    def test_account_created_after_earliest_real_returns_zero(self):
        stats = {"s1": {"cost": 10.0, "tokens": 100, "ts": 1000.0}}
        assert compute_dynamic_baseline(stats, account_created_ts=2000.0, now_ts=1000.0 + 10 * DAY) == (0.0, 0.0)

    def test_real_span_below_minimum_returns_zero(self):
        now = 1_000_000.0
        earliest_real = now - (MIN_RATE_BASIS_DAYS - 0.5) * DAY  # just under the threshold
        stats = {"s1": {"cost": 255.0, "tokens": 1_774_355, "ts": earliest_real}}
        assert compute_dynamic_baseline(stats, account_created_ts=earliest_real - 200 * DAY, now_ts=now) == (0.0, 0.0)

    def test_real_span_above_minimum_extrapolates(self):
        now = 1_000_000.0
        earliest_real = now - (MIN_RATE_BASIS_DAYS + 7) * DAY  # comfortably over threshold
        account_created = earliest_real - 20 * DAY
        stats = {"s1": {"cost": 100.0, "tokens": 1000, "ts": earliest_real}}
        cost, tokens = compute_dynamic_baseline(stats, account_created_ts=account_created, now_ts=now)
        assert cost > 0
        assert tokens > 0
        # Sanity: gap (20d) is roughly 2x the real span (10d) -> roughly 2x the real totals.
        real_span_days = (now - earliest_real) / DAY
        expected_cost = (100.0 / real_span_days) * 20
        assert cost == pytest.approx(expected_cost, rel=1e-9)

    def test_baseline_entries_excluded_from_rate_calculation(self):
        now = 1_000_000.0
        earliest_real = now - (MIN_RATE_BASIS_DAYS + 1) * DAY
        stats = {
            "s1": {"cost": 50.0, "tokens": 500, "ts": earliest_real},
            BASELINE_KEY: {"cost": 999999.0, "tokens": 999999, "ts": 0.0},
        }
        cost, _ = compute_dynamic_baseline(stats, account_created_ts=earliest_real - 5 * DAY, now_ts=now)
        # If the baseline entry leaked into the rate calc this would be huge.
        assert cost < 1000
