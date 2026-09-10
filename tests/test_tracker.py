"""Tests for the sticky per-(stop, bus) state machine.

doc: semantics.time-locality
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tsx.locality import (
    GeoLocality,
    TimeLocality,
    arrival_window,
    departure_window,
)
from tsx.tracker import Observation, RouteTracker

SCHED_ARR = datetime(2026, 9, 9, 13, 0, 0, tzinfo=timezone.utc)
SCHED_DEP = SCHED_ARR + timedelta(seconds=15)
ARR = arrival_window(SCHED_ARR, 120)
DEP = departure_window(SCHED_DEP, 120)

STOP = "stop-a"
BUS = "bus-1"
AWAY = GeoLocality.NOT_AT_STOP
HERE = GeoLocality.AT_STOP


def obs(seconds, geo, stop=STOP, bus=BUS, arr=ARR, dep=DEP) -> Observation:
    return Observation(stop_id=stop, vehicle_id=bus,
                       now=SCHED_ARR + timedelta(seconds=seconds),
                       arrival=arr, departure=dep, geo=geo)


class TestCounters:
    def test_starts_at_zero_for_every_state(self):
        counts = RouteTracker().counts_for(STOP)
        assert len(counts) == 6
        assert set(counts.values()) == {0}
        assert TimeLocality.NA not in counts

    def test_count_accessor(self):
        t = RouteTracker()
        assert t.count(STOP, TimeLocality.ARRIVE_LATE) == 0


class TestLatching:
    def test_away_emits_nothing(self):
        t = RouteTracker()
        assert t.observe(obs(0, AWAY)) == []
        assert t.state_for(STOP) is TimeLocality.NA

    def test_arrival_latches_and_counts_once(self):
        t = RouteTracker()
        assert t.observe(obs(-30, HERE)) == [TimeLocality.ARRIVE_ON_TIME]
        assert t.count(STOP, TimeLocality.ARRIVE_ON_TIME) == 1
        assert t.state_for(STOP) is TimeLocality.ARRIVE_ON_TIME

    def test_repeated_presence_does_not_recount(self):
        t = RouteTracker()
        t.observe(obs(-30, HERE))
        for s in (-20, -10, 0, 60, 600):
            assert t.observe(obs(s, HERE)) == []
        assert t.count(STOP, TimeLocality.ARRIVE_ON_TIME) == 1

    def test_state_is_sticky_while_dwelling(self):
        t = RouteTracker()
        t.observe(obs(-30, HERE))
        t.observe(obs(3600, HERE))
        assert t.state_for(STOP) is TimeLocality.ARRIVE_ON_TIME

    def test_early_and_late_arrivals(self):
        t = RouteTracker()
        assert t.observe(obs(-600, HERE)) == [TimeLocality.ARRIVE_EARLY]
        t2 = RouteTracker()
        assert t2.observe(obs(600, HERE)) == [TimeLocality.ARRIVE_LATE]

    def test_buses_at_reports_who_is_present(self):
        t = RouteTracker()
        t.observe(obs(-30, HERE, bus="b1"))
        t.observe(obs(-30, HERE, bus="b2"))
        assert t.buses_at(STOP) == ["b1", "b2"]
        assert t.buses_at("other") == []

    def test_a_departed_bus_is_no_longer_reported_present(self):
        """Two buses at one stop, one leaves — the NA latch must be excluded."""
        t = RouteTracker()
        t.observe(obs(-30, HERE, bus="b1"))
        t.observe(obs(-30, HERE, bus="b2"))
        t.observe(obs(60, AWAY, bus="b1"))
        assert t.buses_at(STOP) == ["b2"]
        assert t.state_for(STOP) is TimeLocality.ARRIVE_ON_TIME

    def test_a_stop_with_only_departed_latches_reports_na(self):
        t = RouteTracker()
        t.observe(obs(-30, HERE, bus="b1"))
        t.observe(obs(-30, HERE, bus="b2"))
        t.observe(obs(60, AWAY, bus="b1"))
        t.observe(obs(60, AWAY, bus="b2"))
        assert t.buses_at(STOP) == []
        assert t.state_for(STOP) is TimeLocality.NA

    def test_state_for_is_deterministic_across_insertion_order(self):
        forward, backward = RouteTracker(), RouteTracker()
        for bus in ("aaa", "zzz"):
            forward.observe(obs(600 if bus == "aaa" else -600, HERE, bus=bus))
        for bus in ("zzz", "aaa"):
            backward.observe(obs(600 if bus == "aaa" else -600, HERE, bus=bus))
        assert forward.state_for(STOP) is backward.state_for(STOP)


class TestDeparture:
    def test_leaving_counts_a_departure(self):
        t = RouteTracker()
        t.observe(obs(-30, HERE))
        assert t.observe(obs(60, AWAY)) == [TimeLocality.DEPART_ON_TIME]

    def test_returns_to_na_after_leaving(self):
        t = RouteTracker()
        t.observe(obs(-30, HERE))
        t.observe(obs(60, AWAY))
        assert t.state_for(STOP) is TimeLocality.NA

    def test_leaving_before_scheduled_departure_is_early(self):
        t = RouteTracker()
        t.observe(obs(-60, HERE))
        assert t.observe(obs(-10, AWAY)) == [TimeLocality.DEPART_EARLY]

    def test_leaving_after_the_buffer_is_late(self):
        t = RouteTracker()
        t.observe(obs(-30, HERE))
        assert t.observe(obs(600, AWAY)) == [TimeLocality.DEPART_LATE]

    def test_one_visit_yields_exactly_one_arrival_and_one_departure(self):
        t = RouteTracker()
        for o in (obs(-60, AWAY), obs(-30, HERE), obs(-10, HERE),
                  obs(0, HERE), obs(60, AWAY), obs(120, AWAY)):
            t.observe(o)
        counts = t.counts_for(STOP)
        assert sum(counts.values()) == 2
        assert counts[TimeLocality.ARRIVE_ON_TIME] == 1
        assert counts[TimeLocality.DEPART_ON_TIME] == 1

    def test_a_very_late_bus_counts_both_late_verdicts(self):
        t = RouteTracker()
        assert t.observe(obs(600, HERE)) == [TimeLocality.ARRIVE_LATE]
        assert t.observe(obs(700, AWAY)) == [TimeLocality.DEPART_LATE]
        counts = t.counts_for(STOP)
        assert counts[TimeLocality.ARRIVE_LATE] == 1
        assert counts[TimeLocality.DEPART_LATE] == 1

    def test_departure_uses_the_window_pinned_at_arrival(self):
        """A long dwell must not be judged against a later visit's window."""
        t = RouteTracker()
        t.observe(obs(-30, HERE))
        later = departure_window(SCHED_DEP + timedelta(hours=1), 120)
        # Leaving 60s after schedule is on time against the pinned window,
        # even though the observation now carries the next visit's window.
        assert t.observe(obs(60, AWAY, dep=later)) == [
            TimeLocality.DEPART_ON_TIME]


