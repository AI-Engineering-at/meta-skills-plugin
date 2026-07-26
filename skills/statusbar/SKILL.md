---
name: statusbar
description: Session Lifecycle — Statusline, Watcher, Sync. Real-time Model/Costs/Context/Limits with Rainbow. Per-session guardian that cleans up on terminal death and warns on RAM spikes.
trigger: statusbar, statusline, session watcher, session lifecycle, token usage, kosten, costs, rate limits
model: haiku
allowed-tools: [Read, Bash]
user-invocable: true
complexity: skill
last-audit: 2026-07-26
version: 1.2.0
token-budget: 200
type: utility
category: monitoring
requires: []
produces: [status-display]
cooperative: false
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
◆ O4.7(1M) H │ ████░░░░░░░░ 21% │ $186.66 │ in:969k out:826k │ 2d15h │ Σ$208 Σ1.8M Σ4mo(12) │ 5h:9% 7d:72% │ Max(+$8 saved)
```

| Segment | Bedeutung | Quelle |
|---------|--------|-------|
| `S5(1M)` | Modell-Kurzname + Context-Fenster-Größe DIESER Session | `model.id` + `context_window.context_window_size`, Hook-JSON pro Render |
| `X`/`L`/`M`/`H` | Effort-Level | `~/.claude/settings.json` Feld `effortLevel` |
| `████░ 65%` | Wie voll das AKTUELLE Kontextfenster ist (resettet bei `/compact`) | `context_window.used_percentage` |
| `$61.29` | Kosten DIESER Session bis jetzt — Anthropics eigener echter kumulativer Wert | `cost.total_cost_usd` |
| `in:647k out:177` | Momentaufnahme des aktuellen Kontextfensters — kein Laufzähler | `context_window.total_input/output_tokens` |
| `2h26m` | Dauer DIESER Session | `cost.total_duration_ms` |
| `Σ$28k Σ178.3M Σ275d(2)` | **All-time seit echter Account-Anlage** (nicht seit Statusline-Aktivierung). Σ-Kosten/Token = Summe der real getrackten Sessions in `~/.claude/statusline-alltime.json` **plus** Hochrechnung für die Lücke davor — läuft NUR, wenn `~/.claude/statusline-user-config.json` `confirmed_continuous_usage_since_account_creation:true` gesetzt ist (explizite User-Bestätigung, keine Auto-Heuristik). Rate = fixer, am 2026-07-26 verifizierter 67-Tage-Audit-Wert (`AUDITED_DAILY_RATE_COST`/`_TOKENS` in `statusline_lib.py`), NICHT aus der (oft winzigen) Live-Datei berechnet — sonst extrapoliert eine 2-Stunden-Stichprobe über Monate (KE-2026-07-26-M). `275d` = Tage bis zur echten Account-Anlage (`~/.claude.json` `oauthAccount.accountCreatedAt`). `(2)` = Anzahl ECHTER Session-Einträge (die Hochrechnung selbst zählt nicht mit) | siehe oben, Details unten |
| `5h:2%(3h58m) 7d:31%(116h08m)` | Anthropics eigene Rate-Limit-Fenster, 1:1 durchgereicht — NICHT von diesem Skript berechnet | `rate_limits.five_hour/seven_day.used_percentage` + `.resets_at` |
| `Max(+$26k saved)` | Echter Abo-Tier + Ersparnis ggü. Einzelabrechnung: All-time-Kosten minus (aufgerundete Monate seit Account-Anlage × $200) | `~/.claude.json` → `oauthAccount.organizationRateLimitTier` (gemappt via `parse_rate_limit_tier`) |

Model-family parsing (`statusline_lib.parse_model_id`) covers `opus`/`sonnet`/
`haiku`/`fable`, both the legacy two-number scheme (`opus-4-7`) and the
Claude 5 family's bare single-number IDs (`sonnet-5`, `opus-5`, `fable-5` —
no minor digit). Fixed 2026-07-26: `fable` was previously unrecognized
(fell through to showing the literal string `claude`), and single-number
IDs rendered as a generic 4-letter fallback (`Sonn`) instead of `S5`.

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
"statusLine": { "type": "command", "command": "python3 .../statusline.py", "padding": 0 },
"hooks": {
  "SessionStart": [{ "hooks": [{ "command": "python3 .../session_init.py" }] }],
  "SessionEnd":   [{ "hooks": [{ "command": "python3 .../session-end-sync.py" }] }]
}
```

