#!/usr/bin/env python3
"""design-divergence.py — erzwingt, dass K Entwuerfe wirklich verschieden sind.

DER TEUERSTE FEHLERFALL DES VERFAHRENS
Ohne Zwang konvergieren K Entwuerfe. Man bekommt drei Varianten desselben
Gedankens, waehlt eine und nennt das eine Entscheidung. Deshalb zwei Sperren —
eine vorher, eine nachher.

VORHER (P2), DEKLARIERT
Jeder Entwurf traegt Achsenwerte. Fuer JEDES Paar muessen sich mindestens
zwei Achsen unterscheiden. Reine Zeichenkettenrechnung, hart pruefbar.
Welche Achsen es gibt und welche Werte sie annehmen koennen, legt Fable 5
fest — dieses Werkzeug kennt nur die Rechnung, nicht die Gestaltung.

NACHHER (P4), GEMESSEN
Deklarierte Verschiedenheit, die sich nicht messen laesst, ist keine.
Gerechnet wird ueber 04-messung.json: Jaccard-Abstand der Palettenmengen,
Differenz der distinkten Schriftgroessen, Spaltenzahl, Radienmenge.

DIE EHRLICHE LUECKE — UND WARUM SIE NICHT GESCHLOSSEN WIRD
Fuer den GEMESSENEN Abstand gibt es **keinen begruendeten Schwellwert**.
Ich habe keine Datengrundlage: drei Entwuerfe eines einzigen Tages sind keine
Verteilung. Deshalb laeuft dieser Teil im **Nur-Messen-Modus** — der Abstand
wird berechnet, protokolliert und angezeigt, aber nichts bricht.
Eine heute erfundene Zahl waere genau der Platzhalter, den A33 verbietet.
Der Schwellwert wird nach den ersten drei echten Laeufen gesetzt und dann mit
Datum und Datengrundlage in skills/design-jury/references/divergenz.md
eingetragen. Bis dahin: `--messen-bricht` existiert nicht.

Die DEKLARIERTE Sperre bricht sehr wohl — sie braucht keinen Schwellwert,
nur eine Zaehlung.

Aufrufe:
  python3 scripts/design-divergence.py --rahmungen 02-rahmungen.json --ci
  python3 scripts/design-divergence.py --messung 04-messung.json
"""

import io
import json
import os
import sys

MIN_ENTWUERFE = 3
MIN_ACHSEN_ABSTAND = 2


def lade(pfad):
    with io.open(pfad, encoding="utf-8") as fh:
        return json.load(fh)


def achsen_abstand(a, b):
    """Wieviele Achsen unterscheiden sich? Nur gemeinsame Achsen zaehlen."""
    gemeinsam = set(a) & set(b)
    return sum(1 for k in gemeinsam if a[k] != b[k]), sorted(gemeinsam)


def pruefe_rahmungen(daten):
    """P2-Gate: K >= 3 und paarweiser Achsenabstand >= 2."""
    fehler = []
    entwuerfe = daten.get("entwuerfe", [])
    if len(entwuerfe) < MIN_ENTWUERFE:
        fehler.append(
            "Nur %d Entwuerfe. Mindestens %d — zwei Entwuerfe sind eine Alternative, "
            "keine Divergenz." % (len(entwuerfe), MIN_ENTWUERFE)
        )

    ids = [e.get("id") for e in entwuerfe]
    if len(set(ids)) != len(ids):
        fehler.append("doppelte Entwurfs-id: %s" % ids)

    achsen_namen = set()
    for e in entwuerfe:
        achsen_namen.update((e.get("achsen") or {}).keys())
    for e in entwuerfe:
        fehlend = achsen_namen - set((e.get("achsen") or {}).keys())
        if fehlend:
            fehler.append(
                "%s: Achsen fehlen: %s — ohne vollstaendige Matrix ist der Abstand "
                "nicht rechenbar." % (e.get("id"), ", ".join(sorted(fehlend)))
            )

    paare = []
    for i in range(len(entwuerfe)):
        for j in range(i + 1, len(entwuerfe)):
            a, b = entwuerfe[i], entwuerfe[j]
            abstand, gemeinsam = achsen_abstand(a.get("achsen") or {}, b.get("achsen") or {})
            paare.append(
                {"a": a.get("id"), "b": b.get("id"), "abstand": abstand, "achsen": gemeinsam}
            )
            if abstand < MIN_ACHSEN_ABSTAND:
                fehler.append(
                    "%s vs %s: nur %d Achse(n) verschieden (mindestens %d). "
                    "Das sind zwei Varianten eines Gedankens, keine zwei Thesen."
                    % (a.get("id"), b.get("id"), abstand, MIN_ACHSEN_ABSTAND)
                )
    return paare, fehler


