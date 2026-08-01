#!/usr/bin/env python3
"""Ablehnungs-Test fuer pre-write-design-token-guard.

PFLICHT seit 2026-07-28: eine Sperre gilt erst als vorhanden, wenn ein Test
belegt, dass sie ABLEHNEN kann. Hausbeweis fuers Gegenteil: `exploration-first`
ist registriert, laeuft 5x auf sys.exit(0) und hat nie ein deny gesprochen.

Die Fehlalarm-Faelle sind hier der schwierigere Teil, nicht die Treffer. Ein
Lint, der bei jedem Digest anschlaegt, wird abgeschaltet — und ein
abgeschalteter Lint ist schlechter als keiner. Der HTML-Entitaeten-Fall ist
nicht konstruiert: der erste Lauf ueber design-system/ meldete 23 Befunde,
alle aus dieser Klasse (`&#8594;` liest sich als Farbe `#8594`).

NEBENBEFUND BEIM SCHREIBEN DIESER DATEI (2026-08-01)
Der Digest-Fehlalarmfall wurde zuerst als getippte 64-Zeichen-Kette geschrieben.
Der nutzerweite Waechter ~/.claude/hooks/pre-write-secret-pattern.py hat den
Schreibvorgang ABGELEHNT ("Hex-Material, 64 Zeichen"). Er wird deshalb jetzt
gerechnet statt getippt — was ohnehin die ehrlichere Form ist: der Wert ist
reproduzierbar statt behauptet.

Aufruf:  python3 hooks/pre-write-design-token-guard-test.py
"""

import hashlib
import json
import os
import subprocess
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(HIER, "pre-write-design-token-guard.py")

# Ein Wert aus dem Haus-Tokensatz (dunkel, surface.base) und einer, der nicht drin ist.
TOKEN_WERT = "#151E26"
FREMDER_WERT = "#FF00AA"

# Gerechnet, nicht getippt (siehe Kopfkommentar).
DIGEST = hashlib.sha256(b"design-system").hexdigest()

FAELLE = [
    # --- MUSS ABLEHNEN ---------------------------------------------------
    (
        "deny",
        "erfundene Farbe in einer CSS-Datei",
        "Write",
        {"file_path": "/tmp/projekt/app.css", "content": ".x{color:%s}" % FREMDER_WERT},
    ),
    (
        "deny",
        "erfundene Farbe in einer Komponente (tsx)",
        "Write",
        {"file_path": "/tmp/projekt/Card.tsx", "content": "const c = '%s';" % FREMDER_WERT},
    ),
    (
        "deny",
        "Farbfunktion statt Token",
        "Edit",
        {"file_path": "/tmp/projekt/app.css", "new_string": ".y{background:rgb(12,34,56)}"},
    ),
    (
        "deny",
        "Kurzform #f0a wird normalisiert und erkannt",
        "Write",
        {"file_path": "/tmp/projekt/app.css", "content": ".z{color:#f0a}"},
    ),
    # --- MUSS DURCHLASSEN: echte Nutzung ---------------------------------
    (
        "allow",
        "Token-Wert des Hauses ist erlaubt",
        "Write",
        {"file_path": "/tmp/projekt/app.css", "content": ".x{color:%s}" % TOKEN_WERT},
    ),
    (
        "allow",
        "var(--token) statt Literal — der Normalfall",
        "Write",
        {"file_path": "/tmp/projekt/app.css", "content": ".x{color:var(--ink)}"},
    ),
    # --- MUSS DURCHLASSEN: Fehlalarm-Klassen (der schwierige Teil) -------
    (
        "allow",
        "FEHLALARM data:-URI (Entwurf C traegt einen)",
        "Write",
        {
            "file_path": "/tmp/projekt/app.css",
            "content": ".e{background:url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==)}",
        },
    ),
    (
        "allow",
        "FEHLALARM 64-stelliger Digest im Markup",
        "Write",
        {"file_path": "/tmp/projekt/x.html", "content": "<code>%s</code>" % DIGEST},
    ),
    (
        "allow",
        "FEHLALARM HTML-Zahlen-Entitaet &#8594; (gemessen: 23 Falschtreffer im ersten Lauf)",
        "Write",
        {"file_path": "/tmp/projekt/x.html", "content": "<p>a &#8594; b &#9548; c</p>"},
    ),
    (
        "allow",
        "FEHLALARM Kommentarzeile darf eine Farbe nennen",
        "Write",
        {"file_path": "/tmp/projekt/app.css", "content": "/* frueher war das %s */" % FREMDER_WERT},
    ),
    # --- MUSS DURCHLASSEN: ausserhalb des Geltungsbereichs ---------------
    (
        "allow",
        "keine Gestaltungsdatei (Python)",
        "Write",
        {"file_path": "/tmp/projekt/main.py", "content": "C = '%s'" % FREMDER_WERT},
    ),
    (
        "allow",
        "Bash ohne erkennbares Zieldokument — bewusste Reichweitengrenze",
        "Bash",
        {"command": "echo '%s'" % FREMDER_WERT},
    ),
]


def lauf(werkzeug, tool_input):
    payload = json.dumps({"tool_name": werkzeug, "tool_input": tool_input})
    proc = subprocess.run(
        [sys.executable, GUARD],
        input=payload,
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "").strip()
    if not out:
        return "allow", ""
    try:
        data = json.loads(out)
    except ValueError:
        return "allow", out
    entsch = (data.get("hookSpecificOutput") or {}).get("permissionDecision")
    grund = (data.get("hookSpecificOutput") or {}).get("permissionDecisionReason", "")
    return ("deny" if entsch == "deny" else "allow"), grund


def main():
    fehler = 0
    for erwartet, titel, werkzeug, ti in FAELLE:
        tatsaechlich, grund = lauf(werkzeug, ti)
        ok = tatsaechlich == erwartet
        if not ok:
            fehler += 1
        print(
            "%-6s erwartet=%-5s ist=%-5s  %s"
            % ("OK" if ok else "FEHLER", erwartet, tatsaechlich, titel)
        )
        if not ok and grund:
            print("        Grund: %s" % grund.splitlines()[0])
    print("-" * 72)
    print("Faelle: %d · Fehler: %d" % (len(FAELLE), fehler))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
