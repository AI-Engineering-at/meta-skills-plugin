# OpenCode Adapter Status

**Stand:** 2026-08-12

## Purpose

The adapter makes portable Meta-Skills available to OpenCode while preserving the runtime
boundary: shared instructions live under `skills/`, while OpenCode profiles, launchers,
and plugins live here.

## Startup Contract

Start a peer process only through one launcher:

```sh
opencode-brain
opencode-vibe
opencode-vibe
opencode-brain run "summarize the current task"
```

The launcher atomically selects:

| Value | Brain | Vibe |
|---|---|---|
| Mattermost role | `brain` | `vibe` |
| OpenCode primary agent | `brain` | `vibe` |
| MCP identity | `aie-mm-mcp-brain` | `aie-mm-mcp-vibe` |
| Default write channel | `ocode-team` | `ocode-team` |
| Explicit compatibility path | `team-infra` / `town-square` | `team-infra` / `town-square` |

It exports `AIE_MM_ROLE`, `AIE_OPENCODE_AGENT`, `AIE_MM_WRITE_CHANNEL_NAMES`, and
`AIE_MM_READ_CHANNEL_NAMES`, loads exactly one role profile through `OPENCODE_CONFIG`,
and rejects a caller-provided `--agent`. Kimi and Pruefer follow the same
contract through their own profiles. The agent is selected again with OpenCode's
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
| `opencode --version` | `1.18.9` | Re-measured locally on 2026-07-30 |
| `opencode debug agent brain` with Brain profile | Resolved as primary agent `brain` | Profile parsing and agent registration |
| `opencode debug agent vibe` with Vibe profile | Resolved as primary agent `vibe` | Profile parsing and agent registration |
| `opencode models phantom` with the Vibe profile | Phantom models remained available | `OPENCODE_CONFIG` augments the normal local configuration |
| `opencode mcp list` with Brain and Vibe profiles | `aie-mm-mcp connected` | Earlier live transport check |
| Brain-to-Vibe post and read-back | Role-correct round trip observed in `#town-square` | Earlier controlled fallback check |
| Vibe-role read-only smoke test | DMs, user lookup, and post search succeeded; team-channel list returned 403 | Endpoint-specific scope/membership boundary, not token absence |
| Brain and Vibe inbox helper baseline | Read-only `poll` initialized each role/channel watermark with no historical replay | Vault-backed peer inbox path |
| Brain→Vibe DM helper probe | Vibe helper selected the delivered Brain post after adding peer-DM allow-list | Real source/filter proof; plugin restart still required |
| Vibe automatic task execution | Brain DM `a3k61qihxidj5eb9roccy3s3ua` was injected; Vibe ran both requested test commands and replied `6/6`, `2/2` | End-to-end Vibe-side receipt, model execution, tools, and MM reply proven |
| Brain automatic receipt and gate response | Vibe DM `7ydnfedeyfy8ikp1b4hd5d4pfy` appeared as an inbound Brain prompt; Brain posted delivery/gate response | End-to-end Brain-side receipt, reasoning, and MM reply proven |
| `opencode-brain run` session start | Launcher reached OpenCode session creation, then Bridge returned `401 CLIENT_UNAUTHORIZED` | Historical 2026-07-28 result; fresh runtime re-probe remains required |
| Profile JSON and launcher syntax | Valid JSON; `zsh -n` passed | Static configuration |

### Audit Update — 2026-07-30

- Role profiles are credential-free and no longer override the Phantom provider.
  Profile and launcher tests passed locally after the correction.
- Vibe no longer starts with automatic approval. This is a static launcher
  guarantee; it is not a live delegation acceptance.
- Bridge `/healthz` returned HTTP 200 in the same audit, but no authenticated
  model completion or Swarm deployment was performed.
- The previous `CLIENT_UNAUTHORIZED` result is intentionally retained as
  historical evidence. Do not classify it as current until the corrected
  launcher/profile path has a fresh normal-prompt receipt.

The OpenCode documentation inspected for this work describes the session APIs
`session.promptAsync` and `session.prompt`. These are the supported OpenCode mechanisms
for injecting a message into a known session. Their use in an inbound loop is not yet
live-proven on the installed binary.

### Operational update — 2026-08-12

- Persistent roles are `brain`, `vibe`, `ocode-kimi`, and `ocode-pruefer`.
- All four default to `#ocode-team`; direct `opencode/*` models are mandatory
  until Bridge-T2 acceptance.
- A resumed `--session` is exported as `AIE_OPENCODE_SESSION_ID`, allowing the
  inbox plugin to poll immediately instead of waiting for a local prompt.
- Vibe uses the same minimal profile shape as Kimi and Pruefer. Role-specific
  transport shape as Kimi and Pruefer, while retaining Vibe's explicit
  read-only top-level permissions, shared skill paths, and bounded role prompt.
- Operator note from Joe, not independently measured here: anonymous OpenCode
  quota is associated with public IP; router reconnection changes that IP.
  Router restart is not an automatic fallback because it affects the whole network.
- Historical runtime evidence at 2026-08-12 19:24--19:26 UTC: the existing Kimi and
  Pruefer sessions each exceeded 100 messages and then entered automatic
  compaction. Their `agent=compaction` calls to `opencode/big-pickle` both
  returned `Rate limit exceeded` repeatedly. Both roles had answered a normal
  provider canary immediately beforehand. Therefore model/profile availability
  and compaction quota are separate states; do not keep retrying an old session
  when compaction is quota-blocked. Export it, retain the evidence, and start a
  fresh bounded session after the operator restores quota.
- Browser use is backup only, not the primary dispatch or recovery path.

## Current Capability

- `peer-comms` is the active cross-runtime Meta-Skill.
- Brain and Vibe can run separately with their own Mattermost roles.
- The launch contract prevents accidental selection of the other peer's configured agent.
- Mattermost transport and a controlled fallback-channel round trip have prior live
  evidence.
- `peer_inbox.py` plus `plugins/peer-inbox.mjs` are registered in both profiles. They use
  the selected role, shared channel, and DMs from Joe or the other peer only; their unit
  gates pass.

## Not Implemented

- The peer DM path is live-proven in both directions. The direct `opencode-brain run` default
  model path needs a fresh post-correction probe; the historical Bridge 401 must not be
  misclassified as an inbox failure.
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

Use one recipient for a role-specific request. A direct message from Joe, Brain, or Vibe to
the other peer is also input for that one recipient; it needs no address prefix because the
DM recipient selects the role. A direct message cannot reach both peers at once. Use the
shared peer channel for messages that both must receive.

## Version Boundary

The installed binary was re-measured as `1.18.9` on 2026-07-30. The local
`@opencode-ai/plugin` dependency was previously observed as `1.17.6`; re-measure it before
using a plugin API that was introduced after that package version.
Every plugin hook or SDK call must therefore be verified against the installed runtime,
not assumed from the newer documentation.
