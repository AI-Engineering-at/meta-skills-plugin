"""T11 — der Zaehl-Bericht: MANIFEST wird erzeugt, Drift wird rot.

DIE KRANKHEIT, GEGEN DIE DAS GEBAUT IST — im eigenen Repo gemessen:
  plugin.json      346 Tests
  README.md        444
  CHANGELOG        646
  .gitea/ci.yml    725
  tatsaechlich     755
Jede getippte Zahl driftet. Ausnahmslos.
"""

import json

from conftest_design import DESIGN_SYSTEM, lade

dr = lade("design-report")


class TestZaehlung:
    def test_zahlen_stammen_aus_den_dateien(self):
        daten = dr.sammle(str(DESIGN_SYSTEM))
        z = daten["zaehlungen"]
        tokens = json.loads((DESIGN_SYSTEM / "tokens.dtcg.json").read_text(encoding="utf-8"))
        states = json.loads((DESIGN_SYSTEM / "states.json").read_text(encoding="utf-8"))
        komponenten = list((DESIGN_SYSTEM / "components").glob("*.md"))

        design_lib = lade("design_lib")
        assert z["token_gesamt"] == len(design_lib.flatten_tokens(tokens))
        assert z["flaechen"] == len(states["flaechen"])
        assert z["zustaende"] == len(states["zustaende"])
        assert z["komponenten"] == len(komponenten)

    def test_matrix_zellen_gehen_auf(self):
        z = dr.sammle(str(DESIGN_SYSTEM))["zaehlungen"]
        assert z["matrix_zellen"] == z["flaechen"] * z["zustaende"]
        assert (z["matrix_gezeichnet"] + z["matrix_entfaellt"] + z["matrix_offen"]
                == z["matrix_zellen"])

    def test_kontrastrechnungen_stimmen_mit_dem_rechner(self):
        """Zwei Wege, eine Zahl."""
        dc = lade("design-contrast")
        rows, _, _ = dc.evaluate(str(DESIGN_SYSTEM))
        gerechnet = len([r for r in rows if r["kind"] != "info"])
        assert dr.sammle(str(DESIGN_SYSTEM))["zaehlungen"][
            "kontrast_rechnungen_gesamt"] == gerechnet

    def test_datei_hashes_sind_echte_sha256(self):
        h = dr.sammle(str(DESIGN_SYSTEM))["datei_hashes_sha256"]
        assert "tokens.dtcg.json" in h
        for wert in h.values():
            assert len(wert) == 64
            int(wert, 16)


class TestDriftGate:
    def test_committetes_manifest_stimmt(self):
        neu = dr.sammle(str(DESIGN_SYSTEM))
        alt = json.loads((DESIGN_SYSTEM / "MANIFEST.json").read_text(encoding="utf-8"))
        assert alt["zaehlungen"] == neu["zaehlungen"], (
            "MANIFEST.json ist veraltet — python3 scripts/design-report.py"
        )

    def test_manifest_sagt_dass_es_erzeugt_ist(self):
        alt = json.loads((DESIGN_SYSTEM / "MANIFEST.json").read_text(encoding="utf-8"))
        assert "GENERIERT" in alt["$description"]

    def test_check_meldet_manipulierte_zahlen(self, tmp_path):
        """Der Beweis, dass das Gate greift — an einer kuenstlichen Drift."""
        import shutil

        kopie = tmp_path / "design-system"
        shutil.copytree(str(DESIGN_SYSTEM), str(kopie))
        manifest = json.loads((kopie / "MANIFEST.json").read_text(encoding="utf-8"))
        manifest["zaehlungen"]["token_gesamt"] = 999
        (kopie / "MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        rc = dr.main(["design-report", "--check", "--system", str(kopie)])
        assert rc == 1

    def test_check_ist_gruen_nach_erzeugen(self, tmp_path):
        import shutil

        kopie = tmp_path / "design-system"
        shutil.copytree(str(DESIGN_SYSTEM), str(kopie))
        (kopie / "MANIFEST.json").unlink()
        assert dr.main(["design-report", "--check", "--system", str(kopie)]) == 1
        assert dr.main(["design-report", "--system", str(kopie)]) == 0
        assert dr.main(["design-report", "--check", "--system", str(kopie)]) == 0

    def test_erzeugen_ist_deterministisch(self, tmp_path):
        """Zweimal erzeugen ergibt zweimal dasselbe — sonst waere --check nutzlos."""
        a = json.dumps(dr.sammle(str(DESIGN_SYSTEM)), sort_keys=True)
        b = json.dumps(dr.sammle(str(DESIGN_SYSTEM)), sort_keys=True)
        assert a == b


class TestVersionsquelle:
    def test_version_steht_an_genau_einer_stelle(self):
        version = (DESIGN_SYSTEM / "VERSION").read_text(encoding="utf-8").strip()
        assert version
        assert dr.sammle(str(DESIGN_SYSTEM))["version"] == version

    def test_changelog_kennt_diese_version(self):
        version = (DESIGN_SYSTEM / "VERSION").read_text(encoding="utf-8").strip()
        text = (DESIGN_SYSTEM / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## %s" % version in text, (
            "VERSION sagt %s, der CHANGELOG kennt sie nicht — genau die Kette, "
            "die im Plugin gerissen ist." % version
        )
