# M03 — Bestaetigung mit Konsequenz

**Art:** Zusammengesetzt

## Zweck

Der letzte Halt vor einer folgenreichen Aktion. Er zeigt, was *genau* gesendet wird.

## Anatomie — die festen Teile

- Zitat → **exakte Nutzlast vor der Taste**, in der groessten Auszeichnung der Flaeche
- Zeitbudget
- zwei Tasten ungleichen Gewichts
- Esc = nichts senden
- Fokusfalle + Fokusrueckgabe an den Ausloeser
- In jedem Ausgang, der nichts gesendet hat, steht **„nothing was sent“** fett. Abgelaufen und Fehler sind zwei eigene Zustaende, nicht einer.

## Zustaende

Quelle: `states.json`, Flaeche `M03-bestaetigung`. Die Uebersichtstabelle ueber alle
Flaechen erzeugt `scripts/design-states.py --markdown`; hier steht die Begruendung je Zelle.

| Zustand | Wert | Text bzw. Grund |
|---|---|---|
| `idle` | gezeichnet | nicht offen |
| `pending` | gezeichnet | offen, Zeitbudget laeuft |
| `success` | entfaellt | Der Dialog zeigt keinen Erfolg — er uebergibt an die ausloesende Flaeche. Ein Erfolgszustand im Dialog waere eine zweite Wahrheit ueber denselben Vorgang. |
| `empty` | entfaellt | Ein Bestaetigungsdialog ohne Nutzlast wird nicht geoeffnet. 'Leer' ist hier kein Zustand, sondern ein Aufrufsfehler. |
| `partial` | entfaellt | Die Nutzlast wird woertlich und vollstaendig gezeigt oder gar nicht — eine halbe Konsequenz waere die gefaehrlichste Anzeige des Systems. |
| `failed` | gezeichnet | Fehler — 'nothing was sent' fett |
| `unavailable` | gezeichnet | abgelaufen — 'nothing was sent' als eigener Zustand |
| `locked` | offen | — |

## Token-Bezug

- `surface.raised` (Dialog)
- `font.size.t18` / `t22` fuer die Nutzlast
- `state.attention.*` (Zeitbudget)
- `state.danger.ground` + `state.danger.on-ground` (Fehlerausgang)
- `focus.width` / `focus.offset`

## Herkunft

Festlegung: Fable 5, `DESIGN-SYSTEM.md`, Abschnitt `bauteil-katalog`.
Diese Datei faltet diese Festlegung aus; sie trifft keine eigene Gestaltungsentscheidung.
