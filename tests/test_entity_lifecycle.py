"""Entity lifecycle: unique-id migration, counter restore, dynamic stops.

__init__.py and sensor.py had untested paths that only run on a second
startup -- exactly the ones a user hits and a fresh test never does.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache_with_extra_data,
)

from custom_components.tripshot_tracker.api import TripShotApi
from custom_components.tripshot_tracker.const import DOMAIN

FIX = Path(__file__).parent / "fixtures"
ROUTE_ID = "22443444-e127-4e40-8927-a3192e750369"
EASTMAN = "37fb377f-6170-4948-9560-9fd3569c30b4"
ENTRY_DATA = {
    "instance_name": "UofR", "instance_label": "UofR Shuttle",
    "instance_id": 526, "base_url": "https://api.tripshot.com",
    "route_id": ROUTE_ID, "route_name": "Red Line", "region_id": "reg",
}


@pytest.fixture
def bundle():
    return json.loads((FIX / "route_service_bundle.json").read_text())


@pytest.fixture
def live():
    d = json.loads((FIX / "live_status.json").read_text())
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    d["timestamp"] = now
    for v in d.get("vehicleStatuses", []):
        v["when"] = now
    return d


async def setup(hass, bundle, live, entry=None):
    entry = entry or MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, options={}, unique_id=f"UofR:{ROUTE_ID}")
    if entry.entry_id not in hass.config_entries._entries:
        entry.add_to_hass(hass)
    with patch.object(TripShotApi, "route_service_bundle", return_value=bundle), \
         patch.object(TripShotApi, "live_status", return_value=live):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


class TestUniqueIdMigration:
    async def test_entry_id_keyed_entities_are_rekeyed(
        self, hass: HomeAssistant, bundle, live
    ):
        """Old entities keep their entity_id, history and counters."""
        entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, options={},
                                unique_id=f"UofR:{ROUTE_ID}")
        entry.add_to_hass(hass)

        registry = er.async_get(hass)
        old = registry.async_get_or_create(
            "sensor", DOMAIN, f"{entry.entry_id}_{EASTMAN}_depart_early",
            config_entry=entry, suggested_object_id="legacy_depart_early",
        )
        assert old.unique_id.startswith(entry.entry_id)

        await setup(hass, bundle, live, entry)

        migrated = registry.async_get(old.entity_id)
        assert migrated is not None, "the entity was dropped instead of migrated"
        assert migrated.unique_id == f"UofR:{ROUTE_ID}_{EASTMAN}_depart_early"
        assert migrated.entity_id == old.entity_id, "entity_id must not change"

    async def test_new_entities_use_the_stable_key(
        self, hass: HomeAssistant, bundle, live
    ):
        entry = await setup(hass, bundle, live)
        ids = {e.unique_id for e in er.async_entries_for_config_entry(
            er.async_get(hass), entry.entry_id)}
        assert all(i.startswith(f"UofR:{ROUTE_ID}") for i in ids), sorted(ids)[:3]

    async def test_migration_is_idempotent(self, hass: HomeAssistant, bundle, live):
        entry = await setup(hass, bundle, live)
        before = {e.unique_id for e in er.async_entries_for_config_entry(
            er.async_get(hass), entry.entry_id)}
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        after = {e.unique_id for e in er.async_entries_for_config_entry(
            er.async_get(hass), entry.entry_id)}
        assert before == after


class TestCounterRestore:
    async def test_a_counter_is_restored_from_extra_data(
        self, hass: HomeAssistant, bundle, live
    ):
        """The path that survives a restart during an API outage."""
        from homeassistant.core import State
        from homeassistant.helpers.restore_state import RestoredExtraData

        eid = "sensor.red_line_eastman_living_center_depart_early"
        mock_restore_cache_with_extra_data(
            hass, ((State(eid, "unavailable"), {"count": 7}),))

        entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, options={},
                                unique_id=f"UofR:{ROUTE_ID}")
        entry.add_to_hass(hass)
        registry = er.async_get(hass)
        registry.async_get_or_create(
            "sensor", DOMAIN, f"UofR:{ROUTE_ID}_{EASTMAN}_depart_early",
            config_entry=entry, suggested_object_id=
            "red_line_eastman_living_center_depart_early")

        await setup(hass, bundle, live, entry)
        assert hass.states.get(eid).state == "7", \
            "counter was not restored from extra data"

    async def test_an_unavailable_state_alone_does_not_zero_it(
        self, hass: HomeAssistant, bundle, live
    ):
        """Extra data is stored independently of the state string."""
        from homeassistant.core import State
        eid = "sensor.red_line_eastman_living_center_arrive_late"
        mock_restore_cache_with_extra_data(
            hass, ((State(eid, "unavailable"), {"count": 3}),))
        entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, options={},
                                unique_id=f"UofR:{ROUTE_ID}")
        entry.add_to_hass(hass)
        er.async_get(hass).async_get_or_create(
            "sensor", DOMAIN, f"UofR:{ROUTE_ID}_{EASTMAN}_arrive_late",
            config_entry=entry, suggested_object_id=
            "red_line_eastman_living_center_arrive_late")
        await setup(hass, bundle, live, entry)
        assert hass.states.get(eid).state == "3"


class TestAttributes:
    async def test_stop_state_exposes_position_context(
        self, hass: HomeAssistant, bundle, live
    ):
        await setup(hass, bundle, live)
        s = hass.states.get("sensor.red_line_eastman_living_center_current_state")
        assert s is not None
        assert "latitude" in s.attributes and "longitude" in s.attributes
        assert s.attributes["geofence_radius_m"] == pytest.approx(76.2, abs=0.1)

    async def test_counter_attributes_name_the_verdict(
        self, hass: HomeAssistant, bundle, live
    ):
        await setup(hass, bundle, live)
        s = hass.states.get("sensor.red_line_eastman_living_center_depart_early")
        assert s.attributes["verdict"] == "depart_early"
        assert s.attributes["stop_id"] == EASTMAN

    async def test_buses_lists_the_vehicles(self, hass: HomeAssistant, bundle, live):
        await setup(hass, bundle, live)
        s = hass.states.get("sensor.red_line_buses")
        assert s.attributes["buses"] == ["2603"]


class TestDynamicStops:
    async def test_a_new_stop_gains_entities_without_a_reload(
        self, hass: HomeAssistant, bundle, live
    ):
        entry = await setup(hass, bundle, live)
        before = len(er.async_entries_for_config_entry(
            er.async_get(hass), entry.entry_id))

        extended = json.loads(json.dumps(bundle))
        extended["routeServices"][0]["vias"].append({"ViaStop": {"stop": {
            "stopId": "new-stop", "name": "New Stop",
            "location": {"lt": 43.14, "lg": -77.61}}}})

        coordinator = hass.data[DOMAIN][entry.entry_id]
        coordinator._schedule_fetched = None          # force a schedule refresh
        with patch.object(TripShotApi, "route_service_bundle", return_value=extended), \
             patch.object(TripShotApi, "live_status", return_value=live):
            await coordinator.async_refresh()
            await hass.async_block_till_done()

        after = len(er.async_entries_for_config_entry(
            er.async_get(hass), entry.entry_id))
        assert after == before + 9, \
            "expected 6 counters + state + two deviations for the new stop"
        assert hass.states.get("sensor.red_line_new_stop_depart_early") is not None

    async def test_a_vanished_stop_keeps_its_entities(
        self, hass: HomeAssistant, bundle, live
    ):
        """Entities are never removed on what may be a transient absence."""
        entry = await setup(hass, bundle, live)
        reduced = json.loads(json.dumps(bundle))
        reduced["routeServices"][0]["vias"] = [
            v for v in reduced["routeServices"][0]["vias"]
            if not (isinstance(v, dict) and "ViaStop" in v
                    and v["ViaStop"]["stop"]["stopId"] == EASTMAN)
        ]
        coordinator = hass.data[DOMAIN][entry.entry_id]
        coordinator._schedule_fetched = None
        with patch.object(TripShotApi, "route_service_bundle", return_value=reduced), \
             patch.object(TripShotApi, "live_status", return_value=live):
            await coordinator.async_refresh()
            await hass.async_block_till_done()
        assert hass.states.get(
            "sensor.red_line_eastman_living_center_depart_early") is not None
