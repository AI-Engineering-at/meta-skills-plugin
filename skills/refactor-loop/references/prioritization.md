# Prioritization Rules — refactor-loop Step 2

Rank improvements by:

1. **Auto-fixable** issues first (reworker.py `"auto": True`)
2. **Highest point-gain** per change
3. **Lint errors** before warnings

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/reworker.py" --diagnose --top 3
```

Present to user: "Top 3 Improvements: [1] add version to X (+10pts), [2] reduce body of Y (+15pts), [3] fix lint error Z"
