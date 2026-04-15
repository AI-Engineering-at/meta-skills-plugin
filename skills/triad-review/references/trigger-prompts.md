# Triad Review — References

## Trigger Prompts (für Agent-Launch)

### breaker-trigger.md

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

Output format:
## BREAKER
### B-001: {short title}
- Line: {number}
- Trigger Input: `{exact value}`
- Effect: {crash/corrupt/degrade + description}
- Severity: {BREAK|CORRUPT|DEGRADE}
```

### sneak-trigger.md

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

Output format:
## SNEAK
### S-001: {short title}
- Line: {number}
- Payload: `{exact exploit string}`
- Gain: {what attacker achieves}
- Severity: {EXPLOIT|LEAK|GAP}
```

### scalpel-trigger.md

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

Output format:
## SCALPEL
### P-001: {short title}
- Line: {number}
- Trigger Pattern: {usage scenario that exposes it}
- Impact: {latency/OOM/deadlock/CPU}
- Severity: {MELTDOWN|BLEED|STALL}
```

## Synthese-Template

```
# Triad Synthesis — {date}

## Cross-Validated (≥2 Angreifer, höchste Priorität)
| ID | Finding | Angreifer | Severity | PoC validiert? |
|----|---------|-----------|----------|----------------|

## Single-Validated (1 Angreifer, PoC valid)
| ID | Finding | Angreifer | Severity | PoC validiert? |
|----|---------|-----------|----------|----------------|

## Mitigated (PoC valid, aber Schutz vorhanden)
| ID | Finding | Schutzmechanismus | Restrisiko |
|----|---------|-------------------|------------|

## Theoretical (PoC unrealistisch)
| ID | Finding | Warum unrealistisch |
|----|---------|---------------------|

## Entscheidungs-Matrix
| Bedingung | Aktion |
|-----------|--------|
| ≥1 Cross-Validated + BREAK/EXPLOIT/MELTDOWN | **CRITICAL** → sofort fixen |
| ≥1 Single-Validated + BREAK/EXPLOIT/MELTDOWN | **HIGH** → prioritär fixen |
| Nur MITIGATED | **ACCEPTABLE** → dokumentieren |
| Nur THEORETICAL | **INFO** → ignorieren |

## Verdict
{SECURE | PATCH NEEDED | ACCEPTED RISK | ESCALATE}
```

## Re-Validierung (nach Fix)

Nach jedem Fix:

1. **NICHT** die Angreifer neu starten
2. **SELBER** prüfen: Funktioniert der originale PoC noch?
   - PoC Input durch den gefixten Code jagen (mental/statisch)
   - Falls PoC immer noch funktioniert → Fix unvollständig
   - Falls PoC ins Leere läuft → Finding resolved
3. **NUR** wenn PoC nicht mehr funktioniert → Angreifer bestätigen lassen
   (spart Tokens, denn statische Validierung ist kostenlos)

```
# Re-Validation Report

| Finding ID | Original PoC | Nach Fix | Status |
|------------|-------------|----------|--------|
| B-001 | `input=null` | Crashed nicht mehr | ✅ RESOLVED |
| S-003 | `' OR 1=1--` | Parametrized query | ✅ RESOLVED |
| P-002 | 10k items loop | Immer noch O(N²) | ❌ STILL VULNERABLE |
```
