# Self-Improving Index — meta-skills Data Layer

> Auto-updated by meta:feedback, meta:creator audit, and stop hook.
> This is the persistent memory of the meta-skills plugin.

| File | Purpose | Updated By |
|------|---------|------------|
| memory.md | User preferences, patterns, rules | meta:feedback, meta:creator Phase 5 |
| corrections.md | Corrections log with root cause | meta:feedback |
| heartbeat-state.md | Last audit, last discovery, health | stop hook, /meta-skills:audit |
| domains/ | Domain-specific knowledge (per category) | meta:creator Phase 2 |
| projects/ | Project-specific skill configs | meta:creator Phase 1 |
| archive/ | Archived skills + old snapshots | meta:audit archive action |

## Data Flow

```
Session → stop hook → heartbeat-state.md + session-metrics.jsonl
/feedback → corrections.md (misunderstandings) + memory.md (patterns)
/audit → heartbeat-state.md + archive/ + skill-history.jsonl
/create → memory.md (Phase 5 reflection) + domains/
```
