---
name: refactor-loop
description: Automated refactoring with objective verification. Scans target for quality issues, makes ONE improvement per cycle, verifies with tests/lint. Reverts on failure. Loops until done or max reached.
trigger: refactor loop, quality improvement, automated refactoring, improve quality, score verbessern, qualitaet verbessern
model: sonnet
allowed-tools: [Read, Write, Bash, Grep]
user-invocable: true
complexity: agent
last-audit: 2026-04-14
version: 1.0.0
token-budget: 4000
---

# Refactor-Loop — Scan, Improve, Verify

> "A generator that evaluates its own work converges on mediocrity."
> — adversarial-dev principle. eval.py is the EXTERNAL evaluator.

## Overview

Automated scan-improve-verify cycle. ONE improvement per iteration.
Reverts on verification failure. Never ships broken code.

## The 6-Step Cycle

### Step 1: SCAN

Run ALL quality checks on target:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/eval.py" --all --json  # Skill/Agent scores
ruff check .                                                    # Python lint (if applicable)
npm run lint 2>/dev/null                                        # TS lint (if applicable)
```

Collect all issues. Note current scores as BASELINE.

### Step 2: PRIORITIZE (Top 3)

From eval.py results + lint output, rank improvements:
1. **Auto-fixable** issues first (reworker.py `"auto": True`)
2. **Highest point-gain** per change
3. **Lint errors** before warnings

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/reworker.py" --diagnose --top 3
```

Present to Joe: "Top 3 Improvements: [1] add version to X (+10pts), [2] reduce body of Y (+15pts), [3] fix lint error Z"

### Step 3: GIT CHECKPOINT

Create known-good rollback point:
```bash
git add -A && git commit -m "refactor-loop: checkpoint before improvement N"
```

### Step 4: IMPLEMENT ONE

Make exactly ONE improvement. Follow reworker.py diagnosis.
- NO "while I'm here" improvements
- NO bundled changes
- ONE logical change only

### Step 5: VERIFY

Run SAME quality checks as Step 1. Compare:
- Score improved or stayed same? AND
- Lint clean? AND
- Tests pass?

**PASS:** Commit with `git commit -m "refactor-loop: improvement N - description"`
**FAIL:** Revert with `git checkout -- .` Log what failed. Try different approach.
**Max 2 attempts per improvement, then SKIP.**

### Step 6: LOOP

Move to next improvement. Stop when:
- All 3 improvements done, OR
- Max iterations reached (default: 9 = 3 improvements x 3 attempts)

Present FINAL SUMMARY:
```
REFACTOR-LOOP COMPLETE:
  Before: avg 72/100 (3 below 70, 5 lint errors)
  After:  avg 81/100 (0 below 70, 0 lint errors)
  Changes: 3 improvements in 5 iterations
  Commits: refactor-loop: improvement 1/2/3
```

## Red Flags — STOP

- Making more than ONE change per iteration
- Skipping verification
- Not reverting on failure
- Changing files unrelated to the current improvement
- Score DECREASED after change (revert immediately)

## Reference Files

- references/scan-commands.md — Detailed SCAN check commands
- references/prioritization.md — Improvement prioritization rules
- references/verify-commands.md — Verification commands per project type

## Examples

### Example 1: Improve a single skill

```bash
# Scan and improve one skill
refactor-loop skills/dispatch/SKILL.md

# Output:
# Before: Score 65/100 (body too long, missing version)
# After:  Score 82/100 (split into references, version added)
# Changes: 2 improvements in 3 iterations
```

### Example 2: Fix lint errors in a directory

```bash
refactor-loop src/

# Each iteration:
# 1. SCAN → ruff finds 5 errors
# 2. PRIORITIZE → fix unused imports first
# 3. GIT CHECKPOINT
# 4. IMPLEMENT → remove unused imports
# 5. VERIFY → ruff check passes
# 6. LOOP → next improvement
```
