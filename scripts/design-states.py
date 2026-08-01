#!/usr/bin/env python3
"""design-states.py — Zustands-Matrix pruefen und die Markdown-Tabelle erzeugen.

DAS PROBLEM, DAS ES LOEST (gemessen, nicht vermutet)
Entwurf C erklaerte in seiner Spezifikation 7 Zustaende; im CSS existierten 5
(`grep '\\.state-[a-z]+'`). Entwurf B implementierte 6. Prosa und Umsetzung waren
auseinander, und keine Pruefung merkte es. Deshalb ist states.json die Quelle
und die Markdown-Tabelle die GENERIERTE Projektion — dieselbe Mechanik wie
Token -> CSS.

DREI ERLAUBTE ZELLWERTE, MEHR NICHT
  gezeichnet  braucht 'text'  — was genau steht da
  entfaellt   braucht 'grund' — warum es diese Flaeche kategorisch nicht gibt
  offen       ehrlich unentschieden
Ein viertes Wort ist ein Fehler. 'entfaellt' ohne Grund ist ein Fehler — sonst
waere es die bequeme Tuer, durch die jede Luecke verschwindet.

ABDECKUNG = gezeichnet / (Zellen - entfaellt);  vollstaendig <=> offen == 0

WAS ES NICHT KANN — ehrlich
Es rechnet ueber die EINGETRAGENEN Flaechen. Eine vergessene Flaeche faellt
nicht auf. Die Enumerationsregel steht in states.json geschrieben; ihre
Durchsetzung braucht je Sprache einen eigenen Zaehler und existiert nicht.

Aufrufe:
  python3 scripts/design-states.py --coverage
  python3 scripts/design-states.py --coverage --ci     # exit 1 bei Schema-Fehlern
  python3 scripts/design-states.py --markdown          # erzeugt die Tabelle
  python3 scripts/design-states.py --json
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from design_lib import (  # noqa: E402
    DesignSystemNotFound,
    find_design_system,
    load_json,
)

ERLAUBTE_WERTE = ("gezeichnet", "entfaellt", "offen")


def pruefe(spec):
    """Schema-Pruefung. Gibt eine Liste von Fehlertexten zurueck (leer = gut)."""
    fehler = []
    zustaende = spec.get("zustaende") or []
    if not zustaende:
        fehler.append("states.json: 'zustaende' fehlt oder ist leer")
        return fehler
    if len(set(zustaende)) != len(zustaende):
        fehler.append("states.json: 'zustaende' enthaelt Doppel")

    gesehen = set()
    for flaeche in spec.get("flaechen", []):
        fid = flaeche.get("id")
        if not fid:
            fehler.append("Flaeche ohne 'id'")
            continue
        if fid in gesehen:
            fehler.append("%s: doppelte Flaechen-id" % fid)
        gesehen.add(fid)
        if not flaeche.get("quelle"):
            fehler.append("%s: 'quelle' fehlt — jede Flaeche nennt, woher ihre Zellen stammen" % fid)

        zellen = flaeche.get("zellen", {})
        fehlend = [z for z in zustaende if z not in zellen]
        if fehlend:
            fehler.append("%s: Zustaende fehlen: %s" % (fid, ", ".join(fehlend)))
        fremd = [z for z in zellen if z not in zustaende]
        if fremd:
            fehler.append("%s: unbekannte Zustaende: %s" % (fid, ", ".join(sorted(fremd))))

        for zname, zelle in zellen.items():
            if zname not in zustaende:
                continue
            wert = zelle.get("wert")
            if wert not in ERLAUBTE_WERTE:
                fehler.append(
                    "%s/%s: Zellwert '%s' ist nicht erlaubt (nur %s)"
                    % (fid, zname, wert, "/".join(ERLAUBTE_WERTE))
                )
                continue
            if wert == "gezeichnet" and not (zelle.get("text") or "").strip():
                fehler.append("%s/%s: 'gezeichnet' ohne 'text'" % (fid, zname))
            if wert == "entfaellt" and not (zelle.get("grund") or "").strip():
                fehler.append(
                    "%s/%s: 'entfaellt' ohne 'grund' — ohne Grund ist es keine Entscheidung, "
                    "sondern eine Luecke" % (fid, zname)
                )
    return fehler


def abdeckung(spec):
    zustaende = spec["zustaende"]
    gezeichnet = entfaellt = offen = 0
    je_flaeche = []
    for flaeche in spec.get("flaechen", []):
        g = e = o = 0
        for z in zustaende:
            wert = flaeche.get("zellen", {}).get(z, {}).get("wert")
            if wert == "gezeichnet":
                g += 1
            elif wert == "entfaellt":
                e += 1
            else:
                o += 1
        gezeichnet += g
        entfaellt += e
        offen += o
        nenner = len(zustaende) - e
        je_flaeche.append(
            {
                "id": flaeche.get("id"),
                "gezeichnet": g,
                "entfaellt": e,
                "offen": o,
                "abdeckung": (float(g) / nenner) if nenner else 1.0,
            }
        )
    zellen = len(spec.get("flaechen", [])) * len(zustaende)
    nenner = zellen - entfaellt
    return {
        "flaechen": len(spec.get("flaechen", [])),
        "zustaende": len(zustaende),
        "zellen": zellen,
        "gezeichnet": gezeichnet,
        "entfaellt": entfaellt,
        "offen": offen,
        "abdeckung": (float(gezeichnet) / nenner) if nenner else 1.0,
        "vollstaendig": offen == 0,
        "je_flaeche": je_flaeche,
    }


def markdown(spec):
    zustaende = spec["zustaende"]
    out = []
    out.append("<!-- GENERIERT von scripts/design-states.py aus states.json. Nicht von Hand bearbeiten. -->")
    out.append("")
    out.append("| Flaeche | " + " | ".join(zustaende) + " |")
    out.append("|---" * (len(zustaende) + 1) + "|")
    zeichen = {"gezeichnet": "X", "entfaellt": "--", "offen": "?"}
    for flaeche in spec.get("flaechen", []):
        row = [flaeche.get("id", "")]
        for z in zustaende:
            wert = flaeche.get("zellen", {}).get(z, {}).get("wert", "offen")
            row.append(zeichen.get(wert, "?"))
        out.append("| " + " | ".join(row) + " |")
    out.append("")
    out.append("Legende: `X` gezeichnet · `--` entfaellt (mit Grund) · `?` offen")
    a = abdeckung(spec)
    out.append("")
    out.append(
        "Abdeckung: %d gezeichnet / %d anwendbar = %.1f %% · offen: %d · vollstaendig: %s"
        % (
            a["gezeichnet"],
            a["zellen"] - a["entfaellt"],
            a["abdeckung"] * 100,
            a["offen"],
            "ja" if a["vollstaendig"] else "nein",
        )
    )
    return "\n".join(out)


def main(argv):
    args = argv[1:]
    ds = args[args.index("--system") + 1] if "--system" in args else None
    try:
        ds_root = find_design_system(ds)
    except DesignSystemNotFound as exc:
        sys.stderr.write("FEHLER: %s\n" % exc)
        return 2

    spec = load_json(os.path.join(ds_root, "states.json"))
    fehler = pruefe(spec)

    if "--markdown" in args:
        print(markdown(spec))
        return 1 if (fehler and "--ci" in args) else 0

    a = abdeckung(spec)
    if "--json" in args:
        print(json.dumps({"abdeckung": a, "fehler": fehler}, indent=2))
    else:
        print("=== Zustands-Matrix: %s ===" % ds_root)
        print(
            "Flaechen: %d · Zustaende: %d · Zellen: %d"
            % (a["flaechen"], a["zustaende"], a["zellen"])
        )
        print(
            "gezeichnet: %d · entfaellt (mit Grund): %d · offen: %d"
            % (a["gezeichnet"], a["entfaellt"], a["offen"])
        )
        print("Abdeckung: %.1f %% der anwendbaren Zellen" % (a["abdeckung"] * 100))
        print("Vollstaendig (offen == 0): %s" % ("ja" if a["vollstaendig"] else "NEIN"))
        if a["offen"]:
            print("")
            print("OFFENE ZELLEN — ehrlich unentschieden, kein stiller Erfolg:")
            for f in spec.get("flaechen", []):
                offs = [
                    z
                    for z in spec["zustaende"]
                    if f.get("zellen", {}).get(z, {}).get("wert") == "offen"
                ]
                if offs:
                    print("   %-26s %s" % (f.get("id"), ", ".join(offs)))
        if fehler:
            print("")
            print("SCHEMA-FEHLER: %d" % len(fehler))
            for e in fehler:
                print("   %s" % e)

    if "--ci" in args and fehler:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
