"""Config flow: transit system, then route, then adherence settings.

A config entry is keyed by (transit system, route) — its unique_id is
"<instance name>:<routeId>" — so several lines can be tracked side by side.

doc: api.discovery, semantics.time-locality, semantics.geo-locality
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .api import TripShotApi, TripShotError
from .const import (
    CONF_ARRIVAL_EARLY_BUFFER_SEC,
    CONF_BASE_URL,
    CONF_DEPARTURE_LATE_BUFFER_SEC,
    CONF_GEOFENCE_DIAMETER_FT,
    CONF_CONFIRM_POLLS,
    CONF_INSTANCE_ID,
    CONF_MEASUREMENT_GRACE_SEC,
    CONF_INSTANCE_LABEL,
    CONF_INSTANCE_NAME,
    CONF_POLL_INTERVAL_SEC,
    CONF_POSITION_MAX_AGE_SEC,
    CONF_REGION_ID,
    CONF_ROUTE_ID,
    CONF_ROUTE_NAME,
    CONF_TIMEZONE,
    DOMAIN,
    TUNABLES,
)

_LOGGER = logging.getLogger(__name__)


def settings_schema(
    current: dict[str, Any] | None = None, ha_timezone: str = ""
) -> vol.Schema:
    """Schema for the tunables, seeded from `current` or the defaults.

    `ha_timezone` pre-fills the timezone field with Home Assistant's own zone,
    which is the right answer only when Home Assistant is configured for the
    same place the buses run.
    """
    current = current or {}

    def value(key):
        return current.get(key, TUNABLES[key])

    return vol.Schema({
        # Optional, and an empty value is meaningful: it means "follow Home
        # Assistant's timezone". Requiring a non-empty string made that
        # documented behaviour unreachable, and rejected the declared default.
        vol.Optional(CONF_TIMEZONE,
                     default=current.get(CONF_TIMEZONE) or ha_timezone): str,
        vol.Required(CONF_ARRIVAL_EARLY_BUFFER_SEC,
                     default=value(CONF_ARRIVAL_EARLY_BUFFER_SEC)):
            vol.All(vol.Coerce(int), vol.Range(min=0, max=3600)),
        vol.Required(CONF_DEPARTURE_LATE_BUFFER_SEC,
                     default=value(CONF_DEPARTURE_LATE_BUFFER_SEC)):
            vol.All(vol.Coerce(int), vol.Range(min=0, max=3600)),
        vol.Required(CONF_GEOFENCE_DIAMETER_FT,
                     default=value(CONF_GEOFENCE_DIAMETER_FT)):
            vol.All(vol.Coerce(float), vol.Range(min=50, max=5000)),
        vol.Required(CONF_MEASUREMENT_GRACE_SEC,
                     default=value(CONF_MEASUREMENT_GRACE_SEC)):
            vol.All(vol.Coerce(int), vol.Range(min=-1, max=600)),
        vol.Required(CONF_CONFIRM_POLLS,
                     default=value(CONF_CONFIRM_POLLS)):
            vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),
        vol.Required(CONF_POSITION_MAX_AGE_SEC,
                     default=value(CONF_POSITION_MAX_AGE_SEC)):
            vol.All(vol.Coerce(int), vol.Range(min=15, max=3600)),
        vol.Required(CONF_POLL_INTERVAL_SEC,
                     default=value(CONF_POLL_INTERVAL_SEC)):
            vol.All(vol.Coerce(int), vol.Range(min=10, max=600)),
    })


class TripShotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Three-step selection flow. No credentials are ever requested."""

    VERSION = 1

    def __init__(self) -> None:
        self._instances: list[dict[str, Any]] = []
        self._instance: dict[str, Any] | None = None
        self._base_url: str | None = None
        self._routes: list[dict[str, Any]] = []
        self._route: dict[str, Any] | None = None

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> "TripShotOptionsFlow":
        return TripShotOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the transit system from the public instance list."""
        session = async_get_clientsession(self.hass)
        errors: dict[str, str] = {}

        if not self._instances:
            try:
                self._instances = await TripShotApi(session).list_instances()
            except TripShotError as err:
                _LOGGER.error("could not list instances: %s", err)
                return self.async_abort(reason="cannot_connect")

        choices = {
            inst["name"]: inst.get("displayName") or inst["name"]
            for inst in self._instances if inst.get("name")
        }
        if not choices:
            return self.async_abort(reason="no_instances")

        if user_input is not None:
            name = user_input[CONF_INSTANCE_NAME]
            self._instance = next(
                (i for i in self._instances if i.get("name") == name), None)
            if self._instance is None:
                errors["base"] = "unknown_instance"
            else:
                try:
                    self._base_url = await TripShotApi(
                        session).discover_base_url(name)
                except TripShotError as err:
                    _LOGGER.error("discovery failed for %s: %s", name, err)
                    errors["base"] = "cannot_connect"
                if not errors:
                    return await self.async_step_route()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_INSTANCE_NAME): vol.In(
                    dict(sorted(choices.items(), key=lambda kv: kv[1])))
            }),
            errors=errors,
        )

    async def async_step_route(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the route within the selected transit system."""
        assert self._instance is not None and self._base_url is not None
        session = async_get_clientsession(self.hass)

        api = TripShotApi(session, base_url=self._base_url,
                          instance_id=self._instance.get("instanceId"))

        if not self._routes:
            try:
                self._routes = await api.list_routes(dt_util.now().date())
            except TripShotError as err:
                _LOGGER.error("could not list routes: %s", err)
                return self.async_abort(reason="cannot_connect")

        choices = {
            r["routeId"]: r.get("publicName") or r.get("name") or r["routeId"]
            for r in self._routes if r.get("routeId")
        }
        if not choices:
            return self.async_abort(reason="no_routes")

        errors: dict[str, str] = {}
        if user_input is not None:
            route_id = user_input[CONF_ROUTE_ID]
            self._route = next(
                (r for r in self._routes if r.get("routeId") == route_id), None)
            if self._route is None:
                errors["base"] = "unknown_route"
            else:
                await self.async_set_unique_id(
                    f"{self._instance['name']}:{route_id}")
                self._abort_if_unique_id_configured()
                return await self.async_step_settings()

        return self.async_show_form(
            step_id="route",
            data_schema=vol.Schema({
                vol.Required(CONF_ROUTE_ID): vol.In(
                    dict(sorted(choices.items(), key=lambda kv: kv[1])))
            }),
            errors=errors,
            description_placeholders={
                "instance": self._instance.get("displayName")
                or self._instance["name"]},
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set the adherence buffers, geofence size and transit timezone."""
        assert self._instance is not None and self._route is not None
        errors: dict[str, str] = {}

        if user_input is not None:
            if not await _valid_timezone(self.hass, user_input):
                errors[CONF_TIMEZONE] = "invalid_timezone"

        if user_input is not None and not errors:
            label = (self._instance.get("displayName")
                     or self._instance["name"])
            route_name = (self._route.get("publicName")
                          or self._route.get("name") or self._route["routeId"])
            return self.async_create_entry(
                title=f"{label} — {route_name}",
                data={
                    CONF_INSTANCE_NAME: self._instance["name"],
                    CONF_INSTANCE_LABEL: label,
                    CONF_INSTANCE_ID: self._instance.get("instanceId"),
                    CONF_BASE_URL: self._base_url,
                    CONF_ROUTE_ID: self._route["routeId"],
                    CONF_ROUTE_NAME: route_name,
                    CONF_REGION_ID: self._route.get("regionId"),
                },
                options=user_input,
            )

        return self.async_show_form(
            step_id="settings",
            data_schema=settings_schema(
                user_input, self.hass.config.time_zone or "UTC"),
            errors=errors,
        )


class TripShotOptionsFlow(OptionsFlow):
    """Lets the buffers, geofence and timezone be retuned after setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if await _valid_timezone(self.hass, user_input):
                return self.async_create_entry(title="", data=user_input)
            errors[CONF_TIMEZONE] = "invalid_timezone"

        return self.async_show_form(
            step_id="init",
            data_schema=settings_schema(
                user_input or dict(self.config_entry.options),
                self.hass.config.time_zone or "UTC",
            ),
            errors=errors,
        )


async def _valid_timezone(hass, user_input: dict[str, Any]) -> bool:
    """Whether the submitted timezone name resolves.

    Resolved through dt_util because loading zone data reads files, which must
    not happen on the event loop.
    """
    name = str(user_input.get(CONF_TIMEZONE) or "").strip()
    if not name:
        return True
    resolved = await dt_util.async_get_time_zone(name)
    if resolved is None:
        _LOGGER.warning("rejected unknown timezone %r", name)
        return False
    return True
