"""Hard-coded corrections to the operator's published timetable.

The API's schedule is authoritative except where it demonstrably disagrees
with the timetable the operator publishes to riders. Each entry here records
one such disagreement, what it corrects, and how it was established — so an
override can be re-checked later rather than becoming folklore.

Overrides are applied only on days the route actually runs, and only when the
API has not already supplied an equivalent entry, so a fix that the operator
later corrects upstream becomes a no-op rather than a duplicate.

doc: schedule.visits#overrides
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScheduleFix:
    """One supplemented stop entry, in the operator's local wall-clock time."""

    stop_id: str
    arrival: str
    wait_sec: int
    reason: str


#: University of Rochester — Red Line.
UOFR_RED_LINE = "22443444-e127-4e40-8927-a3192e750369"
_RUSH_RHEES = "ed1e77b3-0708-4eda-9f42-00bd897ab70b"

SCHEDULE_OVERRIDES: dict[str, tuple[ScheduleFix, ...]] = {
    UOFR_RED_LINE: (
        ScheduleFix(
            stop_id=_RUSH_RHEES,
            arrival="12:25:00",
            wait_sec=0,
            reason=(
                "The published timetable lists a trip leaving Eastman Living "
                "Center at 12:05 PM and arriving Rush Rhees Library at "
                "12:25 PM. The API has no ride covering that leg: the ride "
                "serving 12:25 begins at Rush Rhees with its first two stop "
                "entries null, so the only 12:25 entry is the PickupOnly at "
                "12:25:05 and the drop-off that should open the visit is "
                "absent. Without this, the 12:25 visit starts five seconds "
                "late. Verified by diffing all 42 published legs against the "
                "API on 2026-09-09: this was the only one missing, and every "
                "other leg matched to the second."
            ),
        ),
    ),
}


def fixes_for(route_id: str) -> tuple[ScheduleFix, ...]:
    """Corrections registered for a route, if any."""
    return SCHEDULE_OVERRIDES.get(route_id, ())
