"""T9 — Versionierung: Ableitung, Overrides, Divergenz-Buchfuehrung, Migration."""

import json

from conftest_design import DESIGN_SYSTEM, lade

dr = lade("design-resolve")
dc = lade("design-check")


def schreibe(pfad, daten):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(daten, indent=2), encoding="utf-8")


class TestSemVerRechnung:
    def test_stufen(self):
        assert dc.stufe((1, 0, 0), (2, 0, 0)) == "MAJOR"
        assert dc.stufe((1, 0, 0), (1, 1, 0)) == "MINOR"
        assert dc.stufe((1, 0, 0), (1, 0, 1)) == "PATCH"
        assert dc.stufe((1, 0, 0), (1, 0, 0)) == "gleich"
        assert dc.stufe((2, 0, 0), (1, 0, 0)) == "rueckwaerts"
        assert dc.stufe(None, (1, 0, 0)) == "unbekannt"

    def test_parser(self):
        assert dc.semver("1.2.3") == (1, 2, 3)
        assert dc.semver("  1.2.3  ") == (1, 2, 3)
        assert dc.semver("keine version") is None


class TestAufloesung:
    def test_basis_ohne_overrides(self):
        lock = dr.aufloesen(str(DESIGN_SYSTEM))
        assert lock["token_gesamt"] > 0
        assert lock["ueberschrieben"] == []
        assert lock["vollkopie"] is False
        assert len(lock["basis_sha256"]) == 64

    def test_lock_haelt_den_basis_hash_fest(self):
        """Ohne diesen Bezug ist jede Migrationsaussage geraten."""
        a = dr.aufloesen(str(DESIGN_SYSTEM))
        b = dr.aufloesen(str(DESIGN_SYSTEM))
        assert a["basis_sha256"] == b["basis_sha256"]

    def test_override_wird_uebernommen_und_markiert(self, tmp_path):
        ov = tmp_path / "tokens.overrides.json"
        schreibe(ov, {"color": {"dark": {"state": {"danger": {"base": {
            "$type": "color",
            "$value": {"colorSpace": "srgb", "components": [0.7, 0.1, 0.1],
                       "hex": "#B31A1A"},
        }}}}}})
        lock = dr.aufloesen(str(DESIGN_SYSTEM), str(ov))
        pfad = "color.dark.state.danger.base"
        assert pfad in lock["ueberschrieben"]
        assert lock["tokens"][pfad]["herkunft"] == "override"
        assert lock["tokens"][pfad]["wert"]["hex"] == "#B31A1A"

    def test_nicht_ueberschriebene_bleiben_basis(self, tmp_path):
        ov = tmp_path / "o.json"
        schreibe(ov, {"color": {"dark": {"state": {"danger": {"base": {
            "$type": "color",
            "$value": {"colorSpace": "srgb", "components": [0.7, 0.1, 0.1],
                       "hex": "#B31A1A"},
        }}}}}})
        lock = dr.aufloesen(str(DESIGN_SYSTEM), str(ov))
        assert lock["tokens"]["color.dark.ink.primary"]["herkunft"] == "basis"

    def test_vollkopie_wird_erkannt(self, tmp_path):
        """Ein Projekt kann das System nicht stillschweigend forken."""
        basis = json.loads((DESIGN_SYSTEM / "tokens.dtcg.json").read_text(encoding="utf-8"))
        ov = tmp_path / "voll.json"
        ov.write_text(json.dumps(basis), encoding="utf-8")
        lock = dr.aufloesen(str(DESIGN_SYSTEM), str(ov))
        assert lock["vollkopie"] is True

    def test_unbekanntes_modul_scheitert_benannt(self, tmp_path):
        try:
            dr.aufloesen(str(DESIGN_SYSTEM), None, ["gibtesnicht"])
        except Exception as exc:
            assert "gibtesnicht" in str(exc)
        else:
            raise AssertionError("haette scheitern muessen")


class TestDivergenzBuchfuehrung:
    def _tabelle(self, zeilen):
        kopf = "| Token-Pfad | Klasse | Grund | ueberpruefen-bis | Wer |\n|---|---|---|---|---|\n"
        return kopf + "".join(zeilen)

    def test_liest_eine_zeile(self, tmp_path):
        f = tmp_path / "DIVERGENZ.md"
        f.write_text(self._tabelle([
            "| `color.dark.state.danger.base` | darf-nicht | Marke | 2027-02-01 | fable-5 |\n"
        ]), encoding="utf-8")
        zeilen = dc.lies_divergenz(str(f))
        assert len(zeilen) == 1
        assert zeilen[0]["token"] == "color.dark.state.danger.base"
        assert zeilen[0]["klasse"] == "darf-nicht"
        assert zeilen[0]["bis"] == "2027-02-01"

    def test_kopf_und_trennzeile_zaehlen_nicht(self, tmp_path):
        f = tmp_path / "D.md"
        f.write_text(self._tabelle([]), encoding="utf-8")
        assert dc.lies_divergenz(str(f)) == []

    def test_fehlende_datei_ist_leer_nicht_fehler(self, tmp_path):
        assert dc.lies_divergenz(str(tmp_path / "gibtsnicht.md")) == []

    def test_die_drei_klassen_sind_die_erlaubten(self):
        assert dc.KLASSEN == ("kann-nicht", "will-nicht", "darf-nicht")


