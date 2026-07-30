"""Contract tests for the role-bound OpenCode launcher.

The tests use only synthetic values.  They prove that the launcher resolves a
Bridge token at process start without emitting it and that administrative
subcommands do not invoke the resolver.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "opencode-peer"
PROFILES = ROOT / "profiles"


def _executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _environment(tmp_path: Path, vault_body: str) -> dict[str, str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _executable(
        fake_bin / "opencode",
        "#!/bin/zsh\nprint \"token=${PHANTOM_BRIDGE_CLIENT_TOKEN:+present}\"\n",
    )
    vault = tmp_path / "fake-vault"
    _executable(vault, vault_body)
    return {
        **os.environ,
        "AIE_VAULT_BIN": str(vault),
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
    }


def test_session_resolves_bridge_token_without_emitting_value(tmp_path: Path) -> None:
    env = _environment(tmp_path, "#!/bin/zsh\nprint synthetic-bridge-token\n")

    result = subprocess.run(
        [str(LAUNCHER), "--role", "brain", "run", "probe"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0
    assert "token=present" in result.stdout
    assert "synthetic-bridge-token" not in result.stdout
    assert "synthetic-bridge-token" not in result.stderr


def test_administration_command_does_not_resolve_bridge_token(tmp_path: Path) -> None:
    env = _environment(tmp_path, "#!/bin/zsh\nexit 99\n")

    result = subprocess.run(
        [str(LAUNCHER), "--role", "brain", "debug", "config"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 64
    assert "sessions only" in result.stderr


def test_vibe_session_does_not_enable_auto_approval(tmp_path: Path) -> None:
    env = _environment(tmp_path, "#!/bin/zsh\nprint synthetic-bridge-token\n")
    fake_bin = Path(env["PATH"].split(":", 1)[0])
    _executable(fake_bin / "opencode", "#!/bin/zsh\nprint -r -- \"$@\"\n")

    result = subprocess.run(
        [str(LAUNCHER), "--role", "vibe", "run", "probe"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0
    assert "--agent vibe" in result.stdout
    assert "--auto" not in result.stdout


def test_role_profiles_do_not_override_phantom_auth() -> None:
    """Profiles must not override phantom auth — token comes from opencode.jsonc."""
    for role in ("brain", "vibe"):
        profile = json.loads((PROFILES / f"opencode.{role}.jsonc").read_text(encoding="utf-8"))
        phantom = profile.get("provider", {}).get("phantom", {})
        assert not phantom, (
            f"opencode.{role}.jsonc must not override phantom provider; "
            f"token comes from main opencode.jsonc"
        )
