"""TripShot public API client.

Only the endpoints documented in docs-apk/30-endpoints-public.md as
unauthenticated are reachable from here. There is deliberately no way to send a
credential: no Authorization header is ever constructed, and no login, signup,
OIDC or SAML path is implemented.

doc: api.transport, api.endpoints.public, integration.request-plan
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date
from typing import Any
from urllib.parse import urlencode

import aiohttp

from .endpoints import (
    ADVERTISED_INSTANCE_PATH,
    GLOBAL_DISCOVERY_PATH,
    LIVE_STATUS_PATH,
    ROUTE_PATH,
    ROUTE_SERVICE_BUNDLE_PATH,
    live_status_body,
    route_service_bundle_params,
    routes_params,
)
from .const import (
    APP_TYPE_RIDER,
    DEFAULT_BASE_URL,
    HTTP_TIMEOUT_SEC,
    USER_BUILD_HEADER,
)

_LOGGER = logging.getLogger(__name__)


class TripShotError(Exception):
    """Any failure talking to the TripShot API."""


class TripShotApi:
    """Thin async wrapper over the public endpoints.

    doc: api.transport — reproduces the client's headers and 10s timeout.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str = DEFAULT_BASE_URL,
        instance_id: int | None = None,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._instance_id = instance_id

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def instance_id(self) -> int | None:
        return self._instance_id

    def _headers(self) -> dict[str, str]:
        # doc: api.transport — X-Tripshot-Build is always sent; X-Instance-Id
        # only once an instance is known. Authorization is never sent.
        headers = {
            "X-Tripshot-Build": USER_BUILD_HEADER,
            "Accept": "application/json",
        }
        if self._instance_id is not None:
            headers["X-Instance-Id"] = str(self._instance_id)
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
        allow_404: bool = False,
    ) -> Any:
        url = f"{self._base_url}{path}"
        try:
            # Stdlib asyncio.timeout: the third-party async_timeout
            # package is not a Home Assistant dependency, so importing
            # it would break setup on a clean install.
            async with asyncio.timeout(HTTP_TIMEOUT_SEC):
                async with self._session.request(
                    method, url, params=params, json=json_body,
                    headers=self._headers(),
                ) as resp:
                    if resp.status == 404 and allow_404:
                        _LOGGER.debug("%s %s -> 404 (treated as absent)",
                                      method, url)
                        return None
                    if resp.status != 200:
                        detail = (await resp.text())[:300]
                        query = (f"?{urlencode(params, doseq=True)}"
                                 if params else "")
                        raise TripShotError(
                            f"{method} {path}{query} -> HTTP {resp.status}: "
                            f"{detail}"
                        )
                    body = await resp.read()
                    data = json.loads(body) if body else None
                    if _LOGGER.isEnabledFor(logging.DEBUG):
                        _LOGGER.debug(
                            "%s %s%s -> 200, %d bytes, top-level keys: %s",
                            method, url,
                            f"?{urlencode(params, doseq=True)}" if params else "",
                            len(body),
                            sorted(data) if isinstance(data, dict)
                            else type(data).__name__,
                        )
                    return data
        except TripShotError:
            raise
        except aiohttp.ClientError as err:
            raise TripShotError(f"{method} {path} failed: {err}") from err
        except TimeoutError as err:
            raise TripShotError(
                f"{method} {path} timed out after {HTTP_TIMEOUT_SEC}s"
            ) from err

    # -- bootstrap --------------------------------------------------------
    async def list_instances(self) -> list[dict[str, Any]]:
        """GET /v1/global/advertisedInstance?appType=RiderApp.

        doc: api.discovery — step 1. Always against the default host.
        """
        data = await self._request(
            "GET", ADVERTISED_INSTANCE_PATH,
            params={"appType": APP_TYPE_RIDER},
        )
        return data or []

    async def discover_base_url(self, instance_name: str) -> str:
        """GET /v1/global/discovery?name=... , falling back on 404.

        doc: api.discovery — step 2. The client maps 404 to "absent" and uses
        BuildConfig.BASE_URL, so a 404 is normal (UofR returns one).
        """
        data = await self._request(
            "GET", GLOBAL_DISCOVERY_PATH,
            params={"name": instance_name}, allow_404=True,
        )
        if data and data.get("apiBaseUrl"):
            _LOGGER.debug("discovery: %s -> %s", instance_name,
                          data["apiBaseUrl"])
            return str(data["apiBaseUrl"])
        _LOGGER.debug("discovery: %s absent, using default host",
                      instance_name)
        return DEFAULT_BASE_URL

    # -- transit data -----------------------------------------------------
    async def list_routes(
        self, day: date, region_id: str | None = None
    ) -> list[dict[str, Any]]:
        """GET /v1/p/route.

        doc: api.endpoints.public — getRoutesPublic.
        """
        data = await self._request(
            "GET", ROUTE_PATH, params=routes_params(day, region_id))
        return data or []

    async def get_route(self, route_id: str) -> dict[str, Any] | None:
        """GET /v1/p/route/{routeId}, or None if this instance has no such route.

        Used only when diagnosing an empty schedule: an unknown route id and a
        day with no service both return an empty 200 from the bundle endpoint,
        and this is what tells them apart.
        """
        return await self._request(
            "GET", f"{ROUTE_PATH}/{route_id}", allow_404=True)

    async def route_service_bundle(
        self, route_id: str, day: date, end_day: date | None = None
    ) -> dict[str, Any]:
        """GET /v1/p/routeServiceBundle.

        doc: integration.request-plan — schedule refresh. The client pins
        withScheduledRides / embedStops / withRoutes inside the annotation
        rather than passing them as arguments, so they must be sent
        explicitly; see endpoints.BUNDLE_PINNED_PARAMS for what happens when
        they are not.

        `end_day` widens the window. Used only to discover the route's stops on
        a day it does not run — see TripShotCoordinator._probe_stops.
        """
        data = await self._request(
            "GET", ROUTE_SERVICE_BUNDLE_PATH,
            params=route_service_bundle_params(route_id, day, end_day),
        )
        return data or {}

    async def live_status(
        self, region_id: str, ride_ids: list[str]
    ) -> dict[str, Any]:
        """POST /v1/p/liveStatus with a populated rideIds filter.

        doc: integration.request-plan — the filter is what keeps the response
        at ~146 KB instead of ~4.5 MB, and mirrors what the client sends.
        """
        data = await self._request(
            "POST", LIVE_STATUS_PATH,
            params={"regionId": region_id},
            json_body=live_status_body(ride_ids),
        )
        return data or {}
