# Quality Checklist — Before Finalizing a Skill

> Verify every item during Phase 4d. All must pass.

## Functional
- [ ] Solves the problem stated in Phase 1
- [ ] All steps from Phase 3 are implemented
- [ ] Edge cases from Phase 3 are handled
- [ ] Another agent could execute this without clarification

## Token Efficiency
- [ ] token-budget is set and realistic
- [ ] No redundant explanations
- [ ] Details in references/, not in SKILL.md body
- [ ] allowed-tools contains ONLY tools actually used
- [ ] model is cheapest that works (haiku > sonnet > opus)

## Triggers
- [ ] Description has precise trigger words
- [ ] No overlap with existing skills (ran check-duplicates.py)
- [ ] Covers both German AND English if bilingual

## Format
- [ ] Valid YAML frontmatter
- [ ] name uses active-verb format
- [ ] version is set (1.0.0 for new skills)
- [ ] category is set

## meta: Fields
- [ ] type: meta or standard
- [ ] cooperative: true
- [ ] created-with: meta:creator v0.1.0
- [ ] created-date: YYYY-MM-DD
- [ ] token-budget: estimated tokens per invocation
- [ ] usage-frequency: daily/weekly/rare
