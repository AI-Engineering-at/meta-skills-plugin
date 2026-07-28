"""Erreichbar ist nicht benutzbar — der Open-Notebook-401.

ANLASS (2026-07-28)
`hook-errors.log` trug seit Tagen dieselbe Zeile:

    HTTP 401 POST http://10.40.10.82:5055/api/search: {"detail":"Missing authorization header"}

Drei Fehler kamen zusammen, und jeder allein wäre unauffällig geblieben:

1. **`_http_request` konnte gar keinen Header senden.** Kein Parameter dafür, kein Aufruf,
   der einen gebraucht hätte — bis dieser eine.
2. **`vault_get` fand nie etwas.** Es liest `~/Documents/phantom-ai/.claude/credentials/vault.py`,
   und diese Datei **existiert nicht**. Jede Zugangsdaten-Suche im Plugin lieferte `None`
   und fiel auf eine Vorgabe zurück — lautlos.
3. **`is_healthy()` prüfte `/api/config`, benutzt wurde `/api/search`.** Der eine Endpunkt
   verlangt keine Auth und antwortete mit 200; der andere verlangt sie und antwortete mit
   401. Die Gesundheitsprüfung meldete „gesund" und **maß einen anderen Weg als den, der
   danach gegangen wurde**.

Ergebnis: jede Sitzung fragte Open-Notebook nach Wissen, bekam eine leere Liste, und das war
von „nichts gefunden" nicht zu unterscheiden. Nichts wurde rot.

Gemessen, welches Schema die API will — statt es zu raten:

    Authorization: Bearer <UI_PASSWORD>   -> 200
    Authorization: Token  <UI_PASSWORD>   -> 401
    Basic :<pw> / admin:<pw>              -> 401

Nach der Reparatur liefert `search_text("Brücke")` **drei echte Treffer**.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def services():
    sys.path.insert(0, str(WURZEL / "hooks"))
    spec = importlib.util.spec_from_file_location(
        "lib.services", WURZEL / "hooks" / "lib" / "services.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_http_request_kann_header_senden(services) -> None:
    """Der Kern: vorher gab es den Parameter nicht."""
    import inspect
    assert "headers" in inspect.signature(services._http_request).parameters


def test_vault_get_hat_einen_ausweichweg(services) -> None:
    """`vault.py` existiert nicht — ohne Ausweich liefert vault_get immer None."""
    assert hasattr(services, "_aie_vault_get")
    assert not services._VAULT_SCRIPT.exists(), (
        "vault.py existiert wieder — dann diesen Test und den Ausweichweg neu bewerten"
    )


def test_maskierte_vorschau_wird_abgelehnt(services, monkeypatch) -> None:
    """`aie-vault get` ohne `--raw` liefert „aie-nS1…R3Pm" — das ist kein Zugangsdatum.

    Es zu senden ergibt ein 401, das wie ein totes Token aussieht und keins ist.
    """
    class Lauf:
        stdout = "aie-nS1…R3Pm"
        returncode = 0
    monkeypatch.setattr(services.os, "access", lambda *a, **k: True)
    monkeypatch.setattr(services.subprocess, "run", lambda *a, **k: Lauf())
    assert services._aie_vault_get("open-notebook", "UI_PASSWORD") is None


def test_ohne_passwort_meldet_der_client_ungesund(services, monkeypatch) -> None:
    """Erreichbar und unbrauchbar ist ein eigener Zustand — und gehört benannt.

    Vorher hätte `is_healthy()` hier `True` gesagt (weil `/api/config` antwortet) und die
    Suche danach wäre leer zurückgekommen.
    """
    monkeypatch.setattr(services, "vault_get", lambda *a, **k: None)
    c = services.OpenNotebookClient(timeout=2.0)
    assert c._passwort is None
    assert c.is_healthy() is False


def test_der_kopf_traegt_bearer(services, monkeypatch) -> None:
    """Bearer, nicht Token, nicht Basic — gemessen, nicht geraten."""
    monkeypatch.setattr(services, "vault_get",
                        lambda a, s, k: "geheim" if k == "UI_PASSWORD" else None)
    c = services.OpenNotebookClient(timeout=2.0)
    assert c._kopf() == {"Authorization": "Bearer geheim"}


def test_is_healthy_prueft_den_benutzten_weg(services) -> None:
    """Die eigentliche Lehre: eine Prüfung, die einen anderen Endpunkt misst, prüft nichts.

    `/api/config` ist ohne Auth erreichbar, `/api/search` nicht. Solange die
    Gesundheitsprüfung den ersten nimmt, meldet sie „gesund", während der zweite 401 gibt.
    """
    import re
    quelle = (WURZEL / "hooks" / "lib" / "services.py").read_text(encoding="utf-8")
    i = quelle.index("def is_healthy", quelle.index("class OpenNotebookClient"))
    j = quelle.index("\n    def ", i + 10)
    # Docstring RAUS, bevor gesucht wird. Beim ersten Anlauf fiel dieser Test durch, weil
    # der Docstring erklaert, dass hier frueher `/api/config` stand — ein Test, der
    # Quelltext durchsucht, findet Kommentare mit. Er muss den CODE pruefen.
    abschnitt = re.sub(r'"""..*?"""', "", quelle[i:j], flags=re.DOTALL)
    assert "/api/search" in abschnitt, "is_healthy prueft wieder einen anderen Endpunkt"
    assert "/api/config" not in abschnitt, (
        "is_healthy prueft wieder /api/config — ein Endpunkt OHNE Auth-Pflicht, waehrend "
        "der benutzte 401 gibt"
    )


def test_alle_drei_aufrufe_senden_den_kopf(services) -> None:
    """Ein vergessener Aufruf reicht, damit die Luecke zurueckkommt."""
    quelle = (WURZEL / "hooks" / "lib" / "services.py").read_text(encoding="utf-8")
    n = quelle.count("headers=self._kopf()")
    assert n >= 3, f"nur {n} von 3 Aufrufen senden den Header"
