"""T2 — Token-Datei: DTCG-Konformitaet, Invarianten, Alias-Disziplin.

Der wichtigste Test hier ist `test_kein_doppelwert_ohne_alias`. Er kodiert einen
gemessenen Fehler aus dem Rohmaterial: `--fog` und `--ink-dim` trugen denselben
Hex-Wert unter zwei Namen — nicht als Absicht deklariert, sondern zufaellig
gleich. Wer den einen aendert, aendert den anderen nicht mit, und niemand merkt es.
"""

import json

import pytest

from conftest_design import DESIGN_SYSTEM, lade

design_lib = lade("design_lib")

TOKENS = json.loads((DESIGN_SYSTEM / "tokens.dtcg.json").read_text(encoding="utf-8"))
FLAT = design_lib.flatten_tokens(TOKENS)

DTCG_TYPEN = {
    "color", "dimension", "fontFamily", "fontWeight", "duration", "cubicBezier",
    "number", "strokeStyle", "border", "transition", "shadow", "gradient", "typography",
}


class TestDTCGKonformitaet:
    def test_es_gibt_ueberhaupt_token(self):
        assert len(FLAT) > 0

    def test_jedes_token_hat_erlaubten_typ(self):
        ohne = [p for p, n in FLAT.items() if n.get("$type") not in DTCG_TYPEN]
        assert ohne == [], "Token mit unbekanntem $type: %s" % ohne

    def test_farbwert_ist_objektform_mit_hex(self):
        """DTCG 2025.10 verlangt {colorSpace, components[, alpha, hex]}."""
        for pfad, node in FLAT.items():
            if node.get("$type") != "color":
                continue
            wert = node.get("$value")
            if isinstance(wert, str):
                continue  # Alias, wird anderswo geprueft
            assert isinstance(wert, dict), pfad
            assert "colorSpace" in wert, pfad
            assert "components" in wert, pfad
            assert len(wert["components"]) == 3, pfad

    def test_dimension_hat_wert_und_einheit(self):
        for pfad, node in FLAT.items():
            if node.get("$type") != "dimension":
                continue
            wert = node["$value"]
            assert isinstance(wert, dict) and "value" in wert and "unit" in wert, pfad

    def test_vendortes_schema_ist_da_und_unveraendert_gross(self):
        """56523 Bytes — der Wert, der beim Laden per curl gemessen wurde.

        Aendert sich die Groesse, hat jemand das Schema getauscht. Das soll ein
        sichtbarer Commit sein, keine stille Verhaltensaenderung.
        """
        schema = DESIGN_SYSTEM / "schema" / "dtcg-format-2025.10.json"
        assert schema.exists()
        assert schema.stat().st_size == 56523


class TestInvarianten:
    def test_i3_jedes_farbtoken_sagt_was_es_bedeutet(self):
        ohne = [
            p for p, n in FLAT.items()
            if n.get("$type") == "color" and not (n.get("$description") or "").strip()
        ]
        assert ohne == [], "Farb-Token ohne $description: %s" % ohne

    def test_i1_bedienfarbe_taucht_in_keinem_zustandstoken_auf(self):
        """Interaktions-Kodierung und Zustands-Kodierung sind disjunkt."""
        for theme in design_lib.theme_names(TOKENS):
            accent = design_lib.token_hex("color.%s.interactive.accent" % theme, FLAT)
            zustand = [
                design_lib.token_hex(p, FLAT)
                for p in FLAT
                if p.startswith("color.%s.state." % theme)
                and FLAT[p].get("$type") == "color"
            ]
            assert accent not in zustand, (
                "%s: der Akzent ist zugleich ein Zustandston — I1 gebrochen" % theme
            )

    def test_i4_jeder_hexwert_ist_grossgeschrieben_und_sechsstellig(self):
        for pfad, node in FLAT.items():
            if node.get("$type") != "color" or isinstance(node["$value"], str):
                continue
            hexwert = node["$value"]["hex"]
            assert hexwert == hexwert.upper(), pfad
            assert len(hexwert) == 7, pfad


