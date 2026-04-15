---
description: "Run behavioral skill tests — verify skills WORK, not just parse"
argument-hint: "[--all|skill-name|--json] — all: test all 15 skills. skill-name: test one. json: machine output."
---

# Behavioral Skill Tests

Run behavioral tests that verify skills produce correct behavior:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/test-skill.py" $ARGUMENTS
```

Tests use the cheapest available CLI (qwen > kimi > opencode) to execute
each skill's test-scenario.md and check output against pass/fail patterns.

Results: PASS (correct behavior), FAIL (anti-patterns detected), WEAK (insufficient signal), SKIP (no test-scenario.md).
