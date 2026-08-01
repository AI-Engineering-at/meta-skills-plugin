"""T4 — Zustands-Matrix: Schema, Zellwerte, Abdeckungsrechnung."""

import json

from conftest_design import DESIGN_SYSTEM, lade

ds = lade("design-states")
SPEC = json.loads((DESIGN_SYSTEM / "states.json").read_text(encoding="utf-8"))

ERWARTETE_ZUSTAENDE = [
    "idle", "pending", "success", "empty", "partial", "failed", "unavailable", "locked",
]


class TestVokabular:
    def test_acht_zustaende_in_fester_reihenfolge(self):
        assert SPEC["zustaende"] == ERWARTETE_ZUSTAENDE

    def test_sechs_stammen_aus_dem_bestands_skill(self):
        """Existing-First: kein zweites Zustandsvokabular erfinden."""
        bestand = ["idle", "pending", "success", "empty", "partial", "failed"]
        assert SPEC["zustaende"][:6] == bestand
        assert SPEC["vokabular"]["ergaenzt"] == ["unavailable", "locked"]

    def test_die_drei_leeren_sind_getrennt(self):
        """empty, unavailable und locked sind drei verschiedene Wahrheiten."""
        for z in ("empty", "unavailable", "locked"):
            assert z in SPEC["zustaende"]


class TestSchema:
    def test_das_haus_system_besteht_sein_eigenes_schema(self):
        assert ds.pruefe(SPEC) == []

    def test_jede_flaeche_nennt_ihre_quelle(self):
        ohne = [f["id"] for f in SPEC["flaechen"] if not f.get("quelle")]
        assert ohne == []

    def test_nur_drei_zellwerte_erlaubt(self):
        kaputt = dict(SPEC)
        kaputt["flaechen"] = [
            {"id": "x", "quelle": "test",
             "zellen": {z: {"wert": "gezeichnet", "text": "t"} for z in ERWARTETE_ZUSTAENDE}}
        ]
        kaputt["flaechen"][0]["zellen"]["idle"] = {"wert": "vielleicht"}
        fehler = ds.pruefe(kaputt)
        assert any("nicht erlaubt" in f for f in fehler), fehler

    def test_entfaellt_ohne_grund_ist_ein_fehler(self):
        """Die bequeme Tuer, durch die sonst jede Luecke verschwindet."""
        kaputt = dict(SPEC)
        kaputt["flaechen"] = [
            {"id": "x", "quelle": "test",
             "zellen": {z: {"wert": "gezeichnet", "text": "t"} for z in ERWARTETE_ZUSTAENDE}}
        ]
        kaputt["flaechen"][0]["zellen"]["idle"] = {"wert": "entfaellt"}
        fehler = ds.pruefe(kaputt)
        assert any("ohne 'grund'" in f for f in fehler), fehler

    def test_gezeichnet_ohne_text_ist_ein_fehler(self):
        kaputt = dict(SPEC)
        kaputt["flaechen"] = [
            {"id": "x", "quelle": "test",
             "zellen": {z: {"wert": "gezeichnet", "text": "t"} for z in ERWARTETE_ZUSTAENDE}}
        ]
        kaputt["flaechen"][0]["zellen"]["idle"] = {"wert": "gezeichnet"}
        fehler = ds.pruefe(kaputt)
        assert any("ohne 'text'" in f for f in fehler), fehler

    def test_fehlender_zustand_wird_gemeldet(self):
        kaputt = dict(SPEC)
        kaputt["flaechen"] = [{"id": "x", "quelle": "test",
                               "zellen": {"idle": {"wert": "offen"}}}]
        fehler = ds.pruefe(kaputt)
        assert any("Zustaende fehlen" in f for f in fehler), fehler


class TestAbdeckung:
    def test_rechnung_stimmt_mit_der_datei(self):
        a = ds.abdeckung(SPEC)
        assert a["zellen"] == a["gezeichnet"] + a["entfaellt"] + a["offen"]
        assert a["flaechen"] == len(SPEC["flaechen"])
        assert a["zustaende"] == 8

    def test_vollstaendig_heisst_offen_null(self):
        voll = {
            "zustaende": ERWARTETE_ZUSTAENDE,
            "flaechen": [{"id": "x", "quelle": "t",
                          "zellen": {z: {"wert": "gezeichnet", "text": "t"}
                                     for z in ERWARTETE_ZUSTAENDE}}],
        }
        a = ds.abdeckung(voll)
        assert a["offen"] == 0
        assert a["vollstaendig"] is True
        assert a["abdeckung"] == 1.0

    def test_entfaellt_zaehlt_nicht_gegen_die_abdeckung(self):
        """Eine Zelle, die kategorisch nicht zutrifft, darf die Quote nicht druecken."""
        spec = {
            "zustaende": ERWARTETE_ZUSTAENDE,
            "flaechen": [{"id": "x", "quelle": "t", "zellen": dict(
                [(z, {"wert": "entfaellt", "grund": "g"}) for z in ERWARTETE_ZUSTAENDE[1:]]
                + [("idle", {"wert": "gezeichnet", "text": "t"})]
            )}],
        }
        a = ds.abdeckung(spec)
        assert a["abdeckung"] == 1.0
        assert a["vollstaendig"] is True

    def test_das_haus_system_ist_ehrlich_unvollstaendig(self):
        """Kein geschoenter Wert.

        Waere das hier vollstaendig, muesste jede offene Zelle entweder
        gezeichnet oder mit Grund abgeraeumt sein. Ist sie nicht — und das
        steht so in STATUS.md.
        """
        a = ds.abdeckung(SPEC)
        assert a["offen"] > 0
        assert a["vollstaendig"] is False
        assert 0.0 < a["abdeckung"] < 1.0


class TestMarkdownWirdErzeugt:
    def test_tabelle_enthaelt_jede_flaeche_und_jeden_zustand(self):
        md = ds.markdown(SPEC)
        for f in SPEC["flaechen"]:
            assert f["id"] in md
        for z in SPEC["zustaende"]:
            assert z in md

    def test_tabelle_sagt_dass_sie_erzeugt_ist(self):
        """Eine generierte Datei, die das nicht sagt, wird von Hand bearbeitet."""
        assert "GENERIERT" in ds.markdown(SPEC)
