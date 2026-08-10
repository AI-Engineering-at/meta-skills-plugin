# n8n betreiben — Version, Deploy, Export, und die drei Fallen

Stand 2026-08-10. Laufende Version **2.33.7**, Dienst `n8n_n8n` 1/1 auf `docker-swarm3:5678`,
PostgreSQL (Schema `n8n`, DB `homelab`), 50 Umgebungsvariablen als Klartext, **0 Docker-Secrets**.

## Falle 1 — nie `docker stack deploy`

Die Compose-Datei beschreibt einen **anderen** Stand als den laufenden: sie deklariert
Verschlüsselungsschlüssel und DB-Passwort über `*_FILE` + Docker-Secrets. Am laufenden Dienst
gemessen: **0 Secrets, 0 `_FILE`-Variablen**.

Ein `stack deploy` tauscht damit den Geheimnis-Mechanismus mit. Greift eine der Quellen nicht,
verliert n8n `N8N_ENCRYPTION_KEY` — und **alle 24 Credentials sind nicht mehr entschlüsselbar**.

> Der Weg ist `docker service update --image`. Er ändert genau eine Größe und lässt Umgebung,
> Secrets, Mounts und Netze unberührt.

## Falle 2 — das Volume ist lokal, die Platzierung war es nicht

`n8n_n8n_data` ist `driver=local` und existiert auf **allen drei Managern mit verschiedenem
Inhalt**: swarm3 723 MB / 21.651 Dateien (das echte), swarm1 23 MB / 6, swarm2 8 KB / 2.

Die Platzierungsregel war nur `node.role == manager` — eine Umplanung hätte n8n stillschweigend
auf eine fast leere Kopie gesetzt. Seit 2026-08-10 gilt `node.hostname==docker-swarm3`.
**Das ist eine Fessel, keine Heilung:** fällt swarm3 aus, läuft n8n nirgends mehr an.

## Falle 3 — `cd` gilt für den ganzen Bash-Aufruf

In einem mehrzeiligen Kommando wirkt ein `cd` auf alle folgenden Zeilen desselben Aufrufs.
Wer danach einen relativen Pfad nutzt, misst am falschen Ort.

## Der Versionssprung

```bash
curl -s https://registry.npmjs.org/-/package/n8n/dist-tags        # stable ist das Ziel, nicht beta
curl -s https://raw.githubusercontent.com/n8n-io/n8n/master/packages/cli/BREAKING-CHANGES.md
# Digest auflösen und pinnen — eine Marke kann umgebogen werden, ein Digest nicht
docker service update --detach --image n8nio/n8n:<version>@sha256:<digest> n8n_n8n
```

**Abnahme, zehn Punkte:** Version über drei Pfade (Image-Label, `n8n --version`, `package.json`
im Container), `/healthz` → `{"status":"ok"}`, `/rest/login` → **401** (nicht 200),
Workflow-/Aktiv-/Credential-Zahl **identisch**, Migrationen **gewachsen**, `N8N_ENCRYPTION_KEY`
gesetzt, **0** Treffer auf `could not be decrypted` im Log — und als einziger, der wirklich
zählt: **eine echte Ausführung mit `status=success`**.

**Rückbau:** `docker service rollback` nur solange **keine** Migration lief. Danach nur mit
DB-Restore — n8n-Migrationen sind vorwärtsgerichtet; ein altes Image auf ein neues Schema ist
kein Rückbau, sondern ein zweiter Schaden.

## Die Export-Kette — der einzige Rückbauweg

n8ns eingebaute Git-Anbindung (`feat:sourceControl`) ist **Enterprise**. Und in der Datenbank
tragen **83 von 83** Workflows genau **einen** `workflow_history`-Eintrag: es gibt nichts, wohin
man zurückrollen könnte. Das Export-Repo ist der Rückbauweg.

| Glied | Wann |
|---|---|
| Export aus der DB → Commit bei echter Änderung | täglich 04:00 per Cron auf swarm3 |
| Geheimnis-Tor vor jedem Push | dito |
| Push über repo-gebundenen Deploy-Key (SSH, Port 2222) | dito |
| Beweis **am Ziel**: `git fetch` + `rev-parse`-Vergleich | dito |
| Frische-Wächter auf swarm1, alle 6 h | Alarm, wenn das Ziel > 48 h hinter dem lokalen Stand liegt |

**Warum der Wächter nicht die Uhr befragt:** Workflow-Definitionen waren über 14 Tage
byte-stabil — ein unveränderter Stand ist der Normalfall. Ein Wächter, der daraus Alarm macht,
wird nach drei Tagen abgeschaltet. Er vergleicht stattdessen zwei unabhängige Orte, gemessen von
einem dritten.

**Warum es überhaupt riss:** Der Push lief über einen Konto-Token, der ungültig wurde. Git fiel
auf die Passwortabfrage zurück, im Cron gibt es kein Terminal. Der Export lief weiter, committete
weiter und **meldete weiter Erfolg** — 20 Commits blieben 23 Tage liegen. Der Absender misst sich
selbst. Deshalb der Beweis am Ziel.

**Wiederherstellen** (am 2026-08-10 gefahren, trägt):

```bash
git log --oneline -- workflows/<name>.json
git show <commit>:workflows/<name>.json
```

Gemessen: Struktur und **Credential-Bindungen überleben** (3 von 3 identisch in Typ und ID).
Grenze: **keine Tiefe** — ein Commit je Datei. Wiederherstellbar ist der aktuelle Stand, nicht
ein früherer.
