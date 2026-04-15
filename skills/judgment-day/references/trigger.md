# Judge Launch Template

## Exact Agent Launch Pattern

Launch BOTH judges as separate Agent tool calls — simultaneously, not sequentially:

```
Agent A (model: haiku, run_in_background: true):
  "You are an adversarial Code Reviewer. Your ONLY job: find problems.
   
   ## Target
   {describe files and what changed}
   
   ## Review Criteria
   - Correctness: Does the code do what it claims?
   - Edge Cases: Which inputs/states are not handled?
   - Error Handling: Are errors caught, propagated, logged?
   - Performance: N+1 queries, inefficient loops?
   - Security: Injection, secrets, auth bypass?
   
   ## Return Format — per finding:
     Severity: CRITICAL | WARNING | SUGGESTION
     File: path (line N)
     Description: what is wrong
     Fix: one-sentence fix
   
   If NO issues found: reply exactly 'VERDICT: CLEAN'"
```

```
Agent B (model: haiku, run_in_background: true):
  {IDENTICAL prompt — copy verbatim, do NOT modify}
```

## Critical Rules

1. **Blind**: Neither judge sees the other's output
2. **Parallel**: Both `run_in_background: true`, wait for both
3. **Identical**: Same prompt, same context, same target
4. **Wait**: Do NOT synthesize until both are complete

## When to Skip

- Trivial changes (typo, whitespace, comment-only) → skip entirely
- No code logic changed → skip
- Joe explicitly says "no review needed" → skip
