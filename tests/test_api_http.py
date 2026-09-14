"""HTTP layer, exercised against a mocked aiohttp session.

api.py was 37% covered: every request builder, the 404-as-absent path, the
non-200 path and the timeout path were never executed.
"""

from __future__ import annotations

from datetime import date

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.tripshot_tracker.api import TripShotApi, TripShotError
from custom_components.tripshot_tracker.const import USER_BUILD_HEADER

BASE = "https://api.tripshot.com"
ROUTE = "22443444-e127-4e40-8927-a3192e750369"
DAY = date(2026, 9, 14)


def api(hass, instance_id=526):
    return TripShotApi(async_get_clientsession(hass), BASE, instance_id)


class TestHeaders:
    async def test_build_header_is_sent(self, hass: HomeAssistant, aioclient_mock):
        aioclient_mock.get(f"{BASE}/v1/p/route", json=[])
        await api(hass).list_routes(DAY)
        assert aioclient_mock.mock_calls[0][3]["X-Tripshot-Build"] == USER_BUILD_HEADER

    async def test_instance_header_is_sent(self, hass: HomeAssistant, aioclient_mock):
        aioclient_mock.get(f"{BASE}/v1/p/route", json=[])
        await api(hass).list_routes(DAY)
        assert aioclient_mock.mock_calls[0][3]["X-Instance-Id"] == "526"

    async def test_no_instance_header_when_unknown(
        self, hass: HomeAssistant, aioclient_mock
    ):
        aioclient_mock.get(f"{BASE}/v1/global/advertisedInstance", json=[])
        await api(hass, instance_id=None).list_instances()
        assert "X-Instance-Id" not in aioclient_mock.mock_calls[0][3]

    async def test_no_authorization_header_is_ever_sent(
        self, hass: HomeAssistant, aioclient_mock
    ):
        """The scope guarantee, asserted rather than described."""
        aioclient_mock.get(f"{BASE}/v1/p/route", json=[])
        aioclient_mock.post(f"{BASE}/v1/p/liveStatus", json={})
        a = api(hass)
        await a.list_routes(DAY)
        await a.live_status("region", ["r:2026-09-14"])
        for call in aioclient_mock.mock_calls:
            assert not any(k.lower() == "authorization" for k in call[3])


class TestRequests:
    async def test_bundle_sends_the_pinned_flags(
        self, hass: HomeAssistant, aioclient_mock
    ):
        aioclient_mock.get(f"{BASE}/v1/p/routeServiceBundle", json={})
        await api(hass).route_service_bundle(ROUTE, DAY)
        q = aioclient_mock.mock_calls[0][1].query
        assert q["withScheduledRides"] == "true"
        assert q["embedStops"] == "true"
        assert q["withRoutes"] == "true"
        assert q["startDay"] == "2026-09-14" == q["endDay"]

    async def test_bundle_end_day_widens_the_window(
        self, hass: HomeAssistant, aioclient_mock
    ):
        aioclient_mock.get(f"{BASE}/v1/p/routeServiceBundle", json={})
        await api(hass).route_service_bundle(ROUTE, DAY, date(2026, 9, 21))
        q = aioclient_mock.mock_calls[0][1].query
        assert q["startDay"] == "2026-09-14"
        assert q["endDay"] == "2026-09-21"

    async def test_live_status_posts_the_ride_filter(
        self, hass: HomeAssistant, aioclient_mock
    ):
        aioclient_mock.post(f"{BASE}/v1/p/liveStatus", json={"rides": []})
        await api(hass).live_status("reg", ["a:2026-09-14", "b:2026-09-14"])
        body = aioclient_mock.mock_calls[0][2]
        assert body == {"rideIds": ["a:2026-09-14", "b:2026-09-14"],
                        "vehicleIds": []}
        assert aioclient_mock.mock_calls[0][1].query["regionId"] == "reg"

    async def test_list_instances_sends_app_type(
        self, hass: HomeAssistant, aioclient_mock
    ):
        aioclient_mock.get(f"{BASE}/v1/global/advertisedInstance", json=[{"name": "UofR"}])
        out = await api(hass).list_instances()
        assert out == [{"name": "UofR"}]
        assert aioclient_mock.mock_calls[0][1].query["appType"] == "RiderApp"

    async def test_list_routes_optional_region(
        self, hass: HomeAssistant, aioclient_mock
    ):
        aioclient_mock.get(f"{BASE}/v1/p/route", json=[])
        await api(hass).list_routes(DAY, region_id="reg")
        assert aioclient_mock.mock_calls[0][1].query["regionId"] == "reg"


