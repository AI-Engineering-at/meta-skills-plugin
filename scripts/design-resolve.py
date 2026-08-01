#!/usr/bin/env python3
"""design-resolve.py — Basis + Module + Projekt-Overrides -> eine flache Tokenmenge.

DIE EINE REGEL, DIE DAS PAKET ZUSAMMENHAELT
Ein Projekt uebernimmt das System NICHT per Kopie, sondern per Ableitung.
`tokens.overrides.json` enthaelt AUSSCHLIESSLICH Abweichungen. Eine Vollkopie
ist mechanisch erkennbar (jedes Basis-Token kommt darin vor) und wird
abgelehnt — sonst forkt ein Projekt das System still, und beim naechsten
Update weiss niemand mehr, was Absicht war und was Altbestand.

WARUM DAS LOCK EXISTIERT
`.design-lock.json` haelt fest, gegen WELCHEN Basis-Hash aufgeloest wurde.
Ohne diesen Bezug ist jede spaetere Migrationsaussage geraten: man sieht,
dass ein Override auf `state.alarm` zeigt, aber nicht, ob `state.alarm` damals
schon anders hiess.

WAS EIN OVERRIDE NICHT DARF
Er darf eine andere Farbe waehlen. Er darf nicht unlesbar werden. Deshalb
laeuft nach dem Aufloesen dieselbe Kontrastrechnung wie ueber der Basis;
Unterschreitungen sind harte Fehler, keine Divergenz.

Aufrufe:
  python3 scripts/design-resolve.py --overrides <projekt>/design/tokens.overrides.json \
                                    --out <projekt>/design/.design-lock.json
  python3 scripts/design-resolve.py --json
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
    resolve_alias,
)


def datei_hash(pfad):
    with open(pfad, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def wert_von(node, flat, pfad):
    """Aufgeloester Wert eines Tokens (Alias gefolgt)."""
    try:
        real_pfad, real_node = resolve_alias(pfad, flat)
    except (KeyError, ValueError):
        return None, None
    return real_node.get("$value"), (real_pfad if real_pfad != pfad else None)


def aufloesen(ds_root, overrides_pfad=None, module=None):
    basis_pfad = os.path.join(ds_root, "tokens.dtcg.json")
    basis = load_json(basis_pfad)
    flat = flatten_tokens(basis)

    module = module or []
    modul_pfade = []
    for m in module:
        p = os.path.join(ds_root, "modules", "%s.tokens.json" % m)
        if not os.path.isfile(p):
            raise DesignSystemNotFound(
                "Modul '%s' nicht gefunden: %s\n"
                "Kein stiller Ersatz — ein Modul, das es nicht gibt, gibt es nicht." % (m, p)
            )
        modul_pfade.append(p)
        flat.update(flatten_tokens(load_json(p)))

    aufgeloest = {}
    for pfad, node in flat.items():
        val, via = wert_von(node, flat, pfad)
        aufgeloest[pfad] = {
            "wert": val,
            "typ": node.get("$type"),
            "herkunft": "basis",
            "alias_auf": via,
        }

    ueberschrieben = []
    vollkopie = False
    if overrides_pfad:
        ov = load_json(overrides_pfad)
        ov_flat = flatten_tokens(ov)
        # Vollkopie-Erkennung: deckt der Override die gesamte Basis ab?
        basis_pfade = set(p for p in flat)
        if basis_pfade and basis_pfade.issubset(set(ov_flat)):
            vollkopie = True
        for pfad, node in ov_flat.items():
            val, via = wert_von(node, dict(list(flat.items()) + list(ov_flat.items())), pfad)
            aufgeloest[pfad] = {
                "wert": val,
                "typ": node.get("$type"),
                "herkunft": "override",
                "alias_auf": via,
            }
            ueberschrieben.append(pfad)

    return {
        "system": ds_root,
        "system_version": io.open(os.path.join(ds_root, "VERSION"), encoding="utf-8").read().strip(),
        "basis_sha256": datei_hash(basis_pfad),
        "module": module,
        "modul_dateien": modul_pfade,
        "overrides_datei": overrides_pfad,
        "overrides_sha256": datei_hash(overrides_pfad) if overrides_pfad else None,
        "token_gesamt": len(aufgeloest),
        "ueberschrieben": sorted(ueberschrieben),
        "vollkopie": vollkopie,
        "tokens": aufgeloest,
    }


def main(argv):
    args = argv[1:]

    def opt(name):
        return args[args.index(name) + 1] if name in args else None

    try:
        ds_root = find_design_system(opt("--system"))
    except DesignSystemNotFound as exc:
        sys.stderr.write("FEHLER: %s\n" % exc)
        return 2

    module = [m for m in (opt("--modules") or "").split(",") if m]
    overrides = opt("--overrides")
    if overrides and not os.path.isfile(overrides):
        sys.stderr.write("FEHLER: Override-Datei nicht gefunden: %s\n" % overrides)
        return 2

    try:
        lock = aufloesen(ds_root, overrides, module)
    except DesignSystemNotFound as exc:
        sys.stderr.write("FEHLER: %s\n" % exc)
        return 2

    if lock["vollkopie"]:
        sys.stderr.write(
            "FEHLER: tokens.overrides.json ist eine VOLLKOPIE der Basis.\n"
            "Overrides enthalten ausschliesslich Abweichungen. Eine Vollkopie ist ein\n"
            "stiller Fork: beim naechsten Update laesst sich nicht mehr berechnen, welcher\n"
            "Wert Absicht war und welcher nur mitkopierter Altbestand.\n"
        )
        return 1

    ziel = opt("--out")
    if ziel:
        with io.open(ziel, "w", encoding="utf-8") as fh:
            json.dump(lock, fh, indent=2, sort_keys=True)
            fh.write("\n")
        print("geschrieben: %s (%d Token, %d ueberschrieben)"
              % (ziel, lock["token_gesamt"], len(lock["ueberschrieben"])))
    elif "--json" in args:
        print(json.dumps(lock, indent=2, sort_keys=True))
    else:
        print("System:    %s (%s)" % (lock["system"], lock["system_version"]))
        print("Basis:     sha256 %s…" % lock["basis_sha256"][:16])
        print("Module:    %s" % (", ".join(module) if module else "keine"))
        print("Token:     %d" % lock["token_gesamt"])
        print("Overrides: %d" % len(lock["ueberschrieben"]))
        for p in lock["ueberschrieben"]:
            print("   %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
