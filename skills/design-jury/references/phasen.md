# Die sieben Phasen

**P0–P5 laufen ohne den Menschen. P6 ist der einzige Ort, an dem er handeln MUSS.**

Das ist die eigentliche Korrektur gegenueber dem alten Skill: der fragte acht Mal nach
einer Kategorie und nannte das Kooperation. Acht Einzelauswahlen ergeben einen
Kompromiss. Eine Wahl zwischen drei fertigen, vermessenen Weltbildern ergibt eine
Entscheidung.

---

## P0 — Bestand

**Ein:** Projektwurzel · **Aus:** `00-bestand.md`

Existing-First, bevor irgendetwas entworfen wird. Jede vorhandene Design-Quelle mit Pfad:
bestehende `DESIGN.md`, CSS-Variablen, Token-Dateien, Style-Guides, das Haus-System.

**Gate:** Datei existiert und nennt jede Quelle mit Pfad. Ein leeres `00-bestand.md` ist
zulaessig — aber nur als **Befund** („nichts gefunden, gesucht wurde in …"), nie als
uebersprungene Phase.

---

## P1 — Messung

**Ein:** Codebasis, echte Daten · **Aus:** `01-belege.md`

Eine Tabelle `Behauptung | Beleg`. Jede Zeile braucht eine Fundstelle `datei.ext:zeile`
oder ein Kommando mit seiner Ausgabe.

**Gate:** jede Tabellenzeile hat eine Fundstelle.

**Warum das die haerteste Zahl im Verfahren ist:** ueber die drei Ausgangsentwuerfe
gemessen — 0 / 15 / 22 Fundstellen bei 21,5 / 36,5 / 36,0 Punkten. Der Entwurf ohne
Belege war der abgeschlagene. Die Belegdichte ist das **einzige** Merkmal, das die
Bewertung mechanisch reproduziert.

---

## P2 — Rahmung

**Ein:** `01-belege.md` · **Aus:** `02-rahmungen.json`

K ≥ 3 einander **ausschliessende** Thesen, je mit Achsenwerten.

**Gate:** `design-divergence.py --rahmungen … --ci` — K ≥ 3 **und** fuer jedes Paar
mindestens 2 verschiedene Achsen.

Die Achsen sind generisch und wertfrei. **Welche Werte** eine Achse annehmen kann, legt
Fable 5 fest.

---

## P3 — Entwurf

**Ein:** je eine These + der Fat-Brief · **Aus:** `entwuerfe/<id>/{spec.md, mockup.html, build.py}`

K Laeufe, **isoliert** — kein Entwerfer sieht die Entwuerfe der anderen. Sonst konvergieren
sie, und die Divergenz aus P2 war umsonst.

**Gate:**
- Slug-Vollstaendigkeit (`design-doc.py --check --profil produkt`)
- Attrappe **selbst-enthalten**: kein externer Request, keine Fremdschrift, kein Server
- `build.py` erzeugt die Attrappe **bytegleich** reproduzierbar
- Frontmatter je Entwurf vollstaendig: `entwurf-id`, `titel`, `autor`, `modell`,
  `erzeugt`, `achsen`, `these`, `build-sha256`

---

## P4 — Sonden

**Ein:** K Attrappen · **Aus:** `04-messung.json`

Dieselben Sonden ueber **alle** K. Symmetrie ist das ganze Gate: ungleiche Sonden erzeugen
Unterschiede, die es nicht gibt.

Mindestens: Palettenmenge · distinkte Schriftgroessen · Seitwaerts-Scroll des Koerpers ·
unkontrollierte Ueberlaeufe · ARIA-Rollen · unbenannte Bedienelemente · Radienmenge.

**Gate:** identische Sondenschluessel ueber alle Entwuerfe.

---

## P5 — Linsen

**Ein:** K Entwuerfe + `04-messung.json` · **Aus:** `05-linsen.md`

L Linsen × K Entwuerfe. Jede Zelle: Befund + Beleg + Wertung + Gewicht.

**Gate:**
- keine Zelle leer
- jede Wertung hat einen Beleg
- **keine Anweisungssprache** — das ist die Fable-5-Grenze, maschinell geprueft

---

## P6 — Entscheidung

**Ein:** `05-linsen.md` · **Aus:** `06-entscheid.md`

**`AskUserQuestion`.** Hier und nur hier haelt der Ablauf an.

Vorgelegt wird: je Entwurf die These in einem Satz, die Linsen-Summe, die staerksten
Befunde beider Richtungen. **Nicht** vorgelegt wird eine Empfehlung des Modells — die
Rangfolge ist Information, die Wahl ist die des Menschen.

`06-entscheid.md` haelt fest: **wer** entschieden hat, **wann**, **welcher** Entwurf,
**warum**, und was aus den nicht gewaehlten uebernommen wird.

---

## P7 — Kanonisierung

**Ein:** `06-entscheid.md` · **Aus:** `DESIGN.md`, `tokens.overrides.json`, `states.json`

**Gate: kein Schreiben ohne `06-entscheid.md`.** Das ist die mechanische Fassung des
Kernsatzes — ohne die Entscheidungsdatei entsteht kein kanonisches Dokument.

Nicht gewaehlte Entwuerfe bleiben liegen. Sie sind die Begruendung der Wahl.
