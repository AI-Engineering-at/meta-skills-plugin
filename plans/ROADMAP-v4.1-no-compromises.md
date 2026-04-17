# Roadmap v4.1 — meta-skills, keine Kompromisse

> Erstellt: 2026-04-17 | Nachfolge von `HANDOVER-2026-04-17.md`
> User-Anweisung: "plana alles ausreichend, keine kompromisse"
> Ziel: alle offenen Punkte aus Session 2026-04-16/17 sauber schliessen,
> inkl. Root-Cause der dual-repo Pain-Points.

Alle Phasen: eigenes Ergebnis + eigene Verifikation + eigener Rollback.
Jede Phase ist atomic (mergen einzeln, revertierbar einzeln).

---

## PHASE 1 — Opus 4.7 live im Statusbar (Priorität: NOW)

**Problem:** `settings.json.statusLine.command` zeigt auf phantom-ai-Working-Tree.
Auto-Sync alle 15min zieht phantom-ai main → reverts meta-skills Working-Tree.
meta-skills-plugin-PR-Commits sind in git history, landen aber nie live.

**Deliverable:** Claude Code rendert `O4.7` nach Neustart. Verifiziert per
Screenshot oder `curl` an die Statusline.

### Schritt 1.1 — Auto-Sync pausieren (Safety)
```bash
# Falls systemd-Timer (Linux/macOS):
systemctl --user stop phantom-ai-sync.timer
# Falls Task Scheduler (Windows — PowerShell als Admin):
Disable-ScheduledTask -TaskName "phantom-ai-autosync"
```
Verifikation: `git status` im phantom-ai-Repo über 20 Minuten unverändert.
Rollback: Task wieder `Enable-ScheduledTask`.

### Schritt 1.2 — statusline.py + statusline_lib.py in phantom-ai main landen
Cherry-pick aus meta-skills-plugin feature branch in phantom-ai main:

```bash
cd C:/Users/Legion/Documents/phantom-ai
# Auf main-Zweig wechseln (VRAM-Branch darf offen bleiben)
git checkout main && git pull --ff-only
git checkout -b chore/meta-skills-opus47-sync

# Cherry-pick der 3 Statusline-Kernfiles aus dem Plugin-Repo:
cd meta-skills
git --git-dir=.git fetch origin feature/statusline-opus47-hardening
git --git-dir=.git checkout origin/feature/statusline-opus47-hardening -- \
  scripts/statusline.py scripts/statusline_lib.py scripts/validate.py \
  tests/test_statusline_formatters.py

cd ..
git add meta-skills/scripts/statusline.py meta-skills/scripts/statusline_lib.py \
        meta-skills/scripts/validate.py meta-skills/tests/test_statusline_formatters.py
git commit -m "chore(meta-skills): sync Opus 4.7 statusline from plugin repo

Cherry-pick from meta-skills-plugin PR #1:
- statusline.py: regex model detection, imports from statusline_lib
- statusline_lib.py: fk/fcost/parse_model_id with boundary fix
- validate.py: claude-opus-4-7 in VALID_MODELS
- tests/test_statusline_formatters.py: 25 boundary tests

Needed because phantom-ai/meta-skills/ is on the statusLine command
path and auto-sync would otherwise revert these files."
git push -u origin chore/meta-skills-opus47-sync
# PR → phantom-ai main
```

Verifikation:
1. PR approved + merged → auto-sync pulls main → working-tree hat Opus 4.7 Code
2. Claude Code neu starten (Window neu öffnen)
3. Statusbar prüfen: erwartet `O4.7(1M)` statt `O4.6(1M)`

Rollback: `git revert` des phantom-ai commits.

### Schritt 1.3 — Auto-Sync wieder aktivieren (nach 1.2 gemerged)
```bash
# Einschalten:
systemctl --user start phantom-ai-sync.timer   # Linux
Enable-ScheduledTask -TaskName "phantom-ai-autosync"  # Windows
# Erste Runde anstossen:
cd ~/Documents/phantom-ai && git pull --ff-only
```
Verifikation: Statusbar zeigt weiterhin `O4.7` nach dem Sync.

**Abbruch-Kriterium P1:** wenn nach Schritt 1.2 `O4.7` nicht erscheint,
STOP. Zurück zu Schritt 1.1 Auto-Sync aus, Ursache debuggen.

---

## PHASE 2 — PR #1 auf meta-skills-plugin mergen

**Stand:** 17 Commits auf `feature/statusline-opus47-hardening`.
PR https://github.com/AI-Engineering-at/meta-skills-plugin/pull/1 offen.

### Schritt 2.1 — CI erst nach Merge laufen lassen
Die neue `.github/workflows/ci.yml` triggert erst AUF main. Daher kann der
Merge-Commit erst die Runs produzieren. Plan:
- PR mergen (squash oder merge-commit — empfohlen merge-commit, Commits
  sind kuratiert, history wertvoll)
- Erste CI-Runs auf main beobachten, bei Fehlern Hotfix-Commit