class TestReArming:
    def test_a_second_visit_counts_again(self):
        t = RouteTracker()
        t.observe(obs(-30, HERE))
        t.observe(obs(60, AWAY))
        t.observe(obs(3600, HERE))
        assert t.count(STOP, TimeLocality.ARRIVE_ON_TIME) == 1
        assert t.count(STOP, TimeLocality.ARRIVE_LATE) == 1

    def test_buses_are_tracked_independently(self):
        t = RouteTracker()
        t.observe(obs(-30, HERE, bus="b1"))
        t.observe(obs(-30, HERE, bus="b2"))
        assert t.count(STOP, TimeLocality.ARRIVE_ON_TIME) == 2

    def test_stops_are_tracked_independently(self):
        t = RouteTracker()
        t.observe(obs(-30, HERE, stop="a"))
        t.observe(obs(600, HERE, stop="b"))
        assert t.count("a", TimeLocality.ARRIVE_ON_TIME) == 1
        assert t.count("b", TimeLocality.ARRIVE_LATE) == 1
        assert t.count("a", TimeLocality.ARRIVE_LATE) == 0


class TestLifecycle:
    def test_counters_do_not_reset_on_their_own(self):
        """They accumulate for the life of the entry, across service days."""
        t = RouteTracker()
        for day in range(3):
            shift = timedelta(days=day)
            t.observe(obs(-30 + day * 86400, HERE, bus=f"b{day}",
                          arr=arrival_window(SCHED_ARR + shift, 120),
                          dep=departure_window(SCHED_DEP + shift, 120)))
        assert t.count(STOP, TimeLocality.ARRIVE_ON_TIME) == 3

    def test_explicit_reset_clears(self):
        t = RouteTracker()
        t.observe(obs(-30, HERE))
        t.reset()
        assert sum(t.counts_for(STOP).values()) == 0
        assert t.state_for(STOP) is TimeLocality.NA

    def test_expiry_drops_a_long_gone_bus_without_counting(self):
        t = RouteTracker()
        t.observe(obs(-30, HERE))
        assert t.expire_stale(SCHED_ARR + timedelta(seconds=9999), 120) == 1
        assert t.state_for(STOP) is TimeLocality.NA
        assert t.count(STOP, TimeLocality.ARRIVE_ON_TIME) == 1
        assert sum(t.counts_for(STOP).values()) == 1

    def test_expiry_keeps_a_recently_seen_bus(self):
        t = RouteTracker()
        t.observe(obs(-30, HERE))
        assert t.expire_stale(SCHED_ARR, 120) == 0
        assert t.state_for(STOP) is TimeLocality.ARRIVE_ON_TIME

    def test_a_one_poll_dropout_does_not_double_count(self):
        """The bug this expiry replaced: drop + re-latch counted two arrivals.

        A bus can vanish from one poll and come back without moving — a missed
        position report, or a bus idling at a terminal between rides while the
        feed is scoped to this route.
        """
        t = RouteTracker()
        t.observe(obs(-30, HERE))                       # arrives, counted
        t.expire_stale(SCHED_ARR + timedelta(seconds=0), 120)   # absent, in grace
        t.observe(obs(30, HERE))                        # back, never moved
        assert t.count(STOP, TimeLocality.ARRIVE_ON_TIME) == 1
        assert t.observe(obs(60, AWAY)) == [TimeLocality.DEPART_ON_TIME]
        assert sum(t.counts_for(STOP).values()) == 2

    def test_expired_bus_returning_later_is_a_fresh_visit(self):
        t = RouteTracker()
        t.observe(obs(-30, HERE))
        t.expire_stale(SCHED_ARR + timedelta(seconds=9999), 120)
        t.observe(obs(10000, HERE))
        assert t.count(STOP, TimeLocality.ARRIVE_ON_TIME) == 1
        assert t.count(STOP, TimeLocality.ARRIVE_LATE) == 1


