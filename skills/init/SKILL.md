---
name: init
version: 1.0.0
type: meta
category: meta
complexity: skill
description: Intelligent project entry point. Audit, goal definition, or bootstrap — context-dependent. Uses project-scan.py, eval.py, validate.py, skill-router and all existing skills.
trigger: init, meta init, project audit, project setup, project status, what is this project, new project, audit, status, analyze project
model: sonnet
allowed-tools: [Read, Bash, Glob, Agent]
user-invocable: true
token-budget: 2500
requires: []
produces: [project-scan-report, audit-results, setup-plan]
last-audit: 2026-04-14
---

# meta:init — Intelligent Project Entry Point

> Not a "Setup Wizard". Rather: "What do you need, and what do we already have?"
> Cooperative — work together, not generate for them.

## Modes

```
/meta-init                     → Auto (has .claude/? → Audit. Otherwise → Setup)
/meta-init audit               → Full project status
/meta-init goal "Performance"  → Goal-focused entry
/meta-init sdd "Feature X"    → Spec-Driven Development workflow
```

Detailed steps: `references/modes.md`

---

## Mode 1: AUDIT

When `.claude/` exists OR "audit", "wo stehen wir", "what's the status".

```bash
# Scan (silent) — use existing tools, don't re-implement
python meta-skills/scripts/project-scan.py --summary --all 2>/dev/null
python meta-skills/scripts/reworker.py --diagnose --top 5 2>/dev/null
git log --oneline -5 && git status --short
```

> **Windows note:** `2>/dev/null` requires POSIX shell. Use Git Bash or redirect with `2>nul` in cmd.exe.

Then: show status report (table: Stack, Score, Rules, Skills, Agents, Git).
Ask: "Here's the current state. What would you like to do next?"

Route based on answer:
- Improve score → `reworker.py --diagnose`
- New skill → `/meta:creator`
- Review → `/meta-judgment`
- Sync → `/full-sync`

---

## Mode 2: GOAL

When user provides a goal: Scan → filter by relevance → propose plan → delegate after "yes".
Only ask if goal is truly unclear. Act immediately if clear.

---

## Mode 3: SETUP

When NO `.claude/` exists: scan project → max 3 questions → show structure → create after "yes".

```bash
ls package.json pyproject.toml Cargo.toml go.mod 2>/dev/null
find . -maxdepth 2 -name "*.py" -o -name "*.ts" | wc -l
```

---

## Integration (ORCHESTRATOR — does nothing itself)

| Task | Delegates to |
|------|-------------|
| Measure quality | eval.py + validate.py |
| Find skill | skill-router |
| Create skill | meta:creator |
| Deployment | /deploy |
| Review | /meta-judgment |
| Document | /full-sync |
| Stack info | echo-log-context |

## Mode 4: SDD (Spec-Driven Development)

When user provides "sdd" OR task is obviously large (>3 files, architecture).

```
/meta-init sdd "Implement feature X"
```

**Size check FIRST:** "Is this a large task?"
- NO (1-2 files, < 1h) → "No SDD needed. Just do it."
- YES → Start SDD flow

**SDD Flow (uses EXISTING capabilities, builds nothing new):**

| Phase | Action | Delegates to |
|-------|--------|-------------|
| Explore | Understand codebase (read-only) | Agent (Explore, haiku) |
| Propose | Show 2-3 approaches, Joe picks | Inline |
| Tasks | Break into tasks | TaskCreate Tool |
| Apply | Implement tasks | dispatch skill (parallel, sonnet) |
| Verify | Check result | judgment-day OR verify skill |

**Execution Mode:** Interactive (default) — after each phase: summary + Joe decides.

**Skill Resolver:** Before Apply phase, load compact rules for sub-agents.

**Model Assignment:**

| Phase | Model | Reason |
|-------|-------|--------|
| Explore | haiku | Reads code, structural |
| Propose | sonnet | Architecture decisions |
| Tasks | sonnet | Mechanical breakdown |
| Apply | sonnet | Implementation |
| Verify | haiku | Validation against spec |

---

## Design Principles

1. **Scan first** — detect what exists, only ask what's necessary
2. **Max 3 questions** for Setup, 1 for Audit, 0-1 for Goal
3. **Show before write** — change nothing without confirmation
4. **Delegate** — use existing skills, never duplicate
5. **Cooperative** — user decides direction
6. **SDD organic** — only for large tasks, never forced

## Examples

### Example 1: First time in a project

```bash
/meta-init
# Scans project, shows status, asks what you want to do
```

### Example 2: Set a goal

```bash
/meta-init goal "Improve API performance"
# Scans, filters relevant files, proposes plan
```

### Example 3: Large feature with SDD

```bash
/meta-init sdd "Implement user authentication"
# Explores codebase → proposes approaches → breaks into tasks → implements
```
