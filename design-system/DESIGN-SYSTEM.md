# AIE Design-System — die Haus-Grundlage

```yaml
projekt:        AIE Design-System (wiederverwendbare Haus-Grundlage, kein Einzelprodukt)
schema-version: 1.0.0        # Struktur dieses Dokuments (Slugs, Pflichtabschnitte)
design-version: 1.0.0        # Inhalt: Token, Rollen, Bauteile
autor:          Fable 5 (claude-fable-5)
stand:          2026-08-01
basiert-auf:    Entwurf C "Der Kontrollraum" + Entwurf B "Die Ermittlungsakte" (beide 2026-08-01)
artefakte:      tokens.dtcg.json (Quelle) · tokens.css (generiert) · showcase.html (Schaustueck)
werkzeuge:      contrast.py (Rechner) · gen_tokens.py (Generator) · verify_showcase.py (Pruefer)
status:         zur Abnahme
```

Abschnitte tragen stabile Slugs, keine tragenden Nummern — C musste „13a" einschieben,
jede Nummerierung verschiebt sich beim ersten Update.

---

## these

**Das AIE-Design-System ist die gestalterische Grundlage, aus der konkrete Produkte
abgeleitet werden — es kodiert nicht Geschmack, sondern nachprüfbare Regeln: Farbe gehört
dem Zustand, Form ist die zweite Kodierung, Schrift trennt Zitat von Kommentar, und jede
Zahl in diesem Dokument ist gerechnet, nicht behauptet.**

Drei Sätze, aus denen alles Weitere folgt:

1. **Farbe gehört dem Zustand, der Akzent gehört der Bedienung.** Die beiden Kodierungen
   sind disjunkt (Invariante I1). Kein Statuston heißt je „hier klicken", kein Akzent heißt
   je „alles gut".
2. **Jede Bedeutung trägt drei Kodierungen: Farbe, Form, Wort.** Wer nur eine wahrnimmt,
   verliert nichts (SC 1.4.1).
3. **Bedeutung wohnt im Token-Namen, nicht im Hex-Wert** (Invariante I4). Ein Themenwechsel
   ist ein Token-Tausch; die Regeln folgen dem schwächeren Thema, damit der Wechsel nie ein
   Audit auslöst.

---

## beleg-grundlage

Alles Folgende ist selbst gelesen, gerechnet oder ausgeführt — nichts aus Zusammenfassungen
übernommen:

| Behauptung | Beleg |
|---|---|
| Cs Palette, Typografie, Bauteile im Detail | `design/C/spec.md` (664 Z.) vollständig gelesen; `C/mockup.html:1-120` (`:root` + Kernstile) |
| Bs Palette, Herkunftsklassen, Messkapitel | `B/spec.md:42-123` + `B/spec.md:372-411` gelesen |
| Generische Struktur (Schema, Token-Kategorien, M1–M14, Q1–Q14) | `erhebung-rohmaterial.md` (635 Z.) vollständig gelesen |
| DTCG 2025.10 ist stabil, Schema erreichbar | `curl …/schemas/2025.10/format.json` → HTTP 200, 56523 Bytes, lokal gesichert als `dtcg-format-schema.json` |
| DTCG-Farbwert 2025.10 = Objekt `{colorSpace, components[, alpha, hex]}`, `additionalProperties:false` | Schema-Definition selbst geparst (nicht aus Doku zitiert) |
| Mein Kontrastrechner ist kalibriert | Referenzfall `#FFFFFF/#767676` → **4.54:1** (kanonischer WCAG-Grenzfall) |
| **Cs behauptete Kontraste weichen ab** | Nachgerechnet gegen `#151E26`: Nebel behauptet 4.9, gerechnet **6.23** · Alarm behauptet 3.8, gerechnet **4.58** · Alarm-Ink behauptet 5.2, gerechnet **7.29** |
| Alle 72 Farb-Kombinationen beider Themen bestehen ihre Schwelle | `python3 contrast.py` → `GESAMT-FAILS: 0`, Rohlauf in `contrast-lauf.txt` (72 Schwellen-Checks + 6 Info-Zeilen) |
| `tokens.dtcg.json` ist schema-valide | `jsonschema.validate(...)` gegen das offizielle Schema → **PASS (0 Fehler)** (jsonschema 4.25.1, lokal nach `_pyvendor/` geholt) |
| Das Schaustück hält seine eigenen Regeln | `python3 verify_showcase.py` → **16/16 PASS** (`verify-lauf.txt`): reines ASCII, Tag-Balance, kein externer Request, keine literale font-size, 26 Kontrastzahlen nachgerechnet, 3 Digests nachgerechnet, 8 Zustände vorhanden, 0 unbenannte Buttons |
| Das Schaustück ist im echten Chrome vermessen | lokaler `http.server` (danach beendet), Werte in `messung-browser.txt` |
| Gemessene Schriftgrößen = exakt die 7 deklarierten Stufen | Browser: `distinctFontSizes = [10,11,12,13,15,18,22px]` — C hatte deklariert 7, gemessen 16 |

**Drei Befunde, die den Entwurf direkt geformt haben:**

- **Cs Kontrastzahlen waren teils falsch** (4.9 behauptet vs. 6.23 gerechnet). Konsequenz:
  dieses System liefert den *Rechner mit* (`contrast.py`), jede Zahl im Schaustück trägt ihr
  Farbpaar als `data`-Attribut, und `verify_showcase.py` rechnet alle 26 angezeigten Zahlen
  nach. Behauptung und Prüfung sind mechanisch gekoppelt.
