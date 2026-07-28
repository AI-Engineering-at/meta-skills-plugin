"""Eine ganze Sitzung durchspielen — so wie sie wirklich abläuft.

ANLASS (2026-07-28)
Joe: *„Was ist das für ein Test? Wo ist der Real-Life-Test wie ein User?"*

Er hat recht, und die Frage trifft eine echte Lücke. An diesem Tag sind **726 Tests**
entstanden, und **kein einziger** hat eine Sitzung durchgespielt. Alle prüfen Funktionen
einzeln — und genau deshalb sind fünf Fehler durchgerutscht, die jeder Einzeltest bestanden
hätte:

| Was kaputt war | Warum kein Unit-Test es fand |
|---|---|
| `token-audit` feuerte 9 statt 5433 mal | der Hook selbst war korrekt — die **Registrierung** war es nicht |
| `vault_get` fand nie etwas | die Funktion tat, was sie sollte — die **Datei** fehlte |
| `is_healthy` prüfte den falschen Endpunkt | beide Endpunkte antworteten, nur verschieden |
| `run-hook.cmd` nicht ausführbar | die Datei existierte, der **Modus** stimmte nicht |
| `exploration-first` „wirkungslos" | es *funktionierte* — ich hatte auf `deny` geprüft statt auf den Rat |

**Jeder dieser Fehler lebt zwischen den Bausteinen, nicht in ihnen.** Ein Unit-Test kann sie
nicht finden, weil er den Baustein isoliert — und isoliert war jeder in Ordnung.

WAS DIESER TEST TUT
Er spielt eine realistische Sitzung: Start, Eingabe, ein paar Werkzeugaufrufe, ein
Schreibversuch ohne vorheriges Lesen, dann Lesen und Schreiben, Ende. Danach wird geprüft,
was **beobachtbar** herausgekommen ist — nicht ob die Hooks mit 0 endeten.

Denn genau das war die Falle des Tages: **Exit 0 ist kein Beleg.** Mein eigener geplanter
Prüfpunkt lautete wörtlich „wächst `token-audit.jsonl`?". Die Antwort war ja, und sie war
wertlos — neun Datensätze mit `tool: "unknown"` sind kein Audit.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
SITZUNG = "e2e-echte-sitzung"


def hook(name: str, nutzlast: dict, daten: Path) -> subprocess.CompletedProcess:
    """Einen Hook so aufrufen, wie Claude Code es tut: JSON auf stdin."""
    return subprocess.run(
        ["python3", str(WURZEL / "hooks" / name)],
        input=json.dumps(nutzlast),
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ,
             "CLAUDE_PLUGIN_ROOT": str(WURZEL),
             "CLAUDE_PLUGIN_DATA": str(daten)},
    )


def werkzeug(name: str, eingabe: dict, ereignis: str, ausgabe: str = "") -> dict:
    """Eine Nutzlast in der Form, die die Dokumentation vorgibt."""
    return {
        "session_id": SITZUNG,
        "prompt_id": "p-1",
        "tool_name": name,
        "tool_input": eingabe,
        "tool_output": ausgabe,
        "tool_use_id": "toolu_e2e",
        "transcript_path": "/dev/null",
        "cwd": str(WURZEL),
        "permission_mode": "default",
        "hook_event_name": ereignis,
    }


@pytest.fixture(scope="module")
def gelaufene_sitzung(tmp_path_factory) -> Path:
    """Spielt die Sitzung EINMAL und gibt das Datenverzeichnis zurück."""
    daten = tmp_path_factory.mktemp("plugin-daten")

    hook("session-init.py", {"session_id": SITZUNG, "prompt": "Baue mir X",
                             "hook_event_name": "UserPromptSubmit", "cwd": str(WURZEL)}, daten)

    # Drei Bash-Aufrufe, jeweils Pre und Post — wie in echter Arbeit.
    for befehl in ("ls -la", "grep -rn muster .", "python3 -m pytest -q"):
        hook("pre-bash-kedb-vorhalt.py", werkzeug("Bash", {"command": befehl}, "PreToolUse"), daten)
        hook("token-audit.py", werkzeug("Bash", {"command": befehl}, "PostToolUse",
                                        "ausgabe-zeile-1\nausgabe-zeile-2"), daten)

    # Schreiben OHNE vorheriges Lesen — hier muss der Rat kommen.
    ohne_lesen = hook("exploration-first.py",
                      werkzeug("Write", {"file_path": "/tmp/neu.py", "content": "x = 1"},
                               "PreToolUse"), daten)

    # Jetzt lesen, dann schreiben — hier muss er schweigen.
    for _ in range(3):
        hook("exploration-first.py",
             werkzeug("Read", {"file_path": str(WURZEL / "README.md")}, "PreToolUse"), daten)
        hook("token-audit.py",
             werkzeug("Read", {"file_path": str(WURZEL / "README.md")}, "PostToolUse",
                      "inhalt"), daten)
    nach_lesen = hook("exploration-first.py",
                      werkzeug("Write", {"file_path": "/tmp/neu.py", "content": "x = 1"},
                               "PreToolUse"), daten)

    hook("session-stop.py", {"session_id": SITZUNG, "hook_event_name": "Stop",
                             "cwd": str(WURZEL)}, daten)
    subprocess.run(["bash", str(WURZEL / "hooks" / "on-stop.sh")],
                   input="{}", capture_output=True, text=True, timeout=30,
                   env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(WURZEL),
                        "CLAUDE_PLUGIN_DATA": str(daten)})

    (daten / ".e2e-ohne-lesen").write_text(ohne_lesen.stdout, encoding="utf-8")
    (daten / ".e2e-nach-lesen").write_text(nach_lesen.stdout, encoding="utf-8")
    return daten


# ----------------------------------------------------------------- was herausgekommen ist

def test_das_token_audit_kennt_die_echten_werkzeuge(gelaufene_sitzung: Path) -> None:
    """DER Test, den es heute früh gebraucht hätte.

    `token-audit.jsonl` wuchs — und trug neun Zeilen `tool: "unknown"`. Die Datei zu zählen
    hätte „ja, wächst" gesagt. Hier wird der INHALT geprüft.
    """
    datei = gelaufene_sitzung / "token-audit.jsonl"
    assert datei.exists(), "token-audit.jsonl wurde ueberhaupt nicht geschrieben"

    zeilen = [json.loads(z) for z in datei.read_text(encoding="utf-8").splitlines() if z.strip()]
    assert len(zeilen) >= 6, f"nur {len(zeilen)} Eintraege fuer 6 Werkzeugaufrufe"

    unbekannt = [z for z in zeilen if z.get("tool") == "unknown"]
    assert not unbekannt, (
        f"{len(unbekannt)} von {len(zeilen)} Eintraegen haben tool='unknown' — die Nutzlast "
        "kommt nicht an. Genau das war der Zustand vor dem matcher-Fix, und die Datei wuchs "
        "trotzdem."
    )
    assert {z["tool"] for z in zeilen} >= {"Bash", "Read"}
    assert all(z.get("session") == SITZUNG for z in zeilen), (
        "die Sitzungs-ID kommt nicht durch — der Verlauf ist dann keiner Sitzung zuzuordnen"
    )


def test_die_bash_befehle_stehen_wirklich_drin(gelaufene_sitzung: Path) -> None:
    """Ein Audit ohne den Befehl beantwortet die Frage nicht, für die es da ist."""
    zeilen = [json.loads(z) for z in
              (gelaufene_sitzung / "token-audit.jsonl").read_text(encoding="utf-8").splitlines()
              if z.strip()]
    befehle = {z.get("command", "") for z in zeilen if z.get("tool") == "Bash"}
    assert any("pytest" in b for b in befehle), befehle
    assert all(z.get("input_bytes", 0) > 2 for z in zeilen if z.get("tool") == "Bash"), (
        "input_bytes = 2 heisst: leeres Objekt angekommen"
    )


def test_der_rat_kommt_wenn_ohne_lesen_geschrieben_wird(gelaufene_sitzung: Path) -> None:
    """Beratend, nicht blockierend — so steht es im Docstring des Hooks.

    Ich hatte ihn als „registriert und wirkungslos" geführt, weil ich auf `deny` geprüft
    habe. Er blockiert absichtlich nicht. **Die Prüfung muss dieselbe Frage stellen wie die
    Behauptung** — hier also: kommt der Rat?
    """
    aus = (gelaufene_sitzung / ".e2e-ohne-lesen").read_text(encoding="utf-8").strip()
    assert aus, "kein Rat bei einem Schreibversuch ohne jedes Lesen"
    d = json.loads(aus)
    assert "additionalContext" in d
    assert "READING" in d["additionalContext"].upper()


def test_nach_drei_reads_schweigt_er(gelaufene_sitzung: Path) -> None:
    """Ein Hinweis, der immer kommt, ist Rauschen und wird überlesen."""
    aus = (gelaufene_sitzung / ".e2e-nach-lesen").read_text(encoding="utf-8").strip()
    assert not aus, f"Rat kommt auch nach drei Reads: {aus[:120]}"


def test_der_sitzungszustand_liegt_unter_der_echten_id(gelaufene_sitzung: Path) -> None:
    """`.meta-state-unknown.json` war heute der Beleg dafür, dass die ID nicht ankommt.

    Landen alle Sitzungen im selben „unknown"-Topf, ist der Zustand wertlos: er vermischt,
    was getrennt gehört.
    """
    dateien = list(gelaufene_sitzung.glob(".meta-state-*.json"))
    assert dateien, "kein Sitzungszustand geschrieben"
    namen = {p.name for p in dateien}
    assert f".meta-state-{SITZUNG}.json" in namen, namen
    assert ".meta-state-unknown.json" not in namen, (
        "der Zustand landete unter 'unknown' — die Sitzungs-ID kommt nicht an"
    )


def test_der_stop_hook_hat_wirklich_geschrieben(gelaufene_sitzung: Path) -> None:
    """`run-hook.cmd` endete auf dem Mac mit „permission denied" und tat nichts.

    Ein Test auf den Exit-Code hätte das nicht gefunden — die aufrufende Shell meldete 0.
    """
    metriken = gelaufene_sitzung / "session-metrics.jsonl"
    assert metriken.exists(), "session-metrics.jsonl fehlt — der Stop-Hook lief nicht"
    assert metriken.stat().st_size > 0, "session-metrics.jsonl ist leer"


def test_kein_hook_hat_sich_beschwert(gelaufene_sitzung: Path) -> None:
    """`hook-errors.log` ist der Kanal, in dem die Hooks selbst Alarm schlagen.

    Er trug heute tagelang dieselbe 401-Zeile, ohne dass jemand hinsah. Nach einer sauberen
    Sitzung gehört er leer.
    """
    log = gelaufene_sitzung / "hook-errors.log"
    if not log.exists():
        return
    zeilen = [z for z in log.read_text(encoding="utf-8").splitlines() if z.strip()]
    assert not zeilen, "Hooks haben Fehler protokolliert:\n  " + "\n  ".join(zeilen[:5])
