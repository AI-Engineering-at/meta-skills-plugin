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

## LEARNINGS_REGISTRY.md aktualisieren

**Pfad:** `.claude/knowledge/LEARNINGS_REGISTRY.md`

Wenn neue Learnings identifiziert wurden:
- Lies die letzte L-ID: `grep "^| L" .claude/knowledge/LEARNINGS_REGISTRY.md | tail -1`
- Wenn keine L-IDs vorhanden (leere Datei oder nicht existent), starte mit L-001
- Format: `| L-XXX | [Learning] | [Session-Datum] | [Quelle] |` (3 Ziffern, zero-padded)

## Session-Report speichern

**Pfad:** `docs/reports/session-retrospective-YYYY-MM-DD.md`

Pruefe ob fuer das Datum schon ein Report existiert:
```
docs/reports/session-retrospective-YYYY-MM-DD*.md
```
Wenn ja, haenge `-2`, `-3` etc. an den Dateinamen. Datei mit dem vollstaendigen Review-Inhalt (gemaess review-template.md) erstellen.