- **Nur Farbe und Schriftstack waren tokenisiert** (gemessen: `--t10..--t22` standen in Cs
  Spezifikation, im CSS existierte keines). Konsequenz: 15 Token-Kategorien, und das
  Schaustück enthält **null** literale `font-size`-Angaben (mechanisch geprüft).
- **`--fog == --ink-dim` war derselbe Hex-Wert unter zwei Namen** — der Beweis der fehlenden
  Alias-Ebene. Konsequenz: `state.neutral.base` ist im Token-File ein **DTCG-Alias** auf
  `ink.secondary` — die Gleichheit ist jetzt Absicht mit Migrationspfad, kein Zufall.

---

## zielbild-einsatzmoment

Die Grundlage bedient die Flächen, die dieses Haus tatsächlich baut: dichte
Operator-Konsolen, Admin- und Nachweis-Oberflächen, Artefakt-Seiten und Plugin-Schauflächen
— Oberflächen, die KI-Ausgaben, Messwerte und folgenreiche Aktionen zeigen. Der
Einsatzmoment ist Arbeit unter Zeitdruck an kleinen Fenstern (Härtetest 900 px als Token
`breakpoint.hard-test`), oft neben einem Terminal. Abgeleitete Produkte erben Token,
Bauteile und Regeln; sie dürfen enger werden (z. B. sich auf eine Welt festlegen), nie
lockerer.

---

## sprache-und-stimme

**Produktfläche: Englisch** (Fehlercodes, Kommandos und Gerätetext sind ohnehin englisch;
die bisherigen Produkte assertieren englische Strings). **Spezifikation und Anmerkungen:
Deutsch** — die Sprache, in der dieses Haus entscheidet. Im Schaustück ist die Trennung
sichtbar: Demo-Inhalte englisch, jede deutsche Zeile ist Anmerkung. Terminologiequelle für
Zustände ist der Bestands-Skill `async-state-coverage` (kein zweites Vokabular erfunden).

---

## modus-festlegung

**Zwei gleichwertige Themen — als Entscheidung, nicht als Kompromiss.**

C legte sich auf eine dunkle Welt fest und begründete das mit einem eingebetteten
xterm-Terminal auf Schwarz — ein **Produkt**-Anker. Eine **Haus**-Grundlage hat diesen
Anker nicht: Artefakt-Seiten rendern im Betrachter-Thema, Plugin-Flächen laufen in fremden
Fenstern, und abgeleitete Produkte sollen die Ein-Welt-Entscheidung selbst treffen dürfen
(sie ist dann ein Token-Tausch, I4).

Das benannte Risiko zweier Themen — „doppelte Prüflast bei halber Sorgfalt" (C §3) — wird
nicht weggeredet, sondern **wegautomatisiert**: beide Paletten laufen durch denselben
Rechner (72 Kombinationen, 0 Fails), beide stehen im Schaustück nebeneinander, und **die
Nutzungsregeln folgen dem schwächeren Thema** (siehe `farbsystem`: die danger-Regel gilt
themenübergreifend, obwohl nur das dunkle Thema sie erzwingt). Dunkel ist die
**Referenz** (Kalibrierreihenfolge, erste Nennung), Hell ist gleich sorgfältig gerechnet —
nicht „invertiert".

---

## farbsystem

### Bedeutungstragende Rollen — und wo sie NICHT gelten

| Rolle | dunkel | hell | Bedeutung — und wo sie *nicht* gilt |
|---|---|---|---|
| `surface.canvas` | `#0E141A` | `#E9EEF2` | App-Grund. Kalt-blaugraues Graphit / kaltes Papier. Trägt keine Bedeutung — er ist das, wovor Bedeutung steht. |
| `interactive.accent` | `#5D9FD6` | `#1C6CA8` | **Nur Bedienung**: Fokusring, aktive Ansicht, Primärtaste, Auswahl, Verweis. Nie Zustand, nie Erfolg, nie „info". |
| `state.ok.base` | `#63AC76` | `#22713F` | **Verifiziert / bereit / erfüllt.** Nie Bedienbarkeit, nie Dekoration. |
| `state.attention.base` | `#CE9737` | `#875410` | **Braucht einen Menschen**: gegatete Aktion, Countdown, offene Antwort. Heißt nie „kaputt", sondern „hier entscheidest du". |
| `state.danger.base` | `#E1584D` | `#AC3428` | **Abweichung / Verweigerung / Fehler.** Nur hier, nie dekorativ. Als Fließtext **nur** auf `state.danger.ground`. |
| `state.neutral.base` | Alias → `ink.secondary` | Alias → `ink.secondary` | **Keine Aussage**: UNKNOWN, „nicht geprüft", leere Erfolgszustände. Die Farbe der Ehrlichkeit — sie behauptet nichts. |

Die vollständige Rampe (Flächen `canvas/base/raised/sunken`, Kanten `quiet/strong/control`,
Text `primary/secondary/tertiary`, je Zustand `base/tint/ground/on-ground`) steht mit jedem
Wert, jeder Rolle und jedem gemessenen Kontrast in `tokens.dtcg.json` und im Schaustück,
Abschnitt `farbsystem`.

### Gerechnete Kontraste (Auszug; vollständig: contrast-lauf.txt, 72 Checks, 0 Fails)

