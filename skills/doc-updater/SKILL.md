---
name: doc-updater
description: Synchronizes documentation after deploys, version bumps, or infra changes using 3 parallel haiku scanners, a sonnet editor, and optional opus auditor. Use when: "update docs", "sync docs", "refresh index", "docs outdated", "docs sync", "docs stale", "after deploy", "version bump"
complexity: agent
model: sonnet
allowed-tools: [Read, Grep, Glob, Edit]
user-invocable: true
last-audit: 2026-04-14
version: 1.0.0
token-budget: 5000
type: meta
category: documentation
requires: []
produces: [documentation]
cooperative: false
---

# doc-updater v2 — Agent Team Orchestrator

## Usage

```
/meta-docs        # Quick: Tier 1 core docs only (default)
/meta-docs infra  # Core + infrastructure docs (Tier 1+2)
/meta-docs full   # All tiers + Opus GAP analysis
```

## Presets

| Preset | Workers | Auditor | Use Case |
|--------|---------|---------|----------|
| quick | doc-scanner-core | — | Version bump, deploy |
| infra | doc-scanner-core, doc-scanner-infra | — | Node/topology changes |
| full | all 3 scanners | doc-auditor | Major changes, releases |

## Smart-Routing

No preset given → analyze recent changes: pyproject.toml → quick, 03-infrastructure.md → infra, swarm/node in git log → infra, multiple areas → full, no changes → quick.

## Critical Rules

1. **persona_prompt.md**: NEVER modify for tool/skill info. Factual infra corrections only.
2. **Version from pyproject.toml** — single source of truth.
3. **Count, don't guess** — always run verification commands.
4. **Deploy path is /opt/phantom-ai/** — never /root/ai-stack/.
5. **One commit per sync** — message: `docs: sync to vX.Y.Z`.
6. Archive/audit files are READ-ONLY.
7. **09-anonymization.md** codenames are STABLE — never flag as stale.

## Execution Flow

See `references/execution-flow.md` for complete 7-step workflow.

Flow: Parse args → Gather source-of-truth → Dispatch scanners (parallel, haiku) → Merge → Dispatch editor (sonnet) → Commit → Dispatch auditor (full only, opus).

## Severity

STALE_VERSION → auto-fix via editor. STALE_ROLE → auto-fix via editor. MISSING_ENTRY → flag to user. ORPHANED_REF → flag to user.

## Reference Files

- references/execution-flow.md — Complete 7-step execution workflow
- references/scanner-prompts.md — Scanner agent prompts
- references/editor-prompt.md — Editor consolidator prompt
- references/auditor-prompt.md — Auditor GAP analysis prompt
