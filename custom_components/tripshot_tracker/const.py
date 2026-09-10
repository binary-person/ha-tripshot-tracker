"""Constants for the TripShot Tracker integration.

Values taken from the decompiled client carry a `doc:` citation naming the
page in docs-apk/ that derives them. Run `python3 tools/derive.py` to check
those citations still hold.

Adherence thresholds are deliberately *not* taken from the client — see
docs-apk/50-semantics-time-locality.md.
"""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "tripshot_tracker"

#: Fired once each time a verdict is counted. The idiomatic trigger for
#: "a bus just departed early": a counter is a poor signal for a discrete
#: occurrence, since an automation would have to diff consecutive states and a
#: restart that restores a counter from 0 to N looks like N verdicts at once.
EVENT_VERDICT: Final = f"{DOMAIN}_event"

# doc: api.transport — BuildConfig.BASE_URL
DEFAULT_BASE_URL: Final = "https://api.tripshot.com"

# doc: api.transport — "Android Rider " + versionName + "/" + versionCode
APP_VERSION_NAME: Final = "127"
APP_VERSION_CODE: Final = "541"
USER_BUILD_HEADER: Final = f"Android Rider {APP_VERSION_NAME}/{APP_VERSION_CODE}"

# doc: api.discovery — AppType.RIDER's wire name is "RiderApp", not "RIDER".
APP_TYPE_RIDER: Final = "RiderApp"

# doc: api.transport — OkHttpClient connect/read/write timeouts are all 10s.
HTTP_TIMEOUT_SEC: Final = 10

# doc: integration.request-plan — the schedule is a static timetable; there is
# no benefit to fetching it more often than the client does.
SCHEDULE_REFRESH_SEC: Final = 300

#: How far ahead to look for the route's stops when today has no service.
PROBE_WINDOW_DAYS: Final = 7

# --- Adherence settings, all user-configurable -------------------------------
# doc: semantics.time-locality — buses report a position roughly every 11s and
# the server view regenerates about every 5s, so 30s is a polling choice rather
# than a data limit. It quantises observed arrival times to +/- the interval.
DEFAULT_POLL_INTERVAL_SEC: Final = 30

# doc: semantics.time-locality — a bus may be this far AHEAD of the scheduled
# arrival and still count as on time. Arriving after the scheduled instant is
# late. Our choice, not the vendor's.
DEFAULT_ARRIVAL_EARLY_BUFFER_SEC: Final = 120

# doc: semantics.time-locality — a bus may be this far BEHIND the scheduled
# departure and still count as on time. Leaving before it is early.
DEFAULT_DEPARTURE_LATE_BUFFER_SEC: Final = 120

# doc: semantics.time-locality#grace — lag between a bus crossing a geofence
# and us being able to observe it, EXCLUDING the poll interval. Measured
# against the live feed: a bus emits a position roughly every 11s, and that fix
# takes about 5s to appear in the server's view.
FEED_LAG_SEC: Final = 16

# doc: semantics.time-locality#grace — tolerance on the STRICT edge of both
# windows, where there is otherwise none: arrival has no late tolerance and
# departure no early tolerance, yet a crossing cannot be resolved more finely
# than it is sampled.
#
# -1 means "follow the poll interval" — grace becomes poll_interval +
# FEED_LAG_SEC, so it tracks the setting that justifies it instead of drifting
# out of sync with it. Any value >= 0 is used literally.
GRACE_FOLLOW_POLL: Final = -1
DEFAULT_MEASUREMENT_GRACE_SEC: Final = GRACE_FOLLOW_POLL

# doc: semantics.geo-locality — our geofence, not the vendor's. Diameter, feet.
DEFAULT_GEOFENCE_DIAMETER_FT: Final = 500

# doc: semantics.geo-locality#debounce — consecutive polls that must agree
# before a geofence crossing is acted on. 1 acts immediately; 2 filters a bus
# hovering on the boundary while GPS noise pushes it across, which would
# otherwise book a departure and a fresh arrival on every oscillation.
DEFAULT_CONFIRM_POLLS: Final = 2

# doc: semantics.geo-locality — ignore position reports older than this.
DEFAULT_POSITION_MAX_AGE_SEC: Final = 120

def stable_key(entry) -> str:
    """A prefix for unique ids that survives removing and re-adding the entry.

    `entry.entry_id` is generated afresh each time a config entry is created,
    so keying unique ids on it means a remove-and-re-add produces entirely new
    entities — losing every counter and all recorded history, even though the
    route is the same one.

    `entry.unique_id` is "<instance>:<routeId>", set by the config flow and
    derived from what is being tracked rather than from this installation of
    it. Note this is a *different* problem from the `_2` suffix on entity ids,
    which comes from two routes sharing a stop name and is solved by putting
    the route in the device name.
    """
    return entry.unique_id or entry.entry_id


CONF_INSTANCE_NAME: Final = "instance_name"
CONF_INSTANCE_ID: Final = "instance_id"
CONF_INSTANCE_LABEL: Final = "instance_label"
CONF_BASE_URL: Final = "base_url"
CONF_ROUTE_ID: Final = "route_id"
CONF_ROUTE_NAME: Final = "route_name"
CONF_REGION_ID: Final = "region_id"

CONF_ARRIVAL_EARLY_BUFFER_SEC: Final = "arrival_early_buffer_sec"
CONF_DEPARTURE_LATE_BUFFER_SEC: Final = "departure_late_buffer_sec"
CONF_GEOFENCE_DIAMETER_FT: Final = "geofence_diameter_ft"
CONF_POSITION_MAX_AGE_SEC: Final = "position_max_age_sec"
CONF_POLL_INTERVAL_SEC: Final = "poll_interval_sec"
CONF_MEASUREMENT_GRACE_SEC: Final = "measurement_grace_sec"
CONF_CONFIRM_POLLS: Final = "confirm_polls"
CONF_TIMEZONE: Final = "timezone"

#: Empty means "use Home Assistant's own timezone". This must be the transit
#: system's timezone, which is only the same thing when Home Assistant happens
#: to be configured for the same place the buses run.
DEFAULT_TIMEZONE: Final = ""

#: Settings that may be changed after setup, with their defaults.
TUNABLES: Final = {
    CONF_ARRIVAL_EARLY_BUFFER_SEC: DEFAULT_ARRIVAL_EARLY_BUFFER_SEC,
    CONF_DEPARTURE_LATE_BUFFER_SEC: DEFAULT_DEPARTURE_LATE_BUFFER_SEC,
    CONF_GEOFENCE_DIAMETER_FT: DEFAULT_GEOFENCE_DIAMETER_FT,
    CONF_POSITION_MAX_AGE_SEC: DEFAULT_POSITION_MAX_AGE_SEC,
    CONF_POLL_INTERVAL_SEC: DEFAULT_POLL_INTERVAL_SEC,
    CONF_MEASUREMENT_GRACE_SEC: DEFAULT_MEASUREMENT_GRACE_SEC,
    CONF_CONFIRM_POLLS: DEFAULT_CONFIRM_POLLS,
    CONF_TIMEZONE: DEFAULT_TIMEZONE,
}
