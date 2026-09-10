"""Tests for schedule parsing and visit merging.

The decisive test here checks the derived visits against the operator's
published timetable, transcribed verbatim below. That timetable is the source
of truth; the API is only trusted insofar as it reproduces it.

doc: schedule.visits
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tsx.schedule import (
    StopVisit,
    _merge_into_visits,
    build_schedule,
    stops_only,
)

FIXTURES = Path(__file__).parent / "fixtures"
RED_LINE = "22443444-e127-4e40-8927-a3192e750369"
TZ = ZoneInfo("America/New_York")
DAY = date(2026, 9, 9)

EASTMAN = "Eastman Living Center"
RUSH_RHEES = "Rush Rhees Library Back Side"

# --- Published timetable (source of truth) -----------------------------------
# "Bus Leaves Eastman Living Center" -> "Bus Arrives at Rush Rhees Library"
EASTMAN_TO_RUSH = [
    ("6:10", "6:30"), ("6:50", "7:10"), ("7:30", "7:50"), ("8:15", "8:35"),
    ("9:00", "9:20"), ("9:45", "10:05"), ("10:35", "10:55"), ("11:25", "11:45"),
    ("12:05", "12:25"), ("12:45", "13:05"), ("13:30", "13:50"), ("14:15", "14:35"),
    ("14:55", "15:15"), ("15:35", "15:55"), ("16:15", "16:35"), ("17:05", "17:25"),
    ("17:45", "18:05"), ("18:25", "18:45"), ("19:05", "19:35"), ("19:55", "20:15"),
    ("20:35", "20:55"),
]
# "Bus Leaves Rush Rhees Library" -> "Bus Arrives at Eastman Living Center"
RUSH_TO_EASTMAN = [
    ("6:30", "6:50"), ("7:10", "7:30"), ("7:55", "8:15"), ("8:40", "9:00"),
    ("9:25", "9:45"), ("10:05", "10:25"), ("11:00", "11:20"), ("11:45", "12:05"),
    ("12:25", "12:45"), ("13:05", "13:25"), ("13:55", "14:15"), ("14:35", "14:55"),
    ("15:15", "15:35"), ("15:55", "16:15"), ("16:45", "17:05"), ("17:25", "17:45"),
    ("18:05", "18:25"), ("18:45", "19:05"), ("19:35", "19:55"), ("20:15", "20:35"),
    ("20:55", "21:15"),
]


def hhmm(text: str) -> str:
    h, m = text.split(":")
    return f"{int(h):02d}:{m}"


def local(when):
    """Visit instants are stored in UTC; the timetable is local wall-clock."""
    return when.astimezone(TZ)


def hm(when) -> str:
    return local(when).strftime("%H:%M")


@pytest.fixture(scope="module")
def schedule():
    data = json.loads((FIXTURES / "route_service_bundle.json").read_text())
    return build_schedule(data, RED_LINE, "Red Line", DAY, TZ)


def stop_id_of(schedule, name):
    return next(s.stop_id for s in schedule.stops.values() if s.name == name)


class TestAgainstPublishedTimetable:
    """The derived visits must reproduce the operator's timetable."""

    def test_two_stops(self, schedule):
        assert {s.name for s in schedule.stops.values()} == {EASTMAN, RUSH_RHEES}

    def test_eastman_departures_match(self, schedule):
        sid = stop_id_of(schedule, EASTMAN)
        derived = {hm(v.departure) for v in schedule.visits_for(sid)}
        for leaves, _ in EASTMAN_TO_RUSH:
            assert hhmm(leaves) in derived, f"missing Eastman departure {leaves}"

    def test_eastman_arrivals_match(self, schedule):
        sid = stop_id_of(schedule, EASTMAN)
        derived = {hm(v.arrival) for v in schedule.visits_for(sid)}
        for _, arrives in RUSH_TO_EASTMAN:
            assert hhmm(arrives) in derived, f"missing Eastman arrival {arrives}"

    def test_rush_rhees_arrivals_match(self, schedule):
        sid = stop_id_of(schedule, RUSH_RHEES)
        derived = {hm(v.arrival) for v in schedule.visits_for(sid)}
        for _, arrives in EASTMAN_TO_RUSH:
            assert hhmm(arrives) in derived, f"missing Rush Rhees arrival {arrives}"

    def test_rush_rhees_departures_match(self, schedule):
        sid = stop_id_of(schedule, RUSH_RHEES)
        derived = {hm(v.departure) for v in schedule.visits_for(sid)}
        for leaves, _ in RUSH_TO_EASTMAN:
            assert hhmm(leaves) in derived, f"missing Rush Rhees departure {leaves}"

    def test_visit_counts(self, schedule):
        """21 legs each way; the first departure and last arrival are unpaired."""
        assert len(schedule.visits_for(stop_id_of(schedule, EASTMAN))) == 22
        assert len(schedule.visits_for(stop_id_of(schedule, RUSH_RHEES))) == 21

    def test_layovers_are_one_visit_not_two(self, schedule):
        """Rush Rhees 7:50 arrive / 7:55 depart is a single visit."""
        sid = stop_id_of(schedule, RUSH_RHEES)
        visit = next(v for v in schedule.visits_for(sid)
                     if hm(v.arrival) == "07:50")
        assert hm(visit.departure) == "07:55"
        assert visit.dwell_sec == pytest.approx(310, abs=15)

    def test_longest_layover_is_ten_minutes(self, schedule):
        """Rush Rhees 16:35 -> 16:45, the widest scheduled dwell."""
        sid = stop_id_of(schedule, RUSH_RHEES)
        visit = next(v for v in schedule.visits_for(sid)
                     if hm(v.arrival) == "16:35")
        assert hm(visit.departure) == "16:45"

    def test_turnarounds_are_one_visit(self, schedule):
        """Eastman 6:50 ends one trip and starts the next: one visit."""
        sid = stop_id_of(schedule, EASTMAN)
        at_0650 = [v for v in schedule.visits_for(sid)
                   if hm(v.arrival) == "06:50"]
        assert len(at_0650) == 1
        assert hm(at_0650[0].departure) == "06:50"

    def test_every_visit_departs_at_or_after_arrival(self, schedule):
        for v in schedule.visits:
            assert v.departure >= v.arrival

    def test_visits_at_a_stop_do_not_overlap(self, schedule):
        for sid in schedule.stop_order:
            visits = sorted(schedule.visits_for(sid), key=lambda v: v.arrival)
            for prev, nxt in zip(visits, visits[1:]):
                assert prev.departure < nxt.arrival


