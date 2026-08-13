# claude-tabs — Read-Only-Audit aller offenen Claude Code Sessions

> **Use this when:** Status aller offenen Claude-Code-Tabs in einem Shot prüfen, JSONL-Token-Scans, Status-Klassifikation. Stack: Python + Claude Agent SDK.
> **Phase 1.0 — read-only verifiziert.** `send`-Befehl ist BROKEN (siehe Caveats + E203), nicht für Production nutzen.

## Feature-Status (Stand 2026-05-12)

| Befehl | Status | Verified |
|---|---|---|
| `list` | ✓ verified | Cowork-Test 2026-05-12 — gibt Sessions sortiert nach Aktivität |
| `status` | ✓ verified | Tail + Status-Klassifikation funktioniert |
| `scan` | ✓ verified | 99 Findings in initialem Run, später 4 (default --max-files=5). Token-Type "candidate" — Vault-Match nötig (L344) |
| `tail` | ✓ verified | Raw-Tail einer Session |
| `find-waiting` | ✓ verified | Convenience-Filter über `status` |
| `find-errors` | ✓ verified | Convenience-Filter über `status` |
| `send` (Agent SDK) | ✗ BROKEN | `session_store_flush=eager` schreibt NICHT in existing JSONL — siehe E203, L346 |
| `send-direct` (Direct-CLI) | ✓ PARTIAL — Phase 1.1 | `claude --resume <full-id> -p "<prompt>"` SCHREIBT Prompt in JSONL (L357 verified 2026-05-13, 5/5 Sessions). ABER Assistant-Response braucht Joe-Auth (Cowork-Env hat 401). Use für **Pre-Load von Decisions/Updates**, nicht für vollautonome Session-Steuerung |

## Architektur (nach Deep Research 2026-05-12 — send-Pfad falsifiziert durch Live-Test 2026-05-12)

```
Cowork-Claude (mich)
    ↓ CLI-Call (Phase 1) oder MCP (Phase 2)
[claude-tabs/cli.py]
    ↓ Read:  ~/.claude/projects/**/*.jsonl
    ↓ Send:  claude_agent_sdk.query(resume=session_id, session_store_flush="eager")
[laufende Claude Code CLI Sessions in Warp-Tabs]
```

**Schlüssel-Erkenntnis:** `session_store_flush="eager"` aus dem Python Agent SDK gibt near-real-time Transkript-Mirror — löst Lock-Konflikt-Problem zwischen externem `resume` und parallel laufender Session im Warp-Tab. Cross-process resume + crash-durability ist offiziell supported.

**Warum nicht Alternative-Ansätze:**
- **Warp IPC** existiert nicht öffentlich (nur Oz Cloud API für Cloud-Agents)
- **ConPTY-Hijack** auf Windows zu fragil
- **tmux-mcp** wäre sauber, braucht aber Migration des gesamten Workflows
- **T3Code** ist GUI-Frontend, kein Orchestrator
- **OpenCode** wäre Alternative-Stack, braucht ebenfalls Migration

Direkt an Claude Code CLI / Agent SDK andocken ist der saubere Weg — exakt das was T3Code intern macht, nur ohne den Umweg über T3Code.

## Trigger

- "wie ist der status meiner claude tabs"
- "welche sessions warten auf input"
- "send an session X den prompt Y"
- "scan alle sessions auf token-leaks"
- "claude-tabs list / status / send / scan / find-waiting / find-errors"

## Setup (einmalig auf Joe's Windows-Rechner)

```powershell
pip install claude-agent-sdk
```

Python 3.10+ erforderlich. Claude Code CLI ist im SDK bundled.

## Befehle

### `list` — alle Sessions mit Letzter-Aktivität

```bash
python cli.py list                    # Top 25 nach Aktivität sortiert
python cli.py list --active-only      # nur <60 Min aktiv
python cli.py list --json             # JSON-Output für weitere Verarbeitung
```

### `status` — Tail parsen + Status klassifizieren

```bash
python cli.py status                              # alle aktiven Sessions
python cli.py status --project Playbook01         # nur matchende Projekte
python cli.py status --session-id 66966474        # spezifische Session
python cli.py status --active-only                # nur <60 Min aktiv
```

Status-Klassen: `waiting-for-input` 🟡 · `executing-tool` 🟢 · `active` 🟢 · `error` 🔴 · `completed` ⚪ · `unknown` ❔

### `tail` — Raw Tail einer Session

```bash
python cli.py tail 66966474 --lines 50
```

