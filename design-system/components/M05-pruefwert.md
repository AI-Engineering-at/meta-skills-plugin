# M05 — Kopierbarer Pruefwert

**Art:** Primitive

## Zweck

Ein Digest oder Fingerabdruck, den man vergleichen und kopieren koennen muss.

## Anatomie — die festen Teile

- 64 Hex in **8 Gruppen zu 8**, mono, tabular; Umbruch nur an Gruppengrenzen
- Kopiertaste je Wert
- Herkunftszeile (M06) darunter
- eigener `overflow-x`-Container
- **mismatch**: beide Werte voll zeigen + Lawinensatz — ausdruecklich **kein Zeichen-Diff**, weil ein Ein-Byte-Unterschied den ganzen Wert aendert
- **file missing** ist ausdruecklich **kein** mismatch

## Zustaende

Quelle: `states.json`, Flaeche `M05-pruefwert`. Die Uebersichtstabelle ueber alle
Flaechen erzeugt `scripts/design-states.py --markdown`; hier steht die Begruendung je Zelle.

| Zustand | Wert | Text bzw. Grund |
|---|---|---|
| `idle` | gezeichnet | not checked — neutral, behauptet nichts |
| `pending` | offen | — |
| `success` | gezeichnet | verified — Digest in 8x8-Gruppen + Herkunftszeile |
| `empty` | entfaellt | Ein Pruefwert ist da oder nicht. 'Leerer Hash' gibt es nicht — der Fall heisst 'file missing' und ist unter unavailable gezeichnet. |
| `partial` | entfaellt | Ein Digest ist ganz oder falsch. Ein Teil-Digest waere eine Aussage, die es nicht gibt (Lawineneffekt). |
| `failed` | gezeichnet | mismatch — beide Werte voll, Lawinensatz, KEIN Zeichen-Diff |
| `unavailable` | gezeichnet | file missing — ausdruecklich KEIN mismatch |
| `locked` | offen | — |

## Token-Bezug

- `font.family.quote`
- `surface.sunken`
- `state.ok.base` / `state.danger.base` / `state.neutral.base`

## Herkunft

Festlegung: Fable 5, `DESIGN-SYSTEM.md`, Abschnitt `bauteil-katalog`.
Diese Datei faltet diese Festlegung aus; sie trifft keine eigene Gestaltungsentscheidung.