class TestMerging:
    """The merge rule: same stop, nothing else between -> one visit."""

    def _e(self, stop, hh, mm, ss=0, wait=10):
        return (stop, datetime(2026, 9, 9, hh, mm, ss, tzinfo=TZ), wait)

    def test_adjacent_same_stop_entries_merge(self):
        visits = _merge_into_visits([
            self._e("a", 6, 50, 0), self._e("a", 6, 50, 5)])
        assert len(visits) == 1
        assert visits[0].arrival.second == 0
        assert visits[0].departure.second == 15

    def test_a_different_stop_between_splits_them(self):
        visits = _merge_into_visits([
            self._e("a", 6, 10), self._e("b", 6, 30), self._e("a", 6, 50)])
        assert [v.stop_id for v in visits] == ["a", "b", "a"]

    def test_a_ten_minute_layover_still_merges(self):
        """No threshold: only an intervening stop ends a visit."""
        visits = _merge_into_visits([
            self._e("b", 16, 35), self._e("b", 16, 45)])
        assert len(visits) == 1
        assert visits[0].dwell_sec == pytest.approx(610, abs=1)

    def test_three_consecutive_entries_merge(self):
        visits = _merge_into_visits([
            self._e("a", 8, 0), self._e("a", 8, 1), self._e("a", 8, 2)])
        assert len(visits) == 1
        assert visits[0].arrival.minute == 0
        assert visits[0].departure.minute == 2

    def test_empty_input(self):
        assert _merge_into_visits([]) == []

    def test_zero_wait_gives_zero_dwell(self):
        visits = _merge_into_visits([self._e("a", 9, 0, wait=0)])
        assert visits[0].dwell_sec == 0
        assert visits[0].arrival == visits[0].departure


