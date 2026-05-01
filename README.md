# meta-skills v4.0.0 — Enterprise Quality Engine for Claude Code

> Enterprise-grade plugin for Claude Code: 16 skills, 17 commands, 9 hooks, 6 agents, 27 scripts.
> Implements all 7 research principles. Adversarial review. CI/CD gates. Cross-model refinement.

## Install

```bash
# Register as local marketplace (once)
claude plugins marketplace add ./meta-skills --scope local

# Install plugin (survives restarts)
claude plugins install meta-skills@meta-skills-local --scope local

# Verify
claude plugins list | grep meta-skills
```

## Architecture

```
meta-skills/
  .claude-plugin/plugin.json       # Plugin manifest (v4.0.0)
  hooks/
    hooks.json                     # 7 events, 16 hooks (v4.4.0)
    lib/config.py                  # Centralized settings (all tunable values)
    lib/services.py                # Shared clients (Honcho, open-notebook, vault)
    lib/hook_wrapper.py            # Shared hook utilities
    session-init.py                # First-prompt: Honcho + open-notebook + CI + watcher
    session-stop.py                # Auto-summary + Honcho + KB recommendation + P7 state
    correction-detect.py           # Correction detection + S10 compliance
    scope-tracker.py               # Topic drift advisory (3+ switches)
    approach-guard.py              # Unauthorized strategy switch blocker
    exploration-first.py           # Read-before-write enforcer (P5)
    quality-gate.py                # Test/lint failure gate + commit/push checks
    token-audit.py                 # Per-tool-call token measurement (JSONL)
    meta-loop-stop.py              # Objective iteration loop gates
  skills/                          # 16 skills with SKILL.md + references/
  commands/                        # 17 slash commands
  agents/                          # 6 sub-agents (doc-auditor, doc-editor, 3x scanner, session-analyst)
  scripts/                         # 27 deterministic Python scripts
  self-improving/                  # Plugin-local learning (memory.md, corrections.md)
  oversight/                       # Quality snapshots, calibration, autoreason results
  plans/                           # Implementation plans
```

## Skills (16)

| Skill | Purpose |
|-------|---------|
| **creator** | Cooperative skill creation (5 phases) |
| **design** | Visual DESIGN.md generator |
| **dispatch** | Intelligent skill routing |
| **doc-updater** | Documentation sync orchestrator |
| **feedback** | Bidirectional end-of-session review |
| **git-worktrees** | Parallel branch workflow |
| **harden** | Automated SCAN-TRIAGE-FIX-VERIFY-REPORT loop |
| **init** | Project entry point (audit/goal/setup) |
| **judgment-day** | 2 blind judges, convergence pattern |
| **knowledge** | Knowledge funnel (log/search/sync/audit) |
| **refactor-loop** | Scan-Improve-Verify cycle (one change per iteration) |
| **statusbar** | Session lifecycle (statusline + watcher + sync) |
| **systematic-debugging** | Root-cause analysis framework |
| **tdd** | Test-driven development workflow |
| **triad-review** | 3-perspective adversarial review |
| **verify** | No completion without evidence (Iron Law) |

## Commands (17)

| Command | Purpose |
|---------|---------|
| `/meta-create` | Cooperative skill creation |
| `/meta-design` | Visual DESIGN.md generator |
| `/meta-discover` | Session pattern analysis → skill suggestions |
| `/meta-docs` | Doc sync via agent team (presets: quick, infra, full) |
| `/meta-feedback` | End-of-session review |
| `/meta-knowledge` | Knowledge funnel operations |
| `/meta-audit` | Skill audit (usage, staleness, efficiency) |
| `/meta-harden` | Automated hardening scan + fix |
| `/meta-judgment` | Adversarial judgment day |
| `/meta-ci` | CI/CD status dashboard |
| `/meta-loop` | Objective iteration loop with real gates |
| `/cancel-meta-loop` | Stop active meta-loop |
| `/meta-quality` | Quality snapshot |
| `/meta-snapshot` | Full plugin state snapshot |
| `/meta-status` | Plugin health check |
| `/meta-test` | Behavioral skill testing |
| `/meta-triad` | 3-perspective adversarial review |

## Hooks (9)

| Hook | Event | Addresses |
|------|-------|-----------|
| session-start | SessionStart | Honcho, open-notebook, CI check, watcher spawn |
| session-init | UserPromptSubmit | Prompt counter + P7 context recovery |
| correction-detect | UserPromptSubmit | Correction patterns + S10 compliance |
| scope-tracker | UserPromptSubmit | Multi-task drift advisory |
| approach-guard | PreToolUse (Bash) | Wrong Approach blocker |
| exploration-first | PreToolUse (Write\|Edit) | Read-before-write + write-time QA (P5) |
| token-audit | PostToolUse (all) | JSONL logging per tool call |
| quality-gate | PostToolUse (Bash) | Test/lint failures + commit gate + push CI |
| context-recovery | PreCompact | State snapshot before context compaction |
| meta-loop-stop | Stop | Objective loop gates |
| session-stop | Stop | User-facing verification + guidance |
| session-end | SessionEnd | Honcho write + state persist + cleanup |

## 7 Research Principles

