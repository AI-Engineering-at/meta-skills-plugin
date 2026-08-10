# n8n diagnostizieren — vier Fehlersorten, nicht eine Liste

Stand 2026-08-10, an 83 Workflows gemessen. **Vorbemerkung zum Fenster:** die
Ausführungshistorie reicht nur ~5 Tage zurück — nicht weil etwas kaputt ist, sondern weil
`EXECUTIONS_DATA_PRUNE_MAX_COUNT` bei 10.000 bindet, nicht das Alter. **„0 Läufe" heißt nicht
„läuft nie", sondern „nicht in diesem Fenster".** Fragen der Form „seit wann geht das schief"
lassen sich aus dieser Datenbank nicht über fünf Tage hinaus beantworten.

## Die Typologie

| Sorte | Was wirklich kaputt ist | Woran man sie erkennt |
|---|---|---|
| **A — rotiertes Credential** | Ein gespeichertes Credential zeigt auf einen Schlüssel, der rotiert wurde | 100 % Fehlerquote, Log sagt *„Authorization failed"*, `updatedAt` des Credentials ist **älter** als der Rotationszeitpunkt |
| **B — Schlüssel fest im Workflow** | Der Wert steht in den Knoten-Parametern statt in einer Credential | 100 % Fehler **und** ein Treffer im Export-Repo |
| **C — Credential-Bindung fehlt ganz** | Der Knoten ruft ein geschütztes Ziel ohne jede Bindung | HTTP 401/403; Gegenprobe: das Ziel antwortet ohne Token mit 401/403, lebt also |
| **D — überwachtes Ziel ist weg** | Der Workflow ist heil, sein Ziel nicht | HTTP 000 / keine Antwort. **Positivkontrolle Pflicht:** antwortet der Host auf einem anderen Port? |

> **Das Urteil, das dahinter steht:** Vier von sechs Defekten gingen auf **eine einzige
> Wartung** zurück — eine Schlüsselrotation, die den Erzeuger erneuerte und die Verbraucher
> stehen ließ. Das ist kein Workflow-Problem, sondern ein Rotations-Problem.

## Webhooks prüfen, ohne sie auszulösen

Absichtlich die **falsche HTTP-Methode** senden. n8n antwortet dann unterscheidbar, **ohne den
Workflow auszuführen** — eine nebenwirkungsfreie Probe für aktive Webhooks.

Gemessen: von 22 aktiven Webhook-Knoten antworteten 16 unter der kurzen Adresse, 6 nicht.
Zweiter Pfad über `n8n.webhook_entity` (23 Einträge): **die 6 sind registriert** — unter
`<workflowId>/<Knotenname>/<pfad>`. 16 + 6 + 1 = 23, die Zahlen gehen auf.

*Korrektur eines früheren Befundes: „nicht registriert" war falsch. Registriert schon — nur
unter einer anderen Adresse.* Die Wirkung bleibt: wer die kurze URL beim Absender hinterlegt
hat, bekommt **404**.

**Was fehlt, um daraus ein Urteil zu machen:** welche Adresse beim jeweiligen Absender wirklich
eingetragen ist. Das ist die Messung **am Ziel**. Ohne sie ist „Umsatzpfad tot" eine Vermutung.

## Der Migrations-Bericht — n8n sagt selbst, was bricht

```
GET /rest/breaking-changes/report?version=v3
```

**Community, read-only, kostenlos.** Nennt für alle 83 Workflows namentlich, was der Sprung auf
v3 (laut Doku Oktober 2026) bricht — u. a. das Entfernen der Function-, FunctionItem- und
ItemLists-Knoten. Das ist die Antwort auf „was sollten wir überarbeiten", von n8n selbst
statt geschätzt.

## Was still bricht — vor jedem Umbau lesen

- **13 Code-Knoten in 11 Workflows** greifen per `$('Knotenname')` auf Nachbarknoten zu.
  Umbenennen oder Ersetzen bricht sie **ohne Fehlermeldung beim Speichern**.
- **6 Knoten** halten Zustand über `getWorkflowStaticData` — nicht ersetzbar.
- Handgebaute HTTP-Knoten sind im Mittel 1632 Zeichen groß: sie tun mehr als den Aufruf.
  **Kein 1:1-Umbau.**

## Was NICHT als Fehler zählt

- `Failed to start Python task runner … Python 3 is missing` — n8n setzt den Runner auf
  „nicht verfügbar" und **fährt bewusst fort** (`return; // allow bootup`). Nur ein
  Python-Code-Knoten würde scheitern; davon gibt es 0.
- Ein unveränderter Export über Tage. Byte-Stabilität ist der Normalfall.

## Zwei Umgebungsvariablen, die täuschen

| Variable | Befund |
|---|---|
| `N8N_EXECUTIONS_TIMEOUT` | **0 Treffer im Quelltext** von 2.33.7 (Positivkontrolle `N8N_RUNNERS_MODE` → 11 Dateien). Wirkungslos — sie täuscht eine Absicherung vor, die es nie gab. `EXECUTIONS_TIMEOUT` ist die, die wirkt. |
| `WEBHOOK_URL` | **Abgekündigt**, n8n loggt bei jedem Start *„Use N8N_WEBHOOK_URL instead"*. Nicht blind umbenennen — die neue Variable setzt die Basis für Test- **und** Produktions-Webhooks. |

## Die Abnahme, die zählt

**Eine echte Ausführung mit `status=success`** aus `n8n.execution_entity`. Nicht der 200 beim
Speichern, nicht die grüne Oberfläche, nicht ein `/healthz`. Und nach einem Adress-Umbau
zusätzlich: `git grep` im Export-Repo findet die ersetzte Adresse in diesem Workflow **nicht
mehr**.
