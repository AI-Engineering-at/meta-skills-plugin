---
name: creator
description: >
  Cooperative skill creation. Analyzes session patterns, suggests skills,
  builds them WITH the user. 5-phase process with token optimization pass.
  Trigger: create skill, neuer skill, skill erstellen, was machen wir oft,
  new skill, build skill, meta create
model: sonnet
allowed-tools: [Read, Grep, Glob, Write, Edit, Bash]
user-invocable: true
version: 0.1.0
type: meta
cooperative: true
token-budget: 25000
---

# meta:creator — Cooperative Skill Creation

> Build skills WITH the user, not FOR the user.
> Token efficiency is not a feature — it is the architecture.

## Quick Start

When invoked, run the 5-phase creation process. Each phase asks the user
ONE question at a time. Never skip phases. Never auto-generate without confirmation.

## Phase 1: PRUEFEN (Does this skill need to exist?)

This phase SAVES THE MOST TOKENS by preventing unnecessary skills.

1. Run duplicate check:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/check-duplicates.py" "<user's description>"
   ```

2. Read the JSON output. If matches with score > 0.3:
   Tell the user: "Es gibt schon [name] ([score*100]% aehnlich): [description].
   Optionen: A) Bestehenden Skill erweitern, B) Ersetzen, C) Trotzdem neu erstellen"

3. Ask: "Wie oft wuerdest du den Skill nutzen?"
   - A) Taeglich
   - B) Woechentlich
   - C) Selten (1-2x pro Monat)

   If C + simple task: "Das ist eher eine CLAUDE.md Regel als ein Skill.
   Soll ich stattdessen CLAUDE.md updaten?"
   If C + complex task: "Token-Investment (~25k) lohnt sich erst ab ~5 Nutzungen.
   Bei 2x/Monat dauert das 3 Monate. Trotzdem erstellen?"

4. If all checks pass → Phase 2.

## Phase 2: POSITIONIEREN (Where in the ecosystem?)

Ask these 3 questions, one at a time. Wait for answer before next question.

1. "Welches Problem loest der Skill? (1 Satz)"

2. "Wer nutzt ihn?"
   - A) Nur du persoenlich
   - B) Dein Team (alle Agents)
   - C) Jeder (universell, plattformuebergreifend)

3. "Was ist der primaere Output?"
   - A) Datei (SKILL.md, Config, Code)
   - B) Terminal-Text (Analyse, Report, Status)
   - C) Aktion (Deploy, Update, Sync)
   - D) Zustandsaenderung (Config-Change, DB-Update)

From answers, determine:
- `model`: haiku (mechanical/simple) / sonnet (standard) / opus (architecture only)
- `category`: infrastructure / documentation / automation / meta / analysis / communication
- `platforms`: [claude] (A) / [claude] (B) / [claude, cursor, chatgpt] (C)

## Phase 3: ERARBEITEN (Cooperative — one question at a time)

4. "Was sind die 3-5 Schritte die der Skill ausfuehrt?"
   Listen to the answer. Repeat back: "Verstehe ich richtig: 1. [X], 2. [Y], 3. [Z]?"

5. "Welche Tools braucht er?"
   Show this list — WENIGER ist BESSER (jedes Tool ~200 Token Kontext):
   Read, Write, Edit, Bash, Grep, Glob, WebSearch, WebFetch, Agent
   User picks. If >4 tools: "Brauchst du wirklich alle? Jedes spart 200 Token."

6. "Welche Edge Cases gibt es? Was kann schiefgehen?"
   If user says "keine Ahnung": suggest 2-3 based on the steps.

7. "Wie testest du ob er funktioniert? Was ist das erwartete Ergebnis?"

## Phase 4: SCHREIBEN (The most important phase — invest tokens here)

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
- 4c: Optimization pass — progressive disclosure, model, scripts, tools, triggers
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

## Phase 5: REFLEKTIEREN (Both sides learn)

After user approves:

1. Save SKILL.md: `Write` to `.claude/skills/<name>/SKILL.md`
2. Save references if any: `Write` to `.claude/skills/<name>/references/`
3. Ask: "Was war in dieser Erstellung unklar oder schwierig?"
4. Give ONE concrete tip: "Naechstes Mal wenn du [X] meinst, sag [Y] — das ist praeziser."
5. Summary: "Skill [name] erstellt. Token-Budget: [N]k. Kategorie: [cat]. Naechster Schritt: teste ihn mit [test from Phase 3]."
