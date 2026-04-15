---
description: "Show quality dashboard — eval scores, validation, trends, delta vs baseline"
---

# Quality Dashboard

Run the quality snapshot script to see current scores and trends:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/quality-snapshot.py"
```

For detailed diagnostics, also run reworker:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/reworker.py" --diagnose --top 5
```
