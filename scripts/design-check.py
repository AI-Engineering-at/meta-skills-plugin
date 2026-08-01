#!/usr/bin/env python3
"""design-check.py — projektseitig: haengt dieses Projekt noch am aktuellen System?

DIE ZWEI ACHSEN, DIE HIER GEPRUEFT WERDEN
  SemVer         der Vertrag  (Token da? Name gleich? Bedeutung gleich?)
  visual-epoch   das Aussehen (Farbwerte)
Eine Farbwertaenderung bricht keinen Vertrag, aber jedes Screenshot. Wer nur
SemVer fuehrt, muss sich zwischen zwei Luegen entscheiden.

STUFEN, BEWUSST UNGLEICH HART
  SessionStart-Hinweis   blockt NIE
  --ci                   warnt bei MINOR, BRICHT bei MAJOR ohne Migrationsdatei
  --migrate              klassifiziert jeden Override, schreibt aber NIE selbst

WARUM DAS WERKZEUG NIE SELBST SCHREIBT
`DIVERGENZ.md` ist die Begruendung eines Menschen. Ein Werkzeug, das sie
fortschreibt, erzeugt Begruendungen, die niemand gedacht hat — und das ist
schlimmer als eine fehlende.

ABGELAUFENE DIVERGENZEN WARNEN, SIE BRECHEN NICHT
Eine abgelaufene Begruendung ist ein Gespraechsanlass, kein Baufehler.

Aufrufe:
  python3 scripts/design-check.py --projekt <pfad>
  python3 scripts/design-check.py --projekt <pfad> --ci
  python3 scripts/design-check.py --projekt <pfad> --migrate --to 2.0.0
"""

import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from design_lib import (  # noqa: E402
    DesignSystemNotFound,
    find_design_system,
    flatten_tokens,
    load_json,
)

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def semver(text):
    m = SEMVER.match((text or "").strip())
    if not m:
        return None
    return tuple(int(x) for x in m.groups())


def stufe(alt, neu):
    """MAJOR / MINOR / PATCH / gleich / rueckwaerts"""
    if alt is None or neu is None:
        return "unbekannt"
    if neu == alt:
        return "gleich"
    if neu < alt:
        return "rueckwaerts"
    if neu[0] != alt[0]:
        return "MAJOR"
    if neu[1] != alt[1]:
        return "MINOR"
    return "PATCH"


def lies_divergenz(pfad):
    """Liest die Markdown-Tabelle. Spalten: Token-Pfad | Klasse | Grund | bis | Wer."""
    if not os.path.isfile(pfad):
        return []
    zeilen = []
    for roh in io.open(pfad, encoding="utf-8"):
        if not roh.strip().startswith("|"):
            continue
        felder = [f.strip() for f in roh.strip().strip("|").split("|")]
        if len(felder) < 4:
            continue
        if felder[0].lower().startswith(("token", "---", ":--")):
            continue
        if set(felder[0]) <= set("-: "):
            continue
        zeilen.append(
            {
                "token": felder[0].strip("`"),
                "klasse": felder[1],
                "grund": felder[2],
                "bis": felder[3],
                "wer": felder[4] if len(felder) > 4 else "",
            }
        )
    return zeilen


KLASSEN = ("kann-nicht", "will-nicht", "darf-nicht")


