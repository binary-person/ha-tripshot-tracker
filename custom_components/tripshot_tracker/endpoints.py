"""Request shapes for the public endpoints — pure, so they can be tested.

Some endpoints pin query parameters inside the Retrofit annotation itself
rather than passing them as arguments, e.g.

    @GET("/v1/p/routeServiceBundle?withScheduledRides=true&embedStops=true&withRoutes=true")

Those flags are load-bearing and easy to lose, because the path alone looks
complete. Omitting them returns HTTP 200 with a structurally similar but
hollow payload — no routes, no rides, and `ViaStop.stop` as a bare id string
instead of an embedded object — which parses to a schedule with no stops.

Keeping the shapes here, away from aiohttp, means a test can assert the pinned
flags are still being sent.

doc: integration.request-plan#pinned-params, api.endpoints.public
"""

from __future__ import annotations

from datetime import date
from typing import Any

ROUTE_SERVICE_BUNDLE_PATH = "/v1/p/routeServiceBundle"
LIVE_STATUS_PATH = "/v1/p/liveStatus"
ROUTE_PATH = "/v1/p/route"
GLOBAL_DISCOVERY_PATH = "/v1/global/discovery"
ADVERTISED_INSTANCE_PATH = "/v1/global/advertisedInstance"

#: Pinned in the client's annotation, and required for a usable response.
#: `embedStops` is the critical one: without it the response still contains
#: ViaStop entries, but each `stop` is an id string rather than the object
#: carrying the name and location.
BUNDLE_PINNED_PARAMS: dict[str, str] = {
    "withScheduledRides": "true",
    "embedStops": "true",
    "withRoutes": "true",
}


def route_service_bundle_params(
    route_id: str, day: date, end_day: date | None = None
) -> dict[str, Any]:
    """Query parameters for GET /v1/p/routeServiceBundle."""
    return {
        **BUNDLE_PINNED_PARAMS,
        "routeId": route_id,
        "withNavigation": "false",
        "startDay": day.isoformat(),
        "endDay": (end_day or day).isoformat(),
    }


def live_status_body(ride_ids: list[str]) -> dict[str, Any]:
    """Body for POST /v1/p/liveStatus.

    An empty rideIds set returns the whole region — megabytes. The filter is
    what scopes the response to this route, as the client also does.
    """
    return {"rideIds": list(ride_ids), "vehicleIds": []}


def routes_params(day: date, region_id: str | None = None) -> dict[str, Any]:
    """Query parameters for GET /v1/p/route."""
    params: dict[str, Any] = {
        "startDay": day.isoformat(),
        "endDay": day.isoformat(),
    }
    if region_id:
        params["regionId"] = region_id
    return params
