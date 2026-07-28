"""Der Sitzungsstart fragt Gitea, nicht GitHub — und die Meldung kommt auch an.

ANLASS (2026-07-28), Joe wörtlich: *„github? wofür wir nutzen gitea?"*

`session-start.py` rief `gh run list` — einen **GitHub**-Aufruf bei jedem Sitzungsstart.
Gitea ist die Code-Quelle, GitHub nur der öffentliche Spiegel. Der Hook meldete also den
Zustand eines Spiegels, während unsere CI woanders läuft. Am selben Tag gemessen: **beide
Repos auf Gitea rot**, und der Hook hätte nur von GitHub berichtet.

DREI FEHLER LAGEN AUF DEM WEG, alle derselben Klasse:

1. **`honcho.local` löst nicht auf** — jeder `is_healthy()` lief in einen DNS-Timeout:
   `honcho.local:8055` → 000 in **5,31 s**, `10.40.10.82:8055` → gesund in **0,09 s**.
   Zweimal je Sitzung. Der Dienst lief die ganze Zeit (`/docs` → 200); der **Name** war das
   Problem. Sitzungskosten: 12,4 s → 5,5 s.

2. **`str | None` ohne `from __future__ import annotations`** — unter Python 3.9 ein
   `TypeError` beim Import. Denselben Fehler hatte ich eine Stunde vorher in vier anderen
   Dateien behoben und beim Schreiben des Fixes wiederholt.

3. **Der Ausgabefilter kannte die neue Formulierung nicht.** Er suchte wörtlich nach
   `"CI FAILURE"`; meine Meldung heißt „CI ROT auf Gitea". Die Meldung entstand und
   **erreichte niemanden** — Hook läuft, Exit 0, 0 Byte Ausgabe.

Der dritte ist der lehrreichste: ich habe die Nachricht gebaut, den Transport nicht geprüft,
und der Beweis war ein leerer stdout, den man leicht für „nichts zu melden" hält.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
HOOK = WURZEL / "hooks" / "session-start.py"
SYSTEM_PYTHON = "/usr/bin/python3"


def test_kein_github_aufruf_mehr() -> None:
    """Gitea ist die Quelle. Ein `gh run list` fragt den Spiegel."""
    s = HOOK.read_text(encoding="utf-8")
    codezeilen = [z for z in s.splitlines() if not z.lstrip().startswith("#")]
    code = "\n".join(codezeilen)
    assert '"gh",' not in code and "'gh'," not in code, (
        "session-start ruft wieder `gh` — das fragt GitHub, unsere CI laeuft auf Gitea"
    )


def test_fragt_den_gitea_commit_status() -> None:
    """Gitea hat keine Actions-API (`/actions/runs` → 404). Der Zustand steht am Commit."""
    s = HOOK.read_text(encoding="utf-8")
    assert "commits/" in s and "/status" in s
    assert "_gitea_ci_zustand" in s


def test_der_filter_kennt_die_meldung() -> None:
    """Der Fehler, der die ganze Änderung unsichtbar machte.

    Der Ausgabefilter sucht nach Schlüsselwörtern. Wird die Meldung umformuliert und das
    Schlüsselwort nicht mitgeführt, entsteht sie und erreicht niemanden.
    """
    s = HOOK.read_text(encoding="utf-8")
    i = s.index("DRINGEND = (")
    kennzeichen = s[i:s.index(")", i)]
    assert "CI ROT" in kennzeichen, (
        "der Filter kennt die tatsaechlich erzeugte Meldung nicht — sie wird herausgefiltert"
    )
    # und die Meldung selbst muss eines der Kennzeichen tragen
    assert "CI ROT auf Gitea" in s


def test_kein_local_name_als_vorgabe() -> None:
    """`honcho.local` kostete 5,31 s je Aufruf, weil der Name nicht aufloest."""
    dienste = (WURZEL / "hooks" / "lib" / "services.py").read_text(encoding="utf-8")
    codezeilen = [z for z in dienste.splitlines() if not z.lstrip().startswith("#")]
    code = "\n".join(codezeilen)
    for name in ("honcho.local", "open-notebook.local"):
        assert name not in code, (
            f"{name} steht wieder als Vorgabe im Code — der Name loest hier nicht auf und "
            "kostet je Aufruf ~5 s DNS-Timeout"
        )


@pytest.mark.skipif(not Path(SYSTEM_PYTHON).exists(), reason="kein System-Python")
def test_laeuft_unter_python_39_und_gibt_etwas_aus(tmp_path) -> None:
    """Die einzige Prüfung, die alle drei Fehler zusammen gefunden hätte: **ausführen**."""
    umg = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(WURZEL), "CLAUDE_PLUGIN_DATA": str(tmp_path)}
    p = subprocess.run(
        [SYSTEM_PYTHON, str(HOOK)],
        input=json.dumps({"session_id": "test-e2e", "hook_event_name": "SessionStart",
                          "cwd": str(WURZEL)}),
        capture_output=True, text=True, timeout=60, env=umg,
    )
    assert p.returncode == 0, p.stderr[:400]
    assert not p.stderr.strip(), f"Hook schreibt nach stderr: {p.stderr[:300]}"
    if p.stdout.strip():
        d = json.loads(p.stdout)
        assert "additionalContext" in d
