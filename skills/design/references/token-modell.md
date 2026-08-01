# Das Token-Modell

## Format: DTCG 2025.10 — adoptiert, nicht erfunden

Der W3C-Community-Group-Standard ist final und stabil („Final Community Group Report",
28.10.2025) und traegt ausdruecklich **kein** „do not implement". Das Schema ist gehostet
und hier vendored. Ein Eigenformat waere ein Existing-First-Verstoss ohne einen einzigen
Vorteil.

Verwendete `$type`: `color` (Objektform mit `colorSpace` / `components` / `hex`, wie das
Schema es verlangt), `fontFamily`, `dimension`, `number`, `duration`.
**Abweichungen vom Standard: keine.**

Alles Hauseigene liegt in `$extensions` unter dem Reverse-Domain-Schluessel
`at.ai-engineering.design`. Der Standard garantiert, dass Werkzeuge unbekannte Extensions
erhalten muessen — deshalb ist das der richtige Ort und nicht ein neues Feld.

## Was der Standard uns schenkt, das wir sonst erfunden haetten

| Feld | Traegt |
|---|---|
| `$description` | die **Bedeutung** — genau das, was gute Design-Dokumente auszeichnet |
| `$deprecated` | den Ersetzungstext — der halbe Migrationspfad |
| `$extensions` | alles Eigene, ohne den Standard zu brechen |

## Die hauseigenen Extensions

```json
"$extensions": {
  "at.ai-engineering.design": {
    "contrast": [ { "vs": "surface", "ratio": 3.46, "min": 3.0 } ],
    "rule": "nur dekorativ; Identifikation braucht line.control"
  }
}
```

`contrast` wird beim Erzeugen **gerechnet**, nie getippt. Damit reist die
Abnahmebedingung im Token mit, statt in einer Prosa daneben zu stehen und zu driften.

`rule` traegt die Nutzungsregel — der Ort fuer „wo diese Farbe ausdruecklich **nicht**
gilt". Genau das kannte der alte `categories.md` nicht: er kannte „welcher Hex".

## Schichtung

| Schicht | Was | Wer setzt |
|---|---|---|
| **L0** | Rohwerte — die Hex- und Zahlwerte in `tokens.dtcg.json` | Fable 5 |
| **L1** | Rollen-Token mit Bedeutung (`ink.secondary`, `state.danger.base`) | Fable 5 |
| **L2** | **generierte** Ableitungen (`*.tint` mit Alpha .10, `*.ground`, `*.on-ground`) | Generator |
| **L3** | Bauteil-Token | Fable 5 — **heute leer**, die Bauteile nutzen L1/L2 direkt |
| **L4** | zuschaltbare Domaenen-Module | Projekt — **heute nicht gebaut** |

L3 und L4 sind ehrlich leer, nicht vorsorglich befuellt. Ein leeres Modulverzeichnis
waere ein Platzhalter; `design-resolve.py --modules` scheitert deshalb benannt, statt
still nichts zu laden.

## Die Alias-Ebene und warum es sie gibt

Im Rohmaterial gemessen: `--fog` und `--ink-dim` waren **derselbe Hex-Wert unter zwei
Namen**. Nicht als Absicht deklariert, sondern zufaellig gleich — der Beweis einer
fehlenden Alias-Ebene. Wer den einen aendert, aendert den anderen nicht mit, und niemand
merkt es.

Heute: `state.neutral.base` ist ein **DTCG-Alias** auf `ink.secondary`
(`"$value": "{color.dark.ink.secondary}"`). Die Gleichheit ist eine deklarierte Absicht
mit Migrationspfad.

**Regel:** zwei Token mit gleichem aufgeloestem Wert sind ein Fehler, es sei denn, einer
erklaert sich per Alias zum anderen. Geprueft in `tests/test_design_tokens.py`.

## Die vier Invarianten

Sie sind **wertfrei formuliert**, damit Fable 5 frei bleibt. Sie kodieren die Regel,
nicht die Loesung.

**I1 — Interaktions-Kodierung ∩ Zustands-Kodierung = leer.**
Kein Statuston heisst je „hier klicken", kein Akzent heisst je „alles gut".
Der Beleg dafuer, dass das eine Invariante und keine Geschmacksfrage ist: Entwurf B und
Entwurf C loesen es **entgegengesetzt** (B: „Interaktion ist unbunt"; C: „Instrumentenblau
ist nur Bedienung") und erfuellen beide dieselbe Invariante.

**I2 — Jeder Zustand ist ohne Farbe unterscheidbar.** Form, Position oder Wort (SC 1.4.1).
Im Haus-System: sechs CSS-Marken plus das Wort im Chip. Drei Kodierungen, damit keine
allein traegt.

**I3 — Jedes bedeutungstragende Token sagt, was es bedeutet.** `$description` ist Pflicht;
wo eine Nutzungsgrenze existiert, traegt `rule` sie.

**I4 — Bedeutung wohnt im Token-Namen, nicht im Hex-Wert.**
Folge: ein Themenwechsel ist ein **Token-Tausch**, kein Audit. Und ein Produkt, das sich
auf eine Welt festlegen will, tut das durch Tausch, nicht durch Umschreiben.

## Pflicht-Kategorien

Gemessen im Rohmaterial: tokenisiert waren nur **Farbe und Schriftstack**. Die
Typo-Skala stand in Entwurf Cs Spezifikation als `--t10..--t22` — im CSS existierte
**keines** davon. Abstand, Radius, Kante, Fokus, Dichte und Umbruchpunkte waren ueberall
Literale. Genau diese Luecke verhindert Wiederverwendung, Skalierung und Updates.

Die Kategorien des Hauses stehen in `categories.md`. Eine Kategorie darf **leer** sein —
dann steht das in `STATUS.md` als „bewusst leer", nicht als Vorgabe. Ehrlich leer schlaegt
erfundene Vorgabe.
