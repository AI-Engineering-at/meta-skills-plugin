# M04 — Ereignisstrom

**Art:** Flaeche

## Zweck

Fortlaufende Ereignisse — mit einer permanenten Aussage darueber, was der Strom NICHT sieht.

## Anatomie — die festen Teile

- Zeitspalte, `tabular-nums`
- Filtermatrix Kategorie x Level **mit sichtbaren Nullen** — eine Null ist eine Zahl, keine Farbe
- permanente **Deckungszeile**: was der Strom sieht und was nicht
- Kategorie ohne Emitter wird als Strich-Marke + `0` gezeichnet, nicht weggelassen

## Zustaende

Quelle: `states.json`, Flaeche `M04-ereignisstrom`. Die Uebersichtstabelle ueber alle
Flaechen erzeugt `scripts/design-states.py --markdown`; hier steht die Begruendung je Zelle.

| Zustand | Wert | Text bzw. Grund |
|---|---|---|
| `idle` | offen | — |
| `pending` | offen | — |
| `success` | gezeichnet | Liste mit Zeitspalte (tabular) und Deckungszeile |
| `empty` | gezeichnet | leer / Filter leer — Erfolgssprache, sichtbare Nullen |
| `partial` | gezeichnet | Kategorie ohne Emitter: Strich-Marke + 0 |
| `failed` | gezeichnet | Listener verloren |
| `unavailable` | gezeichnet | Deckungszeile nennt, was der Strom NICHT sieht |
| `locked` | offen | — |

## Token-Bezug

- `font.family.quote` + `tabular-nums` (Zeitspalte)
- `density.row-dense`
- `ink.tertiary` (Strich-Marke)
- `line.quiet` (Zeilentrenner)

## Herkunft

Festlegung: Fable 5, `DESIGN-SYSTEM.md`, Abschnitt `bauteil-katalog`.
Diese Datei faltet diese Festlegung aus; sie trifft keine eigene Gestaltungsentscheidung.
