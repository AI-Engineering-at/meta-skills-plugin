# Der Entwurfs-Brief (P3)

Jeder der K Entwerfer bekommt **denselben** Brief mit **einer** anderen These. Der Brief
ist absichtlich fett: ein Agent, der Kontext rediscovern muss, verbrennt ihn mit Suchen.

## Aufbau

### 1. Rolle und Grenze

> Du bist Fable 5 und triffst **alle** gestalterischen Entscheidungen dieses Entwurfs:
> Farbe, Typografie, Form, Layout, Token-Werte. Niemand sonst tut das.
> Du bekommst Befunde, keine Anweisungen — und du folgst ihnen oder begruendest, warum
> nicht.

### 2. Die These — und nur sie

Eine These aus `02-rahmungen.json`, mit ihren Achsenwerten.

**Ausdruecklich nicht mitgeliefert:** die Thesen der anderen. Isolation ist das ganze
Verfahren. Wer die anderen sieht, gleicht sich an.

### 3. Die Belege

`01-belege.md` vollstaendig. Nicht die Zusammenfassung — die Fundstellen.

### 4. Das Haus-System

`design-system/` mit dem Hinweis: du darfst abweichen, aber jede Abweichung ist eine
`DIVERGENZ.md`-Zeile mit Klasse und Ablaufdatum. Die Invarianten I1–I4 und die
Kontrastminima sind **nicht** abweichbar.

### 5. Die Lieferpflicht

```
entwuerfe/<id>/
  spec.md        nach TEMPLATE.md, Profil produkt, alle Pflicht-Slugs
  mockup.html    selbst-enthalten: kein externer Request, keine Fremdschrift, kein Server
  build.py       erzeugt mockup.html reproduzierbar, mit Selbstpruefung
```

Frontmatter je Entwurf — **Pflicht**, weil zwei von drei Ausgangsentwuerfen keinen Autor
nannten:

```yaml
entwurf-id: C
titel: «von dir»
autor: fable-5
modell: «exakte Modell-ID dieses Laufs»
erzeugt: «RFC-3339-Zeitstempel»
achsen: { … }
these: «ein Satz»
mockup: mockup.html
build: build.py
build-sha256: «von build.py berechnet, nie getippt»
```

### 6. Die Hausregeln, die nicht verhandelbar sind

- **A33 KEIN-MOCK:** keine Fakes in Produktivpfaden. Was leer ist, ist ehrlich leer.
  In der Attrappe heisst das: jeder Beispielwert traegt eine der vier Herkunftsklassen.
- **A54 / M126 Verify-vor-Behaupten:** jede Zahl in `spec.md` stammt aus einem Kommando,
  dessen Ausgabe du zeigst. Fremde Zusammenfassungen sind Zeiger, nie Fakt.
- **Kein Wert von Hand getippt,** wo ein Rechner ihn erzeugen kann. Kontrastwerte werden
  gerechnet — der Ausloeser ist gemessen: ein Vorgaengerentwurf behauptete 4,9:1, wo
  6,23:1 richtig war, und 3,8:1, wo 4,58:1 richtig war.

### 7. Was am Ende gemessen wird

Die Sonden aus P4 und die sieben Linsen aus P5 — **im Voraus genannt**. Ein Entwerfer,
der die Pruefung kennt, baut besser; das ist kein Schummeln, sondern der Sinn eines
Abnahmekriteriums.

Und ausdruecklich: **`prototyp-messung` muss mindestens einen Fehler nennen, den erst die
eigene Messung fand.** Wer keinen findet, hat nicht gemessen.
