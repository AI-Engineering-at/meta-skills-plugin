"""Tests for OpenCode profile configuration — phantom provider auth.

ANLASS (2026-07-29): Profile no longer override Phantom provider options.
The Phantom Bridge client token comes from the main opencode.jsonc config
(which holds the vault-derived token). Profiles must NOT contain phantom
overrides OR literal tokens.

Kein Live-Probe — das macht Brain selbst.
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


class TestMainConfigPhantomProvider:
    """Main opencode.jsonc must have correct phantom provider config."""

    def test_main_config_has_phantom_with_api_key(self):
        """Main config must have phantom provider with a non-empty apiKey."""
        config = _load_jsonc(CONFIG_DIR / "opencode.jsonc")
        providers = config.get("provider", {})
        assert "phantom" in providers, "opencode.jsonc: phantom provider missing"
        phantom = providers["phantom"]
        assert "options" in phantom, "opencode.jsonc: phantom.options missing"
        assert "apiKey" in phantom["options"], "opencode.jsonc: phantom.options.apiKey missing"
        api_key = phantom["options"]["apiKey"]
        assert api_key == "{env:PHANTOM_BRIDGE_CLIENT_TOKEN}", (
            "opencode.jsonc: apiKey must be the session-scoped Vault environment reference"
        )

    def test_main_config_has_base_url(self):
        """Main config phantom provider must have valid baseURL."""
        config = _load_jsonc(CONFIG_DIR / "opencode.jsonc")
        phantom = config.get("provider", {}).get("phantom", {})
        base_url = phantom.get("options", {}).get("baseURL", "")
        assert base_url.endswith("/v1"), f"baseURL should end with /v1, got {base_url}"
        assert "10.40.10.83:18790" in base_url, f"baseURL should point to bridge, got {base_url}"


def test_vibe_profile_uses_a_model_offered_by_the_current_bridge() -> None:
    config = _load_jsonc(PROFILES_DIR / "opencode.vibe.jsonc")

    assert config["model"] == "phantom/local/bonsai"
    assert config["agent"]["vibe"]["model"] == "phantom/local/bonsai"
