# M07 — Erkenntnisgrad-Marke

**Art:** Primitive

## Zweck

Die zweite Kodierung: eine 8-px-Form, die den Erkenntnisgrad ohne Farbe traegt.

## Anatomie — die festen Teile

- voll — beobachtet, woertlich gelesen
- halb — abgeleitet, berechnet oder klassifiziert
- hohl — unbekannt, keine Aussage
- Strich — nicht pruefbar, kein Vergleichswert
- schraffiert (45 Grad) — gesperrt, nie fokussierbar
- gestrichelt — nicht verfuegbar, Luecke des Werkzeugs
- reines CSS, `currentColor`, kein Icon-Set, kein Bild
- **nie unter 8 px** — darunter wird die Schraffur zu Grau (Risiko 4). Ein Kontrast-Test faengt das nicht, nur Sichtpruefung.

## Zustaende

Quelle: `states.json`, Flaeche `M07-erkenntnisgrad-marke`. Die Uebersichtstabelle ueber alle
Flaechen erzeugt `scripts/design-states.py --markdown`; hier steht die Begruendung je Zelle.

| Zustand | Wert | Text bzw. Grund |
|---|---|---|
| `idle` | entfaellt | Primitive ohne eigene Datenquelle: die Marke KODIERT einen Zustand, sie hat keinen. |
| `pending` | entfaellt | wie idle — die Marke ist die Anzeige, nicht der Anzeigende. |
| `success` | entfaellt | wie idle. |
| `empty` | entfaellt | wie idle. |
| `partial` | entfaellt | wie idle. |
| `failed` | entfaellt | wie idle. |
| `unavailable` | entfaellt | wie idle. |
| `locked` | entfaellt | wie idle. |

## Token-Bezug

- `currentColor`
- 8 px feste Groesse
- `ink.tertiary` fuer den Strich

## Herkunft

Festlegung: Fable 5, `DESIGN-SYSTEM.md`, Abschnitt `bauteil-katalog`.
Diese Datei faltet diese Festlegung aus; sie trifft keine eigene Gestaltungsentscheidung.
