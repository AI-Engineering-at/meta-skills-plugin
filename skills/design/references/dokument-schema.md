# Das Dokument-Schema

Die kanonische, maschinenlesbare Fassung: `design-system/schema/document-schema.json`.
Geprueft mit `python3 scripts/design-doc.py --check <datei> --profil haus|produkt`.

## Herkunft

Entwurf C hatte **17** `##`-Abschnitte — nicht 16, wie oft zitiert: 0…13, **13a**, 14, 15.
Der nachgereichte **13a** („was an der Attrappe wirklich gemessen wurde") ist der
wertvollste von allen, weil er nur entstand, als die Messung drei echte Fehler fand.
Deshalb ist er im Schema **Pflicht** und nicht Anhang.

Dazu vier Abschnitte aus Entwurf B, die C fehlten:
Zugaenglichkeit als eigener Abschnitt · Prototyp-Reproduzierbarkeit · Herkunft der
Beispielwerte · Deckung „heute speisbar vs. braucht Backend".

Das Jolla-Spezifische ist herausgeloest:
„Regel-Abdeckung R1–R11" → `anforderungs-abdeckung` (generischer Kanon) ·
„Inventar-B-Plan" → `sichtbarmachungs-plan` · „Inventar-C-Ehrlichkeit" → `fehlstellen`.

## Warum Slugs

Entwurf C musste `13a` **einschieben**. Jede Nummerierung verschiebt sich beim ersten
Update; ein Slug ueberlebt. Reihenfolge frei, Namen nicht.

## Warum zwei Profile

| Profil | Slugs | Fuer |
|---|---|---|
| `haus` | 20 | ein wiederverwendbares Design-System |
| `produkt` | 23 | ein Produkt, das ableitet |

`produkt` erbt `haus`, laesst `token-architektur` weg (ein Produkt **erbt** die
Architektur, es erfindet sie nicht) und fordert zusaetzlich `informationsarchitektur`,
`sichtbarmachungs-plan`, `fehlstellen`, `umsetzungsskizze`.

**Der Grund ist gemessen, nicht theoretisch:** ARCHITEKTUR.md forderte 23 Pflicht-Slugs
fuer alles. Gegen die einzige real existierende Fassung geprueft — `DESIGN-SYSTEM.md` von
Fable 5 — waeren vier davon unerfuellbar gewesen. Ein Haus-System hat keine
Informationsarchitektur, weil es keinen Bildschirm hat. **Ein Schema, an dem sein eigenes
Referenzdokument scheitert, ist kein Schema, sondern ein Wunsch.**

Gemessen nach der Aufteilung: `DESIGN-SYSTEM.md` besteht Profil `haus` mit **20 von 20**,
0 Fehler.

## Zwei Versionsfelder im Frontmatter

`schema-version` = die Struktur dieses Dokuments (die Slugs).
`design-version` = sein Inhalt (Token, Rollen, Bauteile).

Ein Schema-Bruch trifft **alle** Dokumente, ein Design-Bruch nur eines. Ein einziges Feld
koennte das nicht unterscheiden.

## Autorschaft ist Pflicht

Von den drei Ausgangsentwuerfen nannte **genau einer** seinen Autor. Die Jury-Bewertung,
die zwischen ihnen entschied, existiert bis heute **nicht auf Platte** — die Punktzahlen
lebten nur im Gespraechsverlauf.

`autor` und `modell` sind deshalb Pflichtfelder. Das ist **Buchfuehrung, kein Beweis**:
`autor: fable-5` kann jeder tippen. Aber ohne Buchfuehrung gibt es nicht einmal die.

## Was das Schema nicht pruefen kann

Ob eine Begruendung eine Begruendung ist. `weil` besteht jeden Lint. Und ob eine Farbe
bedeutet, was ihre Beschreibung sagt, liest keine Maschine — das koennen nur eine
Pruef-Linse und ein Mensch.