class TestSeeding:
    """Counters are restored from Home Assistant's saved entity state."""

    def test_seed_sets_a_counter(self):
        t = RouteTracker()
        t.seed(STOP, TimeLocality.ARRIVE_LATE, 42)
        assert t.count(STOP, TimeLocality.ARRIVE_LATE) == 42

    def test_seeding_then_counting_continues_from_there(self):
        t = RouteTracker()
        t.seed(STOP, TimeLocality.ARRIVE_ON_TIME, 10)
        t.observe(obs(-30, HERE))
        assert t.count(STOP, TimeLocality.ARRIVE_ON_TIME) == 11

    def test_seed_never_lowers_a_counter(self):
        """A restore that would move a live counter backwards is ignored.

        Seeding 0 exits at the non-positive guard without reaching the
        monotonicity check, so this seeds a positive value below the current
        count — the case that actually exercises it.
        """
        t = RouteTracker()
        for delta in (-30, 3600, 7200, 10800, 14400):
            t.observe(obs(delta, HERE, bus=f"b{delta}"))
        assert t.count(STOP, TimeLocality.ARRIVE_ON_TIME) >= 1
        live = t.count(STOP, TimeLocality.ARRIVE_ON_TIME)
        t.seed(STOP, TimeLocality.ARRIVE_ON_TIME, max(1, live - 1))
        assert t.count(STOP, TimeLocality.ARRIVE_ON_TIME) == live

    def test_seed_raises_a_counter_that_is_behind(self):
        t = RouteTracker()
        t.observe(obs(-30, HERE))
        t.seed(STOP, TimeLocality.ARRIVE_ON_TIME, 9)
        assert t.count(STOP, TimeLocality.ARRIVE_ON_TIME) == 9

    @pytest.mark.parametrize("bad", [0, -5])
    def test_seed_ignores_nonpositive(self, bad):
        t = RouteTracker()
        t.seed(STOP, TimeLocality.ARRIVE_LATE, bad)
        assert t.count(STOP, TimeLocality.ARRIVE_LATE) == 0


