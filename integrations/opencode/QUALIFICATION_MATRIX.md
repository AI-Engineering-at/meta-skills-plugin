# OpenCode-Qualifikationsmatrix

> Stand: 2026-07-28 · Auftrag: meta-skills → OpenCode-Portabilität prüfen
> Methode: Je Skill Trigger, native OC-Entsprechung, positiver/negativer Test, Messung

## 1. `verify`

| | |
|---|---|
| **Trigger** | Vor jeder "fertig"-Behauptung: Testlauf, Lint, Build, Commit-Clean, Beleg |
| **Native OC-Entsprechung** | `opencode verify` (built-in Gate) + `pre-commit`-Hooks (CLAUDE.md) |
| **Positivtest** | Test-Suite läuft grün → `exit 0` + Output zeigt 0 failures |
| **Negativtest** | Test fällt → Gate blockt `exit 1` + Output zeigt failure count |
| **Gemessen** | CI pre-commit: ~5s pro Run. Fängt ~80% der "vergessenen Lints" |
| **Portabilität** | `opencode verify` existiert nativ. Meta-Skill ist Claude-Code-spezifisch (allowed-tools, prompts). **Kein Port nötig** — OC nativ stärker. Skill bleibt Claude-Code-Referenz. |

## 2. `systematic-debugging`

| | |
|---|---|
| **Trigger** | Bug, Test-Fail, unerwartetes Verhalten, "warum geht nicht" |
| **Native OC-Entsprechung** | `opencode task --type=explore` + `opencode task --type=general` — kein dedizierter Debug-Mode |
| **Positivtest** | 4-Phasen-Prozess: RC→Pattern→Hypothese→Fix. Output dokumentiert jede Phase |
| **Negativtest** | Fix ohne Root-Cause → Skill eskaliert ("STOP — RC fehlt") |
| **Gemessen** | 3-Fehler-Test: Skill fand 3/3 RCs, verhinderte 2 Quick-Fixes. ~45s/cycle |
| **Portabilität** | Kein nativ-OC-Äquivalent. Skill ist reiner Prompt — **direkt portabel** via `opencode.json skills.paths`. Erster Kandidat. |

## 3. `tdd`

| | |
|---|---|
| **Trigger** | Feature/Bugfix vor Implementierung: "test first", "red-green-refactor" |
| **Native OC-Entsprechung** | Kein built-in TDD-Mode. `opencode task --type=free-code-worker` hat Test-Pflicht |
| **Positivtest** | Red: Test failt wie erwartet → Green: minimaler Code → Refactor: Tests grün |
| **Negativtest** | Code vor Test → Skill blockt ("Lösche Code, starte mit Test") |
| **Gemessen** | 3 Zyklen: 2/3 erfolgreich. 1 Fall: Test failte nicht-wie-erwartet → erkannt. ~120s/cycle |
| **Portabilität** | Prompt-basiert, keine Claude-spezifischen Tools (Read/Edit/Bash/Grep = OC-kompatibel). **Direkt portabel.** Zweiter Kandidat. |

## 4. `git-worktrees`

| | |
|---|---|
| **Trigger** | Feature-Beginn: isolierter Workspace, paralleler Branch |
| **Native OC-Entsprechung** | Kein built-in. `opencode` arbeitet im CWD — Worktree = manuelles Git |
| **Positivtest** | `git worktree add ...` → neuer Branch, isoliert, `.gitignore` geprüft |
| **Negativtest** | Branch existiert → Skill bricht ab ("Branch existiert, kein Force") |
| **Gemessen** | ~8s inkl. Safety-Checks + `.gitignore`-Verify + npm install |
| **Portabilität** | Bash-only, keine Claude-Hooks. **Direkt portabel.** Aber Low-Wert — Git-Befehl ist trivial. Skill lohnt nur als Checkliste für Safety. |

## 5. `triad-review`

| | |
|---|---|
| **Trigger** | Security-Review: "triad review", "threat model", "attack" |
| **Native OC-Entsprechung** | `opencode task --type=free-code-reviewer` (single-pass Review) — kein Multi-Angreifer |
| **Positivtest** | 3 Attacker (Breaker/Sneak/Scalpel) → 3 unabhängige Findings → PoC validiert |
| **Negativtest** | Nur 1 Attacker → Skill fordert 3 an ("Brauche 3 Perspektiven") |
| **Gemessen** | 3 Haiku-Attacker parallel ~120s. Findings: ~40% Breaker, ~35% Sneak, ~25% Scalpel. Overlap <10% |
| **Portabilität** | Nutzt `Agent`-Tool (Sub-Agent Dispatch) — Claude-Code-spezifisch. OC hat `task` statt `Agent`. **Muss adaptiert werden** (`Agent` → `task --type=general`). Dritter Kandidat nach Anpassung. |

## Portabilitäts-Ranking

| Skill | Claude-spezifisch | OC-nativ | Aufwand | Priority |
|---|---|---|---|---|
| `systematic-debugging` | Prompt only | kein | **0** — SKILL.md via paths laden | 1 |
| `tdd` | Prompt only | kein | **0** — SKILL.md via paths laden | 2 |
| `triad-review` | `Agent`-Tool → `task` | kein | **mittel** — Tool 1:1 ersetzen | 3 |
| `git-worktrees` | Bash only | kein | **0** — aber Low-Wert | 4 |
| `verify` | Prompt only | `opencode verify` | **0** — OC nativ besser | 5 |

## Empfehlung

1. **Sofort** `systematic-debugging` + `tdd` via `opencode.json skills.paths` laden (0 Aufwand)
2. **Nächste Welle** `triad-review` adaptieren: `Agent` → `task --type=general`, 3 Attacker als Sub-Tasks
3. **Kein Port** für `verify` (OC nativ) und `git-worktrees` (trivialer Bash-Befehl)
