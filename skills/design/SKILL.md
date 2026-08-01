---
name: design
version: 1.0.0
type: meta
category: documentation
complexity: skill
description: Haus-Design-System — DTCG-Token, Dokument-Schema, Projekt-Ableitung, Versionierung und Migration. Trigger bei Design-System, DESIGN.md, Design-Token, Palette, Kontrast, Design-Update, Design-Migration.
trigger: design system, DESIGN.md, design token, palette, contrast, design update, design migration
model: sonnet
allowed-tools: [Read, Write, Bash, Grep]
user-invocable: true
token-budget: 4000
requires: []
produces: [DESIGN.md, tokens.overrides.json, DIVERGENZ.md, design-specification]
cooperative: false
last-audit: 2026-08-01
metadata:
  design-system-version: "1.0.0"
  token-format: "dtcg-2025.10"
  visual-authority: "fable-5"
---

# meta:design — das Haus-Design-System

> Design is cooperation, not description-to-generation.
> The user SEES options and CHOOSES. The AI doesn't decide.

Der Kernsatz bleibt. Er hat jetzt einen Ort: das **Verfahren** liegt in
`meta:design-jury`, wo `AskUserQuestion` die Wahl erzwingt. **Dieser** Skill entscheidet
nichts — er rechnet. Deshalb `cooperative: false`.

**Gestaltungshoheit: Fable 5.** Farbe, Typografie, Form, Layout und Token-Werte werden
hier gelesen und geprueft, nie gesetzt. Ein Befund lautet „Kontrast 3,8:1 liegt unter
4,5:1" — nicht „nimm ein helleres Rot".

## Das System liegt in `design-system/`, nicht hier

Daten mit eigener Lebensdauer und eigener SemVer. Lesbar, ohne dass ein Modell einen Skill
laedt (CI, Build-Werkzeug, fremdes Projekt). Aufloesung in dieser Reihenfolge:
`$AIE_DESIGN_SYSTEM` → `<plugin-root>/design-system` → `./design-system`. Kein Treffer =
benannter Fehler, **kein** eingebauter Vorgabe-Satz.

Was drin liegt: `references/system-anatomie.md`

## Die vier Handgriffe

| Was | Kommando |
|---|---|
| Kontrast aller erklaerten Paare | `python3 scripts/design-contrast.py --ci` |
| Zustands-Abdeckung | `python3 scripts/design-states.py --coverage` |
| Farben ausserhalb des Tokensatzes | `python3 scripts/design-lint.py --all` |
| Dokument gegen das Slug-Schema | `python3 scripts/design-doc.py --check DATEI --profil produkt` |

## Ein Projekt leitet ab — es kopiert nicht

```
<projekt>/design/
  DESIGN.md               nach design-system/TEMPLATE.md, Profil produkt
  tokens.overrides.json   NUR Abweichungen. Eine Vollkopie wird abgelehnt.
  DIVERGENZ.md            je Override eine Zeile: Klasse, Grund, ueberpruefen-bis
  .design-lock.json       erzeugt von design-resolve.py
```

Drei Klassen fuer eine Abweichung: **kann-nicht** (technische Grenze) · **will-nicht**
(Produktentscheidung) · **darf-nicht** (Recht, Marke, Vorschrift). Jede braucht ein
Ablaufdatum — ohne Ablauf wird aus einer Abweichung stillschweigend Dauerzustand.

Ein Override darf eine **andere Farbe** waehlen. Er darf **nicht unlesbar** werden: die
Kontrastminima sind nicht abweichbar. Das ist ein harter Fehler, keine Divergenz.

Vollstaendig: `references/ableitung.md`

## Regeln, die nicht verhandelbar sind

- **I1** Interaktions-Kodierung ∩ Zustands-Kodierung = leer.
- **I2** Jeder Zustand ist ohne Farbe unterscheidbar (Form, Position oder Wort).
- **I3** Jedes bedeutungstragende Token sagt, was es bedeutet.
- **I4** Bedeutung wohnt im Token-Namen, nicht im Hex-Wert.

Warum diese vier: `references/token-modell.md`

## Acht Zustaende, kein neues Vokabular

`idle · pending · success · empty · partial · failed · unavailable · locked`

Die ersten sechs stammen aus dem Bestands-Skill `async-state-coverage`. Ergaenzt sind
`unavailable` (Luecke des **Werkzeugs**, nicht der Daten) und `locked` (strukturell
verweigert). `empty`, `unavailable` und `locked` sind drei verschiedene Wahrheiten und
sehen dreimal anders aus.

Details: `references/zustands-matrix.md`

## Versionierung

Zwei Achsen: **SemVer** fuer den Vertrag, **visual-epoch** fuers Aussehen. Eine
Farbwertaenderung bricht keinen Vertrag, aber jedes Screenshot.
Breaking-Tabelle und Migrationspfad: `references/versionierung.md`

## Ehrlichkeit ist eine Bauvorschrift, kein Ton

Was es nicht gibt, wird als M10-Fehlstellen-Rahmen gezeichnet — mit *was fehlt* in
Produktsprache und *was es braeuchte* in Entwicklersprache. Ein leerer Erfolg ist ein
Erfolg und sieht nicht aus wie ein Fehler.
Muster und Herkunftsklassen: `references/ehrlichkeits-regeln.md`

## Was dieser Skill NICHT hat

Keinen Web-Konfigurator. Der frühere Verweis auf `vg-dashboard/` zeigte ins Leere — im
Plugin nicht vorhanden, real unter `phantom-ai/vg-dashboard`, nicht mitversioniert, mit
einer dritten Kategorienliste. Ersatz ist `design-system/showcase.html`: selbst-enthalten,
laeuft in Claude Code und opencode ohne Server und ohne Port.

Vollstaendige Lage: `design-system/STATUS.md`

## Referenzdateien

- `references/system-anatomie.md` — was in `design-system/` liegt und wie es gefunden wird
- `references/token-modell.md` — Schichten L0–L4, Invarianten, DTCG-Abbildung
- `references/dokument-schema.md` — die Pflicht-Slugs und warum es zwei Profile gibt
- `references/ableitung.md` — Overrides, DIVERGENZ, Lock
- `references/versionierung.md` — SemVer, visual-epoch, Migration
- `references/zustands-matrix.md` — acht Zustaende, Enumerationsregel, Abdeckungsmass
- `references/ehrlichkeits-regeln.md` — A33 im Design
- `references/categories.md` — die Token-Kategorien des Hauses
- `references/export-schema.md` — v1.0, mit Migrationspfad von v0.2
