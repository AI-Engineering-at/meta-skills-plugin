# «Produktname» — Design-Dokument

```yaml
projekt:        «Produktname»
schema-version: 1.0.0        # Struktur dieses Dokuments (Slugs). Nicht selbst waehlen.
design-version: 0.1.0        # Inhalt: Token, Rollen, Bauteile dieses Produkts
extends:        meta-skills-design@1.0.0
autor:          «wer die gestalterischen Entscheidungen getroffen hat»
stand:          «JJJJ-MM-TT»
basiert-auf:    «Entwuerfe, Vorlaeufer»
artefakte:      «tokens.overrides.json · mockup.html · …»
werkzeuge:      «die Rechner und Pruefer, die mitlaufen»
status:         entwurf | zur Abnahme | kanonisch
```

> **Profil `produkt`.** Die Pflicht-Slugs stehen in `schema/document-schema.json`.
> `scripts/design-doc.py --check «datei»` prueft sie. Reihenfolge ist frei, Namen nicht.
>
> **Diese Datei ist eine Vorlage, kein Beispiel.** Jede Zeile in spitzen Klammern ist eine
> unbefuellte Pflichtstelle. Ein Dokument, das sie noch traegt, ist nicht fertig — und
> `--check` sagt das. Ein erfundener Wert waere schlimmer als eine leere Stelle (A33).

---

## these

«Ein fetter Satz, aus dem alles Weitere folgt. Danach zwei bis vier Saetze, die ihn tragen.»

---

## beleg-grundlage

**Pflicht: mindestens eine Fundstelle der Form `datei.ext:zeile`.** Gemessen an den drei
Entwuerfen ist die Belegdichte das einzige Merkmal, das die Bewertung mechanisch
reproduziert — der abgeschlagene Entwurf hatte null solcher Zitate.

| Behauptung | Beleg |
|---|---|
| «was du sagst» | `«datei.ext:zeile»` bzw. das Kommando + seine Ausgabe |

---

## zielbild-einsatzmoment

«Wer benutzt das, unter welchen Bedingungen, an welchem Fenster, neben welchem anderen
Werkzeug? Der Einsatzmoment entscheidet mehr als der Geschmack.»

---

## sprache-und-stimme

«Welche Sprache traegt die Produktflaeche, welche die Spezifikation — und warum.
Woher kommt das Vokabular fuer Zustaende? (Existing-First: `async-state-coverage`.)»

---

## modus-festlegung

«Wert aus {nur-dunkel, nur-hell, beide} + der Risikosatz, den die Wahl mit sich bringt.»

**Risiko der Wahl:** «benennen, nicht wegreden. Und dann: automatisiert oder akzeptiert?»

---

## farbsystem

**Regel: jede bedeutungstragende Farbe nennt ihre Bedeutung UND wo sie ausdruecklich
nicht gilt.** Das zweite ist der Teil, den Wertetabellen ueblicherweise weglassen.

| Rolle | Wert | Bedeutung — und wo sie *nicht* gilt |
|---|---|---|
| «token-pfad» | «geerbt / Override» | «…» |

### Abweichungen vom Haus-System

«Jede Zeile hier braucht eine Entsprechung in `DIVERGENZ.md` mit Klasse und Ablaufdatum.
Keine Abweichung? Dann steht hier genau das: „keine".»

### Zweite Kodierung ohne Farbe

«Form, Position oder Wort — was traegt die Aussage, wenn Farbe nicht ankommt? (SC 1.4.1)»

---

## schriftsystem

«Stacks mit Begruendung **Glied fuer Glied** — welches Glied faengt welches System auf.
Rollen: welche Schrift traegt welche Art von Aussage. Skala als Token, nicht als Literal.»

---

## raster-abstand-form

«Abstand · Radius · Kantenstaerke · Fokusring · Dichte-Masse · Umbruchpunkte · Bewegung.
Alle als Token. Genau hier war das Rohmaterial rein literal — und daran scheitert
Wiederverwendung.»

---

## layout

«Zonen und ihre Regeln. Was kollabiert, was verschwindet nie, was scrollt in seinem
eigenen Container.»

