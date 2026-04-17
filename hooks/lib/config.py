"""config.py — Centralized configuration for meta-skills plugin.

Single source for ALL tunable values. Every hook and script reads from here.
No hardcoded thresholds anywhere else.

Usage:
    from lib.config import load_config
    config = load_config()

    # Access settings:
    config["thresholds"]["min_reads_before_write"]  # 3
    config["autoreason"]["num_judges"]               # 3
    config["quality_gate"]["block_commit_on_lint_fail"]  # False
"""
import json
import os
from pathlib import Path


DEFAULT_CONFIG = {
    "version": 3,
    "platform": "Windows",

    "features": {
        "statusline": True,
        "watcher": True,
        "sync_on_stop": True,
        "correction_detect": True,
        "honcho_context": True,
        "notebook_search": True,
        "process_watchdog": False,
        "context_recovery": True,
        "session_start_hook": True,
    },

    "thresholds": {
        # Watcher
        "ram_warn_mb": 4000,
        "ram_spike_mb": 500,
        "age_warn_h": 24,
        "watcher_poll_s": 10,
        # Quality gates
        "min_reads_before_write": 3,
        "consecutive_failures_warn": 3,
        "scope_drift_warn_switches": 3,
        "correction_pause_count": 2,
        "context_recovery_gap": 10,
        # Cleanup
        "state_files_keep": 5,
        "audit_log_max_mb": 10,
        "error_log_max_kb": 512,
    },

    "services": {
        "honcho_url": "http://honcho.local:8055",
        "notebook_api": "http://open-notebook.local:5055",
        "notebook_id": "notebook:zkxy9fiwelrolgbr2upc",
    },

    "autoreason": {
        "num_judges": 3,
        "max_passes": 5,
        "convergence_k": 2,
        "cli_timeout_s": 180,
        "api_timeout_s": 120,
        "judge_priority": ["kimi", "qwen", "devstral", "codex", "copilot", "opencode", "claude"],
        "role_agents": {
            "critic": "kimi",
            "author_b": "qwen",
            "synthesizer": "claude",
        },
    },

    "quality_gate": {
        "block_commit_on_lint_fail": False,
        "block_push_on_ci_fail": False,
        "warn_commit_without_lint": True,
        "warn_push_without_ci": True,
        "commit_message_format_check": True,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base. Override values win."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _validate_type(value, expected_type: str, path: str) -> list:
    """Minimal type validation. Returns list of error strings."""
    type_map = {
        "dict": dict, "str": str, "int": int,
        "bool": bool, "list": list, "float": (int, float),
    }
    if expected_type in type_map:
        if not isinstance(value, type_map[expected_type]):
            return [f"{path}: expected {expected_type}, got {type(value).__name__}"]
    return []


def validate_config(config: dict) -> list:
    """Basic validation. Returns list of error strings."""
    errors = []
    if not isinstance(config, dict):
        return ["config: not a dict"]

    # Check required top-level keys
    for key in ("version", "features"):
        if key not in config:
            errors.append(f"missing required key: {key}")

    # Check version
    if config.get("version") not in (2, 3):
        errors.append(f"version must be 2 or 3, got {config.get('version')}")

    # Type checks for known sections
    for section in ("features", "thresholds", "services", "autoreason", "quality_gate"):
        if section in config:
            errors.extend(_validate_type(config[section], "dict", section))

    return errors


def load_config(project: str = None) -> dict:
    """Load config with defaults. Never fails — returns defaults on error.

    Load order: DEFAULT_CONFIG → config.json → project_overrides[project]
    """
    plugin_data = Path(os.environ.get(
        "CLAUDE_PLUGIN_DATA",
        Path.home() / ".claude" / "plugins" / "data" / "meta-skills"
    ))
    config_file = plugin_data / "config.json"

    config = DEFAULT_CONFIG.copy()

    try:
        if config_file.exists():
            user_config = json.loads(config_file.read_text(encoding="utf-8"))
            errors = validate_config(user_config)
            if not errors:
                config = _deep_merge(DEFAULT_CONFIG, user_config)
            else:
                # Partial merge — use what's valid
                config = _deep_merge(DEFAULT_CONFIG, user_config)
    except Exception:
        pass

    # Apply project-level overrides if specified
    if project and "project_overrides" in config:
        overrides = config.get("project_overrides", {}).get(project, {})
        if overrides:
            config = _deep_merge(config, overrides)

    return config


# Backward compatibility: old imports still work
CONFIG_SCHEMA = None  # Deprecated — use validate_config() instead