class TestParsing:
    def test_stop_locations_are_read(self, schedule):
        for stop in schedule.stops.values():
            assert 42.0 < stop.location.lt < 44.0
            assert -78.0 < stop.location.lg < -77.0

    def test_region_id_is_read(self, schedule):
        assert schedule.region_id == "ca558ddc-d7f2-4b48-9cac-deea1134f820"

    def test_scheduled_ride_ids_collected(self, schedule):
        assert len(schedule.scheduled_ride_ids) == 24

    def test_visits_are_stored_as_utc_instants(self, schedule):
        """UTC internally, so window arithmetic never goes wall-clock."""
        for v in schedule.visits:
            assert v.arrival.tzinfo is not None
            assert v.arrival.utcoffset() == timedelta(0)

    def test_nearest_visit_picks_the_closest(self, schedule):
        sid = stop_id_of(schedule, EASTMAN)
        target = datetime(2026, 9, 9, 15, 30, tzinfo=TZ)
        assert hm(schedule.nearest_visit(sid, target).arrival) == "15:35"

    def test_nearest_visit_none_for_unknown_stop(self, schedule):
        assert schedule.nearest_visit("nope", datetime(2026, 9, 9, 12, tzinfo=TZ)) is None

    def test_hours_past_midnight_roll_into_next_day(self):
        """TimeOfDay allows 0-47 for service days running past midnight."""
        data = {"routeServices": [], "routes": [], "scheduledRides": [[{
            "scheduledRideId": "r1",
            "stops": [{"stop": "s1", "arrivalTime": "25:30:00", "waitTimeSec": 0}],
        }]]}
        sched = build_schedule(data, RED_LINE, "Red Line", DAY, TZ)
        arrival = local(sched.visits[0].arrival)
        assert arrival.day == DAY.day + 1
        assert arrival.hour == 1

    def test_null_stop_entries_are_skipped(self):
        data = {"routeServices": [], "routes": [], "scheduledRides": [[{
            "scheduledRideId": "r1",
            "stops": [None, {"stop": "s1", "arrivalTime": "09:00:00",
                             "waitTimeSec": 10}],
        }]]}
        sched = build_schedule(data, RED_LINE, "Red Line", DAY, TZ)
        assert len(sched.visits) == 1

    def test_empty_payload_is_not_fatal(self):
        sched = build_schedule({}, RED_LINE, "Red Line", DAY, TZ)
        assert sched.stops == {} and sched.visits == []


class TestNoServiceDay:
    """The route does not run every day.

    The API returns no routeServices for a weekend, holiday, or a day outside
    the service period, so `build_schedule` yields no stops and no visits. The
    stops must survive anyway, or the entities would vanish; the visits must
    not, or yesterday's timetable would be matched against today's clock.
    """

    def test_empty_payload_yields_no_stops(self):
        sched = build_schedule({}, RED_LINE, "Red Line", DAY, TZ)
        assert sched.stops == {} and sched.visits == []

    def test_stops_only_keeps_the_stops(self, schedule):
        carried = stops_only(schedule, date(2026, 9, 12))
        assert carried.stops == schedule.stops
        assert carried.stop_order == schedule.stop_order
        assert len(carried.stops) == 2

    def test_stops_only_drops_the_visits(self, schedule):
        carried = stops_only(schedule, date(2026, 9, 12))
        assert carried.visits == []
        assert carried.scheduled_ride_ids == []

    def test_stops_only_adopts_the_new_day(self, schedule):
        carried = stops_only(schedule, date(2026, 9, 12))
        assert carried.day == date(2026, 9, 12)

    def test_stops_only_has_no_visit_to_match(self, schedule):
        """With no visits, nearest_visit finds nothing to misclassify against."""
        carried = stops_only(schedule, date(2026, 9, 12))
        sid = stop_id_of(schedule, EASTMAN)
        assert carried.nearest_visit(
            sid, datetime(2026, 9, 12, 12, tzinfo=TZ)) is None

    def test_stops_only_does_not_alias_the_original(self, schedule):
        """Mutating the carried schedule must not corrupt the real one."""
        carried = stops_only(schedule, date(2026, 9, 12))
        carried.stops.clear()
        carried.stop_order.clear()
        assert len(schedule.stops) == 2
        assert len(schedule.stop_order) == 2


