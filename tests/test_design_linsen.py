"""T7 — Linsen-Bericht: Vollstaendigkeit, Belegpflicht, und die Fable-5-Grenze.

Die Sprachregel ist der Kern: eine Linse meldet einen BEFUND, keine ANWEISUNG.
„Kontrast 3,8:1 liegt unter 4,5:1" ist erlaubt. „nimm ein helleres Rot" nicht.
"""

import re

import pytest

from conftest_design import REPO

# Anweisungsmuster an den Entwerfer. Das Fehlalarm-Risiko ist bewusst in Kauf
# genommen: ein Fehlalarm kostet eine Minute, eine durchgerutschte
# Gestaltungsanweisung bricht die Rollenzuweisung des Eigentuemers.
ANWEISUNGSMUSTER = [
    r"\bnimm\b", r"\bmach\b", r"\baendere\b", r"\bändere\b", r"\bersetze\b",
    r"\bverwende\b", r"\bbenutze\b", r"\bsetze\b(?!\s+sich)", r"\bfuege\b", r"\bfüge\b",
    r"\buse\b", r"\bshould be\b", r"\bmust be\b", r"\breplace\b", r"\bchange\b",
]
ANWEISUNG_RE = re.compile("|".join(ANWEISUNGSMUSTER), re.I)

BELEG_RE = re.compile(r"[\w./-]+\.[A-Za-z0-9]{1,5}:\d+|\d+([.,]\d+)?\s*:\s*1|`[^`]+`")


def enthaelt_anweisung(text):
    return bool(ANWEISUNG_RE.search(text))


def hat_beleg(text):
    return bool(BELEG_RE.search(text))


class TestSprachregel:
    @pytest.mark.parametrize("zelle", [
        "Kontrast 3,8:1 liegt unter der Schwelle 4,5:1",
        "`partial` ist in dieser Flaeche nicht gezeichnet",
        "drei Bedienelemente ohne zugaenglichen Namen (`unnamedButtons: 3`)",
        "die deklarierte Skala nennt 7 Stufen, gemessen wurden 16",
        "`spec.md:44` verweist auf eine Datei, die nicht existiert",
    ])
    def test_befunde_sind_erlaubt(self, zelle):
        assert not enthaelt_anweisung(zelle), zelle

    @pytest.mark.parametrize("zelle", [
        "nimm ein helleres Rot",
        "aendere die Schriftgroesse auf 14px",
        "fuege einen Teilzustand hinzu",
        "use a lighter red here",
        "the accent should be blue",
        "replace the border color",
    ])
    def test_anweisungen_werden_erkannt(self, zelle):
        assert enthaelt_anweisung(zelle), zelle


class TestBelegpflicht:
    @pytest.mark.parametrize("zelle", [
        "Kontrast 3,8:1 unter der Schwelle",
        "gemessen in `04-messung.json`",
        "`design-system/tokens.dtcg.json:12`",
    ])
    def test_belegte_wertungen(self, zelle):
        assert hat_beleg(zelle), zelle

    @pytest.mark.parametrize("zelle", [
        "wirkt unruhig",
        "gefaellt mir nicht",
        "ist zu dunkel",
    ])
    def test_geschmacksurteile_haben_keinen_beleg(self, zelle):
        assert not hat_beleg(zelle), zelle


class TestBerichtsstruktur:
    ZUSTAENDE = ["idle", "pending", "success", "empty", "partial", "failed",
                 "unavailable", "locked"]

    def _bericht(self, linsen, entwuerfe):
        return {
            "linsen": linsen,
            "entwuerfe": entwuerfe,
            "zellen": {
                "%s/%s" % (l, e): {"befund": "Kontrast 3,8:1 unter 4,5:1",
                                   "beleg": "`04-messung.json`",
                                   "wertung": -1, "gewicht": 2}
                for l in linsen for e in entwuerfe
            },
        }

    def pruefe(self, bericht):
        fehler = []
        for l in bericht["linsen"]:
            for e in bericht["entwuerfe"]:
                key = "%s/%s" % (l, e)
                zelle = bericht["zellen"].get(key)
                if not zelle:
                    fehler.append("Zelle fehlt: %s" % key)
                    continue
                if not (zelle.get("befund") or "").strip():
                    fehler.append("Befund leer: %s" % key)
                if not hat_beleg(zelle.get("beleg", "") + zelle.get("befund", "")):
                    fehler.append("Wertung ohne Beleg: %s" % key)
                if enthaelt_anweisung(zelle.get("befund", "")):
                    fehler.append("Anweisungssprache: %s" % key)
        return fehler

    def test_vollstaendiger_bericht_ist_gruen(self):
        b = self._bericht(["L1", "L2", "L3"], ["A", "B", "C"])
        assert self.pruefe(b) == []

    def test_fehlende_zelle_faellt_auf(self):
        b = self._bericht(["L1", "L2"], ["A", "B"])
        del b["zellen"]["L1/B"]
        assert any("Zelle fehlt" in f for f in self.pruefe(b))

    def test_zelle_mit_anweisung_faellt_auf(self):
        b = self._bericht(["L1"], ["A"])
        b["zellen"]["L1/A"]["befund"] = "nimm ein helleres Rot"
        assert any("Anweisungssprache" in f for f in self.pruefe(b))

    def test_zelle_ohne_beleg_faellt_auf(self):
        b = self._bericht(["L1"], ["A"])
        b["zellen"]["L1/A"] = {"befund": "wirkt unruhig", "beleg": "",
                               "wertung": -1, "gewicht": 1}
        assert any("ohne Beleg" in f for f in self.pruefe(b))


class TestDieLinsenSindDokumentiert:
    def test_alle_sieben_stehen_in_der_referenz(self):
        text = (REPO / "skills" / "design-jury" / "references" / "linsen.md").read_text(
            encoding="utf-8"
        )
        for linse in ("L1", "L2", "L3", "L4", "L5", "L6", "L7"):
            assert linse in text, linse

    def test_die_sprachregel_steht_dort_mit_beispielen(self):
        text = (REPO / "skills" / "design-jury" / "references" / "linsen.md").read_text(
            encoding="utf-8"
        )
        assert "Befund" in text and "Anweisung" in text
        assert "nimm ein helleres Rot" in text

    def test_das_muster_wird_als_adoption_ausgewiesen(self):
        """Existing-First: triad-review hat das Jury-Muster bereits."""
        text = (REPO / "skills" / "design-jury" / "references" / "linsen.md").read_text(
            encoding="utf-8"
        )
        assert "triad-review" in text
        assert (REPO / "skills" / "triad-review" / "SKILL.md").exists()
