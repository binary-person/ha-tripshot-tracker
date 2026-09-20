"""Reduce a live snapshot to observations, and validate the schedule windows.

Pure, and free of Home Assistant, so the joins are unit-testable.

doc: semantics.time-locality, semantics.geo-locality
"""

from __future__ import annotations

import logging
from datetime import datetime

from .locality import (
    LatLng,
    TimeWindow,
    arrival_window,
    departure_window,
    geo_locality,
    haversine_m,
    schedule_is_consistent,
)
from .models import LiveSnapshot
from .schedule import RouteSchedule, StopVisit
from .tracker import Observation

_LOGGER = logging.getLogger(__name__)


def windows_for(
    visit: StopVisit,
    early_buffer_sec: float,
    late_buffer_sec: float,
    grace_sec: float = 0.0,
) -> tuple[TimeWindow, TimeWindow]:
    """The arrival and departure windows for one scheduled visit."""
    return (
        arrival_window(visit.arrival, early_buffer_sec, grace_sec),
        departure_window(visit.departure, late_buffer_sec, grace_sec),
    )


def validate_schedule(
    schedule: RouteSchedule,
    early_buffer_sec: float,
    late_buffer_sec: float,
    grace_sec: float = 0.0,
) -> list[str]:
    """Check the configured buffers against the schedule.

    doc: semantics.time-locality#window-consistency — two things can go wrong:

    1. A visit's scheduled departure precedes its scheduled arrival. That is a
       broken timetable, not a configuration problem. Note this is checked on
       the *schedule*, not the windows: the measurement grace widens both
       strict edges toward each other, so on a short-dwell visit the windows
       legitimately overlap — harmless, because arrival and departure are
       judged from different events, never from one sample.
    2. Consecutive visits to the same stop overlap once the buffers are
       applied, which makes "the nearest visit" ambiguous. That is a
       configuration problem: the buffers are too wide for the headway.

    Returns human-readable problems; empty means consistent.
    """
    problems: list[str] = []

    for visit in schedule.visits:
        if not schedule_is_consistent(visit.arrival, visit.departure):
            problems.append(
                f"stop {visit.stop_id}: scheduled departure "
                f"{visit.departure.isoformat()} precedes scheduled arrival "
                f"{visit.arrival.isoformat()}; windows overlap"
            )

    # Iterate the stops that actually have visits, not the via list: a visit
    # can name a stop that never appeared in `vias`, and such visits would
    # otherwise skip validation entirely.
    for stop_id in sorted({v.stop_id for v in schedule.visits}):
        visits = sorted(schedule.visits_for(stop_id), key=lambda v: v.arrival)
        for prev, nxt in zip(visits, visits[1:]):
            prev_dep = departure_window(prev.departure, late_buffer_sec,
                                        grace_sec)
            next_arr = arrival_window(nxt.arrival, early_buffer_sec, grace_sec)
            if next_arr.start < prev_dep.end:
                overlap = (prev_dep.end - next_arr.start).total_seconds()
                problems.append(
                    f"stop {stop_id}: buffers overlap consecutive visits "
                    f"{prev.arrival.strftime('%H:%M:%S')} and "
                    f"{nxt.arrival.strftime('%H:%M:%S')} by {overlap:.0f}s; "
                    f"reduce the buffers below this headway"
                )

    return problems


def build_observations(
    now: datetime,
    schedule: RouteSchedule,
    snapshot: LiveSnapshot,
    radius_m: float,
    early_buffer_sec: float,
    late_buffer_sec: float,
    position_max_age_sec: float,
    grace_sec: float = 0.0,
) -> list[Observation]:
    """One observation per (fresh bus, stop).

    Every bus is tested against every stop: a bus is at one stop at most, and
    the geofences do not overlap, so this yields at most one AT_STOP per bus.
    """
    observations: list[Observation] = []
    fresh = snapshot.fresh(now, position_max_age_sec)

    stale = len(snapshot.positions) - len(fresh)
    if stale:
        _LOGGER.debug("ignoring %d bus position(s) older than %.0fs",
                      stale, position_max_age_sec)

    for bus in fresh:
        for stop_id in schedule.stop_order:
            stop = schedule.stops[stop_id]
            geo = geo_locality(bus.location, stop.location, radius_m)

            # The visit this sample is judged against: the one scheduled
            # nearest to now. A bus dwelling at a stop keeps matching the same
            # visit, and the tracker pins the departure window at latch time
            # anyway, so a long dwell cannot drift onto the next visit.
            visit = schedule.nearest_visit(stop_id, now)
            if visit is None:
                continue
            arrival, departure = windows_for(
                visit, early_buffer_sec, late_buffer_sec, grace_sec)

            observations.append(
                Observation(
                    stop_id=stop_id,
                    vehicle_id=bus.vehicle_id,
                    now=now,
                    arrival=arrival,
                    departure=departure,
                    geo=geo,
                    scheduled_arrival=visit.arrival,
                    scheduled_departure=visit.departure,
                )
            )
    return observations


def count_buses(
    now: datetime, snapshot: LiveSnapshot, position_max_age_sec: float
) -> list[str]:
    """Names of the buses currently running the route.

    The live request is filtered to this route's rides, so the feed returns
    positions only for buses serving it.
    """
    return sorted(
        bus.name or bus.vehicle_id
        for bus in snapshot.fresh(now, position_max_age_sec)
    )


def distance_to_stop(bus_location: LatLng, schedule: RouteSchedule,
                     stop_id: str) -> float | None:
    """Metres from a bus to a stop — for diagnostics and logging."""
    stop = schedule.stops.get(stop_id)
    return None if stop is None else haversine_m(bus_location, stop.location)
