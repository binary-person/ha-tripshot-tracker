"""Downloadable diagnostics for a config entry.

Everything here is public transit data plus this integration's own state —
there are no credentials to redact, because none exist.

Settings → Devices & Services → TripShot Tracker → ⋮ → Download diagnostics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import TripShotCoordinator
from .locality import COUNTED_STATES, haversine_m


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Everything needed to explain why the counters look the way they do."""
    coordinator: TripShotCoordinator = hass.data[DOMAIN][entry.entry_id]
    now = datetime.now(timezone.utc)
    schedule = coordinator.schedule
    snapshot = coordinator.snapshot

    data: dict[str, Any] = {
        "entry": {
            "title": entry.title,
            "unique_id": entry.unique_id,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "resolved": {
            "base_url": coordinator.api.base_url,
            "instance_id": coordinator.api.instance_id,
            "route_id": coordinator.route_id,
            "route_name": coordinator.route_name,
            "region_id": coordinator.region_id,
            "timezone": str(coordinator.timezone),
            "service_day": coordinator.service_day.isoformat(),
            "geofence_radius_m": round(coordinator.radius_m, 2),
            "arrival_early_buffer_sec": coordinator.early_buffer_sec,
            "departure_late_buffer_sec": coordinator.late_buffer_sec,
            "position_max_age_sec": coordinator.position_max_age_sec,
            "poll_interval_sec": (coordinator.update_interval.total_seconds()
                                  if coordinator.update_interval else None),
        },
        "health": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": str(coordinator.last_exception)
            if coordinator.last_exception else None,
            "no_service_today": coordinator.no_service_today,
            "schedule_problems": coordinator.schedule_problems,
            "primed": coordinator.primed,
            "bus_count": coordinator.bus_count,
            "bus_names": coordinator.bus_names,
        },
    }

    if schedule is None:
        data["schedule"] = None
    else:
        data["schedule"] = {
            "day": schedule.day.isoformat(),
            "stop_count": len(schedule.stops),
            "visit_count": len(schedule.visits),
            "scheduled_ride_count": len(schedule.scheduled_ride_ids),
            "stops": [
                {
                    "stop_id": sid,
                    "name": schedule.stops[sid].name,
                    "latitude": schedule.stops[sid].location.lt,
                    "longitude": schedule.stops[sid].location.lg,
                    "visits_today": len(schedule.visits_for(sid)),
                    "next_visit": next(
                        (v.arrival.isoformat()
                         for v in sorted(schedule.visits_for(sid),
                                         key=lambda v: v.arrival)
                         if v.arrival >= now), None),
                    "counters": {
                        s.value: coordinator.tracker.count(sid, s)
                        for s in COUNTED_STATES
                    },
                    "current_state": coordinator.tracker.state_for(sid).value,
                    "buses_here": coordinator.tracker.buses_at(sid),
                }
                for sid in schedule.stop_order
            ],
        }

    # Where each bus is right now, and how far from each stop — the single
    # most useful thing when a visit was expected but not counted.
    if snapshot is None:
        data["live"] = None
    else:
        data["live"] = {
            "snapshot_timestamp": snapshot.timestamp.isoformat()
            if snapshot.timestamp else None,
            "position_count": len(snapshot.positions),
            "buses": [
                {
                    "vehicle_id": bus.vehicle_id,
                    "name": bus.name,
                    "latitude": bus.location.lt,
                    "longitude": bus.location.lg,
                    "age_sec": round(bus.age_sec(now), 1),
                    "fresh": bus.age_sec(now)
                    <= coordinator.position_max_age_sec,
                    "distance_m": {
                        schedule.stops[sid].name: round(
                            haversine_m(bus.location,
                                        schedule.stops[sid].location), 1)
                        for sid in schedule.stop_order
                    } if schedule else {},
                }
                for bus in snapshot.positions.values()
            ],
        }

    return data
