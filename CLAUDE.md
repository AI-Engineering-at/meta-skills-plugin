# meta-skills v3.1.0 — Quality Engine (all 7 Principles implemented)

## Identity
Cooperative Skill Engine + Quality Gates + Adversarial Review + SDD Workflow.
All 7 research principles implemented: P1 Confidence Consensus, P2 Behavioral Tests,
P3 Orthogonal Revision, P4 Correction Promotion, P5 Write-Time QA, P6 Cost Routing,
P7 Context Recovery.

## Components
- **16 Skills**: creator, design, dispatch, doc-updater, feedback, git-worktrees, harden, init, judgment-day, knowledge, refactor-loop, statusbar, systematic-debugging, tdd, triad-review, verify
- **16 Commands**: /meta-audit, /meta-ci, /meta-create, /meta-design, /meta-discover, /meta-docs, /meta-feedback, /meta-harden, /meta-judgment, /meta-knowledge, /meta-loop, /meta-quality, /meta-snapshot, /meta-status, /meta-test, /cancel-meta-loop
- **6 Agents**: doc-auditor, doc-editor, 3x doc-scanner, session-analyst
- **9 Hooks**: session-init, correction-detect, scope-tracker, approach-guard, exploration-first, token-audit, quality-gate, meta-loop-stop, session-stop

## Quality System

| Component | What | Inspired by |
|-----------|------|-------------|
| **harden** | Automated SCAN-TRIAGE-FIX-VERIFY-REPORT loop | sd0x-dev-flow, Citadel |
| **judgment-day** | 2 blind judges parallel, Convergence Pattern | gentle-ai |
| **quality-gate hook** | Auto-detect test/lint failures + commit gate | Plankton, pilot-shell |
| **meta-loop** | Objective iteration loop with real gates | ralph-loop |
| **refactor-loop** | Scan-Improve-Verify cycle (ONE change per iteration) | adversarial-dev |
| **verify** | NO COMPLETION WITHOUT EVIDENCE (Iron Law) | superpowers |
| **skill-registry** | Automatic Compact Rules injection for sub-agents | gentle-ai Skill Resolver |
| **autoreason** | Cross-model refinement (7 CLIs, Confidence Borda, Orthogonal Revision) | NousResearch/autoreason, MCO, SE-Agent |
| **behavioral-tests** | test-scenario.md per skill, pass/fail regex validation | OpenJudge Skill Graders |
| **context-recovery** | Prompt counter + state sentinel, survives compaction | sd0x-dev-flow |

## Model Assignment (Per-Phase)

| Task | Model | Reason |
|------|-------|--------|
| Explore / Read-Only | haiku | Structural, cheap |
| Code Review (Judges) | haiku | Pattern-matching |
| Implementation | sonnet | Code understanding |
| Architecture | opus | Complex decisions |
| Fix-Agent | sonnet | Needs code understanding |
| Archive / Status | haiku | Mechanical |

## Hooks (9 total)

| Hook | Event | Addresses |
|------|-------|-----------|
| approach-guard | PreToolUse/Bash | Wrong Approach (43x in report) |
| scope-tracker | UserPromptSubmit | Multi-task drift (19/31 sessions) |
| exploration-first | PreToolUse/Write\|Edit | Read before write + write-time QA (P5) |
| correction-detect | UserPromptSubmit | Corrections + S10 compliance |
| quality-gate | PostToolUse/Bash | Test/lint failures + commit gate + push CI check |
| meta-loop-stop | Stop | Objective loop gates |
| session-stop | Stop | Verification + Honcho + P7 state summary |
| session-init | UserPromptSubmit | Context loading + CI warning + P7 recovery |
| token-audit | PostToolUse | JSONL logging |

## Self-Improving
- `self-improving/memory.md` — Preferences, patterns, rules
- `self-improving/corrections.md` — Mistakes not to repeat
- `oversight/` — Quality snapshots, calibration, autoreason results

## Rules
- Universal rules: see `Documents/CLAUDE.md`
- Infra rules: see `phantom-ai/.claude/rules/` (auto-loaded)
- Skill registry: `.claude/skill-registry.md` (auto-generated)
