---
name: harden
description: Automated hardening loop. Scans all hooks, skills, scripts for quality issues. Triages by severity, auto-fixes what it can, dispatches cross-model review for complex issues.
trigger: harden, hardening, quality check all, full quality, meta harden, system check, check all, harden system
model: sonnet
allowed-tools: [Read, Bash, Glob]
user-invocable: true
complexity: agent
last-audit: 2026-04-14
version: 1.0.0
token-budget: 5000
---

# meta:harden — Automated Quality Hardening Loop

> Do not check individual files — harden the ENTIRE system.
> SCAN -> TRIAGE -> FIX -> VERIFY -> REPORT -> LOOP

## When to Use

After large changes (61+ files), before releases, weekly check, or "alles pruefen"/"haerten".

## The Loop

### 1. SCAN

Run ALL checks from `references/scan-checks.md`. Collect: `[{severity, category, file, description, auto_fixable}]`

### 2. TRIAGE

Group by treatment per `references/triage-table.md`:
- **Auto-fixable** → `reworker.py --apply`
- **Lint errors** → `ruff --fix`
- **Score < 70** → cross-model review (`references/autoreason.md`)
- **Security** → IMMEDIATE STOP, inform user

### 3. FIX

Auto-fix what's possible. Cross-model review for complex issues. Security = STOP.
Full rules: `references/triage-table.md`

### 4. VERIFY

Re-run SCAN after EVERY fix. All Scores >= 70 AND 0 Lint AND 0 CRITICAL? → REPORT. Else → TRIAGE (max 3 iterations, then ESCALATE).

### 5. REPORT

Short: Before/After summary. Long: `quality-snapshot.py --verbose`. Save to `oversight/hardening-{date}.md`

### 6. TERMINATE

APPROVED (all green), ESCALATED (issues after 3 iterations), or STOP (security finding).

## Modes

Full SCAN table, mode flags, integration details: `references/scan-checks.md`

## Principles

1. Deterministic first (0 token cost)
2. Auto-fix what is possible
3. Convergence (max 3 iterations)
4. Before/After ALWAYS
5. Security = IMMEDIATE STOP

## Reference Files

- references/scan-checks.md — SCAN checks, modes, integration
- references/triage-table.md — Triage classifications + FIX rules
- references/autoreason.md — Cross-model review workflow
