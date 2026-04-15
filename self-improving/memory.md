# Memory (HOT Tier) — meta-skills Learning Store

> Updated by: meta:feedback, meta:creator Phase 5, manual
> Read by: meta:creator Phase 1, meta:feedback pattern matching

## Preferences

| Key | Value | Source | Date |
|-----|-------|--------|------|
| language | DE (communication), EN (code) | CLAUDE.md | 2026-04-08 |
| model_default | sonnet | meta:creator R2 | 2026-04-08 |
| max_tools | 4 per skill | meta:creator R4 | 2026-04-08 |
| skill_body_max | 150 lines | meta:creator R1 | 2026-04-08 |

## Patterns

| Pattern | Meaning | Learned |
|---------|---------|---------|
| "weniger Kaesten" | Fewer containers, not invisible | 2026-04-06 |
| "wie X" | Spirit of X, not 1:1 copy | 2026-04-06 |
| "billig" | Font thick + color bright + spacing low | 2026-04-06 |
| "ultrathink" | Thorough + creative + dont delegate | 2026-04-06 |
| "mach weiter" | Satisfied, next step | 2026-04-06 |

## Rules

| Rule | Source | Date |
|------|--------|------|
| Token-Effizienz = Architektur | Spec v3 | 2026-04-08 |
| Scripts vor LLM (deterministic) | R3 | 2026-04-08 |
| Phase 1 rejects >30% | Spec | 2026-04-08 |
| Jede Aenderung messen (eval) | Hardening | 2026-04-08 |

## Session 2026-04-13 Learnings

### New Preferences
- judge_count: 3 (Borda count, cross-model)
- judge_priority: kimi, qwen, devstral, codex, copilot, opencode, claude
- caveman_mode: internal_only (NEVER user-facing)
- plan_model: opus (ALWAYS, even if session model differs)
- executor_default: opencode/devstral (cheapest code-capable)
- sdd_activation: organic (only large tasks, never forced)

### New Patterns
- "council" = dispatch to multiple CLIs in parallel
- "judgment day" = 2 blind judges + convergence
- "autoreason" = A/B/AB + Borda judges + convergence
- "skill registry" = auto-generated compact rules for sub-agents
- Windows CLI: subprocess needs shell=True for .cmd wrappers

### New Rules
- Opus plans, cheap models execute (plan = multiplier)
- Theoretical warnings = INFO (no fix, no re-judge)
- Pre-commit: track both test AND lint status (PASS/FAIL/NOT_RUN)
- SDD = routing layer on existing skills, not new system
- CLAUDE.md = identity + references, NEVER data duplication

### Session 2026-04-14 Learnings

### New Patterns
- plugins-ci.yml = 5-job CI gate for meta-skills integrity (syntax, json, hooks, skills, harden)
- session-init CI check = warn on first prompt if last CI run failed (additionalContext injection)
- credential cleanup = vault.py + ssh_connect.py for ALL SSH, never hardcode passwords
- CI grep pitfall: `grep 'CRITICAL'` matches `CRITICAL: 0` — use `grep -E 'CRITICAL: +[1-9]'`
- hooks/lib/ exclusion = library helpers are NOT hooks, exclude from hook safety checks (maxdepth 1)

### New Rules
- CI/CD feedback loop: SESSION START -> PRE-COMMIT -> PRE-PUSH -> POST-PUSH -> ON DEMAND
- Every project with CLAUDE.md needs its own CI workflow in .github/workflows/
- Hook safety checks: exit 0, try/except stdin, no sys.exit(1) in non-Stop hooks
