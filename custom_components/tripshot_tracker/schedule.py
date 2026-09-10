"""Build the day's physical stop visits from the published schedule.

This is the *only* source of scheduled times. Nothing here reads the live
feed's own verdicts (`expectedArrivalTime`, `lateBySec`, `stopStatus`) — those
are the vendor's opinion about lateness, and we compute our own.

doc: schedule.visits, api.models.schedule
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone, tzinfo
from typing import Any

from .locality import LatLng
from .overrides import fixes_for

_LOGGER = logging.getLogger(__name__)

#: Longest gap that can still be one physical visit. Scheduled layovers on a
#: real route run to ~10 minutes; anything beyond this is the bus going away
#: and coming back, which is two visits. Bounding the merge matters because
#: one ride ending at a terminal and the next starting there hours later would
#: otherwise collapse into a single multi-hour "visit", erasing the later
#: arrival entirely.
MAX_MERGE_GAP_SEC = 1800

#: "HH:MM:SS" with hours 0-47 — TimeOfDay allows an extended service day.
#: re.ASCII matters: a bare \d matches Unicode decimal digits, so without it
#: "١٠:00:00" would parse as 10:00:00.
_TIME_OF_DAY_RE = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2})$", re.ASCII)


@dataclass(frozen=True)
class Stop:
    """A stop. The geofence radius is ours, not the vendor's."""

    stop_id: str
    name: str
    location: LatLng


@dataclass(frozen=True)
class StopVisit:
    """One physical scheduled visit: the bus arrives, dwells, departs."""

    stop_id: str
    arrival: datetime
    departure: datetime

    @property
    def dwell_sec(self) -> float:
        return (self.departure - self.arrival).total_seconds()


@dataclass
class RouteSchedule:
    """Stops, and every scheduled visit to them, for one service day."""

    route_id: str
    route_name: str
    region_id: str | None
    day: date
    stops: dict[str, Stop]
    stop_order: list[str]
    visits: list[StopVisit]
    scheduled_ride_ids: list[str]

    def visits_for(self, stop_id: str) -> list[StopVisit]:
        return [v for v in self.visits if v.stop_id == stop_id]

    def nearest_visit(self, stop_id: str, when: datetime) -> StopVisit | None:
        """The visit to `stop_id` closest to `when`.

        Distance is measured to the whole scheduled interval, not to the
        arrival instant: a bus part-way through a long scheduled dwell is
        inside *this* visit, even once the next visit's arrival is nearer in
        absolute terms. Measuring to the arrival alone mismatched any sample
        past the midpoint whenever a dwell exceeded half the headway.
        """
        candidates = self.visits_for(stop_id)
        if not candidates:
            return None

        def distance(v: StopVisit) -> float:
            if v.arrival <= when <= v.departure:
                return 0.0
            if when < v.arrival:
                return (v.arrival - when).total_seconds()
            return (when - v.departure).total_seconds()

        return min(candidates, key=lambda v: (distance(v), v.arrival))


def _parse_time_of_day(text: str) -> tuple[int, int, int] | None:
    """Parse "HH:MM:SS". Hours may exceed 23 — TimeOfDay allows 0-47.

    Strict on purpose. `int()` alone accepts leading signs, underscores,
    surrounding whitespace and non-ASCII digits, so "-1:00:00" would silently
    become the previous day and "99:99:99" a visit four days out — neither
    reaching the unparseable-time warning.
    """
    if not isinstance(text, str):
        return None
    match = _TIME_OF_DAY_RE.match(text)
    if match is None:
        return None
    hour, minute, second = (int(g) for g in match.groups())
    if not (0 <= hour < 48 and 0 <= minute < 60 and 0 <= second < 60):
        return None
    return hour, minute, second


