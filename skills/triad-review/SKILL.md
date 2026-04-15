---
name: triad-review
description: 3 specialized attackers find vulnerabilities from different perspectives. No blind duplication — each attacker has a different target.
trigger: triad review, security review, threat model, vulnerable, attack, test the code
model: haiku
allowed-tools: [Agent, Read, Grep, Bash]
user-invocable: true
complexity: agent
last-audit: 2026-04-14
version: 1.0.0
token-budget: 4000
type: meta
category: quality
requires: []
produces: [quality-report]
cooperative: false
---

# Triad Review — 3 Specialized Attack Vectors

> Two blind judges find the same superficial errors. Three specialized attackers find what actually hurts.

## Concept

Instead of 2 identical judges with the same prompt ("find problems"), we deploy 3 **highly specialized attackers**, each searching for **only one** type of vulnerability. This is like penetration testing instead of code review.

| Attacker | Focus | Model |
|----------|-------|--------|
| **The Breaker** | Can I crash this function / cause exceptions? | haiku |
| **The Sneak** | Can I inject/steal data? (Injection, Leak, Auth) | haiku |
| **The Scalpel** | What happens under load? (Perf, Race, Resource Leak) | haiku |

## Decision Trees (read → attack → stop)

```
Code present?
  ├─ NO → skip
  └─ YES
       ├─ Phase 1: Launch 3 attackers IN PARALLEL → goto Collect
       ├─ Phase 2: Validate exploit PoCs (Bash/Read) → goto Score
       ├─ Phase 3: Prioritize remediation → REPORT
```

## Phase 1: The 3 Attacks (parallel)

### Attacker A: The Breaker

```
You are THE BREAKER. Your ONLY job: find ways to make this code crash,
throw unhandled exceptions, or return wrong results with edge-case inputs.

Target: {file(s)}

Search for:
- Missing null/undefined checks on EVERY input parameter
- Off-by-one in loops, array access, slicing
- Division by zero possibilities
- Type coercion traps (empty string vs null vs 0 vs false)
- Uncaught promise / error swallowing
- Missing bounds checks on user-supplied indices/lengths

For each finding, provide:
1. EXACT line number
2. SPECIFIC input that triggers it (actual value, not "malicious input")
3. What happens (crash type, wrong output, silent data corruption)
4. Severity: BREAK (crash), CORRUPT (silent wrong), DEGRADE (perf hit)

DO NOT comment on style, naming, architecture, or "best practices".
Only report things that BREAK under specific conditions.
```

### Attacker B: The Sneak

```
You are THE SNEAK. Your ONLY job: find ways to inject, extract, or
bypass security in this code.

Target: {file(s)}

Search for:
- SQL/NoSQL injection (string concat, template literals in queries)
- Path traversal (user input in file paths, URL params)
- Command injection (user input in shell/exec/spawn)
- SSRF (user-controlled URLs in fetch/http requests)
- Auth bypass (missing permission checks, token validation gaps)
- Data leaks (secrets in logs, error messages, stack traces)
- IDOR (direct object reference without ownership check)

For each finding, provide:
1. EXACT line number
2. PAYLOAD: exact string/value that exploits it
3. What an attacker gains (data access, code exec, privilege escalation)
4. Severity: EXPLOIT (active attack possible), LEAK (info disclosure), GAP (missing control)

DO NOT comment on code quality. Only report SECURITY-relevant findings.
```

### Attacker C: The Scalpel

```
You are THE SCALPEL. Your ONLY job: find performance, resource, and
concurrency problems.

Target: {file(s)}

Search for:
- N+1 queries or loops-within-loops over unbounded data
- Memory leaks (accumulating arrays/maps without eviction, global state growth)
- Missing timeouts on ALL I/O (network, DB, file, subprocess)
- Race conditions (shared mutable state, TOCTOU, non-atomic check-then-act)
- Unbounded caching/growth (maps that never shrink, logs without rotation)
- Blocking calls in async paths (sync I/O in request handler)
- Redundant work (same computation repeated, no memoization where obvious)

For each finding, provide:
1. EXACT line number
2. TRIGGER: what usage pattern exposes it (N requests, X data size, Y time)
3. Impact: latency spike, OOM, deadlock, CPU burn
4. Severity: MELTDOWN (fails under load), BLEED (gradual degradation), STALL (blocks)

DO NOT comment on security or correctness. Only report PERFORMANCE issues.
```

## Phase 2: Exploit Validation

Each attacker provides PoCs. You validate **statically** (without execution):

```
PoC Validation (you, no agent):

For EACH finding:
1. Is the PoC REALISTIC? (can the input occur in real operation?)
   → YES = VALID, NO = THEORETICAL (downgrade severity)

2. Is there an EXISTING mitigation?
   → Middleware, validator, type system, framework protection
   → YES = MITIGATED (separate category, do not delete)

3. Can ≥ 2 attackers find the same error?
   → YES = CROSS-VALIDATED (highest priority)
   → NO = SINGLE-PERSPECTIVE (normal priority)
```

## Phase 3: Remediation Report

```
# Triad Review Report — {date}

## Critical (VALID + CROSS-VALIDATED)
| # | Finding | Attacker | PoC | Fix-Scope |
|---|---------|----------|-----|-----------|

## High (VALID + SINGLE-PERSPECTIVE)
| # | Finding | Attacker | PoC | Fix-Scope |

## Mitigated (VALID but existing protection)
| # | Finding | Protection | Residual Risk |

## Theoretical (unrealistic PoC)
| # | Finding | Why unlikely |

## Summary
- Critical: N (fix immediately)
- High: N (prioritize)
- Mitigated: N (monitor)
- Theoretical: N (documented)
- Exploitability: HIGH/MEDIUM/LOW (based on PoC realism)
```

## Terminal States

| State | Condition |
|-------|-----------|
| SECURE | 0 Critical, 0 High, all Theoretical |
| PATCHED | All Critical/High fixed and re-validated |
| ACCEPTED-RISK | Critical/High exist but Joe accepts risk |
| ESCALATED | >5 Critical, system not safe to operate |

## Rules (non-negotiable)

1. **NO** agent comments on style, naming, "best practices"
2. **EVERY** agent provides EXACT PoC with concrete input value
3. **NO** "looks good" without running all 3 attackers
4. **NO** commit before PATCHED or ACCEPTED-RISK
5. Attackers do **NOT** know each other (blind as before)
6. Validation happens **BEFORE** the report is created

## Differences from Judgment Day

| Judgment Day | Triad Review |
|--------------|--------------|
| 2 identical judges | 3 specialized attackers |
| "Find problems" (generic) | "Find CRASHES/EXPLOITS/PERF" (specific) |
| Confirmed/Suspect (vague) | VALID/MITIGATED/THEORETICAL (PoC-based) |
| Synthetic classification | Exploit validation on concrete PoC |
| Fix → re-judge (same prompt) | Fix → re-validation (PoC checks directly) |
