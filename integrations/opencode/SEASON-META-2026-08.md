# Season-Meta-Analyse 2026-08 — OpenCode-Peer-Setup

**Stand:** 2026-08-13
**Quellen:** `git log --since=2026-08-01` (meta-skills-plugin), `LEARNINGS.md`, `STATUS.md`,
`INCIDENT-2026-08-12-mm-inbound.md`, Live-Logs 2026-08-12/13.
**Methode:** gemessen aus Commits, Logs und State-Dateien — keine Meinung ohne Beleg.

## 1. Das wiederkehrende Muster (gemessen)

Seit 01.08. eine Kette von Fehler-Fix-Commits am Adapter:

```
MCP-403 (875d46a) → Bridge-Quarantäne (3451063) → Bridge raus (8d202bb) → Provider raus (12a635e)
→ --auto-Sperren (cfad817, d5be1c4, d403123) → Inbound-tot-ohne---session (Incident 12.08.)
```

**Meta-Muster:** Jeder Schritt heilte ein Symptom und erzeugte das nächste. Kein Schritt
enthielt den vorherigen als Lektion — die `fix`-Kette selbst ist das Anti-Pattern.

**Root-Causes (3, jede gemessen):**

1. **Keine Lesepflicht vor Aktion.** L-OC-15 (Kanal existiert nicht), L-OC-11 (Session ≠
   Modell), L-OC-08 (Session-Flags nicht global) standen vor dem Incident in
   `LEARNINGS.md`. Keine wurde geöffnet. → Fix: R-1 (lesen vor handeln) + Start-Hook.
2. **`--session`-Zwang nicht dokumentiert.** Der Launcher beschrieb `--session` nur als
   Resume-Option. Die Tatsache, dass ohne `--session` der Inbound **konstruktionsbedingt tot
   ist**, stand nirgends. → Fix: jetzt in STATUS.md/README.md/peer-comms fixiert.
3. **Kein Selbstschutz beim Kill.** `pkill -f aie_mm_mcp.server` traf die eigene Session.
   → Fix: R-3 (gezielte PIDs, eigene Session zuerst).

## 2. Prozess-Brüche, die zu vermeiden waren (Was)

1. **12h für ein improvisiertes Setup** mit 2 Modellen statt erst den IST-Stand (SSOT) zu
   prüfen. Was da ist und wie es sein muss — wurde nicht gelesen.
2. **Kein Plan, keine Taskliste, kein Gate.** Es wurde „sofort alles gemacht" statt
   Schritt-für-Schritt mit gemessenem Zwischenstand. Jeder Schritt sollte einen
   Positiv-Befund haben, bevor der nächste startet.
3. **Joe musste 2× eingreifen** (killen, neu starten). Zwei Mal hat das Setup den
   Menschen gebraucht, wo die Doku es hätte verhindern können.
4. **Mehrfach-Instanzen** (mehrere brains parallel) ohne Dedupe-Mechanismus.

## 3. Meta-Learnings für die nächste Saison

| # | Learning | Umsetzung |
|---|---|---|
| M1 | Dokumentierte Lehre > neue Diagnose | LEARNINGS.md ist Pflicht-Lektüre vor Adapter-Aktionen; neue Fehler dort eintragen (R-1) |
| M2 | Ein Start-Befehl = eine Zeile | Launcher-Aufrufe als Copy-Paste-Block mit einer Zeile bereitstellen |
| M3 | Inbound braucht `--session`, sonst ist er tot | Dokumentiert + im Peer-Start vertraglich verankert (R-2) |
| M4 | Globale Kills sind Selbstmord | Aufräumen nur gezielt, eigene Session prüfen (R-3) |
| M5 | Der Test muss die echte Grammatik treffen | `[sender -> @role]` statt nacktem `@role` (R-4) |
| M6 | Fix-Ketten = Symptom von fehlender Wurzelanalyse | Vor jedem fix: „war das schon mal da? was steht im LEARNINGS?" |
| M7 | SSOT lesen, nicht raten | Gitea/`~/kb` sind die Quelle; „wie es sein muss" steht dort, nicht im Kopf |

## 4. Konkrete Verbesserungen (Skill-/MCP-/Prozess-Ebene)

**Skills:**
- `peer-comms` korrigiert: Kanal `#ocode-team`, Bracket-Grammatik, `--session`-Pflicht.
  (getan, 2026-08-13)
- Neu empfehlen: **`peer-start`-Skill** mit dem EINEN korrekten Start-Befehl (R-2) und
  der Check-Liste vor jedem Adapter-Eingriff. Verhindert die Fehlerklasse „falsch gestartet".

**MCP:**
- `aie-mm-mcp`: Der Respawn-Fall ist ein offener Punkt — opencode respawnt MCP nicht
  mid-session. Empfehlung: Eine Gesundheits-Probe „ist mein MCP noch da?" als Skill-Check
  vor MM-Aktionen; kein fix im Server, bis der tatsächliche Neustart-Pfad gemessen ist.

**Prozess:**
- **Start-Gate für Adapter-Eingriffe:** erst `LEARNINGS.md` + `STATUS.md` lesen, dann
  handeln. Als Hook denkbar, aber Joe: Hooks sind keine Lösung außer ein Minimum — deshalb
  Prozess-Pflicht (R-1), nicht neue Hook-Komplexität.
- **Ein-Instanz-Regel:** Vor jedem Peer-Start prüfen, ob schon eine Instanz läuft
  (`ps ... grep "opencode --agent <role>"`), sonst nicht starten.
- **Befehle als Copy-Paste-Einzeiler:** keine mehrzeiligen Start-Befehle an Joe geben.

## 5. Was das Team daraus macht (Vorschlag)

- **brain:** übernimmt das Briefing, verankert R-1..R-5 in seiner Prozess-Doku, baut den
  Selbstcheck „habe ich LEARNINGS gelesen?" in seinen Start.
- **Runner (diese Doku):** abgeschlossen mit diesem Dokument + Incident + Briefing.
- **vibe/kimi/pruefer:** keine Änderung nötig — sie liefen korrekt mit `--session`; ihre
  Starts sind die Positivkontrolle für R-2.

## 6. Gemessener Abschluss-Zustand

- Inbound live bewiesen: `peer inbox delivered messages role=brain
  sessionID=ses_01KZVZH80EARSKX22DV179C76D` (Log) + brain-Antwort im Kanal (REALTEST-7b).
- Genau eine brain-Instanz läuft mit `--session` (PID 27635).
- Doku: Incident, Briefing, LEARNINGS L-OC-16..19, STATUS, README, peer-comms, TODO — alle
  aktualisiert und konsistent.
