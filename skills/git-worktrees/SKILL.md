---
name: git-worktrees
description: Use when starting feature work that needs isolation from current workspace or before executing implementation plans. Creates isolated git worktrees with smart directory selection and safety verification.
trigger: worktree, isolate, isolated workspace, parallel branch
model: haiku
allowed-tools: [Bash, Read, Grep]
user-invocable: true
complexity: skill
last-audit: 2026-04-14
version: 1.0.0
token-budget: 2000
type: utility
category: git
requires: []
produces: [worktree]
cooperative: false
---

# Using Git Worktrees

## Overview

Git worktrees create isolated workspaces sharing the same repository,
allowing work on multiple branches simultaneously without switching.

**Core principle:** Systematic directory selection + safety verification = reliable isolation.

## Directory Selection Process

Follow this priority order:

### 1. Check Existing Directories

```bash
ls -d .worktrees 2>/dev/null     # Preferred (hidden)
ls -d worktrees 2>/dev/null      # Alternative
```

> **Windows note:** On cmd.exe, use `dir /ad .worktrees 2>nul` instead of `ls -d`. Or use Git Bash.

**If found:** Use that directory. Both exist? `.worktrees` wins.

### 2. Check CLAUDE.md

```bash
grep -i "worktree.*director" CLAUDE.md 2>/dev/null
```

**If preference specified:** Use it without asking.

### 3. Ask Joe

If no directory exists and no CLAUDE.md preference, ask.

## Safety Verification

### For Project-Local Directories

**MUST verify directory is ignored before creating worktree:**

```bash
git check-ignore -q .worktrees 2>/dev/null || git check-ignore -q worktrees 2>/dev/null
```

**If NOT ignored:** Add to .gitignore, commit, then proceed.

**Why critical:** Prevents accidentally committing worktree contents.

## Creation Steps

### 1. Detect Project Name
```bash
project=$(basename "$(git rev-parse --show-toplevel)")
```

### 2. Create Worktree
```bash
git worktree add "$path" -b "$BRANCH_NAME"
cd "$path"
```

### 3. Run Project Setup (auto-detect)
```bash
[ -f package.json ] && npm install
[ -f requirements.txt ] && pip install -r requirements.txt
[ -f pyproject.toml ] && poetry install
[ -f Cargo.toml ] && cargo build
[ -f go.mod ] && go mod download
```

### 4. Verify Clean Baseline
Run tests to ensure worktree starts clean. If tests fail: report, ask Joe.

### 5. Report Location
```
Worktree ready at <full-path>
Tests passing (<N> tests, 0 failures)
Ready to implement <feature-name>
```

## Quick Reference

| Situation | Action |
|-----------|--------|
| `.worktrees/` exists | Use it (verify ignored) |
| `worktrees/` exists | Use it (verify ignored) |
| Both exist | Use `.worktrees/` |
| Neither exists | Check CLAUDE.md -> Ask Joe |
| Directory not ignored | Add to .gitignore + commit |
| Tests fail during baseline | Report failures + ask Joe |

## Common Mistakes

- **Skipping ignore verification** -- Worktree contents pollute git status
- **Assuming directory location** -- Follow priority: existing > CLAUDE.md > ask
- **Proceeding with failing tests** -- Can't distinguish new from pre-existing bugs
- **Hardcoding setup commands** -- Auto-detect from project files

## Integration

**Called by:** meta-skills:init (when isolation needed), any implementation plan
**Pairs with:** commit-commands:commit-push-pr (for cleanup after work)
