# Die Pruef-Linsen

## Adoption, kein Neubau

`skills/triad-review/SKILL.md` hat das Jury-Muster bereits gebaut. Woertlich von dort:

> „Two blind judges find the same superficial errors. Three specialized attackers find
> what actually hurts."

und die zwei Regeln, die das Muster tragen:

> „**NO** agent comments on style, naming, 'best practices'"
> „**EVERY** agent provides EXACT PoC with concrete input value"

Uebernommen werden: spezialisierte Prueferrollen mit je **einem** Ziel · Belegpflicht statt
Geschmack · Kreuzvalidierung als Prioritaetsklasse · fester Bericht · Terminalzustaende.
Ergaenzt werden **nur** die Design-Kriterien.

## Die sieben Linsen

| Linse | Ziel | Maschinelle Sonde |
|---|---|---|
| **L1 Ehrlichkeit (A33)** | Zeigt die Attrappe etwas, das es nicht gibt? | Abgleich `fehlstellen` gegen den Attrappentext |
| **L2 Herkunft** | Ist jeder Beispielwert klassifiziert? | Slug `herkunft-beispielwerte` gegen die Wertliste |
| **L3 Zustands-Vollstaendigkeit** | Alle 8 Zustaende je Flaeche? | `design-states.py --coverage` |
| **L4 Zugaenglichkeit** | Kontrast, Farbe nie alleiniger Traeger, Fokus, ARIA | `design-contrast.py` + Sonden `roleAlert` / `ariaLive` / unbenannte Bedienelemente |
| **L5 Dichte / Haertetest** | Haelt es im kleinsten Zielfenster? | kein Seitwaerts-Scroll des Koerpers, kein abgeschnittener Dialog |
| **L6 Umsetzbarkeit** | Gegen den echten Baum gebaut? | `datei:zeile`-Zitate muessen aufloesbar sein |
| **L7 Kohaerenz** | Haelt der Entwurf seine **eigenen** Regeln? | deklarierte Skala gegen gemessene Groessen |

## L7 ist die schaerfste

Am Ausgangsmaterial gemessen und ertragreich: Entwurf C **deklarierte** 7 Typo-Stufen —
die Messung fand **16** distinkte Groessen. C forderte Hash-Darstellung in 8×8-Gruppen —
gemessen `grouped8x8 = 0`. Beides stand in keiner Spezifikation und faellt keinem Leser
auf.

Ein Entwurf, der seine eigenen Regeln bricht, ist gefaehrlicher als einer ohne Regeln:
er sieht geprueft aus.

## Die Sprachregel — die Fable-5-Grenze

Eine Linsen-Zelle enthaelt einen **Befund**, keine **Anweisung**.

| erlaubt | verboten |
|---|---|
| „Kontrast 3,8:1 liegt unter der Schwelle 4,5:1" | „nimm ein helleres Rot" |
| „`partial` ist in dieser Flaeche nicht gezeichnet" | „fuege einen Teilzustand hinzu" |
| „drei Bedienelemente ohne zugaenglichen Namen" | „benenne die Knoepfe" |

Maschinell geprueft: die Zelle darf keine Anweisungsform an den Entwerfer enthalten
(`tests/test_design_linsen.py`). Gesucht wird nach Mustern wie „nimm ", „mach ",
„aendere ", „use ", „should be".

**Das Fehlalarm-Risiko ist bewusst in Kauf genommen.** Ein Fehlalarm kostet eine Minute.
Eine durchgerutschte Gestaltungsanweisung bricht die Rollenzuweisung des Eigentuemers.

## Der Bericht

`05-linsen.md` fuehrt L×K Zellen. Je Zelle: **Befund · Beleg · Wertung · Gewicht.**

Ohne diese Datei entsteht kein `06-entscheid.md`.

Der Grund ist ein gemessenes Loch: die Jury-Bewertung, die zwischen den drei
Ausgangsentwuerfen entschied (21,5 / 36,5 / 36,0), existiert **nicht auf Platte**. Kein
Kriterienblatt, keine Gewichtung, keine Einzelwertung, kein Pruefername. Der Prozess, der
zu Recht gelobt wurde, ist heute **nicht wiederholbar, nicht nachpruefbar und nicht
anfechtbar**. `05-linsen.md` repariert genau das.
