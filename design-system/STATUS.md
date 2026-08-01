# STATUS — was aktiviert, gemessen und genutzt ist

Stand: 2026-08-01 · System-Version: siehe `VERSION`

Dieses Blatt folgt dem Muster von `integrations/opencode/STATUS.md`: ein Ort, der den
unfertigen Teil beim Namen nennt. **„Gebaut" ist keine Stufe.** Die Hausregel lautet
aktiviert + gemessen + genutzt — und nur die dritte Spalte entscheidet.

| Bauteil | gebaut | aktiviert | gemessen | genutzt |
|---|---|---|---|---|
| `tokens.dtcg.json` (93 Token, DTCG 2025.10) | ja | ja | ja — Schema-Validierung PASS (Fable 5, jsonschema 4.25.1) | ja — Quelle von `tokens.css` + Schaustueck |
| `tools/contrast.py` (Rechner) | ja | ja | ja — kalibriert an `#FFFFFF/#767676` = 4.54:1 | ja — von `design-contrast.py` importiert |
| `tools/gen_tokens.py` (Generator) | ja | ja | ja — Rebuild bytegleich (sha256 identisch, aus fremdem cwd) | ja |
| `tools/verify_showcase.py` | ja | ja | ja — 16/16 PASS, FAILS 0 | ja |
| `showcase.html` (Schaustueck) | ja | ja | ja — Chrome-Messung, 2 Fehler gefunden und behoben | ja — die Attrappe, an der alles haengt |
| `contrast-pairs.json` + `design-contrast.py` | ja | ja | ja — 72 Rechnungen, 0 Fails, exit 0 | **CI-Auftrag `design`** |
| `states.json` + `design-states.py` | ja | ja | ja — 120 Zellen, 80.3 % Abdeckung, 13 offen | **CI-Auftrag `design`** |
| `design-lint.py` | ja | ja | ja — 0 Befunde bei 44 Werten; 23 Fehlalarme im ersten Lauf gefunden und behoben | **CI-Auftrag `design`** |
| `pre-write-design-token-guard.py` | ja | ja — `hooks/hooks.json` | ja — **12/12, davon 4 echte deny** | ja |
| `design-report.py --check` | ja | ja | ja — Drift kuenstlich erzeugt, CI wurde rot (exit 1), nach Ruecksetzen gruen | **CI-Auftrag `design-report`** |
| `design-doc.py` + `document-schema.json` | ja | ja | ja — `DESIGN-SYSTEM.md` besteht sein eigenes Schema 20/20 | **CI-Auftrag `design`** |
| `components/M01..M14.md` | ja | ja | ja — 14 Dateien, aus `states.json` erzeugt | ja |
| `TEMPLATE.md` | ja | ja | ja — faellt korrekt durch, solange unbefuellt | noch **nicht** von einem echten Produkt benutzt |
| `design-resolve.py` + `.design-lock.json` | ja | ja | ja — nur an einem Testfall (`tmp_path`), **nicht an einem echten Projekt** | **nein** |
| `design-check.py` (Migration) | ja | ja | ja — nur an Testfaellen | **nein** |
| `design-divergence.py` | ja | ja | teilweise | **nein — kein echter Jury-Lauf** |

---

## Was ausdruecklich NICHT da ist

- **Kein Web-Konfigurator.** Der alte `design`-Skill verwies auf `vg-dashboard/` im
  Plugin. Selbst geprueft: `ls vg-dashboard` -> nicht vorhanden. Eine Next.js-App
  existiert unter `/Users/mackbook/code-aie/phantom-ai/vg-dashboard`, ist **nicht** mit
  diesem Skill versioniert, **nicht** adoptiert, und ihr Export hat 6 Abschnitte,
  waehrend das alte `export-schema.md` „ALL 8 sections MUST be present" forderte.
  Der Verweis ist gestrichen. Ersatz ist da und besser: die selbst-enthaltene
  HTML-Attrappe laeuft in Claude Code **und** opencode ohne Server, ohne Port.
- **Keine `modules/`.** ARCHITEKTUR.md sieht L4-Module vor (Erkenntnisgrad, Herkunft,
  Risikoklasse, Schutzstufe). `design-resolve.py --modules` kann sie laden und scheitert
  ehrlich, wenn es sie nicht gibt. Gebaut sind sie **nicht** — die Marken und Chips, die
  sie tragen wuerden, stecken heute in L1/L2. Ein leeres Modulverzeichnis waere ein
  Platzhalter; es gibt deshalb keines.
- **Kein `resolver.json`.** Die zwei Theme-Sets sind resolver-tauglich geschnitten, aber
  eine Resolver-Datei ist nicht geschrieben und nicht validiert.
- **Kein `tdiff`-Lauf.** `@adobe/token-diff-generator` ist als Adoption empfohlen und in
  `CHANGELOG.md` beschrieben — ausgefuehrt wurde es nie. Der CI-Auftrag dafuer existiert
  noch nicht. Bis dahin gilt der reduzierte Eigenvergleich, und er sagt das auch.
- **Kein Divergenz-Schwellwert.** `design-divergence.py` laeuft im Nur-Messen-Modus.
  Drei Entwuerfe eines Tages sind keine Verteilung; eine heute erfundene Zahl waere ein
  Platzhalter im Produktivpfad.
- **Der Migrationsfall „dein Override ist womoeglich ueberfluessig"** braucht den
  Vergleich zweier Basis-Staende und ist nicht gebaut. `--migrate` kennt heute zwei
  Faelle (Token existiert weiter / Token weg), nicht vier.

---

## Was sich grundsaetzlich nicht erzwingen laesst

Diese Liste ist Teil des Entwurfs, kein Eingestaendnis:

1. **Dass eine Farbe bedeutet, was ihre `$description` sagt.** Keine Maschine liest
   Bedeutung.
2. **Dass ein Divergenz-Grund ein Grund ist.** „weil" besteht jeden Lint. Deshalb das
   Ablaufdatum: die Zeit erzwingt das Gespraech, nicht die Grammatik.
3. **Dass Fable 5 die gestalterische Entscheidung wirklich getroffen hat.** `autor:`
   kann jeder tippen. Mechanisch erzwingbar ist nur, dass das Feld da ist — Buchfuehrung,
   kein Beweis.
4. **Dass die Zustands-Matrix alle Flaechen kennt.** Das Abdeckungsmass rechnet ueber die
   **eingetragenen** Flaechen. Eine vergessene Flaeche faellt nicht auf.
5. **Dass die Attrappe misst, was sie behauptet.** Die Sonden pruefen, was jemand als
   Sonde geschrieben hat.

---

## Offene Punkte mit Adresse

| Punkt | Wem gehoert die Entscheidung |
|---|---|
| Laeuft der Skill in opencode wirklich? (Dateiwahrheit ist geprueft, Laufzeitwahrheit nicht) | Plugin-Team — braucht einen echten Lauf mit beiden Werkzeugen |
| `tdiff` einhaengen oder beim Eigenvergleich bleiben | Plugin-Team |
| Wird `design-system/` ein eigenes Repo/Paket? | Eigentuemer |
| L4-Module bauen? | Fable 5 (Gestaltung) + Eigentuemer (Umfang) |
| Divergenz-Schwellwert | nach den ersten drei echten Jury-Laeufen, aus den Daten |
