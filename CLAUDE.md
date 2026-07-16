# meta-skills v4.4.0 — Enterprise Quality Engine

<!-- AIE-SSOT-BLOCK v1.0 · kanonisch: kb/ops/standards/PROJEKT-CLAUDE-BLOCK.md · NICHT lokal editieren -->
## AIE-Standards (gelten in jedem Projekt)
- **Gitea = Code-SSOT** (`10.40.10.82:3050/joe/<repo>`): committen + pushen IMMER nach Gitea. GitHub = nur öffentlicher Spiegel (Schreibrichtung intern→extern, NIE via GitHub zurück).
- **Secrets nie im Repo**: `.env`/Keys in `.gitignore`; Werte in aie-vault/OpenBao (`secret/<domain>/<service>-<key>`). Vor jedem Erst-Push: `git ls-files | grep -iE '\.env$|secret|credential|token|\.pem$|\.key$'` muss leer sein. Token nie in Remote-URLs (osxkeychain-Helper nutzt sie automatisch).
- **KEIN-MOCK (A33)**: keine Fakes/Stubs/Platzhalter in Prod-Pfaden; leer/down → ehrlich `—`. Test-Mocks nur unter `tests/`.
- **Verify-vor-Behaupten (M126)**: „läuft/grün/deployed/gefixt" nur mit gemessenem Beweis (Testlauf, Live-Probe, Senken-Check) — nie aus Doku/Memory/Agent-Summary.
- **Uncommitted = ungesichert**: Arbeitsstände regelmäßig committen + nach Gitea pushen — nur Gepushtes überlebt den Platten-Tod.
- **Bauteil-DoD**: Code + Tests + lauffähig + reproduzierbar + bedienbar; „fertig" = aktiviert + gemessen + genutzt, nicht „gebaut".
- **Wo-ist-was**: Bestand → `~/kb/ops/WAS-WIR-HABEN.md` · Fehler ZUERST → `~/kb/ops/KNOWN-ERRORS-DB.md` (troubleshoot-Skill) · Betriebsmodell/Tiers → `~/kb/ops/WER-MACHT-WAS.md` · System-Fakten → `~/kb/SYSTEM-FACTS.md`.

## Identity
Cooperative Skill Engine + Quality Gates + Adversarial Review + SDD Workflow.
All 7 research principles implemented: P1 Confidence Consensus, P2 Behavioral Tests,
P3 Orthogonal Revision, P4 Correction Promotion, P5 Write-Time QA, P6 Cost Routing,
P7 Context Recovery.

## Components
- **16 Skills**: creator, design, dispatch, doc-updater, feedback, git-worktrees, harden, init, judgment-day, knowledge, refactor-loop, statusbar, systematic-debugging, tdd, triad-review, verify
- **17 Commands**: /meta-audit, /meta-ci, /meta-create, /meta-design, /meta-discover, /meta-docs, /meta-feedback, /meta-harden, /meta-judgment, /meta-knowledge, /meta-loop, /meta-quality, /meta-snapshot, /meta-status, /meta-test, /meta-triad, /cancel-meta-loop
- **6 Agents**: doc-auditor, doc-editor, 3x doc-scanner, session-analyst
- **16 Hooks** across 7 events: session-start, session-init, correction-detect, scope-tracker, approach-guard, exploration-first, token-audit, quality-gate, context-recovery, meta-loop-stop, session-stop, session-end, **false-positive-guard** (4.7 confidence-drift), **org-naming-pre-push** (Wrong-Folder), **ahead-of-remote-warning** (Data-Loss), **working-set-watch** (Unversioned-Strategy)

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

## Hooks (12 across 7 events)

| Hook | Event | Addresses |
|------|-------|-----------|
| session-start | SessionStart | Honcho, open-notebook, CI check, watcher spawn |
| session-init | UserPromptSubmit | Prompt counter + P7 context recovery |
| correction-detect | UserPromptSubmit | Corrections + S10 compliance |
| scope-tracker | UserPromptSubmit | Multi-task drift (19/31 sessions) |
| approach-guard | PreToolUse/Bash | Wrong Approach (43x in report) |
| exploration-first | PreToolUse/Write\|Edit | Read before write + write-time QA (P5) |
| token-audit | PostToolUse | JSONL logging |
| quality-gate | PostToolUse/Bash | Test/lint failures + commit gate + push CI |
| context-recovery | PreCompact | State snapshot before compaction |
| meta-loop-stop | Stop | Objective loop gates |
| session-stop | Stop | User-facing verification + guidance |
| session-end | SessionEnd | Honcho write + state persist + cleanup |

## Self-Improving
- `self-improving/memory.md` — Preferences, patterns, rules
- `self-improving/corrections.md` — Mistakes not to repeat
- `oversight/` — Quality snapshots, calibration, autoreason results

## Rules
- Universal rules: see `Documents/CLAUDE.md`
- Infra rules: see `phantom-ai/.claude/rules/` (auto-loaded)
- Skill registry: `.claude/skill-registry.md` (auto-generated)
