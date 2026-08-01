---
description: "Haus-Design-System: Token pruefen, Dokument pruefen, Projekt ableiten"
---

Ruft `meta:design` auf — das Haus-Design-System.

Der frueher hier beschriebene Web-Konfigurator existiert nicht. Dieser Befehl startete
nie einen Server: `meta:design start` war nirgends implementiert, und der Verweis auf
`vg-dashboard/` zeigte auf ein Verzeichnis, das es im Plugin nicht gibt. Die frueher hier
genannte Kategorienliste (Background, Typography, Cards, Metrics, Controls, Buttons,
Colors, Radius) widersprach ausserdem in vier von acht Punkten der Referenzdatei des
Skills. Beides ist beseitigt — die Kategorien stehen jetzt an genau einer Stelle:
`skills/design/references/categories.md`.

Was der Skill kann:

- Kontrast aller erklaerten Farbpaare nachrechnen  `scripts/design-contrast.py --ci`
- Zustands-Abdeckung messen                        `scripts/design-states.py --coverage`
- Farben ausserhalb des Tokensatzes finden         `scripts/design-lint.py --all`
- Ein Design-Dokument gegen das Slug-Schema pruefen `scripts/design-doc.py --check DATEI`
- Ein Projekt ableiten                             `scripts/design-resolve.py --overrides ...`

Zum Anschauen statt Lesen: `design-system/showcase.html` im Browser oeffnen. Die Datei ist
selbst-enthalten — kein Server, kein Port, kein externer Request.

Fuer einen **Entwurfsprozess** mit mehreren Alternativen und einer echten Wahl:
`meta:design-jury`.
