# Meta Init — Detaillierte Modi

> Referenz-Details fuer alle 3 Modi. Hauptdatei: SKILL.md

## Modus 1: AUDIT — Detailschritte

### Phase A0: Automatischer Scan (silent)

```bash
# Meta-Engine Status
python meta-skills/scripts/validate.py --json 2>/dev/null
python meta-skills/scripts/eval.py --all 2>/dev/null | python -c "
import json,sys; d=json.load(sys.stdin)
scores=[r['quality']['score'] for r in d['results']]
print(json.dumps({'total':d['total'],'avg':sum(scores)/len(scores),
'below70':sum(1 for s in scores if s<70),'above90':sum(1 for s in scores if s>=90)}))"

# Git Status
git log --oneline -10
git status --short

# Projekt-Erkennung
ls package.json pyproject.toml Cargo.toml go.mod 2>/dev/null
ls .claude/rules/ 2>/dev/null | wc -l
ls .claude/skills/ 2>/dev/null | wc -l
ls .claude/agents/ 2>/dev/null | wc -l
```

### Phase A1: Status-Report zeigen

```markdown
## Projekt-Audit: [Name]

| Dimension      | Stand       | Details                           |
|----------------|-------------|-----------------------------------|
| Stack          | Python/...  | N Files, ~N LOC                   |
| Quality Score  | 89.4        | 56 Komponenten, 0 Errors          |
| Rules          | 17 aktiv    | .claude/rules/                    |
| Skills         | 32          | .claude/skills/ + meta-skills/    |
| Agents         | 22          | .claude/agents/                   |
| Teams          | 3           | monitoring, review, session-close |
| Git            | main        | Letzte Commits: ...               |
| CI Gate        | ✅ 0 errors  | validate.py                       |

## Empfehlungen
1. [Bottom-5 aus eval.py]
2. [validate.py Warnings]
3. [git status offene Dateien]
```

### Phase A2: Routing nach User-Antwort

- "Score verbessern" → `python meta-skills/scripts/reworker.py --diagnose --top 5`
- "Neuen Skill" → /meta:creator
- "Deployment" → /deploy
- "Review" → /war-consul
- "Dokumentieren" → /full-sync

---

## Modus 2: ZIEL — Detailschritte

### Phase Z0: Gefilteter Scan

Gleicher Scan wie A0, aber Ergebnisse durch Fokus-Filter:
- Welche Skills sind fuer dieses Ziel relevant?
- Welche Agents helfen?
- Welche Rules gelten besonders?

### Phase Z1: Kontext klaeren (nur wenn noetig)

> "Ziel: [User-Aussage]. Relevante Skills: [Liste].
> Was genau? (1 Satz)" — NUR fragen wenn wirklich unklar.

### Phase Z2: Plan vorschlagen

```markdown
## Plan: [Ziel]

| Skill | Warum | Aktion |
|-------|-------|--------|
| /deploy | ... | SCP + Build + Update |

### Reihenfolge
1. [Konkreter Skill-Aufruf]
2. ...
3. Verify: [Erfolgskriterium]

Starten?
```

### Phase Z3: Delegieren

Nach Bestaetigung: Skills aufrufen, nicht manuell ausfuehren.

---

## Modus 3: SETUP — Detailschritte

### Phase S0: Projekt scannen

```bash
ls package.json pyproject.toml Cargo.toml go.mod pom.xml *.sln 2>/dev/null
find . -maxdepth 2 -type f \( -name "*.py" -o -name "*.ts" -o -name "*.js" \) | wc -l
ls .git/ 2>/dev/null && echo "GIT" || echo "NO_GIT"
```

### Phase S1: 3 Fragen (max)

1. "Ich sehe: [language]/[framework], [N] Files. Zweck? (1 Satz)"
2. (nur wenn unklar) "Solo / Team / Open Source?"
3. (nur wenn ambig) "Fokus: Code-Qualitaet / Produktivitaet / Beides?"

### Phase S2: Vorschau zeigen (NICHT automatisch schreiben)

```markdown
## Vorgeschlagene Struktur

CLAUDE.md: [erste 10 Zeilen Preview]
.claude/rules/: 01-code-conventions.md, 02-testing.md, ...
.claude/skills/: [basierend auf Projekt-Typ]

Anlegen?
```

### Phase S3: Schreiben (nach "ja")

- CLAUDE.md generieren
- .claude/ Struktur anlegen
- Initiale Skills via meta:creator Pattern
- Statusbar konfigurieren
- `python meta-skills/scripts/validate.py` → 0 Errors

### Phase S4: Verify

> "Setup fertig: [N] Rules, [M] Skills, CLAUDE.md.
> validate.py: 0 Errors.
> Weiter: `/meta-init audit` oder `/meta:creator`"
