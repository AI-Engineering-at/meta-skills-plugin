#!/usr/bin/env python3
"""pre-write-negativbefund-guard — die fehlende Sperre fuer M126/M196/M197.

WARUM ES DIESEN HOOK GIBT (2026-07-28)
--------------------------------------
In der Nacht 27./28.07. entstanden 13 Fehlbehauptungen. Danach wurden zwei Sperren
gebaut — eine fuer Commit-Nachrichten, eine fuer Repo-Identitaet. **Keine fuer die
Fehlerklasse der Nacht.** Der Plan-Richter (Fable 5) hat das gefunden, TRON hat es
unabhaengig verschaerft:

    „Bewusstsein ist NICHT der Fix — nur externe Erzwingung wirkt. Deine Eval-Faelle
     sind Detektion NACH dem Fakt. Du koenntest uebersehen, dass dein eigener Fix
     noch Detektion statt Praevention ist."                            — TRON, 2026-07-28

Dieser Hook ist die Praevention: ein Negativbefund ueber ein KONKRET BENANNTES Ziel
darf nicht ins Substrat geschrieben werden, ohne dass im Transkript dieser Sitzung
eine Sonde auf genau dieses Ziel steht.

WARUM NEGATIV UND NICHT POSITIV
-------------------------------
Gemessen (M197): Negativ-Behauptungen loesen Neuaufbau, Loeschung, Alarm aus — sie
sind die teuersten. Positiv-Meldungen sind haeufiger falsch, aber ihre Absicherung
laesst sich nicht mechanisch pruefen (ein Hook kann nicht wissen, ob das Gemessene
die Frage beantwortet). Deshalb: hier die mechanisch erzwingbare Haelfte, die andere
traegt der Berichts-Vertrag im SUBAGENT-BRIEF-TEMPLATE.

DIE REGEL TRAEGT IHRE ABSICHT SELBST
------------------------------------
Kein zu pflegender Host-Whitelist (die wird nicht gepflegt — belegte Lehre). Ausgeloest
wird nur, wenn ein Zustandswort **im selben Satz** neben einem konkreten Ziel steht
(IPv4, unsere Zonen, oder ein Backtick-Bezeichner). Ohne konkretes Ziel: nur Hinweis,
keine Sperre — eine allgemeine Aussage richtet keinen Schaden an.

ABLEHNUNGS-TEST
---------------
`pre-write-negativbefund-guard-test.py` enthaelt echte Faelle dieser Nacht, davon
mindestens einen, der abgelehnt WERDEN MUSS. Ein Hook ohne bewiesenen deny-Fall ist
Dekoration — Hausbeweis: `exploration-first` ist registriert, 5x sys.exit(0), nie ein
einziges deny.

WIRKSAMKEIT — GEMESSEN, NICHT BEHAUPTET (2026-07-28)
----------------------------------------------------
Gegen die 13 echten Fehlbehauptungen der Nacht 27./28.07. durchgerechnet.
**Gefangen haette dieser Hook 2 von 13.** Das ist kein Versagen, sondern die
gemessene Reichweite — und sie deckt sich exakt mit TRONs Klassen-Teilung:

  GEFANGEN (2) — Klasse `unverified-assumption`, gar nicht nachgesehen:
    * „`10.40.10.34` ist eine tote Dublette"  -> kein Ping vor dem Urteil
    * „Home Assistant existiert nicht"        -> nur PVE-Knoten durchsucht, nie `.8`

  NICHT GEFANGEN, WEIL POSITIV (4) — dieser Hook ist fuer Negativbefunde:
    NetBird laeuft / Backend steht / Hook erzwingt Identitaet / Sicherung laeuft taeglich
    -> traegt der Berichts-Vertrag im SUBAGENT-BRIEF-TEMPLATE, nicht dieser Hook.

  NICHT GEFANGEN, WEIL FALSCHE SONDE (4) — Klasse `proxy-instead-of-use`:
    legion/NetBird · aidalon still · Neustart fand nicht statt · drei Dienste ausgefallen
    -> in ALLEN vier stand das Ziel im Transkript. Es wurde gemessen — nur das Falsche.
       **Ein Hook kann pruefen, OB gemessen wurde. Er kann nicht pruefen, ob das
       Gemessene die Frage beantwortet.** (TRON, 2026-07-28: genau deshalb ist diese
       Klasse die am schwaechsten erzwungene.)

  NICHT GEFANGEN, WEIL KEIN KONKRETES ZIEL (3):
    „das Update laedt noch" · „sechs Entwuerfe ohne Sign-off" · „27 Hooks unversioniert"
    -> bewusst: ohne benanntes Ziel richtet eine Aussage keinen Loesch-/Neubau-Schaden an.

FAZIT, ohne Schoenrederei: dieser Hook schliesst die **mechanisch erzwingbare Haelfte**
und laesst die andere offen. Er ist damit 2/2 in seiner Klasse und 0/8 ausserhalb.
Wer ihn fuer die ganze Fehlerklasse haelt, macht denselben Fehler nochmal — er prueft
dann den Stellvertreter „ein Hook existiert" statt die Sache „der Fehler passiert nicht".
"""

