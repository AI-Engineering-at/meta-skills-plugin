# meta-skills — AI Workflow Engine

> Cooperative skill creation. Session analysis. Token optimization. Skill routing.
> AgentSkills.io compatible (Claude Code, Cursor, ChatGPT, Gemini CLI).

## Install

```bash
claude plugins add ./meta-skills
```

## Skills

| Skill | Command | Description |
|-------|---------|-------------|
| meta:creator | `/meta-skills:create` | Cooperative skill creation (5-phase process) |
| meta:feedback | `/meta-skills:feedback` | Bidirectional end-of-session review |
| meta:design | `/meta-skills:design` | Visual DESIGN.md generator |

## Modes

| Mode | What it does |
|------|-------------|
| **Creation** | Build skills WITH the user — 5-phase cooperative process with token optimization |
| **Discovery** | Analyze session history, find repeated patterns, suggest new skills |
| **Audit** | Score all existing skills, recommend: archive / optimize / upgrade / merge / keep |

## Token Efficiency

Every skill created with meta:creator is optimized:
- Progressive Disclosure (core in SKILL.md, details in references/)
- Minimal toolset (each tool costs ~200 tokens of context)
- Model selection (haiku > sonnet > opus — cheapest that works)
- Script delegation (deterministic tasks run as Python, not LLM)

## Architecture

```
meta-skills/
  .claude-plugin/plugin.json     # Plugin manifest
  skills/
    creator/SKILL.md             # 5-phase cooperative creation
    creator/references/          # Progressive Disclosure (4 files)
    feedback/SKILL.md            # Bidirectional session review
    feedback/references/         # Templates + persistence guide
    design/SKILL.md              # Visual DESIGN.md generator
  commands/                      # /meta-skills:create, :feedback, :discover, :audit, :design
  agents/session-analyst.md      # Haiku agent for pattern detection
  hooks/hooks.json               # Stop hook for session metrics
  scripts/
    check-duplicates.py          # TF-IDF skill overlap detection
    analyze-sessions.py          # JSONL session history parser
    detect-patterns.py           # Heuristic pattern + sequence detection
    audit-skills.py              # Skill scoring + catalog generation
    validate-agentskills.py      # Cross-platform conformance checker
```

## Philosophy

- **Cooperative, not generative** — Build skills WITH the user, not FOR the user
- **Token efficiency is architecture** — Scripts do pre-work, LLM gets only results
- **Progressive Disclosure** — SKILL.md has core only, details loaded on demand
- **The best skill is the one you don't need** — Phase 1 rejects >30% of proposals

## Future (v2.0+)

- **meta:flow** — Workflow composition from skill sequences
- **meta:system** — Adaptive self-optimization with reflection loops

## License

MIT — no viral copyleft (unlike skillfish AGPL-3.0). Commercial use allowed.

## Author

[AI Engineering](https://ai-engineering.at)
