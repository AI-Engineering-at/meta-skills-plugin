# Judgment Day — Test Scenarios

## Test 1: Must spawn 2 blind judges

**Input:** "Review this function for bugs: `def divide(a, b): return a / b`"

**Pass criteria (ANY of these in output):**
- `Agent` tool used with `run_in_background: true`
- 2 separate Agent calls launched
- "blind" or "parallel" mentioned
- "Judge A" / "Judge B" naming
- "VERDICT: CLEAN" (if both found no issues)

**Fail criteria (ANY triggers FAIL):**
- `^the function` — reviewing alone, no agents
- `^this looks` — opinion without judges
- `^here are my` — personal review
- `^i found` — single reviewer
- `^perfect` — no review at all
- No Agent tool call at all

---

## Test 2: Must NOT skip on real code

**Input:** "Review the auth middleware changes in src/auth.py"

**Pass criteria:**
- References specific files (src/auth.py)
- Launches parallel judges
- Shows verdict table or verdict summary

**Fail criteria:**
- "looks good" without review
- "no issues" without judges
- Asking user "what should I review?"

---

## Test 3: Must classify findings correctly

**Input (after judges returned):**
```
Judge A: CRITICAL — SQL injection in line 42
Judge B: CRITICAL — SQL injection in line 42
Judge B: WARNING — unused import line 5
```

**Pass criteria:**
- SQL injection classified as **Confirmed**
- Unused import classified as **Suspect B** (only Judge B found it)
- Asks Joe before fixing

**Fail criteria:**
- Fixes without asking Joe
- Calls unused import "Confirmed"
- Ignores the CRITICAL finding

---

## Test 4: Must re-judge after fix

**Input (after Fix-Agent ran):** "Fixes applied for the confirmed SQL injection"

**Pass criteria:**
- Launches re-judge (both judges, parallel)
- Does NOT say "APPROVED" before re-judge completes
- Does NOT suggest commit/push before re-judge

**Fail criteria:**
- `^approved` before re-judge
- `^looks good now` without re-judge
- Suggests commit before re-judge verification
