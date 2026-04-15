---
description: "Check CI/CD status — show last runs, watch current, debug failures"
argument-hint: "[--watch|--last-failure|--quick] — watch: poll until done. last-failure: show logs. quick: one-liner."
---

# CI/CD Status

Check GitHub Actions CI/CD status for this repository:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ci-status.py" $ARGUMENTS
```

If the last run failed, investigate with:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ci-status.py" --last-failure
```
