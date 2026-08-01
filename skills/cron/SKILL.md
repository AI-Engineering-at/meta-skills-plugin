---
name: cron
description: >
  Einfacher Cron-Job — plant Tasks zu bestimmten Zeiten.
  Startet sie automatisch oder postet Erinnerung nach Mattermost.
  Unabhängiger Meta-Skill. Kein Plugin, kein npm.
  Trigger: "cron", "plane ein", "um 15:00", "erinnere mich",
  "scheduled task", "timer", "zeitgesteuert".
allowed-tools: [Read, Write, Edit, Bash, Grep, Glob, WebSearch, WebFetch]
user-invocable: true
complexity: agent
version: 1.0.0
type: meta
category: automation
requires: []
produces: [scheduled-task, mattermost-reminder]
cooperative: false
---

# Cron — Einfacher Task-Scheduler

> Plant Tasks zu bestimmten Zeiten. Startet automatisch wenn OpenCode läuft.
> Für 24/7-Cron: Cluster-Watcher nötig (swarm1). Für einmalige Tasks: reicht dieser Skill.

## Wann verwenden?

- `cron 15:00 "push code"` — Task für 15:00 planen
- `cron 15:00 mm "erinnere mich an Meeting"` — Nur Erinnerung nach Mattermost
- `cron 15:00 loop "mach Feature X"` — Task + Loop starten
- `cron daily 09:00 "daily standup"` — Täglich wiederholen
- `cron list` — Alle geplanten Tasks anzeigen
- `cron cancel 1` — Task #1 löschen

## Wie es funktioniert

### 1. ENTRANCE — Task planen

User sagt "cron HH:MM [task]". Du speicherst:
- **Zeit**: "15:00", "09:30"
- **Intervall** (optional): "daily", "once" (default)
- **Task**: Was passieren soll
- **Modus**: 
  - `loop` → startet den loop-Skill mit dem Task
  - `mm` → postet nur Erinnerung nach Mattermost
  - (default) → direkt ausführen + MM-Post

### 2. SPEICHER — Task merken

Tasks werden im Chat-Kontext gemerkt (für diese Session).
Format:
```
[cron]
1. 15:00 | loop "Feature X"     | once    | ⏳
2. 09:00 | mm "Daily Standup"   | daily   | ⏳
```

### 3. CHECK — Vor jedem Tool-Call

Bevor Du irgendwas machst: **aktuelle Zeit prüfen** (`date`).
Wenn ein Task fällig ist → ausführen:
```
Cron-Trigger: Task #1 "Feature X" um 15:00
→ Ausführen (Code schreiben/loop starten/MM posten)
→ Status: ✅ Erledigt
```

### 4. MODI

| Modus | Verhalten | Beispiel |
|-------|-----------|---------|
| (default) | Task direkt ausführen + MM-Post | `cron 15:00 "fix bug"` |
| `loop` | loop-Skill laden + Task starten | `cron 15:00 loop "Feature X"` |
| `mm` | Nur Nachricht an #agent-tasks | `cron 15:00 mm "Meeting"` |

### 5. WIEDERHOLUNG

- `once` (default) — einmalig, dann gelöscht
- `daily` — jeden Tag zur selben Zeit
- `weekly` — jede Woche (Wochentag + Zeit)

## Grenzen (ehrlich)

1. **Läuft nur wenn OpenCode aktiv ist.** Wenn Du um 15:00 nicht im Chat bist, feuert der Cron nicht.
2. **Für 24/7-Cron** muss das auf dem Cluster laufen (swarm1) — kann ich später bauen.
3. **Einmalige Tasks** — dafür reicht dieser Skill völlig.

## Integration

### Mattermost
Erinnerungen/Status gehen nach `#agent-tasks`:
```
[cron] 🔔 Task #1: Feature X — gestartet um 15:00
[cron] ✅ Task #1: Feature X — erledigt
```

### Loop
Wenn `cron ... loop "task"` — lade den loop-Skill und starte autonome Bearbeitung.
