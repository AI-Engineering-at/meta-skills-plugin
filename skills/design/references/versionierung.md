# Versionierung und Updates

## Zwei Achsen, weil SemVer allein luegt

`design-system/VERSION` traegt **SemVer** fuer den *Vertrag*: Gibt es das Token? Heisst es
noch so? Bedeutet es noch dasselbe?

Ein zusaetzliches **`visual-epoch`** (ganze Zahl im MANIFEST) traegt das *Aussehen*.

Der Grund: eine Farbwertaenderung bricht **keinen Vertrag**, aber **jedes Screenshot**.
Wer nur SemVer fuehrt, muss sich zwischen zwei Luegen entscheiden — entweder er nennt eine
Kontrastreparatur MAJOR (und entwertet die Stufe) oder PATCH (und ueberrascht jeden, der
Bilder abgleicht).

**`visual-epoch` bumpt nur Fable 5.** Das ist die einzige Stelle, an der die
Rollenzuweisung in einer Zahl steht.

## Die Breaking-Tabelle

Kanonisch in `design-system/CHANGELOG.md`. Die sieben MAJOR-Faelle in Kurzform:
Token entfernt · Token umbenannt · `$type` geaendert · Bedeutung geaendert bei gleichem
Namen · Nutzungsregel verschaerft · Slug im Dokument-Schema entfernt/umbenannt ·
Zustand aus `states.json` entfernt.

**Die ehrliche Luecke:** „Bedeutung geaendert bei gleichem Namen" ist die stillste und
schlimmste Sorte — und sie ist **nicht maschinell erkennbar**. Ein `$description`-Diff
kann Kandidaten *melden*; die Einstufung ist ein menschliches Urteil. Hier wird nicht
behauptet, das automatisiert zu haben.

## Deprecation statt Loeschung

Ein Token verschwindet nie direkt. Der Weg ist:

1. **MINOR:** `$deprecated` setzen, mit Ersetzungstext. Das Token funktioniert weiter.
2. **MAJOR:** entfernen — und dann liegt eine Datei in `migrations/`.

`$deprecated` ohne Ersetzungstext ist ein Fehler. Eine Warnung, die nicht sagt, was
stattdessen gilt, erzeugt nur Ratlosigkeit.

## Diff: adoptieren statt bauen

`@adobe/token-diff-generator` (`tdiff`, Apache-2.0) erkennt added / deleted / renamed /
deprecated / updated. Vier Exakt-Namen-Proben auf Alternativen ergaben 404 — es gibt genau
dieses eine reife Werkzeug.

Vorgesehener CI-Ablauf: `tdiff` gegen die Vorversion → enthaelt die Ausgabe `deleted` oder
`renamed` und `VERSION` hat keinen MAJOR-Bump → **rot**. Die Markdown-Ausgabe wandert
angehaengt in den CHANGELOG, nicht getippt.

**Es ist nicht ausgefuehrt worden.** Der CI-Auftrag dafuer existiert noch nicht (siehe
`design-system/STATUS.md`). Die Fallback-Kette ist der eigene Mengenvergleich: er deckt
entfernt / ergaenzt / wertgeaendert ab, **nicht** „umbenannt" — das braucht Heuristik.
Laeuft er im reduzierten Modus, sagt er das ausdruecklich. Kein stiller Downgrade.

## Wie ein Projekt von einer neuen Version erfaehrt

| Weg | Ebene | Wirkung |
|---|---|---|
| `design-check.py` als Hinweis | additionalContext | „System 1.2.0, dein DESIGN.md haengt an 1.0.0" — **blockt nie** |
| `design-check.py --ci` im Projekt-CI | Auftrag | warnt bei MINOR, **bricht bei MAJOR ohne Migrationsdatei** |
| `CHANGELOG.md` + `migrations/` | Text | die Erklaerung |

Die Stufen sind bewusst ungleich hart. Ein Hinweis, der blockt, wird abgeschaltet; ein
Gate, das nur fluestert, wird ueberlesen.

## Die Kette, die im Plugin gerissen ist — und was daraus folgt

Gemessen im eigenen Repo: **ein einziger** Git-Tag (`v1.0.0`). `plugin.json` bei 4.5.1,
`CHANGELOG.md` endet bei 4.4.1, der `CLAUDE.md`-Titel sagt 4.4.0. Die Versionen 4.5.0 und
4.5.1 stehen nur in Prosa und in Commit-Titeln. 19 von 21 Skills tragen unveraendert
`version: 1.0.0`.

Es gibt also **keinen abrufbaren Stand X**. Ein Skill mit Versionierungsanspruch kann sich
dort nicht anhaengen — er muss seine eigene saubere Kette aufbauen und sie an sich selbst
vorleben. Genau deshalb hat `design-system/` eine eigene `VERSION`, einen eigenen
`CHANGELOG` und ein generiertes `MANIFEST` statt getippter Zahlen.
