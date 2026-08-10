---
name: n8n-workflows-betreiben
description: >
  n8n-Workflows betreiben, aktualisieren und umbauen — an 2.33.7 gemessen: Deploy über
  service update (nie stack deploy), Export-Kette nach Gitea als einziger Rückbauweg,
  native Credential-Typen statt hartverdrahteter IPs, vier Fehlersorten, nebenwirkungsfreie
  Webhook-Probe, Migrations-Bericht für den v3-Sprung.
  Trigger: "n8n", "workflow", "n8n updaten", "workflow kaputt", "webhook 404",
  "credential", "n8n deploy", "workflow exportieren", "hartverdrahtete IP", "code node"
trigger: n8n, n8n updaten, workflow aktivieren, workflow kaputt, webhook antwortet nicht, n8n credential, workflow exportieren, n8n rollback, hartverdrahtete IP im Workflow, n8n breaking changes
version: 1.0.0
type: standard
category: infrastructure
complexity: skill
model: sonnet
allowed-tools: [Read, Grep, Glob, Bash, Write, Edit]
user-invocable: true
token-budget: 6000
requires: []
produces: [workflow-update, erp-task]
cooperative: false
last-audit: 2026-08-10
---

# n8n-Workflows betreiben

Bestand am 2026-08-10, an der laufenden Instanz gemessen: **2.33.7**, Dienst `n8n_n8n` 1/1 auf
`docker-swarm3:5678`, PostgreSQL, **83 Workflows · 39 aktiv · 24 Credentials · 1026 Knoten**.

## Die vier Sätze, die alles andere tragen

1. **Nie `docker stack deploy`.** Die Compose-Datei deklariert Secrets über `_FILE`, der
   laufende Dienst trägt **0** davon. Ein Fehlgriff kostet `N8N_ENCRYPTION_KEY` — und damit
   alle 24 Credentials. Der Weg ist `docker service update --image` mit gepinntem Digest.
2. **Das Export-Repo ist der einzige Rückbauweg.** n8ns Git-Anbindung ist Enterprise, und
   **83 von 83** Workflows haben genau *einen* Historieneintrag in der Datenbank.
3. **Fertig heißt: eine Ausführung mit `status=success`.** Nicht der 200 beim Speichern, nicht
   die grüne Oberfläche.
4. **Adressen gehören in die Credential, nicht in den Knoten.** `httpHeaderAuth` ist der
   einzige Typ *ohne* Adressfeld — genau deshalb stecken heute 115 von 1026 Knoten voller IPs.

## Wann dieses Skill greift

- Ein Workflow scheitert, ein Webhook antwortet nicht, ein Credential ist tot
- n8n soll aktualisiert werden, oder ein Stand zurückgeholt
- Adressen oder Zugangsdaten sollen aus Knoten in Credentials wandern
- Vor jedem Umbau: was bricht still?

