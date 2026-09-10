"""Parsing of the live feed.

Only bus positions are read. The feed also carries the vendor's own per-stop
verdicts (`stopStatus`, `expectedArrivalTime`, `lateBySec`) and ride state;
none of it is parsed, because adherence is computed here from the published
schedule and observed positions alone.

doc: api.models.live
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .locality import LatLng

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class BusPosition:
    """One position report for one bus.

    `when` is the moment the bus reported the position, not the moment we
    fetched it — the feed lags reality by a few seconds and buses report every
    ~11 s, so this is what freshness is judged against.
    """

    vehicle_id: str
    name: str | None
    location: LatLng
    when: datetime

    def age_sec(self, now: datetime) -> float:
        return (now - self.when).total_seconds()


@dataclass
class LiveSnapshot:
    """Parsed POST /v1/p/liveStatus response."""

    timestamp: datetime | None = None
    positions: dict[str, BusPosition] = field(default_factory=dict)

    def fresh(self, now: datetime, max_age_sec: float) -> list[BusPosition]:
        """Positions recent enough to be trusted.

        doc: semantics.geo-locality#staleness — a stale position parked inside
        a geofence would otherwise manufacture a permanent at-stop.
        """
        # Bounded on both sides: a position dated in the future — clock skew,
        # or a bogus timestamp — would otherwise read as permanently fresh and
        # pin a phantom at-stop forever.
        return [p for p in self.positions.values()
                if 0 <= p.age_sec(now) <= max_age_sec]


def parse_instant(value: Any) -> datetime | None:
    """Parse an ISO-8601 instant, tolerating sub-microsecond precision.

    The API emits timestamps like "2026-09-09T22:47:26.092560206000Z" — more
    fractional digits than datetime.fromisoformat accepts. Truncate to
    microseconds.
    """
    if not isinstance(value, str) or not value:
        return None
    text = value.replace("Z", "+00:00")
    if "." in text:
        head, _, tail = text.partition(".")
        digits = ""
        for ch in tail:
            if ch.isdigit():
                digits += ch
            else:
                tail = tail[len(digits):]
                break
        else:
            tail = ""
        text = f"{head}.{digits[:6]:0<6}{tail}"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        _LOGGER.debug("could not parse instant %r", value)
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_live_status(data: dict[str, Any]) -> LiveSnapshot:
    """Parse POST /v1/p/liveStatus, keeping only bus positions."""
    snapshot = LiveSnapshot(timestamp=parse_instant(data.get("timestamp")))

    for raw in data.get("vehicleStatuses") or []:
        if not isinstance(raw, dict):
            continue
        vehicle_id = raw.get("vehicleId")
        loc = raw.get("location") or {}
        lt, lg = loc.get("lt"), loc.get("lg")
        when = parse_instant(raw.get("when"))
        if not vehicle_id or lt is None or lg is None or when is None:
            continue
        position = BusPosition(
            vehicle_id=vehicle_id,
            name=raw.get("name") or raw.get("gtfsName"),
            location=LatLng(float(lt), float(lg)),
            when=when,
        )
        # A vehicle can appear more than once; keep the newest fix rather than
        # whichever happened to come last in the array.
        existing = snapshot.positions.get(vehicle_id)
        if existing is None or position.when >= existing.when:
            snapshot.positions[vehicle_id] = position

    _LOGGER.debug("live: %d bus positions", len(snapshot.positions))
    return snapshot
