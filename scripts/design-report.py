#!/usr/bin/env python3
"""design-report.py — erzeugt MANIFEST.json aus einer ZAEHLUNG, nie aus einer Behauptung.

DIE KRANKHEIT, GEGEN DIE DAS HIER GEBAUT IST — im eigenen Repo gemessen
  Testzahl laut plugin.json           346
  Testzahl laut README.md            444
  Testzahl laut CHANGELOG            646
  Testzahl laut .gitea/ci.yml        725
  Testzahl tatsaechlich              755   (python3 -m pytest -q, 2026-08-01)
und dieselbe Spreizung bei den Hooks (16 / 12 / 23 gegen tatsaechlich 3).

Jede getippte Zahl driftet. Ausnahmslos. Also wird gezaehlt.

`--check` ist der Aufrufer, ohne den jeder Generator verrottet. Hausbeweis:
SKILLS_INDEX.md traegt den Vermerk „Regenerate manually" und nennt zwei Skills,
die es nicht gibt. Ein Generator ohne Aufrufer ist so wertlos wie ein Hook ohne
Registrierung.

Aufrufe:
  python3 scripts/design-report.py            # schreibt MANIFEST.json
  python3 scripts/design-report.py --check    # exit 1, wenn committet != gerechnet
"""

import hashlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from design_lib import (  # noqa: E402
    DesignSystemNotFound,
    find_design_system,
    flatten_tokens,
    load_json,
    theme_names,
)


def sha256_datei(pfad):
    with open(pfad, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def sammle(ds_root):
    tokens_pfad = os.path.join(ds_root, "tokens.dtcg.json")
    tokens = load_json(tokens_pfad)
    flat = flatten_tokens(tokens)

    typen = {}
    for node in flat.values():
        t = node.get("$type") or "?"
        typen[t] = typen.get(t, 0) + 1

    aliasse = sorted(p for p, n in flat.items() if isinstance(n.get("$value"), str))

    states = load_json(os.path.join(ds_root, "states.json"))
    zustaende = states.get("zustaende", [])
    flaechen = states.get("flaechen", [])
    gezeichnet = entfaellt = offen = 0
    for f in flaechen:
        for z in zustaende:
            w = f.get("zellen", {}).get(z, {}).get("wert")
            if w == "gezeichnet":
                gezeichnet += 1
            elif w == "entfaellt":
                entfaellt += 1
            else:
                offen += 1
    nenner = len(flaechen) * len(zustaende) - entfaellt

    paare = load_json(os.path.join(ds_root, "contrast-pairs.json"))
    themen = paare.get("themes") or theme_names(tokens)

    komponenten = sorted(
        d for d in os.listdir(os.path.join(ds_root, "components"))
        if d.endswith(".md")
    ) if os.path.isdir(os.path.join(ds_root, "components")) else []

    dateien = {}
    for name in ("tokens.dtcg.json", "tokens.css", "showcase.html",
                 "states.json", "contrast-pairs.json"):
        p = os.path.join(ds_root, name)
        if os.path.isfile(p):
            dateien[name] = sha256_datei(p)

    return {
        "$description": (
            "GENERIERT von scripts/design-report.py. Jede Zahl ist gezaehlt, keine getippt. "
            "Aenderungen von Hand werden von `--check` in der CI rot."
        ),
        "version": io.open(os.path.join(ds_root, "VERSION"), encoding="utf-8").read().strip(),
        "token-format": "dtcg-2025.10",
        "themen": themen,
        "zaehlungen": {
            "token_gesamt": len(flat),
            "token_je_typ": dict(sorted(typen.items())),
            "aliasse": len(aliasse),
            "zustaende": len(zustaende),
            "flaechen": len(flaechen),
            "matrix_zellen": len(flaechen) * len(zustaende),
            "matrix_gezeichnet": gezeichnet,
            "matrix_entfaellt": entfaellt,
            "matrix_offen": offen,
            "matrix_abdeckung_prozent": round(100.0 * gezeichnet / nenner, 1) if nenner else 100.0,
            "kontrast_paare": len(paare.get("pairs", [])),
            "kontrast_komposite": len(paare.get("composites", [])),
            "kontrast_info": len(paare.get("info", [])),
            "kontrast_rechnungen_gesamt": (
                len(themen) * (len(paare.get("pairs", [])) + len(paare.get("composites", [])))
            ),
            "komponenten": len(komponenten),
        },
        "alias_pfade": aliasse,
        "komponenten_dateien": komponenten,
        "datei_hashes_sha256": dateien,
    }


def main(argv):
    args = argv[1:]
    ds = args[args.index("--system") + 1] if "--system" in args else None
    try:
        ds_root = find_design_system(ds)
    except DesignSystemNotFound as exc:
        sys.stderr.write("FEHLER: %s\n" % exc)
        return 2

    neu = sammle(ds_root)
    ziel = os.path.join(ds_root, "MANIFEST.json")
    text = json.dumps(neu, indent=2, sort_keys=True) + "\n"

    if "--check" in args:
        if not os.path.isfile(ziel):
            sys.stderr.write("FEHLER: %s fehlt. Lauf: python3 scripts/design-report.py\n" % ziel)
            return 1
        alt = io.open(ziel, encoding="utf-8").read()
        if alt != text:
            sys.stderr.write(
                "FEHLER: MANIFEST.json weicht von der Zaehlung ab.\n"
                "Das committete Manifest beschreibt einen anderen Stand als die Dateien.\n"
                "Genau diese Drift ist der Grund fuer dieses Werkzeug — nicht von Hand\n"
                "nachziehen, sondern erzeugen: python3 scripts/design-report.py\n"
            )
            alt_j = json.loads(alt) if alt.strip() else {}
            for schluessel, wert in neu["zaehlungen"].items():
                altwert = (alt_j.get("zaehlungen") or {}).get(schluessel)
                if altwert != wert:
                    sys.stderr.write("  %s: committet=%s gerechnet=%s\n"
                                     % (schluessel, altwert, wert))
            return 1
        print("MANIFEST.json stimmt mit der Zaehlung ueberein.")
        return 0

    with io.open(ziel, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("geschrieben: %s" % ziel)
    for schluessel, wert in neu["zaehlungen"].items():
        if not isinstance(wert, dict):
            print("   %-32s %s" % (schluessel, wert))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
