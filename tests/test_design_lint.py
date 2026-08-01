"""T6 — Rohfarb-Erkenner: echte Treffer UND Fehlalarme.

Die Fehlalarme sind der schwierigere Teil. Ein Lint, der bei jedem Digest
anschlaegt, wird abgeschaltet — und ein abgeschalteter Lint ist schlechter als
keiner.
"""

import hashlib

from conftest_design import DESIGN_SYSTEM, lade

lint = lade("design-lint")
ERLAUBT = lint.erlaubte_werte(str(DESIGN_SYSTEM))

DIGEST = hashlib.sha256(b"design-system").hexdigest()


class TestEchteTreffer:
    def test_fremde_farbe_wird_gefunden(self):
        b = lint.pruefe_text(".x{color:#FF00AA}", ERLAUBT)
        assert len(b) == 1
        assert b[0]["normalisiert"] == "#FF00AA"

    def test_kurzform_wird_normalisiert(self):
        b = lint.pruefe_text(".x{color:#f0a}", ERLAUBT)
        assert len(b) == 1
        assert b[0]["normalisiert"] == "#FF00AA"

    def test_farbfunktionen_werden_gefunden(self):
        for ausdruck in ("rgb(1,2,3)", "rgba(1,2,3,.5)", "hsl(1 2% 3%)", "oklch(.5 .1 20)"):
            b = lint.pruefe_text(".x{color:%s}" % ausdruck, ERLAUBT)
            assert b, ausdruck
            assert b[0]["art"] == "funktion", ausdruck

    def test_zeilennummer_stimmt(self):
        text = "zeile1\nzeile2\n.x{color:#FF00AA}\n"
        b = lint.pruefe_text(text, ERLAUBT)
        assert b[0]["zeile"] == 3


class TestErlaubtes:
    def test_hausfarbe_ist_erlaubt(self):
        assert lint.pruefe_text(".x{color:#151E26}", ERLAUBT) == []

    def test_grossschreibung_egal(self):
        assert lint.pruefe_text(".x{color:#151e26}", ERLAUBT) == []

    def test_var_token_ist_der_normalfall(self):
        assert lint.pruefe_text(".x{color:var(--ink)}", ERLAUBT) == []


class TestFehlalarme:
    """Jeder dieser Faelle wurde an echtem Material gemessen."""

    def test_data_uri(self):
        text = ".e{background:url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==)}"
        assert lint.pruefe_text(text, ERLAUBT) == []

    def test_digest(self):
        assert lint.pruefe_text("<code>%s</code>" % DIGEST, ERLAUBT) == []

    def test_html_zahlen_entitaeten(self):
        """23 Falschtreffer im allerersten Lauf ueber design-system/.

        `&#8594;` (Pfeil) liest sich als Vierstellen-Farbe `#8594`. Diese Klasse
        stand in keiner Erhebung — sie kam aus dem eigenen ersten Lauf.
        """
        assert lint.pruefe_text("<p>a &#8594; b &#9548; c &#8984;</p>", ERLAUBT) == []

    def test_hex_entitaet(self):
        assert lint.pruefe_text("<p>&#x2192;</p>", ERLAUBT) == []

    def test_kommentarzeilen(self):
        for kommentar in ("/* war mal #FF00AA */", "// #FF00AA", "<!-- #FF00AA -->",
                          "# #FF00AA", "  * #FF00AA"):
            assert lint.pruefe_text(kommentar, ERLAUBT) == [], kommentar

    def test_l0_definitionszeile_darf_rohwerte_tragen(self):
        """In der Token-Datei STEHEN die Rohwerte — dort sind sie kein Verstoss."""
        text = '  "hex": "#FF00AA"'
        assert lint.pruefe_text(text, ERLAUBT, erlaube_l0=True) == []
        assert lint.pruefe_text(text, ERLAUBT, erlaube_l0=False) != []

    def test_css_variablendefinition_bei_erlaubtem_l0(self):
        text = "--eigen: #FF00AA;"
        assert lint.pruefe_text(text, ERLAUBT, erlaube_l0=True) == []


class TestUeberDasPaket:
    def test_das_eigene_paket_ist_sauber(self):
        befunde = []
        for pfad in lint.sammle_dateien(str(DESIGN_SYSTEM)):
            with open(pfad, encoding="utf-8") as fh:
                befunde.extend(lint.pruefe_text(fh.read(), ERLAUBT, pfad, erlaube_l0=True))
        assert befunde == [], befunde[:5]

    def test_es_gibt_ueberhaupt_erlaubte_werte(self):
        assert len(ERLAUBT) >= 40
