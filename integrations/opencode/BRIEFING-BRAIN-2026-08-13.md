# Briefing an brain nach dem 2026-08-12/13-Incident

**Empfänger:** brain (persistente Session `ses_01KZVZH80EARSKX22DV179C76D`)
**Absender:** Joe, via Brain-Runner-Session 2026-08-13
**Zweck:** Arbeitsprozesse überarbeiten. Kein Doku-Deko — hier ist die Kette dessen, was
wirklich geschah, und was daraus für brain zwingend folgt.

## 1. Was tatsächlich passiert ist

Ein Abend (12+ Stunden) für ein improvisiertes Setup mit 2 Modellen und viel Joe-Eingaben.
Am Ende hat sich brain **selbst zerschossen** und ein Runner musste einspringen. Joe wörtlich:

> „das ist kein plan fehler! es wurde einfach alles sofort ohne nachzudenken oder letzte
> änderungen zu lesen und co alles gemacht, kein denken, keine logik, und schön garnicht
> alles was claude code cli brain memory oder kb gitea ssot vorschreiben festlegen oder sagen!"

Gemessene Kette (Details: `integrations/opencode/INCIDENT-2026-08-12-mm-inbound.md`):

1. Kill aller `aie_mm_mcp.server`-Prozesse → **auch der eigenen Session**. MCP weg, ohne
   Neustart nicht zurück.
2. brain via launcher **ohne `--session`** gestartet → Inbox `initialized`, nie `delivered`,
   weil `activeSessionID` leer bleibt und der Poll nie feuert. 40 Minuten Fehlersuche statt
   2 Minuten Lesen.
3. Mehrere parallele brain-Instanzen, doppelte Polls.
4. Joe gegebener Start-Befehl brach beim Einfügen um → `--session` als eigenes Kommando.
5. Test-Post mit nacktem `@brain` statt Bracket-Präfix `[sender -> @role]` → still von der
   Inbox ausgeschlossen.

## 2. Der Kernvorwurf: Raten statt Lesen

**Alles, was falsch lief, stand bereits als Lehre in `LEARNINGS.md`** (L-OC-15, L-OC-11,
L-OC-08). Keine dieser Dateien wurde geöffnet, bevor gehandelt wurde. Die Fehler waren
nicht neu — sie waren dokumentiert und vergessen. Genau das sagt Joe: „Eigentlich sollte
das beste Gelernte von dort hier sein, unser ganzes Learning — stattdessen ist in der
Krise alles vergessen und wieder im Kreis gebaut."

## 3. Neue, verpflichtende Regeln für brain

**R-1 — Erst lesen, dann handeln.** Vor jedem Start, Kill, Config-Change oder Dispatch auf
den OpenCode-Adapter: `LEARNINGS.md` + `STATUS.md` + die betroffene Modul-Datei lesen.
Dokumentierte Korrekturen sind die billigste Test-Suite, die es gibt. Raten ist verboten.

**R-2 — Peer-Start nur mit `--session`.** `./.opencode-plugin/launcher --role brain
--channel ocode-team --session ses_01KZVZH80EARSKX22DV179C76D` — eine Zeile, nie umbrechen.
Ein Start ohne `--session` ist ein inbound-toter Peer, kein gültiger Zustand.

**R-3 — Nie global killen.** Aufräumen = gezielte PIDs, eigene Session zuerst prüfen,
Überlebende verifizieren.

**R-4 — Adress-Grammatik prüfen.** Testposts mit `[sender -> @role]`-Bracket-Präfix, nie
nacktem `@role`. Vor „Zustellung kaputt"-Urteil den eigenen Test gegen `_recipients()`
prüfen.

**R-5 — Gitea ist SSOT.** Doku-Änderungen landen in `meta-skills-plugin` (bei Adapter-Themen)
bzw. `~/kb` und werden committet+gepusht. Uncommitted = ungesichert.

## 4. Was brain jetzt tun muss

1. Dieses Briefing + `INCIDENT-2026-08-12-mm-inbound.md` + die neuen L-OC-16..19 lesen.
2. Die eigenen Arbeitsprozesse überarbeiten und **schriftlich fixieren** (wo, entscheidet
   brain, Vorschlag: `~/kb/ops/AGENTS-ARBEITSPROZESSE.md` oder bestehende Prozess-Doku
   ergänzen).
3. Vor dem nächsten Adapter-Eingriff R-1 bis R-4 als Selbstcheck in den Start einbauen
   (z.B. in der eigenen Session-Notiz oder einem Start-Hook).
4. Ergebnis + gemessene Belege zurück an Joe/den Kanal melden.
5. Nicht selbst bauen was der Runner gebaut hat — übernehmen, verifizieren, weiterführen.

## 5. Meta-Analyse der Season

Siehe `SEASON-META-2026-08.md` (Runner-Ergebnis, dieselbe Ablage). brain leitet daraus
ab, welche Skill-/MCP-/Prozess-Änderungen er selbst priorisiert.

*Geschrieben 2026-08-13 von Brain-Runner. Geprüft gegen LEARNINGS/STATUS/README/TODO
und die Live-Logs vom 2026-08-12/13.*
