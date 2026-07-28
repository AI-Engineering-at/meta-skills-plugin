#!/usr/bin/env python3
"""pre-bash-kedb-vorhalt — legt den passenden KEDB-Eintrag VOR der Handlung vor.

WARUM ES DIESEN HOOK GIBT (2026-07-28)
--------------------------------------
In der Nacht 27./28.07. habe ich die DNS-Aufloesung im ganzen Netz fuer Minuten
abgeschaltet, mit einem `dnsmasq/service/reconfigure`. Die Warnung davor hatte ich
**wenige Stunden vorher selbst geschrieben**, in `KE-2026-07-28-B`:

    „Bewusst NICHT angewendet: kein reconfigure. Solange ISC laeuft, koennte dnsmasq
     Port 67 nicht binden — zwei DHCP-Server teilen ihn sich nicht."

Formuliert, begruendet, committet — und dann die Handlung ausgefuehrt, vor der sie warnt.
Joe: *„ja wie waere es zuerst Doku lesen, Plan machen und dann umsetzen?? wtf bro"*

`M200` benennt die Klasse: **zwischen der eigenen Aufzeichnung und der eigenen naechsten
Handlung gibt es keinen Weg. Ich schreibe ins Substrat und lese aus dem Gedaechtnis.**
Das erklaert auch, warum von 174 Lehren nur vier durchgesetzt sind — auch die richtige,
auffindbare Lehre wird im Moment der Entscheidung nicht geoeffnet.

WAS ER TUT
----------
Er blockiert **nichts**. Er legt vor. Vor einem zustandsaendernden Kommando an einem
System, zu dem KEDB-Eintraege existieren, blendet er deren Titel und die `Falle`-Zeile
ein — die Zeile, die sagt, *warum die naheliegende Diagnose falsch war*.

DIE REGEL TRAEGT IHRE ABSICHT SELBST
------------------------------------
Kein zu pflegender Schluesselwort-Katalog. **Der Index sind die `tags:` der KEDB-Eintraege
selbst** (gemessen: 93 % der 191 Eintraege tragen Tags). Wer einen Eintrag schreibt,
pflegt damit automatisch den Vorhalt. Eine Liste, die man separat pflegen muesste, wuerde
nicht gepflegt — das ist bei uns belegt.

AUSLOESER IST DAS SYSTEM, NICHT DIE UNSICHERHEIT
------------------------------------------------
Gefuehlte Sicherheit ist genau der Zustand, in dem nicht nachgesehen wird. Deshalb haengt
der Vorhalt am *Kommando*, nicht an einem Zweifel.
"""

import json
import os
import re
import sys
from pathlib import Path

# Portabel: auf legion/anderen Hosts liegt kb woanders. Fehlt sie, tut der Hook
# nichts (kein Fehler) — statt auf einem fremden Rechner ins Leere zu greifen.
KB_WURZEL = Path(os.environ.get("AIE_KB_ROOT", str(Path.home() / "kb")))
KEDB = KB_WURZEL / "ops" / "KNOWN-ERRORS-DB.md"
MAX_EINTRAEGE = 3          # mehr liest niemand
MIN_TAG_LAENGE = 4         # 'dns' o.ae. traefe zu breit

# Verben, die Zustand aendern. Lesen loest nichts aus.
AENDERT_RE = re.compile(
    r"\b(reconfigure|restart|reload|stop|start|apply|enable|disable"
    r"|del_\w+|delete|destroy|remove|\brm\b|prune|wipe|reset"
    r"|set_\w+|add_\w+|/set\b|/add\b"
    r"|migrate|upgrade|update|install|reboot|shutdown|poweroff"
    r"|qm\s+\w+|pct\s+\w+|pvesm\s+\w+|vzdump|zfs\s+\w+"
    r"|systemctl\s+(?!status)|service\s+\w+\s+(?!status)"
    r"|docker\s+(service\s+update|stack\s+deploy|rm|kill|stop|restart)"
    r"|--force|-f\b)",
    re.I,
)

# Reine Lese-Kommandos: auch wenn ein Verb drinsteht, nichts vorhalten.
NUR_LESEN_RE = re.compile(r"^\s*(cat|less|head|tail|grep|rg|ls|find|git\s+(log|show|diff|status))\b")


def _weiter(zusatz=None):
    print(json.dumps({"additionalContext": zusatz} if zusatz else {"continue": True}))
    return 0


def eintraege_laden():
    """-> [(id, titel, tags:set, falle:str)] — leise leer bei Problemen."""
    try:
        text = KEDB.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    raus = []
    bloecke = re.split(r"\n#{2,4}\s+(?=KE-)", text)
    for b in bloecke[1:]:
        kopf = b.split("\n", 1)[0]
        m = re.match(r"(KE-[\w-]+)\s*—\s*(.*?)(?:\s*\(tags:\s*(.*?)\))?\s*$", kopf)
        if not m:
            continue
        kid, titel, roh = m.group(1), m.group(2), (m.group(3) or "")
        # Tags stehen an ZWEI Stellen: in der Ueberschrift `(tags: …)` — nur 89 von 208 —
        # und im Feld `- **Tags:** …`. Beide lesen, sonst indiziert der Vorhalt nur 43 %.
        feld = re.search(r"^\s*[-*]\s*\*\*Tags:?\*\*\s*(.+)$", b, re.M)
        if feld:
            roh = roh + " " + feld.group(1)
        tags = {t.strip().lower() for t in re.split(r"[,\s]+", roh) if len(t.strip()) >= MIN_TAG_LAENGE}
        f = re.search(r"^\s*[-*]\s*\*\*Falle:?\*\*\s*(.+)$", b, re.M)
        raus.append((kid, titel.strip(), tags, (f.group(1).strip() if f else "")))
    return raus


def treffer(cmd, eintraege):
    """KEDB-Eintraege, deren Tags im Kommando vorkommen — juengste zuerst."""
    klein = cmd.lower()
    gefunden = []
    for kid, titel, tags, falle in eintraege:
        passend = sorted(t for t in tags if t in klein)
        if passend:
            gefunden.append((kid, titel, passend, falle))
    gefunden.sort(key=lambda x: x[0], reverse=True)     # KE-JJJJ-MM-TT-X sortiert chronologisch
    return gefunden[:MAX_EINTRAEGE]


def bauen(gefunden):
    z = ["⚠️  KEDB-VORHALT — zu diesem System gibt es dokumentierte Faelle. "
         "M200: die eigene Aufzeichnung wird vor der Handlung nicht geoeffnet, sondern erinnert. "
         "Hier ist sie:\n"]
    for kid, titel, passend, falle in gefunden:
        z.append("• **%s** — %s" % (kid, titel[:150]))
        z.append("  getroffen ueber: %s" % ", ".join(passend[:4]))
        if falle:
            z.append("  **Falle:** %s" % falle[:400])
        z.append("")
    z.append("Kein Blocker. Aber wenn einer davon dein Kommando betrifft: "
             "`kb/ops/KNOWN-ERRORS-DB.md` **oeffnen**, nicht erinnern.")
    return "\n".join(z)


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return _weiter()
        payload = json.loads(raw)
    except Exception:
        return _weiter()

    if payload.get("tool_name") != "Bash":
        return _weiter()
    cmd = (payload.get("tool_input") or {}).get("command", "") or ""
    if not cmd or NUR_LESEN_RE.match(cmd) or not AENDERT_RE.search(cmd):
        return _weiter()

    gefunden = treffer(cmd, eintraege_laden())
    return _weiter(bauen(gefunden) if gefunden else None)


if __name__ == "__main__":
    sys.exit(main())
