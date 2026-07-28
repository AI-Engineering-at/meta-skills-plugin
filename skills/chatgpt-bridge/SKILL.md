---
name: chatgpt-bridge
description: Zugriff auf ChatGPT Plus/Pro-Abos via die Phantom Neural Cortex LLM Bridge. Nutzt den Responses-API-Transport mit PKCE-OAuth (Code-Paste-Flow). Mehrere Abos = mehrere Credentials mit eigenem Token-File, Round-Robin-Auswahl durch den Credential-Pool der Bridge.
trigger: chatgpt, codex, responses, chatgpt-abo, openai oauth, gpt-5, o3, gpt-5-pro, o4-mini, "brauch ich chatgpt", "chatgpt account"
model: sonnet
allowed-tools: [Read, Bash, Task, WebFetch]
user-invocable: true
complexity: skill
last-audit: 2026-07-28
version: 1.0.0
token-budget: 4000
type: meta
category: infrastructure
requires: []
produces: [chatgpt-request]
cooperative: false
---

# ChatGPT-Abo-Zugriff via Phantom Bridge

## Architektur

```
Claude Code (Du)  ── HTTP ──>  Phantom Bridge (10.40.10.83:18790)
                                     │
                                     ├─ CredentialPool (4-6 Abos, Round-Robin)
                                     ├─ OAuthTokenManager (PKCE, Refresh)
                                     └─ _chat_responses() ──> api.openai.com/v1/responses
                                                                      │
                                                                      └─ ChatGPT Plus/Pro (OAuth)
```

## Bridge-API (ChatGPT-Modelle)

Die Bridge exponierte ChatGPT-Modelle unter `/v1/chat/completions` (OpenAI-kompatibel):

| Modell-ID | Upstream | Reasoning | Tools |
|-----------|----------|-----------|-------|
| `chatgpt/o3` | o3 | ja | ja |
| `chatgpt/gpt-5` | GPT-5 | ja | ja |
| `chatgpt/gpt-5-pro` | GPT-5 Pro | ja | ja |
| `chatgpt/o4-mini` | o4-mini | nein | ja |

### API-Call

```bash
curl -X POST http://10.40.10.83:18790/v1/chat/completions \
  -H "Authorization: Bearer $PHANTOM_BRIDGE_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "chatgpt/o3",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": true
  }'
```

## Einrichtung eines neuen Abos

### 1. Provider checken
Sicherstellen, dass `chatgpt_codex`-Provider in der Bridge-Config existiert (`config/llm-bridge.yaml`):
```yaml
chatgpt_codex:
  type: responses
  auth_mode: oauth2
  base_url: https://api.openai.com
  chat_path: /v1/responses
  oauth_config:
    client_id_env: OPENAI_CODEX_CLIENT_ID
    authorize_url: https://auth.openai.com/oauth/authorize
    token_url: https://auth.openai.com/oauth/token
    scope: openid profile email offline_access
```

### 2. OAuth-Client-ID setzen
```bash
export OPENAI_CODEX_CLIENT_ID=app_EMoamEEZ73f0CkXaXp7hrann
```
(Public Client, kein `client_secret` nötig — PKCE regelt das.)

### 3. Abo anmelden (Code-Paste-Flow)
Die Settings-UI der Bridge unter `http://10.40.10.83:18790/settings`:
1. OAuth-Tab → "ChatGPT-Abo hinzufügen"
2. Browser öffnet sich → bei OpenAI anmelden
3. Code aus URL kopieren → in UI einfügen → "Token eintauschen"
4. Credential wird automatisch angelegt

Oder via CLI-Skript:
```bash
python3 scripts/openai_anmelden.py --konto abo1
```

### 4. Token erneuern
Passiert automatisch per `refresh_token` (in der Bridge). Falls nötig:
```bash
curl -X POST http://10.40.10.83:18790/settings/api/oauth/chatgpt_codex/authorize-flow \
  -H "Authorization: Bearer $TOKEN"
```

## Troubleshooting

| Problem | Ursache | Lösung |
|---------|---------|--------|
| "403 Forbidden" | Token abgelaufen/widerrufen | Neu anmelden via UI |
| "400 Stream must be true" | `stream: false` gesendet | Bridge setzt das automatisch |
| "no eligible credentials" | Alle Abos verbraucht/erschöpft | Neues Abo hinzufügen |
| "Provider not found" | Config fehlt | `chatgpt_codex` in Bridge-Config prüfen |
