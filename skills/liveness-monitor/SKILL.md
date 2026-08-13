---
name: liveness-monitor
description: Watchdog für meta-skills Hook-Pipeline. Prüft heartbeat-state.md last-modified — wenn >24h alt, ist Hook-Pipeline tot. Erstellt ERPNext-Bug-Task + optional Mattermost-Alert. Verhindert dass Pipeline 48 Tage unentdeckt schweigt (siehe E207).
trigger: liveness, monitor hooks, hook pipeline check, watchdog, is pipeline alive, heartbeat check, hooks tot
model: haiku
allowed-tools: [Bash, Read]
user-invocable: true
complexity: skill
last-audit: 2026-05-12
---

# liveness-monitor — Hook-Pipeline-Watchdog

## Was es macht

Prüft ob die meta-skills Hook-Pipeline aktuell läuft. Liest `meta-skills/self-improving/heartbeat-state.md` last-modified time. Wenn älter als Threshold (Default 24h) → Alert.

## Warum es existiert

**Anlass:** E207 (2026-05-12). Plugin-Cache war 28 Tage stale (v2.0.0 vs Source v4.4.0), Hook-Pipeline daher tot, niemand hat es bemerkt — bis Cowork-Investigation den Untot-Status manuell entdeckt hat. Strukturelles Anti-Slop-Watchdog hätte das nach 24h erkannt.

## Wann nutzen

- **Automatisch:** Daily via TaskScheduler/cron — `python check.py --alert`
- **Manuell:** `python check.py` — sofortiger Status
- **In Session:** wenn unklar ob Hooks gerade feuern

## Befehle

```bash
# Quick-Check (gibt Exit-Code + JSON)
python check.py

# Mit Alert (ERPNext + MM wenn dead)
python check.py --alert

# Verbose Output
python check.py --verbose

# Threshold anpassen (default 24h)
python check.py --max-age-hours 12
```

## Output-Format

JSON auf stdout:
```json
{
  "status": "live" | "stale" | "dead" | "missing",
  "heartbeat_path": "C:\\Users\\Legion\\Documents\\phantom-ai\\meta-skills\\self-improving\\heartbeat-state.md",
  "last_modified": "2026-05-12T08:30:00Z",
  "age_hours": 0.5,
  "threshold_hours": 24,
  "alert_triggered": false,
  "alert_destinations": []
}
```

Exit-Codes:
- 0 = live
- 1 = stale (zwischen 24h und 7d alt)
- 2 = dead (>7d alt oder missing)
- 3 = error (file unlesbar)

## Alert-Verhalten

Wenn `--alert` flag UND status != live:

1. **ERPNext Task erstellen** (Project: PROJ-0001, Priority: Urgent für dead, High für stale):
   - Subject: `Hook-Pipeline tot — Letzte Aktivität YYYY-MM-DD`
   - Description: heartbeat-path, age, suspected cause (Plugin-Cache stale? Source-Issue? Marketplace fehlt?)
   - Tags: bug, hook-pipeline, anti-slop

2. **Mattermost-Post in #echo_log** (via jim_ops.py mm-post):
   - "🔴 ALERT: Hook-Pipeline schweigt seit {age_hours}h. Erwartet < {threshold_hours}h. Check ERPNext-Task TASK-XXXXX."

3. **Idempotenz:** Wenn ein offener ERPNext-Task mit gleichem Subject < 24h existiert → kein Duplikat erstellen.

## Voraussetzungen

- `python3` mit `pathlib`, `datetime`, `json`, `urllib.request` (stdlib only)
- Vault-Access für ERPNext-Credentials + MM-Token (wenn --alert)
- Schreibrecht auf `meta-skills/self-improving/` für state-File (Dedup-Tracking)

## Integration

### TaskScheduler (Windows .91)

```powershell
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\Users\Legion\Documents\phantom-ai\meta-skills\skills\liveness-monitor\check.py --alert"
$trigger = New-ScheduledTaskTrigger -Daily -At 09:00
Register-ScheduledTask -TaskName "MetaSkills-Liveness-Monitor" -Action $action -Trigger $trigger -Description "Daily Hook-Pipeline-Liveness-Check (E207 prevention)"
```

### systemd timer (Linux .99)

```ini
# /etc/systemd/system/meta-skills-liveness.timer
[Unit]
Description=Daily Hook-Pipeline-Liveness-Check
[Timer]
OnCalendar=09:00
Persistent=true
[Install]
WantedBy=timers.target
```

## Tests

`tests/test_liveness_monitor.py` deckt:
- Live-Case (heartbeat < 24h)
- Stale-Case (24h < age < 7d)
- Dead-Case (age > 7d)
- Missing-Case (file fehlt)
- Idempotenz (zweiter Run innerhalb 24h kein zweiter Task)
- Alert-Output-Format

## Bezug zu E207

Dieser Skill ist die strukturelle Antwort auf E207. Wenn er von 2026-04-15 an gelaufen wäre, hätte Joe am 2026-04-16 (24h nach letztem Hook-Trigger 2026-04-15 etwa) den Alert bekommen — statt am 2026-05-12 zufällig zu entdecken dass 28 Tage vergangen sind.

## Last-Verified

2026-05-12 — initial release. Tests passed lokal (siehe `tests/test_liveness_monitor.py`).
