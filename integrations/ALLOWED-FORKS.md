# Erlaubte Forks von SKILL.md

## Die Regel

**Kein geforkter SKILL.md. Nie.** Eine Datei, zwei Welten — das ist der ganze Sinn des
Agent-Skills-Formats: beide Runtimes scannen `<skills-dir>/*/SKILL.md`, und unbekannte
Frontmatter-Felder werden stillschweigend uebergangen. Ein Skill in `skills/` erreicht
opencode ohne Zusatzarbeit.

Ein Fork bedeutet: zwei Dateien, die dasselbe behaupten und auseinanderlaufen, ohne dass
ein Mechanismus es meldet.

## Warum es diese Datei trotzdem gibt

Der Sündenfall existiert bereits und wird hier **gezaehlt statt versteckt**:
`tests/test_design_cross_runtime.py` macht jeden **neuen** Fork rot. Die Altlast steht
hier — mit Grund, Datum und Adresse.

Das ist dasselbe Muster wie `design-system/gleichwerte.json`: eine Ausnahme, die benannt
ist, ist beherrschbar; eine aufgeweichte Regel ist es nicht.

## Die Eintraege

| Skill | Seit | Grund | Wer entscheidet ueber die Aufloesung |
|---|---|---|---|
| `statusbar` | vor 2026-08-01 (vorgefunden) | Die opencode-Fassung fuehrt 6 statt 15 Frontmatter-Feldern und ein anderes Modell (`free/groq-fast`). Sie wird von `scripts/validate.py` gar nicht gescannt, weil der Pruefer nur `skills/` und `.claude/skills/` kennt — der Fork entkommt also jeder Pruefung. | Plugin-Team |

**Stand: genau ein Eintrag.** Wer einen zweiten braucht, traegt ihn hier ein und
begruendet ihn — oder loest den Fork auf.

## Was hier NICHT hineingehoert

Ein Fork, weil „das Frontmatter in opencode anders aussehen soll". Unbekannte Felder
werden dort laut Quelltext ignoriert; ein zweiter Satz Felder ist nie noetig, nur bequem.
