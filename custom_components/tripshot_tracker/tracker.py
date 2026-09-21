"""Sticky per-(stop, bus) state machine and the counters it feeds.

Pure: no I/O and no implicit clock, so the stickiness contract is testable by
feeding it observations.

doc: semantics.time-locality#stickiness

Contract
--------
For one (stop, bus) pair:

* NA -> X   latches X and counts it exactly once.
* while latched, further observations neither re-classify nor re-count.
* X -> NA   is the leaving edge: the departure is classified at that moment
  against the same visit the arrival was judged against, and counted once.

So a (stop, bus, visit) contributes at most one arrival and one departure,
which is what keeps the totals interpretable.

Counters accumulate for the life of the config entry. They are seeded from
Home Assistant's restored entity state on restart and never reset on their own.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from .locality import (
    COUNTED_STATES,
    GeoLocality,
    TimeLocality,
    TimeWindow,
    classify_departure,
    time_locality,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Observation:
    """One sample of one (stop, bus) pair against one scheduled visit.

    The windows say whether the bus is on time; the scheduled instants say by
    how much it is off. They are not interchangeable — a window edge sits a
    buffer or a measurement grace away from the instant it was built from, so
    measuring deviation against an edge reports a bus that is exactly on time
    as being off by the grace.
    """

    stop_id: str
    vehicle_id: str
    now: datetime
    arrival: TimeWindow
    departure: TimeWindow
    geo: GeoLocality
    #: The scheduled instants the windows were built around.
    scheduled_arrival: datetime
    scheduled_departure: datetime


def _is_arrival(state: TimeLocality) -> bool:
    """Whether a verdict describes an arrival rather than a departure."""
    return state in (
        TimeLocality.ARRIVE_EARLY,
        TimeLocality.ARRIVE_ON_TIME,
        TimeLocality.ARRIVE_LATE,
    )


@dataclass(frozen=True)
class CountedVerdict:
    """A verdict at the moment it was counted, with enough context to act on.

    Emitted so the integration can fire a Home Assistant event. Counters are a
    poor trigger for "this just happened": an automation would have to diff
    consecutive states, and a restart that restores a counter from 0 to N
    looks exactly like N events firing at once.
    """

    stop_id: str
    vehicle_id: str
    verdict: TimeLocality
    at: datetime
    scheduled: datetime
    #: Signed seconds from the SCHEDULED instant -- not from a window edge.
    #: Negative is early, positive is late, and zero means exactly on time.
    deviation_sec: float

    @property
    def is_arrival(self) -> bool:
        return _is_arrival(self.verdict)


@dataclass
class _Latch:
    """Sticky state for a single (stop, bus) pair."""

    state: TimeLocality = TimeLocality.NA
    departure: TimeWindow | None = None
    #: Scheduled departure of the visit the arrival was judged against, pinned
    #: alongside its window so a long dwell cannot drift onto the next visit.
    scheduled_departure: datetime | None = None
    #: When this pair was last observed with a fresh position. Drives expiry.
    last_seen: datetime | None = None
    #: A geofence crossing seen but not yet confirmed by enough polls.
    pending_geo: GeoLocality | None = None
    #: When that crossing was FIRST seen. The verdict is timestamped here, not
    #: at the confirming poll, so requiring confirmation costs no accuracy.
    pending_since: datetime | None = None
    pending_count: int = 0

    def clear_pending(self) -> None:
        self.pending_geo = None
        self.pending_since = None
        self.pending_count = 0


@dataclass
class RouteTracker:
    """Accumulates per-stop counters across every bus on a route."""

    counts: dict[str, dict[TimeLocality, int]] = field(default_factory=dict)
    #: The most recent counted verdict per (stop, kind), for the deviation
    #: metric. Arrivals and departures are kept apart because they measure
    #: different things -- a bus can arrive late and leave early at the same
    #: stop -- so a single series mixing them plots two meanings as one.
    latest: dict[tuple[str, str], CountedVerdict] = field(default_factory=dict)
    _latches: dict[tuple[str, str], _Latch] = field(default_factory=dict)

    # -- counter access ---------------------------------------------------
    def counts_for(self, stop_id: str) -> dict[TimeLocality, int]:
        """Counters for one stop, zero-filled for every countable state."""
        got = self.counts.get(stop_id, {})
        return {s: got.get(s, 0) for s in COUNTED_STATES}

    def count(self, stop_id: str, state: TimeLocality) -> int:
        return self.counts.get(stop_id, {}).get(state, 0)

    def latest_for(self, stop_id: str, kind: str) -> CountedVerdict | None:
        """The most recent arrival or departure verdict at a stop.

        `kind` is "arrival" or "departure".
        """
        return self.latest.get((stop_id, kind))

    def seed(self, stop_id: str, state: TimeLocality, value: int) -> None:
        """Restore a counter from Home Assistant's saved state.

        Called once per entity on startup so a restart does not zero the
        history. Only ever raises a counter, so a partially restored set
        cannot go backwards.
        """
        if value <= 0:
            return
        current = self.counts.setdefault(stop_id, {}).get(state, 0)
        if value > current:
            self.counts[stop_id][state] = value
            _LOGGER.debug("restored %s/%s = %d", stop_id, state.value, value)

    def _bump(self, stop_id: str, state: TimeLocality) -> None:
        self.counts.setdefault(stop_id, {}).setdefault(state, 0)
        self.counts[stop_id][state] += 1

    def state_for(self, stop_id: str) -> TimeLocality:
        """The sticky state currently shown for a stop.

        A stop can host more than one bus at once; report the first latched
        one so the entity shows an active verdict rather than flickering.
        """
        # Sorted by bus id so the reported state does not depend on the order
        # buses happened to first appear in the feed.
        for (sid, _bus), latch in sorted(self._latches.items()):
            if sid == stop_id and latch.state is not TimeLocality.NA:
                return latch.state
        return TimeLocality.NA

    def buses_at(self, stop_id: str) -> list[str]:
        """Ids of buses currently latched at a stop."""
        return sorted(
            bus for (sid, bus), latch in self._latches.items()
            if sid == stop_id and latch.state is not TimeLocality.NA
        )

    # -- lifecycle --------------------------------------------------------
    def reset(self) -> None:
        """Clear everything. Not called automatically."""
        _LOGGER.info("resetting all counters and latches")
        self.counts.clear()
        self.latest.clear()
        self._latches.clear()

    def expire_stale(self, now: datetime, grace_sec: float) -> int:
        """Drop latches for buses not observed recently. Returns how many.

        doc: semantics.time-locality#no-fire

        Deliberately an expiry with a grace period rather than dropping a bus
        the moment it is absent from one poll. A bus can vanish for a single
        cycle — a missed position report, or a bus sitting at a terminal
        between rides while the feed is scoped to this route's rides — and
        come back without having moved. Dropping the latch immediately would
        let the very next poll see NA -> at-stop again and count a **second**
        arrival for one physical visit.

        Once a bus really is gone, its latch is dropped **silently**: no
        departure is counted, because none was observed. Inventing a departure
        time from the moment the feed happened to recover would book it at the
        wrong instant, and possibly at a stop the bus left hours earlier.
        """
        dropped = 0
        for key, latch in list(self._latches.items()):
            if latch.last_seen is not None and (
                    now - latch.last_seen).total_seconds() <= grace_sec:
                continue
            if latch.state is not TimeLocality.NA:
                _LOGGER.info(
                    "bus %s not seen at %s for over %.0fs; dropping latch %s "
                    "without counting a departure",
                    key[1], key[0], grace_sec, latch.state.value,
                )
            del self._latches[key]
            dropped += 1
        return dropped

    # -- the state machine ------------------------------------------------
    def observe(self, obs: Observation, *, count: bool = True,
                confirmations: int = 1) -> list[TimeLocality]:
        """Fold one observation in; return the verdicts counted by it."""
        return [v.verdict for v in self.observe_detailed(
            obs, count=count, confirmations=confirmations)]

    def observe_detailed(
        self, obs: Observation, *, count: bool = True, confirmations: int = 1
    ) -> list[CountedVerdict]:
        """Fold one observation in; return the verdicts counted by it.

        Normally empty — verdicts are produced only on the two edges.

        `confirmations` is how many consecutive polls must agree before a
        geofence crossing is acted on. doc: semantics.geo-locality#debounce

        With 1 the transition is immediate. With 2 or more, a bus hovering on
        the geofence boundary while GPS noise pushes it across cannot generate
        a departure and a fresh arrival on each oscillation — the single
        failure mode that *inflates* counters rather than dropping them. The
        cost is that a genuine crossing is recognised a poll later, but it is
        still *timestamped* at the first poll that saw it, so the recorded
        time is unchanged.

        `count=False` adopts the current state immediately, without
        confirmation and without counting — see the priming note below.
        """
        key = (obs.stop_id, obs.vehicle_id)
        latch = self._latches.setdefault(key, _Latch())
        latch.last_seen = obs.now
        emitted: list[CountedVerdict] = []

        settled_at_stop = latch.state is not TimeLocality.NA
        observed_at_stop = obs.geo is GeoLocality.AT_STOP

        # Priming: adopt what is there, silently and without waiting.
        if not count:
            if observed_at_stop and not settled_at_stop:
                latch.state = time_locality(
                    obs.now, obs.arrival, obs.departure, obs.geo)
                latch.departure = obs.departure
                latch.clear_pending()
                _LOGGER.info(
                    "bus %s already at %s on the first poll; adopting %s "
                    "without counting an arrival",
                    obs.vehicle_id, obs.stop_id, latch.state.value,
                )
            return emitted

        if observed_at_stop == settled_at_stop:
            # Agrees with the settled state; any flicker has resolved itself.
            if latch.pending_count:
                _LOGGER.debug(
                    "bus %s at %s: unconfirmed crossing withdrawn after %d "
                    "poll(s)", obs.vehicle_id, obs.stop_id, latch.pending_count,
                )
            latch.clear_pending()
            return emitted

        # Differs from the settled state: a crossing, pending confirmation.
        if latch.pending_geo is not obs.geo:
            latch.pending_geo = obs.geo
            latch.pending_since = obs.now
            latch.pending_count = 1
        else:
            latch.pending_count += 1

        if latch.pending_count < max(1, confirmations):
            _LOGGER.debug(
                "bus %s at %s: crossing to %s seen %d/%d times, awaiting "
                "confirmation", obs.vehicle_id, obs.stop_id, obs.geo.value,
                latch.pending_count, confirmations,
            )
            return emitted

        at = latch.pending_since or obs.now

        if observed_at_stop:
            verdict = time_locality(at, obs.arrival, obs.departure, obs.geo)
            latch.state = verdict
            # Pin the departure of the visit the arrival was judged against,
            # so a long dwell cannot drift onto the next visit.
            latch.departure = obs.departure
            latch.scheduled_departure = obs.scheduled_departure
            self._bump(obs.stop_id, verdict)
            counted = CountedVerdict(
                stop_id=obs.stop_id, vehicle_id=obs.vehicle_id,
                verdict=verdict, at=at, scheduled=obs.scheduled_arrival,
                deviation_sec=(at - obs.scheduled_arrival).total_seconds(),
            )
            self.latest[(obs.stop_id, "arrival")] = counted
            emitted.append(counted)
            _LOGGER.info(
                "bus %s arrived at %s: %s (at=%s, window=%s..%s)",
                obs.vehicle_id, obs.stop_id, verdict.value, at.isoformat(),
                obs.arrival.start.isoformat(), obs.arrival.end.isoformat(),
            )
        else:
            window = latch.departure or obs.departure
            scheduled = latch.scheduled_departure or obs.scheduled_departure
            verdict = classify_departure(at, window)
            self._bump(obs.stop_id, verdict)
            counted = CountedVerdict(
                stop_id=obs.stop_id, vehicle_id=obs.vehicle_id,
                verdict=verdict, at=at, scheduled=scheduled,
                deviation_sec=(at - scheduled).total_seconds(),
            )
            self.latest[(obs.stop_id, "departure")] = counted
            emitted.append(counted)
            _LOGGER.info(
                "bus %s departed %s: %s (at=%s, window=%s..%s)",
                obs.vehicle_id, obs.stop_id, verdict.value, at.isoformat(),
                window.start.isoformat(), window.end.isoformat(),
            )
            latch.state = TimeLocality.NA
            latch.departure = None
            latch.scheduled_departure = None

        latch.clear_pending()
        return emitted

    def observe_all(self, observations: list[Observation], *,
                    count: bool = True,
                    confirmations: int = 1) -> list[CountedVerdict]:
        """Fold in a whole polling cycle; return everything it counted."""
        counted: list[CountedVerdict] = []
        for obs in observations:
            counted.extend(self.observe_detailed(
                obs, count=count, confirmations=confirmations))
        return counted
