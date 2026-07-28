# OpenCode Adapter

`meta-skills-plugin` is the shared AIE skill substrate. This directory adapts its
shared skills to OpenCode without treating Claude Code and OpenCode as the same
runtime.

## What Is Shared

- Shared behavior: `../../skills/peer-comms/SKILL.md`.
- Shared transport: `aie-mm-mcp`.
- Shared durable record: Gitea.

Peer coordination prefers `ai-chat/#agent-tasks`. `#town-square` is the controlled
fallback when the active peer profile rejects `#agent-tasks` but permits the fallback.

## What Stays Runtime-Specific

- Claude Code loads its plugin manifest and Claude hooks.
- OpenCode loads `SKILL.md` files through `skills.paths` and starts MCP servers from
  `mcp` configuration.
- Claude hooks are not imported into OpenCode. OpenCode plugins remain OpenCode plugins.

## Profiles

Use one profile per OpenCode process:

- `profiles/opencode.brain.jsonc` starts `aie-mm-mcp` as Brain.
- `profiles/opencode.vibe.jsonc` starts `aie-mm-mcp` as Vibe.

Do not merge both profiles into a single OpenCode configuration. The environment of an
MCP process determines the Mattermost identity; loading both would make it possible to
send under the wrong peer identity.

Start through the role launcher rather than running a profile directly:

```sh
opencode-brain
opencode-vibe --channel town-square
opencode-brain run "summarize the current task"
```

The launcher selects one role-bound OpenCode primary agent (`brain` or `vibe`) and one
exact Mattermost write channel. Its default is `agent-tasks`; `town-square` must be
selected explicitly as the documented fallback. It rejects `--agent` overrides, so the
future inbound plugin cannot inject a peer message under a different role. The launcher
also exports the intended inbound read channel, but `aie-mm-mcp` does not yet enforce a
read-channel whitelist; see `STATUS.md` before treating inbound routing as active.
The launchers are for OpenCode sessions (interactive TUI or `run`) only; run `opencode mcp`,
`opencode debug`, and other administration commands directly.

The profiles contain no token: `aie-mm-mcp` retrieves its role-specific credential from
the existing vault at runtime. `OPENCODE_CONFIG` augments the normal global configuration,
so providers, permissions, and local plugins remain available.

Restart OpenCode after changing its configuration. OpenCode reads configuration, skills,
and MCP definitions only when it starts.

## Adoption Plan

`ROADMAP.md` records the staged adoption path. Phase 1 is the Brain/Vibe communication
channel; later phases qualify shared skills and map only proven Claude-Code capabilities
to their native OpenCode equivalents.

`STATUS.md` records measured capability and open boundaries. `LEARNINGS.md` records
corrections made while adopting OpenCode, including claims that were narrowed after source
or runtime verification.