### Two accuracy bugs fixed 2026-07-26 (found by a token-usage audit)

1. **Plan label was a wrong heuristic.** `plan = "Max" if total_ctx >= 1_000_000
   else "Pro"` has no documented link between context-window size and
   subscription tier — it could mislabel. Fixed: read the real tier from
   `~/.claude.json` → `oauthAccount.organizationRateLimitTier` (e.g.
   `"default_claude_max_20x"` → `"Max"`) via `statusline_lib.parse_rate_limit_tier`,
   falling back to the old heuristic only if that file/field is unavailable.

2. **Σ token stat structurally undercounted.** `context_window.total_input/
   output_tokens` is a snapshot of the CURRENT context window, not cumulative
   session throughput — Claude Code resets it on `/compact`. The old code
   overwrote `statusline-alltime.json`'s `"tokens"` with that raw snapshot on
   every invocation, silently losing everything before the last reset. Fixed:
   treat the raw snapshot as a monotonic counter; a drop (new < previous raw)
   is detected as a reset and the pre-reset peak is folded into a persisted
   `tokens_baseline`, so `"tokens"` (= `tokens_baseline + tokens_raw`) is the
   true cumulative value. Legacy entries (flat `"tokens"` int, no baseline
   fields) migrate on first write with no data loss. Regression tests:
   `tests/test_statusline_token_accumulator.py`.

### The "all-time since account creation" baseline (added 2026-07-26)

The Σ figure normally only covers sessions actually tracked in
`statusline-alltime.json` — on the day the statusbar is first activated,
that's whatever ran today, nothing more (`Σtoday(N)`), because there isn't
yet enough real local data to extrapolate anything further back without
guessing (`MIN_RATE_BASIS_DAYS = 3.0` in `statusline_lib.py`).

If the account holder explicitly confirms continuous usage since the real
account creation date — not an auto-detected heuristic — set
`~/.claude/statusline-user-config.json`:
```json
{"confirmed_continuous_usage_since_account_creation": true}
```
This unlocks an immediate extrapolation back to `~/.claude.json`'s
`oauthAccount.accountCreatedAt`, using `AUDITED_DAILY_RATE_COST`/
`_TOKENS` in `statusline_lib.py` as the rate — **not** whatever's in the
live file (which on day one might be a single session, and extrapolating
that as "the daily rate" over months reproduces the exact class of bug
this whole mechanism exists to avoid; see KE-2026-07-26-M).

**These constants are a point-in-time snapshot, not a live sync.** They
were last set 2026-07-26 from `llm_bridge/claude_code_usage.py`'s own
(properly deduped, complete) 67-day measurement in the Phantom LLM
Bridge repo — sourced from that reader specifically because an earlier,
less rigorous manual estimate disagreed with it by roughly 50-100%.
Recalibrate periodically by rerunning that reader, not by guessing or
hand-adjusting. **Scope:** all of this — the constant, the Bridge's own
numbers, everything in this file — covers only local transcripts on THIS
Mac. Usage from another machine or another account is not visible here
and is not folded in.

### Mac interpreter pin (live 2026-07-26, Brain@Mac)

`statusline.py` / `statusline_lib.py` use `datetime.UTC` and PEP-604 return
annotations (`tuple[...] `, `X | None`) — both need **Python ≥ 3.11**.
macOS's default `python3` (`/usr/bin/python3`, CommandLineTools) is **3.9.6**
and fails with `ImportError: cannot import name 'UTC' from 'datetime'`.
Activated `statusLine` command on this Mac pins an explicit newer
interpreter instead of bare `python3`:

```json
"statusLine": {
  "type": "command",
  "command": "/opt/homebrew/bin/python3.12 /Users/mackbook/code-aie/meta-skills-plugin/scripts/statusline.py",
  "padding": 0
}
```

Verify before reusing on another Mac: `python3 --version` may resolve to a
different interpreter per-host (Homebrew vs. system vs. pyenv) — don't
assume the path above is portable, re-check `which -a python3*` first.

## Examples

### Example 1: Check statusline output

```
◆ O4.7(1M) H │ ████░░░░░░░░ 21% │ $186.66 │ in:969k out:826k │ 2d15h │ Σ$208 Σ1.8M Σ4mo(12) │ 5h:9% 7d:72% │ Max(+$8 saved)
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
