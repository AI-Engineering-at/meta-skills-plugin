---
description: "Automated hardening loop — SCAN all code, TRIAGE issues, FIX auto-fixable, VERIFY, REPORT"
argument-hint: "[--scan|--auto|--full|--report] — scan: check only. auto: auto-fix. full: + harness-verify. report: report only."
---

# Meta-Harden — System-Wide Quality Hardening

Start the hardening loop for the entire meta-skills + cli-council system.

Follow the harden skill (skills/harden/SKILL.md):
1. **SCAN** — Run all deterministic checks (eval, validate, lint, reworker, promote-corrections)
2. **TRIAGE** — Group findings by severity + treatment
3. **FIX** — Auto-fixable immediately, cross-model review for complex issues
4. **VERIFY** — Re-run all checks, compare before/after
5. **REPORT** — Metrics snapshot + hardening report
6. **LOOP** — Repeat until all gates green or max 3 iterations

Mode: $ARGUMENTS
