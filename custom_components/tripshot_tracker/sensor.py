"""Sensor entities.

Per stop: one counter for each time-locality state except n/a (six), plus a
diagnostic sensor showing that stop's current sticky state. Per route: a
"Buses" sensor, and a diagnostic sensor surfacing schedule validation problems.

Counters accumulate for the life of the config entry and are restored across
Home Assistant restarts. Home Assistant's statistics engine handles long-term
aggregation on its own, given the TOTAL_INCREASING state class — but it does
not preserve the entity's own value, so each counter restores itself here.

doc: semantics.time-locality#firing-cases
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import ExtraStoredData, RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, stable_key
from .coordinator import TripShotCoordinator
from .locality import COUNTED_STATES, TimeLocality

_LOGGER = logging.getLogger(__name__)

STATE_LABELS: dict[TimeLocality, str] = {
    TimeLocality.ARRIVE_EARLY: "Arrive early",
    TimeLocality.ARRIVE_ON_TIME: "Arrive on time",
    TimeLocality.ARRIVE_LATE: "Arrive late",
    TimeLocality.DEPART_EARLY: "Depart early",
    TimeLocality.DEPART_ON_TIME: "Depart on time",
    TimeLocality.DEPART_LATE: "Depart late",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create route-level entities, then track the stop list as it changes."""
    coordinator: TripShotCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        BusesSensor(coordinator, entry),
        ScheduleHealthSensor(coordinator, entry),
    ])

    known: set[str] = set()

    @callback
    def _sync_stops() -> None:
        """Add entities for stops not seen before.

        Entities are never removed. A stop that disappears from the timetable —
        a seasonal variation, a temporary closure, an operator edit — keeps its
        entities and their accumulated counters rather than having them
        deleted on what may be a transient absence.

        A stop that returns is not re-added here, but it does not need to be:
        after a restart while a stop was absent its entities are not recreated
        at setup, and this listener adds them when the stop reappears. Because
        the unique id is stable, Home Assistant matches the existing registry
        entry, so the entity keeps its id, its history and its restored
        counter. That only holds while the unique id does not embed the config
        entry id — see const.stable_key.
        """
        schedule = coordinator.schedule
        if schedule is None:
            return
        new = [s for s in schedule.stop_order if s not in known]
        if not new:
            return

        entities: list[SensorEntity] = []
        for stop_id in new:
            stop = schedule.stops[stop_id]
            for state in COUNTED_STATES:
                entities.append(
                    StopCounterSensor(coordinator, entry, stop_id, stop.name, state))
            entities.append(
                StopStateSensor(coordinator, entry, stop_id, stop.name))
            known.add(stop_id)

        _LOGGER.info(
            "adding entities for %d stop(s): %s",
            len(new), ", ".join(schedule.stops[s].name for s in new),
        )
        async_add_entities(entities)

    _sync_stops()
    entry.async_on_unload(coordinator.async_add_listener(_sync_stops))


class _Base(CoordinatorEntity[TripShotCoordinator], SensorEntity):
    """Shared plumbing."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TripShotCoordinator,
                 entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def _route_device(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self.coordinator.route_name,
            manufacturer="TripShot",
            model="Transit route",
        )


class _StopEntity(_Base):
    """An entity attached to one stop's device."""

    def __init__(self, coordinator, entry, stop_id: str, stop_name: str) -> None:
        super().__init__(coordinator, entry)
        self._stop_id = stop_id
        self._stop_name = stop_name

    @property
    def device_info(self) -> DeviceInfo:
        # Qualified by route. A stop served by more than one line would
        # otherwise produce identically-named devices across config entries,
        # and Home Assistant resolves the resulting entity_id collision by
        # appending _2, _3 … — which is both ugly and unstable, since the
        # suffix depends on which entry happened to be set up first.
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry.entry_id}_{self._stop_id}")},
            name=f"{self.coordinator.route_name} {self._stop_name}",
            manufacturer="TripShot",
            model="Stop",
            # via_device_id, not via_device: the latter is deprecated and
            # scheduled for removal. The route device is created explicitly
            # during setup so its id is known here.
            via_device_id=self.coordinator.route_device_id,
        )


@dataclass
class _StoredCount(ExtraStoredData):
    """The counter value, persisted independently of the entity's state.

    Restoring from the state alone is not enough: CoordinatorEntity reports
    `unavailable` whenever the last poll failed, and that is the string that
    gets persisted. A restart during an API outage would then restore
    "unavailable", the seed would be skipped, and the accumulated total would
    be lost — precisely when a restart is most likely.
    """

    count: int

    def as_dict(self) -> dict[str, int]:
        return {"count": self.count}


