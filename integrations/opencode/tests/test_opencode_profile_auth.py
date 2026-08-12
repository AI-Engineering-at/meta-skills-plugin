"""Tests for OpenCode profile configuration and the Bridge-T2 boundary.

ANLASS (2026-07-29): Profile no longer override Phantom provider options.
The Phantom Bridge client token comes from the main opencode.jsonc config
(which holds the vault-derived token). Profiles must NOT contain phantom
overrides OR literal tokens.

KORREKTUR (2026-08-12): opencode laeuft auf opencode-Standard-Only —
anonymer `opencode`-Provider, KEINE Provider-Bloecke, kein gpt-5.6/chatgpt/
phantom/openai im Code. GPT-5.6 ist allein Joes situative Wahl, nichts davon
in Konfig oder Tests. Ein Provider-Block mit totem Modell war die Ursache des
`undefined is not an object (evaluating 'M.type')`-Absturzes am 12.08.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

PROFILES_DIR = Path(__file__).parent.parent / "profiles"
CONFIG_DIR = Path.home() / ".config" / "opencode"


def _load_jsonc(path: Path) -> dict:
    """Load a JSONC file, stripping comments."""
    if not path.exists():
        pytest.skip(f"file not found at {path}")
    raw = path.read_text(encoding="utf-8")
    lines = []
    for line in raw.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        idx = line.find("//")
        if idx > 0 and not line[:idx].strip().startswith('"'):
            line = line[:idx]
        lines.append(line)
    return json.loads("\n".join(lines))


class TestPhantomProviderConfig:
    """Profiles must NOT override Phantom provider options."""

    @pytest.mark.parametrize("profile_name", [
        "opencode.brain.jsonc",
        "opencode.vibe.jsonc",
    ])
    def test_phantom_provider_not_overridden(self, profile_name: str):
        """Profile must not override phantom provider options (env-var didn't resolve)."""
        config = _load_jsonc(PROFILES_DIR / profile_name)
        phantom = config.get("provider", {}).get("phantom", {})
        assert not phantom, (
            f"{profile_name}: phantom provider override found — remove it; "
            f"token comes from main opencode.jsonc"
        )

    @pytest.mark.parametrize("profile_name", [
        "opencode.brain.jsonc",
        "opencode.vibe.jsonc",
    ])
    def test_no_literal_token_in_profile(self, profile_name: str):
        """Profile must not contain a literal bridge token (aie-... pattern)."""
        raw = (PROFILES_DIR / profile_name).read_text(encoding="utf-8")
        token_pattern = re.compile(r'"aie-[A-Za-z0-9_-]{20,}"')
        assert not token_pattern.search(raw), (
            f"{profile_name}: contains literal bridge token"
        )


class TestMainConfigOpencodeStandard:
    """Main opencode.jsonc must be opencode-standard-only (anonymous provider)."""

    def test_only_opencode_provider_enabled(self):
        """No provider may be enabled besides the anonymous opencode provider."""
        config = _load_jsonc(CONFIG_DIR / "opencode.jsonc")
        assert config.get("enabled_providers") == ["opencode"], (
            "opencode.jsonc: enabled_providers must be exactly ['opencode']"
        )
        assert not config.get("provider"), (
            "opencode.jsonc: provider block must be empty — kein Phantom/ChatGPT/OpenAI"
        )

    def test_no_nonstandard_model_reference_in_config(self):
        """Config must not reference gpt-5.6/chatgpt/phantom/openai model ids."""
        config = _load_jsonc(CONFIG_DIR / "opencode.jsonc")
        blob = json.dumps(config)
        for forbidden in ("gpt-5.6", "chatgpt/", "phantom/", '"openai/"'):
            assert forbidden not in blob, f"opencode.jsonc: forbidden reference {forbidden}"

    def test_default_models_are_opencode_big_pickle(self):
        """model and small_model must resolve to the anonymous opencode standard."""
        config = _load_jsonc(CONFIG_DIR / "opencode.jsonc")
        assert config["model"] == "opencode/big-pickle"
        assert config["small_model"] == "opencode/big-pickle"
        for agent in config.get("agent", {}).values():
            assert agent.get("model") == "opencode/big-pickle"


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("brain", "opencode/big-pickle"),
        ("vibe", "opencode/big-pickle"),
        ("ocode-kimi", "opencode/big-pickle"),
        ("ocode-pruefer", "opencode/big-pickle"),
    ],
)
def test_team_role_uses_direct_model_during_bridge_t2_quarantine(
    role: str, expected: str
) -> None:
    config = _load_jsonc(PROFILES_DIR / f"opencode.{role}.jsonc")

    assert config["model"] == expected
    assert config["agent"][role]["model"] == expected
    assert config["model"].startswith("opencode/")


def test_brain_small_model_is_direct_during_bridge_t2_quarantine() -> None:
    config = _load_jsonc(PROFILES_DIR / "opencode.brain.jsonc")

    assert config["small_model"] == "opencode/big-pickle"


@pytest.mark.parametrize("role", ["brain", "vibe"])
def test_role_profile_does_not_register_second_model_router(role: str) -> None:
    config = _load_jsonc(PROFILES_DIR / f"opencode.{role}.jsonc")

    assert "@smart-coders-hq/opencode-model-fallback" not in config.get("plugin", [])
