---
name: tdd
description: Test-Driven Development. Use when implementing any feature or bugfix, before writing implementation code. Red-Green-Refactor cycle. NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.
trigger: test first, tdd, test driven, write tests, failing test
model: sonnet
allowed-tools: [Read, Edit, Bash, Grep]
user-invocable: true
complexity: skill
last-audit: 2026-04-14
version: 1.0.0
token-budget: 3000
type: meta
category: quality
requires: [verify]
produces: [quality-report]
cooperative: false
---

# Test-Driven Development (TDD)

## Overview

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over. No exceptions.

## When to Use

**Always:** New features, Bug fixes, Refactoring, Behavior changes

**Exceptions (ask Joe):** Throwaway prototypes, Generated code, Configuration files

## Red-Green-Refactor

### RED -- Write Failing Test

Write one minimal test showing what should happen.

**Requirements:**
- One behavior per test
- Clear name describing behavior
- Real code (no mocks unless unavoidable)

**Good:**
```typescript
test('retries failed operations 3 times', async () => {
  let attempts = 0;
  const operation = () => {
    attempts++;
    if (attempts < 3) throw new Error('fail');
    return 'success';
  };
  const result = await retryOperation(operation);
  expect(result).toBe('success');
  expect(attempts).toBe(3);
});
```

### Verify RED -- Watch It Fail (MANDATORY)

```bash
npm test path/to/test.test.ts   # or pytest, cargo test, etc.
```

Confirm: Test fails (not errors), failure message is expected, fails because feature missing.

### GREEN -- Minimal Code

Write simplest code to pass the test. Don't add features beyond the test.

### Verify GREEN (MANDATORY)

Confirm: Test passes, other tests still pass, output pristine.

### REFACTOR -- Clean Up

After green only: Remove duplication, improve names, extract helpers.
Keep tests green. Don't add behavior.

### Repeat

Next failing test for next feature.

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Deleting X hours is wasteful" | Sunk cost fallacy. Keeping unverified code is debt. |
| "TDD will slow me down" | TDD faster than debugging. |
| "Already manually tested" | Ad-hoc != systematic. No record, can't re-run. |
| "Need to explore first" | Fine. Throw away exploration, start with TDD. |

## Verification Checklist

Before marking work complete:
- [ ] Every new function/method has a test
- [ ] Watched each test fail before implementing
- [ ] Each test failed for expected reason
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass
- [ ] Output pristine (no errors, warnings)
- [ ] Edge cases and errors covered

## Project-Specific Test Commands

| Stack | Command |
|-------|---------|
| Python (generic) | `VOICE_GATEWAY_URL=${API_URL:-http://localhost:8085} pytest tests/ -v` |
| Python (lint) | `ruff check . && ruff format --check .` |
| TypeScript/Electron | `npm test` then `npm run lint` |
| Dashboard | Vitest (unit) + Playwright (E2E) |

## Examples

### Example 1: Implementing a retry function

```typescript
// RED: Write failing test first
test('retries failed operations 3 times', async () => {
  let attempts = 0;
  const operation = () => {
    attempts++;
    if (attempts < 3) throw new Error('fail');
    return 'success';
  };
  const result = await retryOperation(operation);
  expect(result).toBe('success');
  expect(attempts).toBe(3);
});

// Verify RED: npm test → FAILS (retryOperation not defined)

// GREEN: Write minimal code
async function retryOperation(fn) {
  for (let i = 0; i < 3; i++) {
    try { return await fn(); } catch (e) {}
  }
}

// Verify GREEN: npm test → PASSES

// REFACTOR: Extract retry counter, improve names
```

### Example 2: Bugfix with TDD

```
1. Write test reproducing the bug → FAILS
2. Fix the code → test PASSES
3. Run full suite → all PASSES
4. Refactor if needed
```
