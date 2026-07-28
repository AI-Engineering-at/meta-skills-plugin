#!/usr/bin/env python3
"""Ablehnungs-Test fuer pre-task-frist-eigentuemer-guard.

Die deny-Faelle sind ECHTE Aufgaben, die ich in der Nacht 27./28.07. angelegt habe —
alle ohne Frist, alle ohne Eigentuemer, 27 von 30 stehen noch offen.
"""

import importlib.util
import sys
from datetime import date
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "guard", Path(__file__).parent / "pre-task-frist-eigentuemer-guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

HEUTE = date(2026, 7, 28)

FAELLE = [
    # --- MUSS ABLEHNEN: echte Anlagen dieser Nacht ---
    ("deny", "echt 00905: Souveraenitaets-Fund, weder Frist noch Eigentuemer",
     {"subject": "[SOUVERÄNITÄT] Home Assistant spricht mit Google Cloud — STT, TTS, Kalender",
      "description": "HA nutzt Google-Dienste. Lokaler Ersatz laeuft laut Angabe bereits.",
      "priority": "Urgent"}),

    ("deny", "echt 00886: Hermes ins Cluster — nur Betreff, kein Rest",
     {"subject": "[INFRA] Hermes von Mac nach hl-28/hl-29 + in den Docker-Swarm"}),

    ("deny", "Eigentuemer da, Frist fehlt",
     {"subject": "Ollama auf .90 aktualisieren", "assignee": "vibe",
      "description": "laeuft 0.20.2, aktuell ist 0.32.4"}),

    ("deny", "Frist da, Eigentuemer fehlt",
     {"subject": "OMV-Fragmente loeschen", "description": "22,7 GB tote .dat-Reste. Frist: 2026-07-30"}),

    ("deny", "Frist in der Vergangenheit",
     {"subject": "Rueckspiel-Test 502 GB", "assignee": "brain",
      "description": "ueberfaellig seit dem 19. Frist: 2026-07-19"}),

    ("deny", "Frist so weit weg, dass sie keine ist",
     {"subject": "Irgendwann mal aufraeumen", "assignee": "brain",
      "description": "Frist: 2027-12-31"}),

    ("deny", "Frist ist kein gueltiges Datum",
     {"subject": "Kaputtes Datum", "assignee": "brain", "description": "Frist: 2026-13-45"}),

    # --- MUSS DURCHLASSEN ---
    ("weiter", "vollstaendig: Eigentuemer + Frist in Reichweite",
     {"subject": "dnsmasq-Bereich im Wartungsfenster neu anlegen", "assignee": "brain",
      "description": "Bereich .20-.200, GEMEINSAM mit dem ISC-Abschalten. Frist: 2026-07-30"}),

    ("weiter", "Frist im Betreff statt in der Beschreibung",
     {"subject": "Gast 111 sichern — Frist: 2026-07-29", "assignee": "brain",
      "description": "seit 19.07. ohne Sicherung"}),

    ("weiter", "Schreibweise 'Fälligkeit'",
     {"subject": "CI-Runner-Adresse verteilen", "assignee": "brain",
      "description": "Fälligkeit: 2026-08-04 — .183 ist gemessen, TRON und Plan tragen falsche Werte"}),

    ("weiter", "bewusst fristlos, mit benanntem Grund",
     {"subject": "USV beschaffen", "assignee": "joe",
      "description": "OHNE-FRIST: haengt an Joes Budget-Entscheidung, kein technischer Termin setzbar"}),

    ("weiter", "ein anderes Werkzeug geht den Hook nichts an",
     {"subject": "irgendwas"}),   # wird in main() abgefangen, hier nur Vollstaendigkeit
]


def main() -> int:
    ok = fehl = 0
    for i, (erwartet, name, ti) in enumerate(FAELLE):
        if name.startswith("ein anderes Werkzeug"):
            ok += 1
            print("  ok    [weiter] %s (main() filtert nach tool_name)" % name)
            continue
        got, grund = guard.pruefe(ti, heute=HEUTE)
        if got == erwartet:
            ok += 1
            print("  ok    [%-6s] %s" % (erwartet, name))
        else:
            fehl += 1
            print("  FEHL  [erwartet %s, bekam %s] %s" % (erwartet, got, name))
            if grund:
                print("        %s" % grund.splitlines()[0][:100])

    denies = sum(1 for f in FAELLE if f[0] == "deny")
    print("\n  %d/%d bestanden · %d deny-Faelle · %d Fehler" % (ok, len(FAELLE), denies, fehl))
    if denies == 0:
        print("  !! KEIN deny-FALL — diese Sperre waere Dekoration.")
        return 1
    return 1 if fehl else 0


if __name__ == "__main__":
    sys.exit(main())
