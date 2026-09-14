"""The config flow, end to end, including every abort and error path.

config_flow.py was 21% covered: the whole user-facing setup path was never
executed.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tripshot_tracker.api import TripShotApi, TripShotError
from custom_components.tripshot_tracker.const import DOMAIN

ROUTE_ID = "22443444-e127-4e40-8927-a3192e750369"
INSTANCES = [{"name": "UofR", "displayName": "University of Rochester Shuttle",
              "instanceId": 526},
             {"name": "Other", "displayName": "Other Transit", "instanceId": 9}]
ROUTES = [{"routeId": ROUTE_ID, "name": "Red Line", "publicName": "Red Line",
           "regionId": "reg"},
          {"routeId": "other", "name": "Blue Line", "regionId": "reg"}]
BUNDLE = json.loads(
    (Path(__file__).parent / "fixtures" / "route_service_bundle.json").read_text())
LIVE = json.loads(
    (Path(__file__).parent / "fixtures" / "live_status.json").read_text())

SETTINGS = {
    "arrival_early_buffer_sec": 120, "departure_late_buffer_sec": 120,
    "geofence_diameter_ft": 500, "measurement_grace_sec": -1,
    "confirm_polls": 2, "position_max_age_sec": 120, "poll_interval_sec": 30,
    "timezone": "America/New_York",
}


def mocked_api(instances=INSTANCES, routes=ROUTES, base="https://api.tripshot.com"):
    return (
        patch.object(TripShotApi, "list_instances", return_value=instances),
        patch.object(TripShotApi, "discover_base_url", return_value=base),
        patch.object(TripShotApi, "list_routes", return_value=routes),
        patch.object(TripShotApi, "route_service_bundle", return_value=BUNDLE),
        patch.object(TripShotApi, "live_status", return_value=LIVE),
    )


async def run_full_flow(hass, settings=None):
    with mocked_api()[0], mocked_api()[1], mocked_api()[2], \
         mocked_api()[3], mocked_api()[4]:
        r = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER})
        assert r["step_id"] == "user"
        r = await hass.config_entries.flow.async_configure(
            r["flow_id"], {"instance_name": "UofR"})
        assert r["step_id"] == "route"
        r = await hass.config_entries.flow.async_configure(
            r["flow_id"], {"route_id": ROUTE_ID})
        assert r["step_id"] == "settings"
        r = await hass.config_entries.flow.async_configure(
            r["flow_id"], settings or SETTINGS)
        await hass.async_block_till_done()
        return r


class TestHappyPath:
    async def test_creates_an_entry(self, hass: HomeAssistant):
        r = await run_full_flow(hass)
        assert r["type"] is FlowResultType.CREATE_ENTRY

    async def test_title_names_the_system_and_route(self, hass: HomeAssistant):
        r = await run_full_flow(hass)
        assert r["title"] == "University of Rochester Shuttle — Red Line"

    async def test_data_carries_what_setup_needs(self, hass: HomeAssistant):
        d = (await run_full_flow(hass))["data"]
        assert d["instance_name"] == "UofR"
        assert d["instance_id"] == 526
        assert d["route_id"] == ROUTE_ID
        assert d["route_name"] == "Red Line"
        assert d["region_id"] == "reg"
        assert d["base_url"] == "https://api.tripshot.com"

    async def test_unique_id_is_stable_across_reinstalls(self, hass: HomeAssistant):
        await run_full_flow(hass)
        entry = hass.config_entries.async_entries(DOMAIN)[0]
        assert entry.unique_id == f"UofR:{ROUTE_ID}"

    async def test_settings_become_options(self, hass: HomeAssistant):
        r = await run_full_flow(hass)
        assert r["options"]["confirm_polls"] == 2
        assert r["options"]["timezone"] == "America/New_York"


class TestDuplicates:
    async def test_the_same_route_cannot_be_added_twice(self, hass: HomeAssistant):
        MockConfigEntry(domain=DOMAIN, unique_id=f"UofR:{ROUTE_ID}").add_to_hass(hass)
        with mocked_api()[0], mocked_api()[1], mocked_api()[2]:
            r = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER})
            r = await hass.config_entries.flow.async_configure(
                r["flow_id"], {"instance_name": "UofR"})
            r = await hass.config_entries.flow.async_configure(
                r["flow_id"], {"route_id": ROUTE_ID})
        assert r["type"] is FlowResultType.ABORT
        assert r["reason"] == "already_configured"


class TestFailures:
    async def test_unreachable_api_aborts_at_the_first_step(self, hass: HomeAssistant):
        with patch.object(TripShotApi, "list_instances",
                          side_effect=TripShotError("down")):
            r = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER})
        assert r["type"] is FlowResultType.ABORT
        assert r["reason"] == "cannot_connect"

    async def test_no_advertised_instances_aborts(self, hass: HomeAssistant):
        with patch.object(TripShotApi, "list_instances", return_value=[]):
            r = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER})
        assert r["reason"] == "no_instances"

    async def test_no_routes_aborts(self, hass: HomeAssistant):
        with patch.object(TripShotApi, "list_instances", return_value=INSTANCES), \
             patch.object(TripShotApi, "discover_base_url",
                          return_value="https://api.tripshot.com"), \
             patch.object(TripShotApi, "list_routes", return_value=[]):
            r = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER})
            r = await hass.config_entries.flow.async_configure(
                r["flow_id"], {"instance_name": "UofR"})
        assert r["reason"] == "no_routes"

    async def test_route_listing_failure_aborts(self, hass: HomeAssistant):
        with patch.object(TripShotApi, "list_instances", return_value=INSTANCES), \
             patch.object(TripShotApi, "discover_base_url",
                          return_value="https://api.tripshot.com"), \
             patch.object(TripShotApi, "list_routes",
                          side_effect=TripShotError("down")):
            r = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER})
            r = await hass.config_entries.flow.async_configure(
                r["flow_id"], {"instance_name": "UofR"})
        assert r["reason"] == "cannot_connect"

    async def test_an_unknown_timezone_is_rejected_with_an_error(
        self, hass: HomeAssistant
    ):
        with mocked_api()[0], mocked_api()[1], mocked_api()[2]:
            r = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER})
            r = await hass.config_entries.flow.async_configure(
                r["flow_id"], {"instance_name": "UofR"})
            r = await hass.config_entries.flow.async_configure(
                r["flow_id"], {"route_id": ROUTE_ID})
            r = await hass.config_entries.flow.async_configure(
                r["flow_id"], {**SETTINGS, "timezone": "Mars/Olympus_Mons"})
        assert r["type"] is FlowResultType.FORM
        assert r["errors"] == {"timezone": "invalid_timezone"}


class TestOptionsFlow:
    async def test_options_can_be_retuned(self, hass: HomeAssistant):
        await run_full_flow(hass)
        entry = hass.config_entries.async_entries(DOMAIN)[0]

        r = await hass.config_entries.options.async_init(entry.entry_id)
        assert r["step_id"] == "init"
        r = await hass.config_entries.options.async_configure(
            r["flow_id"], {**SETTINGS, "confirm_polls": 3,
                           "poll_interval_sec": 15})
        await hass.async_block_till_done()
        assert r["type"] is FlowResultType.CREATE_ENTRY
        assert entry.options["confirm_polls"] == 3
        assert entry.options["poll_interval_sec"] == 15

    async def test_options_reject_an_unknown_timezone(self, hass: HomeAssistant):
        await run_full_flow(hass)
        entry = hass.config_entries.async_entries(DOMAIN)[0]
        r = await hass.config_entries.options.async_init(entry.entry_id)
        r = await hass.config_entries.options.async_configure(
            r["flow_id"], {**SETTINGS, "timezone": "Nowhere/Nothing"})
        assert r["errors"] == {"timezone": "invalid_timezone"}

    async def test_retuning_does_not_recreate_entities(self, hass: HomeAssistant):
        """The whole point of applying options in place."""
        from homeassistant.helpers import entity_registry as er
        await run_full_flow(hass)
        entry = hass.config_entries.async_entries(DOMAIN)[0]
        before = {e.entity_id for e in er.async_entries_for_config_entry(
            er.async_get(hass), entry.entry_id)}

        r = await hass.config_entries.options.async_init(entry.entry_id)
        with mocked_api()[3], mocked_api()[4]:
            await hass.config_entries.options.async_configure(
                r["flow_id"], {**SETTINGS, "arrival_early_buffer_sec": 300})
            await hass.async_block_till_done()

        after = {e.entity_id for e in er.async_entries_for_config_entry(
            er.async_get(hass), entry.entry_id)}
        assert before == after and before
