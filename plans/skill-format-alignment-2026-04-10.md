# meta-skills — Skill Format Alignment Plan

> Erstellt: 2026-04-10 | Basiert auf: mattpocock/skills Analyse + AgentSkills.io Standard
> Ziel: Skills portabel machen OHNE Plugin-Features zu verlieren

## Analyse-Ergebnis

mattpocock/skills ist KEIN Plugin — es ist eine Sammlung portabler Skills mit minimalem Format.
Der Industry-Standard (AgentSkills.io / npx skills) braucht nur 2 Frontmatter-Felder: `name` + `description`.
Unser meta-skills ist ein vollstaendiges Claude Code Plugin mit Hooks, Agents, Commands, Scripts.

**Beide Ansaetze sind korrekt fuer ihren Zweck.** Aber unsere SKILL.md-Dateien sollten
dem Standard naeher kommen, damit sie:
- Kuerzer sind (weniger Context-Window-Verbrauch)
- Exportierbar sind (community-tauglich)
- Konsistenter sind (gleiche Konventionen wie der Rest der Welt)

## Was sich aendern soll

### 1. SKILL.md Frontmatter trimmen

**Jetzt (15+ Felder):**
```yaml
name, description, complexity, model, allowed-tools, user-invocable,
version, requires, produces, learning-refs, last-verified, type,
category, token-budget, last-audit, cooperative, team-workers,
team-consolidator, argument-hint
```

**Neu — Zwei Ebenen:**

**In SKILL.md (Agent sieht das):**
```yaml
name, description, complexity, model, allowed-tools, user-invocable
```

**In skill-registry.json (Tooling sieht das):**
```json
{
  "creator": {
    "version": "0.2.0",
    "category": "meta",
    "token-budget": 25000,
    "last-verified": "2026-04-10",
    "requires": [],
    "produces": ["new-skill"],
    "team-workers": [],
    "team-consolidator": null
  }
}
```

Validate.py liest beide Quellen zusammen.

### 2. 100-Zeilen-Regel fuer SKILL.md

| Skill | Jetzt | Ziel | Aktion |
|-------|-------|------|--------|
| creator | 262 | <100 | Phase 3-5 in references/ verschieben |
| doc-updater | 150 | <100 | Execution Flow in references/ |
| knowledge | 140 | <100 | Mode-Details in references/ |
| feedback | OK | OK | — |
| design | OK | OK | — |

### 3. Description als Routing-Signal

**Pattern:** Erster Satz = was es tut. Zweiter Satz = "Use when [triggers]".

```yaml
# Vorher:
description: >
  Cooperative skill creation. Analyzes session patterns, suggests skills,
  builds them WITH the user. 5-phase process with token optimization pass.
  Trigger: create skill, neuer skill, skill erstellen, ...

# Nachher:
description: >
  Creates new skills cooperatively using a 5-phase process with token optimization.
  Use when: "create skill", "neuer skill", "skill erstellen", "build skill",
  "was machen wir oft", "new skill"
```

### 4. Reference-Files Konvention

**mattpocock:** `REFERENCE.md` neben `SKILL.md` (flach)
**Unser Standard:** `references/` Subdirectory (organisiert)

**Entscheidung:** `references/` beibehalten — wir haben mehr Dateien pro Skill als mattpocock.
Aber: `cat` Commands in SKILL.md durch relative Links ersetzen wo moeglich.

### 5. Export-Pfad (Zukunft)

Skills die exportiert werden koennten:
- `feedback` — bidirektionaler Session-Review (universell)
- `creator` — Skill-Erstellung (universell)
- `tdd` patterns (wenn wir einen haetten)

Export-Prozess:
1. IP-Adressen → Platzhalter (`<server>`, `<notebook-api>`)
2. Vault-Referenzen → ENV-Variablen
3. Frontmatter auf name+description reduzieren
4. In `exports/` Verzeichnis schreiben

## Was NICHT geaendert wird

- **Hooks** (SessionInit, Stop, PostToolUse, UserPromptSubmit) → Claude Code Feature, kein Standard
- **Agents** (doc-scanner-*, session-analyst) → Claude Code Sub-Agents
- **Commands** (meta-create, meta-docs, etc.) → Claude Code Slash-Commands
- **Scripts** (validate.py, eval.py, statusline.py) → Deterministic Python, zero LLM tokens
- **Self-Improving Layer** (memory.md, corrections.md) → Unique Feature

## Reihenfolge

1. skill-registry.json erstellen (Metadaten aus SKILL.md extrahieren)
2. validate.py anpassen (Registry als zweite Quelle)
3. creator SKILL.md auf <100 Zeilen trimmen
4. doc-updater SKILL.md auf <100 Zeilen trimmen
5. Descriptions auf "Use when..." Pattern umstellen
6. Export-Mechanismus (spaeter, nach Bedarf)
