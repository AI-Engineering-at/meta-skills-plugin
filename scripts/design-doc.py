#!/usr/bin/env python3
"""design-doc.py — prueft ein Design-Dokument gegen das Slug-Schema.

DER TEST, DER ZAEHLT
Das erste Dokument, das dieses Werkzeug bestehen muss, ist das eigene:
`design-system/DESIGN-SYSTEM.md`. Ein Schema, an dem sein Referenzdokument
scheitert, ist kein Schema, sondern ein Wunsch.

WAS ES PRUEFT
  * alle Pflicht-Slugs des Profils sind da (Slugs, nicht Nummern)
  * Frontmatter vollstaendig
  * `beleg-grundlage` enthaelt mindestens eine Fundstelle datei.ext:zeile
  * `prototyp-messung` nennt mindestens einen Fehler, den erst die Messung fand
  * `bewusste-auslassungen` klassifiziert jede Auslassung
  * keine unbefuellten Vorlagen-Stellen (<…>) mehr

WAS ES NICHT PRUEFEN KANN — ehrlich
Ob eine Begruendung eine Begruendung ist. `weil` besteht jeden Lint. Und ob eine
Farbe bedeutet, was ihre Beschreibung sagt, liest keine Maschine.

Aufrufe:
  python3 scripts/design-doc.py --check <datei> [--profil haus|produkt]
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
    load_json,
)

SLUG_RE = re.compile(r"^##\s+([a-z0-9][a-z0-9-]*)\s*$", re.M)
FUNDSTELLE_RE = re.compile(r"[\w./-]+\.[A-Za-z0-9]{1,5}:\d+")
# Unbefuellte Vorlagenstellen sind Guillemets, KEINE spitzen Klammern.
# Grund, selbst gemessen: der erste Entwurf dieses Pruefers benutzte <…> und meldete
# an DESIGN-SYSTEM.md acht Fehler — alle falsch: <button>, <html>, <head>, <title>,
# <style> waren echte Prosa ueber HTML. Ein Marker, der mit dem Gegenstand kollidiert,
# ist der falsche Marker. Guillemets kommen in Auszeichnungssprache nicht vor.
PLATZHALTER_RE = re.compile(u"«[^»\n]{1,200}»")
AUSLASSUNGS_KLASSEN = ("kann-nicht", "will-nicht", "darf-nicht")


def frontmatter(text):
    """Der Kopf ist ein ```yaml-Block direkt nach der Ueberschrift."""
    m = re.search(r"```ya?ml\s*\n(.*?)```", text, re.S)
    if not m:
        return {}
    out = {}
    for zeile in m.group(1).splitlines():
        zeile = zeile.split("#", 1)[0].rstrip()
        if ":" not in zeile or zeile.startswith(" "):
            continue
        k, v = zeile.split(":", 1)
        out[k.strip()] = v.strip()
    return out


def abschnitte(text):
    """{slug: koerpertext}"""
    treffer = list(SLUG_RE.finditer(text))
    out = {}
    for i, m in enumerate(treffer):
        ende = treffer[i + 1].start() if i + 1 < len(treffer) else len(text)
        out[m.group(1)] = text[m.end():ende]
    return out


def pflicht_slugs(schema, profil):
    p = schema["profile"][profil]
    slugs = []
    if "erbt" in p:
        slugs.extend(schema["profile"][p["erbt"]]["pflicht"])
    slugs.extend(p.get("pflicht", []))
    slugs.extend(p.get("zusaetzlich-pflicht", []))
    for weg in p.get("entfaellt", []):
        slugs = [s for s in slugs if s != weg]
    # Reihenfolge stabil, Doppel raus
    gesehen = set()
    out = []
    for s in slugs:
        if s not in gesehen:
            gesehen.add(s)
            out.append(s)
    return out


def pruefe(text, schema, profil):
    fehler = []
    warnungen = []

    fm = frontmatter(text)
    for feld in schema["frontmatter"]["pflicht"]:
        if not fm.get(feld):
            fehler.append("Frontmatter: Pflichtfeld '%s' fehlt" % feld)

    hat = abschnitte(text)
    for slug in pflicht_slugs(schema, profil):
        if slug not in hat:
            fehler.append("Pflicht-Slug fehlt: %s" % slug)

    # beleg-grundlage braucht echte Fundstellen
    beleg = hat.get("beleg-grundlage", "")
    if beleg and not FUNDSTELLE_RE.search(beleg):
        fehler.append(
            "beleg-grundlage enthaelt keine Fundstelle der Form datei.ext:zeile. "
            "Gemessen: der Entwurf ohne solche Zitate wurde abgeschlagen bewertet."
        )

    # prototyp-messung braucht einen gefundenen Fehler
    mess = hat.get("prototyp-messung", "")
    if mess and not re.search(r"fehler|abweichung|korrigiert|behoben", mess, re.I):
        fehler.append(
            "prototyp-messung nennt keinen Fehler, den erst die Messung fand. "
            "Ein Dokument ohne solchen Eintrag hat entweder nicht gemessen oder verschweigt."
        )

    # Auslassungen brauchen Klassen
    ausl = hat.get("bewusste-auslassungen", "")
    if ausl:
        zeilen = [z for z in ausl.splitlines() if z.strip().startswith("|")]
        inhalt = [
            z for z in zeilen
            if not re.match(r"^\|[\s:|-]*\|?\s*$", z) and "Auslassung" not in z
        ]
        for z in inhalt:
            if not any(k in z for k in AUSLASSUNGS_KLASSEN):
                warnungen.append(
                    "bewusste-auslassungen: Zeile ohne Klasse (%s): %s"
                    % ("/".join(AUSLASSUNGS_KLASSEN), z.strip()[:70])
                )

    # Unbefuellte Vorlagenstellen
    offene = PLATZHALTER_RE.findall(text)
    if offene:
        fehler.append(
            "%d unbefuellte Vorlagen-Stelle(n), z. B. %s — ein Dokument, das die Vorlage "
            "noch traegt, ist nicht fertig." % (len(offene), offene[0][:50])
        )

    return fehler, warnungen


def main(argv):
    args = argv[1:]
    if "--check" not in args:
        sys.stderr.write("FEHLER: --check <datei> angeben\n")
        return 2
    datei = args[args.index("--check") + 1]
    profil = args[args.index("--profil") + 1] if "--profil" in args else "haus"

    try:
        ds_root = find_design_system(args[args.index("--system") + 1] if "--system" in args else None)
    except DesignSystemNotFound as exc:
        sys.stderr.write("FEHLER: %s\n" % exc)
        return 2

    schema = load_json(os.path.join(ds_root, "schema", "document-schema.json"))
    if profil not in schema["profile"]:
        sys.stderr.write("FEHLER: unbekanntes Profil '%s' (bekannt: %s)\n"
                         % (profil, ", ".join(schema["profile"])))
        return 2

    text = io.open(datei, encoding="utf-8").read()
    fehler, warnungen = pruefe(text, schema, profil)

    print("=== %s (Profil: %s) ===" % (datei, profil))
    print("Pflicht-Slugs: %d · gefunden: %d"
          % (len(pflicht_slugs(schema, profil)), len(abschnitte(text))))
    for w in warnungen:
        print("WARNUNG: %s" % w)
    for f in fehler:
        print("FEHLER:  %s" % f)
    print("-" * 70)
    print("Fehler: %d · Warnungen: %d" % (len(fehler), len(warnungen)))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
