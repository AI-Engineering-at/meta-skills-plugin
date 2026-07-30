# OpenCode Plugin Setup

This guide explains how to integrate the meta-skills OpenCode adapter into your
local OpenCode configuration.

## Prerequisites

- OpenCode `>= 1.18.5` installed and on `PATH`
- `aie-vault` CLI available (or `$AIE_VAULT_BIN` set)
- `aie-mm-mcp` Python package installed in a `.venv`
- A Mattermost bot account for each peer role (brain/vibe)

## Quick Start

The launcher wrappers (`opencode-brain`, `opencode-vibe`) are the primary entry points.
Add the `integrations/opencode/bin/` directory to your `PATH`:

```zsh
# ~/.zshrc or equivalent
export PATH="$PATH:$HOME/code-aie/meta-skills-plugin/integrations/opencode/bin"
```

Then start a peer session:

```zsh
# Start a Brain session (default channel: agent-tasks)
opencode-brain

# Start a Vibe session on the fallback channel
opencode-vibe --channel town-square

# Run a single-shot prompt as Brain
opencode-brain run "check the current deployment status"
```

## Manual Registration (without PATH)

If you prefer full-path invocation:

```zsh
# From the meta-skills-plugin root
./.opencode-plugin/launcher --role brain
./.opencode-plugin/launcher --role vibe --channel town-square
./.opencode-plugin/launcher --role brain run "probe"
```

## Integrating Profiles

To use the profiles directly in `opencode.json` instead of through the launcher:

1. Copy or reference a profile from `integrations/opencode/profiles/opencode.$role.jsonc`.
2. Set `OPENCODE_CONFIG` to the profile path before starting OpenCode:

```zsh
export OPENCODE_CONFIG="/path/to/meta-skills-plugin/integrations/opencode/profiles/opencode.brain.jsonc"
opencode
```

## Inbox Plugin

The `peer-inbox.mjs` plugin (registered in each profile) provides automatic
Mattermost-to-session message injection. It:

- Polls the `aie-mm-mcp` for new messages targeting the configured role
- Injects them into the current OpenCode session when idle
- Persists source-specific watermarks to prevent replay
- Caps injection at 20 messages per batch

The plugin is already registered in both profiles. No additional setup is needed
when starting through the launcher.

## What Ships

| Component | Path |
|---|---|
| Canonical launcher | `.opencode-plugin/launcher` |
| Brain profile | `integrations/opencode/profiles/opencode.brain.jsonc` |
| Vibe profile | `integrations/opencode/profiles/opencode.vibe.jsonc` |
| Inbox plugin | `integrations/opencode/plugins/peer-inbox.mjs` |
| Shared skills | `../../skills/` (referenced by profiles) |
| Launcher wrappers | `integrations/opencode/bin/opencode-{brain,vibe,peer}` |

## Tests

Run the launcher contract tests from the project root:

```zsh
python -m pytest integrations/opencode/tests/test_opencode_peer_launcher.py -v
```

Run the inbox plugin tests:

```zsh
node --test integrations/opencode/tests/peer-inbox-plugin.test.mjs
python -m pytest integrations/opencode/tests/ -v
```

## Notes

- The launcher never writes credentials to disk or prints them to stdout.
- Role and channel are start-time properties; changing them requires a restart.
- The `--agent` flag is locked to the selected role — the launcher rejects overrides.
- Administration commands (`opencode mcp`, `opencode debug`, etc.) must be run
  directly, not through the launcher.
