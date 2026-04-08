# Phase 4: Writing — The 6-Step Optimization Process

> Loaded on-demand during Phase 4 of meta:creator.
> Total budget: ~12k tokens. Each step builds on the previous.

## Step 4a: First Draft (~3k tokens)

Generate SKILL.md from Phase 1-3 results. Include:
- YAML frontmatter with ALL meta: fields (see frontmatter-schema.md)
- Full instruction body with all steps from Phase 3
- Edge cases from Phase 3 question 6

Write it COMPLETE first. Do NOT optimize yet.

## Step 4b: Token Analysis (~2k tokens)

Estimate tokens in the draft:
- Each word = ~1.3 tokens (English) / ~1.5 tokens (German)
- Each code line = ~10-15 tokens
- YAML frontmatter = ~3-5 tokens per field

Identify token-heavy sections:
- Explanations that repeat frontmatter info
- Examples that belong in references/ instead
- Tool descriptions (Claude already knows its tools)
- Generic advice ("be careful", "handle errors") — delete these

Set `token-budget` in frontmatter.

## Step 4c: Optimization Pass (~3k tokens)

Apply rules in order (see token-optimization.md for details):

R1: Progressive Disclosure — move detail sections to references/
R2: Model Selection — cheapest model that works (haiku > sonnet > opus)
R3: Script Delegation — deterministic tasks as Python scripts, not LLM prompts
R4: Minimal Toolset — remove unused tools from allowed-tools
R5: Trigger Precision — precise but not too narrow

## Step 4d: Quality Check (~2k tokens)

Load and verify: `cat "${CLAUDE_PLUGIN_ROOT}/skills/creator/references/quality-checklist.md"`

Every item must pass. If not → fix before continuing.

## Step 4e: Cross-Platform Check (~2k tokens)

Verify AgentSkills.io conformance:
- [ ] name: active verb format (deploy-service, not service-deployment)
- [ ] description: clear, trigger words at end, max 3 lines
- [ ] No hardcoded absolute paths
- [ ] Scripts use portable shebangs (#!/usr/bin/env python3)
- [ ] No platform-specific features unless declared in `platforms` field

If user chose platforms: [claude, cursor, chatgpt] in Phase 2:
- Note: ChatGPT export would need manifest.json (not generated in v0.1)
- Note: Copilot needs API endpoint (document this limitation)

## Step 4f: User Review (~3k tokens)

Present the finished skill WITH metrics:

"Ergebnis der Token-Optimierung:
- Erst-Entwurf: [X]k Token
- Nach Optimierung: [Y]k Token (-[Z]%)
- Progressive Disclosure: [N] Abschnitte in references/ verschoben
- Modell: [model] — gewaehlt weil [reason]
- Tools: [N] (minimal noetig)
- AgentSkills.io-konform: Ja/Nein
- Trigger-Kollision: Keine / Kollision mit [skill]"

Wait for user approval. Changes → back to 4c.
