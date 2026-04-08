---
name: feedback
description: >
  Bidirektionaler End-of-Session Review — Feedback fuer BEIDE Seiten (AI und User).
  Analysiert Missverstaendnisse, gibt ehrliches Feedback, aktualisiert USER_PATTERNS.md.
  Trigger: "feedback-loop", "session feedback", "was habe ich falsch gemacht",
  "gib mir feedback", "session review", "retrospektive", "wie war die session"
model: sonnet
allowed-tools: [Read, Grep, Glob, Write, Edit, Bash]
user-invocable: true
version: 1.0.0
type: meta
cooperative: true
created-with: meta:creator v0.1.0
token-budget: 12000
category: meta
requires: []
produces: [session-retrospective, user-patterns-update, learnings-update]
last-verified: 2026-04-07
---

# meta:feedback — Bidirektionaler Session Review

> **Kern-Prinzip:** Feedback ist keine Kritik. Feedback sagt "X hat nicht funktioniert, versuch naechstes Mal Y."
> Kritik sagt "X war schlecht." Der Unterschied ist die Loesung.

## Wann verwenden?

- Am Ende einer langen Session (manuell: `/feedback`)
- Nach 3+ Missverstaendnissen — proaktiv vorschlagen (nicht erzwingen)
- Vor `/compact` — Feedback als Teil der Zusammenfassung
- Wenn der User fragt: "Was habe ich falsch gemacht?" oder "Gib mir Feedback"

## Schritt 1: Session analysieren

Gehe den bisherigen Konversationsverlauf chronologisch durch. Identifiziere:

1. **Missverstaendnisse** — Wo hat die AI etwas anders verstanden als der User meinte?
2. **Korrektionen** — Wo hat der User die AI korrigiert? Was war die Root Cause?
3. **Zeitverschwendung** — Welche Aktionen haben nichts gebracht?
4. **Durchbrueche** — Was hat besonders gut funktioniert?
5. **Implizite Annahmen** — Was hat der User vorausgesetzt ohne es auszusprechen?

## Schritt 2: Feedback generieren

Erstelle den Review gemaess dem vollstaendigen Template:

```bash
# Fuer das vollstaendige Review-Format mit Tabellenstruktur:
cat "${CLAUDE_PLUGIN_ROOT}/skills/feedback/references/review-template.md"
```

Kurz-Struktur: Missverstaendnisse-Tabelle | Feedback an AI | Feedback an User | Muster | Vorgeschlagene Aenderungen.

## Schritt 3: User bestaetigen lassen

Zeige den Review und frage:
> "Stimmt diese Analyse? Soll ich die vorgeschlagenen Aenderungen an USER_PATTERNS.md und LEARNINGS_REGISTRY.md durchfuehren?"

Warte auf Bestaetigung. NICHT automatisch aendern.

## Schritt 4: Persistieren (nur nach Bestaetigung)

Fuer vollstaendige Persistenz-Anleitung (Pfade, Edge Cases, Create-If-Missing):

```bash
# Vollstaendige Anleitung mit allen Pfaden und Edge Cases:
cat "${CLAUDE_PLUGIN_ROOT}/skills/feedback/references/persistence-guide.md"
```

Kurz: USER_PATTERNS.md + LEARNINGS_REGISTRY.md updaten, Session-Report unter `docs/reports/` speichern.

## Schritt 5: Zusammenfassung

Poste eine Kurzfassung:
> "Feedback-Loop fertig. [N] Missverstaendnisse dokumentiert, [M] neue Patterns in USER_PATTERNS.md, [K] neue Learnings. Wichtigster Tipp fuer dich: [Tipp]. Wichtigster Tipp fuer mich: [Tipp]."
