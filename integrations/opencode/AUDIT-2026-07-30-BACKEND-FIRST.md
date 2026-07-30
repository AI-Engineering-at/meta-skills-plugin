# Backend-First Audit — OpenCode Adapter

**Date:** 2026-07-30
**Scope:** `meta-skills-plugin` OpenCode adapter and its Bridge dependency
**Result:** source checks pass; runtime qualification remains open

## Measured Evidence

| Check | Result |
| --- | --- |
| Git branch | `main` matches `gitea/main` after commits `42b37b2` and `d501e69` |
| Python adapter tests | `16 passed` |
| Node inbox/statusbar tests | `5 passed` |
| Shell syntax | launcher, watcher, and wrapper passed `zsh -n` |
| OpenCode binary | `1.18.9` |
| Bridge health | `GET /healthz` returned HTTP 200 |

## Corrected Findings

1. Both role profiles had a Phantom-provider override with an inline client
   credential. The existing contract tests reproduced four failures. Profiles
   are now credential-free and rely on the session launcher for the runtime
   credential.
2. Vibe's canonical launcher added automatic approval. It now always invokes
   the selected role without `--auto`; a launcher regression test locks this.
3. The untracked statusbar plugin had embedded admin credential material. It
   now requires `AIE_BRIDGE_ADMIN_TOKEN` and returns without a Bridge request
   when that environment variable is absent. Its source contract is tested.
4. Adapter status documents described OpenCode 1.18.5 and an old Bridge 401 as
   current. The binary is now recorded as 1.18.9; the 401 remains historical
   until a fresh normal-prompt probe is captured.

## Open Gates

- Credential owner/Brain must decide and execute any required rotation.
- The corrected launcher needs one authenticated, normal OpenCode prompt with
  Bridge event evidence before agents are enabled.
- Peer inbox still needs shared-channel, duplicate, wrong-role, wrong-channel,
  and busy-session live acceptance receipts.
- `skills/cron`, `skills/debug`, and `skills/loop` are present locally but
  untracked and unqualified. They are explicitly excluded from this audit
  commit and must not be treated as active capabilities.

## Boundary

No Bridge image build, Swarm update, credential rotation, or productive agent
task occurred in this audit.
