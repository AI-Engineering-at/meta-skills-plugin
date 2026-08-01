# M01 — Statusleiste

**Art:** Flaeche

## Zweck

Zeigt dauerhaft den Bereitschaftsstand aller ueberwachten Faehigkeiten. Sie scrollt nie weg.

## Anatomie — die festen Teile

- je Lampe: Aussage + Erkenntnisgrad-Marke (M07) + **Messzeitpunkt** + Sprungziel
- kollabiert unter `breakpoint.collapse` auf eine Kante mit Ticks — sie wird nie per Media-Query geopfert
- der Messzeitpunkt ist Pflicht: eine Lampe ohne Zeit behauptet eine Gegenwart, die sie nicht belegen kann

## Zustaende

Quelle: `states.json`, Flaeche `M01-statusleiste`. Die Uebersichtstabelle ueber alle
Flaechen erzeugt `scripts/design-states.py --markdown`; hier steht die Begruendung je Zelle.

| Zustand | Wert | Text bzw. Grund |
|---|---|---|
| `idle` | gezeichnet | Lampe aus, nennt den Ausloeser |
| `pending` | gezeichnet | Lampe misst gerade |
| `success` | gezeichnet | Lampe ok + Messzeitpunkt |
| `empty` | gezeichnet | Lampe neutral, Erfolgssprache |
| `partial` | gezeichnet | Lampe teilweise, Zaehlung n/m |
| `failed` | gezeichnet | Lampe danger, bleibt stehen |
| `unavailable` | gezeichnet | Lampe gestrichelt, Werkzeugluecke |
| `locked` | gezeichnet | Lampe schraffiert, kein Fokus |

## Token-Bezug

- `state.*.base` fuer die Lampe
- `density.band` fuer die Bandhoehe
- `font.size.t10` fuer die Versalien-Beschriftung
- `breakpoint.collapse`

## Herkunft

Festlegung: Fable 5, `DESIGN-SYSTEM.md`, Abschnitt `bauteil-katalog`.
Diese Datei faltet diese Festlegung aus; sie trifft keine eigene Gestaltungsentscheidung.
