---
description: "Full quality snapshot — harden + CI + behavioral tests in one view"
argument-hint: "[--quick] — quick: skip behavioral tests (faster)"
---

# Quality Snapshot

Run all quality checks and show a unified dashboard:

```bash
echo "=== HARDEN SCAN ===" && python3 "${CLAUDE_PLUGIN_ROOT}/scripts/harden.py" --scan && echo "" && echo "=== CI STATUS ===" && python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ci-status.py" --quick && echo "" && echo "=== BEHAVIORAL TESTS ===" && python3 "${CLAUDE_PLUGIN_ROOT}/scripts/test-skill.py" --all --timeout 30 $ARGUMENTS 2>&1 | tail -5
```