class TestDiscovery:
    async def test_discovery_returns_the_api_base_url(
        self, hass: HomeAssistant, aioclient_mock
    ):
        aioclient_mock.get(f"{BASE}/v1/global/discovery",
                           json={"apiBaseUrl": "https://other.tripshot.com"})
        assert await api(hass).discover_base_url("X") == "https://other.tripshot.com"

    async def test_404_falls_back_to_the_default_host(
        self, hass: HomeAssistant, aioclient_mock
    ):
        """UofR really does 404 here; the client treats it as absent."""
        aioclient_mock.get(f"{BASE}/v1/global/discovery", status=404)
        assert await api(hass).discover_base_url("UofR") == BASE

    async def test_empty_body_falls_back(self, hass: HomeAssistant, aioclient_mock):
        aioclient_mock.get(f"{BASE}/v1/global/discovery", json={})
        assert await api(hass).discover_base_url("X") == BASE


class TestErrors:
    async def test_non_200_raises_with_the_status_and_path(
        self, hass: HomeAssistant, aioclient_mock
    ):
        aioclient_mock.get(f"{BASE}/v1/p/route", status=500, text="boom")
        with pytest.raises(TripShotError) as err:
            await api(hass).list_routes(DAY)
        assert "500" in str(err.value) and "/v1/p/route" in str(err.value)

    async def test_404_without_allow_404_is_an_error(
        self, hass: HomeAssistant, aioclient_mock
    ):
        aioclient_mock.get(f"{BASE}/v1/p/routeServiceBundle", status=404, text="nope")
        with pytest.raises(TripShotError):
            await api(hass).route_service_bundle(ROUTE, DAY)

    async def test_get_route_maps_404_to_none(
        self, hass: HomeAssistant, aioclient_mock
    ):
        """Used to tell an unknown route from a day with no service."""
        aioclient_mock.get(f"{BASE}/v1/p/route/{ROUTE}", status=404, text="")
        assert await api(hass).get_route(ROUTE) is None

    async def test_get_route_returns_the_route(
        self, hass: HomeAssistant, aioclient_mock
    ):
        aioclient_mock.get(f"{BASE}/v1/p/route/{ROUTE}", json={"name": "Red Line"})
        assert (await api(hass).get_route(ROUTE))["name"] == "Red Line"

    async def test_connection_error_becomes_tripshot_error(
        self, hass: HomeAssistant, aioclient_mock
    ):
        import aiohttp
        aioclient_mock.get(f"{BASE}/v1/p/route", exc=aiohttp.ClientError("down"))
        with pytest.raises(TripShotError):
            await api(hass).list_routes(DAY)

    async def test_timeout_becomes_tripshot_error(
        self, hass: HomeAssistant, aioclient_mock
    ):
        aioclient_mock.get(f"{BASE}/v1/p/route", exc=TimeoutError())
        with pytest.raises(TripShotError) as err:
            await api(hass).list_routes(DAY)
        assert "timed out" in str(err.value)

    async def test_empty_responses_normalise(self, hass: HomeAssistant, aioclient_mock):
        aioclient_mock.get(f"{BASE}/v1/p/route", text="")
        assert await api(hass).list_routes(DAY) == []
