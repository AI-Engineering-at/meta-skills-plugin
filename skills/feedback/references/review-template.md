# Review Template — Vollstaendiges Feedback-Format

Erstelle den Review in diesem exakten Format:

```markdown
# Session Feedback — [Datum]

## Missverstaendnisse (Top 3-5)

> Wenn 0 Missverstaendnisse: schreibe "Keine Missverstaendnisse identifiziert." und ueberspringe die Tabelle.

| # | User sagte | AI verstand | Gemeint war | Tipp fuer naechstes Mal |
|---|-----------|-------------|-------------|------------------------|
| 1 | "[Zitat]" | [Interpretation] | [Tatsaechliche Bedeutung] | "[Bessere Formulierung]" |

## Feedback an die AI
- [Konkreter Punkt mit Beispiel aus dieser Session]
- [Konkreter Punkt mit Beispiel aus dieser Session]

## Feedback an den User
- [Konkreter Punkt MIT Loesung — nie ohne Loesung]
- [Konkreter Punkt MIT Loesung — nie ohne Loesung]

## Muster die funktioniert haben
- [Was beibehalten werden soll]

## Vorgeschlagene Aenderungen
- [ ] USER_PATTERNS.md: [Neuer Eintrag]
- [ ] LEARNINGS_REGISTRY.md: [Neues Learning L-XXX]
- [ ] CLAUDE.md/Rules: [Regel-Aenderung wenn noetig]
```

## Regeln fuer das Feedback

### Feedback an die AI
- Konkrete Entscheidung oder Aktion benennen (was genau wurde falsch gemacht)
- Root Cause, nicht Symptom
- Was haette ich stattdessen tun sollen?

### Feedback an den User
- IMMER mit Loesung — nie "das war unklar" ohne "sag stattdessen X"
- Respektvoll aber ehrlich — der User hat den Skill BEWUSST aufgerufen, er WILL das Feedback
- Maximal 5 Punkte — die wichtigsten, nicht alle

### Missverstaendnisse
- Nur echte Missverstaendnisse, nicht "AI hat Fehler gemacht"
- Immer mit konkretem Zitat aus der Session
- Tipp-Spalte ist PFLICHT — ohne Tipp ist es Kritik, nicht Feedback
