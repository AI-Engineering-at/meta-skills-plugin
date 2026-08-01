# M09 — Fehlerkarte

**Art:** Zusammengesetzt

## Zweck

Ein Fehler mit allem, was man zum Handeln braucht — und er bleibt stehen.

## Anatomie — die festen Teile

- Code-Badge (mono, auf `danger.ground`)
- ein Satz Klartext
- Feldtabelle der Fehlerfelder
- Handlungszeile: was jetzt zu tun ist
- **steht dauerhaft**; die Alarm-Variante ist nicht schliessbar
- danger erscheint hier als Fliesstext, weil `danger.ground` der einzige dafuer erlaubte Grund ist

## Zustaende

Quelle: `states.json`, Flaeche `M09-fehlerkarte`. Die Uebersichtstabelle ueber alle
Flaechen erzeugt `scripts/design-states.py --markdown`; hier steht die Begruendung je Zelle.

| Zustand | Wert | Text bzw. Grund |
|---|---|---|
| `idle` | entfaellt | Die Fehlerkarte existiert nur, wenn ein Fehler vorliegt — sie ist die Darstellung von failed, keine eigene Ladeflaeche. |
| `pending` | entfaellt | wie idle. |
| `success` | entfaellt | wie idle. |
| `empty` | entfaellt | wie idle. |
| `partial` | entfaellt | wie idle. |
| `failed` | gezeichnet | Code-Badge mono auf danger-ground + Feldtabelle + was jetzt zu tun ist |
| `unavailable` | entfaellt | Werkzeugluecken traegt M10, nicht die Fehlerkarte — das ist die Kernunterscheidung. |
| `locked` | entfaellt | Verriegelung traegt M08/M02, nicht die Fehlerkarte. |

## Token-Bezug

- `state.danger.ground` + `state.danger.on-ground`
- `font.family.quote` (Code)
- `surface.raised`
- `radius.m`

## Herkunft

Festlegung: Fable 5, `DESIGN-SYSTEM.md`, Abschnitt `bauteil-katalog`.
Diese Datei faltet diese Festlegung aus; sie trifft keine eigene Gestaltungsentscheidung.
