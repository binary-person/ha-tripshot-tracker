"""The shipped examples must reference things that actually exist.

A dashboard card pointing at a mistyped entity renders empty, and an
automation filtering on a value the integration never emits simply never
fires. Both fail silently, which is the worst way for documentation to be
wrong -- so the examples are checked against a real setup rather than trusted.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

yaml = pytest.importorskip("yaml")

from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.helpers import entity_registry as er  # noqa: E402
from pytest_homeassistant_custom_component.common import (  # noqa: E402
    MockConfigEntry,
)

from custom_components.tripshot_tracker.api import TripShotApi  # noqa: E402
from custom_components.tripshot_tracker.const import (  # noqa: E402
    DOMAIN,
    EVENT_VERDICT,
)
from custom_components.tripshot_tracker.locality import (  # noqa: E402
    COUNTED_STATES,
)

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
FIX = Path(__file__).parent / "fixtures"
ROUTE_ID = "22443444-e127-4e40-8927-a3192e750369"


def _entity_ids(node, found: set[str]) -> set[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "entity" and isinstance(value, str):
                found.add(value)
            else:
                _entity_ids(value, found)
    elif isinstance(node, list):
        for item in node:
            _entity_ids(item, found)
    elif isinstance(node, str):
        found.update(re.findall(r"sensor\.[a-z0-9_]+", node))
    return found


@pytest.fixture
async def created_entity_ids(hass: HomeAssistant) -> set[str]:
    bundle = json.loads((FIX / "route_service_bundle.json").read_text())
    live = json.loads((FIX / "live_status.json").read_text())
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=f"UofR:{ROUTE_ID}", options={},
        data={"instance_name": "UofR", "instance_id": 526,
              "base_url": "https://api.tripshot.com", "route_id": ROUTE_ID,
              "route_name": "Red Line", "region_id": "reg"})
    entry.add_to_hass(hass)
    with patch.object(TripShotApi, "route_service_bundle", return_value=bundle), \
         patch.object(TripShotApi, "live_status", return_value=live):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return {e.entity_id for e in er.async_entries_for_config_entry(
        er.async_get(hass), entry.entry_id)}


class TestDashboard:
    def test_it_parses(self):
        yaml.safe_load((EXAMPLES / "dashboard.yaml").read_text())

    async def test_every_entity_it_references_exists(self, created_entity_ids):
        referenced = _entity_ids(
            yaml.safe_load((EXAMPLES / "dashboard.yaml").read_text()), set())
        assert referenced, "the example references no entities at all"
        missing = sorted(referenced - created_entity_ids)
        assert not missing, f"referenced but never created: {missing}"


class TestAutomations:
    def test_it_is_a_bare_list(self):
        """automations.yaml takes a list; the `automation:` key belongs in
        configuration.yaml, and getting it wrong fails on paste."""
        loaded = yaml.safe_load((EXAMPLES / "automations.yaml").read_text())
        assert isinstance(loaded, list), type(loaded).__name__

    def test_every_automation_is_complete(self):
        for a in yaml.safe_load((EXAMPLES / "automations.yaml").read_text()):
            for key in ("id", "alias", "triggers", "actions"):
                assert key in a, f"{a.get('id', a)} is missing {key}"

    def test_ids_are_unique(self):
        ids = [a["id"] for a in
               yaml.safe_load((EXAMPLES / "automations.yaml").read_text())]
        assert len(ids) == len(set(ids)), "duplicate automation ids"

    def test_event_triggers_use_the_real_event_type(self):
        for a in yaml.safe_load((EXAMPLES / "automations.yaml").read_text()):
            for t in a["triggers"]:
                if t.get("trigger") == "event":
                    assert t["event_type"] == EVENT_VERDICT, t

    def test_filtered_verdicts_are_ones_the_integration_emits(self):
        """A filter on a verdict that never fires is a silent no-op."""
        valid = {s.value for s in COUNTED_STATES}
        for a in yaml.safe_load((EXAMPLES / "automations.yaml").read_text()):
            for t in a["triggers"]:
                verdict = (t.get("event_data") or {}).get("verdict")
                if verdict is not None:
                    assert verdict in valid, f"{a['id']}: unknown verdict {verdict}"

    def test_filtered_event_keys_are_ones_the_event_carries(self):
        carried = {"entry_id", "route", "route_id", "stop", "stop_id", "verdict",
                   "kind", "punctuality", "bus", "vehicle_id", "scheduled",
                   "actual", "deviation_seconds", "deviation_minutes"}
        for a in yaml.safe_load((EXAMPLES / "automations.yaml").read_text()):
            for t in a["triggers"]:
                for key in (t.get("event_data") or {}):
                    assert key in carried, f"{a['id']}: event has no key {key!r}"

    async def test_referenced_entities_exist(self, created_entity_ids):
        """The counter-based and numeric-state examples name real entities."""
        referenced = _entity_ids(
            yaml.safe_load((EXAMPLES / "automations.yaml").read_text()), set())
        missing = sorted(referenced - created_entity_ids)
        assert not missing, f"referenced but never created: {missing}"