| # | Principle | Implementation |
|---|-----------|----------------|
| P1 | Confidence-Weighted Consensus | Borda count with high/medium/low confidence → verdict levels |
| P2 | Behavioral Tests | test-scenario.md per skill, pass/fail regex validation |
| P3 | Orthogonal Revision | Author C generates fundamentally different approach; recombine B+C→D |
| P4 | Correction Promotion | User corrections → persistent rules (corrections.md → CLAUDE.md) |
| P5 | Write-Time QA | exploration-first hook: 3 reads before first write |
| P6 | Cost Routing | Model assignment per task complexity (haiku→sonnet→opus) |
| P7 | Context Recovery | Prompt counter + state sentinel, survives compaction |

## Quality System

| Component | What | Inspired by |
|-----------|------|-------------|
| **harden** | Automated SCAN-TRIAGE-FIX-VERIFY-REPORT loop | sd0x-dev-flow, Citadel |
| **judgment-day** | 2 blind judges parallel, convergence pattern | gentle-ai |
| **quality-gate** | Auto-detect test/lint failures + commit gate | Plankton, pilot-shell |
| **meta-loop** | Objective iteration loop with real gates | ralph-loop |
| **refactor-loop** | Scan-Improve-Verify cycle (one change per iteration) | adversarial-dev |
| **verify** | No completion without evidence (Iron Law) | superpowers |
| **autoreason** | Cross-model refinement (7 CLIs, Confidence Borda, Orthogonal Revision) | NousResearch/autoreason |
| **behavioral-tests** | test-scenario.md per skill, pass/fail regex validation | OpenJudge Skill Graders |
| **context-recovery** | Prompt counter + state sentinel, survives compaction | sd0x-dev-flow |

## Scripts (27)

### Core Quality
| Script | Purpose |
|--------|---------|
| `harden.py` | Frontmatter validation + automated fix |
| `autoreason-skills.py` | Cross-model adversarial refinement (7 CLIs) |
| `test-skill.py` | Behavioral test runner |
| `eval.py` / `eval-skill.py` | Quality scoring (0-100) |
| `validate.py` | CI gate (frontmatter validation) |
| `ci-status.py` | CI/CD status monitor |

### Session Lifecycle
| Script | Purpose |
|--------|---------|
| `statusline.py` | Rainbow statusbar (model, cost, context) |
| `session-watcher.py` | Per-session guardian (RAM warning, ghost cleanup) |
| `process-monitor.py` | System-wide process monitor |
| `benchmark-session.py` | Token benchmark (before/after comparison) |
| `token-report.py` | Token efficiency analysis from audit data |

### Plugin Management
| Script | Purpose |
|--------|---------|
| `plugin-setup.py` | First-run setup (auto/interactive, cross-platform) |
| `build-skill-registry.py` | Auto-generate skill registry |
| `project-scan.py` | Project scanner (stack, files, LOC, quality) |
| `quality-snapshot.py` | Full plugin quality snapshot |
| `oversight.py` | Oversight report generator |
| `migrate-frontmatter.py` | Frontmatter migration tool |
| `promote-corrections.py` | Promote corrections to rules |
| `reworker.py` | Auto-fixer (diagnose + fix score problems) |
| `filter-meta.py` | Metadata filter utility |
| `setup-meta-loop.py` | Meta-loop setup |
| `session-end-sync.py` | End-of-session sync helper |

## Configuration

Centralized settings in `hooks/lib/config.py`. Override via `~/.claude/plugins/data/meta-skills/config.json`:

```json
{
  "features": {
    "watcher": true,
    "correction_detect": true,
    "scope_tracker": true,
    "approach_guard": true,
    "exploration_first": true
  },
  "thresholds": {
    "min_reads_before_write": 3,
    "consecutive_failures_warn": 3,
    "scope_drift_warn_switches": 3,
    "correction_pause_count": 2,
    "context_recovery_gap": 10
  },
  "autoreason": {
    "num_judges": 3,
    "max_passes": 5,
    "convergence_k": 2,
    "cli_timeout_s": 180
  },
  "quality_gate": {
    "block_commit_on_lint_fail": false,
    "block_push_on_ci_fail": false,
    "warn_commit_without_lint": true
  }
}
```

## CI/CD

GitHub Actions workflow (`plugins-ci.yml`) with 5 gates:

1. **Syntax** — `py_compile` all Python files
2. **JSON** — plugin.json validation
3. **Hook Safety** — exit 0 + crash-safety checks
4. **Skill Validation** — frontmatter + body length
5. **Harden Scan** — `harden.py --scan` (0 CRITICAL required)

## Self-Improving System

- `self-improving/memory.md` — Preferences, patterns, learned rules
- `self-improving/corrections.md` — Mistakes not to repeat (promotes to rules)
- `oversight/` — Quality snapshots, calibration data, autoreason results

## Services Integration

| Service | Purpose |
|---------|---------|
| **Honcho** | Cross-session user context (peer detection, derived summaries) |
| **open-notebook** | Knowledge base (RAG search, source creation) |
| **GitHub Actions** | CI/CD gates (5 workflows) |

## v4.0 Changelog

- [x] Phase 1: Centralized settings (hooks/lib/config.py)
- [x] Phase 2: English translation (all hook output messages)
- [x] Phase 3: Centralized state manager (hooks/lib/state.py — replaces 7 patterns)
- [x] Phase 4: Hook event expansion (4→7 events, 9→12 hooks)
- [x] Phase 5: Command standardization (all 17 → Pattern A or B, <10 lines each)
- [x] Phase 6: Skill frontmatter schema (type/category/requires on all 16)
- [x] Phase 7: Documentation + v4.0.0 release

## License

MIT

## Author

[AI Engineering](https://ai-engineering.at) — kontakt@ai-engineering.at
