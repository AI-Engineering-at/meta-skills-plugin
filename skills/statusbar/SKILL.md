---
name: statusbar
description: Session Lifecycle — Statusline, Watcher, Sync. Real-time Model/Costs/Context/Limits with Rainbow. Per-session guardian that cleans up on terminal death and warns on RAM spikes.
trigger: statusbar, statusline, session watcher, session lifecycle, token usage, kosten, costs, rate limits
model: haiku
allowed-tools: [Read, Bash]
user-invocable: true
complexity: skill
last-audit: 2026-07-26
version: 1.3.0
token-budget: 200
type: utility
category: monitoring
requires: []
produces: [status-display]
cooperative: false
---

# meta:statusbar — Session Lifecycle (Statusline + Watcher + Sync)

Three components, one system. All in `meta-skills/scripts/`, all cross-platform.

## Architecture

```
SessionStart Hook
  ├── session_init.py → spawns session-watcher.py (detached)
  └── Statusline → statusline.py (every second via settings.json)

During Session
  ├── Statusline: Model, Cost, Context, Limits, Σ-Stats
  └── Watcher: Parent-PID alive? RAM ok? Heartbeat writing

SessionEnd Hook
  └── session-end-sync.py → create open-notebook KB source
```

## 1. Statusline (`statusline.py`)

```
◆ O5(1M) X │ █████████░░░ 77% │ €70.19 │ I:50.9M O:177k C:99% │ 3h10m │ Σ44.5B Σ275d Σ€38k │ 5h:2%(3h16m) 7d:31%(114h59m) │ Max
```

**Drei Bereiche, streng getrennt** — das war die häufigste Verwechslung:

| Bereich | Was | Zeitraum |
|---|---|---|
| **now** | `€70.19`, `I:`/`O:`/`C:`, `3h10m` | nur diese Session |
| **live** | `5h:…` `7d:…` | Anthropics laufende Rate-Limit-Fenster |
| **total** | `Σ44.5B Σ275d Σ€38k` | seit echter Account-Anlage |

### Jedes Feld: Bedeutung · Herkunft · Zusammensetzung · Persistenz · Ausschlüsse

#### `O5(1M)` — Modell + Kontextfenster
Bereich **now**. Modell-Kurzname und Fenstergröße *dieser* Session.
**Woher:** `model.id` + `context_window.context_window_size` aus dem Hook-JSON, pro Render neu.
**Zusammensetzung:** Familie + Version über `statusline_lib.parse_model_id`; deckt
`opus`/`sonnet`/`haiku`/`fable`, das alte Zweizahl-Schema (`opus-4-7`) und die bloßen
Einzelzahlen der 5er-Familie (`opus-5`) ab. **Wohin:** nirgends, reine Anzeige.

#### `X`/`L`/`M`/`H` — Effort
Bereich **now**. **Woher:** `~/.claude/settings.json` Feld `effortLevel`. **Wohin:** nirgends.

#### `█████████░░░ 77%` — Kontextfenster-Füllung
Bereich **now**. Wie voll das Fenster *jetzt* ist; resettet bei `/compact`.
**Woher:** `context_window.used_percentage`. **Wohin:** nirgends.
**Nicht:** kein Verbrauchsmaß — nur, wieviel gerade geladen ist.

#### `€70.19` — Kosten dieser Session
Bereich **now**. Anthropics eigener kumulativer Wert, die **einzige Kostenwahrheit** im
ganzen System. **Woher:** `cost.total_cost_usd`, umgerechnet mit `usd_eur_rate` aus dem
Annahmen-Register. **Zusammensetzung:** von Anthropic geliefert, hier nicht nachgerechnet.
**Wohin:** wird pro Render in `~/.claude/statusline-alltime.json` fortgeschrieben — nicht für
die Anzeige, sondern als **Kalibrier-Referenz** für das Aggregat (§ Kalibrierung).
**Nicht:** ohne dokumentierten Kurs steht hier `$`, nie ein Dollarbetrag mit `€`-Label.

#### `I:50.9M O:177k C:99%` — Token dieser Session
Bereich **now**, kumulativ.
**Woher:** dem **Session-Transkript** (`~/.claude/projects/<slug>/<session_id>.jsonl` plus
`<session_id>/subagents/**`), nicht dem Hook-JSON.
**Zusammensetzung:** `I:` = gesamte Input-Seite (`input_tokens` + `cache_read` +
`cache_write`). `O:` = `output_tokens`. `C:` = `cache_read / Input-Seite`.
Duplikate sind entfernt: Claude Code schreibt eine Nachricht während des Streamings mehrfach
(bis 42× gemessen), Dedup-Schlüssel ist `requestId`, letzte Zeile gewinnt.
**Wohin:** Sidecar `~/.claude/statusline-session-cache/<session_id>.json` mit `offset` +
`requestId`-Abbildung, damit pro Render nur die neuen Bytes gelesen werden.
**Nicht:** **nicht** `context_window.total_input/output_tokens` — das ist ein Schnappschuss
des Fensters und resettet bei `/compact`; er lieferte `out:1k` für eine 3-Stunden-Session.
Kein Transkript gefunden → `I:— O:—`, nie eine erfundene 0.

