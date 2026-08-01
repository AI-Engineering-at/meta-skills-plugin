# M13 — Alarmband

**Art:** Flaeche

## Zweck

Die staerkste Aussage der Oberflaeche. Hoechstens eine pro Bildschirm.

## Anatomie — die festen Teile

- `danger.ground` + `danger.on-ground`
- Marke (M07) + Wort
- `role="alert"`
- **max. 1 pro Bildschirm**
- bleibt bis Sitzungsende
- Deshalb ist der Alarmfall ein *Band mit eigenem Grund* und nicht rote Schrift: `danger` misst dunkel 4.58:1 und liegt damit unter der Hausreserve von 5.0.

## Zustaende

Quelle: `states.json`, Flaeche `M13-alarmband`. Die Uebersichtstabelle ueber alle
Flaechen erzeugt `scripts/design-states.py --markdown`; hier steht die Begruendung je Zelle.

| Zustand | Wert | Text bzw. Grund |
|---|---|---|
| `idle` | entfaellt | Das Alarmband erscheint nur im Alarmfall — es ist die staerkste Darstellung von failed, keine eigene Ladeflaeche. |
| `pending` | entfaellt | wie idle. |
| `success` | entfaellt | wie idle. |
| `empty` | entfaellt | wie idle. |
| `partial` | entfaellt | wie idle. |
| `failed` | gezeichnet | danger.ground + danger.on-ground, Marke + Wort, role=alert, bleibt bis Sitzungsende |
| `unavailable` | entfaellt | wie idle. |
| `locked` | entfaellt | wie idle. |

## Token-Bezug

- `state.danger.ground` + `state.danger.on-ground`
- `density.band`
- `font.size.t22`

## Herkunft

Festlegung: Fable 5, `DESIGN-SYSTEM.md`, Abschnitt `bauteil-katalog`.
Diese Datei faltet diese Festlegung aus; sie trifft keine eigene Gestaltungsentscheidung.
