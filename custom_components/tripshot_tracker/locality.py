"""Pure locality functions — no I/O, no Home Assistant, no clock.

Two reductions:

    geo:  (bus position, stop position, radius)                -> at_stop | not_at_stop
    time: (now, arrival window, departure window, geo state)   -> TimeLocality

Thresholds are ours. Nothing here consults the vendor's own lateness fields.

doc: semantics.time-locality, semantics.geo-locality
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

#: Mean earth radius, metres. Matches the great-circle model used to define
#: the stop geofences, so distances are comparable with mapping tools.
EARTH_RADIUS_M = 6371009.0

#: 1 international foot in metres — geofence size is configured in feet.
FEET_TO_M = 0.3048


class GeoLocality(str, Enum):
    """Whether a bus is inside a stop's geofence."""

    AT_STOP = "at_stop"
    NOT_AT_STOP = "not_at_stop"


class TimeLocality(str, Enum):
    """Schedule adherence verdict.

    `NA` is the resting state that stickiness latches out of and back into.
    """

    NA = "n/a"
    ARRIVE_EARLY = "arrive_early"
    ARRIVE_ON_TIME = "arrive_on_time"
    ARRIVE_LATE = "arrive_late"
    DEPART_EARLY = "depart_early"
    DEPART_ON_TIME = "depart_on_time"
    DEPART_LATE = "depart_late"


#: The six countable verdicts — every TimeLocality except NA.
COUNTED_STATES: tuple[TimeLocality, ...] = tuple(
    s for s in TimeLocality if s is not TimeLocality.NA
)


@dataclass(frozen=True)
class LatLng:
    """A WGS84 position. Field names mirror the wire keys `lt` / `lg`."""

    lt: float
    lg: float


@dataclass(frozen=True)
class TimeWindow:
    """A closed interval [start, end]."""

    start: datetime
    end: datetime

    def contains(self, when: datetime) -> bool:
        """Inclusive on both ends."""
        return self.start <= when <= self.end


def arrival_window(
    scheduled_arrival: datetime,
    early_buffer_sec: float,
    grace_sec: float = 0.0,
) -> TimeWindow:
    """The window in which arriving counts as on time.

    doc: semantics.time-locality — the buffer extends the window *earlier*
    only: a bus may show up to `early_buffer_sec` ahead of schedule and still
    be on time, and past the scheduled instant it is late.

    doc: semantics.time-locality#grace

    `grace_sec` extends the strict late edge by the measurement precision.
    Without it the edge sits exactly on the scheduled instant while an
    observed crossing lags the real one by up to a poll interval, so a bus
    arriving precisely on time is routinely recorded late — the verdict would
    be reporting our sampling rate rather than the bus.
    """
    return TimeWindow(
        scheduled_arrival - timedelta(seconds=early_buffer_sec),
        scheduled_arrival + timedelta(seconds=grace_sec),
    )


def departure_window(
    scheduled_departure: datetime,
    late_buffer_sec: float,
    grace_sec: float = 0.0,
) -> TimeWindow:
    """The window in which departing counts as on time.

    doc: semantics.time-locality — the buffer extends the window *later* only:
    leaving before the scheduled instant strands riders and is early, leaving
    within `late_buffer_sec` after it is on time.

    `grace_sec` extends the strict early edge by the measurement precision,
    for the same reason as the arrival window's late edge.
    """
    return TimeWindow(
        scheduled_departure - timedelta(seconds=grace_sec),
        scheduled_departure + timedelta(seconds=late_buffer_sec),
    )


def schedule_is_consistent(
    scheduled_arrival: datetime, scheduled_departure: datetime
) -> bool:
    """True when a visit's scheduled departure is not before its arrival.

    doc: semantics.time-locality — this is the invariant that matters, and it
    is about the *schedule*, not the windows.

    An earlier version compared the window edges instead, requiring
    `arrival.end <= departure.start`. That stopped being meaningful once the
    measurement grace existed: grace widens both strict edges toward each
    other, so on a short-dwell visit the windows legitimately overlap. That
    overlap is harmless because the two windows classify *different events* —
    arrival is judged when a bus enters the geofence, departure when it
    leaves, never both from one sample — so no instant is ever ambiguous.
    """
    return scheduled_arrival <= scheduled_departure


