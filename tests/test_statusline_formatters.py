"""Boundary + unit tests for statusline_lib formatters.

Run: pytest tests/test_statusline_formatters.py -v
"""

import sys
from pathlib import Path

# Add scripts/ to import path (tests/ is sibling to scripts/)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from statusline_lib import fcost, fk, parse_model_id  # noqa: E402


# ═══════════════════════════════════════════════════════════════
# fk() — token count formatter
# ═══════════════════════════════════════════════════════════════


class TestFk:
    def test_below_thousand_raw(self):
        assert fk(0) == "0"
        assert fk(1) == "1"
        assert fk(500) == "500"
        assert fk(999) == "999"

    def test_k_scale(self):
        assert fk(1_000) == "1k"
        assert fk(6_200) == "6k"
        assert fk(500_000) == "500k"

    def test_k_to_M_boundary(self):
        # 999_500 / 1000 = 999.5 -> .0f rounds to 1000 -> must promote to M
        assert "M" in fk(999_500)
        assert fk(999_499) == "999k"
        # Exact M boundary
        assert fk(1_000_000) == "1.0M"

    def test_M_scale(self):
        assert fk(6_200_000) == "6.2M"
        assert fk(76_400_000) == "76.4M"
        assert fk(547_000_000) == "547.0M"

    def test_M_to_B_boundary(self):
        # 999_950_000 / 1_000_000 = 999.95 -> .1f rounds to 1000.0 -> promote to B
        assert "B" in fk(999_950_000)
        assert fk(1_000_000_000) == "1.0B"

    def test_B_scale(self):
        assert fk(1_200_000_000) == "1.2B"
        assert fk(76_400_000_000) == "76.4B"

    def test_B_to_T_boundary(self):
        assert "T" in fk(999_950_000_000)
        assert fk(1_000_000_000_000) == "1.0T"

    def test_T_scale(self):
        assert fk(3_500_000_000_000) == "3.5T"


# ═══════════════════════════════════════════════════════════════
# fcost() — dollar amount formatter
# ═══════════════════════════════════════════════════════════════


class TestFcost:
    def test_cents_preserved_below_dollar(self):
        assert fcost(0.01) == "$0.01"
        assert fcost(0.99) == "$0.99"

    def test_small_amounts_with_cents(self):
        assert fcost(1.00) == "$1.00"
        assert fcost(25.50) == "$25.50"
        assert fcost(706.66) == "$706.66"
        assert fcost(999.99) == "$999.99"

    def test_k_scale_no_cents(self):
        assert fcost(1_000) == "$1k"
        assert fcost(25_370) == "$25k"
        assert fcost(705_830) == "$706k"

    def test_k_to_M_boundary_no_thousand_k(self):
        """The original bug: $999_999.99 was rendering as $1000k instead of $1.0M."""
        result = fcost(999_999.99)
        assert "1000k" not in result, f"boundary bug: {result}"
        assert result == "$1.0M"

    def test_k_to_M_boundary_edge(self):
        # 999_500 / 1000 = 999.5 -> :.0f rounds to 1000 -> must promote
        assert fcost(999_500) == "$1.0M"
        assert fcost(999_499) == "$999k"

    def test_M_scale(self):
        assert fcost(1_000_000) == "$1.0M"
        assert fcost(25_400_000) == "$25.4M"

    def test_M_to_B_boundary(self):
        assert "B" in fcost(999_950_000)
        assert fcost(1_000_000_000) == "$1.0B"

    def test_B_scale(self):
        assert fcost(7_200_000_000) == "$7.2B"

    def test_B_to_T_boundary(self):
        assert "T" in fcost(999_950_000_000)
        assert fcost(1_000_000_000_000) == "$1.0T"


# ═══════════════════════════════════════════════════════════════
# parse_model_id() — model ID → short label
# ═══════════════════════════════════════════════════════════════


class TestParseModelId:
    def test_opus_versions(self):
        assert parse_model_id("claude-opus-4-7") == ("O4.7", "opus")
        assert parse_model_id("claude-opus-4-6") == ("O4.6", "opus")
        assert parse_model_id("claude-opus-5-0") == ("O5.0", "opus")

    def test_sonnet_versions(self):
        assert parse_model_id("claude-sonnet-4-6") == ("S4.6", "sonnet")
        assert parse_model_id("claude-sonnet-4-5") == ("S4.5", "sonnet")

    def test_haiku_with_date_suffix(self):
        assert parse_model_id("claude-haiku-4-5-20251001") == ("H4.5", "haiku")

    def test_case_insensitive(self):
        assert parse_model_id("Claude-Opus-4-7") == ("O4.7", "opus")

    def test_family_fallback_when_version_missing(self):
        label, family = parse_model_id("claude-opus-unknown")
        assert family == "opus"
        assert label.startswith("O")

    def test_empty_and_none(self):
        assert parse_model_id("") == ("?", None)
        assert parse_model_id(None) == ("?", None)

    def test_unknown_model(self):
        label, family = parse_model_id("gpt-5")
        assert family is None
        assert label  # non-empty

    def test_integer_input_does_not_crash(self):
        label, family = parse_model_id(12345)
        assert label  # degrades gracefully