class StopCounterSensor(_StopEntity, RestoreEntity):
    """Cumulative count of one verdict at one stop."""

    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, entry, stop_id, stop_name,
                 state: TimeLocality) -> None:
        super().__init__(coordinator, entry, stop_id, stop_name)
        self._state = state
        self._attr_name = STATE_LABELS[state]
        self._attr_unique_id = f"{stable_key(entry)}_{stop_id}_{state.value}"
        self._attr_native_unit_of_measurement = "events"
        self._attr_icon = ("mdi:bus-clock" if state.value.startswith("arrive")
                           else "mdi:bus-marker")

    @property
    def extra_restore_state_data(self) -> _StoredCount:
        """Persisted alongside the state, and survives an `unavailable` one.

        Read at dump time, so it must return the live count even while the
        entity is reporting unavailable — which it does, because the count
        comes from the tracker rather than from the entity's own state.

        Never raises: Home Assistant catches an exception here by dropping the
        entity from the dump entirely, state included, with only a log line —
        so a fault here would silently lose the very history it exists to keep.
        """
        try:
            return _StoredCount(int(self.native_value))
        except Exception:  # noqa: BLE001 - see docstring
            _LOGGER.exception(
                "could not snapshot the counter for %s; storing 0 rather than "
                "letting this entity drop out of the restore dump",
                self.entity_id,
            )
            return _StoredCount(0)

    async def async_added_to_hass(self) -> None:
        """Seed the tracker from the value saved before the last shutdown."""
        await super().async_added_to_hass()

        restored: int | None = None

        # Preferred: the out-of-band count, which is written even when the
        # entity's own state was `unavailable` at shutdown.
        extra = await self.async_get_last_extra_data()
        if extra is not None:
            value = extra.as_dict().get("count")
            if isinstance(value, (int, float)):
                restored = int(value)

        # Fallback: the state itself, for entities saved before this existed.
        if restored is None:
            last = await self.async_get_last_state()
            if last is not None and last.state not in (
                    None, "unknown", "unavailable"):
                try:
                    restored = int(float(last.state))
                except (TypeError, ValueError):
                    _LOGGER.debug("ignoring unrestorable state %r for %s",
                                  last.state, self.entity_id)

        if restored is not None:
            self.coordinator.tracker.seed(self._stop_id, self._state, restored)

    @property
    def native_value(self) -> int:
        return self.coordinator.tracker.count(self._stop_id, self._state)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return {"stop_id": self._stop_id, "verdict": self._state.value}


class StopStateSensor(_StopEntity):
    """The stop's current sticky state — diagnostic."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:map-marker-check"

    def __init__(self, coordinator, entry, stop_id, stop_name) -> None:
        super().__init__(coordinator, entry, stop_id, stop_name)
        self._attr_name = "Current state"
        self._attr_unique_id = f"{stable_key(entry)}_{stop_id}_state"

    @property
    def native_value(self) -> str:
        return self.coordinator.tracker.state_for(self._stop_id).value

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        coord = self.coordinator
        attrs: dict[str, object] = {
            "stop_id": self._stop_id,
            "buses_here": coord.tracker.buses_at(self._stop_id),
            "geofence_radius_m": round(coord.radius_m, 1),
        }
        schedule = coord.schedule
        if schedule and self._stop_id in schedule.stops:
            stop = schedule.stops[self._stop_id]
            attrs["latitude"] = stop.location.lt
            attrs["longitude"] = stop.location.lg
            upcoming = [
                v for v in schedule.visits_for(self._stop_id)
                if coord.snapshot and coord.snapshot.timestamp
                and v.arrival >= coord.snapshot.timestamp
            ]
            attrs["scheduled_visits_today"] = len(
                schedule.visits_for(self._stop_id))
            if upcoming:
                attrs["next_scheduled_arrival"] = upcoming[0].arrival.isoformat()
        return attrs


class BusesSensor(_Base):
    """Number of buses currently running this route."""

    _attr_name = "Buses"
    _attr_icon = "mdi:bus-multiple"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{stable_key(entry)}_buses"
        self._attr_native_unit_of_measurement = "buses"

    @property
    def device_info(self) -> DeviceInfo:
        return self._route_device

    @property
    def native_value(self) -> int:
        return self.coordinator.bus_count

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {
            "buses": self.coordinator.bus_names,
            "route_id": self.coordinator.route_id,
        }


class ScheduleHealthSensor(_Base):
    """Surfaces schedule/buffer validation problems.

    Reports "ok", or the number of problems found — for example buffers wide
    enough that consecutive visits to a stop overlap, which would make "the
    nearest scheduled visit" ambiguous.
    """

    _attr_name = "Schedule health"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{stable_key(entry)}_schedule_health"

    @property
    def device_info(self) -> DeviceInfo:
        return self._route_device

    @property
    def native_value(self) -> str:
        problems = self.coordinator.schedule_problems
        if problems:
            return f"{len(problems)} problems"
        return "no service today" if self.coordinator.no_service_today else "ok"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        coord = self.coordinator
        schedule = coord.schedule
        return {
            "problems": coord.schedule_problems,
            "no_service_today": coord.no_service_today,
            "scheduled_visits": len(schedule.visits) if schedule else 0,
            "service_day": schedule.day.isoformat() if schedule else None,
            "arrival_early_buffer_sec": coord.early_buffer_sec,
            "departure_late_buffer_sec": coord.late_buffer_sec,
        }
