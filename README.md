# TripShot Tracker

A Home Assistant custom integration that measures **schedule adherence per stop**
for a TripShot transit line, using only TripShot's public, unauthenticated API.

For each stop it keeps six counters — arrive/depart × early/on-time/late — and
for each route it reports how many buses are currently running it.

Configured for University of Rochester / Red Line, but the config flow lists
every publicly advertised transit system and route.

## How it works

Two reductions, both pure functions, both unit-tested:

```
geo:   (bus position, stop position, radius)               -> at_stop | not_at_stop
time:  (now, arrival window, departure window, geo state)  -> n/a | arrive_* | depart_*
```

On top of them sits one stateful rule: a state that leaves `n/a` is **sticky**
until it returns to `n/a`. A stop's arrival is counted once when a bus enters its
geofence, and its departure once when the bus leaves. So each (stop, ride) pair
contributes at most one arrival and one departure, which is what keeps the
counters meaningful.

Thresholds are **yours**, set at setup and applying to every stop:

| Setting | Meaning | Default |
|---|---|---|
| Arrival buffer, toward early | how far ahead of schedule a bus may arrive and still be on time | 120 s |
| Departure buffer, toward late | how far behind schedule it may depart and still be on time | 120 s |
| Stop geofence diameter | the at-stop radius | 500 ft |
| Position max age | ignore bus positions older than this | 120 s |
| Poll interval | how often positions are fetched | 30 s |
| Measurement grace | tolerance on the strict side of both windows | follows the poll interval |
| Confirm polls | consecutive polls that must agree before a geofence crossing counts (**1 = off**) | 2 |
| Transit timezone | the zone the **buses** run in, not where HA is | HA's own |

The asymmetry is deliberate: running early strands riders, so it is tolerated
only up to the buffer; running slightly late is not.

The vendor's own lateness fields — `lateNoticeWarnTimeSec`,
`expectedArrivalTime`, `lateBySec`, `stopStatus` — are all discarded. Only two
things are read: the published schedule, and bus positions.

## For agents

[`AGENTS.md`](AGENTS.md) has the working rules: the derivation contract, what
is out of scope, how to run both test suites, and the bugs found so far with
the tests that now guard them.

## Provenance

Every API fact is derived from the decompiled Android client and written up in
[`docs-apk/`](docs-apk/README.md), with each claim carrying a citation to the
symbol it came from. Integration code cites those docs inline.

Citations can name a section, so a line of code points at the paragraph that
justifies it:

```python
# doc: semantics.time-locality#priming — the first cycle only adopts
# what it finds, so a restart mid-dwell cannot double-count an arrival.
```

One command builds the graph connecting APK symbols → docs → code, and fails on
drift:

```console
$ python3 tools/derive.py
graph -> docs-apk/graph.json
  12 docs, 88 apk refs, 15 code files, 153 edges
  no drift
```

## Scope

Read-only, and public-only. No authenticated endpoint is called, and `api.py`
has no code path that can construct an `Authorization` header. The target
instance advertises `userAllowedAuthMethods: []` — it has no rider login at all.

Requests mirror the app's: same headers, same 10-second timeouts, same cadence,
and the live request is filtered to a single route so it transfers ~146 KB
rather than the ~4.5 MB an unfiltered region-wide call returns.

## Install

### HACS

1. HACS → ⋮ → **Custom repositories**
2. Repository `https://github.com/binary-person/ha-tripshot-tracker`,
   category **Integration**
3. Install **TripShot Tracker**, then restart Home Assistant

### Manually

Copy `custom_components/tripshot_tracker/` into your `config/custom_components/`
and restart.

### Then

**Settings → Devices & Services → Add Integration → TripShot Tracker**, and pick
a transit system and a route. No credentials are requested, and none can be
sent.

## Entities

| Entity | Per | Notes |
|---|---|---|
| `Arrive early` / `Arrive on time` / `Arrive late` | stop | `TOTAL_INCREASING` counters |
| `Depart early` / `Depart on time` / `Depart late` | stop | `TOTAL_INCREASING` counters |
| `Current state` | stop | diagnostic; the sticky state |
| `Buses` | route | buses currently running the line |
| `Schedule health` | route | diagnostic; buffer/schedule validation |

