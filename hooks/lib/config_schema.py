"""config_schema.py — JSON Schema validation for meta-skills config.json.

Usage:
    from lib.config_schema import validate_config, load_config

    config = load_config()  # loads + validates, returns defaults on error
"""
import json
import os
from pathlib import Path


CONFIG_SCHEMA = {
    "type": "object",
    "required": ["version", "features"],
    "properties": {
        "version": {"type": "integer", "minimum": 1},
        "platform": {"type": "string", "enum": ["Windows", "Linux", "Darwin"]},
        "setup_date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
        "features": {
            "type": "object",
            "properties": {
                "statusline": {"type": "boolean"},
                "watcher": {"type": "boolean"},
                "sync_on_stop": {"type": "boolean"},
                "correction_detect": {"type": "boolean"},
                "honcho_context": {"type": "boolean"},
                "notebook_search": {"type": "boolean"},
                "process_watchdog": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "thresholds": {
            "type": "object",
            "properties": {
                "ram_warn_mb": {"type": "integer", "minimum": 100},
                "ram_spike_mb": {"type": "integer", "minimum": 50},
                "age_warn_h": {"type": "integer", "minimum": 1},
                "watcher_poll_s": {"type": "integer", "minimum": 1},
            },
        },
        "services": {
            "type": "object",
            "properties": {
                "honcho_url": {"type": "string"},
                "notebook_api": {"type": "string"},
                "notebook_id": {"type": "string"},
            },
        },
    },
}

DEFAULT_CONFIG = {
    "version": 2,
    "platform": "Windows",
    "features": {
        "statusline": True,
        "watcher": True,
        "sync_on_stop": True,
        "correction_detect": True,
        "honcho_context": True,
        "notebook_search": True,
        "process_watchdog": False,
    },
    "thresholds": {
        "ram_warn_mb": 4000,
        "ram_spike_mb": 500,
        "age_warn_h": 24,
        "watcher_poll_s": 10,
    },
    "services": {
        "honcho_url": "http://10.40.10.82:8055",
        "notebook_api": "http://10.40.10.82:5055",
        "notebook_id": "notebook:zkxy9fiwelrolgbr2upc",
    },
}


def _validate_type(value, schema, path="root"):
    """Minimal JSON Schema validator (no external deps)."""
    errors = []
    expected_type = schema.get("type")

    type_map = {
        "object": dict, "string": str, "integer": int,
        "boolean": bool, "array": list, "number": (int, float),
    }

    if expected_type and expected_type in type_map:
        if not isinstance(value, type_map[expected_type]):
            errors.append(f"{path}: expected {expected_type}, got {type(value).__name__}")
            return errors

    if expected_type == "integer" and "minimum" in schema:
        if value < schema["minimum"]:
            errors.append(f"{path}: {value} < minimum {schema['minimum']}")

    if expected_type == "string" and "enum" in schema:
        if value not in schema["enum"]:
            errors.append(f"{path}: '{value}' not in {schema['enum']}")

    if expected_type == "object" and "properties" in schema:
        for key, prop_schema in schema["properties"].items():
            if key in value:
                errors.extend(_validate_type(value[key], prop_schema, f"{path}.{key}"))

        if schema.get("additionalProperties") is False:
            extra = set(value.keys()) - set(schema["properties"].keys())
            if extra:
                errors.append(f"{path}: unknown keys: {extra}")

    if "required" in schema and isinstance(value, dict):
        for req in schema["required"]:
            if req not in value:
                errors.append(f"{path}: missing required key '{req}'")

    return errors


def validate_config(config: dict) -> list[str]:
    """Validate config against schema. Returns list of error strings."""
    return _validate_type(config, CONFIG_SCHEMA)


def load_config() -> dict:
    """Load and validate config.json. Returns defaults on any error."""
    plugin_data = Path(os.environ.get(
        "CLAUDE_PLUGIN_DATA",
        Path.home() / ".claude" / "plugins" / "data" / "meta-skills"
    ))
    config_file = plugin_data / "config.json"

    try:
        if config_file.exists():
            config = json.loads(config_file.read_text(encoding="utf-8"))
            errors = validate_config(config)
            if errors:
                from lib.hook_wrapper import _log_error
                _log_error("config_load", ValueError("; ".join(errors)), str(config_file))
                # Merge defaults for missing keys
                merged = {**DEFAULT_CONFIG, **config}
                return merged
            return config
    except Exception:
        pass

    return DEFAULT_CONFIG.copy()
