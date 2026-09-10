"""Tests for request shapes.

These exist because of a real failure: the client pins three query flags
inside its Retrofit annotation rather than passing them as arguments, and the
integration sent the path without them. The API answered HTTP 200 with a
structurally similar but hollow payload — `routes=0 rides=0`, and every
`ViaStop.stop` a bare id string instead of an embedded object — which parsed
to a schedule with no stops and failed setup with a misleading message.

doc: integration.request-plan
"""

from __future__ import annotations

from datetime import date

import pytest

from tsx.endpoints import (
    BUNDLE_PINNED_PARAMS,
    LIVE_STATUS_PATH,
    ROUTE_SERVICE_BUNDLE_PATH,
    live_status_body,
    route_service_bundle_params,
    routes_params,
)

DAY = date(2026, 9, 9)
ROUTE = "22443444-e127-4e40-8927-a3192e750369"


class TestBundlePinnedParams:
    """The three flags are load-bearing; losing any is silent at the HTTP layer."""

    @pytest.mark.parametrize("flag", [
        "withScheduledRides", "embedStops", "withRoutes"])
    def test_each_pinned_flag_is_sent(self, flag):
        assert route_service_bundle_params(ROUTE, DAY)[flag] == "true"

    def test_embed_stops_is_what_makes_stops_parseable(self):
        """Without it, ViaStop.stop is an id string and no stop is built."""
        assert BUNDLE_PINNED_PARAMS["embedStops"] == "true"

    def test_all_pinned_params_appear_in_the_request(self):
        params = route_service_bundle_params(ROUTE, DAY)
        for key, value in BUNDLE_PINNED_PARAMS.items():
            assert params[key] == value

    def test_route_and_day_range(self):
        params = route_service_bundle_params(ROUTE, DAY)
        assert params["routeId"] == ROUTE
        assert params["startDay"] == "2026-09-09"
        assert params["endDay"] == "2026-09-09"
        assert params["withNavigation"] == "false"

    def test_end_day_widens_the_window(self):
        params = route_service_bundle_params(ROUTE, DAY, date(2026, 9, 16))
        assert params["startDay"] == "2026-09-09"
        assert params["endDay"] == "2026-09-16"

    def test_widening_keeps_the_pinned_flags(self):
        """The probe path must not lose them either."""
        params = route_service_bundle_params(ROUTE, DAY, date(2026, 9, 16))
        assert all(params[k] == v for k, v in BUNDLE_PINNED_PARAMS.items())

    def test_path_carries_no_query_string(self):
        """Flags belong in params, so nothing can be lost to a stray '?'."""
        assert "?" not in ROUTE_SERVICE_BUNDLE_PATH
        assert "?" not in LIVE_STATUS_PATH


class TestLiveStatusBody:
    def test_filter_is_populated(self):
        body = live_status_body(["a:2026-09-09", "b:2026-09-09"])
        assert body["rideIds"] == ["a:2026-09-09", "b:2026-09-09"]
        assert body["vehicleIds"] == []

    def test_empty_filter_is_representable_but_distinct(self):
        """An empty set means the whole region — megabytes. Not an error here,
        but the coordinator must never reach this with no ride ids."""
        assert live_status_body([]) == {"rideIds": [], "vehicleIds": []}

    def test_body_does_not_alias_the_caller_list(self):
        ids = ["a:2026-09-09"]
        body = live_status_body(ids)
        ids.append("b:2026-09-09")
        assert body["rideIds"] == ["a:2026-09-09"]


class TestRoutesParams:
    def test_day_range(self):
        assert routes_params(DAY) == {"startDay": "2026-09-09",
                                      "endDay": "2026-09-09"}

    def test_region_is_optional(self):
        assert "regionId" not in routes_params(DAY)
        assert routes_params(DAY, "reg")["regionId"] == "reg"
