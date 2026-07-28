#!/usr/bin/env python3
"""Ablehnungs-Test fuer pre-write-negativbefund-guard.

PFLICHT seit 2026-07-28: eine Sperre gilt erst als vorhanden, wenn ein Test belegt,
dass sie ABLEHNEN kann. Hausbeweis fuers Gegenteil: `exploration-first` ist registriert,
laeuft 5x auf sys.exit(0) und hat nie ein einziges deny gesprochen.

Die deny-Faelle sind ECHTE Fehlbehauptungen der Nacht 27./28.07. — keine Konstruktion.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import importlib.util

spec = importlib.util.spec_from_file_location(
    "guard", Path(__file__).parent / "pre-write-negativbefund-guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

KB = "/Users/mackbook/kb/ops/KNOWN-ERRORS-DB.md"
RAW = "/Users/mackbook/kb/raw/2026-07-28-bericht.md"
CODE = "/Users/mackbook/code-aie/phantom-ai/server.py"

FAELLE = [
    # --- MUSS ABLEHNEN: echte Fehlbehauptungen dieser Nacht, ohne Sonde ---
    ("deny", "echt: tote Dublette (nichts geloescht, weil ein Ping es widerlegte)",
     KB, "Der Knoten `10.40.10.34` ist eine tote Dublette und kann weg.", ""),

    ("deny", "echt: Home Assistant existiert nicht (lief auf .8, HTTP 200)",
     KB, "Home Assistant existiert nicht — `10.40.10.8` traegt keinen Dienst.", ""),

    ("deny", "echt: drei Dienste ausgefallen (0/0 heisst bewusst aus)",
     RAW, "Die Dienste hinter `swarm1` sind ausgefallen, Replicas stehen auf 0.", ""),

    ("deny", "echt: Update laedt noch (war fertig, Status stand auf error)",
     RAW, "Die Firewall `10.40.10.1` antwortet nicht auf die Statusabfrage.", ""),

    ("deny", "Zone-Ziel ohne Sonde",
     KB, "Der Dienst `hub.ai-engineering.at` ist down seit gestern.", ""),

    # --- MUSS DURCHLASSEN ---
    ("weiter", "dasselbe Ziel, aber die Sonde steht im Transkript",
     KB, "Der Knoten `10.40.10.34` ist eine tote Dublette und kann weg.",
     '{"command": "ping -c2 10.40.10.34"}'),

    ("weiter", "Beleg steht im Dokument selbst (Rohausgabe)",
     KB, "Home Assistant existiert nicht auf `10.40.10.8`.\n\nSonde: `curl -sS -o /dev/null "
         "-w '%{http_code}' http://10.40.10.8:8123` -> HTTP 000, gemessen 04:12.", ""),

    ("weiter", "allgemeine Aussage ohne konkretes Ziel — richtet keinen Schaden an",
     RAW, "Viele unserer Watcher laufen nicht, das muss aufgeraeumt werden.", ""),

    ("weiter", "POSITIV-Aussage — dieser Hook ist fuer Negativbefunde",
     KB, "Der Knoten `10.40.10.34` laeuft und antwortet auf Port 22.", ""),

    ("weiter", "kein Substrat-Pfad (Produktionscode faellt unter andere Hooks)",
     CODE, "# `10.40.10.34` ist tot, deshalb der Fallback", ""),

    ("weiter", "der Hook darf sich selbst nicht blockieren",
     "/Users/mackbook/.claude/hooks/pre-write-negativbefund-guard.py",
     "'.34 ist tot' war eine lebende Maschine.", ""),

    ("weiter", "das Zustands-Lexikon darf seine eigenen Woerter fuehren",
     "/Users/mackbook/kb/ops/ZUSTANDS-LEXIKON.md",
     "`antwortet-nicht` — der Dienst auf `10.40.10.99` ist down.", ""),
]


# --- Bash-Schreibweg (Joe 2026-07-28: "so kannst du doch nicht arbeiten") -----
# Echte Kommandoformen dieser Nacht — so schreibe ich tatsaechlich ins Substrat.
BASH_FAELLE = [
    ("deny", "Heredoc in die KEDB, Negativbefund ohne Sonde",
     "cat >> ~/kb/ops/KNOWN-ERRORS-DB.md <<'EOF'\n"
     "### KE-2026-07-28-X\nDer Knoten `10.40.10.34` ist eine tote Dublette.\nEOF", ""),

    ("deny", "python3-Heredoc (mein haeufigster Weg) schreibt Negativbefund",
     "cd ~/kb && python3 - <<'PY'\nimport pathlib\n"
     "p=pathlib.Path('ops/META-LEARNINGS.md')\n"
     "p.write_text(p.read_text()+'Der Dienst `hub.ai-engineering.at` ist down.')\nPY", ""),

    ("deny", "einfache Umleitung in einen raw-Bericht",
     "echo 'Home Assistant existiert nicht auf `10.40.10.8`' >> ~/kb/raw/2026-07-28-x.md", ""),

    ("weiter", "derselbe Heredoc, aber die Sonde steht im Transkript",
     "cat >> ~/kb/ops/KNOWN-ERRORS-DB.md <<'EOF'\nDer Knoten `10.40.10.34` ist tot.\nEOF",
     '{"command": "ping -c2 10.40.10.34"}'),

    ("weiter", "Heredoc mit mitgeschriebenem Beleg",
     "cat >> ~/kb/raw/x.md <<'EOF'\n`10.40.10.99` antwortet nicht.\n"
     "Sonde: `ping -c3 10.40.10.99` -> 3 packets transmitted, 0 received. gemessen 04:30.\nEOF", ""),

    ("weiter", "LESEN ist kein Schreiben — grep darf Zustandswoerter suchen",
     "grep -n 'ist tot' ~/kb/ops/KNOWN-ERRORS-DB.md | head", ""),

    ("weiter", "Schreiben ausserhalb des Substrats",
     "echo '`10.40.10.34` ist tot' >> /tmp/notiz.md", ""),

    ("weiter", "Commit-Nachricht ist kein Substrat",
     "git commit -F /tmp/m.txt   # '`10.40.10.99` existiert nicht'", ""),

    ("weiter", "Substrat-Schreiben ohne Negativbefund",
     "cat >> ~/kb/ops/META-LEARNINGS.md <<'EOF'\n`10.40.10.34` laeuft und antwortet.\nEOF", ""),
]


def main() -> int:
    ok = fehl = 0

    print("  --- Write/Edit-Weg")
    for erwartet, name, pfad, inhalt, transkript in FAELLE:
        got, grund = guard.pruefe(pfad, inhalt, transkript)
        if got == erwartet:
            ok += 1
            print(f"  ok    [{erwartet:6}] {name}")
        else:
            fehl += 1
            print(f"  FEHL  [erwartet {erwartet}, bekam {got}] {name}")
            if grund:
                print(f"        Grund: {grund.splitlines()[0]}")

    print("\n  --- Bash-Schreibweg (Heredoc / Umleitung / python3 -)")
    for erwartet, name, cmd, transkript in BASH_FAELLE:
        ziel = guard.bash_ziel_datei(cmd)
        got, grund = ("weiter", "") if not ziel else guard.pruefe(ziel, cmd, transkript)
        if got == erwartet:
            ok += 1
            print(f"  ok    [{erwartet:6}] {name}")
        else:
            fehl += 1
            print(f"  FEHL  [erwartet {erwartet}, bekam {got}] {name}   ziel={ziel!r}")

    gesamt = len(FAELLE) + len(BASH_FAELLE)
    denies = sum(1 for f in FAELLE if f[0] == "deny") + sum(1 for f in BASH_FAELLE if f[0] == "deny")
    print(f"\n  {ok}/{gesamt} bestanden · {denies} deny-Faelle · {fehl} Fehler")
    if denies == 0:
        print("  !! KEIN EINZIGER deny-FALL — diese Sperre waere Dekoration.")
        return 1
    return 1 if fehl else 0


if __name__ == "__main__":
    sys.exit(main())
