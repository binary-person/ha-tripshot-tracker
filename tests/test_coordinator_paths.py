"""Coordinator paths that only run against a live Home Assistant.

coordinator.py was 62% covered. The gaps were the ones that matter when
something is wrong: no-service days, the stop probe, the empty-schedule
diagnosis, timezone resolution, options applied in place, and latch expiry.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tripshot_tracker.api import TripShotApi, TripShotError
from custom_components.tripshot_tracker.const import DOMAIN

FIX = Path(__file__).parent / "fixtures"
ROUTE_ID = "22443444-e127-4e40-8927-a3192e750369"
ENTRY_DATA = {
    "instance_name": "UofR", "instance_label": "UofR Shuttle",
    "instance_id": 526, "base_url": "https://api.tripshot.com",
    "route_id": ROUTE_ID, "route_name": "Red Line", "region_id": "reg",
}
EMPTY_BUNDLE: dict = {}


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


async def setup(hass, bundle, live, options=None):
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, options=options or {},
                            unique_id=f"UofR:{ROUTE_ID}")
    entry.add_to_hass(hass)
    with patch.object(TripShotApi, "route_service_bundle", return_value=bundle), \
         patch.object(TripShotApi, "live_status", return_value=live):
        ok = await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry, ok


class TestNoServiceDay:
    async def test_setup_succeeds_by_probing_for_stops(
        self, hass: HomeAssistant, bundle, live
    ):
        """Installing on a weekend must not fail; it probes a week ahead."""
        calls = []

        async def fake_bundle(self, route_id, day, end_day=None):
            calls.append(end_day)
            return EMPTY_BUNDLE if end_day is None else bundle

        with patch.object(TripShotApi, "route_service_bundle", fake_bundle), \
             patch.object(TripShotApi, "live_status", return_value=live):
            entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, options={},
                                    unique_id=f"UofR:{ROUTE_ID}")
            entry.add_to_hass(hass)
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

        assert any(e is not None for e in calls), "never probed a wider window"
        coordinator = hass.data[DOMAIN][entry.entry_id]
        assert coordinator.no_service_today is True
        assert len(coordinator.schedule.stops) == 2      # stops kept
        assert coordinator.schedule.visits == []          # visits dropped

    async def test_entities_still_exist_on_a_no_service_day(
        self, hass: HomeAssistant, bundle, live
    ):
        async def fake_bundle(self, route_id, day, end_day=None):
            return EMPTY_BUNDLE if end_day is None else bundle

        with patch.object(TripShotApi, "route_service_bundle", fake_bundle), \
             patch.object(TripShotApi, "live_status", return_value=live):
            entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, options={},
                                    unique_id=f"UofR:{ROUTE_ID}")
            entry.add_to_hass(hass)
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

        entities = er.async_entries_for_config_entry(er.async_get(hass),
                                                     entry.entry_id)
        assert len(entities) == 20

    async def test_schedule_health_reports_it(
        self, hass: HomeAssistant, bundle, live
    ):
        async def fake_bundle(self, route_id, day, end_day=None):
            return EMPTY_BUNDLE if end_day is None else bundle

        with patch.object(TripShotApi, "route_service_bundle", fake_bundle), \
             patch.object(TripShotApi, "live_status", return_value=live):
            entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, options={},
                                    unique_id=f"UofR:{ROUTE_ID}")
            entry.add_to_hass(hass)
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

        assert hass.states.get("sensor.red_line_schedule_health").state == \
            "no service today"


class TestEmptyScheduleDiagnosis:
    async def test_unknown_route_says_so(self, hass: HomeAssistant, live):
        """An unknown route and a service gap both return an empty 200."""
        with patch.object(TripShotApi, "route_service_bundle",
                          return_value=EMPTY_BUNDLE), \
             patch.object(TripShotApi, "get_route", return_value=None), \
             patch.object(TripShotApi, "live_status", return_value=live):
            entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, options={},
                                    unique_id=f"UofR:{ROUTE_ID}")
            entry.add_to_hass(hass)
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
        assert entry.state is not None
        assert "no route" in str(entry.reason).lower()

    async def test_existing_route_without_service_says_so(
        self, hass: HomeAssistant, live
    ):
        with patch.object(TripShotApi, "route_service_bundle",
                          return_value=EMPTY_BUNDLE), \
             patch.object(TripShotApi, "get_route",
                          return_value={"name": "Red Line"}), \
             patch.object(TripShotApi, "live_status", return_value=live):
            entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, options={},
                                    unique_id=f"UofR:{ROUTE_ID}")
            entry.add_to_hass(hass)
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
        assert "no scheduled service" in str(entry.reason).lower()


class TestErrors:
    async def test_api_failure_is_an_update_failure_not_a_crash(
        self, hass: HomeAssistant, bundle, live
    ):
        entry, _ = await setup(hass, bundle, live)
        coordinator = hass.data[DOMAIN][entry.entry_id]
        with patch.object(TripShotApi, "live_status",
                          side_effect=TripShotError("boom")), \
             patch.object(TripShotApi, "route_service_bundle", return_value=bundle):
            await coordinator.async_refresh()
        assert coordinator.last_update_success is False

    async def test_it_recovers_on_the_next_poll(
        self, hass: HomeAssistant, bundle, live
    ):
        entry, _ = await setup(hass, bundle, live)
        coordinator = hass.data[DOMAIN][entry.entry_id]
        with patch.object(TripShotApi, "live_status",
                          side_effect=TripShotError("boom")), \
             patch.object(TripShotApi, "route_service_bundle", return_value=bundle):
            await coordinator.async_refresh()
        with patch.object(TripShotApi, "live_status", return_value=live), \
             patch.object(TripShotApi, "route_service_bundle", return_value=bundle):
            await coordinator.async_refresh()
        assert coordinator.last_update_success is True


class TestTimezone:
    async def test_configured_timezone_is_used(self, hass: HomeAssistant, bundle, live):
        entry, _ = await setup(hass, bundle, live,
                               options={"timezone": "America/New_York"})
        coordinator = hass.data[DOMAIN][entry.entry_id]
        assert str(coordinator.timezone) == "America/New_York"

    async def test_unknown_timezone_falls_back_without_crashing(
        self, hass: HomeAssistant, bundle, live
    ):
        entry, ok = await setup(hass, bundle, live,
                                options={"timezone": "Mars/Olympus_Mons"})
        assert ok
        coordinator = hass.data[DOMAIN][entry.entry_id]
        assert coordinator.timezone is not None

    async def test_empty_timezone_follows_home_assistant(
        self, hass: HomeAssistant, bundle, live
    ):
        entry, _ = await setup(hass, bundle, live, options={"timezone": ""})
        coordinator = hass.data[DOMAIN][entry.entry_id]
        assert coordinator.timezone is not None


class TestOptionsApplied:
    async def test_grace_follows_the_poll_interval(
        self, hass: HomeAssistant, bundle, live
    ):
        entry, _ = await setup(hass, bundle, live,
                               options={"poll_interval_sec": 10,
                                        "measurement_grace_sec": -1})
        c = hass.data[DOMAIN][entry.entry_id]
        assert c.grace_sec == 10 + 16

    async def test_explicit_grace_wins(self, hass: HomeAssistant, bundle, live):
        entry, _ = await setup(hass, bundle, live,
                               options={"measurement_grace_sec": 11})
        assert hass.data[DOMAIN][entry.entry_id].grace_sec == 11

    async def test_geofence_diameter_becomes_a_radius(
        self, hass: HomeAssistant, bundle, live
    ):
        entry, _ = await setup(hass, bundle, live,
                               options={"geofence_diameter_ft": 1000})
        assert hass.data[DOMAIN][entry.entry_id].radius_m == pytest.approx(152.4, abs=0.1)

    async def test_confirm_polls_floor(self, hass: HomeAssistant, bundle, live):
        entry, _ = await setup(hass, bundle, live, options={"confirm_polls": 0})
        assert hass.data[DOMAIN][entry.entry_id].confirm_polls == 1


class TestBusCount:
    async def test_a_fresh_bus_is_counted(self, hass: HomeAssistant, bundle, live):
        entry, _ = await setup(hass, bundle, live)
        c = hass.data[DOMAIN][entry.entry_id]
        assert c.bus_count == 1
        assert c.bus_names == ["2603"]
        assert hass.states.get("sensor.red_line_buses").state == "1"

    async def test_a_stale_bus_is_not(self, hass: HomeAssistant, bundle, live):
        old = datetime.now(timezone.utc) - timedelta(hours=3)
        live["vehicleStatuses"][0]["when"] = old.isoformat().replace("+00:00", "Z")
        entry, _ = await setup(hass, bundle, live)
        assert hass.data[DOMAIN][entry.entry_id].bus_count == 0


class TestUnload:
    async def test_entry_unloads_cleanly(self, hass: HomeAssistant, bundle, live):
        entry, _ = await setup(hass, bundle, live)
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.entry_id not in hass.data.get(DOMAIN, {})


class TestRolloverOntoANoServiceDay:
    """Friday's schedule must not be carried into Saturday with its visits.

    This is the branch where `known` comes from the *previous* schedule rather
    than a probe. Keeping its visits would leave nearest_visit matching a visit
    a day away, so a bus standing at a stop would latch a bogus ARRIVE_LATE --
    the bug `stops_only` exists to prevent.
    """

    async def test_previous_days_visits_are_dropped(
        self, hass: HomeAssistant, bundle, live
    ):
        entry, _ = await setup(hass, bundle, live)
        coordinator = hass.data[DOMAIN][entry.entry_id]
        assert coordinator.schedule.visits, "precondition: a schedule with visits"
        assert len(coordinator.schedule.stops) == 2

        # The route stops running: the day request now comes back empty, and
        # the previous schedule is the only source of stops.
        coordinator._schedule_fetched = None
        with patch.object(TripShotApi, "route_service_bundle",
                          return_value=EMPTY_BUNDLE), \
             patch.object(TripShotApi, "live_status", return_value=live):
            await coordinator.async_refresh()
            await hass.async_block_till_done()

        assert coordinator.no_service_today is True
        assert len(coordinator.schedule.stops) == 2, "stops must be kept"
        assert coordinator.schedule.visits == [], \
            "yesterday's visits must not be carried into a no-service day"

    async def test_nothing_is_counted_on_a_no_service_day(
        self, hass: HomeAssistant, bundle, live
    ):
        """With no visits there is nothing for a bus to be judged against."""
        entry, _ = await setup(hass, bundle, live)
        coordinator = hass.data[DOMAIN][entry.entry_id]

        coordinator._schedule_fetched = None
        with patch.object(TripShotApi, "route_service_bundle",
                          return_value=EMPTY_BUNDLE), \
             patch.object(TripShotApi, "live_status", return_value=live):
            await coordinator.async_refresh()
            await hass.async_block_till_done()

        for stop_id in coordinator.schedule.stop_order:
            assert coordinator.schedule.nearest_visit(
                stop_id, datetime.now(timezone.utc)) is None
