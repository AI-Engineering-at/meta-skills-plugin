# M12 — Zitatblock

**Art:** Flaeche

## Zweck

Woertliches: Kommando, Ausgabe, Geraetetext. Nichts davon wird umformuliert.

## Anatomie — die festen Teile

- `surface.sunken`
- Etikett + Lesezeit
- eigener `overflow-x`-Container
- mono
- **leer** heisst „Quelle stumm“ und ist ein Erfolg, kein Fehler
- **gekuerzt** nennt die Byte-Angabe

## Zustaende

Quelle: `states.json`, Flaeche `M12-zitatblock`. Die Uebersichtstabelle ueber alle
Flaechen erzeugt `scripts/design-states.py --markdown`; hier steht die Begruendung je Zelle.

| Zustand | Wert | Text bzw. Grund |
|---|---|---|
| `idle` | offen | — |
| `pending` | offen | — |
| `success` | gezeichnet | vorhanden — surface.sunken, Etikett + Lesezeit, mono |
| `empty` | gezeichnet | leer — Quelle stumm (Erfolgssprache, nicht Fehler) |
| `partial` | gezeichnet | gekuerzt — mit Byte-Angabe |
| `failed` | offen | — |
| `unavailable` | offen | — |
| `locked` | offen | — |

## Token-Bezug

- `surface.sunken`
- `font.family.quote`
- `font.size.t12`

## Herkunft

Festlegung: Fable 5, `DESIGN-SYSTEM.md`, Abschnitt `bauteil-katalog`.
Diese Datei faltet diese Festlegung aus; sie trifft keine eigene Gestaltungsentscheidung.
