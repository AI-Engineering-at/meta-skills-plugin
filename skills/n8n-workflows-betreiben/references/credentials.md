# Zugangsdaten und Adressen in n8n — der Kern des Umbaus

Stand 2026-08-10, an n8n 2.33.7 gemessen. Nenner: 83 Workflows, 39 aktiv, 1026 Knoten, 24 Credentials.

## Der Befund in einem Satz

Für jeden Dienst, den wir ansprechen, gibt es einen fertigen Credential-Typ, der **Adresse und
Zugang zusammen** hält und in der Oberfläche bedienbar ist. Genommen wurde stattdessen zehnmal
`httpHeaderAuth` — der **einzige Typ ohne Adressfeld**. Deshalb musste die IP in den Workflow,
und deshalb sind 115 von 1026 Knoten hart verdrahtet.

| Credential-Typ | Adresse | Zugang |
|---|---|---|
| `mattermostApi` | **ja** — `baseUrl` | `accessToken` |
| `erpNextApi` | **ja** — `domain` | `apiKey` + `apiSecret` |
| `ollamaApi` | **ja** — `baseUrl` | `apiKey` |
| `httpHeaderAuth` *(10× im Einsatz)* | **nein** | `name` + `value` |

## Die Umbauregel

1. **Zugangsdaten → nativer Credential-Typ**, nicht `httpHeaderAuth`. Dann wandert die Adresse
   mit und ist unter *Credentials* änderbar, ohne den Workflow anzufassen.
2. **Handgebauter `httpRequest` → nativer Knoten**, wo es einen gibt (Mattermost, ERPNext,
   Ollama). Der native Knoten bringt die Credential mit.
3. **Reine Konfiguration ohne Zugang** (Ports, Pfade, Schwellen) → **Data Table**.
   Gemessen: `api/v1/data-tables` → 200. Variablen und Projekte sind **403 = Enterprise**.
4. **Kein `$env` als Hauptweg** für Adressen. Es funktioniert
   (`N8N_BLOCK_ENV_ACCESS_IN_NODE=false`, 43 Knoten nutzen es), ist aber nur über einen
   Dienst-Neustart änderbar. Notweg, wo kein nativer Typ existiert.

## Wo die Werte liegen

In `n8n.credentials_entity`, verschlüsselt mit `N8N_ENCRYPTION_KEY`. Ohne diesen Schlüssel sind
alle 24 Credentials unlesbar — siehe Falle 1 in betrieb.md.

## Was hart verdrahtet ist (Maßstab für jeden Umbau)

| Ziel | hart verdrahtet | Variable vorhanden, genutzt in |
|---|---|---|
| Mattermost `…83:8065` | **54 Fundstellen / 37 WF** | `MATTERMOST_URL` — 6 Knoten |
| ERPNext `…82:8082` | 14 / 12 WF | `ERPNEXT_URL` — **0** |
| Social Poster `…99:8099` | 12 / 8 WF | `SOCIAL_POSTER_URL` — **0** |
| n8n auf sich selbst | 12 / 11 WF | `N8N_HOST` — **0** |
| Ollama | 6 / 5 WF | `OLLAMA_URL_*` — **0** |

Die Umgebungsvariablen **existieren bereits und werden nicht benutzt**.

## Ein Credential ändern — der gemessene Weg

`PATCH /api/v1/credentials/<id>` mit `{name, type, data}` → **200**.
`PUT` → **405**, `GET /api/v1/credentials/<id>` → **403**. Ein Credential lässt sich also
schreiben, aber nicht zurücklesen; die Kontrolle läuft über eine echte Ausführung.

> **Falle, an einem Produktivdatensatz erlebt:** Wer `PATCH` mit einem Wegwerf-Körper probt,
> um zu sehen *ob* der Endpunkt existiert, **hat damit geschrieben**. Eine Sonde auf einen
> Schreib-Endpunkt ist ein Schreibvorgang. Verfügbarkeit an einem Wegwerf-Objekt prüfen.

## Rotation ist erst fertig, wenn jeder Verbraucher nachgezogen ist

Am 2026-08-02 wurde der n8n-API-Schlüssel rotiert. Erneuert wurde die Dienst-Umgebung; das
gespeicherte Credential blieb stehen. Folge: zwei Wächter-Workflows scheiterten acht Tage lang
zu 100 %, zusammen rund 1.500 Fehlläufe pro Tag — und einer davon war der Dead-Man-Switch, der
seinen eigenen Tod nicht meldet.

Verbraucherliste für diesen einen Schlüssel: Dienst-Umgebung `N8N_API_KEY` · das n8n-Credential ·
OpenBao. Vor dem Abhaken einer Rotation: Liste erheben, jeden einzeln messen.
