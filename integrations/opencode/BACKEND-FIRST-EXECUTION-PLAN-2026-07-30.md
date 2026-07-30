# Backend-First Execution Plan

**Status:** active
**Date:** 2026-07-30
**Scope:** Phantom LLM Bridge, OpenCode adapter, and bounded agent qualification

## Decision

The Bridge backend is the authority for OpenCode model access. No new agent
role, shared-skill rollout, or standing worker is accepted before the Bridge
auth path, routing evidence, and deployment source are verified.

## Current Evidence

- The Bridge health endpoint returned HTTP 200 during the 2026-07-30 review.
- The local Bridge pytest suite completed successfully before this plan.
- The Bridge checkout is divergent from Gitea (`ahead 2`, `behind 1`); it is
  not a deploy source until it is integrated, tested, and reviewed.
- The OpenCode adapter profiles had overridden the Phantom provider and
  contained an inline Bridge client credential. The profile contract test
  reproduced four failures. Removing the overrides and disabling automatic
  approval for Vibe made the focused profile and launcher suites pass
  (`10 passed`).

## Gates

1. **Credential gate:** role profiles never contain provider credentials.
   The role launcher resolves the session credential without printing or
   persisting it. The credential owner decides and performs any required
   rotation; Vibe does not rotate or deploy credentials.
2. **Bridge gate:** the current source is rebased on Gitea, passes the full
   validation gate, receives independent review, and has a fresh authenticated
   Bridge probe before it can become a deployment candidate.
3. **Routing gate:** every enabled OpenCode model route has a measured Bridge
   event, provider result, and failure reason. Direct providers are an
   explicit, documented emergency fallback only.
4. **Agent gate:** qualify one role at a time in an isolated worktree with an
   exact task, actual test command, independent review, and Bridge ledger
   evidence. A configured role is not a qualified role.
5. **Peer gate:** do not mark the peer inbox complete until shared-channel,
   wrong-role, wrong-channel, duplicate, and busy-session cases are live
   proven.

## Work Order

### P0 - Adapter Safety

- Keep Phantom provider configuration only in the global OpenCode config.
- Keep role profiles credential-free.
- Never start Vibe with automatic approval.
- Preserve the role/channel binding and run the profile and launcher tests.

### P1 - Bridge Source and Runtime

- Integrate the divergent Bridge checkout with Gitea without dropping either
  side's changes.
- Run the repository validation gate and review the resulting diff.
- Diagnose the admin discovery-auth failure and provider-address drift from
  source plus fresh probes.
- Hand any image build, Swarm update, or credential rotation to Brain with a
  rollback and live-probe plan.

### P2 - OpenCode Qualification

1. Run one read-only planner prompt through the Bridge.
2. Run one reviewer against a known worktree diff.
3. Run one narrowly bounded worker change and reproduce its test.
4. Use a local mechanical worker only for an explicit mechanical task.

Every step records route, model, test output, review, residual risk, and
rollback path in Gitea before the next role is enabled.

### P3 - Shared Skills and Peer Adapter

Qualify `peer-comms`, `verify`, `systematic-debugging`, `git-worktrees`, and
`tdd` one at a time. The uncommitted plugin and skill artifacts are inventoried
and split into reviewable commits; they are not accepted as a batch.

## Ownership

- **Brain:** Bridge runtime, credentials, production deployment, and final
  acceptance.
- **Vibe:** bounded adapter, launcher, plugin, and test work only. No
  infrastructure change, secret rotation, or deployment.
