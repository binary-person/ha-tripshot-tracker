"""End-to-end setup against a real Home Assistant instance.

The pure tests cover the logic; this covers the wiring — that entities are
actually created, attached to devices, and grouped the way the UI expects.
That wiring is exactly what the pure tests cannot see.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tripshot_tracker.api import TripShotApi

FIXTURES = Path(__file__).parent / "fixtures"
DOMAIN = "tripshot_tracker"
ROUTE_ID = "22443444-e127-4e40-8927-a3192e750369"
REGION_ID = "ca558ddc-d7f2-4b48-9cac-deea1134f820"

ENTRY_DATA = {
    "instance_name": "UofR",
    "instance_label": "University of Rochester Shuttle",
    "instance_id": 526,
    "base_url": "https://api.tripshot.com",
    "route_id": ROUTE_ID,
    "route_name": "Red Line",
    "region_id": REGION_ID,
}


@pytest.fixture
def bundle():
    return json.loads((FIXTURES / "route_service_bundle.json").read_text())


@pytest.fixture
def live():
    return json.loads((FIXTURES / "live_status.json").read_text())


async def setup_entry(hass: HomeAssistant, bundle, live) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, options={},
        unique_id=f"UofR:{ROUTE_ID}",
        title="University of Rochester Shuttle — Red Line",
    )
    entry.add_to_hass(hass)
    with (
        patch.object(TripShotApi, "route_service_bundle", return_value=bundle),
        patch.object(TripShotApi, "live_status", return_value=live),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_entry_sets_up(hass: HomeAssistant, bundle, live) -> None:
    entry = await setup_entry(hass, bundle, live)
    assert entry.state.recoverable is False or entry.state.name == "LOADED"


async def test_entities_are_created(hass: HomeAssistant, bundle, live) -> None:
    entry = await setup_entry(hass, bundle, live)
    mine = er.async_entries_for_config_entry(
        er.async_get(hass), entry.entry_id)
    # 2 stops x (6 counters + state + deviation) + Buses + Schedule health
    assert len(mine) == 18, [e.entity_id for e in mine]


async def test_every_entity_is_attached_to_a_device(
    hass: HomeAssistant, bundle, live
) -> None:
    """The regression this file exists for.

    An invalid key in DeviceInfo makes Home Assistant log
    "Not adding entity with invalid device info" and abort the entity, so a
    stale registry entry is left behind with no device — which is what an
    "Ungrouped" list with an empty Device column looks like in the UI.
    """
    entry = await setup_entry(hass, bundle, live)
    mine = er.async_entries_for_config_entry(
        er.async_get(hass), entry.entry_id)
    orphans = [e.entity_id for e in mine if e.device_id is None]
    assert not orphans, f"entities with no device: {orphans}"


async def test_devices_are_created_per_stop_plus_the_route(
    hass: HomeAssistant, bundle, live
) -> None:
    entry = await setup_entry(hass, bundle, live)
    mine = dr.async_entries_for_config_entry(
        dr.async_get(hass), entry.entry_id)
    names = sorted(d.name for d in mine)
    assert names == [
        "Red Line",
        "Red Line Eastman Living Center",
        "Red Line Rush Rhees Library Back Side",
    ], names


async def test_stop_devices_hang_off_the_route_device(
    hass: HomeAssistant, bundle, live
) -> None:
    entry = await setup_entry(hass, bundle, live)
    mine = dr.async_entries_for_config_entry(
        dr.async_get(hass), entry.entry_id)
    route = next(d for d in mine if d.name == "Red Line")
    stops = [d for d in mine if d.name != "Red Line"]
    assert stops
    for stop in stops:
        assert stop.via_device_id == route.id, (
            f"{stop.name} is not linked to the route device")


async def test_entity_ids_are_route_qualified(
    hass: HomeAssistant, bundle, live
) -> None:
    entry = await setup_entry(hass, bundle, live)
    ids = {e.entity_id for e in er.async_entries_for_config_entry(
        er.async_get(hass), entry.entry_id)}
    assert "sensor.red_line_eastman_living_center_depart_early" in ids, sorted(ids)
    assert "sensor.red_line_buses" in ids, sorted(ids)


async def test_counters_start_at_zero(hass: HomeAssistant, bundle, live) -> None:
    await setup_entry(hass, bundle, live)
    state = hass.states.get("sensor.red_line_eastman_living_center_depart_early")
    assert state is not None
    assert state.state == "0"


async def test_setup_logs_no_deprecation_warnings(
    hass: HomeAssistant, bundle, live, caplog
) -> None:
    """Home Assistant reports deprecated API use through the frame helper.

    Those warnings name a removal version, so they are advance notice of a
    future breakage rather than style advice — worth failing on. This caught
    `via_device` in DeviceInfo, which was deprecated in favour of
    `via_device_id` and scheduled to stop working in 2027.8.0.
    """
    await setup_entry(hass, bundle, live)
    offenders = [
        r.message for r in caplog.records
        if "deprecated" in r.getMessage().lower()
        and "tripshot" in r.getMessage().lower()
    ]
    assert not offenders, offenders


async def test_stop_devices_reference_the_route_by_id(
    hass: HomeAssistant, bundle, live
) -> None:
    """The route device is created during setup, not incidentally by an entity.

    Relying on the Buses sensor happening to be first in the list handed to
    async_add_entities made the parent link depend on list order.
    """
    entry = await setup_entry(hass, bundle, live)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    assert coordinator.route_device_id

    mine = dr.async_entries_for_config_entry(
        dr.async_get(hass), entry.entry_id)
    route = next(d for d in mine if d.name == "Red Line")
    assert route.id == coordinator.route_device_id
    for stop in (d for d in mine if d.name != "Red Line"):
        assert stop.via_device_id == route.id
