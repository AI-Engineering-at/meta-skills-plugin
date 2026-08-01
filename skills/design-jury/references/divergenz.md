# Divergenz erzwingen

## Warum ueberhaupt

Der teuerste Fehlerfall des Verfahrens ist nicht ein schlechter Entwurf — es sind **drei
Varianten desselben Gedankens**. Man waehlt eine, nennt es eine Entscheidung, und hat in
Wahrheit nie eine Alternative gehabt.

Modelle konvergieren ohne Zwang. Sie bekommen denselben Kontext, dieselben Belege,
dieselbe Sprache — und produzieren dieselbe Loesung in drei Farben.

## Sperre 1 (P2): deklariert — bricht hart

`02-rahmungen.json` fuehrt eine Achsenmatrix:

```json
{
  "entwuerfe": [
    { "id": "A", "these": "…", "achsen": { "farbrolle": "…", "dichte": "…",
      "modus": "…", "zweitkodierung": "…", "grundmetapher": "…" } }
  ]
}
```

**Gate:** fuer jedes Paar (A,B), (A,C), (B,C) muessen sich **mindestens 2** Achsenwerte
unterscheiden. Und K ≥ 3 — zwei Entwuerfe sind eine Alternative, keine Divergenz.

Reine Zeichenkettenrechnung. Hart pruefbar, deshalb hart geprueft:
`design-divergence.py --rahmungen … --ci` endet mit 1.

**Die Achsen sind generisch und wertfrei.** Welche Werte sie annehmen koennen, legt
Fable 5 fest — das ist eine gestalterische Entscheidung, keine strukturelle.

## Sperre 2 (P4): gemessen — NUR-MESSEN

Deklarierte Verschiedenheit, die sich nicht messen laesst, ist keine.

Gerechnet wird ueber `04-messung.json`: Jaccard-Abstand der Palettenmengen, Differenz der
distinkten Schriftgroessen, Spaltenzahl, Radienmenge.

**Es gibt keinen Schwellwert.** Drei Entwuerfe eines einzigen Tages sind keine Verteilung.
Eine heute erfundene Zahl waere genau der Platzhalter, den A33 verbietet — und sie waere
schlimmer als keine, weil sie zukuenftig richtige Entwuerfe ablehnen wuerde.

Deshalb: der Abstand wird **berechnet, protokolliert und angezeigt**. Nichts bricht.

**Wann sich das aendert:** nach den ersten drei echten Laeufen. Der Wert wird dann hier
eingetragen — mit Datum und Datengrundlage, nicht als runde Zahl.

## Ein echter Beleg dafuer, dass beides noetig ist

Aus dem Ausgangsmaterial: Entwurf B und Entwurf C loesen die Interaktionsfarbe
**entgegengesetzt** — B sagt „Interaktion ist unbunt", C sagt „Instrumentenblau ist nur
Bedienung" — und **beide** erfuellen dieselbe Invariante I1.

Das ist echte Divergenz: zwei unvereinbare Weltbilder, die beide richtig sind. Genau das
soll die Matrix sichtbar machen — und genau das kann eine Sonde allein nicht, weil beide
Attrappen am Ende „eine Farbe fuer Bedienung" messen.

Deshalb zwei Sperren und nicht eine.
