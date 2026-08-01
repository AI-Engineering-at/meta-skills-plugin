# Die Token-Kategorien des Hauses

## Was sich hier geaendert hat — und warum

Diese Datei hiess frueher „Design Categories" und listete acht Kategorien mit je drei bis
fuenf Auswahloptionen: *Background, Typography, Cards, Colors, Spacing, Animations, Icons,
Layout* — mit Optionen wie „Gradient / Solid / Pattern / Neural / Image" oder
„Glass (blur-amount, background-opacity)".

Drei gemessene Gruende fuer die Abloesung:

1. **Die Liste widersprach sich selbst.** `commands/meta-design.md` nannte
   *Background, Typography, Cards, **Metrics, Controls, Buttons**, Colors, **Radius***;
   diese Referenzdatei nannte *… **Colors, Spacing, Animations, Icons, Layout***; der nie
   ausgelieferte Konfigurator nannte eine **dritte** Liste. Vier von acht Kategorien
   stimmten nicht ueberein.
2. **Acht Einzelauswahlen ergeben einen Kompromiss, keinen Entwurf.** Das alte Schema
   liess zwischen Hex-Werten waehlen. Das Verfahren, aus dem dieses System hervorging,
   liess zwischen *Weltbildern* waehlen. Die Frage „was bedeutet diese Farbe und wo gilt
   sie ausdruecklich **nicht**" kam im alten Schema ueberhaupt nicht vor.
3. **Die Kategorien deckten das Noetige nicht ab.** Es fehlten genau die, deren Fehlen
   Wiederverwendung verhindert: Fokusring, Kantenstaerke, Dichte-Masse, Umbruchpunkte.
   Sie waren im Rohmaterial durchgaengig Literale.

Ausserdem enthielt die alte Fassung zwei Regeln, die dieses Haus nicht mehr traegt:
sie erlaubte **Google Fonts** (das System nimmt nur System-Stacks — lizenzsauber,
offline, CSP-fest) und sie **erzwang Animationsdauern** (das System entscheidet sich
ausdruecklich fuer `motion.none`).

**Wer entschieden hat:** Fable 5. Die Kategorien unten sind aus seinem `DESIGN-SYSTEM.md`
(`farbsystem`, `schriftsystem`, `raster-abstand-form`) uebernommen. Diese Datei
transkribiert eine Festlegung; sie trifft keine.

---

## Die 15 Kategorien

| # | Kategorie | Token-Praefix | Bemerkung |
|---|---|---|---|
| 1 | Flaechen | `color.<theme>.surface.*` | `canvas` · `base` · `raised` · `sunken` |
| 2 | Kanten | `color.<theme>.line.*` | `quiet` (dekorativ) · `strong` (strukturell) · **`control`** (identifikationstragend, SC 1.4.11) |
| 3 | Text | `color.<theme>.ink.*` | `primary` · `secondary` · `tertiary` |
| 4 | Bedienung | `color.<theme>.interactive.*` | `accent` · `on-accent`. **Nur Bedienung, nie Zustand** (I1) |
| 5 | Zustand | `color.<theme>.state.*` | `ok` · `attention` · `danger` · `neutral`, je `base` / `tint` / `ground` / `on-ground` |
| 6 | Schrift-Rollen | `font.family.*` | `comment` (sans) · `quote` (mono). Nur System-Stacks |
| 7 | Typo-Skala | `font.size.t*` | sieben Stufen, **als Token gelebt** — im Schaustueck browser-gemessen exakt sieben distinkte Groessen |
| 8 | Zeilenhoehe | `font.lineheight.t*` | je Stufe eine |
| 9 | Abstand | `space.1..6` | 4-px-Rhythmus |
| 10 | Radius | `radius.s/m/l` | Papier hat keine grossen Rundungen |
| 11 | Kantenstaerke | `border.hairline/strong` | |
| 12 | Fokusring | `focus.width/offset` | Farbe = `interactive.accent`; ein Ring fuer alles |
| 13 | Dichte-Masse | `density.*` | `row` · `row-dense` · `control` · `band` |
| 14 | Umbruchpunkte | `breakpoint.*` | `hard-test` (der Haertetest ist ein Token) · `collapse` |
| 15 | Bewegung | `motion.*` | `none` ist der **Systemwert**, nicht das Fehlen einer Entscheidung |

Die konkreten Werte stehen in `design-system/tokens.dtcg.json` — mit `$description`,
Nutzungsregel und **gerechnetem** Kontrast je Farb-Token. Sie werden hier bewusst nicht
wiederholt: eine zweite Wertetabelle waere eine zweite Wahrheit, und getippte Werte
driften ausnahmslos.

---

## Was eine Kategorie zur Kategorie macht

Sie gehoert in diese Liste, wenn ihr Fehlen dazu fuehrt, dass ein Wert als **Literal** im
Quelltext landet. Das ist das gemessene Kriterium, nicht der Geschmack.

Nicht enthalten — mit Klasse und Grund:

| Nicht enthalten | Klasse | Grund |
|---|---|---|
| Ikonografie-Set | will-nicht (jetzt) | Marken + Woerter tragen alles Bisherige. Ein Icon-Set ist eine eigene Entwurfsrunde mit eigener Messung. |
| Diagramm-/Chart-Stile | will-nicht | Existing-First: der `dataviz`-Skill existiert mit eigenem Palette-Swap. Dieses System liefert ihm die Palette, es ersetzt ihn nicht. |
| Schatten / Verlaeufe | will-nicht | Erhebung ueber Flaeche traegt die vier Flaechenstufen + 1-px-Kanten. |
| Bewegung jenseits Fortschritt | will-nicht | `motion.none` ist die Entscheidung, nicht das Fehlen einer. |
| Bauteil-Token (L3) | kann-nicht (heute) | Die Bauteile nutzen L1/L2 direkt. Ein leerer L3-Satz waere ein Platzhalter. |
