"""The pure modules must stay pure.

Their purity is what lets the logic be tested without a Home Assistant
install, and it is easy to lose by adding one convenient import. Asserted here
rather than described in a document, so it cannot quietly stop being true.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE = (Path(__file__).resolve().parent.parent
           / "custom_components" / "tripshot_tracker")

#: Modules that must import neither Home Assistant nor an HTTP client.
PURE_MODULES = [
    "const.py",
    "endpoints.py",
    "locality.py",
    "models.py",
    "observations.py",
    "overrides.py",
    "schedule.py",
    "tracker.py",
]

HEAVY = {"homeassistant", "aiohttp", "voluptuous", "requests"}


def top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module.split(".")[0])
    return found


@pytest.mark.parametrize("module", PURE_MODULES)
def test_pure_module_has_no_heavy_imports(module):
    offenders = top_level_imports(PACKAGE / module) & HEAVY
    assert not offenders, (
        f"{module} imports {sorted(offenders)}; move the logic that needs it "
        f"into coordinator.py or sensor.py, or the tests can no longer run "
        f"without Home Assistant"
    )


def test_the_pure_list_is_complete():
    """Every module that *is* pure should be listed, so the list stays honest."""
    actual = {
        f.name for f in PACKAGE.glob("*.py")
        if not (top_level_imports(f) & HEAVY) and f.name != "__init__.py"
    }
    assert actual == set(PURE_MODULES), (
        f"PURE_MODULES is out of date: {sorted(actual ^ set(PURE_MODULES))}")


def test_pure_modules_do_not_import_impure_siblings():
    impure = {"api", "coordinator", "sensor", "config_flow", "diagnostics"}
    for module in PURE_MODULES:
        tree = ast.parse((PACKAGE / module).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level > 0 and node.module:
                assert node.module.split(".")[0] not in impure, (
                    f"{module} imports the impure sibling {node.module}")
