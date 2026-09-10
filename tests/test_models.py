"""Tests for live-feed parsing, against a fixture captured from the API.

doc: api.models.live
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tsx.models import LiveSnapshot, parse_instant, parse_live_status

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def live():
    return json.loads((FIXTURES / "live_status.json").read_text())


class TestParseInstant:
    def test_handles_nanosecond_precision(self):
        """The API emits 12 fractional digits; fromisoformat rejects those."""
        assert parse_instant("2026-09-09T22:47:26.092560206000Z") == datetime(
            2026, 9, 9, 22, 47, 26, 92560, tzinfo=timezone.utc)

    def test_handles_milliseconds(self):
        assert parse_instant("2026-09-09T13:03:47.958Z") == datetime(
            2026, 9, 9, 13, 3, 47, 958000, tzinfo=timezone.utc)

    def test_handles_no_fraction(self):
        assert parse_instant("2026-09-09T13:03:47Z") == datetime(
            2026, 9, 9, 13, 3, 47, tzinfo=timezone.utc)

    def test_always_timezone_aware(self):
        assert parse_instant("2026-09-09T13:03:47").tzinfo is not None

    @pytest.mark.parametrize("bad", [None, "", "not a date", 42, {}])
    def test_rejects_garbage(self, bad):
        assert parse_instant(bad) is None


class TestParseLiveStatus:
    def test_reads_positions(self, live):
        snap = parse_live_status(live)
        assert snap.positions
        assert snap.timestamp is not None

    def test_position_fields(self, live):
        bus = next(iter(parse_live_status(live).positions.values()))
        assert 42.0 < bus.location.lt < 44.0
        assert -78.0 < bus.location.lg < -77.0
        assert bus.when.tzinfo is not None
        assert bus.name

    def test_ignores_vendor_verdict_fields(self):
        """The vendor's own adherence verdicts must not enter the model.

        Asserts the SHAPE of what is parsed, not the absence of one attribute
        name: a payload carrying rides, stopStatus, lateBySec and
        expectedArrivalTime alongside a real position must yield a snapshot
        whose fields are exactly timestamp + positions, and a position whose
        fields are exactly the four we read.
        """
        import dataclasses

        snap = parse_live_status({
            "timestamp": "2026-09-09T22:47:26.092Z",
            "date": {"year": 2026, "month": 9, "day": 9},
            "vehicles": [{"vehicleId": "v1", "capacity": 31}],
            "rides": [{"rideId": "r:d", "lateBySec": 300,
                       "state": {"Active": []},
                       "stopStatus": [{"Departed": {
                           "stopId": "s",
                           "expectedArrivalTime": "2026-09-09T22:40:00Z"}}]}],
            "vehicleStatuses": [{
                "vehicleId": "v1", "name": "2603",
                "location": {"lt": 43.1, "lg": -77.6},
                "when": "2026-09-09T22:47:20Z",
                "accuracy": 3.2, "bearing": 90.0, "speed": 11.0,
                "liveDataAvailable": True, "visibility": "PublicRider"}],
        })
        assert {f.name for f in dataclasses.fields(snap)} == {
            "timestamp", "positions"}
        bus = snap.positions["v1"]
        assert {f.name for f in dataclasses.fields(bus)} == {
            "vehicle_id", "name", "location", "when"}

    def test_duplicate_vehicle_keeps_the_newest_position(self):
        """A repeated vehicleId must not let an older fix win on array order."""
        snap = parse_live_status({"vehicleStatuses": [
            {"vehicleId": "v1", "location": {"lt": 1, "lg": 2},
             "when": "2026-09-09T12:00:00Z"},
            {"vehicleId": "v1", "location": {"lt": 3, "lg": 4},
             "when": "2026-09-09T11:00:00Z"},
        ]})
        assert snap.positions["v1"].when.hour == 12
        assert snap.positions["v1"].location.lt == 1

    def test_skips_incomplete_positions(self):
        snap = parse_live_status({"vehicleStatuses": [
            {"vehicleId": "v1"},
            {"vehicleId": "v2", "location": {"lt": 1, "lg": 2}},
            {"vehicleId": "v3", "when": "2026-09-09T22:47:26.092Z"},
            {"vehicleId": "v4", "location": {"lt": 1, "lg": 2},
             "when": "2026-09-09T22:47:26.092Z"},
        ]})
        assert set(snap.positions) == {"v4"}

    def test_falls_back_to_gtfs_name(self):
        snap = parse_live_status({"vehicleStatuses": [
            {"vehicleId": "v1", "gtfsName": "2603",
             "location": {"lt": 1, "lg": 2},
             "when": "2026-09-09T22:47:26.092Z"},
        ]})
        assert snap.positions["v1"].name == "2603"

    def test_empty_payload_is_not_fatal(self):
        assert parse_live_status({}).positions == {}


class TestFreshness:
    NOW = datetime(2026, 9, 9, 23, 0, 0, tzinfo=timezone.utc)

    def _snap(self, age_sec):
        return parse_live_status({"vehicleStatuses": [{
            "vehicleId": "v1", "name": "2603",
            "location": {"lt": 43.1, "lg": -77.6},
            "when": (self.NOW - timedelta(seconds=age_sec)).isoformat(),
        }]})

    def test_recent_position_is_fresh(self):
        assert len(self._snap(10).fresh(self.NOW, 120)) == 1

    def test_old_position_is_not(self):
        assert self._snap(600).fresh(self.NOW, 120) == []

    def test_a_future_position_is_not_fresh(self):
        """Clock skew must not pin a phantom at-stop forever."""
        assert self._snap(-86400).fresh(self.NOW, 120) == []

    def test_boundary_age_is_fresh(self):
        assert len(self._snap(120).fresh(self.NOW, 120)) == 1

    def test_age_sec(self):
        bus = next(iter(self._snap(45).positions.values()))
        assert bus.age_sec(self.NOW) == pytest.approx(45, abs=1)

    def test_empty_snapshot(self):
        assert LiveSnapshot().fresh(self.NOW, 120) == []
