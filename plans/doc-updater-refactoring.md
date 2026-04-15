# Plan: doc-updater Refactoring zu Agent-Team

> Erstellt: 2026-04-10 | Status: OFFEN | Umsetzen mit: meta-skills Creator
> Trigger: `/doc-updater` bricht in langen Sessions ab (Context-Overflow)

## Problem
doc-updater ist ein Skill der ~27 Dateien in einen Kontext laedt. Sprengt das Context-Window.

## Loesung
Refactoring zu Agent-Team mit 5 Agents:

| Agent | Model | Tier | Aufgabe |
|-------|-------|------|---------|
| doc-scanner-core | haiku | Tier 1 (8 Dateien) | Lesen + Stale-Felder identifizieren |
| doc-scanner-infra | haiku | Tier 2 (9 Dateien) | Lesen + Stale-Felder identifizieren |
| doc-scanner-agents | haiku | Tier 3+4 (10 Dateien) | Lesen + Stale-Felder identifizieren |
| doc-editor | sonnet | Stale-Summaries | Gezielte Edits, Commit |
| doc-auditor | opus | Git-Diff | GAP-Analyse, Audit |

## Ablauf
1. Phase 1 SCAN: 3x Haiku parallel (je 8-10 Dateien)
2. Phase 2 EDIT: 1x Sonnet (nur stale Felder, ~2k Tokens statt 60k)
3. Phase 3 AUDIT: 1x Opus (optional, GAP-Analyse)

## Presets
- `quick` — nur Tier 1
- `infra` — Tier 1+2
- `full` — alle Tiers + Opus-Audit

## Umsetzung
Mit meta-skills Creator in frischer Session. Aktueller SKILL.md:
`phantom-ai/.claude/skills/doc-updater/SKILL.md`

## Dateien zu erstellen
```
meta-skills/agents/doc-scanner-core.md
meta-skills/agents/doc-scanner-infra.md
meta-skills/agents/doc-scanner-agents.md
meta-skills/agents/doc-editor.md
meta-skills/agents/doc-auditor.md
```

## Quell-Analyse
Aktueller SKILL.md hat alle Tier-Definitionen + Verification Commands + Checklisten.
Alles in die neuen Agents aufteilen.
