"""The diagnostics dump.

diagnostics.py was 0% covered -- never executed by anything. It is the first
thing anyone reaches for when the counters look wrong, so a traceback there
lands at the worst possible moment.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tripshot_tracker.api import TripShotApi
from custom_components.tripshot_tracker.const import DOMAIN
from custom_components.tripshot_tracker.diagnostics import (
    async_get_config_entry_diagnostics,
)

FIX = Path(__file__).parent / "fixtures"
ROUTE_ID = "22443444-e127-4e40-8927-a3192e750369"
ENTRY_DATA = {
    "instance_name": "UofR", "instance_label": "University of Rochester Shuttle",
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
        v["when"] = now                      # keep the fix fresh
    return d


async def setup(hass, bundle, live):
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, options={},
                            unique_id=f"UofR:{ROUTE_ID}")
    entry.add_to_hass(hass)
    with patch.object(TripShotApi, "route_service_bundle", return_value=bundle), \
         patch.object(TripShotApi, "live_status", return_value=live):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


class TestDiagnostics:
    async def test_it_runs_at_all(self, hass: HomeAssistant, bundle, live):
        entry = await setup(hass, bundle, live)
        d = await async_get_config_entry_diagnostics(hass, entry)
        assert isinstance(d, dict)

    async def test_it_is_json_serialisable(self, hass: HomeAssistant, bundle, live):
        """Home Assistant serialises it; a stray datetime would fail there."""
        entry = await setup(hass, bundle, live)
        d = await async_get_config_entry_diagnostics(hass, entry)
        json.dumps(d)

    async def test_resolved_settings_are_reported(
        self, hass: HomeAssistant, bundle, live
    ):
        entry = await setup(hass, bundle, live)
        r = (await async_get_config_entry_diagnostics(hass, entry))["resolved"]
        assert r["route_id"] == ROUTE_ID
        assert r["geofence_radius_m"] == pytest.approx(76.2, abs=0.1)
        assert r["poll_interval_sec"] == 30
        assert r["timezone"]

    async def test_every_stop_is_listed_with_counters(
        self, hass: HomeAssistant, bundle, live
    ):
        entry = await setup(hass, bundle, live)
        s = (await async_get_config_entry_diagnostics(hass, entry))["schedule"]
        assert s["stop_count"] == 2
        assert len(s["stops"]) == 2
        for stop in s["stops"]:
            assert stop["name"]
            assert len(stop["counters"]) == 6
            assert "current_state" in stop

    async def test_bus_distances_are_reported(
        self, hass: HomeAssistant, bundle, live
    ):
        """The single most useful field when a visit was not counted."""
        entry = await setup(hass, bundle, live)
        d = (await async_get_config_entry_diagnostics(hass, entry))["live"]
        assert d["position_count"] >= 1
        bus = d["buses"][0]
        assert set(bus["distance_m"]) == {"Eastman Living Center",
                                          "Rush Rhees Library Back Side"}
        assert all(isinstance(v, float) for v in bus["distance_m"].values())

    async def test_health_reports_the_update_state(
        self, hass: HomeAssistant, bundle, live
    ):
        entry = await setup(hass, bundle, live)
        h = (await async_get_config_entry_diagnostics(hass, entry))["health"]
        assert h["last_update_success"] is True
        assert h["schedule_problems"] == []
        assert h["primed"] is True

    async def test_it_survives_a_missing_snapshot(
        self, hass: HomeAssistant, bundle, live
    ):
        entry = await setup(hass, bundle, live)
        coordinator = hass.data[DOMAIN][entry.entry_id]
        coordinator.snapshot = None
        coordinator.schedule = None
        d = await async_get_config_entry_diagnostics(hass, entry)
        assert d["schedule"] is None and d["live"] is None

    async def test_no_credentials_are_exposed(
        self, hass: HomeAssistant, bundle, live
    ):
        """There are none to leak, and this keeps it that way."""
        entry = await setup(hass, bundle, live)
        blob = json.dumps(await async_get_config_entry_diagnostics(hass, entry)).lower()
        for word in ("authorization", "bearer", "password", "token", "secret"):
            assert word not in blob