### Schritt 2.2 — PR-Review-Checkliste (vor Merge)
- [ ] Alle 17 Commits logisch, Messages matchen Inhalt
- [ ] `git log --all --stat -- oversight/hardening-2026-04-17.md` — zeigt
      Sanitize-Commit `140c46d` als letzten Touch
- [ ] `git show HEAD:oversight/hardening-2026-04-17.md | grep -E "Legion|C:/" | wc -l` = 0
- [ ] `git ls-files | xargs grep -l "Legion\|10\.40\.10\." 2>/dev/null` = nur
      dokumentierte Vorkommen (skills/creator/references/export-process.md)
- [ ] Lokaler `pytest tests/test_statusline_formatters.py` = 25/25
- [ ] Lokaler `python scripts/hardening-run.py --ci` = exit 0

### Schritt 2.3 — Merge-Strategie
- `main` auf meta-skills-plugin ist noch v3.0.0-Level
- Branch bringt v4.1 (Opus 4.7 + T-Scale + Tests + Evidence-Hardening)
- Nach Merge: `.claude-plugin/plugin.json` → version bump `3.0.0 → 4.1.0`
  - separater Follow-up-Commit (nicht in diesem PR), so dass der PR ausschließlich Code-Arbeit ist

### Schritt 2.4 — Announcement (optional)
Neuer README-Abschnitt "Changelog v4.1" — kann später, nicht blocking.

---

## PHASE 3 — Dual-Repo Architektur sauber machen

**Problem identifiziert (Root-Cause der P1-Pain):**
`phantom-ai/meta-skills/` und `meta-skills-plugin/` sind zwei Git-Repos
die dieselben Files tracken. Jede Änderung muss doppelt gepflegt werden.
Auto-Sync verschlechtert das weiter, weil er nur eine Seite kennt.

### Schritt 3.1 — Architektur-Entscheidung
Drei Varianten, Wahl durch Joe:

| Variante | Was passiert | Vor | Nach |
|---|---|---|---|
| **A: Git Submodule** | `phantom-ai/meta-skills` → submodule von meta-skills-plugin | Klassisch, tooling-support | Submodul-UX ist frickelig, muss explicit init |
| **B: Git Subtree** | meta-skills-plugin per `git subtree` in phantom-ai gemerged | User sieht nur ein Repo | Rechte/History-Mixing, schwierig zu rückgängig |
| **C: Sync-Mirror** | Ein Repo ist Wahrheit, anderer wird per CI gesynct | Flexibel, klare Richtung | CI-Maintenance, Sync-Delay |
| **D: Hard-Merge** | meta-skills-plugin stirbt, lebt nur in phantom-ai | Einfachst | Public-Exposure verlieren falls gewollt |

**Empfehlung:** C (meta-skills-plugin ist Wahrheit, phantom-ai consumes via sync).
- meta-skills-plugin bleibt standalone public repo
- phantom-ai hat nur einen Sync-Hook: nach git pull auf main von meta-skills-plugin
- Verhindert dass lokale Edits in phantom-ai/meta-skills/ divergieren

### Schritt 3.2 — Umsetzung Variante C (falls gewählt)
```bash
# In meta-skills-plugin (auf main):
#   .github/workflows/ publish-to-phantom-ai.yml
#   - on: push.branches: [main]
#   - Action: clone phantom-ai, sync meta-skills/ subtree, PR

# In phantom-ai:
#   - meta-skills/ wird NICHT mehr manuell editiert
#   - CONTRIBUTING.md: "meta-skills changes go to meta-skills-plugin first"
#   - pre-commit hook blockt commits die meta-skills/ anfassen
```

### Schritt 3.3 — Dokumentation
- `meta-skills-plugin/CONTRIBUTING.md` — Source-of-Truth Statement
- `phantom-ai/CLAUDE.md` — Hinweis + neuen Source-of-Truth Eintrag in Rule G2
- `meta-skills/CLAUDE.md` — Pointer nach oben

---

## PHASE 4 — Verbleibende Quality-Debt abbauen

### Schritt 4.1 — Pathlib-Migration PR (74 → 0 lint warnings)
- 45 × `PTH*` (os.path → pathlib) in hooks/ + scripts/
- Umfang ~41 Dateien, großer Diff
- Eigener Branch: `refactor/pathlib-migration`
- Regression-Gate: tests/test_statusline_formatters.py + hardening-run.py vorher + nachher grün
- Cross-Platform-Test: lokal Windows, CI macht Linux

### Schritt 4.2 — CI-Gates in phantom-ai landen
- Patch bereit: `meta-skills/oversight/ci-gates-proposal.patch`
- Voraussetzung: VRAM-Branch in phantom-ai ist gemerged
- Eigener PR auf phantom-ai

### Schritt 4.3 — 2 INFO-Findings aus harden.py
- `hooks/session-end.py` + `hooks/session-stop.py`: subprocess.run ohne
  `shell=True` kann auf Windows bei `.cmd`-Wrappern fehlschlagen
- Fix: `platform.system() == "Windows"` Guard + `shell=True` dort

