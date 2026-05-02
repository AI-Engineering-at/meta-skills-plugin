"""Tests for scripts/validate.py.

Covers:
- parse_frontmatter: edge cases that broke before (multiline description,
  missing end marker, json array values)
- VALID_MODELS whitelist: opus 4.7 accepted, legacy names rejected
- VALID_COMPLEXITY + validate_component: required fields, location-specific
  rules, consistency checks

validate.py is a script (no if __name__ guard at import time), so we
import it as a regular module via sys.path.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import validate as V  # noqa: E402


class TestParseFrontmatter:
    def test_no_frontmatter_returns_empty_meta(self):
        meta, body = V.parse_frontmatter("just body text")
        assert meta == {}
        assert body == "just body text"

    def test_missing_end_marker_returns_empty(self):
        meta, body = V.parse_frontmatter("---\nname: foo\n")
        assert meta == {}

    def test_simple_key_value_pairs(self):
        text = "---\nname: my-skill\ndescription: does stuff\n---\nBody."
        meta, body = V.parse_frontmatter(text)
        assert meta["name"] == "my-skill"
        assert meta["description"] == "does stuff"
        assert body == "Body."

    def test_multiline_description_indented(self):
        text = (
            "---\n"
            "name: x\n"
            "description: >\n"
            "  line one continues\n"
            "  and line two\n"
            "version: 1.0.0\n"
            "---\nbody"
        )
        meta, body = V.parse_frontmatter(text)
        assert "line one" in meta["description"]
        assert "line two" in meta["description"]
        assert meta["version"] == "1.0.0"

    def test_json_array_value(self):
        text = '---\ntools: ["Read", "Edit"]\n---\n'
        meta, _ = V.parse_frontmatter(text)
        assert meta["tools"] == ["Read", "Edit"]

    def test_json_array_with_single_quotes_gets_normalized(self):
        text = "---\ntools: ['Read', 'Edit']\n---\n"
        meta, _ = V.parse_frontmatter(text)
        assert meta["tools"] == ["Read", "Edit"]

    def test_malformed_array_fallback_to_split(self):
        text = "---\ntools: [Read, Edit, Grep]\n---\n"
        meta, _ = V.parse_frontmatter(text)
        assert meta["tools"] == ["Read", "Edit", "Grep"]

    def test_body_whitespace_stripped(self):
        text = "---\nname: a\n---\n\n\nbody content\n\n"
        _, body = V.parse_frontmatter(text)
        assert body == "body content"

    def test_colon_in_value_preserved(self):
        text = "---\ndescription: Use: for all-purpose tasks\n---\n"
        meta, _ = V.parse_frontmatter(text)
        assert meta["description"] == "Use: for all-purpose tasks"


class TestValidModels:
    @pytest.mark.parametrize(
        "model_id",
        [
            "claude-opus-4-7",
            "claude-opus-4-6",
            "claude-sonnet-4-5",
            "claude-sonnet-4-6",
            "claude-haiku-4-5",
            "claude-haiku-4-5-20251001",
            "haiku",
            "sonnet",
            "opus",
        ],
    )
    def test_accepted(self, model_id):
        assert model_id in V.VALID_MODELS

    @pytest.mark.parametrize(
        "model_id",
        [
            "claude-sonnet-3-5",
            "claude-opus-3",
            "gpt-4",
            "gpt-5-turbo",
            "llama3",
            "",
        ],
    )
    def test_rejected(self, model_id):
        # Regression guard: the legacy/3rd-party names must not slip back
        # into the whitelist when somebody edits validate.py.
        assert model_id not in V.VALID_MODELS


class TestValidComplexity:
    def test_skill_accepted(self):
        assert "skill" in V.VALID_COMPLEXITY

    def test_agent_accepted(self):
        assert "agent" in V.VALID_COMPLEXITY

    def test_team_accepted(self):
        assert "team" in V.VALID_COMPLEXITY

    def test_typo_not_accepted(self):
        assert "skils" not in V.VALID_COMPLEXITY


class TestValidateComponent:
    def _mk_skill(self, **meta_override) -> dict:
        meta = {"name": "test-skill", "description": "test", "complexity": "skill"}
        meta.update(meta_override)
        return {
            "name": meta["name"],
            "path": "/fake/path/SKILL.md",
            "location": "skills",
            "meta": meta,
            "body": "x" * 100,
            "body_lines": 1,
        }

    def _mk_agent(self, **meta_override) -> dict:
        meta = {
            "name": "test-agent",
            "description": "test",
            "complexity": "agent",
            "model": "haiku",
        }
        meta.update(meta_override)
        return {
            "name": meta["name"],
            "path": "/fake/path/agent.md",
            "location": "agents",
            "meta": meta,
            "body": "body",
            "body_lines": 1,
        }

    def test_missing_name_flags_error(self):
        comp = self._mk_skill()
        comp["meta"]["name"] = ""
        result = V.validate_component(comp)
        assert any("name" in e for e in result["errors"])

    def test_missing_description_flags_error(self):
        comp = self._mk_skill(description="")
        result = V.validate_component(comp)
        assert any("description" in e for e in result["errors"])

    def test_invalid_complexity_flags_error(self):
        comp = self._mk_skill(complexity="wibble")
        result = V.validate_component(comp)
        assert any("invalid complexity" in e for e in result["errors"])

    def test_agent_missing_model_flags_error(self):
        comp = self._mk_agent()
        comp["meta"]["model"] = ""
        result = V.validate_component(comp)
        assert any("model" in e for e in result["errors"])

    def test_agent_opus47_model_accepted(self):
        comp = self._mk_agent(model="claude-opus-4-7")
        result = V.validate_component(comp)
        assert not any("unusual model" in w for w in result["warnings"])

    def test_agent_unknown_model_warns(self):
        comp = self._mk_agent(model="gpt-5-turbo")
        result = V.validate_component(comp)
        assert any("unusual model" in w for w in result["warnings"])

    def test_skill_missing_version_warns(self):
        comp = self._mk_skill()
        result = V.validate_component(comp)
        assert any("version" in w for w in result["warnings"])

    def test_skill_missing_token_budget_warns(self):
        comp = self._mk_skill()
        result = V.validate_component(comp)
        assert any("token-budget" in w for w in result["warnings"])

    def test_team_without_workers_errors(self):
        comp = self._mk_skill(complexity="team")
        result = V.validate_component(comp)
        assert any("team-workers" in e for e in result["errors"])

    def test_team_with_workers_no_error(self):
        comp = self._mk_skill(
            complexity="team", **{"team-workers": "a,b,c", "team-consolidator": "x"}
        )
        result = V.validate_component(comp)
        assert not any("team-workers" in e for e in result["errors"])
