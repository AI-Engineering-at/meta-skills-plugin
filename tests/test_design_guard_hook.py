"""T8 — der Waechter: laesst durch UND lehnt ab, und ist richtig registriert.

Eine Sperre gilt erst als vorhanden, wenn ein Test belegt, dass sie ABLEHNEN
kann. Hausbeweis fuers Gegenteil: hooks/exploration-first.py ist registriert,
laeuft 5x auf sys.exit(0) und hat nie ein deny gesprochen.
"""

import json
import subprocess
import sys

from conftest_design import REPO

GUARD = REPO / "hooks" / "pre-write-design-token-guard.py"
SELBSTTEST = REPO / "hooks" / "pre-write-design-token-guard-test.py"
HOOKS_JSON = REPO / "hooks" / "hooks.json"


def lauf(werkzeug, tool_input):
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps({"tool_name": werkzeug, "tool_input": tool_input}),
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "").strip()
    if not out:
        return "allow", ""
    data = json.loads(out)
    hso = data.get("hookSpecificOutput") or {}
    return ("deny" if hso.get("permissionDecision") == "deny" else "allow"), hso.get(
        "permissionDecisionReason", ""
    )


class TestErLehntAb:
    def test_erfundene_farbe_in_css(self):
        entscheidung, grund = lauf(
            "Write", {"file_path": "/tmp/p/app.css", "content": ".x{color:#FF00AA}"}
        )
        assert entscheidung == "deny"
        assert "#FF00AA" in grund

    def test_der_grund_nennt_den_ausweg(self):
        """Eine Ablehnung ohne Ausweg ist eine Sackgasse."""
        _, grund = lauf(
            "Write", {"file_path": "/tmp/p/app.css", "content": ".x{color:#FF00AA}"}
        )
        assert "tokens.overrides.json" in grund
        assert "DIVERGENZ.md" in grund
        assert "design-lint.py" in grund

    def test_edit_wird_auch_geprueft(self):
        entscheidung, _ = lauf(
            "Edit", {"file_path": "/tmp/p/a.css", "new_string": ".y{background:rgb(1,2,3)}"}
        )
        assert entscheidung == "deny"


class TestErLaesstDurch:
    def test_hausfarbe(self):
        assert lauf("Write", {"file_path": "/tmp/p/a.css",
                              "content": ".x{color:#151E26}"})[0] == "allow"

    def test_keine_gestaltungsdatei(self):
        assert lauf("Write", {"file_path": "/tmp/p/main.py",
                              "content": "C='#FF00AA'"})[0] == "allow"

    def test_bash_ohne_zieldokument(self):
        """Bewusste Reichweitengrenze, im Kopfkommentar benannt."""
        assert lauf("Bash", {"command": "echo '#FF00AA'"})[0] == "allow"

    def test_leere_nutzlast(self):
        assert lauf("Write", {"file_path": "/tmp/p/a.css", "content": ""})[0] == "allow"

    def test_unbekanntes_werkzeug(self):
        assert lauf("Read", {"file_path": "/tmp/p/a.css"})[0] == "allow"

    def test_kaputte_eingabe_blockiert_nichts(self):
        """Ein kaputter Waechter darf keine Arbeit verhindern."""
        proc = subprocess.run(
            [sys.executable, str(GUARD)], input="kein json", capture_output=True, text=True
        )
        assert proc.returncode == 0
        assert not proc.stdout.strip()


class TestSelbsttestLaeuft:
    def test_der_mitgelieferte_ablehnungstest_ist_gruen(self):
        proc = subprocess.run([sys.executable, str(SELBSTTEST)],
                              capture_output=True, text=True)
        assert proc.returncode == 0, proc.stdout
        assert "Fehler: 0" in proc.stdout

    def test_er_enthaelt_echte_deny_faelle(self):
        """Ein Selbsttest ohne deny-Fall ist Dekoration."""
        proc = subprocess.run([sys.executable, str(SELBSTTEST)],
                              capture_output=True, text=True)
        assert proc.stdout.count("ist=deny") >= 4, proc.stdout


class TestRegistrierung:
    def test_ist_registriert(self):
        reg = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        kommandos = [
            h["command"]
            for eintrag in reg["hooks"]["PreToolUse"]
            for h in eintrag["hooks"]
        ]
        assert any("pre-write-design-token-guard.py" in k for k in kommandos)

    def test_kein_leerer_matcher(self):
        """DER Fund vom 2026-07-28: matcher '' ist nicht '.*' — 9 statt 5433 Ausloesungen."""
        reg = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        for eintrag in reg["hooks"]["PreToolUse"]:
            assert eintrag.get("matcher"), eintrag

    def test_matcher_deckt_write_und_edit(self):
        reg = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        for eintrag in reg["hooks"]["PreToolUse"]:
            if any("design-token-guard" in h["command"] for h in eintrag["hooks"]):
                assert "Write" in eintrag["matcher"]
                assert "Edit" in eintrag["matcher"]
                return
        raise AssertionError("Eintrag nicht gefunden")
