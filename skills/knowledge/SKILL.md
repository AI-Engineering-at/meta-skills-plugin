---
name: knowledge
description: Unified system for errors, learnings, and knowledge retrieval using a 4-layer funnel (session-start, checklist, detail files, RAG). Use when: "knowledge", "wissen", "fehler dokumentieren", "learning dokumentieren", "was wissen wir", "gotcha", "checkliste", "error log", "learning log", "wissen abrufen", "knowledge search"
complexity: skill
model: haiku
allowed-tools: [Read, Edit, Bash, Grep]
user-invocable: true
last-audit: 2026-04-14
version: 1.0.0
token-budget: 3000
type: meta
category: documentation
requires: []
produces: [knowledge-entry]
cooperative: true
---

# meta:knowledge — Knowledge Funnel

> ONE system, ONE chain, NO duplicates.
> Errors and learnings exist in exactly ONE place — everything else references.

## Architecture: 4-Layer Funnel

```
Layer 1: Session-Start Injection (auto, session_init.py)
Layer 2: Checklist (auto-loaded, .claude/rules/08-checkliste.md)
Layer 3: Detail Files (on-demand) — ERRORS.md, LEARNINGS.md
Layer 4: RAG (query-based) — open-notebook, Honcho
```

## Modes

| Mode | Trigger | What |
|------|---------|------|
| LOG | "document error", "record learning" | Append error/learning with E/L number |
| SEARCH | "what do we know", "has this happened" | Search open-notebook → local → Honcho |
| SYNC | "sync knowledge" | Push ERRORS.md/LEARNINGS.md to open-notebook |
| AUDIT | "knowledge audit", "check knowledge" | Verify E/L consistency, checklist refs |

See `references/modes.md` for the complete workflows of each mode.

## Integration with other meta-skills

| Skill | Uses Knowledge how |
|-------|-------------------|
| meta:feedback | Writes new learnings via LOG mode |
| meta:creator | Reads corrections.md (Phase 0) + LEARNINGS via SEARCH |
| meta:init | Uses AUDIT mode during project scan |
| session-end-sync.py | Uses SYNC mode at session end |

## Rules

1. **ONE file per type:** ERRORS.md for errors, LEARNINGS.md for learnings. No second format.
2. **Checklist is a signpost:** 08-checkliste.md contains ONLY one-liners with E/L reference, never details.
3. **open-notebook is the search engine:** For semantic search always ask RAG first.
4. **Honcho is session context:** For "what did we do last session" ask Honcho.

## Examples

```
knowledge log error           → Reads last E-number, assigns E042, appends to ERRORS.md
knowledge search "retry"      → Searches open-notebook → local files → Honcho
knowledge log learning        → Records learning with L-number
```

## Reference Files

- references/modes.md — Complete LOG, SEARCH, SYNC, AUDIT workflows
