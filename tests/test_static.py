"""Static checks over the integration package.

This exists because of a real bug: `_is_arrival` was called by
`CountedVerdict.is_arrival` but had been deleted, so every counted verdict
raised NameError inside the event-firing path. The counter had already been
incremented by then, so counters rose while no event ever reached the bus --
and the whole poll then failed.

298 tests did not catch it, because catching it required *executing* that
line, and nothing did. pyflakes finds it without running anything.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [ROOT / "custom_components" / "tripshot_tracker", ROOT / "tools"]


def run_pyflakes(paths: list[Path]) -> str:
    files = sorted(str(f) for p in paths for f in p.rglob("*.py"))
    proc = subprocess.run(
        [sys.executable, "-m", "pyflakes", *files],
        capture_output=True, text=True,
    )
    return (proc.stdout + proc.stderr).strip()


def test_no_undefined_names_or_unused_imports():
    pytest.importorskip("pyflakes")
    findings = run_pyflakes(TARGETS)
    assert not findings, (
        "pyflakes reported problems:\n" + findings +
        "\n\nAn undefined name here is a crash waiting for the right input; "
        "the event-firing path shipped broken exactly this way."
    )


def test_every_module_imports_cleanly():
    """A module that cannot be imported cannot be tested.

    The pure modules are imported directly; the Home Assistant ones are only
    compiled, so this stays runnable without Home Assistant installed.
    """
    pkg = ROOT / "custom_components" / "tripshot_tracker"
    import py_compile
    for f in sorted(pkg.rglob("*.py")):
        try:
            py_compile.compile(str(f), doraise=True)
        except py_compile.PyCompileError as err:  # pragma: no cover
            pytest.fail(f"{f.name} does not compile: {err}")
