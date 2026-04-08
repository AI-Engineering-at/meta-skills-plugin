# Modus 3: Audit — Full Process

> Loaded on-demand when /meta-skills:audit is invoked.

## Step 1: Run Inventory

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/audit-skills.py"
```

Read the JSON summary. Present to the user:
- Total skills found (by source: local/user/plugin)
- By recommendation: keep/optimize/update/archive
- Top 5 skills needing attention

## Step 2: Review Each Flagged Skill

For each skill with recommendation != "keep", present:
- Name, source, score
- Issues found
- Recommended action with explanation

Ask the user for EACH skill:
- A) Archive (move to _archive/, remove from index)
- B) Optimize (start meta:creator Phase 4 rewrite)
- C) Upgrade (create local optimized copy of plugin skill)
- D) Merge (combine with another overlapping skill)
- E) Keep (update last-audit date only)
- F) Skip (decide later)

## Step 3: Execute Actions

Only after user confirms each action:
- Archive: move SKILL.md to _archive/skills/<name>/
- Optimize: invoke meta:creator in rewrite mode (Phase 4 only)
- Upgrade: copy plugin skill to local, run Phase 4 optimization
- Merge: create new combined skill, archive originals
- Keep: update last-audit in frontmatter

## Step 4: Update Catalog

After all actions:
- Regenerate skill-catalog.json
- Present summary: "N skills audited. X archived, Y optimized, Z kept."
