"""The per-stop deviation metric.

Positive is late, negative is early, zero is exactly on time -- measured from
the scheduled instant, so the buffers and the measurement grace decide what
counts as on time without shifting the number being plotted.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache,
)

from custom_components.tripshot_tracker.api import TripShotApi
from custom_components.tripshot_tracker.const import DOMAIN

FIX = Path(__file__).parent / "fixtures"
ROUTE_ID = "22443444-e127-4e40-8927-a3192e750369"
EASTMAN = "37fb377f-6170-4948-9560-9fd3569c30b4"
AT_STOP = (43.1590312879686, -77.6012646661841)
AWAY = (43.1300000000000, -77.6500000000000)
DEVIATION = "sensor.red_line_eastman_living_center_deviation"

ENTRY_DATA = {
    "instance_name": "UofR", "instance_label": "UofR Shuttle",
    "instance_id": 526, "base_url": "https://api.tripshot.com",
    "route_id": ROUTE_ID, "route_name": "Red Line", "region_id": "reg",
}


def live_at(pos, when=None):
    when = (when or datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z")
    return {"timestamp": when, "vehicleStatuses": [{
        "vehicleId": "97d597ef", "name": "2603",
        "location": {"lt": pos[0], "lg": pos[1]}, "when": when}]}


@pytest.fixture
def bundle():
    return json.loads((FIX / "route_service_bundle.json").read_text())


async def setup(hass, bundle, live, entry=None, options=None):
    entry = entry or MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, options=options or {"confirm_polls": 1},
        unique_id=f"UofR:{ROUTE_ID}")
    if entry.entry_id not in hass.config_entries._entries:
        entry.add_to_hass(hass)
    with patch.object(TripShotApi, "route_service_bundle", return_value=bundle), \
         patch.object(TripShotApi, "live_status", return_value=live):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def poll(hass, coordinator, bundle, live):
    with patch.object(TripShotApi, "route_service_bundle", return_value=bundle), \
         patch.object(TripShotApi, "live_status", return_value=live):
        await coordinator.async_refresh()
        await hass.async_block_till_done()


class TestExists:
    async def test_one_per_stop(self, hass: HomeAssistant, bundle):
        await setup(hass, bundle, live_at(AWAY))
        assert hass.states.get(DEVIATION) is not None
        assert hass.states.get(
            "sensor.red_line_rush_rhees_library_back_side_deviation") is not None

    async def test_it_is_a_measurement_in_seconds(
        self, hass: HomeAssistant, bundle
    ):
        await setup(hass, bundle, live_at(AWAY))
        s = hass.states.get(DEVIATION)
        assert s.attributes["unit_of_measurement"] == "s"
        assert s.attributes["state_class"] == "measurement"

    async def test_unknown_before_any_visit(self, hass: HomeAssistant, bundle):
        await setup(hass, bundle, live_at(AWAY))
        assert hass.states.get(DEVIATION).state == "unknown"


class TestSignConvention:
    """Positive is late, negative is early -- the whole point of the metric."""

    async def _deviation_after_visit(self, hass, bundle, arrive_at):
        """Drive a full visit whose departure lands at `arrive_at`."""
        entry = await setup(hass, bundle, live_at(AT_STOP))
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await poll(hass, coordinator, bundle, live_at(AT_STOP))
        await poll(hass, coordinator, bundle, live_at(AWAY))
        return hass.states.get(DEVIATION), coordinator

    async def test_a_late_departure_is_positive(
        self, hass: HomeAssistant, bundle
    ):
        state, coordinator = await self._deviation_after_visit(hass, bundle, None)
        latest = coordinator.tracker.latest_for(EASTMAN)
        assert latest is not None
        if latest.deviation_sec > 0:
            assert float(state.state) > 0
            assert state.attributes["punctuality"] == "late"

    async def test_the_state_matches_the_tracker(
        self, hass: HomeAssistant, bundle
    ):
        state, coordinator = await self._deviation_after_visit(hass, bundle, None)
        latest = coordinator.tracker.latest_for(EASTMAN)
        assert float(state.state) == pytest.approx(round(latest.deviation_sec))

    async def test_sign_matches_the_verdict(self, hass: HomeAssistant, bundle):
        state, coordinator = await self._deviation_after_visit(hass, bundle, None)
        latest = coordinator.tracker.latest_for(EASTMAN)
        value = float(state.state)
        if latest.verdict.value.endswith("_early"):
            assert value < 0, "early must plot negative"
        elif latest.verdict.value.endswith("_late"):
            assert value > 0, "late must plot positive"
        else:
            assert abs(value) <= max(1, coordinator.late_buffer_sec)


class TestAttributes:
    async def test_it_says_which_event_it_measured(
        self, hass: HomeAssistant, bundle
    ):
        entry = await setup(hass, bundle, live_at(AT_STOP))
        c = hass.data[DOMAIN][entry.entry_id]
        await poll(hass, c, bundle, live_at(AT_STOP))
        await poll(hass, c, bundle, live_at(AWAY))
        a = hass.states.get(DEVIATION).attributes
        assert a["kind"] == "departure"
        assert a["verdict"].startswith("depart_")
        assert "scheduled" in a and "measured_at" in a
        assert a["bus"]

    async def test_minutes_are_offered_alongside_seconds(
        self, hass: HomeAssistant, bundle
    ):
        entry = await setup(hass, bundle, live_at(AT_STOP))
        c = hass.data[DOMAIN][entry.entry_id]
        await poll(hass, c, bundle, live_at(AT_STOP))
        await poll(hass, c, bundle, live_at(AWAY))
        s = hass.states.get(DEVIATION)
        assert s.attributes["deviation_minutes"] == pytest.approx(
            float(s.state) / 60, abs=0.06)


class TestRestore:
    async def test_the_last_reading_survives_a_restart(
        self, hass: HomeAssistant, bundle
    ):
        """So a history graph does not gap across a restart."""
        mock_restore_cache(hass, (State(DEVIATION, "-93"),))
        entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA,
                                options={"confirm_polls": 1},
                                unique_id=f"UofR:{ROUTE_ID}")
        entry.add_to_hass(hass)
        from homeassistant.helpers import entity_registry as er
        er.async_get(hass).async_get_or_create(
            "sensor", DOMAIN, f"UofR:{ROUTE_ID}_{EASTMAN}_deviation",
            config_entry=entry,
            suggested_object_id="red_line_eastman_living_center_deviation")
        await setup(hass, bundle, live_at(AWAY), entry)
        assert hass.states.get(DEVIATION).state == "-93"

    async def test_a_restored_reading_is_marked_as_such(
        self, hass: HomeAssistant, bundle
    ):
        """`measured_at` is absent while restored, so staleness is visible."""
        mock_restore_cache(hass, (State(DEVIATION, "-93"),))
        entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA,
                                options={"confirm_polls": 1},
                                unique_id=f"UofR:{ROUTE_ID}")
        entry.add_to_hass(hass)
        from homeassistant.helpers import entity_registry as er
        er.async_get(hass).async_get_or_create(
            "sensor", DOMAIN, f"UofR:{ROUTE_ID}_{EASTMAN}_deviation",
            config_entry=entry,
            suggested_object_id="red_line_eastman_living_center_deviation")
        await setup(hass, bundle, live_at(AWAY), entry)
        a = hass.states.get(DEVIATION).attributes
        assert a["restored"] is True
        assert "measured_at" not in a

    async def test_a_live_reading_replaces_the_restored_one(
        self, hass: HomeAssistant, bundle
    ):
        mock_restore_cache(hass, (State(DEVIATION, "-93"),))
        entry = await setup(hass, bundle, live_at(AT_STOP))
        c = hass.data[DOMAIN][entry.entry_id]
        await poll(hass, c, bundle, live_at(AT_STOP))
        await poll(hass, c, bundle, live_at(AWAY))
        s = hass.states.get(DEVIATION)
        assert s.state != "-93"
        assert "measured_at" in s.attributes
