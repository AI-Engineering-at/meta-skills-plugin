# M02 — Aktion mit Vorbedingungen

**Art:** Zusammengesetzt

## Zweck

Eine ausloesbare Handlung samt allem, was ihr im Weg steht — bevor jemand klickt.

## Anatomie — die festen Teile

- Titel + Konsequenzklassen-Chip (M08)
- Vorbedingungsliste; **je Zeile der Fehlercode, der sonst floege**
- Konsequenz woertlich + Groesse
- Taste mit dem Satz, *was sie freischalten wuerde*
- Die Konsequenz-Taste ist akzentgefuellt (bedienbar) mit `border.strong`-Kante in attention (kostet eine Entscheidung) — **nie zustandsgefuellt**

## Zustaende

Quelle: `states.json`, Flaeche `M02-handlungskarte`. Die Uebersichtstabelle ueber alle
Flaechen erzeugt `scripts/design-states.py --markdown`; hier steht die Begruendung je Zelle.

| Zustand | Wert | Text bzw. Grund |
|---|---|---|
| `idle` | gezeichnet | Vorbedingungen noch nicht geprueft |
| `pending` | gezeichnet | Vorbedingungen werden geprueft |
| `success` | gezeichnet | alle Vorbedingungen erfuellt, Taste frei |
| `empty` | gezeichnet | nichts zu tun — Erfolg, kein Fehler |
| `partial` | gezeichnet | Teil der Vorbedingungen erfuellt (n/m) |
| `failed` | gezeichnet | Fehlercode je gerissener Vorbedingung |
| `unavailable` | gezeichnet | Werkzeug fehlt — M10-Muster in der Karte |
| `locked` | gezeichnet | verriegelt: Text mit Grund, kein <button> |

## Token-Bezug

- `interactive.accent` + `interactive.on-accent` (Taste)
- `state.attention.base` (Kante der Konsequenz-Taste)
- `surface.raised` (Karte)
- `radius.m`
- `space.3` / `space.4`

## Herkunft

Festlegung: Fable 5, `DESIGN-SYSTEM.md`, Abschnitt `bauteil-katalog`.
Diese Datei faltet diese Festlegung aus; sie trifft keine eigene Gestaltungsentscheidung.
