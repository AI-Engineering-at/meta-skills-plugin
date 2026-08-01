---
name: loop
description: >
  Autonomous work loop — bricht Tasks in Chunks, arbeitet sie ab, postet
  Status via Mattermost. Nutzt OpenCode-eigene Loop-Tools (kein Plugin).
  Trigger: "loop", "auto-loop", "mach weiter", "weiter im programm",
  "arbeite autonom", "continue working", "loop start".
allowed-tools: [Read, Write, Edit, Bash, Grep, Glob, WebSearch, WebFetch]
user-invocable: true
complexity: agent
version: 1.0.0
type: meta
category: automation
requires: []
produces: [loop-result, mattermost-status]
cooperative: false
---

# Loop — Autonomer Work-Loop

> Unabhängiger Meta-Skill. Kein Plugin, kein npm, kein Cache, kein Neustart.
> Nutzt OpenCode's eingebaute `opencode_loop_goal_*`-Tools + Mattermost.

## Wann verwenden?

- `loop "mach Feature X fertig"` — Task autonom abarbeiten
- `loop 10m "bug in Y fixen"` — mit Zeitlimit
- `mach weiter` — nach Unterbrechung weitermachen
- `weiter im programm` — nächsten Schritt ohne Eingabe

## Wie es funktioniert

### 1. ENTRANCE — Task erfassen

User sagt was. Du speicherst:
- **Ziel**: "implementier Login-Seite"
- **Dauer** (optional): "10m", "30m", "5 iterations"
- **Channel** (optional): Mattermost-Channel für Status-Updates

### 2. PLAN — In Chunks brechen

Breche das Ziel in 3-5 erledigbare Chunks. Erst Chunk 1 anfangen,
nicht alle auf einmal planen.

### 3. LOOP — Pro Chunk:

```
for each chunk:
  1. Arbeite (Code schreiben/recherchieren/testen)
  2. Verify (Test/lint/typecheck — nur bei Code-Änderungen)
  3. Status melden:
     → Poste nach Mattermost (primär, funktioniert immer):
        `aie-mm-mcp_post_with_discipline` an channel_id="md3fmixe9f8wjrh3ash6uy71xc" (#agent-tasks)
        Format: "[loop] 🔵 Chunk 2/5: Login-Formular ✅ — nächster: Submit-Handler"
     → Wenn aktiv: `opencode_loop_goal_progress(summary, next)` (optional, nur im --goal-Modus)
  4. Weiter mit nächstem Chunk
```

### 4. EXIT — Fertig oder Blocked

| Zustand | Tool | MM-Format |
|---------|------|-----------|
| Fertig ✅ | `opencode_loop_goal_complete` | `[loop] ✅ Task abgeschlossen: X` |
| Blockiert ⚠️ | `opencode_loop_goal_blocked` | `[loop] ⚠️ Blockiert bei Y — Grund: Z` |
| Abgebrochen 🛑 | — | `[loop] 🛑 Gestoppt` |

### 5. WIEDERAUFNAHME

Wenn User sagt "mach weiter" oder "weiter im programm":
- Prüfe ob ein unfertiger Loop-Kontext im Chat ist
- Falls ja: nimm den letzten Chunk und mach weiter
- Falls nein: frag "was soll ich autonom machen?"

## Regeln

1. **Niemals** `writeFile`→`rename` verwenden (JSCore-Bug in OpenCode).
   Stattdessen: `writeFileSync` oder direkten Write-Befehl.
2. **Niemals** Plugins installieren, npm ausführen oder Configs ändern.
3. **Nur ein Chunk pro Iteration** — nie 2 auf einmal.
4. Nach **jedem** Chunk: `opencode_loop_goal_progress` + Mattermost-Post.
5. Wenn Blockade länger als 2 Versuche: `opencode_loop_goal_blocked` + stopp.

## Integration

### Mattermost
Status-Posts gehen nach `#agent-tasks` via `aie-mm-mcp_post_with_discipline`.
Nutze `auto_thread_min: 10` — alle Posts zum selben Loop laufen im Thread.

### OpenCode-Loop-Tools (eingebaut, kein Plugin!)
- `opencode_loop_goal_progress(summary, next)` — Zwischenstand
- `opencode_loop_goal_complete(summary, evidence)` — Fertig
- `opencode_loop_goal_blocked(reason, needed)` — Blockiert
