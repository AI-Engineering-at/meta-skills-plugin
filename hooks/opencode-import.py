#!/usr/bin/env python3
"""Hook: OpenCode-Verbrauch an die Brücke schicken (SessionEnd).

WARUM ALS HOOK UND NICHT ALS launchd-JOB
Joes Auflage vom 2026-07-28, wörtlich: *„keine Skripte und Dinge auf dem Mac, die die ganze
Zeit laufen müssen."* Auf diesem Mac liegen bereits **41 launchd-Jobs**, von denen zehn
scheitern und neunzehn nur Fremd-Dienste proben — die gehören in den Cluster, nicht hierher.

Der OpenCode-Import kann aber nicht in den Cluster: `~/.local/share/opencode/opencode.db`
liegt hier, 288 MB, und dort gibt es sie nicht.

**Ein `SessionEnd`-Hook löst genau das.** Er läuft, wenn Claude Code läuft — also wenn der Mac
ohnehin wach ist und jemand daran arbeitet. Kein Dauerläufer, kein Timer, nichts, das im
Hintergrund Strom zieht oder beim Aufwachen nachholt.

WAS ER TUT
Ruft `scripts/import_opencode_usage.py` aus dem Brücken-Repo auf — **nicht mehr als einmal
alle sechs Stunden**. Ein Import je Sitzung wäre Verschwendung: die Zahlen ändern sich nicht
schneller, als OpenCode benutzt wird.

WAS ER NICHT TUT
Er blockiert nichts und meldet nichts nach außen. Fehlt das Skript, fehlt der Token oder ist
die Brücke nicht erreichbar, endet er still — genau wie heute schon, nur dass es jetzt
**vermerkt** wird statt spurlos zu bleiben. Ein Sitzungsende ist der falsche Ort für einen
Alarm.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HOOK_NAME = "opencode_import"

PLUGIN_DATA = Path(
    os.environ.get(
        "CLAUDE_PLUGIN_DATA",
        Path.home() / ".claude" / "plugins" / "data" / "meta-skills",
    )
)
MARKE = PLUGIN_DATA / ".opencode-import-zuletzt"
PROTOKOLL = PLUGIN_DATA / "opencode-import.jsonl"

# Sechs Stunden. Kurz genug, dass eine Tagesarbeit noch am selben Tag ankommt; lang genug,
# dass zwanzig kurze Sitzungen nicht zwanzig Importe ausloesen.
ABSTAND_SEKUNDEN = 6 * 3600

BRUECKE = Path.home() / "code-aie" / "phantom-neural-cortex-llm-bridge"
SKRIPT = BRUECKE / "scripts" / "import_opencode_usage.py"
DATENBANK = Path.home() / ".local" / "share" / "opencode" / "opencode.db"


def interpreter() -> str:
    """Die venv der Brücke, sonst `python3`.

    Der erste Lauf dieses Hooks scheiterte mit
    `ImportError: cannot import name 'UTC' from 'datetime'` — das Import-Skript zieht
    Brücken-Module, und die brauchen **3.11+**. Ein Hook läuft aber unter blankem `python3`,
    und das ist auf diesem Mac **3.9.6**.

    Genau die Fehlerklasse, für die im Plugin-CI eine 3.9-Matrix steht: der Code ist richtig,
    der Interpreter ist der falsche. Ohne diesen Umweg hätte der Hook bei jedem Sitzungsende
    still verloren — und das Protokoll hätte „nicht gesendet" gesagt, ohne dass jemand den
    Grund liest.
    """
    venv = BRUECKE / ".venv" / "bin" / "python"
    if os.access(venv, os.X_OK):
        return str(venv)
    return "python3"


def vermerk(zustand: str, detail: str = "") -> None:
    """Was passiert ist — damit „lief nicht" von „lief und fand nichts" unterscheidbar bleibt.

    Genau diese Unterscheidung hat heute dreimal gefehlt: ein Hook, der still nichts tut,
    sieht aus wie einer, der nichts zu tun hatte.
    """
    try:
        PLUGIN_DATA.mkdir(parents=True, exist_ok=True)
        with PROTOKOLL.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), "zustand": zustand, "detail": detail[:300]},
                               ensure_ascii=False) + "\n")
    except OSError:
        pass


def zu_frueh() -> bool:
    try:
        return (time.time() - float(MARKE.read_text(encoding="utf-8").strip())) < ABSTAND_SEKUNDEN
    except (OSError, ValueError):
        return False


def main() -> None:
    # stdin leeren, damit der aufrufende Prozess nicht blockiert.
    try:
        sys.stdin.read()
    except Exception:
        pass

    if not DATENBANK.is_file():
        vermerk("uebersprungen", "keine OpenCode-Datenbank auf diesem Rechner")
        sys.exit(0)
    if not SKRIPT.is_file():
        vermerk("uebersprungen", f"Import-Skript fehlt: {SKRIPT}")
        sys.exit(0)
    if zu_frueh():
        # Auch DIESER Fall gehoert ins Protokoll.
        #
        # Gefunden am 2026-07-28 von `local/bonsai` ueber `scripts/delegiere.py pruefen` —
        # dem ersten Agenten-Befund, der einen echten Fehler in frischem Code traf. Sein
        # Argument war exakt richtig: der Docstring dieses Hooks verspricht, dass ein
        # Nicht-Senden „vermerkt wird statt spurlos zu bleiben" — und ausgerechnet der
        # haeufigste Fall (Drosselung) blieb spurlos. Wer das Protokoll liest, konnte
        # „laeuft nicht" nicht von „laeuft und wartet ab" unterscheiden.
        vermerk("gedrosselt", f"letzter Lauf < {ABSTAND_SEKUNDEN // 3600} h her")
        sys.exit(0)

    try:
        p = subprocess.run(
            [interpreter(), str(SKRIPT)],
            capture_output=True, text=True, timeout=180,
        )
    except subprocess.TimeoutExpired:
        vermerk("abgebrochen", "180s ueberschritten")
        sys.exit(0)
    except Exception as exc:
        vermerk("fehler", f"{type(exc).__name__}: {exc}")
        sys.exit(0)

    # Marke NUR bei Erfolg setzen. Sonst wuerde ein kaputter Lauf den naechsten Versuch
    # sechs Stunden lang verhindern — und der Fehler saesse aus, statt sich zu zeigen.
    if p.returncode == 0:
        try:
            MARKE.write_text(str(time.time()), encoding="utf-8")
        except OSError:
            pass
        vermerk("gesendet", (p.stdout or "").strip().splitlines()[-1][:200] if p.stdout else "")
    else:
        # Exit 5 = kein Admin-Token. Das ist heute der Normalzustand (V-TOKEN hat 0 Zeichen)
        # und kein Fehler des Hooks — er gehoert benannt, nicht als Stoerung gemeldet.
        grund = "kein Admin-Token gesetzt (V-TOKEN)" if p.returncode == 5 else \
                (p.stderr or "").strip().splitlines()[-1][:200] if p.stderr else f"exit {p.returncode}"
        vermerk("nicht gesendet", grund)

    sys.exit(0)


if __name__ == "__main__":
    main()
