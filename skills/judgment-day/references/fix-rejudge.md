# Fix-Agent + Re-Judge Gate

## Fix Agent Launch (when Joe agrees)

Launch a SEPARATE Agent (model: sonnet) — NOT one of the judges:

```
Fix ONLY the confirmed issues from Judgment Day Round {N}:

1. {exact finding 1}
2. {exact finding 2}
...

Scope: ONLY fix the listed issues.
Do NOT refactor. Do NOT change code not flagged.
Do NOT fix Suspect or INFO items.
```

## Re-Judge Gate (MANDATORY after fixes)

After Fix-Agent completes:

1. **Do NOT commit or push** — code changed but unverified
2. Launch **both judges again** with identical prompt (see `references/trigger.md`)
3. Target: the SAME files, now with fixes applied
4. Synthesize new verdict (see `references/synthesis.md`)

## Convergence Rules

| After Fix Round | Situation | Action |
|-----------------|-----------|--------|
| Round 1 fix → Round 2: 0 CRITICALs + 0 real WARNINGs | **APPROVED** | Done, safe to commit |
| Round 1 fix → Round 2: CRITICALs remain | Continue | Fix again, Round 3 |
| Round 2 fix → Round 3: CRITICALs remain | Ask Joe | "Continue or ESCALATE?" |
| Round N > 2 | **ESCALATED** | Stop, document remaining |

## Terminal State Checklist

Before declaring APPROVED:
- [ ] At least 2 rounds completed (or Round 1 was CLEAN)
- [ ] 0 confirmed CRITICALs in current round
- [ ] 0 confirmed real WARNINGs in current round
- [ ] All fixes verified by re-judge

Before declaring ESCALATED:
- [ ] At least 2 fix rounds attempted
- [ ] CRITICAL or real WARNING issues remain
- [ ] Joe explicitly stopped or timeout reached
- [ ] Remaining issues documented
