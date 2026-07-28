# OpenCode Adoption Plan

## Goal

Make the useful, application-independent parts of `meta-skills-plugin` available to
OpenCode from this repository. Do not pretend that Claude Code hooks, agents, and
commands can be copied unchanged: OpenCode has its own skill loader, MCP lifecycle,
plugin hooks, agents, and permission model.

## Phase 1: Peer Communication

**Scope: active now.**

**Implementation state, 2026-07-29:** profiles, launchers, role-bound shared-channel and
Joe-DM filtering, durable watermarks, an active-session/idle guard, and OpenCode
`promptAsync` injection are implemented in Gitea commit `417960d`. The phase remains open
until the live acceptance cases pass; the current Brain standard-model route is blocked by
Bridge `CLIENT_UNAUTHORIZED`.

- Shared skill: `skills/peer-comms/SKILL.md`.
- OpenCode adapter: `integrations/opencode/`.
- Transport: `aie-mm-mcp` with one explicit role per process.
- Brain profile: `profiles/opencode.brain.jsonc`.
- Vibe profile: `profiles/opencode.vibe.jsonc`.
- Start contract: `bin/opencode-brain` or `bin/opencode-vibe`, each binding one role,
  matching primary agent, and one MCP write channel.
- Durable work: Gitea; short coordination: `ai-chat/#agent-tasks`.

Acceptance evidence:

1. OpenCode validates the selected profile.
2. The MCP reports the expected tool surface.
3. A read-only live call resolves as the configured peer identity.
4. A Brain-to-Vibe post is read back from the peer channel under the Brain identity.

The active startup contract is documented in `README.md`; measured state and remaining
limitations are in `STATUS.md`. The inbound Mattermost-to-session implementation exists in
commit `417960d`, but remains unaccepted until its live delivery cases pass; it must not be
inferred merely from a launcher or MCP connection.

## Current Rescope: Brain and Vibe

**Stand: 2026-07-28.** This is a bounded division of work, not a transfer of
infrastructure authority.

| Owner | Scope | Boundary |
|---|---|---|
| Brain | Address/IP truth, Bridge runtime and fallback, PVE, Swarm, NAS, backup, quorum, production deployment, and final acceptance. | No destructive or maintenance-window action without its recorded gate and rollback. |
| Vibe | Adversarial testing and bounded implementation for OpenCode, Meta-Skills, agents, commands, and plugin reliability. | No IP/DNS/PVE/NAS/Swarm/Bridge-runtime change, no infrastructure deploy, and no credential rotation. |

### Vibe's First Wave

1. Start a separate Vibe OpenCode process from `profiles/opencode.vibe.jsonc` and
   prove peer-channel read plus a role-correct reply.
2. Qualify portable shared skills with a trigger, positive test, negative test, and
   observed result before adapting one skill at a time.
3. Re-measure the known session/plugin/agent failures in a fresh runtime rather than
   trusting prior claims: plugin trigger coverage, session latency, OpenCode fallback,
   and model/agent behavior.
4. Record every failure, correction, model-role result, rollback, and next narrow test
   in a committed artifact and report it with the peer-comms address format.

### Brain's First Wave

1. Resolve conflicting `.99`/`.150` address assertions from live DHCP/DNS, host reachability,
   overlay, Prometheus target, and Bridge runtime evidence before changing any value.
2. Continue the P0 infrastructure audit sequence without cleanup: pve1 maintenance preflight,
   swarm2 data-owner/restore evidence, and NAS capacity inventory.
3. Accept Vibe's evidence adversarially before a shared skill, guard, or model assignment is
   treated as operational.

### Closed Learning Loop

`measured task -> raw evidence -> peer review -> accepted change or explicit rejection ->
skill/agent/model matrix update -> next bounded test`

An agent result, a registered hook, or a green unit suite alone never closes this loop.

## Phase 2: Shared Skills

**Scope: load and qualify, do not rewrite by default.**

OpenCode loads the repository's `skills/` directory through `skills.paths`. The first
review set is deliberately small and reusable:

| Shared skill | OpenCode status | Adoption test |
|---|---|---|
| `verify` | candidate | produces a fresh command-backed completion receipt |
| `systematic-debugging` | candidate | follows evidence -> hypothesis -> fix -> recheck |
| `tdd` | candidate | works with OpenCode edit and test tools |
| `git-worktrees` | candidate | respects OpenCode external-directory permissions |
| `triad-review` | candidate | maps to OpenCode review agents without duplicate work |
| `peer-comms` | active | Phase-1 evidence above |

Each candidate stays a shared `SKILL.md` when its instructions work in both runtimes.
Only a runtime-specific limitation belongs under `integrations/opencode/`.

## Phase 3: Claude-Code Capability Mapping

**Scope: assess before implementation.**

| Claude Code capability | OpenCode equivalent | Rule |
|---|---|---|
| Plugin skills | `skills.paths` | Share the skill source when portable. |
| MCP registration | `mcp` configuration | Use an explicit role and no embedded token. |
| Agents | `agent/*.md` or `agent` config | Recreate only a proven, bounded agent role. |
| Commands | `command/*.md` or `command` config | Recreate only a frequently used workflow. |
| Event hooks | OpenCode plugin hook surface | Port only after a direct event mapping and test. |
| Claude permissions | OpenCode `permission` rules | Preserve or tighten the boundary; never weaken it. |

No Claude Code hook is considered active in OpenCode until its OpenCode counterpart has
a measured trigger and outcome. The disabled Claude hook set is not a source of runtime
behavior.

## Phase 4: Native OpenCode Guards

**Scope: future, one guard at a time.**

Prioritize only guards with a clear OpenCode hook equivalent and a testable failure mode:

1. Pre-execution safety/permission guard.
2. Completion-evidence reminder based on actual tool results.
3. Commit/push verification gate.
4. Session-end durable handoff prompt.

Every guard needs a positive test, a deny/failure test, and a measurement showing it
fires in a real OpenCode session. A documented or merely registered hook is not proof
of operation.

## Non-Goals

- Do not run Claude Code hooks inside OpenCode.
- Do not merge Brain and Vibe identities in one OpenCode configuration.
- Do not create a second Mattermost client or store credentials in this repository.
- Do not claim feature parity before each capability has its OpenCode-specific evidence.
