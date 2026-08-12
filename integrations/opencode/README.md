# OpenCode Adapter

`meta-skills-plugin` is the shared AIE skill substrate. This directory adapts its
shared skills to OpenCode without treating Claude Code and OpenCode as the same
runtime.

## What Is Shared

- Shared behavior: `../../skills/peer-comms/SKILL.md`.
- Shared transport: `aie-mm-mcp`.
- Shared durable record: Gitea.

Persistent team coordination uses `ai-engineering/#ocode-team`. `#team-infra`
and `#town-square` are explicit operator-selected compatibility paths, not defaults.

## What Stays Runtime-Specific

- Claude Code loads its plugin manifest and Claude hooks.
- OpenCode loads `SKILL.md` files through `skills.paths` and starts MCP servers from
  `mcp` configuration.
- Claude hooks are not imported into OpenCode. OpenCode plugins remain OpenCode plugins.

## Launch Site (`opencode-plugin/`)

[`.opencode-plugin/`](../../.opencode-plugin/) is the canonical launch site (lesite) —
the OpenCode equivalent of `.claude-plugin/`. It provides:

| Artifact | Location |
|---|---|
| Plugin manifest | `.opencode-plugin/plugin.json` |
| Marketplace listing | `.opencode-plugin/marketplace.json` |
| Canonical launcher | `.opencode-plugin/launcher` |
| Integration guide | `.opencode-plugin/SETUP.md` |

The wrappers in `bin/` delegate to the canonical launcher at `.opencode-plugin/launcher`.

## Profiles

Use one profile per OpenCode process:

- `profiles/opencode.brain.jsonc` starts `aie-mm-mcp` as Brain.
- `profiles/opencode.vibe.jsonc` starts `aie-mm-mcp` as Vibe.
- `profiles/opencode.ocode-kimi.jsonc` starts the bounded builder role.
- `profiles/opencode.ocode-pruefer.jsonc` starts the read-only reviewer role.

Do not merge both profiles into a single OpenCode configuration. The environment of an
MCP process determines the Mattermost identity; loading both would make it possible to
send under the wrong peer identity.

Start through the role launcher rather than running a profile directly:

```sh
opencode-brain
opencode-vibe
opencode-brain run "summarize the current task"
```

The launcher selects one role-bound OpenCode primary agent and one exact
Mattermost write channel. All four persistent roles default to `ocode-team`.
Compatibility channels must be selected explicitly. It rejects `--agent` overrides, so the
inbound plugin cannot inject a peer message under a different role. The launcher also
exports the intended inbound read channel, but `aie-mm-mcp` does not yet enforce a
read-channel whitelist; see `STATUS.md` before treating inbound routing as active.
The launchers are for OpenCode sessions (interactive TUI or `run`) only; run `opencode mcp`,
`opencode debug`, and other administration commands directly.

The profiles contain no token: `aie-mm-mcp` retrieves its role-specific credential from
the existing vault at runtime. `OPENCODE_CONFIG` augments the normal global configuration,
so providers, permissions, and local plugins remain available.

Restart OpenCode after changing its configuration. OpenCode reads configuration, skills,
and MCP definitions only when it starts.

When resuming with `--session`, the launcher also gives the inbox plugin that
exact session ID. This removes lifecycle-event ambiguity and lets Mattermost
target the named session without a local keyboard prompt.

**`--session` is mandatory for peer inbound.** A launcher start without
`--session` leaves the inbox plugin's `activeSessionID` unset, so it never polls
and never delivers (log shows `peer inbox initialized` but no `delivered`). Start
persistent peers only as `./.opencode-plugin/launcher --role <role> --channel
ocode-team --session ses_...` — one single line, never broken across lines.
Measured 2026-08-12; see `INCIDENT-2026-08-12-mm-inbound.md`.

During Bridge-T2 quarantine all four persistent roles use direct `opencode/*`
models. Browser use is an explicit backup surface, never the primary team path.

## Adoption Plan

`ROADMAP.md` records the staged adoption path. Phase 1 is the Brain/Vibe communication
channel; later phases qualify shared skills and map only proven Claude-Code capabilities
to their native OpenCode equivalents.

`STATUS.md` records measured capability and open boundaries. `LEARNINGS.md` records
corrections made while adopting OpenCode, including claims that were narrowed after source
or runtime verification.
