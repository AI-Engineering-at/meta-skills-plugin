---
name: debug
description: >
  Debug + Error-Monitoring. Sendet Fehler als Toasts an die Bridge
  (POST /admin/debug/toast) und zeigt Status an.
  Trigger: "debug", "fehler", "error", "toast", "was ist kaputt",
  "status", "plugin fehler", "monitoring".
allowed-tools: [Read, Write, Edit, Bash, Grep, Glob, WebFetch]
user-invocable: true
complexity: agent
version: 2.0.0
type: meta
category: automation
requires: []
produces: [bridge-toast, error-log]
cooperative: false
---

# Debug — Fehler als Toasts an die Bridge

## Architektur

```
Tool-Fehler / Plugin-Fehler / Skill-Error
  │
  ▼
POST /admin/debug/toast ──→ Bridge (10.40.10.83:18790)
  │
  ▼
Im Toast-Log gespeichert → sichtbar auf /admin/debug/health
```

## WAS bei Fehlern tun (kein Text — Aktion!)

### Bei jedem Tool-Fehler (Bash, Write, MCP):

1. Error-Code bestimmen (siehe Registry unten)
2. Toast an Bridge senden:
   ```bash
   curl -s -X POST http://10.40.10.83:18790/admin/debug/toast \
     -H "Authorization: Bearer [ADMIN_TOKEN]" \
     -H "Content-Type: application/json" \
     -d '{
       "level": "error",
       "code": "PLUGIN_WRITE_001",
       "message": "@bybrawe/opencode-loop writeFile→rename failed",
       "source": "opencode-loop",
       "details": {"session": "..."}
     }'
   ```
3. Wenn curl nicht geht: Mattermost-Post als Fallback
4. Im Chat "❌ [debug] Error-Code: ..." erwähnen

### Bei Mattermost-Fehlern (403/404):
```bash
curl -X POST http://10.40.10.83:18790/admin/debug/toast \
  -H "Authorization: Bearer [ADMIN_TOKEN]" \
  -d '{"level":"error","code":"MM_AUTH_403","message":"MM 403 - Token","source":"aie-mm-mcp"}'
```

## Error-Code-Registry

| Code | Wann | Source |
|------|------|--------|
| PLUGIN_WRITE_001 | writeFile→rename schlägt fehl (JSCore-Bug) | OpenCode-Plugin |
| MM_AUTH_403 | Mattermost 403 (Token abgelaufen) | aie-mm-mcp |
| MM_NOT_FOUND_404 | Channel/User nicht gefunden | aie-mm-mcp |
| MODEL_TIMEOUT_001 | Modell antwortet nicht | Bridge/Model |
| LOOP_BLOCKED_001 | Loop hängt >2 Versuche | loop-Skill |
| TOOL_FAILED_001 | Bash/Write-Tool schlägt fehl | Tool-Call |
| BRIDGE_DOWN_503 | Bridge nicht erreichbar | curl-Check |

## Befehle

| Befehl | Wirkung |
|--------|---------|
| `debug status` | Bridge-Status abrufen: curl GET /admin/debug/status |
| `debug toasts` | Letzte Toasts anzeigen: curl GET /admin/debug/toasts |
| `debug toast test` | Test-Toast senden |
| `debug code PLUGIN_WRITE_001` | Error-Code-Details anzeigen |

## Wichtig

1. Kein Fehler verschwindet mehr — jeder wird als Toast gemeldet.
2. Toasts landen im Bridge-Web: http://10.40.10.83:18790/admin/debug/health
3. Bei curl-Fehler: Fallback auf Mattermost-Post nach #agent-tasks
4. ADMIN_TOKEN kommt aus vault/env — nicht hardcoden!