class TestPriming:
    """The first poll adopts what it finds without counting arrivals.

    Latches live in memory; counters are restored from Home Assistant. Without
    priming, a bus already standing inside a geofence when HA restarts would be
    counted as arriving a second time for a visit already recorded.
    """

    def test_priming_latches_without_counting(self):
        t = RouteTracker()
        assert t.observe(obs(-30, HERE), count=False) == []
        assert t.count(STOP, TimeLocality.ARRIVE_ON_TIME) == 0
        assert t.state_for(STOP) is TimeLocality.ARRIVE_ON_TIME

    def test_a_primed_bus_still_counts_its_departure(self):
        t = RouteTracker()
        t.observe(obs(-30, HERE), count=False)
        assert t.observe(obs(60, AWAY)) == [TimeLocality.DEPART_ON_TIME]
        assert t.count(STOP, TimeLocality.DEPART_ON_TIME) == 1

    def test_restart_mid_dwell_does_not_double_count(self):
        """Simulates: arrive, count, restart, bus still there, leave."""
        before = RouteTracker()
        before.observe(obs(-30, HERE))
        assert before.count(STOP, TimeLocality.ARRIVE_ON_TIME) == 1

        after = RouteTracker()                       # fresh process
        after.seed(STOP, TimeLocality.ARRIVE_ON_TIME, 1)   # counters restored
        after.observe_all([obs(0, HERE)], count=False)     # first poll primes
        after.observe_all([obs(30, HERE)])                 # still dwelling
        assert after.count(STOP, TimeLocality.ARRIVE_ON_TIME) == 1

        after.observe_all([obs(60, AWAY)])                 # finally leaves
        assert after.count(STOP, TimeLocality.DEPART_ON_TIME) == 1
        assert after.count(STOP, TimeLocality.ARRIVE_ON_TIME) == 1

    def test_priming_a_bus_that_is_away_does_nothing(self):
        t = RouteTracker()
        t.observe_all([obs(0, AWAY)], count=False)
        assert t.state_for(STOP) is TimeLocality.NA
        assert sum(t.counts_for(STOP).values()) == 0

    def test_arrivals_after_the_priming_cycle_are_counted(self):
        t = RouteTracker()
        t.observe_all([obs(-60, AWAY)], count=False)
        assert t.observe(obs(-30, HERE)) == [TimeLocality.ARRIVE_ON_TIME]


