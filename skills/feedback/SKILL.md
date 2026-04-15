---
name: feedback
version: 1.0.0
type: meta
category: meta
complexity: skill
description: Bidirectional end-of-session review — feedback for BOTH sides (AI and user). Analyzes misunderstandings, gives honest feedback, updates USER_PATTERNS.md.
trigger: feedback-loop, session feedback, was habe ich falsch gemacht, gib mir feedback, session review, retrospektive, wie war die session
model: sonnet
allowed-tools: [Read, Grep, Write, Bash]
user-invocable: true
token-budget: 12000
requires: []
produces: [session-retrospective, user-patterns-update, learnings-update]
cooperative: true
last-audit: 2026-04-14
---

# meta:feedback — Bidirectional Session Review

> **Core Principle:** Feedback is not criticism. Feedback says "X didn't work, try Y next time."
> Criticism says "X was bad." The difference is the solution.

## When to Use

- At the end of a long session (manual: `/feedback`)
- After 3+ misunderstandings — proactively suggest (don't force)
- Before `/compact` — feedback as part of the summary
- When user asks: "What did I do wrong?" or "Give me feedback"

## Step 1: Analyze Session

Walk through the conversation history chronologically. Identify:

1. **Misunderstandings** — Where did the AI understand something differently than the user meant?
2. **Corrections** — Where did the user correct the AI? What was the root cause?
3. **Wasted Time** — Which actions produced no results?
4. **Breakthroughs** — What worked particularly well?
5. **Implicit Assumptions** — What did the user assume without stating it?

## Step 2: Generate Feedback

Create the review using the full template:

```bash
# For the complete review format with table structure:
cat "${CLAUDE_PLUGIN_ROOT}/skills/feedback/references/review-template.md"
```

Short structure: Misunderstandings table | Feedback to AI | Feedback to User | Patterns | Suggested changes.

## Step 3: User Confirmation

Show the review and ask:
> "Does this analysis look correct? Should I apply the suggested changes to USER_PATTERNS.md and LEARNINGS_REGISTRY.md?"

Wait for confirmation. Do NOT apply changes automatically.

## Step 4: Persist (only after confirmation)

For complete persistence guide (paths, edge cases, create-if-missing):

```bash
# Full guide with all paths and edge cases:
cat "${CLAUDE_PLUGIN_ROOT}/skills/feedback/references/persistence-guide.md"
```

Short: Update USER_PATTERNS.md + LEARNINGS_REGISTRY.md, save session report under `docs/reports/`.

## Step 5: Summary

Post a brief summary:
> "Feedback loop complete. [N] misunderstandings documented, [M] new patterns in USER_PATTERNS.md, [K] new learnings. Top tip for you: [tip]. Top tip for me: [tip]."

## Examples

### Example 1: End-of-session review

```
/feedback
# → Analyzes session, identifies misunderstandings
# → Shows: 3 misunderstandings, 2 corrections, 1 breakthrough
# → Asks: "Apply changes to USER_PATTERNS.md?"
# → After confirmation: Updates files, saves report
```

### Example 2: Proactive feedback suggestion

```
# After 3 misunderstandings detected:
"I noticed 3 cases where I misunderstood. Want a feedback review?"
```
