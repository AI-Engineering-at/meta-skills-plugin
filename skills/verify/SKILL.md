---
name: verify
description: Verification gate before any completion claim. Runs REAL commands and provides EVIDENCE, not promises. NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE.
trigger: verify, verification, before complete, fertig, abschluss, are we done, alles getestet, proof, evidence, beweis
model: sonnet
allowed-tools: [Bash, Read, Grep]
user-invocable: true
complexity: skill
last-audit: 2026-04-14
version: 1.0.0
token-budget: 3000
type: meta
category: quality
requires: []
produces: [quality-report]
cooperative: false
---

# Verify — Evidence Before Claims

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

## The Gate Function (5 Steps)

For EVERY claim you're about to make:

1. **IDENTIFY** — What command proves this claim?
2. **RUN** — Execute the FULL command (fresh, not cached)
3. **READ** — Full output, exit code, failure count
4. **VERIFY** — Does the output confirm the claim?
5. **ONLY THEN** — Make the claim with evidence

## Verification Matrix

| Claim | Requires | NOT Sufficient |
|-------|----------|----------------|
| Tests pass | Test output: 0 failures | "Should pass", previous run |
| Lint clean | Lint output: 0 errors | "Partial check", extrapolation |
| Build succeeds | Build command: exit 0 | "Looks good", linter passing |
| Bug fixed | Test original symptom: passes | "Code changed, assumed fixed" |
| Agent completed | VCS diff shows changes | Agent reports "success" |
| Requirements met | Line-by-line checklist | "Tests passing" |

## Evidence Format

Run all applicable verification commands and present:

```
VERIFICATION EVIDENCE (YYYY-MM-DD HH:MM UTC):
- lint: ruff check -> 0 errors (exit 0) [PASS]
- tests: pytest -> 12/12 pass (exit 0) [PASS]
- build: npm run build -> exit 0 [PASS]
- uncommitted: git status -> clean [PASS]
ALL GATES PASSED — safe to claim completion.
```

If ANY gate fails:
```
VERIFICATION EVIDENCE (YYYY-MM-DD HH:MM UTC):
- lint: ruff check -> 3 errors (exit 1) [FAIL]
  E302: expected 2 blank lines (line 45)
  ...
GATES FAILED — DO NOT claim completion. Fix first.
```

## Red Flags — STOP

If you catch yourself thinking:
- "Should work now" -> RUN the verification
- "I'm confident" -> Confidence != Evidence
- "Just this once" -> NO exceptions to this Iron Law
- "Linter passed" -> Linter != Compiler != Tests
- "Agent said success" -> Verify independently
- "I already tested" -> Run it AGAIN (fresh)

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Should work" | RUN it. 5 seconds vs hours of debugging. |
| "I'm confident" | Then verification is quick. Run it. |
| "Tests are slow" | Slow tests > shipping broken code. |
| "Just a small change" | Small changes break things too. |
| "Already tested manually" | Manual != Automated. Run the suite. |

## Examples

### Example 1: Verifying a feature implementation

```
VERIFICATION EVIDENCE (2026-04-14 10:30 UTC):
- lint: ruff check -> 0 errors (exit 0) [PASS]
- tests: pytest -> 15/15 pass (exit 0) [PASS]
- build: npm run build -> exit 0 [PASS]
- uncommitted: git status -> clean [PASS]
ALL GATES PASSED — safe to claim completion.
```

### Example 2: Catching a false completion

```
Claim: "Bug is fixed"
Verification: pytest test_bug.py → FAILS with same error
Action: DO NOT claim completion. Investigate further.
```
