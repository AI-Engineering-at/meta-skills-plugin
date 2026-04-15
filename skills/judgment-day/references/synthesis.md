# Synthesis — Verdict Table + Status Logic

## After Both Judges Complete

Compare findings. Build verdict table:

```
## Judgment Day — {target} — Round {N}

| # | Finding | Judge A | Judge B | Severity | Status |
|---|---------|---------|---------|----------|--------|
| 1 | ... | found | found | CRITICAL | Confirmed |
| 2 | ... | found | - | WARNING | Suspect A |
| 3 | ... | - | found | WARNING | Suspect B |
| 4 | ... | found | NOT found | WARNING | Conflict |
```

## Status Classification

| Pattern | Status | Action |
|---------|--------|--------|
| Both say CRITICAL | **Confirmed** | Must fix |
| Both say WARNING | **Confirmed** | Must fix |
| Only Judge A finds it | **Suspect A** | Joe decides |
| Only Judge B finds it | **Suspect B** | Joe decides |
| Judge A says issue, Judge B says clean | **Conflict** | Joe decides |
| Both say CLEAN | **APPROVED** | Done |

## WARNING Severity Filter

Before showing verdict table, classify each WARNING:

- **WARNING (real)**: A normal user could trigger this → include in table
- **WARNING (theoretical)**: Requires contrived edge case → demote to INFO, no fix needed

INFO items are reported but never trigger fixes or re-judges.

## Joe's Decision Point

After showing verdict table, ask Joe:

> "Fix {N} confirmed issues? [yes / escalate / selective]"

- **yes** → proceed to Fix-Agent (see `references/fix-rejudge.md`)
- **selective** → Joe picks which to fix, proceed with subset
- **escalate** → mark ESCALATED, document remaining issues
