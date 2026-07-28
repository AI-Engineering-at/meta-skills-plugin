---
name: peer-comms
description: Coordinate work between Brain and Vibe through Mattermost. Use when the user asks to contact, check for, hand off work to, or coordinate with Brain or Vibe.
---

# Brain/Vibe Peer Communication

## Purpose

Use Mattermost for short-lived coordination between Brain and Vibe. Use Gitea issues
and commits for durable tasks, decisions, and evidence.

## Identity

Each runtime must start the Mattermost MCP with exactly one explicit role:

- Brain uses `AIE_MM_ROLE=brain` and the `aie-mm-mcp-brain` identity.
- Vibe uses `AIE_MM_ROLE=vibe` and the `aie-mm-mcp-vibe` identity.

Do not use a shared bot identity, another peer's MCP server, `AIE_MM_TOKEN`, or a
role-less fallback. If the configured MCP identity is missing or wrong, report the
structured error and stop before sending.

## Operating Rules

1. Read the peer channel before claiming a peer has not replied.
2. Post peer coordination in `ai-chat/#agent-tasks` using exactly one address prefix:
   `[brain -> @vibe]`, `[vibe -> @brain]`, or `[joe -> @brain @vibe]`. The last form is
   the shared broadcast to both peers. If the active peer profile rejects that channel, use
   the whitelisted `#town-square` fallback, retain the prefix, and include the originating
   thread or Gitea reference.
3. Keep messages concise: purpose, current evidence, requested decision or next action.
4. Put durable work in Gitea. Include the issue or commit reference in the message.
5. Before a write, confirm the configured channel is whitelisted. The MCP audit trail is
   the delivery receipt; read the created post or its thread before claiming delivery.
6. Do not send a DM unless the request explicitly requires a DM and the MCP confirmation
   parameter is set.

## OpenCode

The OpenCode adapter lives in `integrations/opencode/`. Start exactly one role through
`integrations/opencode/bin/opencode-brain` or `opencode-vibe`; do not load both profiles
into one process. The launcher binds the Mattermost role, OpenCode primary agent, and one
read/write channel together. `agent-tasks` is the default; `town-square` is an explicit
fallback selection. The profile provides the `aie-mm-mcp` transport and loads this shared
skill directory. The launcher restricts MCP writes today; the plugin filters its own inbound
input, but end-to-end delivery remains unaccepted until `STATUS.md` records the live proof.

## Failure Handling

- Token or vault failure: report the MCP error without exposing credential material.
- Channel not allowed: do not bypass the whitelist; use the approved peer channel or
  record the durable task in Gitea.
- Mattermost unavailable: record the coordination item in Gitea and state that the
  live peer delivery could not be verified.
- Direct message: a DM from Joe or the other peer reaches only its recipient. Use the shared
  peer channel, not two assumed copies of a DM, when both Brain and Vibe must receive the
  same instruction.
