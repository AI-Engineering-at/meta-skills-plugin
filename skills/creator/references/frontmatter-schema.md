# meta: Frontmatter Schema Reference

> Loaded on-demand when writing frontmatter in Phase 4.

## Required (AgentSkills.io)

| Field | Type | Example |
|-------|------|---------|
| name | string | deploy-service |
| description | string | "Deploy to prod. Trigger: deploy, ship" |
| model | enum | sonnet |
| allowed-tools | list | [Read, Bash] |
| user-invocable | bool | true |
| version | semver | 1.0.0 |

## meta: Extensions

| Field | Type | Example | When |
|-------|------|---------|------|
| type | enum | meta/standard | Always |
| cooperative | bool | true | If built with meta:creator |
| created-with | string | meta:creator v0.1.0 | If built with meta:creator |
| created-date | date | 2026-04-08 | Always |
| token-budget | int | 8000 | Always (estimated) |
| token-optimized | bool | true | After Phase 4c |
| usage-frequency | enum | daily/weekly/rare | Always |
| category | string | infrastructure | Always |
| last-audit | date | 2026-04-08 | After Modus 3 |
| platforms | list | [claude, cursor] | If cross-platform |
| portable | bool | true | If no platform deps |
