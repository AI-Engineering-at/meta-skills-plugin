# OpenCode Adapter Learnings

**Stand:** 2026-07-28

## Corrections

### L-OC-01: An MCP connection does not deliver inbound work

**Initial mistake:** Treating a connected Mattermost MCP as if it could wake or continue an
interactive OpenCode session.

**Measured correction:** MCP supplies tools to a session. OpenCode's server API provides
`session.promptAsync` for a known session, but neither a connected MCP nor a skill creates
the required poller, session selection, or delivery state.

**Rule:** Do not call inbound coordination active until a plugin has a measured source,
watermark, target-session, and injection receipt.

### L-OC-02: Role selection must not be inferred from a shared directory

**Initial mistake:** The legacy peer-posteingang utility can infer identity from its working
directory. Brain and Vibe can share a directory, so that inference is not a safe authority.

**Correction:** The OpenCode launcher supplies the explicit role and uses it consistently
for the profile, MCP environment, and OpenCode primary agent.

**Rule:** A role is a start-time configuration value, never a best-effort directory guess.

### L-OC-03: Fallback must be selected, not silently broadened

**Initial mistake:** Configuring both `agent-tasks` and `town-square` as simultaneous write
allowances made the fallback available without recording which channel the session chose.

**Correction:** The launcher exports exactly one write channel. `team-infra` is the
default; `town-square` requires `--channel town-square`.

*Channel name corrected 2026-08-02 (TASK-2026-00968): the default read `agent-tasks`
until then — a channel that never existed. See L-OC-15.*

**Rule:** Keep primary and fallback distinct in the process configuration and in delivery
evidence.

### L-OC-04: Write restriction is not read restriction

**Initial mistake:** Documentation initially called the launcher's selected channel a
read/write restriction.

**Measured correction:** `aie-mm-mcp` enforces `AIE_MM_WRITE_CHANNEL_NAMES` for writes;
its read tools do not consume `AIE_MM_READ_CHANNEL_NAMES`. The launcher now documents that
variable as a requirement for the future inbound filter, not existing enforcement.

**Rule:** Name the enforced boundary precisely and test read and write controls separately.

### L-OC-05: A registered configuration is not a runtime proof

**Initial mistake:** Earlier OpenCode experimental hook configuration did not fire. The
runtime's supported mechanism is an OpenCode plugin hook surface, demonstrated by the
local `aie-guard.js` tool-execution plugin.

**Correction:** The adapter uses native profile, agent, launcher, and plugin mechanisms.

**Rule:** Each claimed runtime capability needs a real trigger and observed outcome on the
installed OpenCode version.

### L-OC-06: Documentation and installed API versions can differ

**Observation:** The local OpenCode binary is `1.18.5`, the installed plugin package is
`1.17.6`, and the inspected online plugin documentation is newer (`1.18.9`).

**Rule:** Treat newer documentation as a design reference only. Validate plugin exports,
events, and SDK calls against the installed runtime before enabling them.

### L-OC-07: Configuration inspection can expose secrets

**Mistake:** A broad local configuration read returned an inline provider credential in a
tool result.

**Correction:** The value was not copied into this repository or subsequent documentation.

**Rule:** Inspect credential-bearing configuration through narrow, redacted checks; never
repeat a returned secret in logs, docs, commits, or chat.

### L-OC-08: Session flags are not global subcommand flags

**Mistake:** The first launcher version placed `--agent` before every OpenCode invocation,
including administrative subcommands such as `mcp list`.

**Measured correction:** `--agent` is accepted by a TUI or `run` session, but not by the
`mcp` command parser. The launcher now supports only session starts and rejects
administrative subcommands with an explicit error.

**Rule:** Bind session-only settings only where the OpenCode command accepts them; keep
administration checks separate from peer-session startup.

### L-OC-09: A 403 on one Mattermost endpoint is not a token verdict

**Incident:** The freshly launched Vibe session received `MMAuthError` from
`list_channels(team_slug=ai-engineering)` and concluded that no valid token was present.

**Measured correction:** A read-only smoke test under `AIE_MM_ROLE=vibe` succeeded for
`list_dms` (four DMs), `get_user(joe)`, and `search_posts`; only the team-channel-list and
bot-list endpoints returned 403. The client maps both 401 and 403 into `MMAuthError`, so
the type alone does not mean a token is absent or invalid.

**Rule:** Classify 401 as authentication failure; classify an endpoint-specific 403 as a
scope, membership, or endpoint-permission issue until an independent authenticated read
fails. Never fetch, print, or place a Mattermost credential in an agent session to work
around that distinction.

### L-OC-10: zsh array expansion must preserve argument boundaries

**Mistake:** The `opencode-peer run` branch expanded a zsh array slice as one quoted string.
OpenCode then received `--format json <prompt>` as one argument and showed command help
instead of starting a session.

**Correction:** Expand the remaining zsh arguments with `"${forwarded[@]:1}"`, which passes
each argument independently.

**Rule:** Test launchers through the actual subcommand shape they expose, not only syntax
and deny paths.

### L-OC-11: Session creation and model execution are separate gates

**Observation:** `opencode-brain run` created an OpenCode session after the launcher fix, but
the configured Phantom Bridge returned HTTP 401 `CLIENT_UNAUTHORIZED` when the model request
started.

**Rule:** Do not diagnose an inbound-plugin failure until a normal prompt completes on the
same role/profile/model path. A connected MCP and a created OpenCode session do not prove the
model can execute an injected message.

### L-OC-12: The inbox sender policy must include peer-to-peer DMs

