# Scanner Prompts — doc-updater Step 3

## doc-scanner-core (Tier 1)

Scan core documentation files for stale entries.

**Files:** CLAUDE.md, README.md, INDEX.md, VERSION-MATRIX.md, docs/*.md

**Checks:**
- Version matches pyproject.toml
- Plugin/tool count matches actual inventory
- Test file/function counts accurate
- Role descriptions current

**Output:** JSON array of `{file, line, field, expected, actual, severity}`

## doc-scanner-infra (Tier 2)

Scan infrastructure documentation.

**Files:** docs/03-infrastructure.md, docs/*-setup.md, node configs

**Checks:**
- Deploy paths correct (/opt/phantom-ai/)
- Node topology current
- Leader/Reachable patterns accurate
- Plugin inventory complete

**Output:** Same format as core scanner.

## doc-scanner-agents (Tier 3)

Scan agent/team documentation.

**Files:** agents/*.md, persona_prompt.md, voice-gateway/agent.md

**Checks:**
- Agent roles/current matches code
- Team-worker definitions accurate
- persona_prompt.md factual infra only

**Output:** Same format as core scanner.
