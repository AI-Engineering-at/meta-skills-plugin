---
name: creator
description: Creates new skills cooperatively using a 5-phase process with token optimization. Use when: "create skill", "neuer skill", "skill erstellen", "build skill", "was machen wir oft", "new skill"
complexity: agent
model: sonnet
allowed-tools: [Read, Write, Bash, Grep]
user-invocable: true
last-audit: 2026-04-14
version: 1.0.0
token-budget: 5000
---

# meta:creator — Cooperative Skill Creation

> Build skills WITH the user, not FOR the user.
> Token efficiency is not a feature — it is the architecture.

## Process Overview

5-phase cooperative workflow. Each phase asks ONE question at a time. Never skip phases.
Full details: `references/creation-process.md` (Phase 1-2), `references/phase-3-5-workflow.md` (Phase 3-5)

## Phase 0: LOAD CONTEXT (silent)

Load: `self-improving/memory.md`, `self-improving/corrections.md`, `.claude/knowledge/USER_PATTERNS.md` (if exists).
Learn preferences, corrections, user patterns before first question.

## Phase 1: CHECK (Does this need to exist?)

Run duplicate check. Determine type per Rule A5: Skill (ONE process), Agent (Workflow), Team (Parallel tasks).
Decision tree: `references/creation-process.md`

## Phase 2: POSITION (Where in the ecosystem?)

Ask 3 questions sequentially: problem solved, who uses it, primary output.
Derive: model, category, platforms from answers.

## Phase 3: DEVELOP (Cooperative)

Ask user ONE question at a time: steps, tools, edge cases, testing strategy.
Full workflow: `references/phase-3-5-workflow.md`

## Phase 4: WRITE (Invest tokens here)

6-step process: Draft → Token analysis → Optimization → Quality check → Cross-platform check → User review.
Team creation: load `references/team-creation.md`. Full workflow: `references/phase-3-5-workflow.md`

## Phase 5: REFLECT (Self-improving)

Save files, update learning layer, ask for feedback, provide tip, summarize.
Full workflow: `references/phase-3-5-workflow.md`

## Export

When user says "export/share skill": run 3-step sanitize → format → export from `references/export-process.md`

## Reference Files

- references/creation-process.md — Phase 1-2 decision trees
- references/phase-3-5-workflow.md — Phase 3-5 full workflows
- references/team-creation.md — Team field definitions
- references/quality-checklist.md — Quality verification items
- references/export-process.md — Skill export workflow
- references/token-optimization.md — Token optimization techniques
- references/audit-process.md — Skill audit workflow
- references/frontmatter-schema.md — Frontmatter field definitions
