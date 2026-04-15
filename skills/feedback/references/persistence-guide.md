# Persistence Guide — Schritt 4 Detail

Alle Pfade relativ zum phantom-ai Repo-Root. Nur ausfuehren nach User-Bestaetigung.

## USER_PATTERNS.md aktualisieren

**Pfad:** `.claude/knowledge/USER_PATTERNS.md`

Wenn die Datei nicht existiert, erstelle sie mit diesem Basis-Template:
```markdown
# User Patterns — Kommunikationsstil
> Bidirektionales Lernen: AI lernt User, User lernt AI.
> Aktualisiert: [Datum]

## Wenn User sagt → Er meint
| Ausdruck | Bedeutung | Kontext |
|----------|-----------|---------|

## Positive Patterns
| Was | Kontext | Session |
|-----|---------|---------|
```

Wenn die Datei existiert:
- Neue "Wenn User sagt → Er meint" Eintraege in die Tabelle einfuegen
- Neue "Positive Patterns" wenn etwas gut funktioniert hat
- Datum im Header aktualisieren

## LEARNINGS.md aktualisieren (CANONICAL — nicht LEARNINGS_REGISTRY.md!)

**Pfad:** `.claude/knowledge/LEARNINGS.md`

> ACHTUNG: LEARNINGS_REGISTRY.md ist DEPRECATED (Duplikat). Alle neuen Learnings nach LEARNINGS.md.
> Gleiches gilt fuer ERRORS.md (nicht ERROR_REGISTRY.md).
> Siehe: meta-skills/skills/knowledge/SKILL.md fuer das Knowledge-Funnel-Konzept.

Wenn neue Learnings identifiziert wurden:
- Letzte L-Nummer: `grep -oP "L\d+" .claude/knowledge/LEARNINGS.md | sort -t'L' -k1 -n | tail -1`
- Format:
  ```
  ### L{NNN} — {Kurztitel}
  **Was:** {Pattern}
  **Richtig:** {Was tun}
  **Falsch:** {Was vermeiden}
  **Session:** {Datum}
  ```

## Session-Report speichern

**Pfad:** `docs/reports/session-retrospective-YYYY-MM-DD.md`

Pruefe ob fuer das Datum schon ein Report existiert:
```
docs/reports/session-retrospective-YYYY-MM-DD*.md
```
Wenn ja, haenge `-2`, `-3` etc. an den Dateinamen. Datei mit dem vollstaendigen Review-Inhalt (gemaess review-template.md) erstellen.