def main(argv):
    args = argv[1:]

    def opt(name, standard=None):
        return args[args.index(name) + 1] if name in args else standard

    projekt = opt("--projekt")
    if not projekt:
        sys.stderr.write("FEHLER: --projekt <pfad> fehlt\n")
        return 2

    try:
        ds_root = find_design_system(opt("--system"))
    except DesignSystemNotFound as exc:
        sys.stderr.write("FEHLER: %s\n" % exc)
        return 2

    system_version = io.open(os.path.join(ds_root, "VERSION"), encoding="utf-8").read().strip()
    d = os.path.join(projekt, "design")
    lock_pfad = os.path.join(d, ".design-lock.json")
    div_pfad = os.path.join(d, "DIVERGENZ.md")
    ov_pfad = os.path.join(d, "tokens.overrides.json")

    if not os.path.isdir(d):
        print("Kein design/-Verzeichnis in %s — dieses Projekt leitet nichts ab." % projekt)
        return 0

    warnungen = []
    fehler = []

    lock = load_json(lock_pfad) if os.path.isfile(lock_pfad) else None
    if lock is None:
        warnungen.append(
            ".design-lock.json fehlt. Ohne Lock ist jede Migrationsaussage geraten — "
            "es steht nirgends, gegen welchen Basis-Stand aufgeloest wurde. "
            "Lauf: python3 scripts/design-resolve.py --overrides %s --out %s" % (ov_pfad, lock_pfad)
        )
        projekt_version = None
    else:
        projekt_version = lock.get("system_version")

    alt = semver(projekt_version)
    neu = semver(system_version)
    st = stufe(alt, neu)

    print("System:  %s" % system_version)
    print("Projekt: %s" % (projekt_version or "unbekannt"))
    print("Stufe:   %s" % st)

    if st == "MAJOR":
        ziel = opt("--to", system_version)
        mig = os.path.join(ds_root, "migrations", "%s-zu-%s.md"
                           % (projekt_version, ziel))
        if os.path.isfile(mig):
            print("Migration vorhanden: %s" % mig)
        else:
            fehler.append(
                "MAJOR-Sprung %s -> %s ohne Migrationsdatei. Erwartet: %s"
                % (projekt_version, system_version, mig)
            )
    elif st == "MINOR":
        warnungen.append(
            "MINOR-Sprung %s -> %s. Neue Token koennen dazugekommen sein; "
            "nichts bricht." % (projekt_version, system_version)
        )
    elif st == "rueckwaerts":
        warnungen.append(
            "Das Projekt haengt an einer NEUEREN Version (%s) als das System (%s)."
            % (projekt_version, system_version)
        )

    # --- Divergenzen ----------------------------------------------------
    div = lies_divergenz(div_pfad)
    overrides = []
    if os.path.isfile(ov_pfad):
        overrides = sorted(flatten_tokens(load_json(ov_pfad)))

    erklaert = set(z["token"] for z in div)
    unerklaert = [o for o in overrides if o not in erklaert]
    if unerklaert:
        fehler.append(
            "Override ohne DIVERGENZ-Zeile: %s. Jede Abweichung braucht Klasse, "
            "Grund und ein Ablaufdatum." % ", ".join(unerklaert)
        )
    waisen = [z["token"] for z in div if z["token"] not in overrides]
    if waisen:
        warnungen.append(
            "DIVERGENZ-Zeile ohne Override (Waise): %s — womoeglich ist die "
            "Abweichung schon zurueckgebaut." % ", ".join(waisen)
        )

    heute = opt("--heute")  # testbar machen, statt die Uhr zu befragen
    if heute is None:
        import datetime

        heute = datetime.date.today().isoformat()

    for z in div:
        if z["klasse"] not in KLASSEN:
            fehler.append(
                "%s: Klasse '%s' ist nicht erlaubt (nur %s)"
                % (z["token"], z["klasse"], "/".join(KLASSEN))
            )
        if not SEMVER and not z["bis"]:
            pass
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", z["bis"] or ""):
            fehler.append(
                "%s: 'ueberpruefen-bis' fehlt oder ist kein Datum (JJJJ-MM-TT). "
                "Ohne Ablauf wird aus einer Abweichung stillschweigend Dauerzustand."
                % z["token"]
            )
        elif z["bis"] < heute:
            warnungen.append(
                "%s: Divergenz-Begruendung ist am %s abgelaufen (heute %s). "
                "Gespraechsanlass, kein Baufehler." % (z["token"], z["bis"], heute)
            )

    # --- Migrations-Klassifikation --------------------------------------
    if "--migrate" in args:
        basis = flatten_tokens(load_json(os.path.join(ds_root, "tokens.dtcg.json")))
        print("")
        print("=== Migrations-Klassifikation je Override ===")
        if not overrides:
            print("(keine Overrides)")
        for o in overrides:
            if o in basis:
                print("  UEBERNOMMEN      %s — Token existiert weiter" % o)
            else:
                print("  HARTER KONFLIKT  %s — Token in der Basis nicht mehr vorhanden" % o)
        print("")
        print("Hinweis: dieses Werkzeug schreibt NICHT in DIVERGENZ.md. Es schlaegt vor,")
        print("ein Mensch entscheidet. Der Fall 'dein Override ist womoeglich ueberfluessig'")
        print("braucht einen Vergleich zweier Basis-Staende und ist noch nicht gebaut")
        print("(siehe design-system/STATUS.md).")

    print("")
    for w in warnungen:
        print("WARNUNG: %s" % w)
    for f in fehler:
        print("FEHLER:  %s" % f)
    print("-" * 70)
    print("Warnungen: %d · Fehler: %d" % (len(warnungen), len(fehler)))

    if "--ci" in args and fehler:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