class TestDaylightSaving:
    """Window arithmetic must use real instants, not wall-clock.

    Subtracting from a zone-aware datetime whose tzinfo has DST is wall-clock
    arithmetic: on a spring-forward day 03:05 minus ten minutes yields 02:55,
    an instant seventy minutes earlier in real time, so an adherence window
    built that way comes out inverted. Two datetimes sharing one ZoneInfo also
    compare by wall clock, which hid it from the overlap validation.
    """

    def _sched(self, day, time_of_day="03:05:00"):
        data = {"routeServices": [], "routes": [], "scheduledRides": [[{
            "scheduledRideId": "r",
            "stops": [{"stop": "s", "arrivalTime": time_of_day,
                       "waitTimeSec": 0}],
        }]]}
        return build_schedule(data, RED_LINE, "Red Line", day, TZ)

    @pytest.mark.parametrize("day", [
        date(2026, 3, 8),    # spring forward, 02:00 -> 03:00
        date(2026, 11, 1),   # fall back, 02:00 -> 01:00
        date(2026, 6, 1),    # ordinary day, control
    ])
    def test_arrival_window_spans_exactly_the_buffer(self, day):
        from tsx.locality import arrival_window
        visit = self._sched(day).visits[0]
        window = arrival_window(visit.arrival, 600)
        assert (window.end - window.start).total_seconds() == 600

    @pytest.mark.parametrize("day", [date(2026, 3, 8), date(2026, 11, 1)])
    def test_a_bus_five_minutes_early_is_on_time(self, day):
        from tsx.locality import TimeLocality, arrival_window, classify_arrival
        visit = self._sched(day).visits[0]
        window = arrival_window(visit.arrival, 600)
        verdict = classify_arrival(visit.arrival - timedelta(minutes=5), window)
        assert verdict is TimeLocality.ARRIVE_ON_TIME

    def test_the_nonexistent_hour_collides_and_is_now_detectable(self):
        """26:00 and 27:00 on a spring-forward day are the same real instant.

        The 02:00-03:00 wall-clock hour does not exist on 2026-03-08, so two
        timetable entries an hour apart on paper land on one instant. That is
        unavoidable. What matters is that it is now *visible*: with instants
        stored in UTC the overlap validation compares real time and reports
        it, where wall-clock comparison silently read them as an hour apart.
        """
        from tsx.observations import validate_schedule
        from tsx.schedule import RouteSchedule
        a = self._sched(date(2026, 3, 7), "26:00:00").visits[0]
        b = self._sched(date(2026, 3, 7), "27:00:00").visits[0]
        assert a.arrival == b.arrival

        merged = RouteSchedule(
            route_id="r", route_name="R", region_id=None, day=date(2026, 3, 7),
            stops={}, stop_order=[], scheduled_ride_ids=[],
            visits=[a, StopVisit(a.stop_id, b.arrival, b.departure)],
        )
        assert validate_schedule(merged, 60, 60)

    def test_dwell_is_measured_in_real_seconds(self):
        data = {"routeServices": [], "routes": [], "scheduledRides": [[{
            "scheduledRideId": "r",
            "stops": [{"stop": "s", "arrivalTime": "03:00:00",
                       "waitTimeSec": 600}],
        }]]}
        visit = build_schedule(data, RED_LINE, "Red Line",
                               date(2026, 3, 8), TZ).visits[0]
        assert visit.dwell_sec == 600


class TestMergeBounds:
    """The merge rule is bounded; "nothing between them" is not enough."""

    def _e(self, stop, hh, mm, wait=10):
        return (stop, datetime(2026, 9, 9, hh, mm, tzinfo=TZ).astimezone(
            timezone.utc), wait)

    def test_a_service_gap_at_a_terminal_does_not_merge(self):
        """A morning ride ending at A and an afternoon ride starting there.

        They are adjacent in the sorted list with no other stop between, but
        four hours apart. Merging would erase the afternoon arrival entirely.
        """
        visits = _merge_into_visits([
            self._e("a", 9, 0), self._e("b", 9, 30),
            self._e("a", 10, 0), self._e("a", 14, 0),
            self._e("b", 14, 30), self._e("a", 15, 0),
        ])
        arrivals = [v.arrival.astimezone(TZ).strftime("%H:%M")
                    for v in visits if v.stop_id == "a"]
        assert "14:00" in arrivals
        assert all(v.dwell_sec <= 1800 for v in visits)

    def test_a_ten_minute_layover_still_merges(self):
        visits = _merge_into_visits([self._e("b", 16, 35), self._e("b", 16, 45)])
        assert len(visits) == 1

    def test_the_bound_is_thirty_minutes(self):
        just_under = _merge_into_visits([self._e("a", 10, 0, wait=0),
                                         self._e("a", 10, 29)])
        just_over = _merge_into_visits([self._e("a", 10, 0, wait=0),
                                        self._e("a", 10, 31)])
        assert len(just_under) == 1
        assert len(just_over) == 2

    def test_a_dropped_separator_does_not_fuse_two_visits(self):
        """A malformed middle entry must not silently join its neighbours."""
        data = {"routeServices": [], "routes": [], "scheduledRides": [[{
            "scheduledRideId": "r", "stops": [
                {"stop": "a", "arrivalTime": "10:00:00", "waitTimeSec": 0},
                {"stop": "b", "arrivalTime": "BAD", "waitTimeSec": 0},
                {"stop": "a", "arrivalTime": "10:40:00", "waitTimeSec": 0},
            ]}]]}
        sched = build_schedule(data, RED_LINE, "Red Line", DAY, TZ)
        assert len(sched.visits) == 2

    def test_a_long_first_wait_is_not_truncated_by_a_later_entry(self):
        visits = _merge_into_visits([self._e("a", 16, 35, wait=600),
                                     self._e("a", 16, 40, wait=0)])
        assert len(visits) == 1
        assert visits[0].dwell_sec == 600

    def test_negative_wait_is_clamped_to_zero_dwell(self):
        visits = _merge_into_visits([self._e("a", 9, 0, wait=-60)])
        assert visits[0].dwell_sec == 0
        assert visits[0].departure >= visits[0].arrival


