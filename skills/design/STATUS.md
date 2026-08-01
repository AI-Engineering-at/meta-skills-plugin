# STATUS — skills/design und skills/design-jury

Stand: 2026-08-01

Die Lage des **Systems** (Token, Bauteile, Werkzeuge) steht in
`design-system/STATUS.md`. Hier steht die Lage der **Skills**.

| Bauteil | gebaut | aktiviert | gemessen | genutzt |
|---|---|---|---|---|
| `skills/design/SKILL.md` v1.0.0 | ja | ja | ja — `validate.py --strict-set` gruen | ja |
| 9 Referenzdateien | ja | ja | ja — jede im Koerper genannte Datei existiert (T1) | ja |
| `skills/design-jury/SKILL.md` v1.0.0 | ja | ja | ja — `validate.py --strict-set` gruen | **nein — kein echter Jury-Lauf** |
| 5 Jury-Referenzdateien | ja | ja | ja | nein |
| `AskUserQuestion` in `allowed-tools` | ja | ja | ja — erstmals im Plugin ueberhaupt | **nein** |
| `test-scenario.md` (beide) | ja | nein | **nein** | nein |

## Ehrlich: was hier noch nicht belegt ist

- **Das Jury-Verfahren ist nicht gelaufen.** P0–P7 sind beschrieben, die Gates sind
  gebaut und getestet, aber es gab **keinen** echten Durchlauf mit K=3 an einem realen
  Projekt. Alles ueber die Wirksamkeit des Verfahrens ist bis dahin unbelegt.
  Folge davon: der Divergenz-Schwellwert bleibt im Nur-Messen-Modus, weil die
  Datengrundlage fehlt.
- **`AskUserQuestion` ist deklariert, nicht ausgefuehrt.** Es steht erstmals im Plugin in
  `allowed-tools`. Dass der Harness es an dieser Stelle wirklich anbietet, ist **nicht**
  gemessen — nur, dass das Feld gesetzt ist.
- **Die `test-scenario.md`-Dateien sind ungeprueft.** `scripts/test-skill.py` ruft externe
  LLM-CLIs, steht in keinem CI-Auftrag, und ob je eine der 16 vorhandenen Szenariodateien
  bestanden hat, ist unbekannt. Sie werden deshalb bewusst **nicht** in die CI gehaengt —
  ein Auftrag, der nie lief, ist kein Gate.
- **opencode: Dateiwahrheit ja, Laufzeitwahrheit nein.** Beide Skills liegen in `skills/`
  und sind damit fuer den gemessenen opencode-Mount sichtbar. Dass opencode sie
  tatsaechlich laedt, ist **nicht** durch einen Lauf belegt.
- **`requires: [design]` ist Prosa.** Kein Python liest das Feld — dieselbe Krankheit wie
  `cooperative`. Gegenmittel ist heute nur ein Test, der prueft, dass die Slugs des
  Jury-Skills im Dokument-Schema des System-Skills vorkommen.

## Was bewusst NICHT gebaut wurde

- **Kein `context: fork` / `agent:` am Jury-Skill selbst.** Der Skill *orchestriert*; er
  dispatcht die K Entwerfer einzeln. Wuerde der ganze Skill forken, liefe auch die
  Linsen- und Sondenarbeit unter Fable 5 — genau die Rollenvermischung, die der Auftrag
  verbietet. Die Bindung sitzt im Entwurfs-Brief, nicht am Skill.
- **Kein `paths:`-Feld.** Die Recherche nennt es als gueltiges Claude-Code-Frontmatter,
  aber ich habe es **nicht gegen eine laufende Version geprueft**. Ein Feld, dessen
  Wirkung ich nicht gemessen habe, kommt nicht in eine Datei, die Ladeverhalten steuert.
