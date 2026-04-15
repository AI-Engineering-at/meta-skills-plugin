# SCAN Commands — refactor-loop Step 1

Run ALL quality checks on target:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/eval.py" --all --json  # Skill/Agent scores
ruff check .                                                    # Python lint (if applicable)
npm run lint 2>/dev/null                                        # TS lint (if applicable)
```

Collect all issues. Note current scores as BASELINE.
