# A33 im Design — Ehrlichkeit als Bauvorschrift

Die Hausregel lautet: keine Fakes, Stubs oder Platzhalter in Produktivpfaden; was leer
ist, ist ehrlich leer. Im Design hat das eine **gezeichnete** Form, nicht nur eine Haltung.

## Die drei Leeren sehen verschieden aus

| Zustand | Was es heisst | Wie es aussieht |
|---|---|---|
| `empty` | nachgesehen, nichts da — **Erfolg** | Erfolgssprache, Neutralfarbe, nie Fehlersprache |
| `unavailable` | konnten nicht nachsehen, Werkzeug fehlt | M10-Fehlstellen-Rahmen, gestrichelt |
| `locked` | duerfen nicht nachsehen | schraffiert + Wort + Grund, kein Bedienelement |

Wer alle drei als leere Tabelle zeigt, behauptet in zwei von drei Faellen etwas Falsches.

## Das Fehlstellen-Muster (M10)

Ein Fehlstellen-Rahmen traegt **zwei Saetze in zwei Sprachen**:

- **was fehlt** — in Produktsprache, fuer den, der davorsitzt
- **was es braeuchte** — in Entwicklersprache, fuer den, der es bauen koennte

Und er enthaelt **kein klickbares Element**. Eine Luecke bietet nichts an. Ein Knopf in
einer Fehlstelle ist ein Versprechen ohne Bauteil — genau der Verstoss, den dieses System
in seinem eigenen Vorgaenger beseitigt hat (`vg-dashboard/`: ein Verweis auf eine App, die
an der genannten Stelle nicht existierte).

## Herkunft jeder gezeigten Aussage

Jeder Wert traegt seinen Erkenntnisgrad — als **Form**, nicht als Farbe (M07):

| Marke | Bedeutung |
|---|---|
| voll | beobachtet — woertlich gelesen |
| halb | abgeleitet — berechnet oder klassifiziert |
| hohl | unbekannt — keine Aussage |
| Strich | nicht pruefbar, kein Vergleichswert |
| schraffiert | gesperrt |
| gestrichelt | nicht verfuegbar |

`state.neutral` ist dabei die Farbe der Ehrlichkeit: sie behauptet nichts.

## Die vier Herkunftsklassen fuer Beispielwerte

Jede Attrappe und jedes Beispiel klassifiziert seine Werte. Ohne das ist jede Attrappe
potenziell ein Mock:

1. **verbatim** — woertlich uebernommen, mit Quelle
2. **real berechnet** — und reproduzierbar nachrechenbar
3. **Beispielwert in echter Form** — als Demo gekennzeichnet, Form aus dem echten System
4. **bewusst nicht gezeigt** — und warum (Geheimnis, Recht, Groesse)

Im Haus-Schaustueck ist der „verified"-Digest tatsaechlich `sha256(tokens.dtcg.json)` und
das Mismatch-Paar tatsaechlich `sha256("uname -a")` gegen `sha256("uname -a\n")` — ein
Byte Unterschied, was den Lawinensatz daneben **wahr** macht. Nachgerechnet von
`verify_showcase.py`, nicht behauptet.

## Zahlen werden gerechnet, nicht getippt

Der Ausloeser ist gemessen: Entwurf C **behauptete** Kontrastwerte, die nicht stimmten
(Nebel 4,9 behauptet — 6,23 gerechnet; Alarm 3,8 behauptet — 4,58 gerechnet). Nicht aus
Nachlaessigkeit, sondern weil niemand nachrechnete.

Konsequenz im System: der Rechner reist mit, jede angezeigte Zahl traegt ihr Farbpaar als
`data`-Attribut, und ein Pruefer rechnet alle nach. Behauptung und Pruefung sind
**mechanisch gekoppelt**.

Dieselbe Krankheit im Plugin: fuenf verschiedene Testzahlen (346 / 444 / 646 / 725) gegen
tatsaechlich gemessene 755. Deshalb `MANIFEST.json` generiert und `design-report --check`
als Gate.

## Was ein Dokument ueber sich selbst sagen muss

- **mindestens einen Fehler, den erst die eigene Messung fand** — sonst wurde nicht
  gemessen oder es wird verschwiegen
- **was NICHT geprueft wurde** — kein Lauf, kein Geraet, keine Sprache, kein Browser, den
  man nicht selbst gesehen hat
- **Auslassungen mit Klasse** — kann-nicht / will-nicht / darf-nicht

Diese drei sind keine Bescheidenheitsfloskeln. Sie sind der Unterschied zwischen einem
Dokument, dem man glauben kann, und einem, dem man glauben muss.