#### `3h10m` — Dauer dieser Session
Bereich **now**. **Woher:** `cost.total_duration_ms`. **Wohin:** `time_ms` in
`statusline-alltime.json` — dient dem Gültigkeitstest der Kalibrierung.

#### `Σ44.5B Σ275d Σ€38k` — seit Account-Anlage
Bereich **total**. Reihenfolge **Token → Tage → Ersparnis**.
**Woher:** `~/.claude/statusline-usage-agg.json`, gebaut von `scripts/usage_aggregate.py`.
Die Leiste **rechnet hier nichts** — der Vollscan gehört nicht in einen 1-Sekunden-Render.
**Zusammensetzung:**
- `Σ44.5B` = gemessene Token des Fensters **+** Hochrechnung für die Lücke bis
  `accountCreatedAt`. **Mit Cache** (96 % des Volumens sind Cache-Token).
- `Σ275d` = Tage seit `~/.claude.json` `oauthAccount.accountCreatedAt`.
- `Σ€38k` = **Ersparnis** = All-time-Kosten − (aufgerundete Monate × `subscription_usd_per_month`).
**Wohin:** nirgends — abgeleitet, nicht persistiert.
**Nicht enthalten:** **nur dieser Rechner.** Thor@.91 und aidalon@legion haben eigene
Transkripte. Gemessen 44,5 Mrd. hier; über ~20 Oberflächen ergibt das die Größenordnung
~890 Mrd. Host-Aggregation ist noch nicht gebaut.
**Fehlt das Aggregat, entfällt der ganze Block** — keine Σ-Nullen.

#### `5h:2%(3h16m) 7d:31%(114h59m)` — Rate-Limit-Fenster
Bereich **live**. Anthropics eigene Werte, 1:1 durchgereicht.
**Woher:** `rate_limits.five_hour/seven_day.used_percentage` + `.resets_at`.
**Nicht:** von diesem Skript nicht berechnet und nicht korrigiert.

#### `Max` — Abo-Tier
**Woher:** `~/.claude.json` → `oauthAccount.organizationRateLimitTier`, gemappt über
`parse_rate_limit_tier` (`default_claude_max_20x` → `Max`).
**Nicht:** **kein** `(+$X saved)` mehr. Das war derselbe Wert wie `Σ€38k` minus dem
Abo-Preis — ein Geldwert zweimal in einer Zeile.

Rainbow: HSV Phase Shift (`time.time() * 0.3`), Separatoren + Σ-Symbole schimmern.

## 2. Session Watcher (`session-watcher.py`)

Spawnt als detached Hintergrundprozess bei SessionStart.

| Was | Wann | Aktion |
|-----|------|--------|
| Parent-PID tot | Alle 10s Check | 30s Grace → Children killen → Heartbeat loeschen → Exit |
| RAM > 4 GB | Alle 10s | Desktop-Notification (Win/Mac/Linux) |
| RAM Spike > 500 MB | Innerhalb eines Intervalls | Desktop-Notification |
| Session > 24h | Einmal | Desktop-Notification |

Heartbeats: `~/.claude/watchers/{pid}.json`

```bash
# Show all watchers
python meta-skills/scripts/session-watcher.py --list

# Clean up orphaned heartbeats
python meta-skills/scripts/session-watcher.py --cleanup-orphans
```

## 3. Session-End Sync (`session-end-sync.py`)

Automatic via SessionEnd hook. Collects today's git commits, posts as source in open-notebook KB.

Logs: `~/.claude/sync-logs/sync-YYYY-MM-DD.log`

## 4. Process Monitor (`process-monitor.py`)

Manual tool for system overview (not automatic, not in statusline).

```bash
python meta-skills/scripts/process-monitor.py --status    # Alle claude-Prozesse
python meta-skills/scripts/process-monitor.py --report    # Markdown-Report
python meta-skills/scripts/process-monitor.py --cleanup   # Zombies killen
python meta-skills/scripts/process-monitor.py --install   # Als Scheduled Task
```

## Cross-Platform

