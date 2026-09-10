"""Tests for the bus/stop joins and schedule validation.

doc: semantics.time-locality, semantics.geo-locality
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tsx.locality import GeoLocality, LatLng, diameter_ft_to_radius_m
from tsx.models import BusPosition, LiveSnapshot
from tsx.observations import (
    build_observations,
    count_buses,
    validate_schedule,
    windows_for,
)
from tsx.schedule import RouteSchedule, Stop, StopVisit, build_schedule

FIXTURES = Path(__file__).parent / "fixtures"
TZ = ZoneInfo("America/New_York")
DAY = date(2026, 9, 9)
RED_LINE = "22443444-e127-4e40-8927-a3192e750369"

STOP_A, STOP_B = "stop-a", "stop-b"
LOC_A = LatLng(43.1590312879686, -77.6012646661841)
LOC_B = LatLng(43.128, -77.628)          # ~4 km away
NOW = datetime(2026, 9, 9, 17, 0, 0, tzinfo=timezone.utc)
R500 = diameter_ft_to_radius_m(500)


def make_schedule(visits=None) -> RouteSchedule:
    visits = visits if visits is not None else [
        StopVisit(STOP_A, NOW, NOW + timedelta(seconds=15)),
        StopVisit(STOP_B, NOW + timedelta(minutes=20),
                  NOW + timedelta(minutes=20, seconds=15)),
    ]
    return RouteSchedule(
        route_id="r", route_name="Red Line", region_id="reg", day=DAY,
        stops={STOP_A: Stop(STOP_A, "Eastman", LOC_A),
               STOP_B: Stop(STOP_B, "Rush Rhees", LOC_B)},
        stop_order=[STOP_A, STOP_B], visits=visits, scheduled_ride_ids=["s1"],
    )


def snap(at=LOC_A, age=5, bus="v1", name="2603") -> LiveSnapshot:
    return LiveSnapshot(
        timestamp=NOW,
        positions={bus: BusPosition(bus, name, at,
                                    NOW - timedelta(seconds=age))},
    )


def build(schedule=None, snapshot=None, early=120, late=120, max_age=120):
    return build_observations(
        NOW, schedule or make_schedule(), snapshot or snap(),
        radius_m=R500, early_buffer_sec=early, late_buffer_sec=late,
        position_max_age_sec=max_age)


class TestJoins:
    def test_one_observation_per_bus_per_stop(self):
        assert len(build()) == 2

    def test_bus_is_at_exactly_one_stop(self):
        obs = build()
        at = [o for o in obs if o.geo is GeoLocality.AT_STOP]
        assert len(at) == 1
        assert at[0].stop_id == STOP_A

    def test_bus_between_stops_is_at_none(self):
        obs = build(snapshot=snap(at=LatLng(43.145, -77.615)))
        assert all(o.geo is GeoLocality.NOT_AT_STOP for o in obs)

    def test_two_buses_produce_two_sets(self):
        s = snap()
        s.positions["v2"] = BusPosition("v2", "2508", LOC_B,
                                        NOW - timedelta(seconds=5))
        obs = build(snapshot=s)
        assert len(obs) == 4
        assert {o.vehicle_id for o in obs} == {"v1", "v2"}

    def test_no_buses_no_observations(self):
        assert build(snapshot=LiveSnapshot(timestamp=NOW)) == []

    def test_stop_without_visits_is_skipped(self):
        sched = make_schedule(visits=[
            StopVisit(STOP_A, NOW, NOW + timedelta(seconds=15))])
        obs = build(schedule=sched)
        assert {o.stop_id for o in obs} == {STOP_A}


class TestFreshness:
    def test_fresh_position_is_used(self):
        assert build(snapshot=snap(age=10)) != []

    def test_stale_position_is_held_not_forced_to_na(self):
        """A dropout must not look like a departure."""
        assert build(snapshot=snap(age=600)) == []

    def test_boundary_age_is_accepted(self):
        assert build(snapshot=snap(age=120)) != []

    def test_stale_bus_is_not_counted(self):
        assert count_buses(NOW, snap(age=600), 120) == []

    def test_fresh_bus_is_counted_by_name(self):
        assert count_buses(NOW, snap(), 120) == ["2603"]

    def test_unnamed_bus_falls_back_to_id(self):
        assert count_buses(NOW, snap(name=None), 120) == ["v1"]


class TestWindows:
    def test_windows_come_from_the_nearest_visit(self):
        obs = next(o for o in build() if o.stop_id == STOP_A)
        assert obs.arrival.end == NOW
        assert obs.departure.start == NOW + timedelta(seconds=15)

    def test_buffers_are_applied(self):
        obs = next(o for o in build(early=60, late=300) if o.stop_id == STOP_A)
        assert obs.arrival.start == NOW - timedelta(seconds=60)
        assert obs.departure.end == NOW + timedelta(seconds=315)

    def test_windows_for_helper(self):
        visit = StopVisit(STOP_A, NOW, NOW + timedelta(seconds=30))
        arrival, departure = windows_for(visit, 60, 90)
        assert arrival.start == NOW - timedelta(seconds=60)
        assert arrival.end == NOW
        assert departure.start == NOW + timedelta(seconds=30)
        assert departure.end == NOW + timedelta(seconds=120)

    def test_nearest_visit_is_chosen_among_many(self):
        visits = [
            StopVisit(STOP_A, NOW - timedelta(hours=2), NOW - timedelta(hours=2)),
            StopVisit(STOP_A, NOW + timedelta(minutes=3),
                      NOW + timedelta(minutes=3)),
            StopVisit(STOP_A, NOW + timedelta(hours=2), NOW + timedelta(hours=2)),
        ]
        obs = next(o for o in build(schedule=make_schedule(visits))
                   if o.stop_id == STOP_A)
        assert obs.arrival.end == NOW + timedelta(minutes=3)


class TestValidation:
    def test_a_sane_schedule_has_no_problems(self):
        assert validate_schedule(make_schedule(), 120, 120) == []

    def test_departure_before_arrival_is_reported(self):
        bad = [StopVisit(STOP_A, NOW, NOW - timedelta(seconds=1))]
        problems = validate_schedule(make_schedule(bad), 120, 120)
        assert len(problems) == 1
        assert "precedes scheduled arrival" in problems[0]

    def test_grace_does_not_make_a_short_dwell_visit_a_problem(self):
        """Grace widens both strict edges; on a short dwell they cross."""
        visits = [StopVisit(STOP_A, NOW, NOW + timedelta(seconds=10))]
        assert validate_schedule(make_schedule(visits), 120, 120, 30) == []

    def test_grace_does_not_affect_the_headway_check(self):
        """It widens the edges that face inward on a visit, not outward.

        The headway check compares a visit's departure-window END against the
        next visit's arrival-window START — both governed by the buffers. The
        grace moves the departure-window start and the arrival-window end,
        which face the other way, so it cannot create or hide a headway
        overlap. Only the buffers can.
        """
        visits = [
            StopVisit(STOP_A, NOW, NOW),
            StopVisit(STOP_A, NOW + timedelta(minutes=5),
                      NOW + timedelta(minutes=5)),
        ]
        for grace in (0, 45, 600):
            assert validate_schedule(make_schedule(visits), 120, 120, grace) == []
        # The buffers, by contrast, do trip it.
        assert validate_schedule(make_schedule(visits), 200, 200, 0)

    def test_zero_dwell_is_allowed(self):
        """Windows touching at one instant is fine."""
        visits = [StopVisit(STOP_A, NOW, NOW)]
        assert validate_schedule(make_schedule(visits), 120, 120) == []

    def test_buffers_wider_than_the_headway_are_reported(self):
        visits = [
            StopVisit(STOP_A, NOW, NOW),
            StopVisit(STOP_A, NOW + timedelta(minutes=10),
                      NOW + timedelta(minutes=10)),
        ]
        problems = validate_schedule(make_schedule(visits), 400, 400)
        assert any("overlap consecutive visits" in p for p in problems)

    def test_narrow_buffers_do_not_overlap(self):
        visits = [
            StopVisit(STOP_A, NOW, NOW),
            StopVisit(STOP_A, NOW + timedelta(minutes=10),
                      NOW + timedelta(minutes=10)),
        ]
        assert validate_schedule(make_schedule(visits), 120, 120) == []

    def test_real_schedule_validates_with_default_buffers(self):
        data = json.loads((FIXTURES / "route_service_bundle.json").read_text())
        sched = build_schedule(data, RED_LINE, "Red Line", DAY, TZ)
        assert validate_schedule(sched, 120, 120) == []

    def test_real_schedule_flags_absurd_buffers(self):
        """20-minute buffers exceed this route's turnaround headway."""
        data = json.loads((FIXTURES / "route_service_bundle.json").read_text())
        sched = build_schedule(data, RED_LINE, "Red Line", DAY, TZ)
        problems = validate_schedule(sched, 1200, 1200)
        assert problems
        assert all("overlap consecutive visits" in p for p in problems)
