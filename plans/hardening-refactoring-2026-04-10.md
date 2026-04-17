# meta-skills Plugin — Hardening + Refactoring Plan

> Erstellt: 2026-04-10 | **Phase 1-3 ERLEDIGT** (gleiche Session)
> Phase 4 nach Bedarf. Skill-Format-Alignment: separater Plan.

## Audit-Ergebnis (2026-04-10) — GEFIXT

~~**Plugin ist NICHT korrekt registriert.** Slash-Commands erscheinen nicht.~~
**GEFIXT:** Plugin registriert, 8 Slash-Commands, 6 Agents, alle Hooks funktional.
- Root Cause: Fehlt in `installed_plugins.json`
- SessionStart Hook ungueltig
- Commands nicht namespaced
- doc-updater sprengt Context-Window

---

## Phase 1 — Kritische Fixes (sofort)

### Fix 1.1: Plugin in installed_plugins.json registrieren
**Datei:** `~/.claude/plugins/installed_plugins.json`
**Aktion:** Eintrag hinzufuegen:
```json
"meta-skills": [{
  "scope": "local",
  "installPath": "~\\Documents\\phantom-ai\\meta-skills",
  "version": "2.0.0",
  "installedAt": "2026-04-09T14:06:00.000Z",
  "projectPath": "~\\Documents\\phantom-ai"
}]
```
**Verifizierung:** Claude Code neustarten, `/meta` tippen, Commands muessen erscheinen.

### Fix 1.2: SessionStart Hook entfernen
**Datei:** `meta-skills/hooks/hooks.json`
**Problem:** `SessionStart` ist KEIN gueltiger Hook-Event in Claude Code
**Gueltige Events:** PreToolUse, PostToolUse, UserPromptSubmit, Stop, SubagentStop, Notification
**Aktion:** SessionStart-Block entfernen. session-init.py Logik in UserPromptSubmit einbauen (First-Prompt-Detection via State-File).

### Fix 1.3: Commands namespacing
**Problem:** Commands heissen `create.md`, `audit.md` etc. → erscheinen als `/create`, `/audit` — kollidiert mit anderen Plugins
**Aktion:** Umbenennen zu `meta-create.md`, `meta-discover.md`, `meta-audit.md`, `meta-design.md`
**Ergebnis:** `/meta-create`, `/meta-discover`, `/meta-audit`, `/meta-design`

---

## Phase 2 — doc-updater als Agent-Team (siehe doc-updater-refactoring.md)

### Agents zu erstellen:
```
meta-skills/agents/doc-scanner-core.md      # haiku — Tier 1 (8 Dateien)
meta-skills/agents/doc-scanner-infra.md     # haiku — Tier 2 (9 Dateien)
meta-skills/agents/doc-scanner-agents.md    # haiku — Tier 3+4 (10 Dateien)
meta-skills/agents/doc-editor.md            # sonnet — Edits schreiben
meta-skills/agents/doc-auditor.md           # opus — GAP-Analyse
```

### Orchestrator:
`meta-skills/skills/doc-updater/SKILL.md` (migriert aus phantom-ai/.claude/skills/)
- complexity: team
- 3 Presets: quick (Tier 1), infra (Tier 1+2), full (alle + Opus)

---

## Phase 3 — Hardening

### 3.1: Hook Error-Handling
**Problem:** Hooks haben keinen Error-Recovery — wenn ein Script crasht, gibt es kein Logging
**Aktion:** Wrapper-Funktion in `hooks/lib/` die stdout/stderr in Logfile schreibt
**Logfile:** `~/.claude/plugins/data/meta-skills/hook-errors.log`

### 3.2: Plugin Health-Check Command
**Neuer Command:** `meta-status.md`
**Funktion:** Zeigt Plugin-Status, Hook-Status, letzte Fehler, Skill-Anzahl, Agent-Anzahl
**Model:** haiku

### 3.3: Skill-Validierung bei Load
**Problem:** Skills mit falscher Frontmatter werden still ignoriert
**Aktion:** validate-skills.py erweitern — prueft ALLE Skills auf:
- Pflichtfelder (name, description, user-invocable, model)
- complexity vs. Ort (skill in skills/, agent in agents/)
- Referenzierte Tools existieren
- Token-Budget realistisch
**Trigger:** Als PostToolUse Hook oder manuell via `/meta-audit`

### 3.4: Config-Schema Validierung
**Problem:** config.json hat kein Schema — falsche Keys werden still ignoriert
**Aktion:** JSON Schema erstellen, bei Plugin-Load validieren

### 3.5: Statusline Resilience
**Problem:** Wenn statusline.py crasht, gibt es keinen Fallback
**Aktion:** try/except in statusline.py, bei Fehler einfaches "meta-skills OK" ausgeben

---

## Phase 4 — Erweiterungen

### 4.1: Session-Lifecycle Verbesserung
- First-Prompt-Detection statt SessionStart Hook
- Session-Ende Summary automatisch an Honcho senden
- Token-Verbrauch pro Session tracken

### 4.2: Skill-Discovery Automation
- Automatisch neue Skills erkennen wenn Dateien hinzugefuegt werden
- skill-catalog.json automatisch updaten

### 4.3: Correction-Detect Verbesserung
- Patterns erweitern (aktuell zu wenig Trigger)
- Corrections in Honcho + open-notebook speichern

---

## Umsetzungs-Status

1. ✅ Fix 1.1 (installed_plugins.json) — commit `88a6b20f`
2. ✅ Fix 1.2 (SessionStart → UserPromptSubmit) — commit `88a6b20f`
3. ✅ Fix 1.3 (Command Namespacing) — commit `88a6b20f`
4. ✅ Phase 2 (doc-updater Team) — 5 Agents + Orchestrator — commits `cca05883`, `5afda413`
5. ✅ Phase 3 (Hardening) — Error-Handling, Health-Check, Config-Validierung — commit `0c87d984`
6. ✅ Statusbar Audit — 2 CRITICAL + 6 WARNING gefixt — commits `5137464e`, `c493e397`
7. ✅ Creator Optimierung — Score 78→86, -13% Tokens — commit `c272e3c6`
8. ⬜ Phase 4 (Erweiterungen) — nach Bedarf
9. ⬜ Skill-Format-Alignment — separater Plan: `skill-format-alignment-2026-04-10.md`

## Offene Fragen (beantwortet)
- Plugin ist projektspezifisch (phantom-ai) installiert mit `scope: local` ✅
- doc-updater nach meta-skills migriert, alter deprecated (Rule G8) ✅
- Test: validate.py + eval.py decken Validierung + Qualitaet ab ✅