### Schritt 4.4 — Plugin-Version bump in .claude-plugin/plugin.json
- v2.0.0 → v4.1.0
- CHANGELOG.md mit Zusammenfassung v3 → v4.1
- Upload zu Marketplace falls gelistet

---

## PHASE 5 — Hygiene + Prevention (damit's nicht wieder passiert)

### Schritt 5.1 — Pre-Commit-Hook fuer PII-Checks (meta-skills-plugin)
```bash
#!/usr/bin/env bash
# .git/hooks/pre-commit (installiert via scripts/install-hooks.sh)
set -e
if git diff --cached | grep -E "(C:/Users/|/home/[a-z]+/|10\.40\.10\.|Legion)"; then
  echo "ERROR: PII detected in staged changes"
  exit 1
fi
```
Verhindert C-CLAIM01-Wiederholung (absolute Pfade in Commits).

### Schritt 5.2 — Hardening-Report als CI-Artifact-Only
- Aktuell: `oversight/hardening-*.md` wird mit committed (kann durch Generator-Bugs PII leaken)
- Besser: .gitignore auch für `.md`, CI-Run uploaded als Artifact
- Historische Reports separat in `oversight/archive/` mit Sanitize-Gate

### Schritt 5.3 — Auto-Sync Safety
- phantom-ai Auto-Sync: `meta-skills/` per `.gitattributes merge=ours` schützen ODER
- Explizite Whitelist welche Files synced werden (nicht komplette subtree)
- Dokumentiert in `phantom-ai/.claude/rules/XX-auto-sync.md`

### Schritt 5.4 — Test-Coverage erweitern
- `tests/test_statusline_formatters.py` ist der Anfang (25 tests)
- Nächste: test_statusline_stats_file.py (Backfill-Logik, Prune-Exception)
- `tests/test_hardening_run.py` (sanitize + check-parser)
- Ziel: 50+ Tests, alle boundary/edge cases gecoverd

---

## Verifikations-Matrix (pro Phase)

| Phase | Ende-Kriterium | Befehl zum Prüfen |
|---|---|---|
| P1 | Statusbar rendert `O4.7` | visual check, `~/.claude/statusline-alltime.json` zeigt model=claude-opus-4-7 |
| P2 | PR #1 merged, main grün | `git log meta-skills-plugin/main`, GitHub Actions tab |
| P3 | Nur 1 Wahrheit für meta-skills | `git log` der zweiten Seite zeigt NUR Sync-Commits |
| P4.1 | Lint 74 → 0 | `ruff check hooks/ scripts/` |
| P4.2 | phantom-ai CI hat 2 neue Jobs | GitHub Actions Tab |
| P4.3 | harden.py INFO 2 → 0 | `python scripts/harden.py --scan` |
| P5.1 | Pre-Commit blockt PII | Test-Commit mit Legion-Pfad → Reject |
| P5.2 | `oversight/*.md` nicht mehr tracked | `git ls-files oversight/` |
| P5.4 | 50+ Tests grün | `pytest tests/ -v` |

---

## Timeline (Schätzung, kann parallelisiert werden)

| Phase | Dauer solo | Dauer parallel |
|---|---|---|
| P1 (Opus 4.7 live) | 30 min | 30 min (blockiert alles andere) |
| P2 (PR #1 merge) | 15 min Review + Merge | parallel zu P3 |
| P3 (Dual-Repo) | 2h Design + 2h Impl | parallel zu P4 |
| P4.1 (Pathlib) | 3h Refactor + 1h Test | — |
| P4.2 (CI-Gates) | 20 min | parallel zu P4.1 |
| P4.3 (Windows subprocess) | 30 min | parallel |
| P4.4 (Version bump) | 10 min | nach P2 |
| P5.1-5.4 (Hygiene) | je 30-60 min | parallel |

**Sequenz nicht-parallelisiert:** P1 → P2 → P3 → P4 → P5
**Sequenz parallel (realistisch):** P1, dann P2+P3 parallel, dann P4.*+P5.* parallel
**Gesamt solo:** ~12h | **Gesamt mit parallelen Sub-Agenten:** ~6h

---

## Entscheidungspunkte für Joe

1. **Phase 3 Variante A/B/C/D?** — bestimmt den Architektur-Stil
2. **Phase 4.1 priority?** — Pathlib jetzt oder später?
3. **Phase 5.2 oversight/*.md ganz ignoren?** — dann historische Reports in Archive
4. **Plugin-Version**: v4.1.0 mit dem Merge, oder erst v4.1.0 nach P4?

---

## Was explizit NICHT im Scope ist (um Drift zu vermeiden)

- VRAM-Guard Arbeit auf phantom-ai (separater Task)
- Zeroth-Core v0.4.0 → v0.4.1 Verifikation (separater Task)
- Marketplace-Publishing (nach v4.1 Release)
- Mehrere CLIs parallel evaluieren (v5.0-Kandidat)

---

*Plan-Autor: Claude Opus 4.7 (1M context) | Trust-Status nach Session
2026-04-16/17: 2/10 — nächste Session bitte mit engem Scope + expliziten
User-Bestätigungen je Phase starten.*