class TestDebounce:
    """A crossing counts only once N consecutive polls agree.

    Without this, a bus parked on the geofence boundary with GPS noise pushing
    it across books a departure and a fresh arrival on every oscillation — the
    only failure mode here that inflates counters rather than dropping them.
    """

    def test_one_confirmation_acts_immediately(self):
        t = RouteTracker()
        assert t.observe(obs(-30, HERE), confirmations=1) == [
            TimeLocality.ARRIVE_ON_TIME]

    def test_two_confirmations_need_two_polls(self):
        t = RouteTracker()
        assert t.observe(obs(-40, HERE), confirmations=2) == []
        assert t.observe(obs(-30, HERE), confirmations=2) == [
            TimeLocality.ARRIVE_ON_TIME]

    def test_a_single_poll_flicker_counts_nothing(self):
        """The bug this exists for: out and back in must be a no-op."""
        t = RouteTracker()
        t.observe(obs(-40, HERE), confirmations=2)
        t.observe(obs(-30, HERE), confirmations=2)      # arrival confirmed
        assert t.observe(obs(0, AWAY), confirmations=2) == []   # flicker out
        assert t.observe(obs(30, HERE), confirmations=2) == []  # back in
        assert t.state_for(STOP) is TimeLocality.ARRIVE_ON_TIME
        assert sum(t.counts_for(STOP).values()) == 1

    def test_repeated_flicker_still_counts_nothing_extra(self):
        t = RouteTracker()
        t.observe(obs(-40, HERE), confirmations=2)
        t.observe(obs(-30, HERE), confirmations=2)
        for i in range(6):
            t.observe(obs(i * 20, AWAY if i % 2 == 0 else HERE), confirmations=2)
        assert sum(t.counts_for(STOP).values()) == 1

    def test_a_confirmed_departure_is_timestamped_at_the_first_sighting(self):
        """Confirmation delays recognition, not the recorded time."""
        t = RouteTracker()
        t.observe(obs(-40, HERE), confirmations=2)
        t.observe(obs(-30, HERE), confirmations=2)
        t.observe(obs(60, AWAY), confirmations=2)       # first seen away
        counted = t.observe_detailed(obs(90, AWAY), confirmations=2)
        assert len(counted) == 1
        assert counted[0].at == SCHED_ARR + timedelta(seconds=60)

    def test_a_confirmed_arrival_is_timestamped_at_the_first_sighting(self):
        t = RouteTracker()
        t.observe(obs(-40, HERE), confirmations=2)
        counted = t.observe_detailed(obs(-30, HERE), confirmations=2)
        assert counted[0].at == SCHED_ARR - timedelta(seconds=40)

    def test_a_genuine_departure_still_counts(self):
        t = RouteTracker()
        t.observe(obs(-40, HERE), confirmations=2)
        t.observe(obs(-30, HERE), confirmations=2)
        assert t.observe(obs(60, AWAY), confirmations=2) == []
        assert t.observe(obs(90, AWAY), confirmations=2) == [
            TimeLocality.DEPART_ON_TIME]
        assert t.state_for(STOP) is TimeLocality.NA

    def test_priming_is_exempt_from_confirmation(self):
        t = RouteTracker()
        t.observe(obs(-30, HERE), count=False, confirmations=3)
        assert t.state_for(STOP) is TimeLocality.ARRIVE_ON_TIME

    def test_three_confirmations(self):
        t = RouteTracker()
        for i in range(2):
            assert t.observe(obs(-40 + i, HERE), confirmations=3) == []
        assert t.observe(obs(-38, HERE), confirmations=3) == [
            TimeLocality.ARRIVE_ON_TIME]

    def test_a_visit_shorter_than_the_confirmation_window_is_missed(self):
        """The documented trade: a drive-by does not register."""
        t = RouteTracker()
        t.observe(obs(-30, HERE), confirmations=2)   # one poll inside only
        t.observe(obs(0, AWAY), confirmations=2)
        assert sum(t.counts_for(STOP).values()) == 0