import json
import re
import sys
from pathlib import Path

LOG = Path.home() / ".claude" / "logs" / "negativbefund-guard.log"
BLICK_FENSTER = 400          # so viele Transkript-Zeilen zurueck
NAH = 260                    # Zeichen-Abstand Zustandswort <-> Ziel (etwa ein Satz)

# Nur wo eine Behauptung DAUERHAFT wird. Fluechtige Notizen sind nicht das Problem.
SUBSTRAT_RE = re.compile(
    r"/(kb|memory)/.*\.(md|markdown)$"
    r"|/(META-LEARNINGS|KNOWN-ERRORS-DB|SYSTEM-FACTS|INCIDENT-FACTS|STATE|HANDOVER)\.md$"
    r"|/kb/(ops|control-plane|raw|wiki|infrastructure)/",
    re.I,
)

# Der Hook darf sich nicht selbst blockieren, und Tests/Beispiele auch nicht.
AUSNAHME_RE = re.compile(r"negativbefund-guard|/tests?/|-test\.py$|ZUSTANDS-LEXIKON", re.I)

# Geschlossene Klasse: Woerter, die einen NICHT-Zustand behaupten.
# Bewusst klein und ohne Pflegebedarf — das sind die Woerter, die Loeschung/Neubau ausloesen.
NEGATIV_RE = re.compile(
    r"\b("
    r"ist tot|sind tot|tote[nrs]?\b|leiche"
    r"|existiert nicht|existieren nicht|gibt es nicht|nicht vorhanden|nicht existent"
    r"|ist down|sind down|offline\b|nicht erreichbar|unerreichbar"
    r"|antwortet nicht|reagiert nicht|keine antwort"
    r"|fehlt\b|fehlen\b|kein[e]? (?:reservierung|eintrag|sicherung|backup|hook|prozess|dienst|zugang)"
    r"|ist leer|sind leer|leer\b"
    r"|laeuft nicht|läuft nicht|laufen nicht|ist gestoppt|abgestuerzt|abgestürzt"
    r"|ist kaputt|defekt\b|ausgefallen"
    r"|does not exist|is dead|is down|not reachable|missing\b"
    r")",
    re.I,
)

# Konkretes Ziel: IPv4, unsere Zonen, host:port, oder ein Backtick-Bezeichner.
ZIEL_RE = re.compile(
    r"(?:\b\d{1,3}(?:\.\d{1,3}){3}\b"
    r"|\b[\w.-]+\.(?:nb\.aie|aie\.lan|ai-engineering\.at)\b"
    r"|\b[\w-]+:\d{2,5}\b"
    r"|`([\w][\w.:@/-]{2,40})`)"
)

# Wortteile, die als "Ziel" nur Rauschen waeren.
ZIEL_MUELL_RE = re.compile(r"^(true|false|null|none|https?|md|py|sh|json|yaml|main|head|deny|ok)$", re.I)

