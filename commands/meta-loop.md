---
description: "Start objective quality loop — iterates until ALL gates pass (pytest, ruff, eval)"
argument-hint: '"TASK PROMPT" --gates ruff,pytest[,eval:80] [--max-iterations N]'
---

# Meta-Loop — Objective Quality Iteration

Start an iterative loop that blocks session exit until ALL quality gates pass.

## Setup

Run the setup script with your task and gates:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup-meta-loop.py" $ARGUMENTS
```

## How It Works

1. You work on the task as normal
2. When you try to end the session, the meta-loop-stop hook fires
3. It runs each gate command (pytest, ruff, eval.py)
4. ALL gates must pass (exit 0) for the session to end
5. If any gate fails: exit is blocked, you see the failures, iteration increments
6. You fix the issues and try again

## Available Gates

| Gate | What it runs | Pass condition |
|------|-------------|----------------|
| `ruff` | `ruff check .` | exit 0 |
| `pytest` | `pytest -x -q` | exit 0 |
| `eslint` | `npm run lint` | exit 0 |
| `build` | `npm run build` | exit 0 |
| `eval` | `eval.py --all` | avg score >= 70 |
| `eval:85` | `eval.py --all` | avg score >= 85 |
| `custom:CMD` | your command | exit 0 |

## Examples

```
/meta-loop "Fix all ruff lint errors in voice-gateway/" --gates ruff --max 5
/meta-loop "Get all skill scores above 80" --gates eval:80 --max 10
/meta-loop "Fix failing tests and lint" --gates ruff,pytest --max 8
```

## Cancel

Use `/cancel-meta-loop` to stop the loop at any time.