def _instant(day: date, text: str, tz: tzinfo) -> datetime | None:
    """Turn a wall-clock "HH:MM:SS" on `day` into an absolute UTC instant.

    Hours >= 24 roll into the following day, which is how extended service
    days past midnight are expressed.

    The result is converted to UTC deliberately. Arithmetic and comparison on
    a zone-aware datetime whose tzinfo has DST is *wall-clock* arithmetic:
    subtracting ten minutes from 03:05 on a spring-forward day yields 02:55,
    an instant an hour and ten minutes earlier in real time, so an adherence
    window built that way comes out inverted. Two datetimes sharing one
    ZoneInfo also compare by wall clock, which hid the problem from the
    overlap validation. Normalising here makes every downstream window,
    comparison and sort operate on real instants.
    """
    parsed = _parse_time_of_day(text)
    if parsed is None:
        return None
    hour, minute, second = parsed
    base = datetime(day.year, day.month, day.day, tzinfo=tz)
    local = base + timedelta(hours=hour, minutes=minute, seconds=second)
    return local.astimezone(timezone.utc)


def _merge_into_visits(entries: list[tuple[str, datetime, int]]) -> list[StopVisit]:
    """Collapse scheduled stop entries into physical visits.

    `entries` is (stop_id, arrival instant, waitTimeSec), in time order.

    doc: schedule.visits#merge-rule

    Two entries at the same stop belong to the same physical visit when no
    visit to a *different* stop falls between them — the bus has to drive
    somewhere else to end a visit. That rule needs no tuning threshold, which
    matters because the gaps it must span vary wildly:

      * 5 seconds  — a drop-off entry immediately followed by a pick-up entry,
        and the tail of one ride meeting the head of the next at the same stop
      * 10 minutes — a scheduled layover at a turnaround

    while genuinely distinct visits to the same stop are a headway apart.

    The rule is bounded by MAX_MERGE_GAP_SEC, because "nothing between them"
    is not sufficient on its own: a morning ride *ending* at a terminal and an
    afternoon ride *starting* there are adjacent in the sorted list with no
    other stop between, and would otherwise merge into one multi-hour visit,
    erasing the afternoon arrival. The bound sits far above any real layover
    and far below any service gap.
    """
    visits: list[StopVisit] = []
    for stop_id, arrival, wait in entries:
        departure = arrival + timedelta(seconds=max(0, wait))
        if (
            visits
            and visits[-1].stop_id == stop_id
            and (arrival - visits[-1].departure).total_seconds()
            <= MAX_MERGE_GAP_SEC
        ):
            prev = visits[-1]
            visits[-1] = StopVisit(
                stop_id=stop_id,
                arrival=min(prev.arrival, arrival),
                departure=max(prev.departure, departure),
            )
        else:
            visits.append(StopVisit(stop_id, arrival, departure))
    return visits


def stops_only(schedule: RouteSchedule, day: date) -> RouteSchedule:
    """The same stops, for a day the route does not run.

    doc: schedule.visits#no-service-days

    Keeping the stops keeps the entities alive across a weekend or holiday;
    dropping the visits is what stops yesterday's timetable being matched
    against today's clock, which would otherwise classify any bus standing at a
    stop against a visit a day away.
    """
    return RouteSchedule(
        route_id=schedule.route_id,
        route_name=schedule.route_name,
        region_id=schedule.region_id,
        day=day,
        stops=dict(schedule.stops),
        stop_order=list(schedule.stop_order),
        visits=[],
        scheduled_ride_ids=[],
    )


def _apply_overrides(
    entries: list[tuple[str, datetime, int]],
    route_id: str,
    day: date,
    tz: tzinfo,
    stops: dict[str, Stop],
) -> list[tuple[str, datetime, int]]:
    """Supplement the API's entries with any registered corrections.

    doc: schedule.visits#overrides

    Skipped entirely when the API returned nothing for this day — that means
    the route does not run, and injecting a visit would invent service.
    Skipped per-fix when the stop is not part of this route's stops, or when
    an equivalent entry already exists — so an upstream correction quietly
    retires the override instead of duplicating it.
    """
    fixes = fixes_for(route_id)
    if not fixes or not entries:
        return entries

    existing = {(stop_id, when) for stop_id, when, _ in entries}
    supplemented = list(entries)
    for fix in fixes:
        when = _instant(day, fix.arrival, tz)
        if when is None:
            _LOGGER.warning("override for %s has an unparseable time %r",
                            fix.stop_id, fix.arrival)
            continue
        if fix.stop_id not in stops:
            _LOGGER.debug(
                "override names stop %s, which this route does not serve; "
                "skipping", fix.stop_id)
            continue
        if (fix.stop_id, when) in existing:
            _LOGGER.debug(
                "override for %s at %s already present upstream; skipping",
                fix.stop_id, fix.arrival)
            continue
        supplemented.append((fix.stop_id, when, max(0, fix.wait_sec)))
        _LOGGER.info("applied timetable override: %s at %s (%s)",
                     fix.stop_id, fix.arrival, fix.reason.split(".")[0])
    return supplemented


