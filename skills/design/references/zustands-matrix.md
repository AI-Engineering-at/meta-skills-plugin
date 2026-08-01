# Die Zustands-Matrix

## Acht Zustaende — sechs geerbt, zwei ergaenzt

| Zustand | Definition | Abnahmekriterium |
|---|---|---|
| `idle` | noch nichts angefordert | nennt, **was** passieren wird und **wer** es ausloest |
| `pending` | Anfrage laeuft | nennt was + seit wann; statische Skelettzeilen |
| `success` | Daten da | Inhalt **+ Herkunftszeile** |
| `empty` | erfolgreich, Ergebnis leer — **ein Erfolg** | Erfolgssprache, Neutralfarbe, nie „Fehler" |
| `partial` | Teil da, Teil fehlt | Zaehlung `n/m`; eigener Zustand, kein Fehler |
| `failed` | Anfrage gescheitert | Code + Felder + Klartext + Handlungszeile; **bleibt stehen** |
| `unavailable` | Luecke des **Werkzeugs** | M10-Muster; kein Bedienelement darin |
| `locked` | strukturell verweigert | Schraffur + Wort + Grund; kein `<button>`, kein Fokus |

Die ersten sechs stammen woertlich aus dem Bestands-Skill `async-state-coverage`.
**Kein zweites Vokabular erfunden** — sonst haette das Haus zwei Zustandssprachen und
zwei Audit-Laeufe.

## Die Kernunterscheidung

`empty`, `unavailable` und `locked` sind **drei verschiedene Wahrheiten** und sehen
dreimal anders aus:

- `empty` — wir haben nachgesehen, es ist nichts da. **Das ist ein Erfolg.**
- `unavailable` — wir konnten nicht nachsehen, weil uns das Werkzeug fehlt.
- `locked` — wir duerfen nicht nachsehen.

Die meisten Systeme treffen diese Unterscheidung nicht und zeigen dreimal dieselbe leere
Tabelle. Wer das tut, behauptet im Fall `unavailable` faelschlich, es gebe nichts.

## Die Enumerationsregel

Eine **Flaeche** = eine Region mit eigener Datenquelle oder eigener Anforderung.
Mechanisch: **eine Zeile je Lade-/Abfrage-Aufrufstelle**, plus jede Flaeche an einem
Push-Strom.

Diese Regel fehlte in allen drei Ausgangsentwuerfen. Sie zaehlten 12, 15 und 13 Flaechen
fuer dieselbe Anwendung — die Differenz war reiner Schnitt, und keine Spezifikation nannte,
wonach geschnitten wurde.

## Genau drei Zellwerte

| Wert | Braucht | Bedeutet |
|---|---|---|
| `gezeichnet` | `text` | im Schaustueck sichtbar gebaut, mit dem exakten angezeigten Text |
| `entfaellt` | `grund` | trifft kategorisch nicht zu |
| `offen` | — | ehrlich unentschieden |

Ein vierter Wert ist ein Fehler. **`entfaellt` ohne Grund ist ein Fehler** — sonst waere
es die bequeme Tuer, durch die jede Luecke verschwindet.

## Abdeckung

```
Abdeckung   = gezeichnet / (Zellen - entfaellt)
vollstaendig ⇔ offen == 0
```

Gemessen am Haus-System: **15 Flaechen, 120 Zellen, 53 gezeichnet, 54 entfaellt mit Grund,
13 offen → 80,3 %.** Nicht vollstaendig, und das steht so in `STATUS.md`. Eine auf 100 %
geschoenter Matrix waere wertlos.

## Die Datei ist die Quelle, die Tabelle ist die Projektion

`design-system/states.json` ist maschinenlesbar; die Markdown-Tabelle erzeugt
`scripts/design-states.py --markdown`. Dieselbe Mechanik wie Token → CSS.

Der Grund ist gemessen: Entwurf C erklaerte in seiner Spezifikation **7** Zustaende und
implementierte im CSS **5**. Entwurf B implementierte 6. Prosa und Umsetzung waren
auseinander, und nichts merkte es.

## Was diese Matrix NICHT kann — ehrlich

Das Abdeckungsmass rechnet ueber die **eingetragenen** Flaechen. **Eine vergessene Flaeche
faellt nicht auf.** Die Enumerationsregel steht geschrieben; ihre Durchsetzung braucht je
Sprache einen eigenen Zaehler ueber die Aufrufstellen, und der existiert nicht.
Benannt, nicht geloest.
