#!/usr/bin/env python3
"""pre-write-design-token-guard — kein Projekt erfindet eigene Farben.

WAS DIESER HOOK IST — UND WAS ER AUSDRUECKLICH NICHT IST
--------------------------------------------------------
Er ist die SCHNELLE RUECKMELDUNG, nicht das Gate. Das Gate ist
`scripts/design-lint.py --all` als CI-Auftrag ueber den ganzen Baum.

Der Unterschied ist nicht kosmetisch: dieser Hook sieht die NUTZLAST eines
Write/Edit/Bash, nicht die Datei danach. Ein Edit, der nur eine Zeile
verschiebt, bringt keine Farbe mit und wird durchgelassen — richtig so, aber
es heisst, er ist kein vollstaendiger Zustandspruefer. Was er prinzipiell
nicht sehen kann:

  * zur Laufzeit zusammengesetzte Farben (`'#' + h`)
  * Farben, die schon auf der Platte liegen
  * Bash mit Heredoc, nur teilweise

EINE LOGIK, ZWEI AUSLOESER
-------------------------
Die Erkennung steht in `scripts/design-lint.py::pruefe_text` und wird hier
importiert, nicht nachgebaut. Ein zweiter Regex waere eine zweite Wahrheit —
und genau daran ist die Hook-Schicht dieses Hauses schon einmal erkrankt:
fuenf Dateinamen existieren in zwei Schichten, drei davon inhaltlich
auseinandergelaufen, ohne dass ein Mechanismus es meldet.

WANN ER SCHWEIGT (und warum das kein Loch ist)
----------------------------------------------
  1. Zielpfad ist keine Gestaltungsdatei          -> exit 0
  2. Es gibt kein aufgeloestes Design-System      -> exit 0
     Kein System = keine Regel. Ehrlich, nicht heimlich: wer kein
     design-system/ hat, soll nicht von einer Regel getroffen werden, die
     er nicht lesen kann.

ABLEHNUNGS-TEST
---------------
`pre-write-design-token-guard-test.py` — Pflicht seit 2026-07-28. Eine Sperre
gilt erst als vorhanden, wenn ein Test belegt, dass sie ablehnen KANN.
Hausbeweis fuers Gegenteil: `hooks/exploration-first.py` ist registriert,
laeuft 5x auf sys.exit(0) und hat nie ein einziges deny gesprochen.
Der Test enthaelt beide Richtungen — und die Fehlalarm-Faelle (data:-URI,
Digest, HTML-Entitaet, Kommentar) sind der schwierigere Teil.
"""

import json
import os
import sys

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))

# Dateiendungen, in denen eine Farbe Gestaltung bedeutet.
GESTALTUNGSENDUNGEN = (
    ".css", ".scss", ".sass", ".less", ".html", ".htm",
    ".tsx", ".jsx", ".vue", ".svelte",
)


def _lint():
    """Laedt design-lint.py ueber den Dateinamen (Bindestrich = kein Modulname)."""
    import importlib.util

    pfad = os.path.join(PLUGIN_ROOT, "scripts", "design-lint.py")
    spec = importlib.util.spec_from_file_location("design_lint", pfad)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def deny(grund):
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": grund,
                }
            }
        )
    )
    return 0


def ziel_und_nutzlast(payload):
    """Holt (zielpfad, text) aus der Werkzeug-Eingabe. Kennt Write, Edit, Bash."""
    werkzeug = payload.get("tool_name") or ""
    ti = payload.get("tool_input") or {}
    if werkzeug == "Write":
        return ti.get("file_path", ""), ti.get("content", "") or ""
    if werkzeug == "Edit":
        return ti.get("file_path", ""), ti.get("new_string", "") or ""
    if werkzeug == "Bash":
        # Nur teilweise erkennbar — im Kopfkommentar benannt.
        return "", ti.get("command", "") or ""
    return "", ""


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except (ValueError, OSError):
        return 0

    ziel, nutzlast = ziel_und_nutzlast(payload)
    if not nutzlast:
        return 0

    # (1) Nur Gestaltungsdateien. Bash ohne erkennbares Ziel: schweigen.
    if not ziel or not ziel.lower().endswith(GESTALTUNGSENDUNGEN):
        return 0

    # (2) Kein aufgeloestes System = keine Regel.
    try:
        import design_lib

        ds_root = design_lib.find_design_system()
    except Exception:
        return 0

    # Die Token-Datei und das Paket selbst duerfen Rohwerte tragen (L0).
    if os.path.abspath(ziel).startswith(ds_root):
        return 0

    try:
        lint = _lint()
        erlaubt = lint.erlaubte_werte(ds_root)
        befunde = lint.pruefe_text(nutzlast, erlaubt, quelle=ziel)
    except Exception:
        # Ein kaputter Waechter darf keine Arbeit blockieren.
        return 0

    if not befunde:
        return 0

    zeilen = []
    for b in befunde[:6]:
        if b["art"] == "hex":
            zeilen.append("  Zeile %s: %s" % (b["zeile"], b["wert"]))
        else:
            zeilen.append("  Zeile %s: %s…) — Farbfunktion" % (b["zeile"], b["wert"]))
    mehr = "" if len(befunde) <= 6 else "\n  … und %d weitere" % (len(befunde) - 6)

    return deny(
        "Farbe ausserhalb des Design-Systems in %s:\n%s%s\n\n"
        "Das System liegt in %s und kennt %d Werte. "
        "Nimm ein Token (var(--…) bzw. den Token-Pfad) statt eines Literals.\n"
        "Ist die Abweichung gewollt, gehoert sie nach <projekt>/design/tokens.overrides.json "
        "MIT einer Zeile in DIVERGENZ.md (Klasse kann-nicht/will-nicht/darf-nicht + "
        "ueberpruefen-bis).\n"
        "Vollpruefung des Baums: python3 scripts/design-lint.py --all"
        % (ziel, "\n".join(zeilen), mehr, ds_root, len(erlaubt))
    )


if __name__ == "__main__":
    sys.exit(main())
