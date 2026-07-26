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
| Plan-Label | `~/.claude.json` `oauthAccount.organizationRateLimitTier` | Ja (fixed 2026-07-26) |
| Savings | Σ Cost - $200/mo Abo | Berechnet |

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