def resolve_grace_sec(
    configured: float, poll_interval_sec: float, feed_lag_sec: float
) -> float:
    """The measurement grace actually in force.

    doc: semantics.time-locality#grace

    A negative `configured` means "follow the poll interval": the grace
    becomes `poll_interval + feed_lag`. Deriving rather than storing keeps it
    tied to the setting that justifies it — the poll interval is the dominant
    term in how coarsely a geofence crossing can be observed, so a grace that
    did not track it would go stale the moment the poll changed.

    `feed_lag` covers what remains even at an instantaneous poll: the bus
    reports its position periodically, and that fix takes time to reach the
    server's view.

    Any value >= 0 is used literally, so an explicit setting is never
    silently overridden.
    """
    if configured < 0:
        return max(0.0, poll_interval_sec) + max(0.0, feed_lag_sec)
    return configured


def haversine_m(a: LatLng, b: LatLng) -> float:
    """Great-circle distance in metres."""
    lat1, lat2 = math.radians(a.lt), math.radians(b.lt)
    dlat = lat2 - lat1
    dlng = math.radians(b.lg - a.lg)
    hav = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    )
    # Clamp guards against sqrt of a marginally-over-1 value from rounding.
    return 2.0 * EARTH_RADIUS_M * math.asin(math.sqrt(min(1.0, hav)))


def diameter_ft_to_radius_m(diameter_ft: float) -> float:
    """Convert a configured geofence diameter in feet to a radius in metres."""
    return diameter_ft * FEET_TO_M / 2.0


def geo_locality(
    bus: LatLng | None,
    stop: LatLng,
    radius_m: float,
) -> GeoLocality:
    """Reduce a position pair to at-stop / not-at-stop.

    doc: semantics.geo-locality#containment — inclusive boundary, and note
    there is no hysteresis: see semantics.time-locality#flicker.

    A missing position is not-at-stop rather than an error: an absent or stale
    position simply tells us nothing.
    """
    if bus is None:
        return GeoLocality.NOT_AT_STOP
    if haversine_m(bus, stop) <= radius_m:
        return GeoLocality.AT_STOP
    return GeoLocality.NOT_AT_STOP


def classify_arrival(now: datetime, window: TimeWindow) -> TimeLocality:
    """Classify an arrival observed at `now`."""
    if now < window.start:
        return TimeLocality.ARRIVE_EARLY
    if window.contains(now):
        return TimeLocality.ARRIVE_ON_TIME
    return TimeLocality.ARRIVE_LATE


def classify_departure(now: datetime, window: TimeWindow) -> TimeLocality:
    """Classify a departure observed at `now`."""
    if now < window.start:
        return TimeLocality.DEPART_EARLY
    if window.contains(now):
        return TimeLocality.DEPART_ON_TIME
    return TimeLocality.DEPART_LATE


def time_locality(
    now: datetime,
    arrival: TimeWindow,
    departure: TimeWindow,
    geo: GeoLocality,
) -> TimeLocality:
    """Reduce (now, windows, geo state) to a verdict.

    doc: semantics.time-locality#firing-cases

    A bus that is not at the stop yields NA: from a single sample there is no
    way to distinguish "not arrived yet" from "already gone".

    While at the stop the verdict always describes the *arrival*. A bus still
    standing at a stop has not departed, however overdue it is, so departure
    is classified on the leaving edge by RouteTracker instead.

    `departure` is unused today. It stays in the signature because it is part
    of the specified reduction, and because a rule that needs it should not
    have to change every call site.
    """
    del departure  # see docstring
    if geo is GeoLocality.NOT_AT_STOP:
        return TimeLocality.NA
    return classify_arrival(now, arrival)
