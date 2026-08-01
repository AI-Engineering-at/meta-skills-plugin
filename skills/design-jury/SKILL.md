---
name: design-jury
version: 1.0.0
type: meta
category: quality
complexity: agent
description: Divergentes Entwurfsverfahren mit sichtbaren Attrappen, maschinellen Sonden und Pruef-Linsen. Der Mensch entscheidet. Trigger bei UI entwerfen, mehrere Entwuerfe, Design-Jury, Redesign, Design-Vergleich.
trigger: ui entwerfen, mehrere entwuerfe, design jury, redesign, design vergleich, design options
model: sonnet
allowed-tools: [Agent, AskUserQuestion, Read, Write, Bash]
user-invocable: true
token-budget: 9000
requires: [design]
produces: [design-entwuerfe, 05-linsen.md, 06-entscheid.md, DESIGN.md]
cooperative: true
last-audit: 2026-08-01
metadata:
  visual-authority: "fable-5"
  human-gate: "06-entscheid.md"
---

# meta:design-jury — das Verfahren

> Design is cooperation, not description-to-generation.
> The user SEES options and CHOOSES. The AI doesn't decide.

Dieser Satz stand vier Monate im `design`-Skill und hatte **keinen Ort**. Gemessen:
`AskUserQuestion` kam im gesamten Plugin **null** Mal vor; `cooperative: true` wurde von
**keiner** Python-Datei gelesen. Vier Skills trugen das Etikett, keiner wurde durch es zu
irgendetwas gezwungen.

Hier bekommt der Satz einen Ort: **Phase 6 ist der einzige Punkt, an dem der Ablauf
anhaelt** — und er haelt mit `AskUserQuestion` an, nicht mit einer hoeflichen Frage im
Fliesstext.

## Die Rollengrenze — bindend

**Fable 5 entwirft.** Rahmung und Entwurf gehen an ihn, ebenso jede Aenderung an Farbe,
Typografie, Form, Layout oder Token.

**Alle anderen Rollen melden Befunde ohne Gestaltungsvollmacht.** Ein Linsen-Befund lautet
„Kontrast 3,8:1 liegt unter 4,5:1" — **nicht** „nimm ein helleres Rot". Diese Grenze ist
maschinell geprueft: eine Linsen-Zelle darf keine Anweisungsform an den Entwerfer
enthalten (`tests/test_design_linsen.py`).

## Sieben Phasen, je ein Pflicht-Artefakt

| Phase | Ausgang | Gate |
|---|---|---|
| **P0 Bestand** | `00-bestand.md` | nennt jede gefundene Design-Quelle mit Pfad |
| **P1 Messung** | `01-belege.md` | jede Tabellenzeile hat `datei.ext:zeile` |
| **P2 Rahmung** | `02-rahmungen.json` | K ≥ 3 **und** paarweiser Achsenabstand ≥ 2 |
| **P3 Entwurf** | `entwuerfe/<id>/{spec.md,mockup.html,build.py}` | K Laeufe **isoliert**; Attrappe selbst-enthalten; Bau bytegleich |
| **P4 Sonden** | `04-messung.json` | **dieselben** Sondenschluessel ueber alle K |
| **P5 Linsen** | `05-linsen.md` | L×K Zellen, keine leer; jede Wertung mit Beleg; keine Anweisungssprache |
| **P6 Entscheidung** | `06-entscheid.md` | **AskUserQuestion** — hier und nur hier haelt es an |
| **P7 Kanonisierung** | `DESIGN.md`, `tokens.overrides.json` | **kein Schreiben ohne `06-entscheid.md`** |

P0–P5 laufen ohne den Menschen. Das ist der Punkt: er soll nicht acht Mal nach einem
Hex-Wert gefragt werden, sondern **einmal** zwischen fertigen, vermessenen Weltbildern
waehlen.

Vollstaendig mit Ein- und Ausgang je Phase: `references/phasen.md`

## Warum Divergenz erzwungen wird

Ohne Zwang konvergieren K Entwuerfe — man bekommt drei Varianten desselben Gedankens,
waehlt eine und nennt das eine Entscheidung. Zwei Sperren:

- **vorher, deklariert:** Achsenmatrix, fuer jedes Paar mindestens 2 verschiedene Achsen.
  Reine Zaehlung, **bricht hart**.
- **nachher, gemessen:** Abstand ueber die Sonden. **Nur-Messen-Modus** — es gibt keinen
  begruendeten Schwellwert, und eine erfundene Zahl waere ein Platzhalter im
  Produktivpfad. Der Wert wird nach den ersten drei echten Laeufen aus den Daten gesetzt.

`references/divergenz.md`

## Die Linsen — adoptiert, nicht erfunden

`skills/triad-review/` hat das Jury-Muster bereits: spezialisierte Prueferrollen mit je
einem Ziel, Belegpflicht statt Geschmack, Kreuzvalidierung, fester Bericht,
Terminalzustaende. Ergaenzt werden nur die Design-Kriterien:

Ehrlichkeit (A33) · Herkunft je Fakt · Zustands-Vollstaendigkeit · Zugaenglichkeit ·
Dichte im kleinsten Zielfenster · Umsetzbarkeit gegen den echten Baum · **Kohaerenz**
(haelt der Entwurf seine *eigenen* Regeln).

Kohaerenz ist die ertragreichste: Entwurf C erklaerte 7 Typo-Stufen — gemessen wurden 16.

`references/linsen.md`

## Was nicht geloescht wird

Nicht gewaehlte Entwuerfe bleiben unter `entwuerfe/`. Sie sind die **Begruendung der
Wahl** und die Quelle fuer „was uebernehmen wir aus B in C". Heute existiert die
Jury-Bewertung, die zwischen den drei Ausgangsentwuerfen entschied, **gar nicht auf
Platte** — die Punktzahlen lebten nur im Gespraechsverlauf. `05-linsen.md` ist die
Reparatur genau dieses Lochs.

## Was sich nicht erzwingen laesst

Dass Fable 5 die gestalterische Entscheidung wirklich getroffen hat. `autor: fable-5` kann
jeder tippen. Mechanisch erzwingbar ist nur, dass das Feld da ist — **Buchfuehrung, kein
Beweis.** Hier wird nichts anderes behauptet.

## Referenzdateien

- `references/phasen.md` — P0–P7 mit Ein- und Ausgang
- `references/divergenz.md` — Achsen, Abstandsmass, Ablehnungsgrund
- `references/linsen.md` — die sieben Linsen nach dem triad-review-Muster
- `references/entwurfs-brief.md` — der Fat-Brief je Entwerfer
- `references/artefakt-schema.md` — `00-bestand.md` … `06-entscheid.md`, Feld fuer Feld
