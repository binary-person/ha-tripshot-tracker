"""Tests for the pure locality reductions.

doc: semantics.time-locality, semantics.geo-locality
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tsx.locality import (
    EARTH_RADIUS_M,
    GeoLocality,
    LatLng,
    TimeLocality,
    TimeWindow,
    arrival_window,
    classify_arrival,
    classify_departure,
    departure_window,
    diameter_ft_to_radius_m,
    geo_locality,
    haversine_m,
    resolve_grace_sec,
    time_locality,
    schedule_is_consistent,
)

STOP = LatLng(43.1590312879686, -77.6012646661841)   # Eastman Living Center
SCHED_ARR = datetime(2026, 9, 9, 13, 0, 0, tzinfo=timezone.utc)
SCHED_DEP = SCHED_ARR + timedelta(seconds=15)
EARLY_BUF = 120
LATE_BUF = 120
R500 = diameter_ft_to_radius_m(500)


def at(**kw) -> datetime:
    return SCHED_ARR + timedelta(**kw)


# --------------------------------------------------------------- geo --
class TestGeofenceSize:
    def test_500ft_diameter_is_about_76m_radius(self):
        assert diameter_ft_to_radius_m(500) == pytest.approx(76.2, abs=0.01)

    def test_scales_linearly(self):
        assert diameter_ft_to_radius_m(1000) == pytest.approx(
            2 * diameter_ft_to_radius_m(500))

    def test_zero(self):
        assert diameter_ft_to_radius_m(0) == 0


class TestHaversine:
    def test_zero_distance(self):
        assert haversine_m(STOP, STOP) == pytest.approx(0.0, abs=1e-9)

    def test_symmetric(self):
        other = LatLng(43.16, -77.60)
        assert haversine_m(STOP, other) == pytest.approx(
            haversine_m(other, STOP), abs=1e-9)

    def test_one_degree_of_latitude(self):
        expected = EARTH_RADIUS_M * (3.141592653589793 / 180.0)
        assert haversine_m(LatLng(0, 0), LatLng(1, 0)) == pytest.approx(
            expected, rel=1e-9)


class TestGeoLocality:
    def test_at_the_stop(self):
        assert geo_locality(STOP, STOP, R500) is GeoLocality.AT_STOP

    def test_far_away(self):
        assert geo_locality(LatLng(43.20, -77.60), STOP, R500) is (
            GeoLocality.NOT_AT_STOP)

    def test_missing_position_is_not_at_stop(self):
        assert geo_locality(None, STOP, R500) is GeoLocality.NOT_AT_STOP

    def test_just_inside(self):
        inside = LatLng(STOP.lt + 70.0 / 111320.0, STOP.lg)
        assert geo_locality(inside, STOP, R500) is GeoLocality.AT_STOP

    def test_just_outside(self):
        outside = LatLng(STOP.lt + 80.0 / 111320.0, STOP.lg)
        assert geo_locality(outside, STOP, R500) is GeoLocality.NOT_AT_STOP

    def test_boundary_is_inclusive(self):
        edge = LatLng(STOP.lt + 0.0005, STOP.lg)
        assert geo_locality(edge, STOP, haversine_m(STOP, edge)) is (
            GeoLocality.AT_STOP)

    def test_the_two_red_line_stops_do_not_overlap(self):
        """4 km apart, so a 500 ft geofence cannot match both."""
        rush = LatLng(43.128, -77.628)
        assert haversine_m(STOP, rush) > 2 * R500


# -------------------------------------------------------------- time --
class TestWindows:
    def test_arrival_window_extends_earlier_only(self):
        w = arrival_window(SCHED_ARR, EARLY_BUF)
        assert w.start == SCHED_ARR - timedelta(seconds=EARLY_BUF)
        assert w.end == SCHED_ARR

    def test_departure_window_extends_later_only(self):
        w = departure_window(SCHED_DEP, LATE_BUF)
        assert w.start == SCHED_DEP
        assert w.end == SCHED_DEP + timedelta(seconds=LATE_BUF)

    def test_zero_buffer_gives_an_instant(self):
        w = arrival_window(SCHED_ARR, 0)
        assert w.start == w.end == SCHED_ARR

    def test_contains_is_inclusive(self):
        w = arrival_window(SCHED_ARR, EARLY_BUF)
        assert w.contains(w.start) and w.contains(w.end)
        assert not w.contains(w.start - timedelta(seconds=1))
        assert not w.contains(w.end + timedelta(seconds=1))


class TestScheduleConsistency:
    """The invariant is about the schedule, not the window edges."""

    def test_a_normal_visit_is_consistent(self):
        assert schedule_is_consistent(SCHED_ARR, SCHED_DEP)

    def test_zero_dwell_is_consistent(self):
        assert schedule_is_consistent(SCHED_ARR, SCHED_ARR)

    def test_departure_before_arrival_is_not(self):
        assert not schedule_is_consistent(
            SCHED_ARR, SCHED_ARR - timedelta(seconds=1))

    def test_grace_may_make_the_windows_overlap_and_that_is_fine(self):
        """On a short dwell the grace widens both strict edges past each other.

        Harmless: arrival is judged when a bus enters the geofence and
        departure when it leaves, never both from one sample, so no instant is
        ever ambiguous. The schedule invariant still holds.
        """
        arrival = arrival_window(SCHED_ARR, EARLY_BUF, grace_sec=30)
        departure = departure_window(SCHED_DEP, LATE_BUF, grace_sec=30)
        assert arrival.end > departure.start          # they do overlap
        assert schedule_is_consistent(SCHED_ARR, SCHED_DEP)


class TestMeasurementGrace:
    """The strict edge of each window gets the measurement precision.

    Without it, the arrival window ends exactly on the scheduled instant while
    an observed crossing lags the real one by up to a poll interval — so a bus
    arriving on time is routinely recorded late, and the verdict reports our
    sampling rate rather than the bus.
    """

    def test_grace_extends_the_arrival_late_edge(self):
        w = arrival_window(SCHED_ARR, EARLY_BUF, grace_sec=30)
        assert w.end == SCHED_ARR + timedelta(seconds=30)
        assert w.start == SCHED_ARR - timedelta(seconds=EARLY_BUF)

    def test_grace_extends_the_departure_early_edge(self):
        w = departure_window(SCHED_DEP, LATE_BUF, grace_sec=30)
        assert w.start == SCHED_DEP - timedelta(seconds=30)
        assert w.end == SCHED_DEP + timedelta(seconds=LATE_BUF)

    def test_the_configured_value_is_used_literally(self):
        """Not clamped, not derived from anything else."""
        for grace in (0, 1, 11, 29, 30, 45, 300):
            w = arrival_window(SCHED_ARR, EARLY_BUF, grace_sec=grace)
            assert (w.end - SCHED_ARR).total_seconds() == grace
            d = departure_window(SCHED_DEP, LATE_BUF, grace_sec=grace)
            assert (SCHED_DEP - d.start).total_seconds() == grace

    def test_zero_grace_reproduces_the_strict_edges(self):
        assert arrival_window(SCHED_ARR, EARLY_BUF, 0).end == SCHED_ARR
        assert departure_window(SCHED_DEP, LATE_BUF, 0).start == SCHED_DEP

    def test_grace_defaults_to_zero(self):
        assert arrival_window(SCHED_ARR, EARLY_BUF).end == SCHED_ARR

    def test_an_on_time_arrival_within_grace_is_not_late(self):
        w = arrival_window(SCHED_ARR, EARLY_BUF, grace_sec=30)
        assert classify_arrival(SCHED_ARR + timedelta(seconds=25), w) is (
            TimeLocality.ARRIVE_ON_TIME)
        assert classify_arrival(SCHED_ARR + timedelta(seconds=31), w) is (
            TimeLocality.ARRIVE_LATE)

    def test_a_marginally_early_departure_within_grace_is_not_early(self):
        w = departure_window(SCHED_DEP, LATE_BUF, grace_sec=30)
        assert classify_departure(SCHED_DEP - timedelta(seconds=25), w) is (
            TimeLocality.DEPART_ON_TIME)
        assert classify_departure(SCHED_DEP - timedelta(seconds=31), w) is (
            TimeLocality.DEPART_EARLY)

    def test_grace_of_eleven_seconds(self):
        """The value discussed explicitly: telemetry cadence, not poll lag."""
        w = arrival_window(SCHED_ARR, EARLY_BUF, grace_sec=11)
        assert classify_arrival(SCHED_ARR + timedelta(seconds=11), w) is (
            TimeLocality.ARRIVE_ON_TIME)
        assert classify_arrival(SCHED_ARR + timedelta(seconds=12), w) is (
            TimeLocality.ARRIVE_LATE)


class TestClassifyArrival:
    W = arrival_window(SCHED_ARR, EARLY_BUF)

    @pytest.mark.parametrize("delta,expected", [
        (-3600, TimeLocality.ARRIVE_EARLY),
        (-121, TimeLocality.ARRIVE_EARLY),
        (-120, TimeLocality.ARRIVE_ON_TIME),
        (-60, TimeLocality.ARRIVE_ON_TIME),
        (0, TimeLocality.ARRIVE_ON_TIME),
        (1, TimeLocality.ARRIVE_LATE),
        (3600, TimeLocality.ARRIVE_LATE),
    ])
    def test_boundaries(self, delta, expected):
        assert classify_arrival(at(seconds=delta), self.W) is expected


class TestClassifyDeparture:
    W = departure_window(SCHED_DEP, LATE_BUF)

    @pytest.mark.parametrize("delta,expected", [
        (-3600, TimeLocality.DEPART_EARLY),
        (14, TimeLocality.DEPART_EARLY),
        (15, TimeLocality.DEPART_ON_TIME),
        (75, TimeLocality.DEPART_ON_TIME),
        (135, TimeLocality.DEPART_ON_TIME),
        (136, TimeLocality.DEPART_LATE),
        (3600, TimeLocality.DEPART_LATE),
    ])
    def test_boundaries(self, delta, expected):
        assert classify_departure(at(seconds=delta), self.W) is expected


class TestTimeLocality:
    ARR = arrival_window(SCHED_ARR, EARLY_BUF)
    DEP = departure_window(SCHED_DEP, LATE_BUF)

    def test_not_at_stop_is_always_na(self):
        for delta in (-3600, -60, 0, 60, 3600):
            assert time_locality(at(seconds=delta), self.ARR, self.DEP,
                                 GeoLocality.NOT_AT_STOP) is TimeLocality.NA

    def test_at_stop_before_window_is_early(self):
        assert time_locality(at(seconds=-600), self.ARR, self.DEP,
                             GeoLocality.AT_STOP) is TimeLocality.ARRIVE_EARLY

    def test_at_stop_in_window_is_on_time(self):
        assert time_locality(at(seconds=-30), self.ARR, self.DEP,
                             GeoLocality.AT_STOP) is TimeLocality.ARRIVE_ON_TIME

    def test_at_stop_after_scheduled_arrival_is_late(self):
        assert time_locality(at(seconds=60), self.ARR, self.DEP,
                             GeoLocality.AT_STOP) is TimeLocality.ARRIVE_LATE

    def test_presence_never_yields_a_departure_verdict(self):
        """Standing at a stop is not a departure, however overdue."""
        for delta in (300, 3600, 86400):
            assert time_locality(at(seconds=delta), self.ARR, self.DEP,
                                 GeoLocality.AT_STOP) is TimeLocality.ARRIVE_LATE


class TestHaversineExtremes:
    """The sqrt clamp guards against rounding past 1.0 at antipodes."""

    def test_antipodal_longitude(self):
        d = haversine_m(LatLng(0.0, 0.0), LatLng(0.0, 180.0))
        assert d == pytest.approx(3.141592653589793 * EARTH_RADIUS_M, rel=1e-9)

    def test_pole_to_pole(self):
        d = haversine_m(LatLng(90.0, 0.0), LatLng(-90.0, 0.0))
        assert d == pytest.approx(3.141592653589793 * EARTH_RADIUS_M, rel=1e-9)

    def test_no_domain_error_near_antipodes(self):
        for lng in (179.9, 179.999, 180.0):
            assert haversine_m(LatLng(0.0, 0.0), LatLng(0.0, lng)) > 0


class TestGraceDerivation:
    """The grace follows the poll interval unless explicitly overridden.

    It is a statement about resolution, not a preference: a crossing cannot be
    observed more finely than it is sampled. Storing it as a free-floating
    number lets it drift out of sync with the poll interval that justifies it.
    """

    def test_negative_follows_the_poll_interval(self):
        assert resolve_grace_sec(-1, 30, 16) == 46

    def test_it_tracks_a_changed_poll_interval(self):
        assert resolve_grace_sec(-1, 10, 16) == 26
        assert resolve_grace_sec(-1, 60, 16) == 76

    def test_feed_lag_is_included(self):
        """Even an instantaneous poll looks at slightly stale truth."""
        assert resolve_grace_sec(-1, 0, 16) == 16

    @pytest.mark.parametrize("configured", [0, 1, 11, 29, 30, 45, 300])
    def test_an_explicit_value_is_used_literally(self, configured):
        """Never silently overridden, however inconsistent with the poll."""
        assert resolve_grace_sec(configured, 30, 16) == configured

    def test_zero_is_honoured_and_is_not_treated_as_auto(self):
        assert resolve_grace_sec(0, 30, 16) == 0

    def test_eleven_with_a_thirty_second_poll_is_still_eleven(self):
        """Under-covers the sampling lag, but the setting is obeyed."""
        assert resolve_grace_sec(11, 30, 16) == 11

    def test_negative_inputs_cannot_produce_a_negative_grace(self):
        assert resolve_grace_sec(-1, -5, -5) == 0

    def test_derived_grace_covers_the_poll_interval(self):
        """The property that makes it correct: grace >= poll, always."""
        for poll in (10, 15, 30, 60, 300):
            assert resolve_grace_sec(-1, poll, 16) >= poll
