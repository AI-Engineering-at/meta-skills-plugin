# Audit-Verify Report — 2026-04-21

> **Context**: Parallele Session hat 5-Agent-Audit gefahren. Diese Session
> hat jede SOFORT/HIGH Premise verifiziert bevor irgendeine Action
> geplant wurde. "prüfe alles" Direktive von Joe.
>
> **Kernbefund**: Audit-Findings sind **nicht einheitlich vertrauenswürdig**
> innerhalb desselben Dispatch-Runs. 1 Agent komplett halluziniert
> (Agent 1), 1 Agent teilweise falsch (Agent 2), 3rd-party Quelle
> zufällig korrekt (Agent 4 Premise), Agent 5 korrekt.

---

## Findings-Matrix (F1-F11)

| # | Claim | Quelle | Status | Evidence |
|---|---|---|---|---|
| F1 | API-Keys in `~/.claude/settings.json` Klartext | Agent 3 | ✅ **REAL** | settings.json:34-37 Frappe, :39 N8N JWT, :72 N8N JWT |
| F2 | 7 globale Hooks referenzieren fehlende Files | Agent 1 | ❌ **HALLUZINATION** | Glob: alle 8/8 Files on disk |
| F3 | Opus 4.7 Tokenizer +1.0-1.35× | aicatchup.com + Joe-Dok | ✅ **OFFICIAL ANTHROPIC** | docs.anthropic.com, news.anthropic.com |
| F4 | Real-world Tokenizer-Faktor | Simon Willison, claudecodecamp | ✅ **1.46×** gemessen | Exceeds Anthropic 1.35× |
| F5 | Prefill removal = 400 error | Anthropic migration | ✅ REAL API-Break | 0 in meta-skills (Grep) |
| F6 | `count_tokens` Endpoint returns different numbers | Anthropic | ✅ REAL | `scripts/eval.py`, `scripts/eval-skill.py` |
| F7 | Images bis 3× Tokens | Anthropic | ✅ REAL | 0 Images in meta-skills (Grep false positive = install-hooks.sh skip-list) |
| F8 | `token-budget:` in YAML frontmatter existiert | Agent 4 | ✅ konfirmiert | 16/16 SKILL.md haben `token-budget:` Field |
| F9 | "8 Skills brauchen execute-without-pausing" | Agent 4 (aicatchup) | ⚠️ **UNVERIFIZIERT** | Anthropic confirmed "literal instruction following" — aber konkrete 8 Skills nicht belegt |
| F10 | CLAUDE.md Schritte 1-5 redundant | Agent 2 | ⚠️ **TEILWEISE FALSCH** | Nur 3/5 Schritte hook-covered (siehe unten) |
| F11 | tuneforge mypy/pre-commit/coverage fehlen | Agent 5 | ✅ **REAL** (alle 3) | pyproject.toml:68 hat `[tool.ruff]` aber kein `[tool.mypy]`; `.pre-commit-config.yaml` MISSING; keine `fail_under` config |

---

## V-Claims (eigene Verifikation)

### V1 tuneforge Gaps