# Ein Beleg IM Dokument selbst zaehlt auch — dann steht die Messung ja da.
BELEG_IM_TEXT_RE = re.compile(
    r"(gemessen|live-probe|rohausgabe|exit=|HTTP \d{3}|`{3}|\$ (?:ping|curl|ssh|dig|nc|pvesh)"
    r"|Sonde:|zurueckgelesen|zurückgelesen)",
    re.I,
)


def _log(msg: str) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def _weiter() -> int:
    print(json.dumps({"continue": True}))
    return 0


def _deny(grund: str) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": grund,
    }}))
    return 0


def ziele_im_satz(text: str) -> list[str]:
    """Konkrete Ziele, die NAH an einem Zustandswort stehen."""
    treffer: list[str] = []
    for m in NEGATIV_RE.finditer(text):
        fenster = text[max(0, m.start() - NAH): m.end() + NAH]
        for z in ZIEL_RE.finditer(fenster):
            roh = (z.group(1) or z.group(0)).strip("`")
            if ZIEL_MUELL_RE.match(roh) or len(roh) < 3:
                continue
            if roh not in treffer:
                treffer.append(roh)
    return treffer


def transkript_erwaehnungen(transcript: str, limit: int = BLICK_FENSTER) -> str:
    """Alles, was in dieser Sitzung an Werkzeuge ging — als eine Textflaeche.

    Fehlschlag ist bewusst leise, faellt aber auf die STRENGERE Seite (leer =
    'kein Blick gefunden'), damit ein unlesbares Transkript das Tor nicht oeffnet.
    """
    if not transcript:
        return ""
    try:
        p = Path(transcript)
        if not p.is_file():
            return ""
        with p.open("r", encoding="utf-8", errors="replace") as f:
            zeilen = f.readlines()[-limit:]
    except Exception:
        return ""

    stuecke: list[str] = []
    for zeile in zeilen:
        if '"tool_use"' not in zeile and '"tool_result"' not in zeile:
            continue
        try:
            eintrag = json.loads(zeile)
        except Exception:
            stuecke.append(zeile)          # lieber roh als gar nicht
            continue
        inhalt = (eintrag.get("message") or {}).get("content")
        if isinstance(inhalt, list):
            for block in inhalt:
                if isinstance(block, dict):
                    stuecke.append(json.dumps(block.get("input") or "", ensure_ascii=False))
                    c = block.get("content")
                    if isinstance(c, str):
                        stuecke.append(c[:4000])
    return "\n".join(stuecke)


def pruefe(file_path: str, content: str, transcript_text: str):
    """-> (entscheidung, grund). entscheidung in {'weiter','deny'}"""
    if not file_path or AUSNAHME_RE.search(file_path):
        return "weiter", ""
    if not SUBSTRAT_RE.search(file_path):
        return "weiter", ""
    if not content or not NEGATIV_RE.search(content):
        return "weiter", ""

    ziele = ziele_im_satz(content)
    if not ziele:
        return "weiter", ""                      # allgemeine Aussage: kein Schaden

    if BELEG_IM_TEXT_RE.search(content):
        return "weiter", ""                      # die Messung steht im Dokument selbst

    ungeprueft = [z for z in ziele if z.lower() not in transcript_text.lower()]
    if not ungeprueft:
        return "weiter", ""

    return "deny", (
        "NEGATIVBEFUND OHNE SONDE (M126/M197). Du schreibst in "
        f"{Path(file_path).name} einen Nicht-Zustand ueber: {', '.join(ungeprueft[:4])} — "
        "aber im Transkript dieser Sitzung steht keine Sonde auf dieses Ziel.\n\n"
        "Ein Negativbefund loest Neuaufbau, Loeschung und Alarm aus; er ist die teuerste "
        "Aussage, die du treffen kannst. Und er ist fast immer ein SONDEN-ARTEFAKT: "
        "'legion hat kein NetBird' war eine Linux-Sonde auf Windows; '.34 ist eine tote "
        "Dublette' war eine lebende Maschine an einem anderen Standort.\n\n"
        "Zwei Wege weiter — beide dauern unter einer Minute:\n"
        "  1. MISS ES: ping/curl/ssh/pvesh gegen das Ziel, dann erneut schreiben.\n"
        "  2. SCHREIB DEN BELEG MIT: Rohausgabe, 'Sonde:', 'gemessen', exit=, HTTP-Code "
        "oder einen Code-Block ins Dokument — dann traegt der Text seinen Nachweis selbst.\n\n"
        "Sonde passt nicht zum Gegenstand? Dann ist die Sonde der erste Verdaechtige, "
        "nicht das Ziel."
    )