```
DUNKEL (Grund surface #151E26)          HELL (Grund surface #F6F9FB)
ink.primary        13.43:1  (>=4.5)     ink.primary        15.42:1  (>=4.5)
ink.secondary       6.77:1  (>=4.5)     ink.secondary       7.01:1  (>=4.5)
interactive.accent  5.94:1  (>=4.5)     interactive.accent  5.28:1  (>=4.5)
on-accent/accent    6.74:1  (>=4.5)     on-accent/accent    5.59:1  (>=4.5)
state.ok            6.18:1  (>=4.5)     state.ok            5.67:1  (>=4.5)
state.attention     6.51:1  (>=4.5)     state.attention     6.01:1  (>=4.5)
state.danger        4.58:1  (Regel!)    state.danger        6.06:1  (>=4.5)
danger-on/ground    8.02:1  (>=4.5)     danger-on/ground    7.55:1  (>=4.5)
line.control        3.46:1  (>=3.0)     line.control        3.59:1  (>=3.0)
Fokusring accent    5.94:1  (>=3.0)     Fokusring accent    5.28:1  (>=3.0)
ink auf allen 4 Tints >=11.52:1         ink auf allen 4 Tints >=13.21:1
```

**Hausreserve:** Text-Token müssen **≥ 5.0:1** messen (AA + Reserve), sonst greift eine
Nutzungsregel. Einziger Fall: `state.danger.base` dunkel mit 4.58:1 — numerisch über AA,
aber unter der Reserve. Daraus die eine gemessene Bauregel des Farbsystems:

> **danger ist als Fließtext nur auf `state.danger.ground` erlaubt** (dort 8.02 / 7.55:1);
> auf normalem Grund ist danger ausschließlich Marke, Kante oder Balken (≥ 3:1 gemessen).
> Deshalb ist der Alarmfall ein *Band mit eigenem Grund*, nicht rote Schrift.

**Drei Kanten statt zwei:** `line.quiet` (dekorativ) · `line.strong` (Zonentrennung,
strukturell) · **`line.control`** (neu): die Identifikationskante für Bedienelemente
(Eingabefeld, Konturtaste, Chip). Nur sie muss SC 1.4.11 erfüllen und misst 3.46 / 3.59 /
3.25:1 auf allen drei Gründen. So bleibt die Fläche ruhig, ohne dass eine
identifikationstragende Kante je unter 3:1 fällt.

### Zweite Kodierung ohne Farbe

| Zeichen | Bedeutung | Umsetzung |
|---|---|---|
| voll (●) | beobachtet — wörtlich gelesen | gefüllter Kreis, 8 px, reines CSS |
| halb (◐) | abgeleitet — berechnet/klassifiziert | halb gefüllter Kreis |
| hohl (○) | unbekannt — keine Aussage | Kreisring |
| Strich (—) | nicht prüfbar / kein Vergleichswert | 8×2-Balken, `ink.tertiary` |
| schraffiert (▨) | gesperrt — strukturell verweigert | 45°-Schraffur, nie fokussierbar |
| gestrichelt (╌) | nicht verfügbar — Lücke des Werkzeugs | 1-px-Strichkante rundum |

Dritte Sicherung ist das **Wort**: Chips kombinieren Farbe + Form + Wort
(`READ-ONLY` rund/neutral · `GATED` eckig/attention · `BLOCKED` schraffiert/quadratisch ·
`NOT AVAILABLE` gestrichelt). Kein Emoji, keine Fremdschrift, kein Bild.

---

## schriftsystem

**Nur System-Stacks** — lizenzsauber, offline, CSP-fest, keine Datei im Bundle. Die Stacks
sind aus C übernommen, weil ihre Begründung Glied für Glied gemessen war (Inter/Fira Code
waren im Bestand deklariert und auf keinem Zielsystem installiert):

```css
--sans: system-ui, -apple-system, "Segoe UI Variable Text", "Segoe UI",
        Roboto, "Noto Sans", "DejaVu Sans", sans-serif;
--mono: ui-monospace, "SF Mono", Menlo, "Cascadia Mono", Consolas,
        "DejaVu Sans Mono", "Liberation Mono", monospace;
```

`system-ui` → SF Pro (macOS) / Segoe UI Variable (Win 11); `-apple-system` deckt ältere
WebKit-Stände; `"Segoe UI"` fängt Windows 10; auf Linux ist `system-ui` fontconfig-abhängig,
darum `Roboto`/`Noto Sans` explizit und `DejaVu Sans` als garantierter Ausgang. Mono:
`ui-monospace` → SF Mono/Cascadia; `Menlo` (macOS-Sicherheit), `Consolas` (Win-Altstände),
`DejaVu Sans Mono`/`Liberation Mono` (Linux).

**Rollen (die eigentliche Entscheidung):**

| Rolle | Stack | Trägt |
|---|---|---|
| **Kommentar** | sans | Deutung des Werkzeugs: Labels, Erklärungen, Tasten, Navigation |
| **Zitat** | mono | alles Wörtliche: Kommando, Hash, Pfad, Zeitstempel, Fehlercode, Gerätetext |
| **Zahl** | mono + `tabular-nums` | Countdown, Zähler, Bytes, jede Zahlenspalte — Ziffern springen nie |

**Skala — sieben Stufen, als Token gelebt** (`font.size.t10 … t22` im DTCG-File,
`--t10 … --t22` im CSS): 10/1.2 (Versalien + .08em) · 11/1.35 · 12/1.4 · **13/1.5
(Grundtext)** · 15/1.35 · 18/1.25 · 22/1.2 (nur der Alarmfall, einmal pro Bildschirm).
Browser-gemessen: das Schaustück enthält **exakt diese 7** distinkten Größen — C hatte
7 deklariert und 16 gemessen. Hash-Darstellung: 64 Hex in 8 Gruppen zu 8, mono, tabular,
Umbruch nur an Gruppengrenzen, Kopiertaste je Wert.

