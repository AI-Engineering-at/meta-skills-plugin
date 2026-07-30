---
name: statusbar
description: OpenCode Session Lifecycle — usage tracking, status display, and process monitoring. Model, RAM, Tool Calls, Session Duration.
trigger: statusbar, status, watcher, session status, usage, leiste, was läuft, costs, tools, how's it going, is it alive
model: free/groq-fast
allowed-tools: [Read, Bash]
complexity: skill
---

# statusbar — OpenCode Session Status

Displays session status collected by the statusbar plugin. Register
`.opencode-plugin/plugins/statusbar.mjs` explicitly in the OpenCode `plugin`
configuration before relying on it. The Brain/Vibe role profiles do not
register it yet, so this skill must not claim active monitoring.

## Components

| Component | Location | Function |
|---|---|---|
| Statusbar plugin | `.opencode-plugin/plugins/statusbar.mjs` | Tracks session, model, tools, messages, RAM, processes |
| Status file | `~/.config/opencode/statusbar/current.json` | Live session data (+ process info) |
| History | `~/.config/opencode/statusbar/history.jsonl` | All sessions (append log) |
| Watcher bin | `.opencode-plugin/bin/opencode-watcher` | Standalone status reader (optional, plugin does monitoring built-in) |

## Status File Format

`~/.config/opencode/statusbar/current.json`:

```json
{
  "sessionID": "abc-123",
  "agent": "brain",
  "model": "phantom/local/fast",
  "status": "idle",
  "duration": "1h23m",
  "messages": 15,
  "toolCalls": 42,
  "tools": "bash:30 read:8 edit:4",
  "processCount": 3,
  "ramMB": 256,
  "updatedAt": "2026-07-29T..."
}
```

## Commands

### Show session status

```bash
opencode-watcher
# or directly:
cat ~/.config/opencode/statusbar/current.json
```

### Clean up stale status files

```bash
opencode-watcher --cleanup
```

### Show usage tools (built-in OpenCode)

```
usage-current    # Current session tokens
usage-summary    # Cross-session costs
usage-workers    # Agent run stats
```

## Example: Session Status

```
◆ brain · phantom/local/fast · 15 messages · 42 tool calls · 1h23m · idle
```

When no session is active:

```
No active session. Opencode processes: 0  RAM: —
```

## Modes

After explicit registration, the plugin can run in TUI, web, and serve modes.
That runtime behavior still needs a separate live acceptance test.
