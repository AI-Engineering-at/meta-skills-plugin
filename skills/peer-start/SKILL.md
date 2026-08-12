---
name: peer-start
description: Peer-Session starten oder Adapter-Eingriff vorbereiten — der EINE korrekte Start-Befehl mit --session und die Check-Liste vor jedem Start/Kill/Config-Change am OpenCode-Adapter. Trigger bei "peer starten", "brain starten", "vibe starten", "Session starten", "Adapter-Eingriff", "MCP killen/aufräumen", "Peer neu starten", oder VOR jeder Aktion am OpenCode-Peer-Setup.
---

# Peer-Start — der eine korrekte Weg (R-2)

## Warum dieser Skill existiert

Incident 2026-08-12: Ein Start ohne `--session` ließ die Inbox `initialized` melden,
aber nie `delivered` — 40 Minuten Fehlersuche statt 2 Minuten Lesen. Diese Seite ist
der Copy-Paste-Block, der das verhindert. Details: `integrations/opencode/INCIDENT-2026-08-12-mm-inbound.md`.

## Pflicht-Lektüre VOR jedem Adapter-Eingriff (R-1)

1. `integrations/opencode/LEARNINGS.md` (insbesondere L-OC-16..19)
2. `integrations/opencode/STATUS.md`
3. Die betroffene Modul-Datei (z. B. `peer-inbox.mjs`, `launcher`, `peer_inbox.py`)

Dokumentierte Korrekturen sind die billigste Test-Suite, die es gibt. Raten ist verboten.

## Der EINE Start-Befehl (eine Zeile, nie umbrechen)

```sh
/Users/mackbook/code-aie/meta-skills-plugin/.opencode-plugin/launcher --role brain --channel ocode-team --session <SES_ID>
```

Rollen: `brain`, `vibe`, `ocode-kimi`, `ocode-pruefer` (alle Default `#ocode-team`).

**Invariante:** Ein Start OHNE `--session` ist inbound-tot (Poll feuert nie:
`if (activeSessionID) schedulePoll()`). Kein gültiger Peer-Zustand.

## Check-Liste vor jedem Start/Kill/Config-Change

- [ ] LEARNINGS.md + STATUS.md gelesen (R-1)
- [ ] Läuft schon eine Instanz dieser Rolle? `ps aux | grep "opencode.*--agent <role>"` — wenn ja: NICHT starten (Ein-Instanz-Regel)
- [ ] Kill geplant? Eigene Session-PID notieren, nur gezielte fremde PIDs killen — niemals `pkill -f aie_mm_mcp.server` (R-3, L-OC-17)
- [ ] Start-Befehl als EINE Zeile vorbereitet, mit `--session <SES_ID>` (R-2)
- [ ] Nach Start: Log auf `peer inbox delivered messages role=<role> sessionID=<SES_ID>` geprüft — ohne diesen Beleg ist der Peer inbound-tot

## Nach dem Start

- Zustellungs-Test mit Bracket-Präfix: `[sender -> @role]`, nie nacktem `@role` (R-4, L-OC-19).
- Antworten in `#ocode-team` als neue Top-Level-Posts (`post_message`), nie `reply_thread`.
- Belege und Doku nach Gitea committen + pushen (R-5).
