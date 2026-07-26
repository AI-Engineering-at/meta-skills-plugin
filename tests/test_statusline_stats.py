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
    assumption,
    compute_sigma,
    money,
    prune_stats,
    read_session_usage,
    read_usage_agg,
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



class TestReadUsageAgg:
    """Fehlendes/kaputtes Aggregat muss ``None`` liefern — nicht 0.

    Eine 0 waere eine Behauptung ("kein Verbrauch"), die Datei fehlt aber
    einfach nur. Genau diese Verwechslung (leeres Feld = Datenquelle
    unbrauchbar bzw. = null) war eine der vier Ursachen am 2026-07-26.
    """

    def test_missing_file(self, tmp_path):
        assert read_usage_agg(tmp_path / "weg.json") is None

    def test_malformed_json(self, tmp_path):
        p = tmp_path / "a.json"
        p.write_text("{kaputt", encoding="utf-8")
        assert read_usage_agg(p) is None

    def test_without_stand_rejected(self, tmp_path):
        p = tmp_path / "a.json"
        p.write_text('{"alltime": {"tokens_all": 5}}', encoding="utf-8")
        assert read_usage_agg(p) is None

    def test_zero_tokens_is_unknown_not_zero(self, tmp_path):
        p = tmp_path / "a.json"
        p.write_text('{"stand": "2026-07-26T00:00:00+00:00", "alltime": {"tokens_all": 0}}',
                     encoding="utf-8")
        assert read_usage_agg(p) is None

    def test_valid(self, tmp_path):
        p = tmp_path / "a.json"
        p.write_text('{"stand": "2026-07-26T00:00:00+00:00",'
                     ' "alltime": {"tokens_all": 44500000000, "saved_usd": 42774.0}}',
                     encoding="utf-8")
        agg = read_usage_agg(p)
        assert agg is not None
        assert agg["alltime"]["tokens_all"] == 44_500_000_000


class TestAssumption:
    def test_none_agg_returns_default(self):
        assert assumption(None, "usd_eur_rate", 1.0) == 1.0

    def test_missing_key_returns_default(self):
        assert assumption({"assumptions": {}}, "usd_eur_rate", 1.0) == 1.0

    def test_present_value(self):
        agg = {"assumptions": {"usd_eur_rate": {"value": 0.87897,
                                                "stand": "2026-07-24", "quelle": "EZB"}}}
        assert assumption(agg, "usd_eur_rate") == pytest.approx(0.87897)

    def test_entry_without_value_field_returns_default(self):
        agg = {"assumptions": {"usd_eur_rate": {"stand": "x", "quelle": "y"}}}
        assert assumption(agg, "usd_eur_rate", 1.0) == 1.0


class TestMoney:
    """Ohne dokumentierten Kurs bleibt es USD — ein Dollarbetrag darf nie
    still als EUR beschriftet werden (A33)."""

    def test_no_agg_stays_usd(self):
        assert money(100.0, None) == (100.0, "$")

    def test_rate_applied(self):
        agg = {"assumptions": {"usd_eur_rate": {"value": 0.5, "stand": "x", "quelle": "y"}}}
        assert money(100.0, agg) == (50.0, "\u20ac")

    def test_zero_rate_stays_usd(self):
        agg = {"assumptions": {"usd_eur_rate": {"value": 0, "stand": "x", "quelle": "y"}}}
        assert money(100.0, agg) == (100.0, "$")


def _rec(rid, out, cread=0, cwrite=0, inp=0):
    import json as _json
    return _json.dumps({
        "type": "assistant", "requestId": rid, "uuid": rid + "-u",
        "message": {"id": "msg_" + rid, "model": "claude-opus-5",
                    "usage": {"input_tokens": inp, "output_tokens": out,
                              "cache_read_input_tokens": cread,
                              "cache_creation_input_tokens": cwrite}},
    }) + "\n"


class TestReadSessionUsage:
    """Streaming-Schnappschuesse: mehrere Zeilen pro requestId, letzte gewinnt.

    Gemessen 2026-07-26: eine message.id kam bis zu 42x vor, ``cache_creation``
    auf allen Zeilen identisch, ``output_tokens`` wachsend. Summieren haette
    denselben Cache-Write dutzendfach gezaehlt.
    """

    def _mk(self, tmp_path, sid, lines):
        proj = tmp_path / "projects" / "-p"
        proj.mkdir(parents=True)
        (proj / f"{sid}.jsonl").write_text("".join(lines), encoding="utf-8")
        return tmp_path / "projects", tmp_path / "cache"

    def test_unknown_session_returns_none(self, tmp_path):
        assert read_session_usage("", tmp_path, tmp_path) is None
        assert read_session_usage("unknown", tmp_path, tmp_path) is None

    def test_no_transcript_returns_none(self, tmp_path):
        (tmp_path / "projects").mkdir()
        assert read_session_usage("fehlt", tmp_path / "projects", tmp_path / "c") is None

    def test_snapshots_deduped_last_wins(self, tmp_path):
        sid = "s1"
        proj, cache = self._mk(tmp_path, sid, [
            _rec("r1", 4, cwrite=20865),
            _rec("r1", 4, cwrite=20865),
            _rec("r1", 233, cwrite=20865),   # dieselbe Anfrage, vollstaendiger
        ])
        got = read_session_usage(sid, proj, cache)
        assert got["records"] == 1
        assert got["output"] == 233          # nicht 4+4+233
        assert got["cache_write"] == 20865   # nicht 3x20865

    def test_cache_hit_ratio(self, tmp_path):
        sid = "s2"
        proj, cache = self._mk(tmp_path, sid, [_rec("r1", 10, cread=90, cwrite=0, inp=10)])
        got = read_session_usage(sid, proj, cache)
        assert got["cache_hit_ratio"] == pytest.approx(0.9)

    def test_ratio_none_when_no_input_side_tokens(self, tmp_path):
        sid = "s3"
        proj, cache = self._mk(tmp_path, sid, [_rec("r1", 5)])
        assert read_session_usage(sid, proj, cache)["cache_hit_ratio"] is None

    def test_incremental_append_picked_up(self, tmp_path):
        sid = "s4"
        proj, cache = self._mk(tmp_path, sid, [_rec("r1", 100)])
        first = read_session_usage(sid, proj, cache)
        assert first["output"] == 100
        with (proj / "-p" / f"{sid}.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(_rec("r2", 50))
        second = read_session_usage(sid, proj, cache)
        assert second["output"] == 150
        assert second["records"] == 2

    def test_truncated_file_restarts_cleanly(self, tmp_path):
        sid = "s5"
        proj, cache = self._mk(tmp_path, sid, [_rec("r1", 100), _rec("r2", 100)])
        read_session_usage(sid, proj, cache)
        (proj / "-p" / f"{sid}.jsonl").write_text(_rec("r9", 7), encoding="utf-8")
        got = read_session_usage(sid, proj, cache)
        assert got["output"] == 7
        assert got["records"] == 1
