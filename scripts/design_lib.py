#!/usr/bin/env python3
"""design_lib.py — gemeinsamer Unterbau der design-*-Werkzeuge.

WARUM ES DIESE DATEI GIBT
Sechs Werkzeuge (design-contrast, design-lint, design-states, design-report,
design-resolve, design-check) brauchen dieselben drei Dinge: das Paket finden,
die Token-Datei flach machen, einen Token-Pfad auf einen Hex-Wert aufloesen.
Dreimal getippt waere dreimal driftbar — genau die Krankheit, die im Plugin
gemessen ist (fuenf verschiedene Testzahlen in Prosa).

WOHER DIE MATHEMATIK KOMMT — UND WOHER DIE WERTE
Die Kontrastformel wird NICHT hier nachgebaut. Sie wird aus
design-system/tools/contrast.py importiert, dem Rechner, den Fable 5 am
kanonischen WCAG-Grenzfall #FFFFFF/#767676 -> 4.54:1 kalibriert hat.
Die WERTE dagegen kommen aus tokens.dtcg.json, nicht aus den Python-Paletten
desselben Moduls. Das ist Absicht: gleiche Mathematik, zwei Wertequellen.
Laufen Token-Datei und Palette auseinander, faellt es auf
(tests/test_design_contrast.py::TestQuerprobe) — statt still weiterzurechnen.

PYTHON 3.9
hooks.json ruft mit blankem `python3`; auf dem Mac ist das 3.9.6, und die
Gitea-CI prueft mit `vermin --target=3.9`. Deshalb: keine PEP-604-Unions,
kein match, kein datetime.UTC.
"""

import json
import os
import re
import sys

# --------------------------------------------------------------- Paketsuche

ENV_VAR = "AIE_DESIGN_SYSTEM"
PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class DesignSystemNotFound(Exception):
    """Das Paket wurde nicht gefunden.

    Bewusst eine Ausnahme und kein eingebauter Vorgabe-Satz: ein stiller
    Fallback auf erfundene Token waere ein Mock im Produktivpfad (A33).
    """


def candidate_roots():
    """Suchreihenfolge, in genau dieser Reihenfolge."""
    out = []
    env = os.environ.get(ENV_VAR)
    if env:
        out.append(("$" + ENV_VAR, env))
    out.append(("<plugin-root>/design-system", os.path.join(PLUGIN_ROOT, "design-system")))
    out.append(("./design-system", os.path.join(os.getcwd(), "design-system")))
    return out


def find_design_system(explicit=None):
    """Findet das Paket oder scheitert mit einer Liste der geprueften Orte."""
    if explicit:
        if os.path.isfile(os.path.join(explicit, "tokens.dtcg.json")):
            return os.path.abspath(explicit)
        raise DesignSystemNotFound(
            "kein tokens.dtcg.json unter dem angegebenen Pfad: %s" % explicit
        )
    geprueft = []
    for label, path in candidate_roots():
        geprueft.append("%s -> %s" % (label, path))
        if os.path.isfile(os.path.join(path, "tokens.dtcg.json")):
            return os.path.abspath(path)
    raise DesignSystemNotFound(
        "design-system/ nicht gefunden. Geprueft in dieser Reihenfolge:\n  "
        + "\n  ".join(geprueft)
        + "\nKein eingebauter Vorgabe-Satz: ein System, das nicht da ist, ist nicht da."
    )


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------ Token-Zugriff


def flatten_tokens(tree, prefix=""):
    """DTCG-Baum -> {punkt.pfad: knoten}. Nur Knoten mit $value sind Token."""
    out = {}
    if not isinstance(tree, dict):
        return out
    if "$value" in tree:
        out[prefix] = tree
        return out
    for key, val in tree.items():
        if key.startswith("$"):
            continue
        sub = "%s.%s" % (prefix, key) if prefix else key
        out.update(flatten_tokens(val, sub))
    return out


ALIAS_RE = re.compile(r"^\{([^}]+)\}$")


def resolve_alias(path, flat, _seen=None):
    """Folgt DTCG-Aliassen ({a.b.c}) bis zum Wert. Erkennt Zyklen."""
    if _seen is None:
        _seen = set()
    if path in _seen:
        raise ValueError("Alias-Zyklus bei %s" % path)
    _seen.add(path)
    node = flat.get(path)
    if node is None:
        raise KeyError("unbekannter Token-Pfad: %s" % path)
    val = node.get("$value")
    if isinstance(val, str):
        m = ALIAS_RE.match(val.strip())
        if m:
            return resolve_alias(m.group(1), flat, _seen)
    return path, node


def token_hex(path, flat):
    """Hex-Wert eines Farb-Tokens, Aliasse aufgeloest."""
    real_path, node = resolve_alias(path, flat)
    val = node.get("$value")
    if isinstance(val, dict) and "hex" in val:
        return val["hex"].upper()
    raise ValueError("Token %s (-> %s) hat keinen hex-Wert" % (path, real_path))


def theme_names(tokens):
    """Die Theme-Sets unter color.* — gemessen, nicht angenommen."""
    return sorted(k for k in tokens.get("color", {}) if not k.startswith("$"))


# ------------------------------------------------- Rechner aus dem Paket


def load_calculator(ds_root):
    """Importiert contrast.py AUS DEM PAKET.

    Nicht nachgebaut: eine zweite Formel waere eine zweite Wahrheit. Das Modul
    liegt in design-system/tools/ und ist der von Fable 5 kalibrierte Rechner.
    """
    tools = os.path.join(ds_root, "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import contrast  # noqa: E402  (Pfad wird zur Laufzeit gesetzt)

    return contrast


# -------------------------------------------------------- Hex-Erkennung


HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
FUNC_COLOR_RE = re.compile(r"\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\s*\(")


def normalize_hex(value):
    """#abc -> #AABBCC. Gibt None zurueck, wenn es keine Farbe ist."""
    v = value.strip()
    if not v.startswith("#"):
        return None
    body = v[1:]
    if len(body) in (3, 4):
        body = "".join(ch * 2 for ch in body)
    if len(body) == 8:
        body = body[:6]
    if len(body) != 6:
        return None
    try:
        int(body, 16)
    except ValueError:
        return None
    return "#" + body.upper()


def known_hex_values(flat):
    """Alle Hex-Werte des Systems, gross geschrieben — der erlaubte Vorrat."""
    out = set()
    for path, node in flat.items():
        val = node.get("$value")
        if isinstance(val, dict) and "hex" in val:
            out.add(val["hex"].upper())
    return out