| Feature | Windows | macOS | Linux |
|---------|---------|-------|-------|
| Prozess-Erkennung | claude.exe | claude / node | claude / node |
| Notifications | PowerShell Balloon | osascript | notify-send |
| Scheduler Install | schtasks | launchd plist | crontab |
| Watcher Detach | CREATE_NO_WINDOW | start_new_session | start_new_session |

## Configuration

Everything in `~/.claude/settings.json`:
```json
"statusLine": { "type": "command", "command": "python3 .../statusline.py", "padding": 0 },
"hooks": {
  "SessionStart": [{ "hooks": [{ "command": "python3 .../session_init.py" }] }],
  "SessionEnd":   [{ "hooks": [{ "command": "python3 .../session-end-sync.py" }] }]
}
```

### Datenquellen und warum es drei Ebenen gibt (Stand 2026-07-26)

| Datei | Rolle | Wahrheit über |
|---|---|---|
| Hook-JSON pro Render | Live-Zustand | Session-Kosten, Rate-Limits, Modell, Kontextfüllung |
| `~/.claude/projects/**/*.jsonl` | Rohbeleg | Token pro Session und pro Sub-Agent |
| `~/.claude/statusline-usage-agg.json` | Aggregat (von `usage_aggregate.py`) | All-time-Σ |
| `~/.claude/statusline-alltime.json` | Cache **+** Kalibrier-Quelle | Anthropics echte Kosten je beobachteter Session |
| `~/.claude/statusline-assumptions.json` | Annahmen mit Herkunft | Kurs, Abo-Preis, Toleranzen |

`statusline-alltime.json` ist ausdrücklich **keine** Wahrheit über Σ mehr. Sie wird von N
parallelen `claude`-Prozessen geschrieben; der Per-PID-Tmp-Trick plus `os.replace` schützt die
Datei, nicht den Inhalt — ein Prozess mit veraltetem Snapshot im Speicher löscht fremde
Session-Keys. Da die Wahrheit jetzt in den Transkripten liegt, ist dieser Race
**strukturell** erledigt statt abgesichert.

### Kalibrierung — die einzige Brücke von Token zu Kosten

Kosten sind aus Token **nicht** ableitbar. Gemessen 2026-07-26 gegen Anthropics eigenen
`cost.total_cost_usd`: die Token-Preisrechnung lag bei 63 % (Sonnet-5-Session) bzw. 140 %
(Opus-5[1m]-Session) — kein systematischer Faktor. Und die Transkripte enthalten kein
Kostenfeld (Record-Keys: `requestId`, `uuid`, `isSidechain`, `message.usage` — kein `costUSD`).

Deshalb: `usage_aggregate.calibration()` bildet pro beobachteter Session
`echte Kosten / token-gepreiste Kosten` und mittelt. Eine Session zählt nur, wenn die Leiste
sie **vollständig** gesehen hat — Test: Hook-Dauer ≈ Transkript-Spanne, Toleranz
`calibration_span_tolerance`. Gemessen: Session `4e56a2b8` 3,26 h vs. 3,26 h → gültig,
Faktor 1,062. Session `2ab1310f` 39,9 h vs. 29,6 h → verworfen, ihr Kostenwert ist
unvollständig und ergab einen um 62 % verzerrten Faktor.

Das verbessert sich selbst: jede neue Session legt einen echten Kostenwert dazu. Keine
Konstante, keine Pflege-Auflage.

### Annahmen-Register

Alle Annahmen liegen in `~/.claude/statusline-assumptions.json`, jede mit **`value`,
`stand`, `quelle`, `notiz`**. Ein Eintrag ohne `stand` + `quelle` wird beim Laden
**verworfen**, nicht stillschweigend benutzt.

| Annahme | Wert | Stand | Quelle |
|---|---|---|---|
| `usd_eur_rate` | 0,87897 | 2026-07-24 | Frankfurter API (EZB-Referenzkurse) |
| `subscription_usd_per_month` | 200,00 | 2026-07-26 | `organizationRateLimitTier = default_claude_max_20x` |
| `cache_write_ttl_default` | `5m` | 2026-07-26 | claude-api-Skill: 1,25× input (5m) bzw. 2,0× (1h) |
| `continuous_usage_since_account_creation` | true | 2026-07-26 | Joe explizit, Session `4e56a2b8` 09:40 |
| `calibration_span_tolerance` | 0,25 | 2026-07-26 | Messung 4e56a2b8 gültig / 2ab1310f verworfen |
| `scope_single_machine` | true | 2026-07-26 | `~/.claude/projects` existiert pro Rechner |

### Was am 2026-07-26 falsch war — und was daraus folgt

