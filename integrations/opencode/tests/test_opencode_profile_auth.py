"""Tests for OpenCode profile configuration — phantom provider auth.

ANLASS (2026-07-29): Brain pushed runtime resolver (33adbb1) + Phantom
profile override (fd2b8b3) mit {env:PHANTOM_BRIDGE_CLIENT_TOKEN}.
Diese Tests verifizieren, dass die Profile korrekt konfiguriert sind
und kein Literal-Token mehr enthalten.

Kein Live-Probe — das macht Brain selbst.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

PROFILES_DIR = Path(__file__).parent.parent / "profiles"

ENV_REF_PATTERN = re.compile(r"^\{env:[A-Z_][A-Z0-9_]*\}$")


def _load_profile(name: str) -> dict:
    """Load a JSONC profile, stripping comments."""
    path = PROFILES_DIR / name
    if not path.exists():
        pytest.skip(f"profile {name} not found at {path}")
    raw = path.read_text(encoding="utf-8")
    # Strip // comments
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
    """Phantom provider in profiles must use env-reference apiKey."""

    @pytest.mark.parametrize("profile_name", [
        "opencode.brain.jsonc",
        "opencode.vibe.jsonc",
    ])
    def test_phantom_provider_has_base_url(self, profile_name: str):
        """Phantom provider must have baseURL pointing to Bridge."""
        config = _load_profile(profile_name)
        phantom = config.get("provider", {}).get("phantom", {})
        assert "options" in phantom, f"{profile_name}: phantom.options missing"
        assert "baseURL" in phantom["options"], f"{profile_name}: phantom.options.baseURL missing"
        assert phantom["options"]["baseURL"].endswith("/v1"), (
            f"{profile_name}: baseURL should end with /v1, got {phantom['options']['baseURL']}"
        )

    @pytest.mark.parametrize("profile_name", [
        "opencode.brain.jsonc",
        "opencode.vibe.jsonc",
    ])
    def test_phantom_provider_has_env_api_key(self, profile_name: str):
        """Phantom provider apiKey must be an {env:VAR} reference, not a literal."""
        config = _load_profile(profile_name)
        phantom = config.get("provider", {}).get("phantom", {})
        assert "options" in phantom, f"{profile_name}: phantom.options missing"
        assert "apiKey" in phantom["options"], f"{profile_name}: phantom.options.apiKey missing"
        api_key = phantom["options"]["apiKey"]
        assert ENV_REF_PATTERN.match(api_key), (
            f"{profile_name}: apiKey must be {{env:VAR}} reference, got: {api_key}"
        )

    @pytest.mark.parametrize("profile_name", [
        "opencode.brain.jsonc",
        "opencode.vibe.jsonc",
    ])
    def test_phantom_provider_env_var_name(self, profile_name: str):
        """The env-var name must be PHANTOM_BRIDGE_CLIENT_TOKEN."""
        config = _load_profile(profile_name)
        phantom = config.get("provider", {}).get("phantom", {})
        api_key = phantom["options"]["apiKey"]
        var_name = api_key[len("{env:"):-1]
        assert var_name == "PHANTOM_BRIDGE_CLIENT_TOKEN", (
            f"{profile_name}: expected PHANTOM_BRIDGE_CLIENT_TOKEN, got {var_name}"
        )

    @pytest.mark.parametrize("profile_name", [
        "opencode.brain.jsonc",
        "opencode.vibe.jsonc",
    ])
    def test_no_literal_token_in_profile(self, profile_name: str):
        """Profile must not contain a literal token (aie-... pattern).

        Only matches tokens that look like 'aie-' followed by 20+ alphanumeric
        chars (real bridge tokens). Does not match MCP names like 'aie-mm-mcp'.
        """
        raw = (PROFILES_DIR / profile_name).read_text(encoding="utf-8")
        # Real bridge tokens: aie- followed by 20+ base62 chars
        token_pattern = re.compile(r'"aie-[A-Za-z0-9_-]{20,}"')
        assert not token_pattern.search(raw), (
            f"{profile_name}: contains literal bridge token"
        )
