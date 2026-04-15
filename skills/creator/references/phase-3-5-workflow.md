# Phase 3-5: Develop, Write, Reflect

## Phase 3: DEVELOP (Cooperative — one question at a time)

4. "What are the 3-5 steps the skill performs?"
   Listen to the answer. Repeat back: "Do I understand correctly: 1. [X], 2. [Y], 3. [Z]?"

5. "Which tools does it need?"
   Show this list — FEWER is BETTER (each tool ~200 token overhead):
   Read, Write, Edit, Bash, Grep, Glob, WebSearch, WebFetch, Agent
   User picks. If >4 tools: "Do you really need all of them? Each saves 200 tokens."

6. "What edge cases exist? What could go wrong?"
   If user says "no idea": suggest 2-3 based on the steps.

7. "How do you test if it works? What is the expected result?"

## Phase 4: WRITE (The most important phase — invest tokens here)

Load the full optimization process:
```bash
cat "${CLAUDE_PLUGIN_ROOT}/skills/creator/references/creation-process.md"
```

Follow the 6-step process (4a-4f):
- 4a: First draft from Phase 1-3 results
- 4b: Token analysis — run eval-skill.py on the draft:
  ```bash
  python "${CLAUDE_PLUGIN_ROOT}/scripts/eval-skill.py" ".claude/skills/<name>/SKILL.md" --baseline
  ```
  This saves the BEFORE measurement automatically.
- 4c: Optimization pass — progressive disclosure, model, tools, triggers
- 4c-Team: If Phase 1 = "Team", load team fields:
  ```bash
  cat "${CLAUDE_PLUGIN_ROOT}/skills/creator/references/team-creation.md"
  ```
- 4d: Quality check — load references/quality-checklist.md, verify every item
- 4e: Cross-platform check — AgentSkills.io conformance:
  ```bash
  python "${CLAUDE_PLUGIN_ROOT}/scripts/validate-agentskills.py" ".claude/skills/<name>/SKILL.md" --strict
  ```
- 4f: User review with measured delta:
  ```bash
  python "${CLAUDE_PLUGIN_ROOT}/scripts/eval-skill.py" ".claude/skills/<name>/SKILL.md" --compare
  ```
  Show: "Draft: Xk tokens → Optimized: Yk tokens (-Z%)"

If user requests changes → back to 4c (not from scratch).

## Phase 5: REFLECT (Both sides learn — self-improving)

After user approves:

1. **Save** the skill/agent:
   - Skill → `Write` to `.claude/skills/<name>/SKILL.md`
   - Agent → `Write` to `.claude/agents/<name>.md`
   - References if any → `.claude/skills/<name>/references/`

2. **Write back to the Learning Layer:**
   - `memory.md`: Update preferences if user showed new preference
   - `corrections.md`: New entry if misunderstanding during this creation
   - `heartbeat-state.md`: Update skill/agent count

3. **Ask:** "What was unclear or difficult during this creation?"
   → Save answer as pattern in memory.md

4. **Tip:** "Next time when you mean [X], say [Y] — it's more precise."

5. **Summary:** "[Type] [name] created. Token budget: [N]k. Model: [model]. Execution: [Main Context/Sub-Agent]. Next step: test it with [test from Phase 3]."

6. **Meta-improvement:** Each creation makes the NEXT one better because:
   - memory.md has more preferences (default model, max tools, language)
   - corrections.md has more anti-patterns (what not to repeat)
   - USER_PATTERNS.md has more communication patterns
   → Phase 0 of the next creation reads all of this automatically
