# Anatomie von `design-system/`

## Warum an der Plugin-Wurzel und nicht in `skills/design/references/`

Das System ist **Daten mit eigener Lebensdauer**. Es muss lesbar sein, ohne dass ein
Modell einen Skill laedt — von der CI, von einem Build-Werkzeug, von einem fremden
Projekt. Und es darf nicht an die Skill-Version gekoppelt sein: ein Skill kann sich
aendern, ohne dass ein Token sich aendert, und umgekehrt.

Der Preis ist eine Aufloesung ausserhalb des Skill-Verzeichnisses. Er wird in
`scripts/design_lib.py::find_design_system` bezahlt.

## Aufloesungsreihenfolge

```
1. $AIE_DESIGN_SYSTEM             (explizit gesetzt)
2. <plugin-root>/design-system    (der Normalfall)
3. ./design-system                (Projekt bringt sein eigenes mit)
```

Kein Treffer → `DesignSystemNotFound` **mit der Liste der geprueften Orte**.
Ausdruecklich **kein** eingebauter Vorgabe-Satz: ein stiller Fallback auf erfundene Token
waere ein Mock im Produktivpfad. Ein System, das nicht da ist, ist nicht da.

## Der Inhalt

| Datei | Was | Erzeugt? |
|---|---|---|
| `VERSION` | eine Zeile SemVer. **Die** Quelle. Nirgends sonst getippt. | nein |
| `MANIFEST.json` | Zaehlungen, Hashes, Alias-Liste | **ja** — `design-report.py` |
| `tokens.dtcg.json` | 93 Token, DTCG 2025.10. Die Wertequelle. | **ja** — `tools/gen_tokens.py` |
| `tokens.css` | CSS-Custom-Properties beider Themen | **ja** — `tools/gen_tokens.py` |
| `contrast-pairs.json` | die **erklaerten** Farbpaare mit Schwelle und Ort | nein |
| `states.json` | Flaeche × 8 Zustaende, drei erlaubte Zellwerte | nein |
| `showcase.html` | das Schaustueck, selbst-enthalten, ohne Server | nein |
| `components/M01..M14.md` | 14 Bauteile mit Zustandsliste | nein |
| `TEMPLATE.md` | die leere Vorlage, Profil `produkt` | nein |
| `DESIGN-SYSTEM.md` | das Referenzdokument (Fable 5) | nein |
| `STATUS.md` | aktiviert / gemessen / genutzt | nein |
| `CHANGELOG.md` | zwei Versionsachsen, Breaking-Tabelle | nein |
| `migrations/` | eine Datei je MAJOR. Heute leer. | nein |
| `schema/dtcg-format-2025.10.json` | **vendored**, 56523 B | nein |
| `schema/document-schema.json` | Pflicht-Slugs, zwei Profile | nein |
| `tools/contrast.py` | der kalibrierte Rechner | nein |
| `tools/gen_tokens.py` | Generator | nein |
| `tools/verify_showcase.py` | Selbstpruefung des Schaustuecks | nein |

## Warum das Schema vendored ist

`https://www.designtokens.org/schemas/2025.10/format.json` ist erreichbar (HTTP 200,
56523 Bytes, selbst nachgemessen). Es liegt trotzdem **als Datei im Repo**:

1. Die CI laeuft dann ohne Netz.
2. Ein Schema-Wechsel wird ein sichtbarer Commit statt einer stillen Verhaltensaenderung.

**Nie** `tr.designtokens.org` verlinken — das leitet auf die Drafts-Fassung um, und die
traegt ausdruecklich „do not implement anything in this document". Immer `/TR/2025.10/`.

## Die Erzeugungskette

```
tools/contrast.py        Paletten + Rechner (kalibriert an #FFFFFF/#767676 = 4.54:1)
   └─> tools/gen_tokens.py     erzeugt  tokens.dtcg.json · tokens.css · tools/palette-rows.html
         └─> showcase.html     bettet   die erzeugten Werte ein
               └─> tools/verify_showcase.py   prueft zurueck:
                     eingebettete Werte == tokens.css
                     angezeigte Kontraste == Rechnung
                     eingebetteter Digest == sha256(tokens.dtcg.json)
```

Kein Hex-Wert und keine Kontrastzahl ist von Hand getippt. Ein erneuter Lauf erzeugt
bytegleiche Dateien — **selbst nachgemessen**, auch aus fremdem Arbeitsverzeichnis.

Wer die Quelle aendert, ohne neu zu erzeugen, bricht `verify_showcase.py` beim
Digest-Vergleich. Drift ist damit ein Pruef-Fehler, kein stiller Zustand.

## Die Grenze dieser Kette — ehrlich

`verify_showcase.py` muss **laufen**, um zu wirken. Ohne Aufrufer verrottet es wie jeder
Generator. Hausbeweis: `SKILLS_INDEX.md` traegt den Vermerk „Regenerate manually" und
nennt zwei Skills, die es nicht gibt. Der Aufrufer ist deshalb die CI, nicht die Absicht.
