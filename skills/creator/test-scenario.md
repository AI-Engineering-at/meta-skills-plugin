Input: "I keep doing the same database migration steps every time. Can we automate this?"
Expected: Agent should analyze the pattern and propose a skill, not just write a script.
Pass: skill|pattern|reusable|SKILL\.md|frontmatter|trigger|automat|phase|create
Fail: ^here's a script|^run this command|^bash.*migrate
