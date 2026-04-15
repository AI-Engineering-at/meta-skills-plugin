# Session QA Report — 2026-04-13

## Syntax Check

### meta-skills (33 Python files)
- **33/33 files OK** — all hooks/*.py and scripts/*.py pass `python -m py_compile`
- hooks.json: **VALID**
- plugin.json (v3.0.0): **VALID**

### cli-council (3 Python files)
- **3/3 files OK** — all scripts/*.py pass `python -m py_compile`
- hooks.json: **VALID**
- plugin.json (v1.0.0): **VALID**

### System Config
- settings.json: **VALID**
- Failures: **None**

## Error Handling Audit

### Hooks (must never crash)

| File | stdin-parse | exit-0 | timeout | logging | race-cond | Status |
|------|-----------|--------|---------|---------|-----------|--------|
| approach-guard.py | try/except + empty fallback | sys.exit(0) at all paths | N/A (no subprocess) | Silent (pass on errors) | State file per session_id (low risk) | OK |
| scope-tracker.py | try/except + empty fallback | sys.exit(0) at all paths | N/A (no subprocess) | Silent (pass on errors) | State file per session_id (low risk) | OK |
| exploration-first.py | try/except + empty fallback | sys.exit(0) at all paths | N/A (no subprocess) | Silent (pass on errors) | State file per session_id (low risk) | OK |
| quality-gate.py | try/except + empty fallback | sys.exit(0) at all paths | N/A (no subprocess) | Silent (pass on errors) | State file per session_id (low risk) | OK |
| meta-loop-stop.py | try/except + empty fallback | sys.exit(0) at all paths | subprocess timeout=30s | Silent (pass on errors) | State file single-writer (OK) | OK |
| correction-detect.py | try/except + empty fallback | sys.exit(0) at all paths | N/A (no subprocess) | log_error via lib/services | Single state file (low risk) | OK |
| session-stop.py | try/except + empty fallback | sys.exit(0) at all paths | HTTP timeout=4s, subprocess timeout=5s/15s | log_error via lib/services | Audit JSONL append (safe) | OK |
| session-init.py | try/except + empty fallback | sys.exit(0) at all paths | HTTP timeout=4s, subprocess timeout=5s | log_error via lib/services | State file per session_id (OK) | OK |
| token-audit.py | try/except + empty fallback | sys.exit(0) at all paths | N/A (JSONL append only) | Silent (pass on errors) | JSONL append-only (safe for parallel) | OK |

### Scripts

| File | error-handling | timeout | edge-cases | Status |
|------|---------------|---------|------------|--------|
| setup-meta-loop.py | argparse + clear error msgs | N/A (no subprocess) | Checks for ralph-loop/meta-loop conflict | OK |
| quality-snapshot.py | try/except around subprocess | timeout=30s (eval), 15s (validate) | Handles empty results, missing baseline | OK |
| build-skill-registry.py | try/except per file read | N/A (file I/O only) | Handles missing dirs, empty frontmatter | OK |
| autoreason-skills.py | try/except per CLI call | subprocess timeout=120s per CLI | Handles missing CLIs, empty responses, convergence | OK |
| detect-clis.py (cli-council) | try/except per CLI check | subprocess timeout=10s | Handles FileNotFoundError, timeout, OSError | OK |
| dispatch.py (cli-council) | try/except per CLI call | subprocess timeout=180s | Handles failure, parallel dispatch, dry-run | OK |
| synthesize.py (cli-council) | try/except in JSON loading | N/A (file processing only) | Handles missing files, empty results | OK |

## Specific Issue Analysis

### quality-gate.py: detect_failure() False Positives
- **FINDING [WARNING]**: The `\berror\b` pattern (line 54, case-insensitive) WILL match "error" in code comments, documentation output, and help text (e.g., "error handling", "no errors found in documentation"). However, the false-positive exclusion list (lines 62-67) catches the common safe cases: "0 errors", "no errors found", "All checks passed", "passed ... 0 failed". The check for "Error:" (capitalized with colon) is more precise. **Risk: Medium** — could produce occasional false positives on verbose tool output that contains the word "error" in non-failure contexts. Mitigated by the false-positive filter running FIRST (line 91-93), which returns False before any indicator is checked.

### meta-loop-stop.py: Missing Gate Command
- **FINDING [INFO]**: If a gate command does not exist (e.g., `ruff` not installed), `subprocess.run` with `shell=True` will return a non-zero exit code, causing the gate to report FAIL. This is **correct behavior** — a missing tool should fail the gate. The `subprocess.TimeoutExpired` exception is caught (line 141). If `CLAUDE_PLUGIN_ROOT` is not set, the eval gate falls back to `Path(__file__).parent.parent` which is sensible.

### autoreason-skills.py: CLI Hang/Timeout Handling
- **FINDING [OK]**: Each CLI call has `timeout=120` (line 294-296). `subprocess.TimeoutExpired` is caught (line 303-304) and returns empty string, which terminates the current pass. The `detect_available_clis()` function (line 243-268) also has `timeout=5` for version checks. **No hang risk**.

### session-stop.py: Import of subprocess
- **FINDING [INFO]**: `subprocess` is imported inside functions at lines 112 (`import subprocess as _sp`) and 132 (`import subprocess as _sp_verify`), not at top level. This is intentional — saves ~2ms on subsequent prompts where session-stop is not the code path. The aliased import pattern (`as _sp`) is unusual but functional. No issue.

### quality-gate.py: False Positive on FAILURE_INDICATORS order
- **FINDING [WARNING]**: The false-positive check (line 91-93) returns `False` (meaning "no failure") if ANY false-positive pattern matches. This means if output contains both "0 errors" AND a real "FAILED" on different lines, the false-positive check wins and the real failure is MISSED. The false-positive patterns should only cancel their specific failure indicator, not all of them. **Impact: Could miss real failures if output also contains success messages for other tools in the same command.**

### Race Conditions Assessment
- All hooks use per-session-id state files (e.g., `.approach-guard-{session_id}.json`), which prevents cross-session corruption.
- `token-audit.py` uses append-only JSONL — safe for concurrent writes on the same line.
- `correction-detect.py` uses a single `.escalation-state.json` keyed by session_id inside the file — safe as long as one session = one process.
- `session-init.py` writes state file atomically before doing work (line 55) — correct guard against re-entry.
- **No critical race conditions identified.**

## Eval Scores

### New/Changed Skills from this Session

| Skill | Score | Issues |
|-------|-------|--------|
| systematic-debugging | 90/100 | None — good |
| tdd | 90/100 | None — good |
| git-worktrees | 90/100 | None — good |
| verify | 90/100 | None — good |
| refactor-loop | 83/100 | Missing some optional fields |
| dispatch | 83/100 | Missing some optional fields |
| judgment-day | 83/100 | Declared complexity=agent but scored as skill |
| init | not separately scored | Extended with SDD |

### Overall Portfolio

| Metric | Value |
|--------|-------|
| Total evaluated | 70 (42 skills + 28 agents) |
| Average score | 90.5/100 |
| Below 70 | 0 |
| Above 90 | 44 |

### Eval Discovery Bug
- **FINDING [WARNING]**: `eval.py --all` returns 0 results when run from `meta-skills/` directory. The `find_skills()` function (line 328-336) searches `cwd/.claude/skills/` and `cwd/meta-skills/skills/` — but when CWD is already `meta-skills/`, neither path exists. Must be run from `phantom-ai/` root. The `quality-snapshot.py` script sets `cwd=str(PLUGIN_ROOT)` (line 33) which is `meta-skills/`, causing it to also find 0 items. This means quality-snapshot.py always reports 0 scored items.

## Issues Found

1. **[WARNING]** quality-gate.py `detect_failure()` false-positive logic is order-dependent: any false-positive match cancels ALL failure detection, not just the specific indicator it contradicts. Could miss real test failures if output also contains "0 errors" from a different tool.

2. **[WARNING]** quality-snapshot.py always reports 0 scored items because it runs eval.py with CWD=PLUGIN_ROOT (meta-skills/) instead of phantom-ai/. The snapshot saved to `oversight/snapshots/snapshot-2026-04-13.json` shows `avg_score: 0, total_items: 0`.

3. **[WARNING]** eval.py `find_skills(cwd)` does not search `cwd/skills/` (only `cwd/.claude/skills/` and `cwd/meta-skills/skills/`), making it impossible to get results when run from within the meta-skills directory itself.

4. **[INFO]** session-stop.py imports `subprocess` inside functions with aliased names (`_sp`, `_sp_verify`). Functional but unconventional. Could cause confusion if extended.

5. **[INFO]** meta-loop-stop.py YAML parser (lines 50-94) is custom and fragile. Does not handle quoted strings with colons, multi-line values, or nested objects beyond simple `{key: val}` format. Acceptable for the controlled frontmatter format used, but will break on edge cases.

6. **[INFO]** autoreason-skills.py line 575: `'pass_num' in dir()` is a fragile way to check if the loop ran. If max_passes=0, `pass_num` is undefined. Should use a separate counter variable.

7. **[INFO]** settings.json contains hardcoded API keys and tokens in the `permissions.allow` list (lines 34-39, 69, 72, etc.). These are permission patterns but still expose credential strings.

8. **[INFO]** cli-council `dispatch.py` `autoreason()` function at line 412: `"pass_num" in dir()` has same fragile pattern as autoreason-skills.py.

## Recommendations

1. **Fix quality-snapshot.py CWD**: Change `cwd=str(PLUGIN_ROOT)` to `cwd=str(PLUGIN_ROOT.parent)` so eval.py can find skills in the `meta-skills/skills/` path relative to phantom-ai root.

2. **Fix detect_failure() in quality-gate.py**: Make false-positive checks more targeted — only suppress the specific failure indicator that the false positive contradicts, not all indicators.

3. **Fix eval.py discovery**: Add `cwd / "skills"` to `find_skills()` search paths so it works when run from within meta-skills.

4. **Replace `'pass_num' in dir()` pattern**: Use `pass_num = 0` before the loop and check `pass_num > 0` after.

5. **Audit settings.json permissions**: The allow list contains literal API keys and tokens. While these are permission matchers, they expose credential strings in a file that could be committed to git.
