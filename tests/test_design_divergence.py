"""T5 — Divergenz: die deklarierte Sperre bricht, die gemessene misst nur."""

from conftest_design import lade

dv = lade("design-divergence")


def entwurf(eid, **achsen):
    return {"id": eid, "these": "These %s" % eid, "achsen": achsen}


ACHSEN = ("farbrolle", "dichte", "modus", "zweitkodierung", "grundmetapher")


def matrix(*tripel):
    return {"entwuerfe": [entwurf(eid, **dict(zip(ACHSEN, werte)))
                          for eid, werte in tripel]}


class TestDeklarierteSperre:
    def test_drei_klar_verschiedene_bestehen(self):
        daten = matrix(
            ("A", ("semantik", "konsole", "dunkel", "form", "instrument")),
            ("B", ("unbunt", "papier", "beide", "position", "akte")),
            ("C", ("semantik", "papier", "hell", "wort", "karte")),
        )
        paare, fehler = dv.pruefe_rahmungen(daten)
        assert fehler == [], fehler
        assert len(paare) == 3

    def test_zwei_entwuerfe_sind_zu_wenig(self):
        """Zwei Entwuerfe sind eine Alternative, keine Divergenz."""
        daten = matrix(
            ("A", ("semantik", "konsole", "dunkel", "form", "instrument")),
            ("B", ("unbunt", "papier", "beide", "position", "akte")),
        )
        _, fehler = dv.pruefe_rahmungen(daten)
        assert any("Mindestens" in f for f in fehler), fehler

    def test_ein_achsenunterschied_ist_zu_wenig(self):
        """Zwei Varianten eines Gedankens, nicht zwei Thesen."""
        daten = matrix(
            ("A", ("semantik", "konsole", "dunkel", "form", "instrument")),
            ("B", ("semantik", "konsole", "dunkel", "form", "akte")),
            ("C", ("unbunt", "papier", "hell", "wort", "karte")),
        )
        _, fehler = dv.pruefe_rahmungen(daten)
        assert any("A vs B" in f for f in fehler), fehler

    def test_fehlende_achse_wird_gemeldet(self):
        daten = matrix(
            ("A", ("semantik", "konsole", "dunkel", "form", "instrument")),
            ("B", ("unbunt", "papier", "beide", "position", "akte")),
            ("C", ("semantik", "papier", "hell", "wort", "karte")),
        )
        del daten["entwuerfe"][2]["achsen"]["modus"]
        _, fehler = dv.pruefe_rahmungen(daten)
        assert any("Achsen fehlen" in f for f in fehler), fehler

    def test_doppelte_id_wird_gemeldet(self):
        daten = matrix(
            ("A", ("semantik", "konsole", "dunkel", "form", "instrument")),
            ("A", ("unbunt", "papier", "beide", "position", "akte")),
            ("C", ("semantik", "papier", "hell", "wort", "karte")),
        )
        _, fehler = dv.pruefe_rahmungen(daten)
        assert any("doppelte" in f for f in fehler), fehler

    def test_abstand_wird_richtig_gezaehlt(self):
        a, _ = dv.achsen_abstand({"x": 1, "y": 2, "z": 3}, {"x": 1, "y": 9, "z": 8})
        assert a == 2


class TestGemesseneSperre:
    def _messung(self):
        return {
            "entwuerfe": [
                {"id": "A", "sonden": {"palette": ["#111", "#222"],
                                       "fontSizes": [10, 12, 14], "radien": [2],
                                       "spalten": 3}},
                {"id": "B", "sonden": {"palette": ["#333", "#444"],
                                       "fontSizes": [11, 13], "radien": [8],
                                       "spalten": 1}},
            ]
        }

    def test_rechnet_abstaende(self):
        paare, symmetrisch = dv.messe(self._messung())
        assert symmetrisch is True
        assert paare[0]["palette_jaccard"] == 1.0
        assert paare[0]["spalten_diff"] == 2
        assert paare[0]["fontsizes_anzahl_diff"] == 1

    def test_gleiche_entwuerfe_haben_abstand_null(self):
        daten = self._messung()
        daten["entwuerfe"][1]["sonden"] = dict(daten["entwuerfe"][0]["sonden"])
        paare, _ = dv.messe(daten)
        assert paare[0]["palette_jaccard"] == 0.0

    def test_ungleiche_sonden_werden_erkannt(self):
        """Ungleiche Sonden erzeugen Unterschiede, die es nicht gibt."""
        daten = self._messung()
        del daten["entwuerfe"][1]["sonden"]["radien"]
        _, symmetrisch = dv.messe(daten)
        assert symmetrisch is False

    def test_jaccard_grundfaelle(self):
        assert dv.jaccard([], []) == 0.0
        assert dv.jaccard(["a"], ["a"]) == 0.0
        assert dv.jaccard(["a"], ["b"]) == 1.0


class TestNurMessenModus:
    def test_es_gibt_keinen_schwellwert_im_code(self):
        """Wave 1 misst nur. Eine heute erfundene Zahl waere ein Platzhalter (A33).

        Dieser Test ist bewusst eine Quelltext-Behauptung: sobald jemand einen
        Schwellwert einbaut, muss er auch diesen Test anfassen — und dabei die
        Datengrundlage eintragen.
        """
        quelle = (dv.__file__ or "")
        assert quelle
        text = open(quelle, encoding="utf-8").read()
        assert "MIN_ENTWUERFE" in text
        assert "MIN_ACHSEN_ABSTAND" in text
        for verdaechtig in ("MIN_ABSTAND_GEMESSEN", "SCHWELLWERT_GEMESSEN"):
            assert verdaechtig not in text, (
                "Es gibt jetzt einen gemessenen Schwellwert. Trage seine "
                "Datengrundlage in divergenz.md ein und passe diesen Test an."
            )

    def test_konstanten_haben_die_begruendeten_werte(self):
        assert dv.MIN_ENTWUERFE == 3
        assert dv.MIN_ACHSEN_ABSTAND == 2
