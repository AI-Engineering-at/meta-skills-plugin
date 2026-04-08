# Token Optimization — The 5 Rules

> Loaded on-demand during Phase 4c.

## R1: Progressive Disclosure

SKILL.md = core logic only (max 150 lines).
Details → references/ (loaded with Read when needed).

Savings: 30-60% per invocation.

## R2: Model Selection

| Task | Model | Relative Cost |
|------|-------|--------------|
| Parse, transform, format | haiku | 1x |
| Judgment, writing, analysis | sonnet | 3x |
| Architecture, complex reasoning | opus | 15x |

## R3: Script Delegation

| Operation | LLM Cost | Script Cost |
|-----------|----------|-------------|
| Parse JSONL files | ~100k tokens | 0 (500 token output) |
| Check duplicates | ~50k tokens | 0 (200 token output) |
| Count lines/tokens | ~5k tokens | 0 (10 token output) |

Rule: Deterministic → script. Judgment → LLM.

## R4: Minimal Toolset

Each tool in allowed-tools adds ~200 tokens context.
6 tools = 1.2k overhead. 2 tools = 400 overhead.

## R5: Trigger Precision

Too broad → loaded unnecessarily → wasted tokens.
Too narrow → not found → user frustrated.

Test: "Would [trigger] EVER mean something else here?"
If yes → add context words.
