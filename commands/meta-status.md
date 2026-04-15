---
description: "Show meta-skills plugin health — hooks, skills, agents, errors, config"
---

Run the meta-skills health check. Report the following:

## 1. Plugin Registration
```bash
python3 -c "
import json, sys
try:
    with open('$HOME/.claude/plugins/installed_plugins.json') as f:
        d = json.load(f)
    if 'meta-skills' in d.get('plugins', d):
        print('REGISTERED: yes')
        entry = d.get('plugins', d)['meta-skills']
        if isinstance(entry, list): entry = entry[0]
        print(f'  Version: {entry.get(\"version\", \"?\")}')
        print(f'  Path: {entry.get(\"installPath\", \"?\")}')
    else:
        print('REGISTERED: NO — plugin will not load!')
except Exception as e:
    print(f'ERROR reading installed_plugins.json: {e}')
"
```

## 2. Component Counts
```bash
# Skills
echo "Skills: $(find meta-skills/skills -name 'SKILL.md' 2>/dev/null | wc -l) (meta-skills) + $(find .claude/skills -name 'SKILL.md' 2>/dev/null | wc -l) (project)"

# Agents
echo "Agents: $(find meta-skills/agents -name '*.md' 2>/dev/null | wc -l) (meta-skills)"

# Commands
echo "Commands: $(find meta-skills/commands -name '*.md' 2>/dev/null | wc -l)"

# Hooks
echo "Hooks: $(python3 -c "import json; d=json.load(open('meta-skills/hooks/hooks.json')); print(sum(len(v) for v in d['hooks'].values()))" 2>/dev/null || echo '?') hook entries"
```

## 3. Hook Status
```bash
python3 -c "
import json
with open('meta-skills/hooks/hooks.json') as f:
    d = json.load(f)
for event, entries in d['hooks'].items():
    for entry in entries:
        for h in entry.get('hooks', []):
            cmd = h.get('command', '?').split('/')[-1].split('\\\\')[-1]
            print(f'  {event}: {cmd} (timeout={h.get(\"timeout\", \"?\")}s)')
"
```

## 4. Recent Errors
```bash
python3 -c "
from pathlib import Path
import os
log = Path(os.path.expanduser('~/.claude/plugins/data/meta-skills/hook-errors.log'))
if not log.exists():
    print('No errors logged.')
else:
    lines = log.read_text(encoding='utf-8', errors='replace').strip().split('\n')
    # Show last 15 lines
    for line in lines[-15:]:
        print(line)
"
```

## 5. Validation
```bash
python3 meta-skills/scripts/validate.py --errors-only 2>/dev/null || echo "validate.py not found or failed"
```

Present the results as a clean status table. Flag any issues.
