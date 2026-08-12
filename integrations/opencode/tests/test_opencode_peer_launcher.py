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


def test_session_resolves_role_specific_bridge_token(tmp_path: Path) -> None:
    calls = tmp_path / "vault-calls"
    env = _environment(
        tmp_path,
        f'#!/bin/zsh\nprint -r -- "$@" >> "{calls}"\nprint synthetic-bridge-token\n',
    )

    for role in ("brain",):
        result = subprocess.run(
            [str(LAUNCHER), "--role", role, "run", "probe"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        assert result.returncode == 0

    assert calls.read_text(encoding="utf-8").splitlines() == [
        "get phantom-bridge client-token-opencode-brain --raw",
    ]


def test_direct_model_workers_do_not_resolve_a_bridge_token(tmp_path: Path) -> None:
    env = _environment(tmp_path, "#!/bin/zsh\nexit 99\n")
    fake_bin = Path(env["PATH"].split(":", 1)[0])
    _executable(fake_bin / "opencode", "#!/bin/zsh\nprint -r -- \"$@\"\n")

    for role in ("vibe", "ocode-kimi", "ocode-pruefer"):
        result = subprocess.run(
            [str(LAUNCHER), "--role", role, "run", "probe"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        assert result.returncode == 0
        assert "--agent " + role in result.stdout


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


def test_team_sessions_enable_auto_approval_but_brain_does_not(tmp_path: Path) -> None:
    env = _environment(tmp_path, "#!/bin/zsh\nprint synthetic-bridge-token\n")
    fake_bin = Path(env["PATH"].split(":", 1)[0])
    _executable(fake_bin / "opencode", "#!/bin/zsh\nprint -r -- \"$@\"\n")

    for role in ("vibe", "ocode-kimi", "ocode-pruefer"):
        result = subprocess.run(
            [str(LAUNCHER), "--role", role, "run", "probe"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        assert result.returncode == 0
        assert f"--agent {role}" in result.stdout
        assert "--auto" in result.stdout

    result = subprocess.run(
        [str(LAUNCHER), "--role", "brain", "run", "probe"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0
    assert "--auto" not in result.stdout


def test_ocode_workers_use_exact_agents_and_default_channel(tmp_path: Path) -> None:
    env = _environment(tmp_path, "#!/bin/zsh\nprint synthetic-bridge-token\n")
    fake_bin = Path(env["PATH"].split(":", 1)[0])
    _executable(fake_bin / "opencode", "#!/bin/zsh\nprint -r -- \"$@\"\n")

    for role in ("ocode-kimi", "ocode-pruefer"):
        result = subprocess.run(
            [str(LAUNCHER), "--role", role, "run", "probe"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        assert result.returncode == 0
        assert f"--agent {role}" in result.stdout
        assert "channel=ocode-team" in result.stdout
        assert "--auto" in result.stdout


def test_new_profiles_bind_exact_role_model_and_no_secret() -> None:
    expected = {
        "ocode-kimi": "opencode/big-pickle",
        "ocode-pruefer": "opencode/big-pickle",
        "vibe": "opencode/big-pickle",
    }
    for role, model in expected.items():
        text = (PROFILES / f"opencode.{role}.jsonc").read_text(encoding="utf-8")
        profile = json.loads(text)
        assert profile["model"] == model
        assert profile["default_agent"] == role
        assert profile["agent"][role]["model"] == model
        assert profile["mcp"]["aie-mm-mcp"]["env"]["AIE_MM_ROLE"] == role
        assert "token" not in text.lower()


def test_brain_profile_bypasses_bridge_during_t2_quarantine() -> None:
    profile = json.loads((PROFILES / "opencode.brain.jsonc").read_text(encoding="utf-8"))
    assert profile["model"] == "opencode/gpt-5.6-sol"
    assert profile["small_model"] == "opencode/big-pickle"
    assert profile["agent"]["brain"]["model"] == "opencode/gpt-5.6-sol"
    assert "phantom/" not in json.dumps(profile)


def test_ocode_team_profiles_allow_only_their_assigned_worktree() -> None:
    expected = {
        "ocode-kimi": "/Users/mackbook/code-aie/worktrees/bridge-01322-deploy-convergence/**",
        "vibe": "/Users/mackbook/code-aie/meta-skills-plugin/**",
        "ocode-pruefer": "/Users/mackbook/code-aie/worktrees/bridge-01322-deploy-convergence/**",
    }
    for role, path in expected.items():
        profile = json.loads((PROFILES / f"opencode.{role}.jsonc").read_text(encoding="utf-8"))
        external = profile["permission"]["external_directory"]
        assert external == {path: "allow"}


def test_role_profiles_do_not_override_phantom_auth() -> None:
    """Profiles must not override phantom auth — token comes from opencode.jsonc."""
    for role in ("brain", "vibe"):
        profile = json.loads((PROFILES / f"opencode.{role}.jsonc").read_text(encoding="utf-8"))
        phantom = profile.get("provider", {}).get("phantom", {})
        assert not phantom, (
            f"opencode.{role}.jsonc must not override phantom provider; "
            f"token comes from main opencode.jsonc"
        )
