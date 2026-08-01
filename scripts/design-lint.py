#!/usr/bin/env python3
"""design-lint.py — findet Farbliterale, die nicht aus dem Tokensatz stammen.

DIE ROLLENVERTEILUNG, DIE HIER WICHTIG IST
Der Hook (hooks/pre-write-design-token-guard.py) ist die SCHNELLE RUECKMELDUNG.
Er sieht nur die Nutzlast eines Write/Edit und ist damit blind fuer alles, was
schon auf der Platte liegt. DIESES Skript ist das GATE: es liest Endzustaende
ueber den ganzen Baum und hat keine Nutzlast-Blindheit. Beide rufen dieselbe
Funktion (`pruefe_text`) auf — eine Logik, zwei Ausloeser, kein Nachbau.

DIE FEHLALARME SIND DER SCHWIERIGE TEIL, NICHT DIE TREFFER
Am Rohmaterial gemessen: Entwurf C traegt einen `data:`-URI und vier volle
64-stellige Hex-Ketten (Digests). Ein naiver Farb-Regex faellt auf beides
herein und macht den Lint unbrauchbar — und ein Lint, den man abschaltet, ist
schlechter als keiner. Deshalb werden ausgenommen:
  1. `data:`-URIs            (Bilddaten, kein Design)
  2. Hex-Ketten ab 12 Zeichen (Digests, IDs — nie eine Farbe)
  3. Kommentarzeilen         (Erklaerungen duerfen Farben nennen)
  4. Definitionszeilen der L0-Schicht (dort STEHEN die Rohwerte)
  5. Werte, die im Tokensatz vorkommen (das ist ja der Sinn)

Aufrufe:
  python3 scripts/design-lint.py --all
  python3 scripts/design-lint.py --paths a.css b.html
  python3 scripts/design-lint.py --payload -      # Text von stdin (Hook/opencode)
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from design_lib import (  # noqa: E402
    DesignSystemNotFound,
    FUNC_COLOR_RE,
    find_design_system,
    flatten_tokens,
    known_hex_values,
    load_json,
    normalize_hex,
)

# Dateiendungen, in denen eine Farbe ueberhaupt Design bedeutet.
GEPRUEFTE_ENDUNGEN = (".css", ".scss", ".sass", ".less", ".html", ".htm",
                      ".tsx", ".jsx", ".vue", ".svelte")

# Hex ab 12 Zeichen ist ein Digest/eine ID, nie eine Farbe.
LANGE_HEXKETTE = re.compile(r"\b[0-9a-fA-F]{12,}\b")
DATA_URI = re.compile(r"data:[^;,\s]*[;,][^\s\"')]*")
# HTML-Zahlen-Entitaeten: &#8594; sieht aus wie die Farbe #8594 (4-stellig = #RGBA).
# Selbst gemessen: der erste Lauf ueber design-system/ meldete 23 Befunde, ALLE aus
# dieser Klasse (&#8594; Pfeil, &#9548; Strich-Marke, &#8984; Cmd-Taste). Ohne diese
# Maske waere der Lint beim ersten echten Einsatz unbrauchbar gewesen.
HTML_ENTITAET = re.compile(r"&#x?[0-9a-fA-F]+;?")
KOMMENTAR = re.compile(r"^\s*(?://|/\*|\*|<!--|#)")
# Eine L0-Definitionszeile: --token: #RRGGBB  bzw.  "hex": "#RRGGBB"
L0_DEFINITION = re.compile(r"(--[a-zA-Z0-9-]+\s*:|\"hex\"\s*:)")

FARBE = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def _maskiere(zeile):
    """Entfernt alles, was nur AUSSIEHT wie eine Farbe."""
    zeile = DATA_URI.sub(" ", zeile)
    zeile = HTML_ENTITAET.sub(" ", zeile)
    zeile = LANGE_HEXKETTE.sub(" ", zeile)
    return zeile


def pruefe_text(text, erlaubt, quelle="<payload>", erlaube_l0=False):
    """Kern der Pruefung. Gibt eine Liste von Befunden zurueck.

    `erlaubt` ist die Menge der zulaessigen Hex-Werte (gross geschrieben).
    `erlaube_l0` laesst Definitionszeilen durch — fuer die Token-Datei selbst.
    """
    befunde = []
    for nr, zeile in enumerate(text.splitlines(), 1):
        if KOMMENTAR.match(zeile):
            continue
        if erlaube_l0 and L0_DEFINITION.search(zeile):
            continue
        sauber = _maskiere(zeile)

        for treffer in FARBE.finditer(sauber):
            norm = normalize_hex(treffer.group(0))
            if norm is None:
                continue
            if norm in erlaubt:
                continue
            befunde.append(
                {
                    "quelle": quelle,
                    "zeile": nr,
                    "wert": treffer.group(0),
                    "normalisiert": norm,
                    "art": "hex",
                    "text": zeile.strip()[:120],
                }
            )

        for treffer in FUNC_COLOR_RE.finditer(sauber):
            befunde.append(
                {
                    "quelle": quelle,
                    "zeile": nr,
                    "wert": treffer.group(0).strip(),
                    "normalisiert": None,
                    "art": "funktion",
                    "text": zeile.strip()[:120],
                }
            )
    return befunde


def erlaubte_werte(ds_root):
    tokens = load_json(os.path.join(ds_root, "tokens.dtcg.json"))
    return known_hex_values(flatten_tokens(tokens))


def sammle_dateien(wurzel):
    out = []
    for pfad, dirs, dateien in os.walk(wurzel):
        dirs[:] = [
            d
            for d in dirs
            if d not in (".git", "node_modules", "__pycache__", ".venv", "venv", "_pyvendor")
        ]
        for d in dateien:
            if d.lower().endswith(GEPRUEFTE_ENDUNGEN):
                out.append(os.path.join(pfad, d))
    return sorted(out)


def main(argv):
    args = argv[1:]
    ds = args[args.index("--system") + 1] if "--system" in args else None
    try:
        ds_root = find_design_system(ds)
    except DesignSystemNotFound as exc:
        sys.stderr.write("FEHLER: %s\n" % exc)
        return 2

    erlaubt = erlaubte_werte(ds_root)

    if "--payload" in args:
        idx = args.index("--payload") + 1
        quelle = args[idx] if idx < len(args) else "-"
        text = sys.stdin.read() if quelle == "-" else open(quelle).read()
        befunde = pruefe_text(text, erlaubt, quelle)
    elif "--paths" in args:
        pfade = [a for a in args[args.index("--paths") + 1:] if not a.startswith("--")]
        befunde = []
        for p in pfade:
            with open(p) as fh:
                befunde.extend(
                    pruefe_text(fh.read(), erlaubt, p, erlaube_l0=os.path.abspath(p).startswith(ds_root))
                )
    else:
        # --all: der ganze Baum des Pakets
        befunde = []
        for p in sammle_dateien(ds_root):
            with open(p) as fh:
                befunde.extend(pruefe_text(fh.read(), erlaubt, p, erlaube_l0=True))

    if "--json" in args:
        print(json.dumps({"erlaubte_werte": len(erlaubt), "befunde": befunde}, indent=2))
    else:
        print("=== design-lint: %d erlaubte Token-Werte ===" % len(erlaubt))
        if not befunde:
            print("Keine Farbe ausserhalb des Tokensatzes gefunden.")
        for b in befunde:
            print("%s:%d  %s  %s" % (b["quelle"], b["zeile"], b["wert"], b["text"]))
        print("-" * 70)
        print("BEFUNDE: %d" % len(befunde))

    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
