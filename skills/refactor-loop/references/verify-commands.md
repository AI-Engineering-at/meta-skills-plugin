# Verify Commands — refactor-loop Step 5

Run SAME quality checks as Step 1. Compare:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/eval.py" --all --json
ruff check .
npm run lint 2>/dev/null
```

**Criteria:**
- Score improved or stayed same? AND
- Lint clean? AND
- Tests pass?

**PASS:** Commit with `git commit -m "refactor-loop: improvement N - description"`
**FAIL:** Revert with `git checkout -- .` Log what failed. Try different approach.
**Max 2 attempts per improvement, then SKIP.**
