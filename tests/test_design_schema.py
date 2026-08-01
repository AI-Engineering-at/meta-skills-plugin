"""T1 — Dokument-Schema: Slugs, Profile, Pflichtregeln.

Der Test, der zaehlt: das Referenzdokument besteht sein EIGENES Schema.
Ein Schema, an dem seine Referenz scheitert, ist kein Schema, sondern ein Wunsch.
"""

import json

from conftest_design import DESIGN_SYSTEM, REPO, lade

doc = lade("design-doc")
SCHEMA = json.loads(
    (DESIGN_SYSTEM / "schema" / "document-schema.json").read_text(encoding="utf-8")
)

# Eingefrorene Slug-Liste. Sie zu aendern ist ein MAJOR — deshalb steht sie hier
# ausgeschrieben und nicht aus dem Schema gelesen: ein Test, der seine Erwartung
# aus dem Pruefling zieht, prueft nichts.
HAUS_SLUGS = [
    "these", "beleg-grundlage", "zielbild-einsatzmoment", "sprache-und-stimme",
    "modus-festlegung", "farbsystem", "schriftsystem", "raster-abstand-form",
    "layout", "token-architektur", "bauteil-katalog", "zustands-matrix",
    "anforderungs-abdeckung", "barrierefreiheit-bewegung", "prototyp-messung",
    "prototyp-reproduzierbarkeit", "herkunft-beispielwerte", "bewusste-auslassungen",
    "risiken", "nicht-geprueft",
]
PRODUKT_ZUSAETZLICH = [
    "informationsarchitektur", "sichtbarmachungs-plan", "fehlstellen", "umsetzungsskizze",
]


class TestSlugsSindEingefroren:
    def test_haus_profil_unveraendert(self):
        assert SCHEMA["profile"]["haus"]["pflicht"] == HAUS_SLUGS

    def test_produkt_erbt_und_ergaenzt(self):
        p = SCHEMA["profile"]["produkt"]
        assert p["erbt"] == "haus"
        assert p["zusaetzlich-pflicht"] == PRODUKT_ZUSAETZLICH
        assert p["entfaellt"] == ["token-architektur"]

    def test_produkt_hat_23_pflicht_slugs(self):
        slugs = doc.pflicht_slugs(SCHEMA, "produkt")
        assert len(slugs) == 23
        assert "token-architektur" not in slugs

    def test_slugs_sind_kleingeschrieben_ohne_nummern(self):
        """Slugs statt Nummern — C musste '13a' einschieben."""
        for s in HAUS_SLUGS + PRODUKT_ZUSAETZLICH:
            assert s == s.lower()
            assert not s[0].isdigit()


class TestDasReferenzdokument:
    def test_besteht_sein_eigenes_schema(self):
        text = (DESIGN_SYSTEM / "DESIGN-SYSTEM.md").read_text(encoding="utf-8")
        fehler, _ = doc.pruefe(text, SCHEMA, "haus")
        assert fehler == [], fehler

    def test_hat_genau_die_erwarteten_abschnitte(self):
        text = (DESIGN_SYSTEM / "DESIGN-SYSTEM.md").read_text(encoding="utf-8")
        assert sorted(doc.abschnitte(text)) == sorted(HAUS_SLUGS)

    def test_frontmatter_vollstaendig(self):
        text = (DESIGN_SYSTEM / "DESIGN-SYSTEM.md").read_text(encoding="utf-8")
        fm = doc.frontmatter(text)
        for feld in SCHEMA["frontmatter"]["pflicht"]:
            assert fm.get(feld), feld


class TestDieVorlage:
    def test_hat_alle_produkt_slugs(self):
        text = (DESIGN_SYSTEM / "TEMPLATE.md").read_text(encoding="utf-8")
        vorhanden = set(doc.abschnitte(text))
        for slug in doc.pflicht_slugs(SCHEMA, "produkt"):
            assert slug in vorhanden, slug

    def test_faellt_durch_solange_sie_unbefuellt_ist(self):
        """Ein Dokument, das die Vorlage noch traegt, ist nicht fertig."""
        text = (DESIGN_SYSTEM / "TEMPLATE.md").read_text(encoding="utf-8")
        fehler, _ = doc.pruefe(text, SCHEMA, "produkt")
        assert any("unbefuellte Vorlagen-Stelle" in f for f in fehler), fehler


class TestDieRegelnMitZaehnen:
    def _basis(self, **ersetzungen):
        kopf = "```yaml\n" + "\n".join(
            "%s: x" % f for f in SCHEMA["frontmatter"]["pflicht"]
        ) + "\n```\n"
        teile = [kopf]
        for slug in doc.pflicht_slugs(SCHEMA, "haus"):
            teile.append("## %s\n\n%s\n" % (slug, ersetzungen.get(slug, "Inhalt.")))
        return "\n".join(teile)

    def test_gute_basis_ist_gruen(self):
        text = self._basis(
            **{
                "beleg-grundlage": "| a | `datei.py:12` |",
                "prototyp-messung": "Ein Fehler wurde gefunden und behoben.",
            }
        )
        fehler, _ = doc.pruefe(text, SCHEMA, "haus")
        assert fehler == [], fehler

    def test_beleg_ohne_fundstelle_faellt_durch(self):
        text = self._basis(
            **{
                "beleg-grundlage": "| a | ich habe nachgesehen |",
                "prototyp-messung": "Ein Fehler wurde behoben.",
            }
        )
        fehler, _ = doc.pruefe(text, SCHEMA, "haus")
        assert any("Fundstelle" in f for f in fehler), fehler

    def test_messung_ohne_gefundenen_fehler_faellt_durch(self):
        text = self._basis(
            **{
                "beleg-grundlage": "| a | `datei.py:12` |",
                "prototyp-messung": "Alles lief auf Anhieb durch.",
            }
        )
        fehler, _ = doc.pruefe(text, SCHEMA, "haus")
        assert any("keinen Fehler" in f for f in fehler), fehler

    def test_fehlender_slug_faellt_durch(self):
        text = self._basis(
            **{
                "beleg-grundlage": "| a | `datei.py:12` |",
                "prototyp-messung": "Ein Fehler wurde behoben.",
            }
        ).replace("## risiken\n", "## risikoo\n")
        fehler, _ = doc.pruefe(text, SCHEMA, "haus")
        assert any("risiken" in f for f in fehler), fehler

    def test_fehlendes_frontmatter_feld_faellt_durch(self):
        text = self._basis(
            **{
                "beleg-grundlage": "| a | `datei.py:12` |",
                "prototyp-messung": "Ein Fehler wurde behoben.",
            }
        ).replace("autor: x\n", "")
        fehler, _ = doc.pruefe(text, SCHEMA, "haus")
        assert any("autor" in f for f in fehler), fehler


class TestJurySlugsPassenZumSystemSkill:
    def test_jury_erzeugt_nur_bekannte_slugs(self):
        """Gegenmittel gegen Risiko 2 der Architektur: die zwei Skills laufen auseinander.

        `requires: [design]` ist Prosa, kein Python liest es. Was pruefbar ist:
        dass die Vorlage, auf die der Jury-Skill seine Entwuerfe verpflichtet,
        genau das Produkt-Profil des System-Skills ist.
        """
        brief = (REPO / "skills" / "design-jury" / "references" / "entwurfs-brief.md").read_text(
            encoding="utf-8"
        )
        assert "TEMPLATE.md" in brief
        assert "Profil produkt" in brief