**Mistake:** The first direct-message filter admitted only Joe. A live Brain-to-Vibe DM was
therefore silently and correctly excluded, which meant the desired automatic peer conversation
could not happen through DM.

**Correction:** Each role now accepts DMs from Joe and from the other peer only: Brain accepts
Joe/Vibe; Vibe accepts Joe/Brain. The Vibe helper independently selected the original test DM.

**Rule:** Test the intended sender/recipient matrix with real identities. A policy that is safe
but excludes the requested workflow is still a product failure.

### L-OC-13: A useful live proof must include execution, not just a receipt

**Evidence:** Vibe received Brain's task DM automatically, ran the requested Python and Node
test commands, and returned the independently reproducible results `6/6` and `2/2` through
Mattermost.

**Rule:** A message appearing in a session proves transport only. A bounded task with a
measured command result and a peer read-back proves the full receive → reason → tool → reply
path for that role.

### L-OC-14: A working inbox does not grant deploy authority

**Evidence:** Vibe automatically delivered a request to deploy the OpenCode LAN Hub. Brain
received it through the new inbox and explicitly held the deployment pending independent
commit/deploy-document review and Bridge/Swarm preflight.

**Rule:** Faster peer communication must shorten coordination latency, not bypass the
decision/gate boundary. Deploy authority remains with Brain even when Vibe can build and
test the code.

### L-OC-15: A channel name in a whitelist is not a channel

**Evidence (measured 2026-08-02, TASK-2026-00968):** The canonical launcher shipped
`channel="agent-tasks"` as its default, and `agent-tasks` was in every whitelist —
launcher, `peer_inbox.py`, `peer-inbox.mjs`. The channel did not exist. Same probe,
same endpoint: `GET /teams/{tid}/channels/name/agent-tasks` → HTTP 404, while
`team-infra`, `town-square` and `brain` → HTTP 200. Full enumeration (3 public +
7 private + 0 archived = 10 of 10) contains no such name. A stale hardcoded id in
`skills/loop/SKILL.md` (`md3fmix…`) was likewise 404 after the 2026-08-01 Mattermost
rebuild.

**Why nobody noticed:** the failure was silent, not loud. The read path
(`peer_inbox.py::_fetch`, `search_posts(f"in:{channel} …")`) answers **HTTP 200 with
`order=0`** for a channel that does not exist — byte-identical in shape to an existing
but quiet channel (measured: `in:agent-tasks` order=0, `in:team-infra` order=0,
positive control `in:brain` order=2). So the inbox returned `{"ok": true,
"messages": []}` forever, and every peer session read an empty mailbox as silence.

**Rule:** A name that only ever appears in your own whitelists is unverified. Resolve
each configured channel against the server once and let a missing one fail loudly —
a probe whose negative result is indistinguishable from success is not a measurement.

### L-OC-16: Read the lesson file before touching the runtime

**Incident (2026-08-12):** An evening of repeated Mattermost-inbound failures happened
while `LEARNINGS.md` already contained L-OC-15, L-OC-11, and L-OC-08 — each a prior
instance of the same error classes. The lesson file was never opened before acting.

**Rule:** Before any start/kill/config change on the adapter, read `LEARNINGS.md` and
`STATUS.md` first. Documented corrections are the cheapest available test suite; acting
without them is guessing.

### L-OC-17: Killing all MCP processes kills your own session's tools

**Incident (2026-08-12):** A cleanup `kill` of all `aie_mm_mcp.server` processes also
killed the server serving the acting session. OpenCode does not respawn an MCP mid-session;
the session lost its Mattermost tools for the rest of the run.

**Rule:** Never clean up by broad pattern. Enumerate the exact PIDs, exclude the current
session's own MCP, and verify the survivor before killing anything.

### L-OC-18: A peer start without `--session` has a dead inbound

**Incident (2026-08-12):** brain started via launcher without `--session ses_...` showed
`peer inbox initialized` but never `delivered`. In `peer-inbox.mjs`, the poll only runs
`if (activeSessionID) schedulePoll()`; without `AIE_OPENCODE_SESSION_ID` the plugin has no
bound session and never polls. 40 minutes of debugging replaced 2 minutes of reading.

**Rule:** Persistent peer roles start ONLY through the launcher with `--session`. A start
without `--session` is an inbound-disabled session, not a valid peer session.

### L-OC-19: An addressed test must use the implemented address grammar

**Incident (2026-08-12):** REALTEST-7 used a bare `@brain` while the contemporaneous
inbox configuration did not deliver it. The later implementation and its unit test now
accept **two** leading address forms: the canonical peer form `[sender -> @role ...]` and
a human's bare leading mention `@role ...`. A mention in the middle of prose remains
non-addressing. The earlier claim that `_recipients()` accepts only brackets was stale
documentation, found on 2026-08-13 by reading the current filter and its test
(`test_peer_inbox.py:107-133`, 8/8 passing).

**Rule:** Before attributing non-delivery to the inbox, read `_recipients()` and its tests.
For peer/broadcast traffic use `[sender -> @role]`; for a human one-role request a bare
leading `@role` is accepted. Do not infer either rule from an old incident write-up.

## Reusable Checklist

Before adding another OpenCode-connected Meta-Skill:

1. Bind role, agent, and outbound channel at process start.
2. Separate the documented intent from what the runtime actually enforces.
3. Keep credentials out of profiles and source control.
4. Test the installed OpenCode version, not only a published API page.
5. Exercise positive and deny paths in a real session.
6. Add the resulting limitation or correction here before claiming the capability active.