### `send` — Prompt an Session via Agent SDK ⚠ BROKEN (Phase 0.5 — DO NOT USE)

```bash
# DO NOT USE IN PRODUCTION — verified broken 2026-05-12 (siehe ERRORS.md E203)
python cli.py send 66966474 "ja, Option A"
```

**Problem:** Verwendet `claude_agent_sdk.query()` mit `resume=session_id` und `session_store_flush="eager"`. Test 2026-05-12 ergab: Marker-String tauchte NICHT in Ziel-JSONL auf. SDK spawnt vermutlich neue Session statt in existierende JSONL der Warp-Tab-Session zu schreiben.

**Repair-Plan (Phase 1.1 — Backlog):** Direct-CLI-Approach statt SDK:
```python
subprocess.run(["claude", "--resume", session_id, "-p", prompt], cwd=cwd, check=True, capture_output=True, timeout=120)
```
Plus Side-Effect-Verify: pre-send JSONL-size loggen, post-send 5s wait + tail prüfen, assert Marker im JSONL.

**Fallback (Phase 1.0 final):** send-Feature aus diesem Skill droppen, claude-tabs bleibt explizit Read-Only-Audit-Tool. Joe muss manuell Tab anklicken für Input.

### `scan` — Security-Scan über alle Sessions

```bash
python cli.py scan                    # erkennt GitHub PAT, OpenAI, Anthropic, AWS, Slack, Stripe, JWT
python cli.py scan --show-full        # zeigt volle Token-Strings (für Rotation)
```

Findet exakt das was heute passiert ist (GitHub-PAT im Klartext in der Documents-Session).

### `find-waiting` / `find-errors` — Convenience-Filter

```bash
python cli.py find-waiting    # alle Sessions auf User-Input wartend
python cli.py find-errors     # alle Sessions mit Errors in letzten 50 events
```

## Wie Cowork-Claude (ich) das nutzt

Phase 1 (jetzt): Ich rufe `python cli.py <command>` via `mcp__Windows-MCP__PowerShell` auf, parse Output, reportiere konsolidiert. Keine UI-Klicks mehr.

Phase 2 (später): MCP-Server-Wrapper um `cli.py`, damit die Funktionen direkt als Tools aufrufbar sind statt als Subprocess. Vorgesehen: `fastmcp` oder offizielles `mcp` Python-Package.

## Caveats

- **send ist BROKEN** (E203, 2026-05-12): SDK-eager-flush-Mechanismus war über-verkauft, JSONL-Mirror in existing Warp-Session funktioniert nicht. Direct-CLI-Approach via `claude --resume -p` ist im Backlog. Bis Phase 1.1: skill ist Read-Only.
- **scan-Output ist Candidate-Type** (E205, L344): Token-Prefix `sk-` ist nicht service-eindeutig — OpenAI vs OpenRouter vs Kimi vs Brave Search. Vor Service-Aktion: Vault-Slot-Lookup ODER API-Probe ODER JWT-Decode (Issuer-Claim).
- **CWD-Pflicht:** `claude_agent_sdk` braucht den richtigen CWD. Wird automatisch aus Project-Dir-Namen dekodiert (`C--Users-Legion-Documents-Playbook01` → `C:\Users\Legion\Documents\Playbook01`).
- **Output-Streaming:** lange Sessions haben mehrere MB JSONL. CLI nutzt efficient tail-only-read.
- **Token-Sichtbarkeit:** `scan --show-full` zeigt volle Token-Strings im Output. Vorsicht bei Logging.
- **Live-Verify-Pflicht für Tokens** (L343): scan-Findings sagen NICHTS über aktuellen Token-Status. Vor Notfall-Rotation: `GET /user` (GitHub) ODER `GET /v1/auth/key` (OpenRouter) mit beiden Header-Varianten testen.

## Files

- `cli.py` — Python implementation, canonical (Phase 1)
- `SKILL.md` — diese Dokumentation
- ~~`list.ps1`, `status.ps1`, `send.ps1`, `scan.ps1`~~ — DEPRECATED, PowerShell-Versionen aus erster Iteration. Können entfernt werden.

## Roadmap

- [x] Phase 1: Python CLI mit list/status/tail/send/scan/find-waiting/find-errors
- [ ] Phase 2: MCP-Server-Wrapper für direkte Tool-Aufrufe von Cowork
- [ ] Phase 3: Optional Web-UI für Joe (FastAPI + React) als Übersichts-Dashboard
- [ ] Phase 4: Optional Mattermost-Bot-Hook für Push-Benachrichtigungen bei waiting/error
