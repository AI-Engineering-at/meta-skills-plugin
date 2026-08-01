# M06 — Herkunftszeile

**Art:** Primitive

## Zweck

Drei Zellen unter jedem Wert: woher · wann · geprueft. Sichtbar, nie ein Tooltip.

## Anatomie — die festen Teile

- `woher` · `wann` · `geprueft`
- 11 px mono
- **sichtbar, nie Tooltip** — eine Herkunft, die man suchen muss, ist keine
- traegt die Erkenntnisgrad-Marke (M07)

## Zustaende

Quelle: `states.json`, Flaeche `M06-herkunftszeile`. Die Uebersichtstabelle ueber alle
Flaechen erzeugt `scripts/design-states.py --markdown`; hier steht die Begruendung je Zelle.

| Zustand | Wert | Text bzw. Grund |
|---|---|---|
| `idle` | gezeichnet | nicht erfasst — hohle Marke |
| `pending` | entfaellt | Die Herkunftszeile beschreibt einen vorliegenden Wert. Waehrend der Anfrage gibt es keinen Wert, dessen Herkunft sie behaupten koennte. |
| `success` | gezeichnet | beobachtet (volle Marke) / Datei — woher, wann, geprueft |
| `empty` | entfaellt | Sie ist ein Anhaengsel an einen Wert, keine eigene Flaeche mit eigener Abfrage. |
| `partial` | gezeichnet | abgeleitet — halbe Marke (berechnet/klassifiziert) |
| `failed` | offen | — |
| `unavailable` | gezeichnet | Strich-Marke: nicht pruefbar, kein Vergleichswert |
| `locked` | offen | — |

## Token-Bezug

- `font.size.t11`
- `font.family.quote`
- `ink.secondary`

## Herkunft

Festlegung: Fable 5, `DESIGN-SYSTEM.md`, Abschnitt `bauteil-katalog`.
Diese Datei faltet diese Festlegung aus; sie trifft keine eigene Gestaltungsentscheidung.
