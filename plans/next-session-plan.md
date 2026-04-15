# Next Session Plan: meta-skills v4.0 + Pi-Mono Migration

## Session Start Prompt

```
meta-skills Plugin v3.0 (15 Skills, 14 Commands, 9 Hooks, 26 Scripts).
cli-council v1.0 (7 CLIs). pi-skills Phase 1 (3 Extensions, 4 Skills).
Lies: phantom-ai/meta-skills/plans/next-session-plan.md

ALLE 7 Prinzipien DONE: P1 Confidence Consensus, P2 Behavioral Tests,
P3 Orthogonal Revision, P4 Correction Promotion, P5 Write-Time QA,
P6 Cost Routing, P7 Context Recovery.

harden.py: 0 CRITICAL, 0 WARNING, 0 INFO (parser fixed).
5 CI Workflows gruen. 15/15 Skills haben test-scenario.md.
Pi Coding Agent installiert (v0.67.1).

Naechste Aufgaben:
1. Pi-Mono Phase 2: Extensions testen + correction-detect portieren
2. Voller Autoreason Run auf alle 15 Skills (Cross-Model mit 7 CLIs)
3. Skill-Registry regenerieren (build-skill-registry.py)
4. Session Report schreiben
5. Promote Corrections (3x Korrekturen -> automatische Rules)
```

## DONE (Session 2026-04-14)

| Was | Status |
|-----|--------|
| CI Failure gefixt (credentials) | DONE |
| session-init CI Check | DONE |
| plugins-ci.yml (5 Jobs) | DONE |
| Circuit Breaker entfernt | DONE |
| Docs Update (5 stale Files) | DONE |
| Research (13 Repos, 2 KB Sources) | DONE |
| P1 Confidence-Weighted Consensus | DONE |
| P2 Behavioral Skill Tests (15/15) | DONE |
| P3 Orthogonal Revision | DONE |
| P7 Context Recovery | DONE |
| harden.py YAML parser fix | DONE |
| OpenCode/Kimi/Qwen Configs (32 Files) | DONE |
| Pi-mono Phase 1 (3 Extensions, 4 Skills) | DONE |
| ERPNext Task TASK-2026-00621 | DONE |

## Priority 1: Pi-Mono Phase 2 — Test + Extend

Pi Coding Agent v0.67.1 installiert. Extensions in `pi-skills/`.

**Test:**
```bash
cd phantom-ai && pi  # Starten, Skills + Extensions pruefen
```

**Bauen:**
- correction-detect Extension (User-Korrektur Erkennung)
- verify als echte Permission Gate (blockiert statt warnt)
- Autoreason ueber Pi native Provider (statt CLI subprocess)

## Priority 2: Voller Autoreason Run

```bash
cd meta-skills
python3 scripts/autoreason-skills.py --all --max-passes 2 --dry-run
```

Jetzt mit: P1 Confidence Weighting, P3 Orthogonal Revision, 7 CLIs als Judges.

## Priority 3: Skill Registry + Promote Corrections

```bash
python3 scripts/build-skill-registry.py    # Regenerate registry
python3 scripts/promote-corrections.py     # 3x corrections -> rules
```

## Priority 4: Session Report + Knowledge Sync

- Session Report in oversight/
- open-notebook: volle Session Summary
- ERPNext: Task-Updates

## Architecture Reference

```
phantom-ai/
├── meta-skills/          # Claude Code Plugin (v3.0, 15 Skills, all P1-P7 DONE)
├── cli-council/          # Multi-CLI Council (v1.0, 7 CLIs)
├── cli-configs/          # OpenCode/Kimi/Qwen native configs (32 Files)
├── pi-skills/            # Pi Coding Agent Extensions (Phase 1)
│   ├── extensions/       # quality-gate, exploration-first, approach-guard
│   ├── skills/           # verify, systematic-debugging, tdd, harden
│   ├── AGENTS.md         # Core rules
│   └── package.json      # Future npm package
└── harness-verify/       # Enterprise harness (678 checks)
```
