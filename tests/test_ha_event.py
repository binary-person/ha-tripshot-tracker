"""Prove the tripshot_tracker_event actually reaches the Home Assistant bus.

The event is what automations trigger on, and nothing else in the suite
exercised it -- the logic tests stop at the tracker returning a verdict, and
the setup tests stop at entities existing. This drives a real Home Assistant
through a full visit and captures the bus.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tripshot_tracker.api import TripShotApi
from custom_components.tripshot_tracker.const import DOMAIN, EVENT_VERDICT

FIXTURES = Path(__file__).parent / "fixtures"
ROUTE_ID = "22443444-e127-4e40-8927-a3192e750369"

# Eastman Living Center, from the schedule fixture.
AT_STOP = (43.1590312879686, -77.6012646661841)
AWAY = (43.1300000000000, -77.6500000000000)

ENTRY_DATA = {
    "instance_name": "UofR", "instance_label": "University of Rochester Shuttle",
    "instance_id": 526, "base_url": "https://api.tripshot.com",
    "route_id": ROUTE_ID, "route_name": "Red Line",
    "region_id": "ca558ddc-d7f2-4b48-9cac-deea1134f820",
}


def live_at(lat_lng, when=None):
    """A live payload with one bus at the given position, reported just now."""
    when = when or datetime.now(timezone.utc)
    return {
        "timestamp": when.isoformat().replace("+00:00", "Z"),
        "vehicleStatuses": [{
            "vehicleId": "97d597ef-73bc-4940-bfcc-c04df064ad00",
            "name": "2603",
            "location": {"lt": lat_lng[0], "lg": lat_lng[1]},
            "when": when.isoformat().replace("+00:00", "Z"),
        }],
    }


@pytest.fixture
def bundle():
    return json.loads((FIXTURES / "route_service_bundle.json").read_text())


async def test_event_is_fired_on_a_departure(
    hass: HomeAssistant, bundle
) -> None:
    """Drive arrival -> departure and assert the bus carries the event."""
    captured: list = []
    hass.bus.async_listen(EVENT_VERDICT, lambda e: captured.append(e))

    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA,
        options={"confirm_polls": 1},          # act on the first poll
        unique_id=f"UofR:{ROUTE_ID}",
    )
    entry.add_to_hass(hass)

    with (
        patch.object(TripShotApi, "route_service_bundle", return_value=bundle),
        patch.object(TripShotApi, "live_status", return_value=live_at(AT_STOP)),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Poll 1 primed. Poll 2 latches the arrival; poll 3 the bus has left.
    with (
        patch.object(TripShotApi, "route_service_bundle", return_value=bundle),
        patch.object(TripShotApi, "live_status", return_value=live_at(AT_STOP)),
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    with (
        patch.object(TripShotApi, "route_service_bundle", return_value=bundle),
        patch.object(TripShotApi, "live_status", return_value=live_at(AWAY)),
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    assert captured, "no tripshot_tracker_event reached the bus"

    # Only a departure: the first poll primes, adopting the bus's presence
    # without counting an arrival, so the arrival that opened this visit was
    # never a counted verdict and correctly produced no event.
    kinds = {e.data["kind"] for e in captured}
    assert kinds == {"departure"}, kinds

    dep = next(e for e in captured if e.data["kind"] == "departure")
    d = dep.data
    print("\n  event_type:", dep.event_type)
    for k in sorted(d):
        print(f"    {k}: {d[k]!r}")

    # The exact fields an automation filters on.
    assert dep.event_type == "tripshot_tracker_event"
    assert d["route"] == "Red Line"
    assert d["stop"] == "Eastman Living Center"
    assert d["verdict"].startswith("depart_")
    assert d["punctuality"] in ("early", "on_time", "late")
    assert d["bus"] == "2603"
    assert isinstance(d["deviation_seconds"], int)
    assert set(d) == {
        "entry_id", "route", "route_id", "stop", "stop_id", "verdict", "kind",
        "punctuality", "bus", "vehicle_id", "scheduled", "actual",
        "deviation_seconds", "deviation_minutes",
    }
