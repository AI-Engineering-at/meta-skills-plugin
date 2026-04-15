---
name: statusbar
description: Session Lifecycle — Statusline, Watcher, Sync. Real-time Model/Costs/Context/Limits with Rainbow. Per-session guardian that cleans up on terminal death and warns on RAM spikes.
trigger: statusbar, statusline, session watcher, session lifecycle, token usage, kosten, costs, rate limits
model: haiku
allowed-tools: [Read, Bash]
user-invocable: true
complexity: skill
last-audit: 2026-04-14
version: 1.0.0
token-budget: 200
---

# meta:statusbar — Session Lifecycle (Statusline + Watcher + Sync)

Three components, one system. All in `meta-skills/scripts/`, all cross-platform.

## Architecture

```
SessionStart Hook
  ├── session_init.py → spawns session-watcher.py (detached)
  └── Statusline → statusline.py (every second via settings.json)

During Session
  ├── Statusline: Model, Cost, Context, Limits, Σ-Stats
  └── Watcher: Parent-PID alive? RAM ok? Heartbeat writing

SessionEnd Hook
  └── session-end-sync.py → create open-notebook KB source
```

## 1. Statusline (`statusline.py`)

```
◆ O4.6(1M) H │ ████░░░░░░░░ 21% │ $186.66 │ in:969k out:826k │ 2d15h │ Σ$208 Σ1.8M Σ4mo(12) │ 5h:9% 7d:72% │ Max(+$8 saved)
```

| Segment | Source | Live? |
|---------|--------|-------|
| Model + Context | `model.id` + `context_window_size` | Ja |
| Effort | `~/.claude/settings.json` effortLevel → L/M/H | Ja |
| Progress Bar | `used_percentage` (10-step gradient) | Ja |
| Cost | `cost.total_cost_usd` (echte API-Kosten) | Ja |
| In/Out | `total_input/output_tokens` | Ja |
| Duration | `total_duration_ms` | Ja |
| Σ Stats | `~/.claude/statusline-alltime.json` | Akkumuliert |
| Rate Limits | `five_hour/seven_day.used_percentage` | Ja |
| Savings | Σ Cost - $200/mo Abo | Berechnet |

Rainbow: HSV Phase Shift (`time.time() * 0.3`), Separatoren + Σ-Symbole schimmern.

## 2. Session Watcher (`session-watcher.py`)

Spawnt als detached Hintergrundprozess bei SessionStart.

| Was | Wann | Aktion |
|-----|------|--------|
| Parent-PID tot | Alle 10s Check | 30s Grace → Children killen → Heartbeat loeschen → Exit |
| RAM > 4 GB | Alle 10s | Desktop-Notification (Win/Mac/Linux) |
| RAM Spike > 500 MB | Innerhalb eines Intervalls | Desktop-Notification |
| Session > 24h | Einmal | Desktop-Notification |

Heartbeats: `~/.claude/watchers/{pid}.json`

```bash
# Show all watchers
python meta-skills/scripts/session-watcher.py --list

# Clean up orphaned heartbeats
python meta-skills/scripts/session-watcher.py --cleanup-orphans
```

## 3. Session-End Sync (`session-end-sync.py`)

Automatic via SessionEnd hook. Collects today's git commits, posts as source in open-notebook KB.

Logs: `~/.claude/sync-logs/sync-YYYY-MM-DD.log`

## 4. Process Monitor (`process-monitor.py`)

Manual tool for system overview (not automatic, not in statusline).

```bash
python meta-skills/scripts/process-monitor.py --status    # Alle claude-Prozesse
python meta-skills/scripts/process-monitor.py --report    # Markdown-Report
python meta-skills/scripts/process-monitor.py --cleanup   # Zombies killen
python meta-skills/scripts/process-monitor.py --install   # Als Scheduled Task
```

## Cross-Platform

| Feature | Windows | macOS | Linux |
|---------|---------|-------|-------|
| Prozess-Erkennung | claude.exe | claude / node | claude / node |
| Notifications | PowerShell Balloon | osascript | notify-send |
| Scheduler Install | schtasks | launchd plist | crontab |
| Watcher Detach | CREATE_NO_WINDOW | start_new_session | start_new_session |

## Configuration

Everything in `~/.claude/settings.json`:
```json
"statusLine": { "command": "python3 .../statusline.py" },
"hooks": {
  "SessionStart": [{ "hooks": [{ "command": "python3 .../session_init.py" }] }],
  "SessionEnd":   [{ "hooks": [{ "command": "python3 .../session-end-sync.py" }] }]
}
```

## Examples

### Example 1: Check statusline output

```
◆ O4.6(1M) H │ ████░░░░░░░░ 21% │ $186.66 │ in:969k out:826k │ 2d15h │ Σ$208 Σ1.8M Σ4mo(12) │ 5h:9% 7d:72% │ Max(+$8 saved)
```

### Example 2: Manage session watchers

```bash
# List all active watchers
python meta-skills/scripts/session-watcher.py --list

# Clean up orphaned heartbeats
python meta-skills/scripts/session-watcher.py --cleanup-orphans
```

### Example 3: Process monitoring

```bash
# Show all claude processes
python meta-skills/scripts/process-monitor.py --status

# Generate markdown report
python meta-skills/scripts/process-monitor.py --report
```
