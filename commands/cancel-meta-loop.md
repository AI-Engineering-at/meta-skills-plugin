---
description: "Cancel an active meta-loop"
---

# Cancel Meta-Loop

Check for and remove the meta-loop state file:

```bash
if [ -f ".claude/meta-loop.local.md" ]; then
  iteration=$(grep "iteration:" .claude/meta-loop.local.md | head -1 | awk '{print $2}')
  rm .claude/meta-loop.local.md
  echo "Meta-Loop cancelled after iteration ${iteration:-unknown}."
else
  echo "No active meta-loop found."
fi
```
