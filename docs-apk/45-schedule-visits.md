---
id: schedule.visits
title: From scheduled stop entries to physical visits
kind: semantics
apk_refs:
  - path: com/tripshot/common/models/ScheduledStop.java
    symbol: waitTimeSec
    sha256: 1a1565469558a2634c82ae4710a7682a390bf33483ef7dc2285ee3bdb23c0b9a
  - path: com/tripshot/common/models/ScheduledRide.java
    symbol: scheduledRideId
    sha256: e3b91732836b9aa1779ce551bbf34cf068b606467cf3a3e0e30b13316be385cb
  - path: com/tripshot/common/utils/TimeOfDay.java
    symbol: onDate
    sha256: 7c2cc3092771847b32c8e6e9a0e8ca1f674d6131188210cbce47119ab0882d81
depends_on: [api.models.schedule, api.transport]
---

# Scheduled visits

The timetable is the source of truth for *when* a bus should be somewhere. This
page covers turning the API's per-ride stop entries into the physical visits a
rider would recognise, and validating the result against the operator's own
published timetable.

## 1. The raw shape

`ScheduledRide.stops[]` holds `ScheduledStop` entries, each with a wall-clock
`arrivalTime` (`"HH:MM:SS"`, hours 0–47) and a non-negative `waitTimeSec`.
Entries are individually nullable — a ride may skip a via.

A `TimeOfDay` becomes an instant only against a service day and a timezone:

```java
Date dateOnDate = timeOfDay.onDate(localDate, timeZone);
```

Hours ≥ 24 roll into the following day, which is how service past midnight is
expressed.

## 2. Why entries are not visits

A single physical visit — bus pulls in, waits, pulls out — is split across
several `ScheduledStop` entries, for two independent reasons:

**Within a ride**, a turnaround is written as a drop-off followed by a pick-up:

```
Eastman  06:10:00  DropOffOrPickup
Rush Rh  06:30:00  DropOffOnly
Rush Rh  06:30:05  PickupOnly     <- same visit, 5 seconds later
Eastman  06:50:00  DropOffOnly
```

**Across rides**, one ride's last stop is the next ride's first:

```
ride A ... Eastman 06:50:00 DropOffOnly
ride B     Eastman 06:50:05 DropOffOrPickup   <- same visit
```

And a scheduled layover can be minutes long — Rush Rhees is scheduled
`07:50:00` arrive, `07:55:00` depart, and once as long as `16:35` → `16:45`.

## 3. The merge rule
<!-- anchor: merge-rule -->

> Two entries at the same stop belong to the same physical visit when no visit
> to a **different** stop falls between them.

The bus has to drive somewhere else to end a visit. This needs no tuning
threshold, which matters because the gaps it must span range from 5 seconds to
10 minutes, while genuinely distinct visits are a headway (~40 min) apart. Any
fixed threshold would have to be picked between 10 and 40 minutes for this
route and would be wrong on another.

Merging yields, per visit:

```
arrival   = first entry's arrivalTime
departure = the latest arrivalTime + waitTimeSec among the merged entries
```

> **Derivation strength.** `arrival` is directly evidenced. The `+ waitTimeSec`
> for the departure is an inference from field naming and the `>= 0` guard —
> **no client code performs that addition**. Validated indirectly in §4: the
> merged departures reproduce the published timetable.

## 4. Validation against the published timetable
<!-- anchor: timetable-validation -->

The operator publishes a timetable for the Red Line. Merging the API's 24
scheduled rides for 2026-09-09 produces **43 visits**, and every one matches:

| | Published | Derived | Match |
|---|---|---|---|
| Eastman departures | 21 | 21 | all&nbsp;[^1] |
| Eastman arrivals | 21 | 21 | all |
| Rush Rhees arrivals | 21 | 21 | all |
| Rush Rhees departures | 21 | 21 | all |

Eastman has **22** visits and Rush Rhees **21**: the first departure (06:10)
has no preceding arrival and the last arrival (21:15) has no following
departure, so those two are unpaired.

[^1]: Eastman's 12:05 departure is derived from `waitTimeSec` rather than a
    scheduled departure entry — the API is missing that leg. See below.

Layovers survive intact — Rush Rhees `07:50 → 07:55` and `16:35 → 16:45` each
come out as one visit with the right dwell, not two visits.