class TestStrictTimeParsing:
    """int() alone accepts signs, underscores and non-ASCII digits."""

    @pytest.mark.parametrize("bad", [
        "-1:00:00", "99:99:99", "1_0:00:00", "١٠:00:00", " 5 : 0 : 0 ",
        "+10:00:00", "10:60:00", "10:00:60", "48:00:00", "9:00", "",
        "aa:bb:cc", "10:00:00Z",
    ])
    def test_malformed_times_are_rejected(self, bad):
        data = {"routeServices": [], "routes": [], "scheduledRides": [[{
            "scheduledRideId": "r",
            "stops": [{"stop": "s", "arrivalTime": bad, "waitTimeSec": 0}]}]]}
        assert build_schedule(data, RED_LINE, "Red Line", DAY, TZ).visits == []

    @pytest.mark.parametrize("good", ["00:00:00", "9:05:00", "23:59:59",
                                      "24:00:00", "47:59:59"])
    def test_valid_times_are_accepted(self, good):
        data = {"routeServices": [], "routes": [], "scheduledRides": [[{
            "scheduledRideId": "r",
            "stops": [{"stop": "s", "arrivalTime": good, "waitTimeSec": 0}]}]]}
        assert len(build_schedule(data, RED_LINE, "Red Line", DAY, TZ).visits) == 1

    def test_malformed_numeric_fields_do_not_raise(self):
        data = {
            "routeServices": [{"vias": [
                {"ViaStop": {"stop": {"stopId": "s1", "name": "Bad",
                                      "location": {"lt": "north", "lg": 0}}}},
                {"ViaStop": {"stop": {"stopId": "s2", "name": "Good",
                                      "location": {"lt": 43.1, "lg": -77.6}}}},
                "not-a-dict",
            ]}],
            "routes": [],
            "scheduledRides": [[{"scheduledRideId": "r", "stops": [
                {"stop": "s2", "arrivalTime": "09:00:00",
                 "waitTimeSec": "soon"}]}]],
        }
        sched = build_schedule(data, RED_LINE, "Red Line", DAY, TZ)
        assert set(sched.stops) == {"s2"}
        assert len(sched.visits) == 1
        assert sched.visits[0].dwell_sec == 0


