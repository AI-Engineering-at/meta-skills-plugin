"""Tests für usage_core — den gemeinsamen Rechenkern für Nutzungsdaten.

Jeder Test hier hält einen Fehler fest, der am 2026-07-26 real Geld und
Vertrauen gekostet hat. Reihenfolge entspricht den drei Punkten im
Modul-Docstring von usage_core.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import usage_core as U  # noqa: E402


class TestNormalizeModel:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("claude-opus-4-8", "opus-4.8"),
            ("claude-opus-5", "opus-5"),
            # Der [1m]-Suffix ist Claude Codes Anzeige fuer das 1M-Kontextfenster,
            # kein eigener Tarif — Opus 4.7+ haben keinen Long-Context-Aufschlag.
            ("claude-opus-5[1m]", "opus-5"),
            ("claude-sonnet-5", "sonnet-5"),
            ("claude-sonnet-4-6", "sonnet-4.6"),
            # Datums-Suffix darf die Version nicht verfaelschen.
            ("claude-haiku-4-5-20251001", "haiku-4.5"),
            ("claude-fable-5", "fable-5"),
        ],
    )
    def test_known_ids(self, raw, expected):
        assert U.normalize_model(raw) == expected

    @pytest.mark.parametrize("raw", ["<synthetic>", "unknown", "", None])
    def test_non_models_are_none(self, raw):
        """``<synthetic>`` ist kein Modell. Es mit einem Tarif zu belegen wuerde
        eine Zahl erfinden; ``None`` laesst den Aufrufer es ehrlich als
        unbepreisbar zaehlen."""
        assert U.normalize_model(raw) is None


class TestPriceFor:
    def test_known_model_no_fallback(self):
        prices, fallback = U.price_for("claude-opus-5")
        assert prices["input"] == 5.00
        assert fallback is False

    def test_unknown_model_uses_opus_and_flags_it(self):
        """Eine neue Modellgeneration darf nicht still als kostenlos
        durchlaufen (der Fehler, der ``costUSD: 0`` zu 'keine Kostendaten'
        gemacht hat). Konservativ nach oben, und der Aufrufer erfaehrt es."""
        prices, fallback = U.price_for("claude-nochnichtgeboren-9")
        assert prices == U.MODEL_PRICES[U.FALLBACK_PRICE_KEY]
        assert fallback is True

    def test_non_model_has_no_price(self):
        assert U.price_for("<synthetic>") == (None, False)


class TestSplitUsage:
    def test_cache_creation_object_splits_ttl(self):
        usage = {
            "input_tokens": 1,
            "output_tokens": 2,
            "cache_read_input_tokens": 3,
            "cache_creation": {"ephemeral_5m_input_tokens": 10,
                               "ephemeral_1h_input_tokens": 20},
        }
        assert U.split_usage(usage) == (1, 2, 3, 10, 20)

    def test_aggregate_without_split_counts_as_5m(self):
        """Ohne 5m/1h-Split gilt der Aggregatwert als 5m — die guenstigere
        Variante. Konservative Richtung: eine unbelegte Zahl nie nach oben
        treiben (A33)."""
        usage = {"cache_creation_input_tokens": 500}
        assert U.split_usage(usage) == (0, 0, 0, 500, 0)

    def test_missing_fields_are_zero(self):
        assert U.split_usage({}) == (0, 0, 0, 0, 0)


class TestPriceUsage:
    def test_cache_read_is_ten_percent_of_input(self):
        p = U.MODEL_PRICES["opus-5"]["input"]
        got = U.price_usage({"cache_read_input_tokens": 1_000_000}, "claude-opus-5")
        assert got == pytest.approx(p * U.CACHE_READ_FACTOR)

    def test_cache_write_5m_is_125_percent(self):
        p = U.MODEL_PRICES["opus-5"]["input"]
        got = U.price_usage({"cache_creation_input_tokens": 1_000_000}, "claude-opus-5")
        assert got == pytest.approx(p * U.CACHE_WRITE_5M_FACTOR)

    def test_unpriceable_model_returns_none_not_zero(self):
        """``None`` heisst 'nicht bepreisbar', ``0.0`` hiesse 'kostenlos'.
        Die Verwechslung war Ursache 3 am 2026-07-26."""
        assert U.price_usage({"output_tokens": 999}, "<synthetic>") is None


class TestTotals:
    def test_tokens_all_includes_cache(self):
        """96 % des echten Volumens sind Cache-Token. Wer nur in+out summiert,
        zeigt 0,9 % des Verbrauchs — die Leiste lag deshalb um Faktor ~110
        zu niedrig."""
        t = U.Totals()
        t.add({"input_tokens": 10, "output_tokens": 20,
               "cache_read_input_tokens": 9_000, "cache_creation_input_tokens": 970},
              "claude-opus-5")
        assert t.tokens_io == 30
        assert t.tokens_cache == 9_970
        assert t.tokens_all == 10_000

    def test_cache_hit_ratio(self):
        t = U.Totals()
        t.add({"input_tokens": 10, "cache_read_input_tokens": 90}, "claude-opus-5")
        assert t.cache_hit_ratio == pytest.approx(0.9)

    def test_ratio_none_without_input_side_tokens(self):
        t = U.Totals()
        t.add({"output_tokens": 5}, "claude-opus-5")
        assert t.cache_hit_ratio is None

    def test_unpriceable_counted_separately(self):
        t = U.Totals()
        t.add({"output_tokens": 5}, "<synthetic>")
        assert t.records == 1
        assert t.unpriceable_records == 1
        assert t.priced_usd == 0.0


def _line(rid, out, cwrite=0, mid=None, typ="assistant"):
    return json.dumps({
        "type": typ, "requestId": rid, "uuid": f"{rid}-u",
        "message": {"id": mid or f"msg_{rid}", "model": "claude-opus-5",
                    "usage": {"output_tokens": out, "cache_creation_input_tokens": cwrite}},
    }) + "\n"


class TestIterUsageRecords:
    def test_reads_assistant_records(self, tmp_path):
        p = tmp_path / "s.jsonl"
        p.write_text(_line("r1", 5) + _line("r2", 7), encoding="utf-8")
        assert len(list(U.iter_usage_records(p))) == 2

    def test_skips_non_assistant(self, tmp_path):
        p = tmp_path / "s.jsonl"
        p.write_text(_line("r1", 5, typ="user"), encoding="utf-8")
        assert list(U.iter_usage_records(p)) == []

    def test_malformed_line_skipped_not_fatal(self, tmp_path):
        p = tmp_path / "s.jsonl"
        p.write_text('{"type":"assistant" kaputt\n' + _line("r1", 5), encoding="utf-8")
        assert len(list(U.iter_usage_records(p))) == 1

    def test_unreadable_file_yields_nothing(self, tmp_path):
        """Die Leiste rendert jede Sekunde — ein defektes Transkript darf sie
        nicht abschiessen."""
        assert list(U.iter_usage_records(tmp_path / "gibtsnicht.jsonl")) == []

    def test_missing_usage_block_skipped(self, tmp_path):
        p = tmp_path / "s.jsonl"
        p.write_text(json.dumps({"type": "assistant", "message": {"id": "m"}}) + "\n",
                     encoding="utf-8")
        assert list(U.iter_usage_records(p)) == []


class TestDedupRecords:
    def test_last_occurrence_wins(self, tmp_path):
        """Gemessen 2026-07-26: eine message.id kam bis zu 42x vor,
        ``cache_creation`` auf allen Zeilen identisch, ``output_tokens``
        wachsend. Die Zeilen sind Schnappschuesse, keine Deltas."""
        p = tmp_path / "s.jsonl"
        p.write_text(_line("r1", 4, cwrite=20865)
                     + _line("r1", 4, cwrite=20865)
                     + _line("r1", 233, cwrite=20865), encoding="utf-8")
        ded = U.dedup_records(list(U.iter_usage_records(p)))
        assert len(ded) == 1
        t = U.Totals()
        for rec in ded:
            t.add(rec["usage"], rec["model"])
        assert t.output == 233            # nicht 4+4+233
        assert t.cache_write_5m == 20865  # nicht 3 x 20865

    def test_distinct_requests_kept(self, tmp_path):
        p = tmp_path / "s.jsonl"
        p.write_text(_line("r1", 10) + _line("r2", 20), encoding="utf-8")
        assert len(U.dedup_records(list(U.iter_usage_records(p)))) == 2

    def test_keyless_records_survive_individually(self):
        """Lieber ein Record zu viel als einer verworfen, dessen Zugehoerigkeit
        unklar ist."""
        recs = [{"key": None, "usage": {}, "model": "x"},
                {"key": None, "usage": {}, "model": "x"}]
        assert len(U.dedup_records(recs)) == 2

    def test_requestid_preferred_over_message_id(self, tmp_path):
        """Zwei verschiedene Anfragen koennen dieselbe message.id tragen; der
        requestId trennt sie."""
        p = tmp_path / "s.jsonl"
        p.write_text(_line("r1", 10, mid="msg_same")
                     + _line("r2", 20, mid="msg_same"), encoding="utf-8")
        assert len(U.dedup_records(list(U.iter_usage_records(p)))) == 2