| Defekt | Wirkung | Ursache |
|---|---|---|
| Σ-Token summierte nur `input + output` | 396 M angezeigt statt 44,5 Mrd. — **Faktor ~110** | 96 % des Volumens sind Cache-Token |
| Zwei handgesetzte Tagesraten (`AUDITED_DAILY_RATE_*`) | $155/Tag statt verifizierter $168/Tag (8 % zu niedrig) | Konstante mit Pflege-Auflage; wurde nie nachgezogen |
| `MIN_RATE_BASIS_DAYS`-Zweig | hätte nach 3 Tagen still die Basis gewechselt und Σ springen lassen | Heuristik auf zu wenig Daten |
| `Σ$43k` **und** `Max(+$41k saved)` | derselbe Geldwert zweimal, Differenz = Abo-Preis | zwei Codepfade für eine Zahl |
| `Σ275d(3)` | 275 Tage aus 3 Sessions — in sich widersprüchlich | Session-Zähler neben hochgerechnetem Zeitraum |
| `stats-cache.json` als Kostenquelle verworfen | „`costUSD: 0` ⇒ keine Kostendaten" | die Token lagen in derselben Datei; ein Rechenschritt fehlte |
| drei Reader, kein Abgleich | Bridge 36 %, Rohscan 90 %, Anthropic 100 % | niemand hat sie gegeneinander geprüft |

**Die generische Lehre, in `~/kb/ops/KNOWN-ERRORS-DB.md` festgehalten:** ein leeres Feld macht
eine Datenquelle nicht unbrauchbar, und zwei Implementierungen derselben Größe sind erst dann
eine Messung, wenn sie gegeneinander geprüft wurden. Deshalb erzwingt `usage_aggregate.py` den
Drei-Wege-Abgleich, und `Totals` trennt `tokens_io` von `tokens_cache` von `tokens_all` — damit
niemand mehr „total" schreiben und in+out meinen kann.

**Plan-Label (2026-07-26, weiter gültig):** `plan = "Max" if total_ctx >= 1_000_000 else "Pro"`
war eine Heuristik ohne dokumentierten Zusammenhang zwischen Fenstergröße und Abo-Tier. Jetzt
wird der echte Tier aus `~/.claude.json` gelesen; die alte Heuristik greift nur, wenn Datei
oder Feld fehlen.

### Mac interpreter pin (live 2026-07-26, Brain@Mac)

`statusline.py` / `statusline_lib.py` use `datetime.UTC` and PEP-604 return
annotations (`tuple[...] `, `X | None`) — both need **Python ≥ 3.11**.
macOS's default `python3` (`/usr/bin/python3`, CommandLineTools) is **3.9.6**
and fails with `ImportError: cannot import name 'UTC' from 'datetime'`.
Activated `statusLine` command on this Mac pins an explicit newer
interpreter instead of bare `python3`:

```json
"statusLine": {
  "type": "command",
  "command": "/opt/homebrew/bin/python3.12 /Users/mackbook/code-aie/meta-skills-plugin/scripts/statusline.py",
  "padding": 0
}
```

Verify before reusing on another Mac: `python3 --version` may resolve to a
different interpreter per-host (Homebrew vs. system vs. pyenv) — don't
assume the path above is portable, re-check `which -a python3*` first.

## Examples

### Example 1: Check statusline output

```
◆ O5(1M) X │ █████████░░░ 77% │ €70.19 │ I:50.9M O:177k C:99% │ 3h10m │ Σ44.5B Σ275d Σ€38k │ 5h:2%(3h16m) 7d:31%(114h59m) │ Max
```

Fehlt das Aggregat oder das Session-Transkript, zeigt die Leiste ehrlich weniger statt
erfundene Nullen:

```
◆ O5(1M) X │ █░░░░░░░░░░░ 10% │ $0.50 │ I:— O:— │ 1m00s │ Max
```

Aggregat manuell nachziehen (die Leiste stößt das sonst alle 6 h abgekoppelt selbst an):

```bash
python3 meta-skills/scripts/usage_aggregate.py --force   # ~6 s beim ersten Mal, dann ~0,3 s
python3 meta-skills/scripts/usage_aggregate.py --show    # Aggregat inkl. Kalibrierung ansehen
```

### Example 2: Manage session watchers

```bash
# List all active watchers
python meta-skills/scripts/session-watcher.py --list

# Clean up orphaned heartbeats
python meta-skills/scripts/session-watcher.py --cleanup-orphans
```

### Example 3: Process monitoring

```bash
# Show all claude processes
python meta-skills/scripts/process-monitor.py --status

# Generate markdown report
python meta-skills/scripts/process-monitor.py --report
```