class TestProjektPruefung:
    def _projekt(self, tmp_path, override_hex="#B31A1A", divergenz=True,
                 bis="2099-01-01", klasse="darf-nicht", version="1.0.0"):
        d = tmp_path / "design"
        d.mkdir(parents=True, exist_ok=True)
        pfad = "color.dark.state.danger.base"
        schreibe(d / "tokens.overrides.json", {"color": {"dark": {"state": {"danger": {
            "base": {"$type": "color", "$value": {
                "colorSpace": "srgb", "components": [0.7, 0.1, 0.1], "hex": override_hex}}
        }}}}})
        schreibe(d / ".design-lock.json", {"system_version": version})
        if divergenz:
            (d / "DIVERGENZ.md").write_text(
                "| Token-Pfad | Klasse | Grund | ueberpruefen-bis | Wer |\n|---|---|---|---|---|\n"
                "| `%s` | %s | Kundenmarke | %s | fable-5 |\n" % (pfad, klasse, bis),
                encoding="utf-8",
            )
        return tmp_path

    def test_sauberes_projekt_ist_gruen(self, tmp_path, capsys):
        p = self._projekt(tmp_path)
        rc = dc.main(["design-check", "--projekt", str(p), "--ci",
                      "--system", str(DESIGN_SYSTEM), "--heute", "2026-08-01"])
        assert rc == 0, capsys.readouterr().out

    def test_override_ohne_divergenzzeile_bricht(self, tmp_path, capsys):
        p = self._projekt(tmp_path, divergenz=False)
        rc = dc.main(["design-check", "--projekt", str(p), "--ci",
                      "--system", str(DESIGN_SYSTEM), "--heute", "2026-08-01"])
        assert rc == 1
        assert "ohne DIVERGENZ-Zeile" in capsys.readouterr().out

    def test_unbekannte_klasse_bricht(self, tmp_path, capsys):
        p = self._projekt(tmp_path, klasse="weil-halt")
        rc = dc.main(["design-check", "--projekt", str(p), "--ci",
                      "--system", str(DESIGN_SYSTEM), "--heute", "2026-08-01"])
        assert rc == 1
        assert "nicht erlaubt" in capsys.readouterr().out

    def test_fehlendes_ablaufdatum_bricht(self, tmp_path, capsys):
        """Ohne Ablauf wird aus einer Abweichung stillschweigend Dauerzustand."""
        p = self._projekt(tmp_path, bis="")
        rc = dc.main(["design-check", "--projekt", str(p), "--ci",
                      "--system", str(DESIGN_SYSTEM), "--heute", "2026-08-01"])
        assert rc == 1
        assert "ueberpruefen-bis" in capsys.readouterr().out

    def test_abgelaufene_divergenz_warnt_nur(self, tmp_path, capsys):
        """Gespraechsanlass, kein Baufehler."""
        p = self._projekt(tmp_path, bis="2020-01-01")
        rc = dc.main(["design-check", "--projekt", str(p), "--ci",
                      "--system", str(DESIGN_SYSTEM), "--heute", "2026-08-01"])
        ausgabe = capsys.readouterr().out
        assert rc == 0
        assert "abgelaufen" in ausgabe

    def test_major_ohne_migrationsdatei_bricht(self, tmp_path, capsys):
        p = self._projekt(tmp_path, version="0.1.0")
        rc = dc.main(["design-check", "--projekt", str(p), "--ci",
                      "--system", str(DESIGN_SYSTEM), "--heute", "2026-08-01"])
        assert rc == 1
        assert "ohne Migrationsdatei" in capsys.readouterr().out

    def test_projekt_ohne_design_ordner_ist_kein_fehler(self, tmp_path, capsys):
        rc = dc.main(["design-check", "--projekt", str(tmp_path), "--ci",
                      "--system", str(DESIGN_SYSTEM)])
        assert rc == 0
        assert "leitet nichts ab" in capsys.readouterr().out


class TestChangelogFuehrtDieRegeln:
    def test_breaking_tabelle_nennt_die_major_faelle(self):
        text = (DESIGN_SYSTEM / "CHANGELOG.md").read_text(encoding="utf-8")
        for fall in ("Token entfernt", "Token umbenannt", "$type", "Bedeutung geaendert"):
            assert fall in text, fall

    def test_die_ehrliche_luecke_ist_benannt(self):
        """'Bedeutung geaendert' ist nicht maschinell erkennbar — das muss dastehen."""
        text = (DESIGN_SYSTEM / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "nicht maschinell erkennbar" in text

    def test_tdiff_wird_als_nicht_ausgefuehrt_ausgewiesen(self):
        text = (DESIGN_SYSTEM / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "nicht ausgefuehrt" in text