class TestAliasDisziplin:
    def test_aliasse_loesen_auf(self):
        aliasse = [p for p, n in FLAT.items() if isinstance(n.get("$value"), str)]
        assert aliasse, "keine Aliasse vorhanden — dann fehlt die Alias-Ebene"
        for a in aliasse:
            ziel, node = design_lib.resolve_alias(a, FLAT)
            assert ziel != a
            assert not isinstance(node["$value"], str)

    def test_kein_doppelwert_ohne_alias(self):
        """DER gemessene Fehler aus dem Rohmaterial: --fog == --ink-dim.

        Zwei Token mit gleichem aufgeloestem Wert sind ein Fehler, es sei denn,
        einer erklaert sich per Alias zum anderen ODER der Fall steht mit Grund
        und Adresse in gleichwerte.json.

        WICHTIG — die Deckung gehoert zum Wert. Der erste Entwurf dieses Tests
        verglich nur den Hex-Anteil und meldete deshalb `state.*.tint` gegen
        `state.*.base` als Doppel. Falsch: der Tint ist derselbe Ton bei
        alpha 0.1, sein aufgeloester Wert ist ein anderer. Das war ein Fehler im
        Test, nicht in den Token.
        """
        register = json.loads(
            (DESIGN_SYSTEM / "gleichwerte.json").read_text(encoding="utf-8")
        )
        erlaubt = set()
        for eintrag in register["gleichwerte"]:
            erlaubt.add(tuple(sorted(eintrag["token"])))

        for theme in design_lib.theme_names(TOKENS):
            nach_wert = {}
            for pfad, node in FLAT.items():
                if not pfad.startswith("color.%s." % theme):
                    continue
                if node.get("$type") != "color":
                    continue
                wert = node.get("$value")
                if isinstance(wert, str):
                    continue  # deklarierter Alias — genau der erlaubte Fall
                schluessel = "%s@%s" % (wert["hex"].upper(), wert.get("alpha", "1"))
                nach_wert.setdefault(schluessel, []).append(pfad)

            unerklaert = {
                w: sorted(p)
                for w, p in nach_wert.items()
                if len(p) > 1 and tuple(sorted(p)) not in erlaubt
            }
            assert unerklaert == {}, (
                "%s: gleicher Wert unter mehreren Namen, weder Alias noch in "
                "gleichwerte.json eingetragen: %s" % (theme, unerklaert)
            )

    def test_register_beschreibt_nur_echte_gleichwerte(self):
        """Ein Register, das Faelle auffuehrt, die es nicht mehr gibt, verrottet.

        Jeder Eintrag muss noch zutreffen — sonst ist er eine Ausnahme fuer
        nichts und deckt beim naechsten Mal einen echten Fund zu.
        """
        register = json.loads(
            (DESIGN_SYSTEM / "gleichwerte.json").read_text(encoding="utf-8")
        )
        for eintrag in register["gleichwerte"]:
            werte = set()
            for pfad in eintrag["token"]:
                node = FLAT[pfad]
                wert = node["$value"]
                werte.add("%s@%s" % (wert["hex"].upper(), wert.get("alpha", "1")))
            assert len(werte) == 1, (
                "Eintrag in gleichwerte.json trifft nicht mehr zu (%s hat jetzt "
                "verschiedene Werte: %s) — er gehoert entfernt." % (eintrag["token"], werte)
            )
            assert eintrag.get("grund", "").strip(), eintrag["token"]
            assert eintrag.get("wer-entscheidet", "").strip(), eintrag["token"]

    def test_alias_zyklus_wird_erkannt(self):
        zyklisch = {
            "a": {"$type": "color", "$value": "{b}"},
            "b": {"$type": "color", "$value": "{a}"},
        }
        with pytest.raises(ValueError):
            design_lib.resolve_alias("a", zyklisch)


class TestPaketsuche:
    def test_findet_das_paket(self):
        assert design_lib.find_design_system() == str(DESIGN_SYSTEM)

    def test_scheitert_benannt_statt_still(self, tmp_path):
        """Kein eingebauter Vorgabe-Satz — ein System, das nicht da ist, ist nicht da."""
        with pytest.raises(design_lib.DesignSystemNotFound) as exc:
            design_lib.find_design_system(str(tmp_path))
        assert "tokens.dtcg.json" in str(exc.value)
