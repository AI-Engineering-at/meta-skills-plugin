"""T3 — Kontrast: die Rechnung, die Hauspaare, und die Querprobe gegen die Palette."""

import json

from conftest_design import DESIGN_SYSTEM, lade

design_lib = lade("design_lib")
dc = lade("design-contrast")
calc = design_lib.load_calculator(str(DESIGN_SYSTEM))
PAARE = json.loads((DESIGN_SYSTEM / "contrast-pairs.json").read_text(encoding="utf-8"))


class TestDieRechnungSelbst:
    def test_schwarz_auf_weiss_ist_21(self):
        assert round(calc.ratio("#000000", "#FFFFFF"), 2) == 21.0

    def test_gleiche_farbe_ist_1(self):
        assert round(calc.ratio("#151E26", "#151E26"), 2) == 1.0

    def test_kanonischer_wcag_grenzfall(self):
        """#767676 auf Weiss ist der Lehrbuchfall knapp ueber 4.5:1.

        Daran ist der Rechner kalibriert. Faellt dieser Test, stimmt die Formel
        nicht mehr — und dann ist JEDE Zahl im System falsch.
        """
        assert round(calc.ratio("#FFFFFF", "#767676"), 2) == 4.54

    def test_symmetrisch(self):
        assert calc.ratio("#111111", "#EEEEEE") == calc.ratio("#EEEEEE", "#111111")


class TestHauspaare:
    def test_alle_erklaerten_paare_halten_ihre_schwelle(self):
        rows, fehler, regelpflicht = dc.evaluate(str(DESIGN_SYSTEM))
        assert fehler == [], "Paare unter ihrer Schwelle: %s" % [
            (r["theme"], r["fg"], r["bg"], r["ratio"], r["min"]) for r in fehler
        ]

    def test_es_werden_wirklich_paare_gerechnet(self):
        rows, _, _ = dc.evaluate(str(DESIGN_SYSTEM))
        gerechnet = [r for r in rows if r["kind"] != "info"]
        assert len(gerechnet) >= 60, len(gerechnet)

    def test_jedes_paar_nennt_seinen_ort(self):
        """Ein Paar ohne 'wo' ist eine Zahl ohne Aussage."""
        for p in PAARE["pairs"] + PAARE["composites"]:
            assert p.get("wo", "").strip(), p

    def test_hausreserve_unterschreitung_traegt_eine_regel(self):
        """Der danger-Grenzfall: 4.58:1 ist ueber AA, aber unter der Reserve 5.0.

        Wer darunter liegt, MUSS eine Nutzungsregel tragen — sonst meldet das
        Werkzeug Regelpflicht und die CI bricht.
        """
        rows, _, regelpflicht = dc.evaluate(str(DESIGN_SYSTEM))
        assert regelpflicht == [], (
            "unter Hausreserve, aber ohne 'regel-noetig': %s"
            % [(r["theme"], r["fg"], r["ratio"]) for r in regelpflicht]
        )

    def test_der_grenzfall_ist_ueberhaupt_noch_einer(self):
        """Gegenprobe zum Test darueber: wenn danger dunkel plotzlich ueber 5.0
        laege, waere die Regel unnoetig geworden und gehoerte entfernt."""
        rows, _, _ = dc.evaluate(str(DESIGN_SYSTEM))
        treffer = [
            r for r in rows
            if r["theme"] == "dark" and r["fg"] == "state.danger.base"
            and r["bg"] == "surface.base"
        ]
        assert treffer, "der bekannte Grenzfall fehlt in den Paaren"
        assert treffer[0]["ratio"] < PAARE["hausreserve"]["text"]
        assert treffer[0]["ratio"] >= 4.5


class TestQuerprobe:
    """Gleiche Mathematik, zwei Wertequellen.

    `tools/contrast.py` rechnet ueber die Python-Paletten, `design-contrast.py`
    ueber tokens.dtcg.json. Laufen sie auseinander, ist die Token-Datei nicht
    mehr das, was der Rechner prueft — und dann prueft niemand das Ausgelieferte.
    """

    ABBILDUNG = {
        "canvas": "surface.canvas", "surface": "surface.base",
        "raised": "surface.raised", "sunken": "surface.sunken",
        "line": "line.quiet", "line_strong": "line.strong",
        "line_control": "line.control",
        "ink": "ink.primary", "ink_dim": "ink.secondary", "ink_quiet": "ink.tertiary",
        "accent": "interactive.accent", "on_accent": "interactive.on-accent",
        "ok": "state.ok.base", "attention": "state.attention.base",
        "danger": "state.danger.base", "neutral": "state.neutral.base",
        "ok_ground": "state.ok.ground", "ok_on": "state.ok.on-ground",
        "att_ground": "state.attention.ground", "att_on": "state.attention.on-ground",
        "dan_ground": "state.danger.ground", "dan_on": "state.danger.on-ground",
        "neu_ground": "state.neutral.ground", "neu_on": "state.neutral.on-ground",
    }

    def _pruefe(self, palette, theme):
        tokens = json.loads((DESIGN_SYSTEM / "tokens.dtcg.json").read_text(encoding="utf-8"))
        flat = design_lib.flatten_tokens(tokens)
        abweichungen = []
        for schluessel, token_pfad in self.ABBILDUNG.items():
            aus_palette = palette[schluessel].upper()
            aus_token = design_lib.token_hex("color.%s.%s" % (theme, token_pfad), flat)
            if aus_palette != aus_token:
                abweichungen.append((schluessel, aus_palette, token_pfad, aus_token))
        assert abweichungen == [], (
            "%s: Palette und Token-Datei sind auseinandergelaufen: %s" % (theme, abweichungen)
        )

    def test_dunkles_thema_stimmt_ueberein(self):
        self._pruefe(calc.DARK, "dark")

    def test_helles_thema_stimmt_ueberein(self):
        self._pruefe(calc.LIGHT, "light")


class TestVollstaendigkeitDerErklaerung:
    def test_jedes_in_bauteilen_benutzte_farbpaar_ist_erklaert(self):
        """Gegenmittel gegen die Kernluecke dieses Werkzeugs.

        Gerechnet wird nur, was erklaert ist. Wer zwei Token kombiniert, ohne das
        Paar zu erklaeren, wird von der Mathematik nicht erwischt. Also wird die
        VOLLSTAENDIGKEIT der Erklaerung erzwungen: jedes Zustands-Ground-Paar,
        das ein Bauteil benutzt, muss in contrast-pairs.json stehen.
        """
        erklaert = set()
        for p in PAARE["pairs"]:
            erklaert.add((p["fg"], p["bg"]))

        for zustand in ("ok", "attention", "danger", "neutral"):
            paar = ("state.%s.on-ground" % zustand, "state.%s.ground" % zustand)
            assert paar in erklaert, (
                "Bauteile benutzen %s auf %s, das Paar ist aber nicht erklaert" % paar
            )
