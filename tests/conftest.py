"""Pytest configuration — subprocess coverage tracking.

When tests spawn subprocess-invocations of hooks (the dominant pattern for
hook tests because hooks read stdin and exit), coverage.py cannot follow
those children by default. Setting COVERAGE_PROCESS_START lets any Python
subprocess auto-instrument on startup (via coverage's sitecustomize hook).

See: https://coverage.readthedocs.io/en/latest/subprocess.html
"""
import os
from pathlib import Path

COVERAGERC = Path(__file__).resolve().parent.parent / ".coveragerc"

if COVERAGERC.exists():
    os.environ.setdefault("COVERAGE_PROCESS_START", str(COVERAGERC))
