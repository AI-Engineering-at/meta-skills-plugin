#!/usr/bin/env python3
"""pre-task-frist-eigentuemer-guard — der Zufluss-Riegel fuer den Aufgaben-Rueckstau.

WARUM ES DIESEN HOOK GIBT (2026-07-28)
--------------------------------------
Gemessen an 100 offenen ERPNext-Aufgaben (die zuletzt geaenderten, API-Deckel 100):

    mit Frist (exp_end_date):  0 von 100
    mit Eigentuemer (_assign): 2 von 100
    in EINER Nacht angefasst: 69 von 100
    in dieser Nacht: 30 angelegt, 4 geschlossen

**Eine Aufgabe ohne Frist und ohne Eigentuemer ist ein Wunsch.** Nichts ist je faellig,
nichts je ueberfaellig, nichts zwingt zum Abschluss. Der Bestand waechst, weil der
ZUFLUSS ungebremst ist — nicht weil der Abfluss zu langsam waere. Und der Zufluss bin
ich: eine Aufgabe anzulegen war meine Art geworden, etwas nicht zu entscheiden.

Der Plan-Richter (Fable 5, 2026-07-28): *„Neue Aufgaben in ein System zu schreiben, das
nachweislich nichts austraegt, ist Sichtbarmachen ohne Konsequenz."*

DIE REGEL
---------
Eine Aufgabe wird nur angelegt, wenn sie **einen Eigentuemer** und **eine Frist** traegt.
Fehlt eines, gehoert der Punkt in eine der zwei anderen Ablagen:

  * **Joe-Buendel** — braucht eine Entscheidung. EINE gesammelte Nachricht, nicht sieben.
  * **Ein Satz im Beleg** — muss nur festgehalten werden. raw/-Notiz, KEDB, Handoff.

WARUM ALS HOOK UND NICHT ALS VORSATZ
------------------------------------
`M200`: auch die geschriebene, richtige, auffindbare Regel wird im Moment der Handlung
nicht gelesen. Von 174 Lehren sind vier durchgesetzt. Diese hier ist die fuenfte, weil
sie an der einzigen Stelle sitzt, an der sie wirkt — im Anlege-Vorgang selbst.

ABLEHNUNGS-TEST
---------------
`pre-task-frist-eigentuemer-guard-test.py`, mit echten Aufgaben dieser Nacht. Eine Sperre
ohne bewiesenen deny-Fall ist Dekoration (Hausbeweis: `exploration-first`, 5x exit 0).
"""

import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

LOG = Path.home() / ".claude" / "logs" / "task-zufluss-guard.log"

WERKZEUG = "mcp__aie-erpnext__create_task"

# Frist im Beschreibungstext: "Frist: 2026-08-05" (oder Faelligkeit/Deadline/due)
FRIST_RE = re.compile(r"\b(?:Frist|F[äa]lligkeit|Deadline|due)\s*[:=]\s*(\d{4}-\d{2}-\d{2})", re.I)

# Der Ausweg fuer Faelle, die WIRKLICH keine Frist haben koennen: bewusst und benannt.
AUSNAHME_RE = re.compile(r"\bOHNE-FRIST\s*[:=]\s*\S", re.I)

MAX_HORIZONT_TAGE = 120   # eine Frist in 2 Jahren ist keine Frist


def _log(m: str) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(m + "\n")
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


def pruefe(ti, heute=None):
    # Bewusst ohne PEP-604-Annotation (`date | None`): das System-Python ist aelter als
    # 3.10 und wuerde beim Laden abstuerzen. Der Test hat das gefangen, bevor der Hook
    # registriert war — genau dafuer gibt es ihn.
    """-> (entscheidung, grund). entscheidung in {'weiter','deny'}"""
    heute = heute or date.today()
    betreff = (ti.get("subject") or "").strip()
    text = (ti.get("description") or "") + "\n" + betreff
    eigner = (ti.get("assignee") or "").strip()

    if AUSNAHME_RE.search(text):
        return "weiter", ""                      # bewusst fristlos, mit Begruendung

    m = FRIST_RE.search(text)
    fehlt = []
    if not eigner:
        fehlt.append("**Eigentuemer** (`assignee`)")
    if not m:
        fehlt.append("**Frist** (`Frist: JJJJ-MM-TT` in der Beschreibung)")

    if not fehlt:
        try:
            d = date.fromisoformat(m.group(1))
        except ValueError:
            return "deny", "Die Frist ist kein gueltiges Datum: %r" % m.group(1)
        if d < heute:
            return "deny", ("Die Frist %s liegt in der VERGANGENHEIT. Eine Aufgabe mit "
                            "abgelaufener Frist entsteht schon tot." % d)
        if d > heute + timedelta(days=MAX_HORIZONT_TAGE):
            return "deny", ("Die Frist %s liegt mehr als %d Tage entfernt — das ist keine "
                            "Frist, das ist ein Vielleicht. Entweder naeher setzen oder als "
                            "`OHNE-FRIST: <Grund>` bewusst fristlos anlegen."
                            % (d, MAX_HORIZONT_TAGE))
        return "weiter", ""

    return "deny", (
        "AUFGABE OHNE " + " UND OHNE ".join(x.replace("**", "") for x in fehlt).upper() + ".\n\n"
        "Gemessen an 100 offenen Aufgaben: **0 haben eine Frist, 2 haben einen Eigentuemer** — "
        "und 30 der heute Nacht angelegten stehen noch offen, 4 sind geschlossen. Ein Ticket "
        "ohne diese beiden Felder wird nie faellig, nie ueberfaellig und nie fertig. "
        "**Es ist ein Wunsch, kein Auftrag.**\n\n"
        "Es fehlt: " + ", ".join(fehlt) + "\n\n"
        "Drei Wege, und zwei davon sind meistens der richtige:\n"
        "  1. **Frist + Eigentuemer eintragen** — `assignee` setzen, `Frist: JJJJ-MM-TT` in die "
        "Beschreibung. Nur wenn jemand es wirklich in den naechsten Wochen tut.\n"
        "  2. **Braucht eine Entscheidung?** → ins **Joe-Buendel**, EINE gesammelte Nachricht. "
        "Kein Ticket.\n"
        "  3. **Muss nur festgehalten werden?** → **ein Satz in den Beleg**: `raw/`-Notiz, "
        "KEDB-Eintrag, Handoff. Kein Ticket.\n\n"
        "Wirklich fristlos und trotzdem ein Ticket? Dann schreib `OHNE-FRIST: <Grund>` in die "
        "Beschreibung — bewusst und benannt, nicht beilaeufig."
    )


def main() -> int:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return _weiter()
        payload = json.loads(raw)
    except Exception:
        return _weiter()

    if payload.get("tool_name") != WERKZEUG:
        return _weiter()

    entscheidung, grund = pruefe(payload.get("tool_input") or {})
    if entscheidung == "deny":
        _log("TASK_DENY subject=%r" % (payload.get("tool_input") or {}).get("subject"))
        return _deny(grund)
    return _weiter()


if __name__ == "__main__":
    sys.exit(main())
