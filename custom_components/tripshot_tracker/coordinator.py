"""Polling coordinator: fetch the schedule and bus positions, fold them in.

doc: integration.request-plan
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone, tzinfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import TripShotApi, TripShotError
from .const import (
    CONF_ARRIVAL_EARLY_BUFFER_SEC,
    CONF_TIMEZONE,
    EVENT_VERDICT,
    CONF_DEPARTURE_LATE_BUFFER_SEC,
    CONF_CONFIRM_POLLS,
    CONF_GEOFENCE_DIAMETER_FT,
    CONF_MEASUREMENT_GRACE_SEC,
    FEED_LAG_SEC,
    CONF_POLL_INTERVAL_SEC,
    CONF_POSITION_MAX_AGE_SEC,
    PROBE_WINDOW_DAYS,
    SCHEDULE_REFRESH_SEC,
    TUNABLES,
)
from .locality import (
    GeoLocality,
    diameter_ft_to_radius_m,
    resolve_grace_sec,
)
from .models import LiveSnapshot, parse_live_status
from .observations import (
    build_observations,
    count_buses,
    distance_to_stop,
    validate_schedule,
)
from .schedule import RouteSchedule, build_schedule, stops_only
from .tracker import RouteTracker

_LOGGER = logging.getLogger(__name__)


def describe_bundle(raw: dict) -> str:
    """One-line summary of what a routeServiceBundle actually contained.

    An unknown route id and a day the route does not run both come back as an
    empty HTTP 200, so the counts are what distinguish "nothing was returned"
    from "nothing was scheduled".
    """
    services = [s for s in (raw.get("routeServices") or [])
                if isinstance(s, dict)]
    vias = [v for s in services for v in (s.get("vias") or [])
            if isinstance(v, dict)]
    return (
        f"routeServices={len(services)} "
        f"routes={len(raw.get('routes') or [])} "
        f"rides={sum(len(g or []) for g in (raw.get('scheduledRides') or []))} "
        f"vias={len(vias)} "
        f"viaStops={sum(1 for v in vias if 'ViaStop' in v)}"
    )


class TripShotCoordinator(DataUpdateCoordinator[None]):
    """Polls bus positions, and the schedule every 300s."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: TripShotApi,
        route_id: str,
        route_name: str,
        region_id: str | None,
    ) -> None:
        self.entry = entry
        super().__init__(
            hass,
            _LOGGER,
            name=f"TripShot {route_name}",
            update_interval=timedelta(seconds=self._opt(CONF_POLL_INTERVAL_SEC)),
        )
        self.api = api
        self.route_id = route_id
        self.route_name = route_name
        self.region_id = region_id

        self.schedule: RouteSchedule | None = None
        self.snapshot: LiveSnapshot | None = None
        self.tracker = RouteTracker()
        self.bus_count: int = 0
        self.bus_names: list[str] = []
        self.schedule_problems: list[str] = []
        self.no_service_today = False
        #: Device registry id of the route device, set during setup so stop
        #: devices can reference it with via_device_id.
        self.route_device_id: str | None = None

        self._schedule_day: date | None = None
        self._schedule_fetched: datetime | None = None
        # doc: semantics.time-locality#priming — the first cycle only adopts
        # what it finds, so a restart mid-dwell cannot double-count an arrival.
        self._primed = False
        self._last_bus_count: int | None = None
        self._tz: tzinfo = dt_util.DEFAULT_TIME_ZONE
        self._tz_name: str | None = None

    @property
    def timezone(self) -> tzinfo:
        """The transit system's timezone, as resolved."""
        return self._tz

    @property
    def service_day(self) -> date:
        """The service day currently being tracked."""
        return self._service_day()

    @property
    def primed(self) -> bool:
        """Whether the first poll has been folded in."""
        return self._primed

    # -- settings ---------------------------------------------------------
    def _opt(self, key: str) -> float:
        """Read a tunable, falling back to its default."""
        return float(self.entry.options.get(key, TUNABLES[key]))

    @property
    def radius_m(self) -> float:
        return diameter_ft_to_radius_m(self._opt(CONF_GEOFENCE_DIAMETER_FT))

    @property
    def early_buffer_sec(self) -> float:
        return self._opt(CONF_ARRIVAL_EARLY_BUFFER_SEC)

    @property
    def late_buffer_sec(self) -> float:
        return self._opt(CONF_DEPARTURE_LATE_BUFFER_SEC)

    @property
    def position_max_age_sec(self) -> float:
        return self._opt(CONF_POSITION_MAX_AGE_SEC)

    @property
    def poll_interval_sec(self) -> float:
        return self._opt(CONF_POLL_INTERVAL_SEC)

    @property
    def confirm_polls(self) -> int:
        """Consecutive polls that must agree before a crossing is acted on."""
        return max(1, int(self._opt(CONF_CONFIRM_POLLS)))

    @property
    def grace_sec(self) -> float:
        """Tolerance on the strict edge of both windows.

        doc: semantics.time-locality#grace

        Derived from the poll interval by default, because that is what the
        grace is *for*: the poll interval is the dominant term in how coarsely
        a geofence crossing can be observed. Deriving it keeps the two from
        drifting apart — lowering the poll tightens the tolerance
        automatically, instead of leaving a stale over-tolerant number behind.

        FEED_LAG_SEC is added because the poll is not the only lag: the bus
        reports its position roughly every 11s and that fix takes about 5s to
        reach the server's view, so even an instantaneous poll would be
        looking at slightly stale truth.

        A value >= 0 overrides the derivation and is used literally.
        """
        configured = self._opt(CONF_MEASUREMENT_GRACE_SEC)
        resolved = resolve_grace_sec(
            configured, self.poll_interval_sec, FEED_LAG_SEC)
        if 0 <= configured < self.poll_interval_sec:
            _LOGGER.debug(
                "measurement grace %.0fs is below the %.0fs poll interval, so "
                "it cannot cover the sampling lag; arrivals may be recorded "
                "late and departures early on that account alone",
                configured, self.poll_interval_sec,
            )
        return resolved

    def apply_options(self) -> None:
        """Adopt changed options without a reload.

        The buffers, geofence and freshness bound are read live by `_opt`, so
        only the poll interval needs adopting here. The schedule is
        revalidated because the buffers feed that check.
        """
        interval = timedelta(seconds=self._opt(CONF_POLL_INTERVAL_SEC))
        if interval != self.update_interval:
            _LOGGER.info("poll interval %s -> %s", self.update_interval, interval)
            self.update_interval = interval

        if str(self.entry.options.get(CONF_TIMEZONE) or "").strip() != (
                self._tz_name or ""):
            # Forces _ensure_timezone to re-resolve and the schedule to be
            # rebuilt against the new zone on the next poll.
            self._schedule_fetched = None

        if self.schedule is not None:
            self.schedule_problems = validate_schedule(
                self.schedule, self.early_buffer_sec, self.late_buffer_sec,
                self.grace_sec)
            for problem in self.schedule_problems:
                _LOGGER.warning("schedule validation: %s", problem)

        _LOGGER.info(
            "options applied: geofence radius %.1fm, buffers early=%.0fs "
            "late=%.0fs, max position age %.0fs, poll %.0fs",
            self.radius_m, self.early_buffer_sec, self.late_buffer_sec,
            self.position_max_age_sec, interval.total_seconds(),
        )

    # -- helpers ----------------------------------------------------------
    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    async def _ensure_timezone(self) -> None:
        """Resolve the configured transit timezone, once per change.

        Resolved through dt_util rather than constructing a ZoneInfo directly:
        loading zone data reads files, which must not happen on the event loop.
        """
        name = str(self.entry.options.get(CONF_TIMEZONE) or "").strip()
        if name == (self._tz_name or ""):
            return
        if not name:
            self._tz = dt_util.DEFAULT_TIME_ZONE
            self._tz_name = ""
            _LOGGER.debug("using Home Assistant's timezone (%s)", self._tz)
            return
        resolved = await dt_util.async_get_time_zone(name)
        if resolved is None:
            _LOGGER.warning(
                "unknown timezone %r configured for %s; falling back to Home "
                "Assistant's (%s). Schedule times will be wrong if the transit "
                "system is not in that zone.",
                name, self.route_name, dt_util.DEFAULT_TIME_ZONE,
            )
            self._tz = dt_util.DEFAULT_TIME_ZONE
        else:
            self._tz = resolved
            _LOGGER.info("using transit timezone %s for %s", name,
                         self.route_name)
        self._tz_name = name

    def _service_day(self) -> date:
        """Today, in the TRANSIT SYSTEM's timezone.

        The service day and the schedule's wall-clock times belong to the
        transit system, not to wherever Home Assistant happens to be. Using
        HA's timezone is only right when the two coincide; near midnight, for
        a route in another zone, it would request the wrong day's timetable.
        """
        return datetime.now(self._tz).date()

    async def _ensure_schedule(self, now: datetime) -> None:
        """(Re)fetch the schedule on day rollover or when it goes stale."""
        day = self._service_day()
        stale = (
            self.schedule is None
            or self._schedule_day != day
            or self._schedule_fetched is None
            or (now - self._schedule_fetched).total_seconds() >= SCHEDULE_REFRESH_SEC
        )
        if not stale:
            return

        raw = await self.api.route_service_bundle(self.route_id, day)
        schedule = build_schedule(
            raw, self.route_id, self.route_name, day, self._tz
        )

        if not schedule.stops:
            _LOGGER.debug("empty schedule for %s: %s", day,
                          describe_bundle(raw))
            # doc: schedule.visits#no-service-days — the API returns no
            # routeServices for a day the route does not
            # run — a weekend, a holiday, or outside the service period. That
            # is a normal state, not a failure: keep the stops so the entities
            # and their counters survive, and drop the visits so yesterday's
            # timetable is never matched against today's clock.
            known = self.schedule or await self._probe_stops(day)
            if known is None or not known.stops:
                raise UpdateFailed(await self._diagnose_empty(day, raw))
            schedule = stops_only(known, day)
            if not self.no_service_today or self._schedule_day != day:
                _LOGGER.info(
                    "no service scheduled for %s on %s; keeping %d stop(s), "
                    "no visits to track today",
                    self.route_name, day, len(schedule.stops),
                )
            self.no_service_today = True
        else:
            self.no_service_today = False
        #: Device registry id of the route device, set during setup so stop
        #: devices can reference it with via_device_id.
        self.route_device_id: str | None = None

        self.schedule = schedule
        self._schedule_day = day
        self._schedule_fetched = now

        # Counters are cumulative and deliberately survive the day rollover.
        self.schedule_problems = validate_schedule(
            schedule, self.early_buffer_sec, self.late_buffer_sec,
            self.grace_sec,
        )
        for problem in self.schedule_problems:
            _LOGGER.warning("schedule validation: %s", problem)

        _LOGGER.debug(
            "schedule for %s (tz %s): %d stops, %d visits, %d rides — %s",
            day, self._tz, len(schedule.stops), len(schedule.visits),
            len(schedule.scheduled_ride_ids), ", ".join(
                f"{schedule.stops[s].name}:{len(schedule.visits_for(s))}"
                for s in schedule.stop_order),
        )

    async def _diagnose_empty(self, day: date, raw: dict) -> str:
        """Explain an empty schedule in terms of what was actually observed.

        Both an unknown route id and a genuine service gap return an empty
        HTTP 200 from the bundle endpoint, so this asks the route endpoint
        which one it is rather than asserting a cause.
        """
        summary = describe_bundle(raw)
        end = day + timedelta(days=PROBE_WINDOW_DAYS)
        where = (f"instance {self.api.instance_id} at {self.api.base_url}"
                 if self.api.instance_id is not None else self.api.base_url)

        try:
            route = await self.api.get_route(self.route_id)
        except TripShotError as err:
            return (
                f"no stops for route {self.route_id} on {day} "
                f"(bundle: {summary}); could not check whether the route "
                f"still exists: {err}"
            )

        if route is None:
            return (
                f"{where} has no route {self.route_id}. The configured route "
                f"may have been removed or renamed by the operator, or the "
                f"entry may point at a different transit system. Re-add the "
                f"integration to pick a current route. "
                f"(bundle for {day}: {summary})"
            )

        name = route.get("name") or route.get("publicName") or self.route_name
        return (
            f"route '{name}' exists, but has no scheduled service between "
            f"{day} and {end} (bundle for {day}: {summary}). That normally "
            f"means a holiday, a term break, or a suspended route. Retrying; "
            f"no action needed if service resumes."
        )

    async def _probe_stops(self, day: date) -> RouteSchedule | None:
        """Learn the route's stops when today has no service.

        Only needed on a first setup that lands on a non-service day — with no
        previous schedule to borrow stops from, there would otherwise be
        nothing to build entities out of. A week-long window covers any normal
        weekend or single holiday.
        """
        end = day + timedelta(days=PROBE_WINDOW_DAYS)
        _LOGGER.debug("probing %s..%s for this route's stops", day, end)
        raw = await self.api.route_service_bundle(self.route_id, day, end_day=end)
        probed = build_schedule(
            raw, self.route_id, self.route_name, day, self._tz
        )
        _LOGGER.debug("probe %s..%s returned %s", day, end,
                      describe_bundle(raw))
        if probed.stops:
            _LOGGER.debug("probe found %d stop(s)", len(probed.stops))
            # The window spans several days, so the visits it carries are a
            # week's entries collapsed onto one day. Only the stops are wanted.
            return stops_only(probed, day)
        return None

    def _ride_ids(self, day: date) -> list[str]:
        """doc: integration.request-plan — RideId is "<scheduledRideId>:<day>".

        Used only to scope the live request to this route; the rides
        themselves are not read.
        """
        assert self.schedule is not None
        return [f"{rid}:{day.isoformat()}"
                for rid in self.schedule.scheduled_ride_ids]

    # -- the poll ---------------------------------------------------------
    async def _async_update_data(self) -> None:
        now = self._now()
        # Expire before anything can return early. A day with no service
        # takes the `not ride_ids` path below, and a latch left over from the
        # last service day would otherwise be held all weekend and then
        # resolved on Monday against a departure window three days stale.
        # Grace comfortably exceeds one poll, so a single missed cycle does
        # not drop a latch and let the bus be counted as arriving twice.
        grace = max(self.position_max_age_sec,
                    3 * self.update_interval.total_seconds()
                    if self.update_interval else 0)
        expired = self.tracker.expire_stale(now, grace)
        if expired:
            _LOGGER.debug("expired %d stale latch(es) (grace %.0fs)",
                          expired, grace)

        try:
            await self._ensure_timezone()
            await self._ensure_schedule(now)
            assert self.schedule is not None

            region_id = self.region_id or self.schedule.region_id
            if not region_id:
                raise UpdateFailed("no regionId available for this route")

            ride_ids = self._ride_ids(self._service_day())
            if not ride_ids:
                _LOGGER.debug("no scheduled rides today for %s", self.route_name)
                self.snapshot = LiveSnapshot(timestamp=now)
                self.bus_count = 0
                self.bus_names = []
                return

            raw = await self.api.live_status(region_id, ride_ids)
        except TripShotError as err:
            raise UpdateFailed(str(err)) from err

        snapshot = parse_live_status(raw)
        self.snapshot = snapshot

        observations = build_observations(
            now, self.schedule, snapshot,
            radius_m=self.radius_m,
            early_buffer_sec=self.early_buffer_sec,
            late_buffer_sec=self.late_buffer_sec,
            position_max_age_sec=self.position_max_age_sec,
            grace_sec=self.grace_sec,
        )
        if not self._primed:
            self.tracker.observe_all(observations, count=False)
            self._primed = True
            _LOGGER.info(
                "primed from first poll: adopted %d bus/stop state(s) without "
                "counting arrivals", len(observations),
            )
        else:
            for counted in self.tracker.observe_all(
                    observations, confirmations=self.confirm_polls):
                self._fire_verdict(counted, snapshot)

        self.bus_names = count_buses(now, snapshot, self.position_max_age_sec)
        self.bus_count = len(self.bus_names)

        # Log only on change. A steady state is not worth repeating every
        # poll, but going to or from zero is exactly what someone asking
        # "why is nothing being counted?" needs to see.
        if self.bus_count != self._last_bus_count:
            if self.bus_count:
                _LOGGER.info("%s: %d bus(es) running — %s",
                             self.route_name, self.bus_count,
                             ", ".join(self.bus_names))
            else:
                stale = len(snapshot.positions)
                _LOGGER.info(
                    "%s: no buses reporting a fresh position%s. Nothing will "
                    "be counted until one does.",
                    self.route_name,
                    f" ({stale} position(s) older than "
                    f"{self.position_max_age_sec:.0f}s)" if stale else
                    " (the feed returned none)",
                )
            self._last_bus_count = self.bus_count

        if _LOGGER.isEnabledFor(logging.DEBUG):
            self._log_detail(now, snapshot, observations)

    def _fire_verdict(self, counted, snapshot) -> None:
        """Announce one counted verdict on the Home Assistant event bus.

        The deviation is reported so an automation can *describe* what
        happened. It is deliberately not something to threshold on: the
        buffers already define early, on-time and late, and a second threshold
        in YAML would be a competing definition that silently disagrees with
        the counters.
        """
        schedule = self.schedule
        stop = schedule.stops.get(counted.stop_id) if schedule else None
        bus = snapshot.positions.get(counted.vehicle_id)

        self.hass.bus.async_fire(EVENT_VERDICT, {
            "entry_id": self.entry.entry_id,
            "route": self.route_name,
            "route_id": self.route_id,
            "stop": stop.name if stop else counted.stop_id,
            "stop_id": counted.stop_id,
            "verdict": counted.verdict.value,
            "kind": "arrival" if counted.is_arrival else "departure",
            "punctuality": counted.verdict.value.split("_", 1)[1],
            "bus": bus.name if bus and bus.name else counted.vehicle_id,
            "vehicle_id": counted.vehicle_id,
            "scheduled": counted.scheduled.isoformat(),
            "actual": counted.at.isoformat(),
            # Signed against the window edge that was crossed: negative is
            # early, positive is late.
            "deviation_seconds": round(counted.deviation_sec),
            "deviation_minutes": round(counted.deviation_sec / 60, 1),
        })

    def _log_detail(self, now, snapshot, observations) -> None:
        """Per-bus distances, so a missed visit can be diagnosed."""
        assert self.schedule is not None
        at_stop = [o for o in observations if o.geo is GeoLocality.AT_STOP]
        _LOGGER.debug(
            "poll: %d positions (%d fresh), %d observations, %d at-stop, "
            "%d buses, radius=%.0fm",
            len(snapshot.positions),
            len(snapshot.fresh(now, self.position_max_age_sec)),
            len(observations), len(at_stop), self.bus_count, self.radius_m,
        )
        for bus in snapshot.fresh(now, self.position_max_age_sec):
            parts = []
            for stop_id in self.schedule.stop_order:
                dist = distance_to_stop(bus.location, self.schedule, stop_id)
                name = self.schedule.stops[stop_id].name
                parts.append(f"{name}={dist:.0f}m" if dist is not None else name)
            _LOGGER.debug(
                "  bus %s age=%.0fs %s",
                bus.name or bus.vehicle_id, bus.age_sec(now), " ".join(parts),
            )
