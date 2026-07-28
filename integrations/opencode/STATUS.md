# OpenCode Adapter Status

**Stand:** 2026-07-28

## Purpose

The adapter makes portable Meta-Skills available to OpenCode while preserving the runtime
boundary: shared instructions live under `skills/`, while OpenCode profiles, launchers,
and plugins live here.

## Startup Contract

Start a peer process only through one launcher:

```sh
opencode-brain
opencode-vibe
opencode-vibe --channel town-square
opencode-brain run "summarize the current task"
```

The launcher atomically selects:

| Value | Brain | Vibe |
|---|---|---|
| Mattermost role | `brain` | `vibe` |
| OpenCode primary agent | `brain` | `vibe` |
| MCP identity | `aie-mm-mcp-brain` | `aie-mm-mcp-vibe` |
| Default write channel | `agent-tasks` | `agent-tasks` |
| Explicit fallback | `town-square` | `town-square` |

It exports `AIE_MM_ROLE`, `AIE_OPENCODE_AGENT`, `AIE_MM_WRITE_CHANNEL_NAMES`, and
`AIE_MM_READ_CHANNEL_NAMES`, loads exactly one role profile through `OPENCODE_CONFIG`,
and rejects a caller-provided `--agent`. The agent is selected again with OpenCode's
`--agent` flag, so the session and the environment agree.

The launchers are session entry points, not wrappers for `opencode mcp`, `opencode debug`,
or other administration subcommands. This prevents the session-only `--agent` flag from
being passed to an incompatible subcommand parser.

`AIE_MM_WRITE_CHANNEL_NAMES` is enforced by `aie-mm-mcp` for outbound posts. The read
variable is a contract for the planned inbound plugin only; the MCP's ordinary read tools
can still read any channel available to its Mattermost identity. Do not describe this as a
read-channel restriction until an enforcement test exists.

## Measured Evidence

| Check | Result | Scope |
|---|---|---|
| `opencode --version` | `1.18.5` | Local OpenCode binary |
| `opencode debug agent brain` with Brain profile | Resolved as primary agent `brain` | Profile parsing and agent registration |
| `opencode debug agent vibe` with Vibe profile | Resolved as primary agent `vibe` | Profile parsing and agent registration |
| `opencode models phantom` with the Vibe profile | Phantom models remained available | `OPENCODE_CONFIG` augments the normal local configuration |
| `opencode mcp list` with Brain and Vibe profiles | `aie-mm-mcp connected` | Earlier live transport check |
| Brain-to-Vibe post and read-back | Role-correct round trip observed in `#town-square` | Earlier controlled fallback check |
| Vibe-role read-only smoke test | DMs, user lookup, and post search succeeded; team-channel list returned 403 | Endpoint-specific scope/membership boundary, not token absence |
| Brain and Vibe inbox helper baseline | Read-only `poll` initialized each role/channel watermark with no historical replay | Vault-backed peer inbox path |
| `opencode-brain run` session start | Launcher reached OpenCode session creation, then Bridge returned `401 CLIENT_UNAUTHORIZED` | Current live delivery blocker |
| Profile JSON and launcher syntax | Valid JSON; `zsh -n` passed | Static configuration |

The OpenCode documentation inspected for this work describes the session APIs
`session.promptAsync` and `session.prompt`. These are the supported OpenCode mechanisms
for injecting a message into a known session. Their use in an inbound loop is not yet
live-proven on the installed binary.

## Current Capability

- `peer-comms` is the active cross-runtime Meta-Skill.
- Brain and Vibe can run separately with their own Mattermost roles.
- The launch contract prevents accidental selection of the other peer's configured agent.
- Mattermost transport and a controlled fallback-channel round trip have prior live
  evidence.
- `peer_inbox.py` plus `plugins/peer-inbox.mjs` are registered in both profiles. They use
  the selected role, shared channel, and Joe DM only; their unit gates pass.

## Not Implemented

- No end-to-end Mattermost-to-OpenCode delivery is live-proven yet. The new plugin must be
  loaded by restarting both processes, and the Brain default model path currently fails with
  Bridge `401 CLIENT_UNAUTHORIZED` before it can process a prompt.
- The delivery design avoids concurrent turns by waiting for the selected session's idle
  event. It batches up to 20 accepted messages and persists source-specific watermarks after
  OpenCode accepts the injected prompt. A crash between acceptance and acknowledgement can
  cause one retry; exact-once delivery across Mattermost and OpenCode is not claimed.
- `peer_posteingang.py` in the KB is a session-start reporting script. It is not an
  OpenCode plugin and must not be represented as a continuous inbound runner.
- The launcher does not itself apply a Mattermost read filter.

## Required Inbound Design

The next implementation must satisfy all of the following before it is enabled:

1. Read only the startup-selected role and channel.
2. Use a durable per-role, per-channel watermark and do not advance it before successful
   delivery or explicit durable queueing.
3. Select only the active session belonging to the launcher process; never guess from all
   locally stored sessions.
4. If that session is busy, queue rather than start a competing turn.
5. Inject through `session.promptAsync` with the launcher-selected agent.
6. Log delivery metadata without copying tokens or message secrets.
7. Prove one positive delivery, one duplicate suppression, one wrong-role rejection, one
   wrong-channel rejection, and one busy-session case in a real OpenCode runtime.
8. Resolve the OpenCode-to-Bridge client authorization failure and prove a normal Brain
   prompt before attributing an inbound-delivery failure to the inbox plugin.

## Addressing Contract for Joe

Once the inbound plugin is enabled, use the shared peer channel to reach both processes:

```text
[joe -> @brain @vibe] Please check the current deployment status.
```

Use one recipient for a role-specific request. A direct message from Joe to Brain or Vibe is
also an input for that one role; it needs no address prefix because the DM recipient already
selects the role. A direct message cannot reach both peers at once. Use the shared peer
channel for messages that both must receive.

## Version Boundary

The installed binary is `1.18.5`. The local `@opencode-ai/plugin` dependency is `1.17.6`,
while the current documentation inspected during this work was published for `1.18.9`.
Every plugin hook or SDK call must therefore be verified against the installed runtime,
not assumed from the newer documentation.
