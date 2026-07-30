# OpenCode Peer Messaging — TODO and Acceptance

**Stand:** 2026-07-29

This is the operational backlog for the Meta-Skills OpenCode adapter. Status reflects
measured evidence, not implementation intent.

## Done

- [x] Separate Brain/Vibe profiles, one explicit Mattermost role each.
- [x] Global `opencode-brain` and `opencode-vibe` commands; role and primary agent bind at
  process start and caller-supplied `--agent` is rejected.
- [x] Shared-channel messages for one/both peers: `[joe -> @brain]`, `[joe -> @vibe]`, and
  `[joe -> @brain @vibe]`.
- [x] DM intake for only the addressed peer from Joe or the other peer; all other DM
  participants are excluded.
- [x] Vault-backed helper with per-role/per-channel shared and DM watermarks.
- [x] OpenCode plugin: active-session tracking, idle-only injection, 20-message batch cap,
  source-specific acknowledgement, and structured logs.
- [x] Unit checks: Python 6 passed; Node 2 passed; profile JSON and launcher syntax passed;
  Vibe and Brain helper baselines completed read-only.
- [x] Errors and corrections are recorded in `LEARNINGS.md`; status and limitations in
  `STATUS.md`.
- [x] **Vibe live proof:** Brain DM was automatically injected; Vibe executed a read-only
  pytest/Node review and returned `6/6` and `2/2` in Mattermost.
- [x] **Brain live proof:** Vibe DM was automatically injected into Brain; Brain made and
  delivered a gate decision through Mattermost.

## Blocking Before Activation

- [ ] **Bridge authorization re-probe:** the pre-correction direct `opencode-brain run` reached a
  session but received HTTP 401 `CLIENT_UNAUTHORIZED`. Re-run one normal prompt on the corrected
  launcher/profile path without printing or copying a token; diagnose only if it still fails.
- [ ] Restart both peers after the plugin/profile commit is present. Plugins load only when
  OpenCode starts.

## Live Acceptance Cases

After the authorization blocker is resolved, record receipts in `STATUS.md` and a Gitea
commit.

- [ ] Joe posts `[joe -> @brain @vibe] inbox delivery test` in `#agent-tasks`; both idle
  sessions receive one injected message and can acknowledge it.
- [ ] Re-poll does not inject an acknowledged post again.
- [ ] One-recipient, wrong-role, and wrong-channel messages reach only the intended result.
- [ ] A Joe or peer DM reaches only its recipient; shared channel remains the one-to-both
  route.
- [ ] A busy target retains the message and receives it after `session.idle`; no competing
  turn starts.
- [ ] A source/helper failure leaves the watermark unchanged.

## Follow-ups

- [ ] Decide whether ordinary MCP read tools need a hard channel-read whitelist. The inbox
  plugin filters its own input; generic MCP reads do not enforce `AIE_MM_READ_CHANNEL_NAMES`.
- [ ] Add a delivery receipt command only after the end-to-end behaviour is proven. Do not add
  a misleading `/mm-*` role switch: identity remains a start-time property.