def jaccard(a, b):
    a, b = set(a), set(b)
    if not a and not b:
        return 0.0
    return 1.0 - (len(a & b) / float(len(a | b)))


def messe(daten):
    """P4: gemessener Abstand. NUR-MESSEN — bricht nichts."""
    entwuerfe = daten.get("entwuerfe", [])
    schluessel = [set((e.get("sonden") or {}).keys()) for e in entwuerfe]
    symmetrisch = True
    if schluessel:
        erste = schluessel[0]
        symmetrisch = all(s == erste for s in schluessel)

    paare = []
    for i in range(len(entwuerfe)):
        for j in range(i + 1, len(entwuerfe)):
            a = entwuerfe[i].get("sonden") or {}
            b = entwuerfe[j].get("sonden") or {}
            eintrag = {"a": entwuerfe[i].get("id"), "b": entwuerfe[j].get("id")}
            if "palette" in a and "palette" in b:
                eintrag["palette_jaccard"] = round(jaccard(a["palette"], b["palette"]), 3)
            if "fontSizes" in a and "fontSizes" in b:
                eintrag["fontsizes_jaccard"] = round(jaccard(a["fontSizes"], b["fontSizes"]), 3)
                eintrag["fontsizes_anzahl_diff"] = abs(len(a["fontSizes"]) - len(b["fontSizes"]))
            if "radien" in a and "radien" in b:
                eintrag["radien_jaccard"] = round(jaccard(a["radien"], b["radien"]), 3)
            if "spalten" in a and "spalten" in b:
                eintrag["spalten_diff"] = abs(int(a["spalten"]) - int(b["spalten"]))
            paare.append(eintrag)
    return paare, symmetrisch


def main(argv):
    args = argv[1:]

    def opt(name):
        return args[args.index(name) + 1] if name in args else None

    rc = 0

    r = opt("--rahmungen")
    if r:
        daten = lade(r)
        paare, fehler = pruefe_rahmungen(daten)
        print("=== P2: deklarierte Divergenz (HARTES GATE) ===")
        for p in paare:
            print("  %s vs %s: %d Achse(n) verschieden von %d"
                  % (p["a"], p["b"], p["abstand"], len(p["achsen"])))
        if fehler:
            print("")
            for f in fehler:
                print("FEHLER: %s" % f)
        print("-" * 70)
        print("Paare: %d · Fehler: %d" % (len(paare), len(fehler)))
        if fehler and "--ci" in args:
            rc = 1

    m = opt("--messung")
    if m:
        daten = lade(m)
        paare, symmetrisch = messe(daten)
        print("")
        print("=== P4: gemessener Abstand (NUR-MESSEN, bricht nicht) ===")
        if not symmetrisch:
            print("FEHLER: die Sondenschluessel sind ueber die Entwuerfe NICHT gleich.")
            print("        Ungleiche Sonden erzeugen Unterschiede, die es nicht gibt.")
            if "--ci" in args:
                rc = 1
        for p in paare:
            teile = ["%s vs %s:" % (p["a"], p["b"])]
            for k in sorted(p):
                if k in ("a", "b"):
                    continue
                teile.append("%s=%s" % (k, p[k]))
            print("  " + "  ".join(teile))
        print("")
        print("Kein Schwellwert gesetzt — Nur-Messen-Modus (Wave 1).")
        print("Grund: drei Entwuerfe eines Tages sind keine Verteilung. Eine heute")
        print("erfundene Zahl waere ein Platzhalter im Produktivpfad (A33).")

    if not r and not m:
        sys.stderr.write("FEHLER: --rahmungen und/oder --messung angeben\n")
        return 2
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
