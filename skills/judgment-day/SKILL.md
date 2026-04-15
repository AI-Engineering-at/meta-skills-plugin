---
name: judgment-day
description: Spawn 2 blind parallel judges, synthesize findings, fix, re-judge. Never approve without independent confirmation.
trigger: judgment day, adversarial review, blind review, dual review, code review, quality gate, pruefen, review durch 2
model: haiku
allowed-tools: [Agent, Read, Grep]
user-invocable: true
complexity: agent
last-audit: 2026-04-14
version: 1.0.0
token-budget: 4000
---

# Judgment Day — 2 Blind Judges + Convergence Gate

> One reviewer misses what two independent ones catch.

## Decision Tree

```
Target code changed?
  ├─ NO  → skip (nothing to review)
  └─ YES
       ├─ Round = 0? → LAUNCH 2 JUDGES (parallel, blind, haiku) → Synthesis
       ├─ Round ≤ 2? → FIX found → Re-Judge
       └─ Round > 2? → ESCALATE (Joe decides)
```

## Step 1: Launch 2 Judges

Both via `Agent` tool with `model: haiku`, `run_in_background: true`. Identical prompt — neither knows about the other.
Full prompt: `references/trigger.md`

## Step 2: Synthesize

Classification per `references/synthesis.md`:
- Both find → **Confirmed** → must fix
- Only one → **Suspect** → Joe decides
- Contradict → **Conflict** → Joe decides
- WARNING (theoretical) → **INFO** → no fix, no re-judge

## Step 3: Fix

Only confirmed issues. No refactoring.
Full prompt: `references/fix-rejudge.md`

## Step 4: Re-Judge Gate

Confirmed CRITICALs → mandatory re-judge (both, parallel). 0 CRITICALs + 0 real WARNINGs → **APPROVED**.
After 2 fix rounds → ask Joe: continue or **ESCALATED**.

## Terminal States

APPROVED: 0 confirmed CRITICALs + 0 real WARNINGs. ESCALATED: Joe stops after 2+ fix rounds.

## Iron Laws

- **Never** commit/push between fix and re-judge
- **Never** say APPROVED before gate passes
- **Never** synthesize yourself — use the classification table

## Reference Files

- references/trigger.md — Judge agent prompt
- references/synthesis.md — Classification table + rules
- references/fix-rejudge.md — Fix + re-judge prompt
