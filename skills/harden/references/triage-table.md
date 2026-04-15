# Triage Table — Hardening Step 2

Group findings by treatment:

| Category | Action | Tool |
|----------|--------|------|
| **Auto-fixable** (reworker "auto": True) | Fix immediately | reworker.py --apply |
| **Lint errors** | Run ruff --fix | ruff |
| **Score < 70** | Autoreason with cross-model judges | autoreason-skills.py |
| **Structural Issues** (>150 lines, >4 Tools) | Manual refactoring | Suggestion to user |
| **Corrections >= 3x** | Suggest promotion to rule | promote-corrections.py |
| **Security Findings** | Inform user IMMEDIATELY | verify-security.py |

## Example Triage Output

```
HARDENING SCAN: 15 Findings
  2 CRITICAL (security: hardcoded token in settings.json permissions)
  5 WARNING (3 auto-fixable, 2 need review)
  8 INFO (style, suggestions)

Auto-fixable: 3 (missing token-budget, missing version, lint errors)
Need review: 2 (score < 70, structural issue)
Need user: 2 (security)

Should I fix the 3 auto-fixable issues now?
```