Pfad: `C:\Users\Legion\Documents\tuneforge\` (nicht `phantom-ai/tuneforge`).

| Gap | Status |
|---|---|
| `pyproject.toml` exists | ✅ yes |
| `[tool.mypy]` in pyproject | ❌ missing (grep 0 matches) |
| `[tool.coverage]` fail_under | ❌ missing |
| `.pre-commit-config.yaml` | ❌ missing |
| `.mypy_cache/` Verzeichnis | ⚠️ existiert (mypy wurde laufen gelassen ohne Config) |
| `.coverage` Datei | ⚠️ existiert (coverage wurde laufen gelassen ohne Threshold) |

Fazit: Agent 5 korrekt. Tuneforge-Hardening ist legitimer Track.

### V2+V3 Skill-Budget-Probe (tiktoken cl100k @ 1.46×)

| skill | declared (SKILL.md) | cl100k | est @1.46× | Status |
|---|---:|---:|---:|---|
| creator | 5000 | 654 | 954 | ok (81% headroom) |
| design | 3000 | 486 | 709 | ok |
| dispatch | 3000 | 1266 | 1848 | ok (38% headroom) |
| doc-updater | 5000 | 631 | 921 | ok |
| feedback | 12000 | 760 | 1109 | ok (10× headroom!) |
| git-worktrees | 2000 | 837 | 1222 | ok |
| harden | 5000 | 606 | 884 | ok |
| init | 2500 | 1192 | 1740 | ok |
| judgment-day | 4000 | 576 | 840 | ok |
| knowledge | 3000 | 669 | 976 | ok |
| refactor-loop | 4000 | 1004 | 1465 | ok |
| **statusbar** | **200** | **1321** | **1928** | ⚠️ **OVER 10×** |
| systematic-debugging | 3000 | 630 | 919 | ok |
| tdd | 3000 | 1099 | 1604 | ok |
| triad-review | 4000 | 1685 | 2460 | ok |
| verify | 3000 | 901 | 1315 | ok |

**Agent 4's "alle 16 Skills über Budget" ist FALSCH.** 15/16 haben massive Reserve. Nur statusbar ist kritisch.

**ABER**: `token-budget:` Semantik ist unklar. Per `hooks/exploration-first.py:91-93` + `scripts/audit-skills.py:149-150` dient das Feld als **Scoring-Signal** (+15 Punkte wenn gesetzt), nicht als enforced cap. Per `skill-registry.json` existieren **zweite, teilweise abweichende Budgets**:

| Skill | SKILL.md | skill-registry.json | Diff |
|---|---:|---:|---|
| creator | 5000 | 25000 | 5× |
| dispatch | 3000 | 5000 | 1.67× |
| doc-updater | 5000 | 1500 | 3.3× |
| harden | 5000 | 10000 | 2× |
| refactor-loop | 4000 | 8000 | 2× |
| knowledge | 3000 | 8000 | 2.67× |
| triad-review | 4000 | 5000 | 1.25× |

**7/16 divergieren** zwischen SKILL.md und registry. Agent 4 hat das nicht erwähnt.

### V4 Images in meta-skills

Grep für `.png|.jpg|.jpeg|.gif|base64|data:image` → **1 match**: `scripts/install-hooks.sh:50` — Zeile ist Skip-Filter (`*.png|*.jpg|...) continue`), also false positive.

**0 tatsächliche Images in meta-skills.** F7 image-budget-audit = no-op.

### V5 CLAUDE.md Schritte 1-5 vs Hook-Coverage

Documents/CLAUDE.md Schritte:

| # | Schritt | Hook-Coverage | Redundant? |
|---|---|---|---|
| 1 | Aufgabe verstehen ("Verstehe ich richtig: [X]?") | KEIN Hook — manuelles Klarifizieren | ❌ NEIN — behalten |
| 2 | Scope-Vertrag (erlaubte Dateien, Done-Kriterien) | `scope-tracker.py` (UserPromptSubmit) | ✅ JA |
| 3 | Wissen prüfen (Quelle vorhanden? Keine Quelle → fragen) | KEIN Hook — semantischer Check | ❌ NEIN — behalten |
| 4 | Handeln (eine Aktion, verifizieren, bei Fehler STOP) | `exploration-first.py` + `quality-gate.py` | ✅ JA |
| 5 | Abschliessen (Scope durchgehen, dokumentieren) | `session-stop.py` + `session-end.py` | ✅ JA |

**Agent 2 "CLAUDE.md Schritte 1-5 redundant (29 Zeilen) → löschen" ist PARTIAL-FALSCH.** Schritt 1+3 haben KEIN Hook-Äquivalent und dürfen nicht gelöscht werden. Surgical Trim auf Schritt 2+4+5 OK.

---

## Summary: was ist WIRKLICH actionable

| # | Track | Status | Aufwand |
|---|---|---|---|
| 1 | tuneforge-harden (mypy + pre-commit + coverage-threshold) | GO-kandidat | 60-90 min |
| 2 | statusbar token-budget von 200 auf realistischen Wert (~2500 für Headroom) | GO-kandidat | 5 min — aber Semantik klären mit Joe |
| 3 | SKILL.md-vs-registry-budget-Divergenz auf 7 Skills consolidate | GO-kandidat | 20 min |
| 4 | count_tokens migration in eval.py + eval-skill.py für Opus 4.7 | GO-kandidat | 15-30 min |
| 5 | CLAUDE.md surgical trim — NUR Schritt 2+4+5 | GO-kandidat | 10 min (muss Joe-reviewed werden) |
| 6 | C-AGENT-HALLUCINATE-2026-04-21 in corrections.md.example | ✅ **done** | (5 min, fertig) |

## Nicht actionable (entweder falsch, 0-impact oder deferred)

| # | Track | Reason |
|---|---|---|
| — | "7 fehlende Hook-Files" | Halluzination (F2) |
| — | "Alle 16 Skills Budget +35%" | False pauschalisierung (V2+V3) |
| — | "Prefill removal fix" | 0 matches in meta-skills (F5) |
| — | "Images 3× budget" | 0 Images (V4) |
| — | CLAUDE.md "alle 29 Zeilen Schritte 1-5 löschen" | Schritt 1+3 sind nicht redundant |
| — | API-Keys rotieren | Joe hat deferred ("keys bleiben bis OK") |
| — | settings.json allow-list cleanup | Part von Key-Rotation-Sequenz (deferred) |
| — | `fix_daily_ops.py` archive-leak | Joe: "Unberührt lassen" |

---

## Sources

Anthropic official:
- https://www.anthropic.com/news/claude-opus-4-7
- https://docs.anthropic.com/en/release-notes/api
- https://docs.anthropic.com/en/docs/about-claude/models/migrating-to-claude-4
- https://platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-7

Third-party measurements (verified against multiple sources):
- https://simonwillison.net/2026/Apr/20/claude-token-counts/
- https://www.claudecodecamp.com/p/i-measured-claude-4-7-s-new-tokenizer-here-s-what-it-costs-you

---

*Erstellt: 2026-04-21 · Opus 4.7 · 1M context · Phase 0 Deliverable der VERIFY-FIRST Session · Quelle: `plans/idk-ich-will-es-happy-liskov.md`*
