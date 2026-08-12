# Incident 2026-08-12: MM-Inbound-Zustellung — Raten statt Lesen

**Datum:** 2026-08-12/13 (22:00–00:50 UTC+2)
**Klassifikation:** Prozessbruch, kein Werkzeugfehler. Joe: „Das ist kein Planfehler — es wurde
einfach alles sofort ohne nachzudenken oder letzte Änderungen zu lesen gemacht."
**Status:** behoben (gemessen), Lektionen unten

## Symptom

Brain postete mit neuem Token, aber Mattermost-Inbound kam nicht an: `peer inbox initialized`
erschien, `peer inbox delivered messages` erschien nie. Der REALTEST-7 (Joe→brain) blieb unbeantwortet.

## Was tatsächlich schiefging (Kette)

1. **Kill ohne Blick auf die eigene Session.** Beim Aufräumen alter MCP-Prozesse wurden **alle**
   `aie_mm_mcp.server`-Prozesse beendet — auch der der eigenen Session 7226. OpenCode respawnt MCP
   nicht mitten in der Session. Die Session verlor ihre MM-Werkzeuge. **L-OC-08-Klasse: Der globale
   Kill traf das eigene System.**
2. **Neu gestartet ohne `--session`.** brain wurde via launcher ohne `--session ses_...` gestartet.
   Der launcher dokumentiert `--session` als Resume-Option, aber erst beim genauen Lesen von
   `peer-inbox.mjs` Zeile 94 + 143 wurde klar: **ohne `--session` bleibt `activeSessionID`
   ungesetzt und der Poll greift nie** (`if (activeSessionID) schedulePoll()`). 40 Minuten
   Fehlersuche hätten 2 Minuten Lesen sein können.
3. **Doppelte brain-Instanzen.** Mehrere Starts parallel (ein Prozess mit, einer ohne `--session`),
   was die Verwirrung verlängerte und den Kanal mehrfach pollen ließ.
4. **Joes Start-Befehl brach um.** Die von mir gegebene Zeile wurde beim Einfügen so umgebrochen,
   dass `--session ses_...` als eigenes Kommando ankam (`zsh: command not found: --session`).
5. **Falsche Adressierung im Test.** REALTEST-7 begann mit nacktem `@brain`; der Inbox-Filter
   `_recipients()` in `peer_inbox.py` akzeptiert nur Bracket-Präfix `[sender -> @brain]`. Erst
   REALTEST-7b mit korrektem Präfix wurde zugestellt — und quittiert.

## Beweise

- Manueller Poll `peer_inbox.py poll --role brain --channel ocode-team` lieferte die Nachricht
  `8gmr17k6r7g1mpe4xrezwdknrr` korrekt — Helper war nie kaputt.
- Nach korrektem Start mit `--session`: Log `22:40:13 peer inbox delivered messages role=brain
  sessionID=ses_01KZVZH80EARSKX22DV179C76D`.
- Kanal: brain antwortete `[brain -> @joe] REALTEST-7b quittiert — Inbound-Zustellung empfangen`.

## Was hätte es verhindert (in dieser Reihenfolge)

1. **Erst lesen, dann handeln:** `LEARNINGS.md` + `STATUS.md` + `peer-inbox.mjs` VOR jedem Start
   und jedem Kill. L-OC-15, L-OC-11, L-OC-08 decken die Fehler bereits ab.
2. **Nie alle MCP-Prozesse blind killen.** Nur gezielt die bekannte alte PID; die eigene Session
   zuerst schonen.
3. **Immer mit `--session` starten** — und in README/STATUS explizit schreiben, dass ein Start
   ohne `--session` Inbound funktionslos macht (das stand vorher nicht da).
4. **Einen Start-Befehl als EINE Zeile** übergeben, nie mehrzeilig.

## Regeln (neu verschärft)

- **R-NEUE-1:** Vor jedem Start/Kill/Änderung: die Quelle lesen (LEARNINGS, STATUS, die betroffene
  Modul-Datei), dann handeln. „Raten statt zu lesen wie es sein muss" ist der Fehler, den dieser
  Incident dokumentiert.
- **R-NEUE-2:** Peer-Inbox-Start IMMER mit `--session ses_...` via launcher. Ohne `--session`
  gibt es keine Inbound-Zustellung — das ist jetzt dokumentierte Invariante.
- **R-NEUE-3:** Ein Test mit falschem Adress-Format beweist nichts über die Zustellung. Erst
  Bracket-Präfix `[sender -> @role]` prüfen, dann den Kanal beobachten.
- **R-NEUE-4:** Beim Aufräumen nie global killen; gezielte PIDs, eigene Session zuerst prüfen.

## Korrektur-Eintrag in LEARNINGS.md

Siehe L-OC-16 bis L-OC-19 (hinzugefügt am 2026-08-13).
