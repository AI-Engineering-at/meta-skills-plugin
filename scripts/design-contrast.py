#!/usr/bin/env python3
"""design-contrast.py — rechnet jedes erklaerte Farbpaar aus der Token-Datei nach.

WAS DIESES WERKZEUG IST — UND WAS NICHT
Es ist ein Gate: `--ci` endet mit 1, sobald ein Paar seine Schwelle reisst.
Es ist KEIN vollstaendiger Kontrastpruefer. Es rechnet ausschliesslich die
Paare, die in contrast-pairs.json ERKLAERT sind. Wer zwei Token kombiniert,
ohne das Paar zu erklaeren, wird von dieser Mathematik nicht erwischt — nur
von einer Browser-Sonde, die berechnete Stile liest.
Gegenmittel gegen genau diese Luecke: tests/test_design_contrast.py prueft,
dass jedes in components/ benutzte Paar auch erklaert ist. Die Vollstaendigkeit
der Erklaerung wird erzwungen, nicht nur die Rechnung.

WARUM WCAG 2.1 UND NICHT APCA
APCA modelliert dunkle Oberflaechen besser, ist aber nicht normativ. Deshalb:
WCAG 2.1 wird gerechnet und bricht. Ein APCA-Wert wird NICHT mitgeschrieben —
ARCHITEKTUR.md §9.3 schlug das vor, aber eine Zahl ohne Rechner waere erfunden.
Ehrlich offen statt scheinpraezise.

Aufrufe:
  python3 scripts/design-contrast.py            # Bericht, exit 0
  python3 scripts/design-contrast.py --ci       # Gate, exit 1 bei Verstoss
  python3 scripts/design-contrast.py --json     # maschinenlesbar
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from design_lib import (  # noqa: E402
    DesignSystemNotFound,
    find_design_system,
    flatten_tokens,
    load_calculator,
    load_json,
    theme_names,
    token_hex,
)


def _pair_paths(theme, ref):
    """'ink.primary' -> 'color.<theme>.ink.primary'."""
    return "color.%s.%s" % (theme, ref)


def evaluate(ds_root):
    """Rechnet alle erklaerten Paare. Gibt (zeilen, fehler, regelpflicht) zurueck."""
    tokens = load_json(os.path.join(ds_root, "tokens.dtcg.json"))
    spec = load_json(os.path.join(ds_root, "contrast-pairs.json"))
    calc = load_calculator(ds_root)
    flat = flatten_tokens(tokens)

    themes = spec.get("themes") or theme_names(tokens)
    reserve = float(spec.get("hausreserve", {}).get("text", 0) or 0)

    rows = []
    fehler = []
    regelpflicht = []

    for theme in themes:
        for p in spec.get("pairs", []):
            fg_path = _pair_paths(theme, p["fg"])
            bg_path = _pair_paths(theme, p["bg"])
            fg = token_hex(fg_path, flat)
            bg = token_hex(bg_path, flat)
            r = calc.ratio(fg, bg)
            need = float(p["min"])
            ok = r >= need
            row = {
                "theme": theme,
                "fg": p["fg"],
                "bg": p["bg"],
                "fg_hex": fg,
                "bg_hex": bg,
                "ratio": round(r, 2),
                "min": need,
                "sc": p.get("sc", ""),
                "wo": p.get("wo", ""),
                "ok": ok,
                "kind": "pair",
            }
            rows.append(row)
            if not ok:
                fehler.append(row)
            # Hausreserve gilt nur fuer Text (SC 1.4.3), nicht fuer Grafik.
            elif p.get("sc") == "1.4.3" and reserve and r < reserve:
                row["unter_hausreserve"] = True
                if not p.get("regel-noetig"):
                    regelpflicht.append(row)

        for c in spec.get("composites", []):
            over = token_hex(_pair_paths(theme, c["quelle"]), flat)
            under = token_hex(_pair_paths(theme, c["under"]), flat)
            eff = calc.composite(over, float(c["alpha"]), under)
            fg = token_hex(_pair_paths(theme, c["fg"]), flat)
            r = calc.ratio(fg, eff)
            need = float(c["min"])
            ok = r >= need
            row = {
                "theme": theme,
                "fg": c["fg"],
                "bg": "%s @%d%% ueber %s = %s"
                % (c["quelle"], round(float(c["alpha"]) * 100), c["under"], eff),
                "fg_hex": fg,
                "bg_hex": eff,
                "ratio": round(r, 2),
                "min": need,
                "sc": c.get("sc", ""),
                "wo": c.get("wo", ""),
                "ok": ok,
                "kind": "composite",
            }
            rows.append(row)
            if not ok:
                fehler.append(row)

        for i in spec.get("info", []):
            fg = token_hex(_pair_paths(theme, i["fg"]), flat)
            bg = token_hex(_pair_paths(theme, i["bg"]), flat)
            rows.append(
                {
                    "theme": theme,
                    "fg": i["fg"],
                    "bg": i["bg"],
                    "fg_hex": fg,
                    "bg_hex": bg,
                    "ratio": round(calc.ratio(fg, bg), 2),
                    "min": 0.0,
                    "sc": "",
                    "wo": i.get("wo", ""),
                    "ok": True,
                    "kind": "info",
                }
            )

    return rows, fehler, regelpflicht


def format_text(rows, fehler, regelpflicht):
    out = []
    current = None
    for r in rows:
        if r["theme"] != current:
            current = r["theme"]
            out.append("=" * 78)
            out.append("THEMA: %s" % current)
            out.append("=" * 78)
        if r["kind"] == "info":
            mark = "[info]"
        elif r["ok"]:
            mark = "PASS  "
        else:
            mark = "**FAIL**"
        extra = "  << unter Hausreserve" if r.get("unter_hausreserve") else ""
        out.append(
            "%s %-26s auf %-26s %6.2f:1 (>=%.1f) %s%s"
            % (mark, r["fg"], r["bg"], r["ratio"], r["min"], r["sc"], extra)
        )
    out.append("-" * 78)
    out.append("Paare gerechnet: %d" % len([r for r in rows if r["kind"] != "info"]))
    out.append("FAILS: %d" % len(fehler))
    if regelpflicht:
        out.append(
            "REGELPFLICHT (ueber WCAG, unter Hausreserve, aber ohne 'regel-noetig'): %d"
            % len(regelpflicht)
        )
        for r in regelpflicht:
            out.append("   %s: %s auf %s = %.2f" % (r["theme"], r["fg"], r["bg"], r["ratio"]))
    return "\n".join(out)


def main(argv):
    args = argv[1:]
    ds = None
    if "--system" in args:
        ds = args[args.index("--system") + 1]
    try:
        ds_root = find_design_system(ds)
    except DesignSystemNotFound as exc:
        sys.stderr.write("FEHLER: %s\n" % exc)
        return 2

    rows, fehler, regelpflicht = evaluate(ds_root)

    if "--json" in args:
        print(
            json.dumps(
                {
                    "system": ds_root,
                    "rows": rows,
                    "fails": len(fehler),
                    "regelpflicht": len(regelpflicht),
                },
                indent=2,
            )
        )
    else:
        print(format_text(rows, fehler, regelpflicht))

    if "--ci" in args and (fehler or regelpflicht):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
