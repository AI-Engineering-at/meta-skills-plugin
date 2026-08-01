# M08 — Klassen-Chip

**Art:** Primitive

## Zweck

Konsequenzklasse als Farbe + Form + Wort. Drei Kodierungen, damit keine allein traegt.

## Anatomie — die festen Teile

- `READY` — rund, ok
- `GATED` — eckig, attention
- `BLOCKED` — schraffiert, quadratisch, **nicht fokussierbar**
- `NOT AVAILABLE` — gestrichelt
- **nie ein `<button>`** — ein Chip ist eine Aussage, kein Bedienelement
- kein Emoji, keine Fremdschrift, kein Bild

## Zustaende

Quelle: `states.json`, Flaeche `M08-klassen-chip`. Die Uebersichtstabelle ueber alle
Flaechen erzeugt `scripts/design-states.py --markdown`; hier steht die Begruendung je Zelle.

| Zustand | Wert | Text bzw. Grund |
|---|---|---|
| `idle` | entfaellt | Primitive: der Chip kodiert eine Konsequenzklasse, er laedt nichts. |
| `pending` | entfaellt | wie idle. |
| `success` | gezeichnet | READY — rund, ok |
| `empty` | entfaellt | wie idle. |
| `partial` | gezeichnet | GATED — eckig, attention |
| `failed` | entfaellt | wie idle. |
| `unavailable` | gezeichnet | NOT AVAILABLE — gestrichelt |
| `locked` | gezeichnet | BLOCKED — schraffiert, quadratisch, nicht fokussierbar |

## Token-Bezug

- `state.ok.*` / `state.attention.*` / `state.neutral.*`
- `radius.s`
- `line.control` (Kontur)
- `font.size.t10`, Versalien

## Herkunft

Festlegung: Fable 5, `DESIGN-SYSTEM.md`, Abschnitt `bauteil-katalog`.
Diese Datei faltet diese Festlegung aus; sie trifft keine eigene Gestaltungsentscheidung.
