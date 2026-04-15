---
description: "Adversarial blind review — 2 parallel Judges, Verdict Synthesis, Fix + Re-Judge"
argument-hint: '"target description" [--scope files/dirs]'
---

# Judgment Day

Start an adversarial review with 2 parallel blind judges.

Load the Judgment Day skill and follow the full flow:
1. Skill Resolver: load compact rules
2. Launch 2 judges in parallel (haiku, blind)
3. Verdict Synthesis (Confirmed/Suspect/Contradiction)
4. WARNING classification (real vs theoretical)
5. Fix-Agent for confirmed issues (sonnet)
6. Re-Judge for CRITICALs
7. APPROVED or ESCALATED

Target: $ARGUMENTS