# --- Bash-Zweig -------------------------------------------------------------
# Joe, 2026-07-28: "so kannst du doch nicht arbeiten" — die erste Fassung hing nur
# am Write-Werkzeug. Mein eigener Hauptweg ins Substrat ist aber Bash: Heredocs,
# Umleitungen, python3 - <<'PY'. Eine Sperre, die den Hauptweg nicht sieht, ist
# die Halbheit, gegen die sie gebaut wurde.

# Ein SCHREIB-Vorgang, nicht ein Lesevorgang. Ohne das wuerde `grep 'ist tot' kb/…`
# faelschlich ausgeloest.
SCHREIBT_RE = re.compile(
    r">>?\s*[\"']?[\w./~$-]*(?:kb|memory)/"          # > kb/… bzw. >> ~/kb/…
    r"|\btee\s+(?:-a\s+)?[\"']?[\w./~$-]*(?:kb|memory)/"
    r"|\.write_text\(|\.writelines\(|\.write\("        # pathlib / file-Objekt
    r"|open\([^)]*[\"'][wa]\+?[\"']"                   # open(..., 'w'/'a')
    r"|\bsed\s+-i\b"
    r"|\bcat\s*>>?",
    re.I,
)

# Welche Substrat-Datei ist gemeint? (fuer die Begruendung + den SUBSTRAT_RE-Test)
SUBSTRAT_PFAD_RE = re.compile(
    r"[\w./~$-]*(?:kb|memory)/[\w./-]*\.(?:md|markdown)\b"
    r"|(?:META-LEARNINGS|KNOWN-ERRORS-DB|SYSTEM-FACTS|INCIDENT-FACTS|STATE|HANDOVER)\.md",
    re.I,
)


def bash_ziel_datei(cmd: str) -> str:
    """Schreibt dieses Kommando in eine Substrat-Datei? -> Pfad, sonst ''."""
    if not cmd or not SCHREIBT_RE.search(cmd):
        return ""
    m = SUBSTRAT_PFAD_RE.search(cmd)
    if not m:
        return ""
    p = m.group(0).lstrip("\"'")
    # SUBSTRAT_RE erwartet einen Pfad mit fuehrendem /kb/ bzw. /memory/
    return p if p.startswith("/") else "/" + p.lstrip("~").lstrip("./")


def main() -> int:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return _weiter()
        payload = json.loads(raw)
    except Exception:
        return _weiter()

    werkzeug = payload.get("tool_name")

    if werkzeug == "Bash":
        cmd = (payload.get("tool_input") or {}).get("command", "") or ""
        ziel = bash_ziel_datei(cmd)
        if not ziel:
            return _weiter()
        entscheidung, grund = pruefe(
            ziel, cmd, transkript_erwaehnungen(payload.get("transcript_path", "")))
        if entscheidung == "deny":
            _log(f"NEGATIV_DENY_BASH ziel={ziel}")
            return _deny(grund + "\n\n(Erkannt im Bash-Schreibweg — Heredoc/Umleitung "
                                 "zaehlt genauso wie das Write-Werkzeug.)")
        return _weiter()

    if werkzeug not in ("Write", "Edit", "NotebookEdit"):
        return _weiter()

    ti = payload.get("tool_input") or {}
    file_path = ti.get("file_path", "") or ""
    content = ti.get("content") or ti.get("new_string") or ""

    entscheidung, grund = pruefe(
        file_path, content, transkript_erwaehnungen(payload.get("transcript_path", "")))

    if entscheidung == "deny":
        _log(f"NEGATIV_DENY path={file_path}")
        return _deny(grund)
    return _weiter()


if __name__ == "__main__":
    sys.exit(main())
