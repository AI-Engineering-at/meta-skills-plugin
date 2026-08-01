# M10 — Fehlstellen-Rahmen

**Art:** Muster

## Zweck

Die ehrliche Leere: hier gibt es etwas nicht, und zwar aus einem benennbaren Grund.

## Anatomie — die festen Teile

- gestrichelte Kante rundum
- Chip (M08) `NOT AVAILABLE`
- **was fehlt** in Produktsprache
- **was es braeuchte** in Entwicklersprache
- **kein klickbares Element darin** — eine Luecke bietet nichts an
- Das ist der Zustand `unavailable` in gezeichneter Form. Ihn mit `empty` zu verwechseln ist genau der Fehler, den dieses Muster verhindert.

## Zustaende

Quelle: `states.json`, Flaeche `M10-fehlstellen-rahmen`. Die Uebersichtstabelle ueber alle
Flaechen erzeugt `scripts/design-states.py --markdown`; hier steht die Begruendung je Zelle.

| Zustand | Wert | Text bzw. Grund |
|---|---|---|
| `idle` | entfaellt | M10 IST der Zustand unavailable in gezeichneter Form; andere Zustaende hat er per Konstruktion nicht. |
| `pending` | entfaellt | wie idle. |
| `success` | entfaellt | wie idle. |
| `empty` | entfaellt | wie idle — und die Verwechslung mit empty ist genau der Fehler, den M10 verhindert. |
| `partial` | entfaellt | wie idle. |
| `failed` | entfaellt | wie idle — eine Werkzeugluecke ist kein Fehler. |
| `unavailable` | gezeichnet | gestrichelte Kante, Chip, 'was fehlt' (Produktsprache) + 'was es braeuchte' (Entwicklersprache), kein klickbares Element |
| `locked` | entfaellt | Verriegelung ist eine Entscheidung, keine Luecke — sie traegt M08. |

## Token-Bezug

- `state.neutral.*`
- `line.control`, gestrichelt
- `ink.secondary`

## Herkunft

Festlegung: Fable 5, `DESIGN-SYSTEM.md`, Abschnitt `bauteil-katalog`.
Diese Datei faltet diese Festlegung aus; sie trifft keine eigene Gestaltungsentscheidung.
