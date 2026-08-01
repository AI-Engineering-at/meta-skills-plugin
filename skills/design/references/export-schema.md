# Export-Schema v1.0 — was ein DESIGN.md sein muss

**Vorgaenger: v0.2.** Migrationspfad steht unten.

## Die Struktur liegt nicht hier

Die kanonische Fassung ist **maschinenlesbar**:
`design-system/schema/document-schema.json`. Geprueft wird mit

```
python3 scripts/design-doc.py --check <datei> --profil haus|produkt
```

Diese Datei erklaert die Regeln; die Datei dort setzt sie durch. Zwei Prosafassungen
derselben Liste waeren zwei Wahrheiten — im selben Repo sind auf genau diesem Weg fuenf
verschiedene Testzahlen entstanden.

## Zwei Profile

| Profil | Fuer | Pflicht-Slugs |
|---|---|---|
| `haus` | ein wiederverwendbares Design-System | 20 |
| `produkt` | ein Produkt, das ableitet | 23 (erbt `haus`, ohne `token-architektur`, plus `informationsarchitektur`, `sichtbarmachungs-plan`, `fehlstellen`, `umsetzungsskizze`) |

**Warum zwei und nicht eins:** ein Haus-System hat keine Informationsarchitektur, weil es
keinen Bildschirm hat. Ein Schema, an dem sein eigenes Referenzdokument scheitert, ist
kein Schema, sondern ein Wunsch. Gemessen: `DESIGN-SYSTEM.md` besteht Profil `haus`
mit 20 von 20.

## Slugs statt Nummern

Belegter Grund: Entwurf C musste nachtraeglich einen Abschnitt **13a** einschieben, weil
erst die eigene Messung drei Fehler fand. Jede Nummerierung verschiebt sich beim ersten
Update; ein Slug ueberlebt. Die Reihenfolge ist frei, die Namen nicht.

## Die vier Regeln mit Zaehnen

| Regel | Warum sie existiert |
|---|---|
| `beleg-grundlage` braucht mindestens eine Fundstelle `datei.ext:zeile` | Gemessen ueber drei Entwuerfe: 0 / 15 / 22 Zitate bei 21,5 / 36,5 / 36,0 Punkten. Die Belegdichte ist das einzige Merkmal, das die Bewertung mechanisch reproduziert. |
| `prototyp-messung` nennt mindestens einen Fehler, den erst die Messung fand | C fand drei, B fand drei. Ein Dokument ohne solchen Eintrag hat entweder nicht gemessen oder verschweigt. |
| `bewusste-auslassungen` klassifiziert jede Zeile (kann-nicht / will-nicht / darf-nicht) | B fuehrte ein Sicherheits-Geheimnis als Auslassung — kategorisch etwas anderes als „kein Hellmodus". |
| keine unbefuellten Vorlagenstellen (`«…»`) | Ein Dokument, das die Vorlage noch traegt, ist nicht fertig. |

## Was v1.0 anders macht als v0.2

| v0.2 | v1.0 | Grund |
|---|---|---|
| 8 feste Abschnitte (Background, Typography, Cards, Colors, Spacing, Animations, Icons, Layout) | 20 bzw. 23 Slugs | Die alten acht hatten kein Feld fuer Beleg, Zustand, Auslassung, Herkunft oder Risiko — also fuer nichts, was ein Dokument pruefbar macht. |
| „ALL 8 sections MUST be present" | Profil entscheidet | Die eigene Referenz-App verletzte diese Regel (6 statt 8 Abschnitte). Eine Regel, die das eigene Bauteil bricht, ist falsch gestellt. |
| „Font MUST be available (Google Fonts or system)" | nur System-Stacks | Lizenz, Offline-Faehigkeit, CSP. Gemessen war ausserdem: das im Bestand deklarierte `Inter` war auf keinem Zielsystem installiert. |
| „Durations MUST be: 100/200/300/500ms" | `motion.none` ist der Systemwert | Beide Sieger-Entwuerfe fuehrten Animation als **bewusste Auslassung**. Ein Schema, das Bewegung erzwingt, verbietet die richtige Antwort. |
| Werte im Dokument | Werte in `tokens.dtcg.json` | Das Dokument erklaert, die Token-Datei traegt. Werte an zwei Orten driften. |
| kein Versionsbezug | `schema-version` + `design-version` getrennt | Ein Schema-Bruch trifft alle Dokumente, ein Design-Bruch nur eines. |

## Migration v0.2 → v1.0

Ein bestehendes DESIGN.md nach v0.2 ist **nicht automatisch konvertierbar** — die
fehlenden Abschnitte enthalten Aussagen, die niemand aufgeschrieben hat (Belege,
Auslassungen, Risiken). Ein Werkzeug, das sie erfindet, waere genau das Falsche.

Der Weg:

1. `design-system/TEMPLATE.md` als neue Datei anlegen (Profil `produkt`).
2. Die alten acht Abschnitte in ihre neuen Slugs uebertragen:
   `Background`/`Colors` → `farbsystem` · `Typography` → `schriftsystem` ·
   `Spacing`/`Radius` → `raster-abstand-form` · `Cards`/`Layout` → `layout` +
   `bauteil-katalog` · `Animations` → `barrierefreiheit-bewegung` ·
   `Icons` → meist `bewusste-auslassungen`.
3. Die Farbwerte **nicht** uebertragen, sondern gegen das Haus-System pruefen: was
   abweicht, wird `tokens.overrides.json` + eine `DIVERGENZ.md`-Zeile.
4. Die neuen Pflichtabschnitte fuellen. Das ist Arbeit, keine Konvertierung — und sie ist
   der eigentliche Gewinn.
5. `design-doc.py --check` bis gruen.
