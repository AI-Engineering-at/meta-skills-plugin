---
name: systematic-debugging
description: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes. 4-phase process: Root Cause, Pattern Analysis, Hypothesis, Implementation. NO FIXES WITHOUT ROOT CAUSE.
trigger: bug, test failure, error, debugging, fix broken, warum geht nicht
model: sonnet
allowed-tools: [Read, Grep, Glob, Bash]
user-invocable: true
complexity: agent
last-audit: 2026-04-14
version: 1.0.0
token-budget: 3000
---

# Systematic Debugging

> **Iron Law:** NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST

## When to Use

ANY bug, test failure, unexpected behavior. ESPECIALLY under time pressure, after failed fixes, or "just one quick fix" thinking.

## The Four Phases

Complete each before proceeding to the next.

### Phase 1: Root Cause Investigation

**BEFORE any fix:**

1. **Read Errors Carefully** — Complete stack traces, line numbers, file paths, error codes.
2. **Reproduce Consistently** — Reliably trigger issue. Not reproducible? Gather more data, don't guess.
3. **Check Recent Changes** — Git diff, recent commits, new deps, config changes, env differences.
4. **Gather Evidence (Multi-Component)** — Instrument at EACH boundary. Log what enters/exits. Verify config propagation.
5. **Trace Data Flow** — Where does bad value originate? Trace up to source. Fix at source, not symptom.

### Phase 2: Pattern Analysis

Find working examples in same codebase. Compare against reference COMPLETELY. List every difference. Understand dependencies.

### Phase 3: Hypothesis and Testing

Single hypothesis: "I think X is root cause because Y". Test minimally — ONE variable at a time. When you don't know: say "I don't understand X".

### Phase 4: Implementation

Use `meta-skills:tdd` for failing tests. ONE change at a time. Verify fix. After 3 failed attempts → STOP. Question architecture. Discuss with Joe.

## Red Flags — STOP and Return to Phase 1

"Quick fix for now", "Just try changing X", "Add multiple changes", "Skip the test", "I don't fully understand but this might work", "One more fix" (after 2+ failures).

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple" | Simple issues have root causes too |
| "Emergency, no time" | Systematic is FASTER than guess-and-check |
| "Just try this first" | First fix sets the pattern. Do it right. |
| "One more fix" (after 2+) | 3+ failures = architectural problem |
