"""Ein leerer `matcher` heißt nicht „alle Werkzeuge" — `'.*'` heißt das.

ANLASS (2026-07-28)
`token-audit.py` war auf `PostToolUse` mit `matcher: ""` registriert und sollte damit jeden
Werkzeugaufruf mitschreiben. Gemessen an einem Tag schwerer Arbeit:

    token-audit.jsonl      9 Einträge, ALLE  session="unknown" tool="unknown", 2 Byte Eingabe
    brain-token-log/…      5433 Einträge, echte session_id, echtes tool_call, sekundenaktuell

Beide sind `PostToolUse`, beide in derselben Sitzung, beide Python über stdin. Der einzige
Unterschied ist der Matcher: der eine `""`, der andere `".*"`.

WARUM DAS SO SCHWER ZU SEHEN WAR
Der Hook lief. Er schrieb. Er endete mit 0. Die Datei wuchs. Mein eigener geplanter Prüfpunkt
lautete wörtlich „wächst `token-audit.jsonl` bei normaler Arbeit?" — die Antwort war **ja**, und
sie war wertlos. Neun Datensätze mit `"tool": "unknown"` sind kein Audit, sie sind neun Zeilen.

Das ist „grünes Rohr ohne Inhalt": Exit 0 und eine geschriebene Datei belegen den Transport
nicht. Ein Zähler, der nur zählt, ob etwas ankam, misst nicht, ob etwas drin war.

WAS DIESE TESTS HALTEN
Kein Werkzeug-Ereignis darf einen leeren Matcher tragen. Das ist eine Ein-Zeichen-Änderung, die
niemand beim Lesen bemerkt und die den Hook still wirkungslos macht.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

HOOKS_JSON = Path(__file__).resolve().parent.parent / "hooks" / "hooks.json"

# Ereignisse, bei denen der Matcher gegen den Werkzeugnamen läuft. Bei SessionStart,
# UserPromptSubmit, Stop, PreCompact und SessionEnd gibt es kein Werkzeug — dort ist ein
# leerer Matcher richtig und bleibt unangetastet.
WERKZEUG_EREIGNISSE = ("PreToolUse", "PostToolUse")


@pytest.fixture(scope="module")
def registrierung() -> dict:
    return json.loads(HOOKS_JSON.read_text(encoding="utf-8"))


def _eintraege(reg: dict, ereignis: str) -> list[dict]:
    return reg.get("hooks", {}).get(ereignis, [])


def _namen(eintrag: dict) -> list[str]:
    return [h.get("command", "").rsplit("/", 1)[-1].replace('"', "")
            for h in eintrag.get("hooks", [])]


@pytest.mark.parametrize("ereignis", WERKZEUG_EREIGNISSE)
def test_kein_werkzeug_hook_mit_leerem_matcher(registrierung: dict, ereignis: str) -> None:
    """Der eigentliche Fund. Ein Zeichen entscheidet über 9 gegen 5433 Aufrufe."""
    leer = [
        ", ".join(_namen(e))
        for e in _eintraege(registrierung, ereignis)
        if e.get("matcher", None) == ""
    ]
    assert not leer, (
        f"{ereignis} hat Einträge mit leerem matcher: {leer}. "
        "Ein leerer Matcher lässt den Hook fast nie feuern und ohne Nutzlast — gemessen "
        "2026-07-28: 9 Aufrufe statt 5433, alle mit tool='unknown'. Für „alle Werkzeuge\" "
        "gehört '.*' dorthin."
    )


@pytest.mark.parametrize("ereignis", WERKZEUG_EREIGNISSE)
def test_jeder_werkzeug_hook_hat_ueberhaupt_einen_matcher(registrierung: dict, ereignis: str) -> None:
    """Ein fehlender Schlüssel ist nicht besser als ein leerer — nur schlechter sichtbar."""
    ohne = [
        ", ".join(_namen(e))
        for e in _eintraege(registrierung, ereignis)
        if "matcher" not in e
    ]
    assert not ohne, f"{ereignis}: Eintrag ohne matcher-Schlüssel: {ohne}"


def test_token_audit_faengt_wirklich_alles(registrierung: dict) -> None:
    """Namentlich, weil dieser Hook der Grund für die ganze Datei ist."""
    treffer = [
        e for e in _eintraege(registrierung, "PostToolUse")
        if any("token-audit" in n for n in _namen(e))
    ]
    assert treffer, "token-audit.py ist nicht mehr auf PostToolUse registriert"
    assert treffer[0].get("matcher") == ".*", (
        f"token-audit hat matcher={treffer[0].get('matcher')!r} statt '.*' — damit "
        "protokolliert es wieder einen Bruchteil der Aufrufe, ohne dass etwas rot wird."
    )


def test_die_registrierung_ist_lesbar() -> None:
    """Eine kaputte hooks.json nimmt alle 26 Hooks mit, nicht nur einen."""
    reg = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    assert reg.get("hooks"), "hooks.json hat keinen 'hooks'-Schlüssel"
    for ereignis, eintraege in reg["hooks"].items():
        assert isinstance(eintraege, list), f"{ereignis} ist keine Liste"
        for e in eintraege:
            assert e.get("hooks"), f"{ereignis}: Eintrag ohne auszuführende Hooks"
            for h in e["hooks"]:
                assert h.get("command"), f"{ereignis}: Hook ohne command"


def test_kein_hook_wird_direkt_und_nicht_ausfuehrbar_aufgerufen(registrierung: dict) -> None:
    """Der fünfte Fall derselben Klasse an einem Tag (2026-07-28).

    `hooks/run-hook.cmd` war auf `Stop` registriert und wurde **direkt** aufgerufen —
    ein Windows-Batch-Wrapper (`@echo off`, `REM Windows wrapper`) mit Modus 644. Auf dem
    Mac scheitert das mit „permission denied", der Hook tut nichts, und **nichts wird rot**.

    Der Witz daran: der Wrapper machte nur `bash "%SCRIPT_DIR%%1.sh"`. Er brauchte bash
    ohnehin. Der Umweg über Batch machte die Sache also **nicht portabler, sondern weniger**
    — auf jedem System, auf dem der Wrapper funktionierte, hätte auch `bash on-stop.sh`
    funktioniert. Jetzt steht genau das dort.

    `on-stop.sh` bleibt geprüft, nicht nur registriert: ein Probelauf schreibt 90 Byte nach
    `session-metrics.jsonl`. Exit 0 allein wäre kein Beleg gewesen — das war heute dreimal
    die Falle.
    """
    for ereignis, eintraege in registrierung.get("hooks", {}).items():
        for e in eintraege:
            for h in e.get("hooks", []):
                cmd = (h.get("command") or "").strip()
                if "${CLAUDE_PLUGIN_ROOT}/" not in cmd:
                    continue
                if cmd.startswith(("python3", "python", "bash", "sh ")):
                    continue  # laeuft durch einen Interpreter, braucht kein +x
                rel = cmd.split("${CLAUDE_PLUGIN_ROOT}/", 1)[1].split('"')[0].split("'")[0].split()[0]
                p = Path(__file__).resolve().parent.parent / rel
                assert p.exists(), f"{ereignis}: registriert, aber nicht vorhanden: {rel}"
                assert p.stat().st_mode & 0o111, (
                    f"{ereignis}: {rel} wird DIREKT aufgerufen und ist nicht ausfuehrbar — "
                    "der Hook scheitert still, und nichts wird rot"
                )