---

## informationsarchitektur

| Was | Wo | **Warum hier** |
|---|---|---|
| «…» | «…» | «die dritte Spalte ist die eigentliche Aussage» |

---

## bauteil-katalog

«Je Bauteil: Zweck, feste Teile, vollstaendige Zustandsliste, Token-Bezug.
Geerbte Bauteile referenzieren `design-system/components/M*.md`, statt sie zu wiederholen.»

---

## zustands-matrix

«GENERIERT aus `states.json` per `scripts/design-states.py --markdown`. Nicht tippen.
Drei erlaubte Zellwerte: gezeichnet (mit exaktem Text) · entfaellt (mit Grund) · offen.
Vollstaendig heisst: offen == 0.»

---

## sichtbarmachungs-plan

«Welche Daten existieren heute schon, sind aber unsichtbar — und an welchem Ort macht
dieser Entwurf sie sichtbar? Je Punkt ein Ort.»

---

## fehlstellen

| Was fehlt (Produktsprache) | Was es braeuchte (Entwicklersprache) | Wo im Bild |
|---|---|---|
| «…» | «…» | «M10-Rahmen an Stelle …» |

---

## anforderungs-abdeckung

Generischer Kanon — jede Zeile genau einmal:

| Anforderung | Wo erfuellt | Beleg |
|---|---|---|
| Herkunft je Aussage | | |
| Erkenntnisgrad sichtbar | | |
| Konsequenzklasse vor der Aktion | | |
| Ausgangs-Gate (was passiert beim Bestaetigen) | | |
| Dichte im kleinsten Zielfenster | | |
| Tastaturweg vollstaendig | | |
| Nichts Fluechtiges (keine Aussage, die wegblendet) | | |
| Systemgrenzen benannt | | |
| Ehrliche Leere | | |

«Darunter der projekteigene Zusatzkanon.»

---

## barrierefreiheit-bewegung

«Kontrastwerte **gerechnet** (nicht behauptet) · Tastaturpfad · Fokus · ARIA-Rollen ·
Bewegung und `prefers-reduced-motion`. Und die Grenze: was hier NICHT erfuellbar ist.»

---

## umsetzungsskizze

«Wie wird das gebaut — gegen den echten Baum, mit `datei:zeile`, nicht gegen einen
gedachten.»

---

## prototyp-messung

**Pflicht: mindestens ein Fehler, den erst die eigene Messung fand.** Ein Dokument ohne
solchen Eintrag hat entweder nicht gemessen oder verschweigt.

```
«Rohwerte der Messung — Kommando und Ausgabe, nicht die Zusammenfassung»
```

**Was die Messung fand — behoben, nicht wegerklaert:**

1. «Fehler, und was daraufhin geaendert wurde. Wenn die Unterschrift falsch war, wird die
   DATEI korrigiert, nicht die Unterschrift.»

---

## prototyp-reproduzierbarkeit

«Bau-Kommando + Nachweis der Bytegleichheit. Kein Wert von Hand getippt.»

---

## herkunft-beispielwerte

Vier Klassen, jeder gezeigte Wert traegt genau eine:

- **verbatim:** «woertlich uebernommen, mit Quelle»
- **real berechnet:** «und reproduzierbar nachrechenbar»
- **Beispielwert in echter Form:** «als Demo gekennzeichnet, Form aus dem echten System»
- **bewusst nicht gezeigt:** «und warum — Geheimnis, Recht, Groesse»

---

## bewusste-auslassungen

| Auslassung | Klasse | Grund + Entsprechung |
|---|---|---|
| «…» | kann-nicht \| will-nicht \| darf-nicht | «…» |

---

## risiken

1. «Das Risiko · woran man es merkt · das Gegenmittel.»

---

## nicht-geprueft

«Was dieses Dokument ausdruecklich NICHT belegt. Kein Lauf, kein Geraet, keine Sprache,
kein Browser, den du nicht selbst gesehen hast. Diese Liste ist ein Qualitaetsmerkmal,
kein Eingestaendnis.»
