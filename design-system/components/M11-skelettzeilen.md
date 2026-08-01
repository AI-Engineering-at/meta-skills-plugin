# M11 — Skelettzeilen

**Art:** Primitive

## Zweck

Der Ladezustand, ohne zu flackern.

## Anatomie — die festen Teile

- statische Balken in der **Ergebnis-Zeilenhoehe**
- **kein Schimmern, keine Animation**
- Anzahl = erwartete Zeilen — das Skelett verspricht die Menge, die kommt

## Zustaende

Quelle: `states.json`, Flaeche `M11-skelettzeilen`. Die Uebersichtstabelle ueber alle
Flaechen erzeugt `scripts/design-states.py --markdown`; hier steht die Begruendung je Zelle.

| Zustand | Wert | Text bzw. Grund |
|---|---|---|
| `idle` | entfaellt | M11 IST der Zustand pending in gezeichneter Form. |
| `pending` | gezeichnet | statische Balken in Ergebnis-Zeilenhoehe, Anzahl = erwartete Zeilen |
| `success` | entfaellt | wie idle. |
| `empty` | entfaellt | wie idle. |
| `partial` | entfaellt | wie idle. |
| `failed` | entfaellt | wie idle. |
| `unavailable` | entfaellt | wie idle. |
| `locked` | entfaellt | wie idle. |

## Token-Bezug

- `density.row`
- `surface.raised`
- `motion.none` (ausdruecklich)

## Herkunft

Festlegung: Fable 5, `DESIGN-SYSTEM.md`, Abschnitt `bauteil-katalog`.
Diese Datei faltet diese Festlegung aus; sie trifft keine eigene Gestaltungsentscheidung.
