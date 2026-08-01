# M14 — Systemblatt / Legende

**Art:** Meta

## Zweck

Erklaert Farbe, Form, Klasse und Taste **im Produkt** — nicht in einer Doku daneben.

## Anatomie — die festen Teile

- Farbrollen mit Bedeutung
- die sechs Marken (M07)
- die Konsequenzklassen (M08)
- die Tastaturwege
- **Pflichtbestandteil** — ohne ihn bleibt die zweite Kodierung ungelernt und traegt nichts

## Zustaende

Quelle: `states.json`, Flaeche `M14-systemblatt`. Die Uebersichtstabelle ueber alle
Flaechen erzeugt `scripts/design-states.py --markdown`; hier steht die Begruendung je Zelle.

| Zustand | Wert | Text bzw. Grund |
|---|---|---|
| `idle` | entfaellt | Statische Erklaerflaeche ohne Datenquelle — sie erklaert die Zustaende, sie hat keine. |
| `pending` | entfaellt | wie idle. |
| `success` | gezeichnet | statische Legende; Pflichtbestandteil, sonst bleibt die zweite Kodierung ungelernt |
| `empty` | entfaellt | wie idle. |
| `partial` | entfaellt | wie idle. |
| `failed` | entfaellt | wie idle. |
| `unavailable` | entfaellt | wie idle. |
| `locked` | entfaellt | wie idle. |

## Token-Bezug

- alle Rollen-Token
- `font.size.t11`

## Herkunft

Festlegung: Fable 5, `DESIGN-SYSTEM.md`, Abschnitt `bauteil-katalog`.
Diese Datei faltet diese Festlegung aus; sie trifft keine eigene Gestaltungsentscheidung.
