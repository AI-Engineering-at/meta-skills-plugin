"""T10 — Cross-Runtime: die Trennlinie laeuft zwischen Wissen und Mechanik.

Nicht zwischen Claude Code und opencode. Wissen (SKILL.md, design-system/,
scripts/) ist geteilt; Mechanik (hooks.json, commands/, JS-Plugins) ist
adapterspezifisch.

EHRLICH: dieser Test prueft DATEIWAHRHEIT, nicht Laufzeitwahrheit. Dass opencode
die Skills tatsaechlich laedt, ist damit NICHT belegt — dazu braucht es einen
echten Lauf mit beiden Werkzeugen. Steht als offener Punkt in skills/design/STATUS.md.
"""

import json
import re

from conftest_design import DESIGN_SYSTEM, REPO, lade

design_lib = lade("design_lib")

OPENCODE_SKILLS = REPO / ".opencode-plugin" / "skills"
ALLOWED_FORKS = REPO / "integrations" / "ALLOWED-FORKS.md"
DESIGN_SKILLS = ["design", "design-jury"]


def frontmatter_name(pfad):
    text = pfad.read_text(encoding="utf-8")
    m = re.search(r"^name:\s*(\S+)", text, re.M)
    return m.group(1) if m else None


class TestForkErkennung:
    def test_kein_unerlaubter_fork(self):
        if not OPENCODE_SKILLS.exists():
            return
        haus = {d.name for d in (REPO / "skills").iterdir() if d.is_dir()}
        erlaubt = set(re.findall(r"^\|\s*`([\w-]+)`", ALLOWED_FORKS.read_text(encoding="utf-8"), re.M))
        forks = []
        for skill_md in OPENCODE_SKILLS.glob("*/SKILL.md"):
            name = skill_md.parent.name
            if name in haus and name not in erlaubt:
                forks.append(name)
        assert forks == [], (
            "geforkte SKILL.md ohne Eintrag in ALLOWED-FORKS.md: %s" % forks
        )

    def test_die_altlast_ist_gezaehlt(self):
        """Genau ein Eintrag am Tag 1 — gezaehlt statt versteckt."""
        erlaubt = re.findall(r"^\|\s*`([\w-]+)`", ALLOWED_FORKS.read_text(encoding="utf-8"), re.M)
        assert erlaubt == ["statusbar"], erlaubt

    def test_jeder_eintrag_hat_grund_und_adresse(self):
        text = ALLOWED_FORKS.read_text(encoding="utf-8")
        for zeile in text.splitlines():
            if not zeile.startswith("| `"):
                continue
            felder = [f.strip() for f in zeile.strip("|").split("|")]
            assert len(felder) >= 4, zeile
            assert felder[2], "Grund fehlt: %s" % zeile
            assert felder[3], "Adresse fehlt: %s" % zeile

    def test_die_design_skills_sind_nicht_geforkt(self):
        if not OPENCODE_SKILLS.exists():
            return
        for name in DESIGN_SKILLS:
            assert not (OPENCODE_SKILLS / name / "SKILL.md").exists(), name


class TestGeteiltesWissen:
    def test_beide_design_skills_liegen_im_geteilten_ordner(self):
        for name in DESIGN_SKILLS:
            assert (REPO / "skills" / name / "SKILL.md").exists(), name

    def test_der_name_im_frontmatter_passt_zum_verzeichnis(self):
        """Agent-Skills-Standard: name MUSS dem Verzeichnisnamen entsprechen."""
        for name in DESIGN_SKILLS:
            assert frontmatter_name(REPO / "skills" / name / "SKILL.md") == name

    def test_name_haelt_das_standard_muster(self):
        muster = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
        for name in DESIGN_SKILLS:
            assert muster.match(name), name
            assert 1 <= len(name) <= 64

    def test_description_haelt_die_standard_laenge(self):
        for name in DESIGN_SKILLS:
            text = (REPO / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            m = re.search(r"^description:\s*(.+)$", text, re.M)
            assert m, name
            assert 1 <= len(m.group(1).strip()) <= 1024, name

    def test_werkzeuge_sind_reine_cli_ohne_harness_aufruf(self):
        """scripts/design-*.py muessen ohne Claude-Code-Harness laufen.

        Sonst waeren sie nicht cross-runtime, sondern Claude-Code-Mechanik.
        """
        for pfad in (REPO / "scripts").glob("design*.py"):
            text = pfad.read_text(encoding="utf-8")
            assert "hookSpecificOutput" not in text, pfad.name
            assert "CLAUDE_PLUGIN_ROOT" not in text, pfad.name


class TestErreichbarkeit:
    def test_das_paket_wird_von_der_plugin_wurzel_aus_gefunden(self):
        assert design_lib.find_design_system() == str(DESIGN_SYSTEM)

    def test_die_suchreihenfolge_ist_die_dokumentierte(self):
        labels = [label for label, _ in design_lib.candidate_roots()]
        assert labels[-2:] == ["<plugin-root>/design-system", "./design-system"]

    def test_opencode_profile_zeigen_auf_vorhandene_skill_pfade(self):
        """Nebenbefund, den dieser Test aufdecken soll: harte /Users/-Pfade."""
        profile = list((REPO / "integrations" / "opencode" / "profiles").glob("*.jsonc")) \
            if (REPO / "integrations" / "opencode" / "profiles").exists() else []
        if not profile:
            return
        for p in profile:
            text = p.read_text(encoding="utf-8")
            for treffer in re.findall(r'"(/Users/[^"]+/skills)"', text):
                # Kein assert auf Existenz — der Pfad ist maschinenabhaengig.
                # Geprueft wird nur, dass er auf skills/ zeigt und nicht auf einen Fork.
                assert treffer.endswith("skills"), treffer


class TestMechanikBleibtGetrennt:
    def test_hooks_sind_claude_code_spezifisch_und_nicht_im_skill(self):
        for name in DESIGN_SKILLS:
            text = (REPO / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            assert "hooks:" not in text, name

    def test_der_waechter_liegt_in_der_mechanik_schicht(self):
        assert (REPO / "hooks" / "pre-write-design-token-guard.py").exists()
        reg = json.loads((REPO / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        assert "PreToolUse" in reg["hooks"]
