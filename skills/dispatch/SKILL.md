---
name: dispatch
description: Dispatch parallel sub-agents for independent out-of-scope tasks. Two-stage review (spec compliance THEN code quality). Caveman output for internal agent communication only.
trigger: dispatch agents, parallel tasks, sub-agent, delegate, out of scope, unabhaengige aufgaben, parallel bearbeiten
model: sonnet
allowed-tools: [Read, Grep, Bash, Agent]
user-invocable: true
complexity: agent
last-audit: 2026-04-14
version: 1.0.0
token-budget: 3000
---

# Dispatch — Parallel Sub-Agent Development

## When to Dispatch

```
DISPATCH when:
  2+ independent problems (no shared state)
  Each problem is UNDERSTOOD (root cause known)
  Tasks don't need full system context
  Work can run in parallel

DO NOT dispatch when:
  Tasks depend on each other
  Architecture decision needed (ask Joe)
  Shared state between tasks
  Problem not yet understood (use systematic-debugging first)
```

## Agent Prompt Structure

For EACH sub-agent, provide:

1. **Specific scope** — One file, one subsystem, one test suite
2. **Clear goal** — "Make these tests pass" / "Score above 80"
3. **Constraints** — "Don't change files outside X/" / "No new dependencies"
4. **Expected output** — Summary of findings + changes made

## Model Selection (A5b)

```
haiku:   Checks, audits, status reports, simple lint fixes
sonnet:  Code fixes, multi-file tasks, analysis
opus:    Architecture decisions, complex multi-step (selten)

DEFAULT: haiku (cheapest that can do the job)
Upgrade only when haiku demonstrably fails
```

## Caveman Mode (Internal Only)

For AUTONOMOUS/INTERNAL agent communication — save tokens:
- Agent reports: `[thing] [action] [result]. [next step].`
- Example: "3 lint errors fixed. 2 remaining in utils.py. Need ruff --fix."

**NEVER caveman for:**
- User-facing summaries (Joe reads these)
- Cooperative skills (/meta-create, /meta-feedback)
- Documentation (ERPNext, open-notebook, CLAUDE.md)
- Mattermost messages

## Skill Resolver Protocol (vor JEDEM Sub-Agent Launch)

1. **Registry laden** (1x pro Session cached):
   ```bash
   cat .claude/skill-registry.json
   ```
   If not present: run `python3 scripts/build-skill-registry.py`.

2. **Skills matchen** nach:
   - **Code Context:** .py → Python Rules, .ts → TypeScript Rules
   - **Task Context:** review → quality Skills, fix → debugging Skills
   - Max 5 Skill-Blocks pro Agent (~400-600 Tokens)

3. **Inject in Sub-Agent Prompt** (TEXT, NICHT Pfade):
   ```
   ## Project Standards (auto-resolved)
   {matching Compact Rules Blocks aus Registry}
   ```
   VOR den task-spezifischen Instructions.

4. **Check Resolution Feedback** after Agent return:
   - `injected` → OK, standards were used
   - `fallback|none` → Reload registry, provide standards to next agent

---

## Two-Stage Review (After Each Agent Returns)

### Stage 1: Spec Compliance (FIRST)

- Did the agent do what was asked?
- All requirements addressed?
- No under-building (missing features)?
- No over-building (unrequested additions)?

**If spec fails:** Re-dispatch with clarification. Do NOT proceed to Stage 2.

### Stage 2: Code Quality (SECOND, only after Stage 1 passes)

- Tests pass?
- Lint clean?
- No regressions?
- Code follows project conventions?

**Never Stage 2 before Stage 1** — wrong order causes rework.

## Handling Agent Status

| Status | Action |
|--------|--------|
| DONE | Proceed to spec review |
| DONE_WITH_CONCERNS | Address concerns before review |
| NEEDS_CONTEXT | Provide context, re-dispatch (same model) |
| BLOCKED | Assess: context problem → re-dispatch; reasoning → upgrade model; too large → break apart |

## Example: 3 Independent Lint Fixes

```
Agent 1 (haiku): "Fix ruff errors in voice-gateway/plugins/"
  Scope: voice-gateway/plugins/*.py
  Goal: ruff check exits 0
  Constraint: Don't change API behavior

Agent 2 (haiku): "Fix ruff errors in voice-gateway/core/"
  Scope: voice-gateway/core/*.py
  Goal: ruff check exits 0
  Constraint: Don't change API behavior

Agent 3 (haiku): "Fix eslint errors in ops-dashboard/src/"
  Scope: ops-dashboard/src/**/*.ts
  Goal: npm run lint exits 0
  Constraint: Don't change component behavior

→ All 3 run in parallel
→ Two-stage review each result
→ Merge results
```

## Examples

### Example 1: Fix lint errors across 3 subsystems

```
dispatch 3 agents to fix lint errors in parallel:
  Agent 1 (haiku): scope=src/auth/, goal=ruff check exits 0
  Agent 2 (haiku): scope=src/api/, goal=ruff check exits 0
  Agent 3 (haiku): scope=src/ui/, goal=eslint exits 0
```

### Example 2: Parallel test fixes

```
dispatch 2 agents for independent test failures:
  Agent 1 (sonnet): scope=tests/test_auth.py, goal=make all tests pass
  Agent 2 (sonnet): scope=tests/test_api.py, goal=make all tests pass
  Constraint: Don't change production code behavior
```
