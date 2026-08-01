# Die Artefakte, Feld fuer Feld

Sieben Phasen, sieben Pflichtdateien. Jede ist ein Gate — fehlt sie, geht es nicht weiter.

---

## `00-bestand.md`

| Feld | Pflicht |
|---|---|
| gesuchte Orte | ja — auch wenn nichts gefunden wurde |
| gefundene Quellen mit Pfad | ja |
| Haus-System-Version | ja |

Ein leerer Bestand ist zulaessig — als **Befund**, nie als uebersprungene Phase.
„Nichts gefunden" ist eine Aussage; sie braucht die Liste der Orte, an denen gesucht wurde.

---

## `01-belege.md`

Tabelle `Behauptung | Beleg`. Jede Zeile: `datei.ext:zeile` **oder** Kommando + Ausgabe.

Keine Zeile ohne Beleg. Keine Behauptung, die auf eine Zusammenfassung zeigt.

---

## `02-rahmungen.json`

```json
{ "entwuerfe": [ { "id": "…", "these": "…", "achsen": { … } } ] }
```

K ≥ 3 · alle Entwuerfe fuehren dieselben Achsen · paarweise ≥ 2 Unterschiede.

---

## `entwuerfe/<id>/spec.md`

Nach `design-system/TEMPLATE.md`, Profil `produkt`. Frontmatter siehe
`entwurfs-brief.md` — `autor` und `modell` sind Pflicht.

## `entwuerfe/<id>/mockup.html`

Selbst-enthalten. Kein externer Request, keine Fremdschrift, kein Server, kein Port.

Das ist zugleich die Cross-Runtime-Entscheidung: eine selbst-enthaltene HTML-Datei laeuft
in Claude Code **und** in opencode. Eine Next.js-App tut das nicht.

## `entwuerfe/<id>/build.py`

Erzeugt `mockup.html` reproduzierbar, mit `assert`-Selbstpruefung. Der Nachweis gehoert in
den Slug `prototyp-reproduzierbarkeit`: Kommando + bytegleiches Ergebnis.

---

## `04-messung.json`

```json
{ "entwuerfe": [ { "id": "…", "sonden": { "palette": [], "fontSizes": [], … } } ] }
```

**Dieselben Schluessel ueber alle K.** Ungleiche Sonden erzeugen Unterschiede, die es
nicht gibt — das ist der haeufigste stille Messfehler.

---

## `05-linsen.md`

L×K Zellen. Je Zelle: **Befund · Beleg · Wertung · Gewicht.**

Keine Zelle leer · jede Wertung mit Beleg · **keine Anweisungssprache**.

Diese Datei ist die Reparatur eines gemessenen Lochs: die Bewertung, die zwischen den drei
Ausgangsentwuerfen entschied, existiert nirgends auf Platte.

---

## `06-entscheid.md`

Das **einzige** Artefakt, das ein Mensch erzeugt.

| Feld | Pflicht |
|---|---|
| wer entschieden hat | ja |
| wann | ja |
| welcher Entwurf | ja |
| warum | ja |
| was aus den nicht gewaehlten uebernommen wird | ja |
| was ausdruecklich verworfen wurde | ja |

Erzeugt ueber `AskUserQuestion`. Ohne diese Datei entsteht kein `DESIGN.md` — das ist der
Kernsatz des Skills in mechanischer Form.

---

## Was liegen bleibt

`entwuerfe/` wird **nicht** aufgeraeumt. Die nicht gewaehlten Entwuerfe sind die
Begruendung der Wahl und die Quelle fuer spaetere Uebernahmen. Wer sie loescht, behaelt
das Ergebnis und verliert den Grund.
