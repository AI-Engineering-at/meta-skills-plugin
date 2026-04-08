# Modus 3: Audit — Full Process with Eval Integration

> Loaded on-demand when /meta-skills:audit is invoked.
> EVERY optimization is measured: baseline BEFORE, compare AFTER.

## Step 0: Baseline ALL Skills (PFLICHT — vor jeder Aenderung)

```bash
# Save baseline snapshot for every local skill
for skill in $(find .claude/skills -name "SKILL.md" 2>/dev/null); do
  python "${CLAUDE_PLUGIN_ROOT}/scripts/eval-skill.py" "$skill" --baseline
done
```

This creates a JSONL history entry for each skill BEFORE any changes.
Without this step, we cannot measure improvement.

## Step 1: Run Inventory + Eval Report

```bash
# Audit: score all skills
python "${CLAUDE_PLUGIN_ROOT}/scripts/audit-skills.py"

# Eval: generate readable Markdown report
python "${CLAUDE_PLUGIN_ROOT}/scripts/eval-skill.py" --all --report-md
```

Present to the user:
- Total skills found (by source: local/user/plugin)
- By recommendation: keep/optimize/update/archive
- Top 5 most expensive skills (token cost)
- Top 5 lowest quality skills
- Average quality score across all skills

## Step 2: Review Each Flagged Skill

For each skill with recommendation != "keep", present:
- Name, source, score
- Token cost (invocation + tool overhead)
- Issues found
- Recommended action with explanation

Ask the user for EACH skill (or ask for batch mode):
- A) Archive (move to _archive/, remove from index)
- B) Optimize (start meta:creator Phase 4 rewrite)
- C) Upgrade (create local optimized copy of plugin skill)
- D) Merge (combine with another overlapping skill)
- E) Keep (update last-audit date only)
- F) Skip (decide later)

## Step 3: Execute Actions with Eval

EVERY change is measured. For each skill being optimized:

```
1. eval-skill.py SKILL.md --baseline   ← VORHER (if not done in Step 0)
2. Apply optimization (Phase 4c rules: tools, triggers, budget, category)
3. eval-skill.py SKILL.md --compare    ← NACHHER
4. Show delta to user: "1,833 -> 1,056 Token (-42%), Quality 38 -> 80 (+111%)"
5. User confirms or reverts
```

Actions:
- Archive: move SKILL.md to _archive/skills/<name>/
- Optimize: apply R1-R5 from token-optimization.md, measure delta
- Upgrade: copy plugin skill to local, run optimization, measure delta
- Merge: create new combined skill, archive originals, measure combined vs sum
- Keep: update last-audit in frontmatter, save snapshot with label "audit-keep"

## Step 4: Final Report

After all actions:

```bash
# Regenerate catalog with updated data
python "${CLAUDE_PLUGIN_ROOT}/scripts/audit-skills.py" --catalog-only

# Generate final report showing all improvements
python "${CLAUDE_PLUGIN_ROOT}/scripts/eval-skill.py" --all --report-md
```

Present summary:
"Audit complete:
- N skills evaluated
- X archived (saved Yk routing tokens)
- Y optimized (avg -Z% invocation tokens)
- W kept (last-audit updated)
- Total token savings: N tokens per session
- Report saved to: [path]"

## Step 5: Commit Results

```bash
git add .claude/skills/
git commit -m "refactor(skills): meta:audit batch — X optimized, Y archived, Z% avg improvement"
```