---

## raster-abstand-form

Alle Werte sind Token (DTCG `dimension`), keine Literale:

| Kategorie | Token | Werte |
|---|---|---|
| Abstand | `space.1..6` | 4 · 8 · 12 · 16 · 24 · 32 px (4-px-Rhythmus) |
| Radius | `radius.s/m/l` | 2 (Chips) · 3 (Karten, Dialoge) · 4 px (Rahmen) — Papier hat keine großen Rundungen |
| Kante | `border.hairline/strong` | 1 · 2 px |
| Fokus | `focus.width/offset` | 2 · 2 px, Farbe `interactive.accent` |
| Dichte | `density.row/row-dense/control/band` | 28 · 24 · 28 · 60 px |
| Umbruch | `breakpoint.hard-test/collapse` | 900 · 1100 px |
| Bewegung | `motion.none/progress` | 0 ms (Default) · 1000 ms (einzige Ausnahme: Fortschritt/Countdown; bei `prefers-reduced-motion` Zahlensprünge statt Balken) |

Keine Schatten, keine Verläufe, keine Illustration. Erhebung über Fläche wird durch die
vier Flächenstufen + 1-px-Kanten getragen.

---

## layout

Regeln statt fester Zonenschnitte (der Schnitt ist Produktentscheidung):

1. **Feste Zonen verschwinden nie, sie kollabieren.** Was Zustand trägt (Statusleiste,
   Ereignisstrom), schrumpft unter `breakpoint.collapse` auf eine Kante mit Ticks — es
   wird nie per Media-Query geopfert.
2. **Der Seitenkörper scrollt nie seitwärts.** Zu breite Inhalte (Tabellen, Hashes,
   Zitate) scrollen in ihrem eigenen `overflow-x:auto`-Container. Browser-gemessen am
   Schaustück: `bodyHorizontalScroll: false`, `unmanagedOverflowCount: 0`.
3. **Der Härtetest ist ein Token.** Ein abgeleitetes Produkt muss bei
   `breakpoint.hard-test` (900 px) vollständig bedienbar sein und weist das per Messung
   nach, nicht per Behauptung.

---

## token-architektur

### Format: DTCG 2025.10 — adoptiert, nicht erfunden

Der W3C-Community-Group-Standard ist final und stabil („Final Community Group Report",
28.10.2025), das Schema ist gehostet und hier **gegen die Datei validiert**:
`tokens.dtcg.json` → jsonschema-Validierung **PASS, 0 Fehler**. Ein Eigenformat wäre ein
Verstoß gegen Existing-First ohne einen einzigen Vorteil. Verwendete `$type`: `color`
(Objektform mit `colorSpace`/`components`/`hex`, wie das Schema verlangt), `fontFamily`,
`dimension`, `number`, `duration`. **Abweichungen vom Standard: keine.** Alles Hauseigene
liegt in `$extensions` unter dem Reverse-Domain-Schlüssel **`at.ai-engineering.design`** —
Werkzeuge müssen unbekannte Extensions erhalten, das garantiert der Standard.

**Das Neue daran:** jedes Farb-Token trägt in `$extensions.…design.contrast` seine
**gerechneten** Kontraste samt Grund und Schwelle (von `gen_tokens.py` beim Erzeugen aus
`contrast.py` berechnet — nie getippt) und in `…design.rule` seine Nutzungsregel. Die
Abnahmebedingung reist im Token mit.

### Schichtung

```
L0  Rohwerte        die Hex-/Zahlwerte in tokens.dtcg.json          <- einzige Stelle mit Werten
L1  Rollen-Token    color.{dark,light}.surface|line|ink|interactive|state.*
                    font.family/size · space · radius · border · focus · motion · density · breakpoint
L2  Ableitungen     state.*.tint (alpha .10) · state.*.ground · state.*.on-ground
                    -> von gen_tokens.py generiert, nie handgepflegt
L3  Komponenten     nur wo nötig (heute: keine — Bauteile nutzen L1/L2 direkt)
L4  Domänen-Module  zuschaltbar: Konsequenzklasse (READ-ONLY/GATED/BLOCKED),
                    Erkenntnisgrad (Marken), Integritätszustand, Schutzstufe
                    -> Erkenntnisgrad + Herkunftsart sind Default-AN (KI-Ausgabe-Flächen)
```

**Alias-Ebene, konkret:** `state.neutral.base` ist `{color.dark.ink.secondary}` bzw.
`{color.light.ink.secondary}` — die in C gemessene stille Duplikation (`--fog == --ink-dim`)
ist damit eine deklarierte Absicht; wer den einen Wert ändert, ändert nachweislich beide
oder löst den Alias bewusst.

### Theming, Versionierung, Updates