**Nicht dafür:** reine Statusfragen („läuft n8n?") — dafür genügt `docker service ls` und
`/healthz`.

## Der Einstieg in jede Diagnose

```bash
# Bestand — der Maßstab für hinterher
docker exec $(docker ps -q -f name=core_postgres) psql -U homelab -d homelab -At -c "
SELECT 'workflows='||count(*) FROM n8n.workflow_entity
UNION ALL SELECT 'aktiv='||count(*) FROM n8n.workflow_entity WHERE active=true"

# Wer scheitert, und wie oft — mit Nenner statt Gefühl
docker exec $(docker ps -q -f name=core_postgres) psql -U homelab -d homelab -c "
SELECT w.name, e.status, count(*) FROM n8n.execution_entity e
JOIN n8n.workflow_entity w ON w.id = e.\"workflowId\"
WHERE e.\"startedAt\" > now() - interval '24 hours' GROUP BY 1,2 ORDER BY 3 DESC"
```

Die Historie reicht nur ~5 Tage zurück (Mengenkappe bei 10.000, nicht Alter). **„0 Läufe" heißt
„nicht in diesem Fenster", nicht „läuft nie".**

## Die vier Fehlersorten

**A — rotiertes Credential** · 100 % Fehler, Log sagt *„Authorization failed"*, das Credential
ist älter als die Rotation. **B — Schlüssel fest im Workflow** · derselbe Effekt, andere
Ursache; er liegt zusätzlich im Export-Repo. **C — Credential-Bindung fehlt ganz** · 401/403,
Gegenprobe: das Ziel antwortet ohne Token, lebt also. **D — überwachtes Ziel ist weg** · keine
Antwort; **Positivkontrolle Pflicht**, sonst hält man einen toten Port für einen toten Host.

Einzelheiten, Belege und die Webhook-Probe: `references/diagnose.md`

## Der Umbau: Adresse und Zugang zusammenführen

Zugangsdaten in den **nativen** Credential-Typ (`mattermostApi` bringt `baseUrl` mit,
`erpNextApi` `domain`, `ollamaApi` `baseUrl`), nicht in `httpHeaderAuth`. Dann ist die Adresse
in der Oberfläche änderbar — ohne den Workflow anzufassen.

Ein Credential schreiben: `PATCH /api/v1/credentials/<id>` → **200**. `PUT` → **405**,
`GET /api/v1/credentials/<id>` → **403**. Schreiben geht, Zurücklesen nicht — die Kontrolle
läuft über eine Ausführung.

> **Eine Sonde auf einen Schreib-Endpunkt ist ein Schreibvorgang.** Wer `PATCH` mit einem
> Wegwerf-Körper probt, um zu sehen *ob* es den Endpunkt gibt, hat das Objekt verändert.
> Verfügbarkeit an einem Wegwerf-Objekt prüfen, nie am Produktivdatensatz.

Tabellen, Zahlen und die Rotations-Regel: `references/credentials.md`

## Vor jedem Umbau: was still bricht

- **13 Code-Knoten in 11 Workflows** greifen per `$('Knotenname')` auf Nachbarn zu. Umbenennen
  bricht sie **ohne Fehlermeldung beim Speichern**.
- **6 Knoten** halten Zustand über `getWorkflowStaticData` — nicht ersetzbar.
- Handgebaute HTTP-Knoten sind im Mittel 1632 Zeichen groß. Kein 1:1-Umbau.

## Aktualisieren und zurückholen

Deploy-Weg, Abnahme in zehn Punkten, Rückbau-Regel (nach einer Migration **nur** mit
DB-Restore), die Export-Kette und der geprüfte Wiederherstellungsweg: `references/betrieb.md`

**Wiederherstellen** ist gemessen und trägt — Struktur und Credential-Bindungen überleben.
Die Grenze steht dabei: **ein Commit je Datei**, also der aktuelle Stand, kein früherer.

## Was diesem Haus verboten ist

- **Kein neues n8n-Repo.** Es gäbe dann zwei, und das bessere wäre das eingefrorene.
- **Kein `N8N_BLOCK_ENV_ACCESS_IN_NODE=true`**, solange 43 Knoten `$env` nutzen — erst wenn die
  Werte in Credentials liegen.
- **Keine n8n-Variablen** (403, Enterprise). Data Tables sind der Community-Weg.
- **Kein Durable Scheduler** auf dem Produktivpfad — Preview, laut Doku änderbar vor GA.

## Belege

Die Messungen hinter jeder Zahl liegen in `~/kb`: ops/RUNBOOK-N8N-UPDATE.md (Versionssprung),
ops/RUNBOOK-N8N-EXPORT-KETTE.md (Export und Wiederherstellung),
ops/PLAN-N8N-2026-08-10-NACH-DEM-SPRUNG.md (Lagebild und Fehler-Typologie),
control-plane/registries/n8n-workflows.yaml (maschinenlesbares Register).
