"""Gemeinsamer Lader fuer die design-*-Werkzeuge.

Die Skripte heissen `design-lint.py` mit Bindestrich — das ist kein gueltiger
Modulname, also geht `import design_lint` nicht. Statt die Dateien umzubenennen
(und damit die Aufrufe in hooks.json, CI und Dokumentation zu brechen), werden
sie hier ueber den Dateipfad geladen. Ein Lader an einer Stelle statt derselbe
importlib-Block in zehn Testdateien.
"""

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
DESIGN_SYSTEM = REPO / "design-system"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def lade(name):
    """Laedt scripts/<name>.py als Modul, auch mit Bindestrich im Namen."""
    pfad = SCRIPTS / ("%s.py" % name)
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), pfad)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
