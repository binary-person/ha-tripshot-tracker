"""Load the integration's pure modules without importing Home Assistant.

`custom_components/tripshot_tracker/__init__.py` pulls in Home Assistant, and
`api.py`/`coordinator.py` pull in aiohttp and HA respectively. The modules
under test here — locality, tracker, models, const — depend on none of that.

Binding the package directory under a synthetic name gives their relative
imports (`from .locality import ...`) a package to resolve against, while
never executing the real `__init__.py`.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

PKG_DIR = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "tripshot_tracker"
)

if "tsx" not in sys.modules:
    pkg = types.ModuleType("tsx")
    pkg.__path__ = [str(PKG_DIR)]
    sys.modules["tsx"] = pkg


# --- Home Assistant integration tests ---------------------------------------
# pytest-homeassistant-custom-component registers itself as a plugin, so it
# needs no `pytest_plugins` declaration here — declaring one raises a
# double-registration error. All that is needed is to opt each Home Assistant
# test into loading custom_components/.
try:  # pragma: no cover - environment dependent
    import homeassistant  # noqa: F401
except ImportError:  # pragma: no cover
    pass
else:
    import pytest

    @pytest.fixture(autouse=True)
    def auto_enable_custom_integrations(request):
        """Let Home Assistant load custom_components/tripshot_tracker."""
        if "hass" in request.fixturenames:
            request.getfixturevalue("enable_custom_integrations")
        yield
