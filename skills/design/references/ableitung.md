# Wie ein Projekt ableitet

## Was im Projekt liegt

```
<projekt>/design/
  DESIGN.md                 nach TEMPLATE.md; Frontmatter: extends: meta-skills-design@1.0.0
  tokens.overrides.json     DTCG, NUR Abweichungen — niemals Vollkopie
  states.json               eigene Flaechen, dieselben 8 Zustandsschluessel
  DIVERGENZ.md              je Override eine Zeile
  .design-lock.json         GENERIERT: aufgeloeste Menge + Hash der Basis
```

## Der Ableitungslauf

```
python3 scripts/design-resolve.py \
    --overrides <projekt>/design/tokens.overrides.json \
    --out       <projekt>/design/.design-lock.json
```

## Drei Mechanismen gegen Zerfaserung — alle maschinell

### 1. Overrides enthalten ausschliesslich Abweichungen

Eine Vollkopie ist mechanisch erkennbar (jedes Basis-Token kommt darin vor) und wird
**abgelehnt**. Ein Projekt kann das System nicht stillschweigend forken.

Der Grund ist nicht Ordnungsliebe: nur bei einer Abweichungsdatei laesst sich spaeter
berechnen, ob die **Basis sich in die Richtung des Overrides bewegt hat** — also ob die
Abweichung ueberfluessig geworden ist. Bei einer Vollkopie ist diese Frage prinzipiell
unbeantwortbar, weil man Absicht nicht mehr von mitkopiertem Altbestand unterscheiden kann.

### 2. Jeder Override braucht eine DIVERGENZ-Zeile

Ohne sie: Lint-Fehler.

| Token-Pfad | Klasse | Grund | ueberpruefen-bis | Wer |
|---|---|---|---|---|
| `color.dark.state.danger.base` | darf-nicht | Kundenmarke schreibt ein anderes Rot vor | 2027-02-01 | fable-5 |

Die drei Klassen:

- **kann-nicht** — technische Grenze
- **will-nicht** — Produktentscheidung
- **darf-nicht** — Recht, Marke, Vorschrift

Belegter Grund fuer die Dreiteilung: Entwurf B fuehrte ein Sicherheits-Geheimnis als
Auslassung („ein Geheimnis mit 45 s Leben gehoert nicht auf den Schirm"). Das ist
kategorisch etwas anderes als „kein Hellmodus" — und eine Liste, die beides gleich
behandelt, verliert genau die Information, die zaehlt.

### 3. Abweichung laeuft ab

`ueberpruefen-bis` ist Pflicht. `design-check.py` meldet abgelaufene Divergenzen; die CI
**warnt, blockt aber nicht** — eine abgelaufene Begruendung ist ein Gespraechsanlass, kein
Baufehler.

Der Grund fuer das Ablaufdatum ist eine eingestandene Grenze: **„weil" besteht jeden
Lint.** Keine Maschine prueft, ob ein Grund ein Grund ist. Was eine Maschine kann, ist die
Zeit erzwingen — und die erzwingt das Gespraech.

## Was ein Override NICHT darf

Eine **Invariante brechen** (I1–I4) oder ein Paar aus `contrast-pairs.json` unter sein
Minimum druecken. Das sind **harte Fehler, keine Divergenz**.

Ein Projekt darf eine andere Farbe waehlen. Es darf nicht unlesbar werden.

## Warum es das Lock gibt

`.design-lock.json` haelt fest, gegen **welchen** Basis-Hash aufgeloest wurde. Ohne diesen
Bezug ist jede spaetere Migrationsaussage geraten: man sieht, dass ein Override auf ein
Token zeigt, aber nicht, ob dieses Token damals schon so hiess.

## Was heute noch nicht geht — ehrlich

`design-check.py --migrate` kennt **zwei** Faelle (Token existiert weiter / Token weg),
nicht vier. Die beiden fehlenden — „umbenannt, automatisch umschreibbar" und „dein
Override ist womoeglich ueberfluessig" — brauchen den Vergleich **zweier** Basis-Staende.
Das ist nicht gebaut. Steht so in `design-system/STATUS.md`.