class TestTimetableOverrides:
    """Hard-coded corrections where the API disagrees with the timetable."""

    def test_the_missing_leg_is_corrected(self, schedule):
        """Rush Rhees 12:25 arrives at 12:25:00, as published.

        The API's ride serving 12:25 begins at Rush Rhees with its first two
        stop entries null, so the drop-off that should open the visit is
        missing and only the 12:25:05 pick-up remains.
        """
        sid = stop_id_of(schedule, RUSH_RHEES)
        visit = next(v for v in schedule.visits_for(sid)
                     if hm(v.arrival) == "12:25")
        assert local(visit.arrival).strftime("%H:%M:%S") == "12:25:00"

    def test_the_override_does_not_add_a_visit(self, schedule):
        """It merges into the existing visit rather than creating one."""
        sid = stop_id_of(schedule, RUSH_RHEES)
        at_1225 = [v for v in schedule.visits_for(sid)
                   if hm(v.arrival) == "12:25"]
        assert len(at_1225) == 1
        assert len(schedule.visits) == 43

    def test_overrides_are_skipped_on_a_no_service_day(self):
        """An override must never invent service the operator does not run."""
        sched = build_schedule({}, RED_LINE, "Red Line", DAY, TZ)
        assert sched.visits == []

    def test_overrides_are_skipped_for_stops_this_route_lacks(self):
        """A fix naming an unserved stop is ignored, not injected."""
        data = {"routeServices": [{"vias": [{"ViaStop": {"stop": {
                    "stopId": "elsewhere", "name": "Elsewhere",
                    "location": {"lt": 43.1, "lg": -77.6}}}}]}],
                "routes": [],
                "scheduledRides": [[{"scheduledRideId": "r", "stops": [
                    {"stop": "elsewhere", "arrivalTime": "08:00:00",
                     "waitTimeSec": 0}]}]]}
        sched = build_schedule(data, RED_LINE, "Red Line", DAY, TZ)
        assert len(sched.visits) == 1
        assert sched.visits[0].stop_id == "elsewhere"

    def test_an_override_is_not_duplicated_if_upstream_supplies_it(self):
        """If the operator fixes their data, the override becomes a no-op."""
        from tsx.overrides import fixes_for
        fix = fixes_for(RED_LINE)[0]
        data = {"routeServices": [{"vias": [{"ViaStop": {"stop": {
                    "stopId": fix.stop_id, "name": "Rush Rhees",
                    "location": {"lt": 43.13, "lg": -77.63}}}}]}],
                "routes": [],
                "scheduledRides": [[{"scheduledRideId": "r", "stops": [
                    {"stop": fix.stop_id, "arrivalTime": fix.arrival,
                     "waitTimeSec": 0}]}]]}
        sched = build_schedule(data, RED_LINE, "Red Line", DAY, TZ)
        assert len(sched.visits) == 1

    def test_other_routes_are_unaffected(self):
        data = {"routeServices": [{"vias": [{"ViaStop": {"stop": {
                    "stopId": "s1", "name": "S1",
                    "location": {"lt": 43.1, "lg": -77.6}}}}]}],
                "routes": [],
                "scheduledRides": [[{"scheduledRideId": "r", "stops": [
                    {"stop": "s1", "arrivalTime": "08:00:00",
                     "waitTimeSec": 0}]}]]}
        sched = build_schedule(data, "some-other-route", "Blue", DAY, TZ)
        assert len(sched.visits) == 1

    def test_every_override_documents_why_it_exists(self):
        from tsx.overrides import SCHEDULE_OVERRIDES
        for route_id, fixes in SCHEDULE_OVERRIDES.items():
            assert fixes, f"{route_id} registered with no fixes"
            for fix in fixes:
                assert len(fix.reason) > 40, "an override needs a rationale"
                assert fix.wait_sec >= 0


class TestPublishedArrivalsAreExact:
    """Set equality, not subset — proves no extra or missing visits."""

    def test_rush_rhees_arrivals_match_exactly(self, schedule):
        sid = stop_id_of(schedule, RUSH_RHEES)
        derived = {hm(v.arrival) for v in schedule.visits_for(sid)}
        published = {hhmm(a) for _, a in EASTMAN_TO_RUSH}
        assert derived == published

    def test_rush_rhees_departures_match_exactly(self, schedule):
        sid = stop_id_of(schedule, RUSH_RHEES)
        derived = {hm(v.departure) for v in schedule.visits_for(sid)}
        published = {hhmm(d) for d, _ in RUSH_TO_EASTMAN}
        assert derived == published


class TestUnembeddedStops:
    """A response missing embedStops=true must fail loudly, not silently."""

    def _payload(self, stop_value):
        return {"routeServices": [{"vias": [
                    {"ViaStop": {"stop": stop_value}}]}],
                "routes": [], "scheduledRides": []}

    def test_a_bare_id_yields_no_stops(self):
        sched = build_schedule(self._payload("37fb377f-6170-4948-9560-9fd3569c30b4"),
                               RED_LINE, "Red Line", DAY, TZ)
        assert sched.stops == {}

    def test_a_bare_id_is_logged_as_an_error(self, caplog):
        build_schedule(self._payload("37fb377f-6170-4948-9560-9fd3569c30b4"),
                       RED_LINE, "Red Line", DAY, TZ)
        assert "embedStops" in caplog.text

    def test_an_embedded_stop_parses(self):
        sched = build_schedule(self._payload(
            {"stopId": "s1", "name": "S1", "location": {"lt": 43.1, "lg": -77.6}}),
            RED_LINE, "Red Line", DAY, TZ)
        assert len(sched.stops) == 1
