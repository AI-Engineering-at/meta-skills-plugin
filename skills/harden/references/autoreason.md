# Cross-Model Review — Hardening Step 3

For skills with score < 70:

## Autoreason

```bash
python3 scripts/autoreason-skills.py skills/weak-skill/SKILL.md --max-passes 2
```

## Judgment Day

For changed hooks or critical fixes:
- 2 blind judges (parallel, different models)
- See judgment-day SKILL.md for workflow

## CLI-Council Dispatch (for code fixes)

```bash
python3 ../cli-council/scripts/dispatch.py \
  --cli qwen --prompt "Fix ruff errors in hooks/quality-gate.py: [error list]"
```
