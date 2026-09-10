"""TripShot Tracker — per-stop schedule-adherence statistics.

Reads only the public, unauthenticated TripShot endpoints documented in
docs-apk/, and only two things from them: the published schedule and bus
positions. No credential is ever sent.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TripShotApi
from .const import (
    CONF_BASE_URL,
    CONF_INSTANCE_ID,
    CONF_REGION_ID,
    CONF_ROUTE_ID,
    CONF_ROUTE_NAME,
    DEFAULT_BASE_URL,
    DOMAIN,
    stable_key,
)
from .coordinator import TripShotCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def _async_migrate_unique_ids(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Re-key entities from `entry_id` onto the stable `unique_id` prefix.

    Rewriting the registry entry in place keeps each entity's `entity_id`,
    its recorded history and its restored counter. Creating new entities
    instead would abandon all three.
    """
    old_prefix = f"{entry.entry_id}_"
    new_prefix = f"{stable_key(entry)}_"
    if old_prefix == new_prefix:
        return

    migrated = 0

    @callback
    def _migrate(existing: er.RegistryEntry) -> dict[str, str] | None:
        nonlocal migrated
        if not existing.unique_id.startswith(old_prefix):
            return None
        migrated += 1
        return {"new_unique_id": new_prefix + existing.unique_id[len(old_prefix):]}

    await er.async_migrate_entries(hass, entry.entry_id, _migrate)
    if migrated:
        _LOGGER.info(
            "re-keyed %d entity unique id(s) onto %s so they survive the entry "
            "being removed and re-added", migrated, stable_key(entry),
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a transit-system + route config entry."""
    await _async_migrate_unique_ids(hass, entry)

    session = async_get_clientsession(hass)
    api = TripShotApi(
        session,
        base_url=entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
        instance_id=entry.data.get(CONF_INSTANCE_ID),
    )

    coordinator = TripShotCoordinator(
        hass,
        entry,
        api,
        route_id=entry.data[CONF_ROUTE_ID],
        route_name=entry.data.get(CONF_ROUTE_NAME, "Route"),
        region_id=entry.data.get(CONF_REGION_ID),
    )

    # Entities are built from the schedule, so it must exist before forwarding.
    await coordinator.async_config_entry_first_refresh()

    # Create the route device up front and hand its id to the stop devices.
    # Passing `via_device=(DOMAIN, ...)` in DeviceInfo is deprecated — Home
    # Assistant warns that it "will stop working in 2027.8.0" — and it also
    # relied on the route device happening to be created first, which is only
    # true because the Buses sensor is first in the list handed to
    # async_add_entities. Creating it explicitly removes both problems.
    route_device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=coordinator.route_name,
        manufacturer="TripShot",
        model="Transit route",
    )
    coordinator.route_device_id = route_device.id

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    _LOGGER.info(
        "set up %s: instance=%s route=%s base=%s tz=%s day=%s | "
        "geofence %.1fm (%.0f ft diameter), buffers early=%.0fs late=%.0fs, "
        "position max age %.0fs, poll %.0fs | %d stops, %d visits today",
        entry.title,
        entry.data.get(CONF_INSTANCE_ID),
        entry.data[CONF_ROUTE_ID],
        api.base_url,
        coordinator.timezone,
        coordinator.service_day,
        coordinator.radius_m,
        coordinator.radius_m * 2 / 0.3048,
        coordinator.early_buffer_sec,
        coordinator.late_buffer_sec,
        coordinator.position_max_age_sec,
        coordinator.update_interval.total_seconds()
        if coordinator.update_interval else -1,
        len(coordinator.schedule.stops) if coordinator.schedule else 0,
        len(coordinator.schedule.visits) if coordinator.schedule else 0,
    )
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply new buffers/geofence in place, without reloading.

    Deliberately not a reload. Every tunable is read live from
    `entry.options` on each poll, so the only thing needing attention is the
    poll interval, which the coordinator captured at construction.

    Not reloading means the entities are never torn down: their history,
    entity ids and accumulated counters all survive retuning untouched,
    rather than depending on state restoration to put them back.
    """
    coordinator: TripShotCoordinator | None = hass.data.get(DOMAIN, {}).get(
        entry.entry_id)
    if coordinator is None:
        return
    coordinator.apply_options()
    await coordinator.async_request_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Tear down a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