- **Theming:** die zwei Sets `color.dark` / `color.light` sind für den **publizierten**
  DTCG-Resolver 2025.10 geschnitten (`resolver.json` HTTP 200). Wichtig: nie die
  Drafts-Fassung (`…/TR/drafts/resolver/` trägt „do not implement") und nie
  `tr.designtokens.org` verlinken (301 auf Drafts).
- **Versionierung:** Token-Paket führt Semver getrennt von Produkt-Versionen.
  **MAJOR** = Token gelöscht/umbenannt oder Nutzungsregel verschärft · **MINOR** = neues
  Token, neue `$deprecated`-Markierung (mit Ersetzungstext) · **PATCH** = Wertkorrektur,
  die alle gemessenen Schwellen hält (Nachweis: `contrast.py`-Lauf im Commit).
- **Diff:** `@adobe/token-diff-generator` (`tdiff`, Apache-2.0) als CI-Schritt gegen die
  Vorversion; Markdown-Ausgabe in den CHANGELOG; `deleted`/`renamed` erzwingt MAJOR.
  *(Empfehlung aus der Extern-Erhebung; hier nicht ausgeführt — siehe `nicht-geprueft`.)*
- **Update-Pfad ins Plugin:** `tokens.dtcg.json` ist die Quelle; `tokens.css` und die
  Paletten-Tabellen des Schaustücks werden von `gen_tokens.py` erzeugt.
  `verify_showcase.py` schlägt an, wenn Schaustück und Quelle auseinanderlaufen —
  das ist die mechanische Antwort auf die im Plugin gemessene Zahlen-Drift
  (fünf verschiedene Testzahlen in Prosa).

---

## bauteil-katalog

Vierzehn generische Muster, aus C §8 und den CSS-Beständen beider Attrappen destilliert
(Struktur: `erhebung-rohmaterial.md` §4 — hier die gestalterische Festlegung). Ordnung:
Primitive → Zusammengesetzte → Flächen → Muster → Meta.

| # | Muster | Feste Teile | Zustände (gezeichnet im Schaustück) |
|---|---|---|---|
| M7 | Erkenntnisgrad-Marke | 8-px-CSS-Form, `currentColor` | voll · halb · hohl · Strich · schraffiert · gestrichelt |
| M8 | Klassen-Chip | Farbe + Form + Wort, nie `<button>` | READY (rund) · GATED (eckig) · BLOCKED (schraffiert, kein Fokus) · NOT AVAILABLE (gestrichelt) |
| M11 | Skelettzeilen | statische Balken in Ergebnis-Zeilenhöhe, **kein Schimmern** | ein Zustand; Anzahl = erwartete Zeilen |
| M5 | Kopierbarer Prüfwert | 8×8-Gruppen, Kopiertaste, Herkunftszeile, eigener Scroll | verified · mismatch (beide Werte voll + Lawinensatz, **kein Zeichen-Diff**) · file missing (**kein** Mismatch) · not checked |
| M6 | Herkunftszeile | drei Zellen `woher · wann · geprüft`, 11 px mono, **sichtbar, nie Tooltip** | beobachtet · abgeleitet · Datei · nicht erfasst |
| M9 | Fehlerkarte | Code-Badge (mono, danger-ground) + Satz + Feldtabelle + Handlungszeile | steht dauerhaft; Alarm-Variante nicht schließbar |
| M10 | Fehlstellen-Rahmen | gestrichelte Kante, Chip, *was fehlt* (Produktsprache) + *was es bräuchte* (Entwicklersprache), **kein klickbares Element** | genau ein Zustand |
| M12 | Zitatblock | `surface.sunken`, Etikett + Lesezeit, eigener Scroll, mono | vorhanden · leer (Quelle stumm) · gekürzt (mit Byte-Angabe) |
| M13 | Alarmband | `danger.ground` + `danger.on-ground`, Marke + Wort, `role="alert"` | max. 1 pro Bildschirm; bleibt bis Sitzungsende |
| M1 | Statusleiste | je Lampe: Aussage + Erkenntnisgrad + **Messzeitpunkt** + Sprungziel; scrollt nie weg, kollabiert auf Tick-Kante | alle 8 (im Schaustück: 8 Lampen = 8 Zustände) |
| M3 | Bestätigung mit Konsequenz | Zitat → exakte Nutzlast (**vor** der Taste, größte Auszeichnung) → Zeitbudget → 2 Tasten ungleichen Gewichts; Esc = nichts senden; Fokusfalle + Fokusrückgabe | offen · abgelaufen („nothing was sent" als **eigener** Zustand) · Fehler (fett: nothing was sent) · nicht offen |
| M4 | Ereignisstrom | Zeitspalte (tabular) · Filtermatrix Kategorie×Level **mit sichtbaren Nullen** · permanente **Deckungszeile** (was der Strom sieht und was nicht) | Liste · leer · Filter leer · Kategorie ohne Emitter (╌ + 0) · Listener verloren |
| M2 | Aktion mit Vorbedingungen | Titel + Konsequenzklassen-Chip · Vorbedingungsliste (je Zeile der Fehlercode, der sonst flöge) · Konsequenz wörtlich + Größe · Taste mit „was sie freischalten würde" | **alle 8**, je als eigene Karte gezeichnet |
| M14 | Systemblatt / Legende | Farbe, Form, Klasse, Taste **im Produkt** erklärt | statisch; Pflichtbestandteil — sonst bleibt die zweite Kodierung ungelernt |

Zwei Regeln, die aus Messungen stammen und für alle Bauteile gelten:

- **Die Konsequenz-Taste** ist akzentgefüllt (bedienbar) mit `border.strong`-Kante in
  attention (kostet eine Entscheidung) — nie zustandsgefüllt (C §8.3, beim Bauen gemessen).
- **Erklären statt verbieten:** deaktiviert ist nie nur grau; wirklich verriegelt
  (`locked`) ist kein `<button>`, sondern Text mit Grund.

---

## zustands-matrix

**Acht Zustände** — die sechs des Bestands-Skills `async-state-coverage` plus zwei:

| Zustand | Definition | Abnahmekriterium (prüfbar) |
|---|---|---|
| `idle` | noch nichts angefordert | nennt, was passieren wird, und den Auslöser |
| `pending` | Anfrage läuft | nennt was + seit wann; statische Skelettzeilen |
| `success` | Daten da | Inhalt **+ Herkunftszeile** |
| `empty` | erfolgreich, Ergebnis leer — **ein Erfolg** | Erfolgssprache, Neutralfarbe, nie „Fehler"; unterscheidbar von `unavailable` |
| `partial` | Teil da, Teil fehlt/weicht ab | Zählung `n/m`; eigener Zustand, kein Fehler |
| `failed` | Anfrage gescheitert | Code + Felder + Klartext + Handlungszeile; **bleibt stehen** |
| `unavailable` | Lücke des **Werkzeugs** | M10-Muster; kein Bedienelement darin |
| `locked` | strukturell verweigert | Schraffur + Wort + Grund; kein `<button>`, kein Fokus |

`empty`, `unavailable` und `locked` sind drei verschiedene Wahrheiten und sehen dreimal
anders aus — das ist die Kernunterscheidung, die die meisten Systeme nicht treffen.

**Enumerationsregel** (übernommen aus der Erhebung, hier gesetzt): eine Fläche = eine
Region mit eigener Datenquelle/Anforderung; mechanisch eine Zeile je
Lade-/Abfrage-Aufrufstelle plus jede Fläche an einem Push-Strom. **Zellwerte:** genau drei
(`gezeichnet` mit exaktem Text · `entfällt` mit Grund · `offen`); Abdeckung =
gezeichnet / (Zellen − entfällt); vollständig ⇔ offen = 0. Die Matrix wird als
maschinenlesbare Datei geführt (YAML je Fläche × 8 Schlüssel), die Markdown-Tabelle wird
generiert — dieselbe Mechanik wie Token → CSS.

---

## anforderungs-abdeckung

| Anforderung (Auftrag) | Wo erfüllt | Beleg |
|---|---|---|
| 1 Token-System, geschichtet, Standard | `token-architektur` | tokens.dtcg.json, Schema-Validierung PASS |
| 2 Semantische Schicht + strukturelle Verwechslungs-Verhinderung | `farbsystem`, Invariante I1; unbekannt/gesperrt/abgeleitet sind **Form**-Rollen, keine Farben | Schaustück §2; accent kommt in keinem state-Token vor |
| 3 Form als zweite Kodierung | `farbsystem` (6 Marken), M7/M8 | Schaustück §3, reines CSS |
| 4 Typografie, System-Stacks, begründet | `schriftsystem` | Browser-Messung: exakt 7 Stufen |
| 5 Bauteile mit ALLEN Zuständen | `bauteil-katalog`, M2 mit 8 Karten | verify: 8 stateTags, 8 Galerie-Zustände |
| 6 Themes | `modus-festlegung`: beide, gleich sorgfältig | 72 Kontrast-Checks, 2×36, 0 Fails |
| WCAG SC 1.4.3 (Text ≥4.5) | alle Text-Token gerechnet | contrast-lauf.txt; 26 Zahlen im Schaustück nachgerechnet |
| WCAG SC 1.4.1 (Farbe nie allein) | Marken + Wörter + Formen überall | Schaustück §3/§8 |
| WCAG SC 1.4.11 (Grafik ≥3) | `line.control`, Marken, Fokusring gerechnet | contrast-lauf.txt |
| WCAG SC 4.1.2 (Namen) | alle Buttons benannt | Browser: `unnamedButtons: 0` |
| WCAG SC 4.1.3 (Statusmeldungen) | `role="status"` an Ergebnis-/Ablaufmeldungen, `role="alert"` am Alarmband | Browser: roleStatus 2, roleAlert 1 |
| WCAG SC 2.4.7 (Fokus sichtbar) | `:focus-visible` 2 px accent + 2 px Versatz auf jedem Element | CSSOM-Messung: Regel vorhanden, Token lösen auf |

---

## barrierefreiheit-bewegung

- **Fokus:** ein Ring für alles — `focus.width` (2 px) `interactive.accent` mit
  `focus.offset` (2 px), gemessen ≥ 4.78:1 gegen alle drei Gründe in beiden Themen.
- **Bewegung:** `motion.none` ist der Systemwert. Einzige Ausnahme: Fortschritt/Countdown;
  unter `prefers-reduced-motion` Zahlensprünge statt Balken. Ladezustände sind statische
  Skelette. Browser-gemessen am Schaustück: `animatedElements: 0`.
- **Farbe nie allein:** jede semantische Aussage trägt Form + Wort (SC 1.4.1); die
  Filtermatrix zeigt Nullen als Zahl, nicht als Farbe.
- **Kontrast:** 72 Kombinationen gerechnet, 0 unter Schwelle; Hausreserve 5.0 für Text.
- **Grenze der gelieferten Form:** ohne `<html>`-Tag kann das Schaustück kein
  `lang`-Attribut tragen (SC 3.1.1 ist dort nicht erfüllbar); im echten Produkt mit
  `<head>` entfällt das Problem. Ehrlich benannt statt wegerklärt.

---

## prototyp-messung

**Selbstprüfung** (`verify_showcase.py`, Rohlauf `verify-lauf.txt`): 16/16 PASS —
reines ASCII (0 Bytes > 127) · beginnt mit `<title>`, dann `<style>`, kein
doctype/html/head/body · Tag-Balance 0/0 · 0 externe Requests · **0 literale font-sizes** ·
**26 Kontrastzahlen nachgerechnet, 0 falsch** · 3 Digests nachgerechnet · kein
zusammenhängendes 64-Hex im Quelltext · 8 Zustände in Galerie und Kartenreihe · alle
tokens.css-Werte enthalten · 0 unbenannte Buttons. Statistik: 73 199 Bytes, 974 Zeilen.

**Browser-Messung** (echtes Chrome, lokaler Server, danach beendet — `messung-browser.txt`):

```
bodyHorizontalScroll     false
unmanagedOverflowCount   0        (nach Korrektur; vorher 2)
distinctFontSizes        [10,11,12,13,15,18,22px]  = exakt die deklarierte Skala
theme toggle             dunkel->hell->dunkel, aria-pressed korrekt
aria                     roleAlert 1 · roleStatus 2 · buttons 23 · unnamed 0
hashGroups               [8,8,8]
animatedElements         0
focusRule (CSSOM)        :focus-visible { outline: var(--focus-w) solid var(--accent); offset: var(--focus-off) }
focusTokens aufgelöst    2px / 2px / #5D9FD6
```

**Zwei Fehler, die erst die Messung fand — behoben, nicht wegerklärt:**

1. Die Paletten-Tabellen liefen in `.scopeBody` unkontrolliert über
   (`unmanagedOverflowCount: 2`). Korrigiert: `.scopeBody` erhielt `overflow-x:auto` —
   die Regel „breite Inhalte scrollen im eigenen Container" galt jetzt auch für die
   Fläche, die sie erklärt.
2. Der Fokusring war per JS-`focus()` nicht messbar — `:focus-visible` greift korrekt nur
   bei Tastatur. Die Messung wurde umgestellt (CSSOM-Regel + Token-Auflösung), nicht der
   Ring aufgeweicht: ein `:focus`-Ring für Mausklicks wäre die falsche Korrektur gewesen.

---

## prototyp-reproduzierbarkeit

Eine Quelle, drei generierte Ausgaben, eine Rückprüfung:

```
contrast.py   (Paletten + Rechner, kalibriert am 4.54-Referenzfall)
   -> gen_tokens.py  erzeugt  tokens.dtcg.json + tokens.css + palette-rows.html
   -> showcase.html  bettet   tokens.css-Werte + Tabellenzeilen ein
   -> verify_showcase.py  prüft: eingebettete Werte == tokens.css, angezeigte
      Kontraste == Rechnung, eingebetteter Digest == sha256(tokens.dtcg.json)
```

Kein Hex-Wert und keine Kontrastzahl ist von Hand getippt. Ein erneuter
`gen_tokens.py`-Lauf erzeugt bytegleiche Token-Dateien (deterministische Serialisierung);
ändert jemand die Quelle, bricht `verify_showcase.py` beim Digest-Vergleich — Drift
zwischen Quelle und Schaustück ist damit ein Prüf-Fehler, kein stiller Zustand.

---

## herkunft-beispielwerte

Vier Klassen (Muster aus B §11.2 — die A33-Klausel):

- **Real berechnet:** der „verified"-Digest ist `sha256(tokens.dtcg.json)` (von
  `verify_showcase.py` nachgerechnet); das Mismatch-Paar ist `sha256("uname -a")` gegen
  `sha256("uname -a\n")` — beide reproduzierbar nachrechenbar, der Unterschied ist genau
  ein Byte, was den Lawinensatz daneben *wahr* macht. Alle 26 Kontrastzahlen: gerechnet.
- **Beispielwerte in echter Form:** Zeitstempel (`21:18:04Z`, RFC-3339-Stil), Lauf-ID
  (`20260724T211804Z`), Fehlercodes mit Feldern (`FILE_TOO_LARGE{max_bytes:5242880}`),
  Zähler (`4/12`, `11/12`) — als Demo-Inhalte gekennzeichnet, Formen aus dem C/B-Material.
- **Wörtlich übernommen:** die Schriftstacks und die Kern-Neutraltöne des dunklen Themas
  aus C (bewusste Adoption der gemessen begründeten Werte); die Regelursprünge sind je
  Stelle zitiert.
- **Bewusst nicht gezeigt:** keine echten Fingerprints, keine Secrets, kein
  zusammenhängendes 64-Hex im Quelltext (Digests stehen nur in 8er-Gruppen; die
  Kopiertaste setzt sie zusammen) — der hauseigene Secret-Hook hat genau das beim ersten
  Schreibversuch erzwungen, und die Gruppierung war ohnehin die typografische Regel.

---

## bewusste-auslassungen

| Auslassung | Klasse | Grund + Entsprechung |
|---|---|---|
| Ikonografie-Set | will-nicht (jetzt) | Marken + Wörter tragen alles Bisherige; ein Icon-Set ist eine eigene Entwurfsrunde mit eigener Messung. Im Schaustück: kein einziges Icon, nichts fehlt. |
| Diagramm-/Chart-Stile | will-nicht | Existing-First: der `dataviz`-Skill existiert mit eigenem Palette-Swap-Mechanismus; dieses System liefert ihm die Palette, ersetzt ihn nicht. |
| Bewegung jenseits Fortschritt | will-nicht | `motion.none` ist die Entscheidung, nicht das Fehlen (R9 + reduced-motion). |
| Markenzeichen (Adler) im Schaustück | darf-nicht | C §15.1 gilt fort: es existiert kein freigegebenes Asset ohne Schriftzug im Repo; ein Platz ist definierbar, ein Bild wäre eine ungeklärte Ableitung. |
| Komponenten-Code-Bibliothek | kann-nicht (hier) | Dieses System liefert Token + Muster + Abnahmekriterien; Implementierung ist je Produkt/Framework. Das Schaustück beweist die Umsetzbarkeit in reinem CSS. |
| CI-Verdrahtung (tdiff, Schema-Check als Gate) | will-nicht (hier) | Empfehlung steht in `token-architektur`; die Entscheidung, in welcher Pipeline (Gitea-SSOT!), gehört dem Plugin-Team, nicht dem Gestalter. |
| Ein-Welt-Festlegung | will-nicht | Haus-Grundlage trägt beide Welten; ein Produkt darf sich festlegen (Token-Tausch, I4) und dokumentiert das dann als eigene Modus-Entscheidung. |

---

## risiken

1. **danger dunkel = 4.58:1** liegt 1.8 % über AA und unter der Hausreserve. Wer die
   Nutzungsregel (Text nur auf ground) beim Ableiten eines Produkts ignoriert, ist
   numerisch legal und praktisch grenzwertig. Merkbar: `contrast.py` druckt die Zeile mit
   „Regel nötig"; Gegenmittel: die Regel reist im Token (`$extensions.…rule`) mit.
2. **Doppelte Pflege Schaustück/Token.** Die Palette steht generiert im Schaustück —
   wer sie dort von Hand ändert, erzeugt Drift. Merkbar: `verify_showcase.py` schlägt an
   (Werte-Abgleich + Digest). Das Skript muss dafür *laufen* — ohne Aufrufer verrottet es
   wie jeder Generator (Plugin-Befund SKILLS_INDEX). 
3. **Alias-Bruch beim Theme-Editieren.** Ändert jemand `ink.secondary` hell, wandert
   `state.neutral` hell mit — gewollt, aber überraschend für Fremde. Merkbar: der Alias
   steht ausdrücklich in Token-`$description` und Paletten-Tabelle.
4. **Schraffur unter 8 px** wird zu Grau. Regel: `mk-hatch` nie unter 8 px setzen; Chips
   tragen zusätzlich das Wort. Ein Kontrast-Test fängt das nicht — nur Sichtprüfung.
5. **`:focus-visible` ist per JS nicht messbar** — künftige Messwellen könnten fälschlich
   „kein Fokusring" melden (Negativ-Befund-Falle). Die korrekte Messform (CSSOM + Token)
   steht in `messung-browser.txt`; genau dieser Fehlschluss ist dort dokumentiert.
6. **Die gelieferte Dateiform** (kein `<head>`) erzwingt reines ASCII mit Entitäten und
   verhindert `lang`. Jede spätere Bearbeitung der Datei muss die ASCII-Disziplin halten;
   `verify_showcase.py` prüft sie. Im echten Produktbau entfällt beides.
7. **Zwei Themen = doppelte Zustands-Sichtprüfung.** Die Kontraste sind automatisiert,
   die *Gestalt* jedes Zustands im zweiten Thema nicht. Merkbar: Schaustück im hellen
   Thema durchsehen (ein Klick) — das ist die verbleibende Handarbeit je Änderung.

---

## nicht-geprueft

Ehrlich benannt, was dieser Entwurf **nicht** belegt:

- **Kein `tdiff`-Lauf, kein Resolver-File gebaut** — die Versionierungs-Empfehlungen
  stützen sich auf die Extern-Erhebung (Registry-Metadaten), nicht auf eigene Läufe.
- **Keine Schema-Validierung des Resolver-Schnitts** — `color.dark/light` als Sets sind
  resolver-tauglich geschnitten, ein `resolver.json` wurde nicht geschrieben.
- **Kein Screenreader-Lauf.** `role`/`aria`-Muster sind gesetzt und gezählt (1× alert,
  2× status, 0 unbenannte Buttons), aber nicht mit VoiceOver/NVDA gehört.
- **Keine Messung auf Windows/Linux** — die Font-Stack-Begründung dort ist aus C
  übernommen (dessen Bestandsmessung), nicht von mir auf diesen Systemen geprüft.
- **Hover-Zustände nicht einzeln kontrastgeprüft** (tint-Hover über raised); die
  Ink-auf-Tint-Kompositwerte sind gerechnet, Hover-Kombinationen über raised nicht.
- **`ARCHITEKTUR.md` im selben Ordner stammt nicht von mir** (Parallel-Arbeit eines
  anderen Team-Agenten, mtime 16:28); ich habe sie weder gelesen noch verändert — meine
  Aussagen sind nicht mit ihr abgeglichen.
- **Browser-Messung nur in Chrome** (via MCP), Fensterbreite 856 px — schmaler als der
  900-px-Härtetest, was die Überlauf-Prüfung eher verschärft; andere Browser ungeprüft.
- **`_pyvendor/` und `dtcg-format-schema.json`** sind Prüf-Werkzeug-Artefakte im
  Arbeitsordner (lokal vendored jsonschema, lokal gesichertes Schema); sie gehören nicht
  zur Auslieferung und sind hier deklariert statt still hinterlassen.
- Außerhalb von `scratchpad/designsystem/` wurde **nichts** geändert; kein git, kein
  Commit, der lokale Messserver wurde nach der Messung beendet.
