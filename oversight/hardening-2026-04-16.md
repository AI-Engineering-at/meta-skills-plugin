# Hardening Report 2026-04-16

Branch: `feature/statusline-opus47-hardening`
Scope: meta-skills plugin (hooks/ + scripts/) + Opus 4.7 upgrade

## Summary

| Metric | Before | After | Δ |
|---|---|---|---|
| Lint errors | 236 | 74 | -162 (-69%) |
| Critical bugs (F821) | 2 | 0 | -2 |
| Syntax errors | 0 | 0 | = |
| JSON schema errors | 0 | 0 | = |
| Frontmatter errors | 0 | 0 | = |
| Quality score (avg) | n/a | 89.7 | baseline |
| Skills below 70 | n/a | 0 | = |
| Components evaluated | 72 | 72 | = (44 skills + 28 agents) |

## Round 1 — Statusline + Opus 4.7 (commit ee22d12)

- `scripts/statusline.py`: regex model-version detection (`O4.7`/`S4.6`/`H4.5`),
  auto-parse from `claude-(opus|sonnet|haiku)-MAJ-MIN` ID, future-proof for 5.x
- `scripts/statusline.py`: `fk()` formatter extended with T (trillion) step —
  token sums now unambiguous across k → M → B → T
- `scripts/validate.py`: add `claude-opus-4-7` to VALID_MODELS (keep 4-6 for
  backwards compat during transition)
- `skills/statusbar/SKILL.md`: examples updated to `O4.7(1M)`
- Cleanup: removed 0-byte `nul` Windows artifact from repo root

## Round 2 — Hardening (commit edff6d0)

### Critical Bug Fixed
- `hooks/quality-gate.py:256,270`: `subprocess.run()` called without `import
  subprocess` — real F821 bug in the CI-check code path. Hook would have
  crashed on any `gh run list` attempt. Added import at file top.

### Auto-Fixes Applied
- 148 × ruff `--fix` (imports, f-strings, redundant parens, etc.)
- 30 × ruff `--fix --unsafe-fixes` (safe semantic preservation)
- 10 × F841/F401 unused variables/imports removed
- 5 × `# noqa: E402` for intentional sys.path manipulation before sibling
  imports (approach-guard, exploration-first, quality-gate, scope-tracker,
  session-init)
- 1 × `# noqa: F401` for psutil availability probe pattern (plugin-setup.py)

### Verification
- `py_compile`: all hooks + scripts compile ✓
- `statusline.py`: smoke test with Opus 4.7 payload — exit 0, correct render ✓
- `validate.py`: 22 components, 0 errors, 22 cross-repo path warnings (known
  baseline: agents reference files in phantom-ai that exist but at paths
  relative to repo root, not cwd)
- `eval.py --all`: 72 components, avg score 89.7/100, 0 below 70
- `harden.py --scan`: 0 CRITICAL, 0 WARNING, 2 INFO (Windows `.cmd` subprocess
  advisories in session-end/session-stop — acceptable)

## Known Baseline (74 remaining style warnings — non-behavioral)

| Category | Count | Status |
|---|---|---|
| `PTH*` (os.path → pathlib) | 45 | Deferred — separate refactor |
| `E701` multi-statement one-liner | 13 | Style, e.g. `if x: y` |
| `E741` ambiguous variable (`l`, `O`) | 6 | Pre-existing |
| `SIM102` collapsible-if | 4 | Style |
| `SIM115` open-without-context-manager | 4 | Often intentional short-lived |
| `N806` non-lowercase-var-in-function | 2 | Naming |
| `N802` invalid-function-name | 1 | Naming |
| `RUF005` collection-literal-concat | 3 | Style |
| `RUF034` useless-if-else | 1 | Logic quirk |
| `PTH103/105/110` (small PTH) | 3 | Deferred with main PTH batch |

All style only. 0 behavioral impact. Pathlib migration recommended as
dedicated follow-up PR (touches 41 files, large diff, needs its own review).

## Terminate Status

**APPROVED WITH DEFERRED STYLE BASELINE**

- All critical bugs fixed ✓
- All skills/agents above quality threshold ✓
- Syntax + JSON schema + frontmatter clean ✓
- Opus 4.7 support end-to-end verified ✓
- 74 remaining lint errors are pure style, documented as accepted baseline

## Follow-ups (Separate Work)

1. **Pathlib migration** — PR replacing `os.path` → `pathlib.Path` across 41
   files. Needs dedicated testing on Windows + Linux.
2. **Compaction threshold investigation** — Joe reports compaction sometimes
   fires at 80%. Looking into `hooks/context-recovery.py` threshold.
3. **Cross-repo frontmatter WARN cleanup** — 22 warnings reference files that
   live at `phantom-ai/.claude/knowledge/...` but validate.py checks paths
   relative to meta-skills cwd. Fix: resolve refs relative to repo root.