Each stop is its own device, named `<route> <stop>` and linked to the route
device — so a stop served by two lines yields two devices, e.g.
`sensor.red_line_rush_rhees_library_back_side_depart_early` and
`sensor.orange_line_rush_rhees_library_back_side_depart_early`, rather than one
of them being suffixed `_2`. Entity IDs are assigned at creation and never
revised, so entities that already exist keep the IDs they were given; see
[`examples/README.md`](examples/README.md#entity-names-include-the-route).

## Development

```console
$ python3 -m venv .venv
$ .venv/bin/pip install pytest                      # logic tests only
$ .venv/bin/pip install pytest-homeassistant-custom-component   # + wiring tests
$ .venv/bin/python -m pytest tests/ -q     # 298 tests
$ python3 tools/derive.py                  # graph + drift check
```

`locality.py`, `tracker.py`, `models.py`, `schedule.py`, `endpoints.py` and
`observations.py` import neither Home Assistant nor aiohttp, so the logic is
testable on its own — that suite runs with plain `pytest`.

`tests/test_ha_setup.py` covers the wiring the logic tests cannot see: that
entities are created, attached to devices, grouped under the route, named as
expected, and that Home Assistant logs no deprecation warnings during setup.
It needs `pytest-homeassistant-custom-component`; without it those tests are
skipped and the rest still run.
`tests/test_schedule.py` transcribes the operator's published timetable and
asserts the derived visits reproduce it. `tests/fixtures/` holds trimmed
verbatim excerpts of real public responses, so parsing is pinned against the
actual wire format.

## Automations

The integration fires a `tripshot_tracker_event` bus event each time a verdict
is counted — carrying the route, stop, bus, scheduled and actual times, and the
signed deviation. That is the trigger to use for "a bus just departed early":

```yaml
triggers:
  - trigger: event
    event_type: tripshot_tracker_event
    event_data:
      verdict: depart_early
```

Ready-made examples in [`examples/automations.yaml`](examples/automations.yaml),
with installation instructions in [`examples/README.md`](examples/README.md) —
covering the format difference between `automations.yaml` (a plain list) and
`configuration.yaml` (an `automation:` key), filtering by route and stop, and
pointing the alerts somewhere other than the sidebar.

Use `deviation_seconds` to *describe* what happened, not to decide whether it
counts — early, on-time and late are already defined by the buffers and the
measurement grace. A threshold in YAML would be a second definition that
disagrees with the counters.

## Troubleshooting

**Download diagnostics** — Settings → Devices & Services → TripShot Tracker →
⋮ → *Download diagnostics*. It dumps the resolved settings, every stop with
its counters and next scheduled visit, and **where each bus is right now with
its distance to every stop**, which is usually the fastest way to see why a
visit was or was not counted. There is nothing to redact: it is all public
transit data.

**Debug logging**:

```yaml
logger:
  logs:
    custom_components.tripshot_tracker: debug
```

At `info` you get setup context (instance, route, base URL, timezone, service
day, every resolved setting), each arrival and departure as it is counted with
the window it was judged against, and a line whenever the number of running
buses changes. At `debug` you additionally get every request with its response
size, and per-poll distances from each bus to each stop.

Common messages:

| Message | Meaning |
|---|---|
| `no service scheduled for … keeping N stop(s)` | a weekend, holiday, or term break — normal; entities and counters are kept |
| `… has no route <id>` | the configured route no longer exists on that instance; re-add the integration |
| `route '<name>' exists, but has no scheduled service between …` | the route is real but suspended for that window |
| `no buses reporting a fresh position` | the feed returned nothing recent; nothing will be counted until it does |
| `already at <stop> on the first poll; adopting …` | priming after a restart — deliberately not counted, see the docs |

## Counters and durability

Counters accumulate for the life of the config entry. Home Assistant's
statistics engine handles long-term aggregation on its own, given the
`TOTAL_INCREASING` state class — but it does not preserve the entity's own
value, so each counter restores itself.

* **Retuning settings does not touch them.** Every option is read live on each
  poll, so a change applies in place with no reload and no teardown.
* **Recorder purges are irrelevant.** Restore data lives in
  `.storage/core.restore_state`, not the recorder database. `purge_keep_days`
  and `recorder.purge` affect history graphs, not the restored value.
* **A restart restores them**, including one during an API outage — the count
  is persisted out of band, so an `unavailable` state does not erase it.
* **A hard kill loses up to 15 minutes.** Restore state is written at startup,
  every 15 minutes, and on clean shutdown — never per state change. SIGKILL or
  power loss loses whatever accumulated since the last write. The
  `homeassistant.save_persistent_states` action forces one.

## Known limits

* `scheduled_departure = arrivalTime + waitTimeSec` is inferred from field
  naming — no client code performs that addition. It is validated indirectly
  but strongly: the derived visits reproduce the operator's published timetable
  exactly, departures included.
* Adherence is **observed**, not predicted. The vendor's own late badge comes
  from its ETA; these counters come from timing geofence crossings. They will
  disagree, by design.
* A geofence crossing cannot be resolved more finely than it is sampled, which
  is why the measurement grace is derived from the poll interval rather than
  chosen. See
  [`docs-apk/50-semantics-time-locality.md`](docs-apk/50-semantics-time-locality.md).

## Trademarks and affiliation

Independent and unofficial. **Not affiliated with, sponsored by, endorsed by,
or supported by TripShot, Inc. or the University of Rochester.**

"TripShot" is a trademark of TripShot, Inc. Route and stop names are the
operator's. Those names appear here only to identify the service this software
interoperates with — there is no other way to say what it does.

No third-party logo or brand asset is shipped. The icon is original work, MIT
licensed with the rest of the source. See [`NOTICE`](NOTICE).
