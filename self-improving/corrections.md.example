# Corrections Log — meta-skills

> Appended by: meta:feedback (Missverstaendnis-Tabelle), manual
> Read by: meta:creator (avoid repeating mistakes), meta:feedback (pattern detection)

| Date | What I Got Wrong | Correct Answer | Root Cause | Status |
|------|-----------------|----------------|------------|--------|
| 2026-04-06 | "weniger Kaesten" = unsichtbar | = weniger Container | Woertlich interpretiert | Fixed (USER_PATTERNS) |
| 2026-04-06 | "wie knut.network" = Layout kopieren | = Stimmung uebernehmen | Referenz woertlich genommen | Fixed (USER_PATTERNS) |
| 2026-04-06 | 3 farbige Blur-Kreise | User wollte Neural Network BG | Stitch-Output blind kopiert | Fixed (NeuralBackground.tsx) |
| 2026-04-08 | meta: Fields nested in YAML | Should be flat fields | Agent schrieb nested statt flat | Fixed (Patch) |
| 2026-04-08 | UI-Frage fuer Text-Skill gestellt | Text-Skill braucht offensichtlich keine UI | Ueber-vorsichtiges Fragen statt Nachdenken | Noted |
| 2026-04-08 | Sub-Agent falscher Pfad (voice-gateway/) | Sollte meta-skills/ sein | Zu wenig Pfad-Kontext im Prompt | Fixed (manuell) |
| 2026-04-08 | marketplace.json blind erstellt | Schema nicht gelesen | Erst Doku lesen, dann erstellen | Fixed (geloescht) |
| 2026-04-08 | eval-skill.py Markdown-Backtick im Python | Write-Tool escaped Backticks nicht | Syntax-Check nach Write | Fixed |
| 2026-04-08 | 37 Skills batch-refactored ohne Funktionstest | Mechanisch != funktional getestet | Geschwindigkeit vor Qualitaet | OFFEN |

## Session 2026-04-13 Corrections

### C-QA01: quality-snapshot.py CWD Bug
eval.py findet keine Skills wenn von meta-skills/ Verzeichnis gestartet.
Fix: CWD auf PLUGIN_ROOT.parent setzen.

### C-QA02: quality-gate.py detect_failure() Order
False-positive Check ist order-dependent. "0 errors" + "FAILED" = False Positive gewinnt.
Fix: Failure-Indicators erst pruefen, False-Positives nur als Override.

### C-QA03: Windows subprocess shell=True
npm-installierte CLIs (.cmd Wrapper) brauchen shell=True auf Windows.
Vergessen = FileNotFoundError. Immer platform.system() checken.

## Session 2026-04-14 Corrections

### C-CI01: grep 'CRITICAL' matches 'CRITICAL: 0'
harden.py CI check used `grep -q 'CRITICAL'` which matched the summary line
`CRITICAL: 0`. Fix: `grep -E 'CRITICAL: +[1-9]'` for non-zero count only.

### C-CI02: hooks/lib/*.py are NOT hooks
Plugins CI hook safety check scanned `hooks/lib/` helper modules and flagged
missing sys.exit(0). Fix: `find -maxdepth 1` to exclude lib/ subdirectory.

### C-PARSE01: YAML multiline description not parsed
harden.py frontmatter parser only read non-indented lines, missing multiline
`description: >` continuation lines. All 15 skills had Trigger: keywords but
parser didn't see them. Fix: track current_key, append indented lines.

### C-HOOK01: Circuit breaker counts harmless errors
Legacy post_failure_tracker.py in ~/.claude/hooks/ counted "Shell cwd was reset"
as real errors. Disabled — quality-gate.py handles failure detection better
with per-line false-positive exclusion.
