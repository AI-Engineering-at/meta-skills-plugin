# CHANGELOG — AIE Design-System

Dieses Paket fuehrt **zwei Versionsachsen**, weil SemVer allein hier luegen wuerde:

- **`VERSION`** (SemVer) traegt den **Vertrag**: gibt es das Token, heisst es noch so,
  bedeutet es noch dasselbe.
- **`visual-epoch`** (ganze Zahl im MANIFEST) traegt das **Aussehen**.

Grund: eine Farbwertaenderung bricht keinen Vertrag, aber jedes Screenshot. Wer nur
SemVer fuehrt, muss sich zwischen zwei Luegen entscheiden. `visual-epoch` bumpt **nur
Fable 5** — das ist die einzige Stelle, an der die Rollenzuweisung in einer Zahl steht.

## Was ist ein Breaking Change an einem Token

| Aenderung | Stufe | Grund |
|---|---|---|
| Token entfernt | **MAJOR** | Referenzen brechen |
| Token umbenannt | **MAJOR** | dito — ein Alias ist die MINOR-Alternative |
| `$type` geaendert | **MAJOR** | Build-Werkzeuge brechen |
| Bedeutung geaendert bei gleichem Namen | **MAJOR** | die stillste und schlimmste Sorte |
| Nutzungsregel verschaerft (`gilt nicht fuer` erweitert) | **MAJOR** | verbietet nachtraeglich bestehende Nutzung |
| Slug im Dokument-Schema entfernt/umbenannt | **MAJOR** | jedes DESIGN.md bricht |
| Zustand aus `states.json` entfernt | **MAJOR** | Matrizen werden unvollstaendig |
| Token ergaenzt | MINOR | |
| `$deprecated` mit Ersetzungstext gesetzt | MINOR | Entfernen erst in der naechsten MAJOR |
| Modul ergaenzt · Bauteil ergaenzt | MINOR | |
| Wert geaendert, Bedeutung gleich | **PATCH** + `visual-epoch`++ | z. B. Kontrastreparatur |
| `$description` praezisiert | PATCH | |

**Ehrliche Luecke:** „Bedeutung geaendert" ist nicht maschinell erkennbar. Ein
`$description`-Diff kann Kandidaten *melden*; die Einstufung ist ein menschliches Urteil.
Hier wird nicht behauptet, das automatisiert zu haben.

**Diff-Werkzeug:** `@adobe/token-diff-generator` (`tdiff`, Apache-2.0) ist als Adoption
vorgesehen — `deleted` oder `renamed` in der Ausgabe erzwingt einen MAJOR-Bump.
**Es ist bis heute nicht ausgefuehrt worden** (siehe `STATUS.md`). Bis dahin gilt der
reduzierte Eigenvergleich, der „umbenannt" nicht erkennen kann und das ausdruecklich
meldet — kein stiller Downgrade.

---

## 1.0.0 — 2026-08-01

Erste Fassung. Das System wird aus drei UI-Entwuerfen desselben Tages herausgeloest:
Entwurf C („Der Kontrollraum") als Vorbild fuer die Dokumentqualitaet, Entwurf B
(„Die Ermittlungsakte") fuer vier Abschnitte, die C fehlten.

**Gestaltung:** Fable 5 (`claude-fable-5`). Farbe, Schrift, Form, Skala und
Bauteil-Festlegungen stammen vollstaendig von ihm und sind hier unveraendert uebernommen.

### Dazu

- **93 Token** im DTCG-2025.10-Format, ein einziges `tokens.dtcg.json` als Quelle.
  Verwendete `$type`: `color` (Objektform mit `colorSpace`/`components`/`hex`),
  `fontFamily`, `dimension`, `number`, `duration`. Abweichungen vom Standard: keine.
  Alles Hauseigene liegt in `$extensions` unter `at.ai-engineering.design`.
- **Zwei Themen** (`color.dark` Referenz, `color.light` gleich sorgfaeltig gerechnet),
  als Sets fuer den **publizierten** Resolver 2025.10 geschnitten.
- **Kontrast reist im Token mit:** jedes Farb-Token traegt seine gerechneten Werte und
  seine Nutzungsregel in `$extensions`. Die Abnahmebedingung ist nicht Prosa daneben.
- **Alias-Ebene:** `state.neutral.base` ist ein DTCG-Alias auf `ink.secondary`. Damit ist
  die im Rohmaterial gemessene stille Duplikation (`--fog` == `--ink-dim`, derselbe Hex
  unter zwei Namen) eine deklarierte Absicht mit Migrationspfad.
- **15 Token-Kategorien** statt zwei. Gemessen war im Rohmaterial nur Farbe und
  Schriftstack tokenisiert; Typo-Skala, Abstand, Radius, Kante, Fokus, Dichte und
  Umbruchpunkte waren ueberall Literale. Genau diese Luecke verhindert Wiederverwendung.
- **14 Bauteile** (`components/M01..M14.md`) mit vollstaendiger Zustandsliste je Bauteil.
- **8 Zustaende**: die sechs des Bestands-Skills `async-state-coverage`
  (idle/pending/success/empty/partial/failed) plus `unavailable` (Luecke des *Werkzeugs*)
  und `locked` (strukturell verweigert). Kein zweites Vokabular erfunden.
- **Dokument-Schema mit zwei Profilen** (`haus`, `produkt`), damit das Referenzdokument
  sein eigenes Schema bestehen kann.

### Gemessen bei der Aufnahme ins Plugin

| Was | Kommando | Ergebnis |
|---|---|---|
| Kette reproduzierbar | `gen_tokens.py`, dann `shasum -a 256` | bytegleich, auch aus fremdem cwd |
| Schaustueck haelt seine Regeln | `verify_showcase.py` | 16/16, FAILS 0 |
| Kontrast aus der Token-Datei | `design-contrast.py --ci` | 72 Rechnungen, 0 Fails |
| Zustands-Matrix | `design-states.py --coverage` | 120 Zellen, 80.3 %, 13 offen |
| Farben ausserhalb des Satzes | `design-lint.py --all` | 0 Befunde |
| Dokument gegen eigenes Schema | `design-doc.py --check DESIGN-SYSTEM.md` | 20/20, 0 Fehler |
| Sperre lehnt wirklich ab | `pre-write-design-token-guard-test.py` | 12/12, davon 4 deny |

### Bewusst nicht enthalten

Ikonografie-Set (will-nicht) · Diagramm-Stile (will-nicht, Existing-First: `dataviz`) ·
Bewegung jenseits Fortschritt (will-nicht, `motion.none` ist die Entscheidung) ·
Markenzeichen (darf-nicht, kein freigegebenes Asset) · Komponenten-Code-Bibliothek
(kann-nicht hier, je Produkt) · L4-Module (nicht gebaut, siehe `STATUS.md`) ·
`resolver.json` (nicht geschrieben).