def build_schedule(
    data: dict[str, Any],
    route_id: str,
    route_name: str,
    day: date,
    tz: tzinfo,
) -> RouteSchedule:
    """Parse GET /v1/p/routeServiceBundle into stops and physical visits."""
    region_id: str | None = None
    for raw in data.get("routes") or []:
        if raw.get("routeId") == route_id:
            region_id = raw.get("regionId") or region_id
            route_name = raw.get("name") or route_name

    stops: dict[str, Stop] = {}
    stop_order: list[str] = []
    for service in data.get("routeServices") or []:
        for via in service.get("vias") or []:
            if not isinstance(via, dict):
                continue
            via_stop = via.get("ViaStop")
            if not isinstance(via_stop, dict):
                continue
            raw = via_stop.get("stop")
            if isinstance(raw, str):
                # The stop came back as a bare id rather than an embedded
                # object, which means the request omitted embedStops. Loud,
                # because the response otherwise looks structurally fine and
                # simply yields a schedule with no stops.
                _LOGGER.error(
                    "stop %s was not embedded in the response — the "
                    "routeServiceBundle request is missing embedStops=true. "
                    "See endpoints.BUNDLE_PINNED_PARAMS.", raw,
                )
                continue
            if not isinstance(raw, dict):
                continue
            stop_id = raw.get("stopId")
            loc = raw.get("location") or {}
            lt, lg = loc.get("lt"), loc.get("lg")
            if not stop_id or lt is None or lg is None:
                continue
            try:
                location = LatLng(float(lt), float(lg))
            except (TypeError, ValueError):
                _LOGGER.warning("unparseable location %r/%r for stop %s",
                                lt, lg, stop_id)
                continue
            if stop_id not in stops:
                stops[stop_id] = Stop(stop_id, raw.get("name") or stop_id,
                                      location)
                stop_order.append(stop_id)
            if region_id is None:
                region_id = raw.get("regionId")

    entries: list[tuple[str, datetime, int]] = []
    ride_ids: list[str] = []
    for group in data.get("scheduledRides") or []:
        for ride in group or []:
            if not isinstance(ride, dict) or not ride.get("scheduledRideId"):
                continue
            ride_ids.append(ride["scheduledRideId"])
            for entry in ride.get("stops") or []:
                # Entries are individually nullable: a ride may skip a via.
                if not isinstance(entry, dict):
                    continue
                stop_id, at = entry.get("stop"), entry.get("arrivalTime")
                if not stop_id or not at:
                    continue
                when = _instant(day, at, tz)
                if when is None:
                    _LOGGER.warning("unparseable arrivalTime %r at stop %s",
                                    at, stop_id)
                    continue
                try:
                    wait = int(entry.get("waitTimeSec") or 0)
                except (TypeError, ValueError):
                    _LOGGER.warning(
                        "unparseable waitTimeSec %r at stop %s; assuming 0",
                        entry.get("waitTimeSec"), stop_id)
                    wait = 0
                entries.append((stop_id, when, wait))

    # Sort by stop id as well as time: the API does not guarantee an order for
    # entries sharing an arrival time, and without the tiebreak the merged
    # visit structure would depend on incidental JSON ordering.
    entries = _apply_overrides(entries, route_id, day, tz, stops)

    # Sort by stop id as well as time: the API does not guarantee an order for
    # entries sharing an arrival time, and without the tiebreak the merged
    # visit structure would depend on incidental JSON ordering.
    entries.sort(key=lambda e: (e[1], e[0]))
    visits = _merge_into_visits(entries)

    schedule = RouteSchedule(
        route_id=route_id, route_name=route_name, region_id=region_id,
        day=day, stops=stops, stop_order=stop_order, visits=visits,
        scheduled_ride_ids=ride_ids,
    )
    _LOGGER.debug(
        "schedule %s: %d stops, %d scheduled entries -> %d physical visits",
        day, len(stops), len(entries), len(visits),
    )
    return schedule