`tests/test_schedule.py` transcribes the published timetable verbatim and
asserts the derived visits reproduce it, so a schedule change that breaks the
merge fails the suite.

### The one discrepancy — corrected by an override
<!-- anchor: overrides -->

The published timetable lists **Eastman 12:05 PM → Rush Rhees 12:25 PM**. The
API has no such leg: the ride serving 12:25 begins at Rush Rhees, with its
first two stop entries `null`. Every other one of the 41 remaining published legs is
present with exactly matching times.

Consequences, both minor:

* Eastman's 12:05 visit is arrival-only; its departure falls out of
  `waitTimeSec` as `12:05:10` rather than a scheduled departure.
* Rush Rhees' 12:25 visit begins at `12:25:05` (the `PickupOnly` entry) instead
  of `12:25:00`, because the drop-off entry that would have opened it is
  missing. Five seconds.

This is a gap in the operator's data, so it is corrected by a hard-coded
override in `overrides.py`: one supplemented entry, Rush Rhees at `12:25:00`,
which merges into the existing visit and brings its arrival onto the published
time. The 12:25 visit now reads `12:25:00 → 12:25:15`, and the derived Rush
Rhees arrival and departure sets match the published timetable **exactly**
(set equality, not subset — `TestPublishedArrivalsAreExact`).

An override is deliberately narrow. It is:

* **keyed by route id**, so no other route is touched;
* **skipped on a day with no service**, so it can never invent a visit the
  operator does not run;
* **skipped when the route does not serve that stop**;
* **skipped when an equivalent entry already exists**, so if the operator
  fixes their feed the override silently retires instead of duplicating;
* **required to carry a written rationale** — a test asserts every registered
  fix explains itself, so an override cannot quietly become folklore.

Four other rides also carry leading `null` stop entries (12:25, 13:05, 13:50,
18:45). Those are **not** gaps: they are one-way return legs whose outbound
half is simply a separate ride. Diffing all 42 published legs confirmed only
the 12:05 → 12:25 leg is genuinely absent.

## 5. Days the route does not run
<!-- anchor: no-service-days -->

`scheduledRides` is **not** a per-day list — it is the route service's
recurring pattern, which carries its own `daysOfWeek`, `startDate`, `endDate`,
`excludedDays` and `extraDays`. The server applies those to the requested day
range, so a request for a day the route does not run returns
`routeServices: []` and therefore no stops and no visits at all.

Measured for the Red Line:

| Requested day | `routeServices` | `viaStops` | rides |
|---|---|---|---|
| Wed 2026-09-09 | 1 | 4 | 24 |
| Thu 2026-09-10 | 1 | 4 | 24 |
| Fri 2026-09-11 | 1 | 4 | 24 |
| **Sat 2026-09-12** | **0** | **0** | **0** |
| **Sun 2026-09-13** | **0** | **0** | **0** |

This is a normal state — a weekend, a holiday, or a date outside the service
period — and must not be treated as an error. Two things follow:

* **The stops are kept.** They come from the last known schedule, so the
  entities and their accumulated counters survive the weekend intact. On a
  first setup that lands on a non-service day there is no previous schedule to
  borrow from, so the route is probed over a 7-day window purely to learn its
  stops; a week covers any normal weekend or single holiday.
* **The visits are dropped.** Carrying yesterday's visits forward would leave
  `nearest_visit` matching a visit a day away, so any bus standing at a stop
  would latch a bogus `ARRIVE_LATE`. A day with no service has nothing to
  match against, and `nearest_visit` correctly returns `None`.

`stops_only()` performs exactly that carry-over, and copies the stop
collections rather than aliasing them.

## 6. What is deliberately not used

The live feed carries the vendor's own opinion about adherence:
`expectedArrivalTime`, `lateBySec`, and per-stop `stopStatus` variants
(`Awaiting` / `Present` / `Departed` / `Skipped` / `Canceled`, plus an
unmodelled `riderStatus` observed taking `OnTime` / `Delayed`).

**None of it is parsed.** Adherence here is computed from the published
schedule and observed positions alone — see
[`50-semantics-time-locality.md`](50-semantics-time-locality.md). The schedule
is read from `/v1/p/routeServiceBundle`; the live feed is read only for bus
positions.
