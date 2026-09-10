---
id: semantics.time-locality
title: Time locality — schedule adherence semantics
kind: semantics
apk_refs:
  - path: com/tripshot/common/models/ScheduledStop.java
    symbol: arrivalTime
    sha256: de48080ae0f106c0e1ec13d2038a5afaa083f32b2133ee65386fab08c7cf7d37
  - path: com/tripshot/android/rider/models/StopTimeForDisplay.java
    symbol: isLate
    sha256: e9d996e307257f625deae5f38feeb9c89b5030fcf5d757b32e7db2b9ea740c6c
depends_on: [schedule.visits, api.models.live]
---

# Time locality

Reduces `(now, arrival window, departure window, geo state) -> verdict`.

**The thresholds here are ours.** The client's own notion of lateness is
described in §4 only to record that it exists and is *not* used.

## 1. Inputs

From the published schedule, per physical visit
([`45-schedule-visits.md`](45-schedule-visits.md)):

```
scheduled_arrival    the instant the bus should pull in
scheduled_departure  the instant it should pull out
```

Two configured buffers, set at integration setup and applying to every stop on
the route:

| Setting | Meaning |
|---|---|
| `arrival_early_buffer_sec` | how far **ahead** of schedule a bus may arrive and still count as on time |
| `departure_late_buffer_sec` | how far **behind** schedule a bus may depart and still count as on time |
| `measurement_grace_sec` | tolerance on the strict side of **both** windows, for sampling precision |

## 2. The windows
<!-- anchor: windows -->

Each buffer extends its window in one direction only — the direction in which
slack is tolerable:

Each window also carries a **measurement grace** on its strict side:

```
arrival_window   = [scheduled_arrival − early_buffer,  scheduled_arrival + grace]
departure_window = [scheduled_departure − grace, scheduled_departure + late_buffer]
```

Read plainly: a bus is **on time arriving** if it shows up at most
`arrival_early_buffer` early and no more than `grace` past the scheduled
arrival. It is **on time departing** if it leaves no more than `grace` before
the scheduled departure and at most `departure_late_buffer` late.

### Why the grace exists
<!-- anchor: grace -->

Without it each window has a **zero-tolerance side** — arrival has no late
tolerance, departure no early tolerance — and those edges are narrower than
the measurement precision:

| Source of lag | Bound |
|---|---|
| Bus emits its next position report | up to ~11 s |
| That fix reaches the server view | ~5 s |
| Our next poll observes it | up to the poll interval (default 30 s) |

So an observed crossing sits roughly −7 s to +45 s of the real one (the geofence
is entered slightly *before* the stop marker, which pulls the other way). Against
a 120 s buffer that is noise; against a **0 s** edge it is decisive — a bus
arriving exactly on schedule would routinely be recorded `ARRIVE_LATE`, and the
verdict would be reporting our sampling rate rather than the bus.

The grace is a **single number applied to both strict edges**, and by default
it is **derived from the poll interval** rather than stored:

```
grace = poll_interval + FEED_LAG_SEC          (FEED_LAG_SEC = 16)
```

Deriving matters. The grace is a statement about resolution, not a preference,
so it must track the setting that justifies it — a stored number would go
stale the moment the poll interval changed, leaving the tolerance
over-generous with nothing pointing at why. `FEED_LAG_SEC` covers what remains
even at an instantaneous poll: ~11 s until the bus emits its next fix, ~5 s for
that fix to reach the server's view, both measured against the live feed.

| Poll interval | Derived grace |
|---|---|
| 10 s | 26 s |
| 15 s | 31 s |
| 30 s (default) | 46 s |
| 60 s | 76 s |

Setting the option to any value **≥ 0 overrides the derivation and is used
literally** — configuring 11 gives exactly 11 seconds, never silently adjusted.
A value below the poll interval cannot cover the sampling lag, so it is logged
at debug when one is in force.

> **This is deliberately not a job for automations.** An automation that
> triggered on `depart_early` and then filtered on
> `deviation_seconds < −180` would be a *second* definition of early, living
> in YAML, silently disagreeing with the counters. There is one definition,
> and it is the windows. If early is firing too readily, widen the grace or
> the buffer — the counters move with it.

### Grace and window overlap

On a short-dwell visit the grace widens both strict edges past each other, so
the arrival and departure windows overlap. That is harmless and expected: the
two windows classify **different events** — arrival when a bus enters the
geofence, departure when it leaves — and never both from one sample.

The invariant that is actually checked is therefore about the *schedule*
(`scheduled_arrival ≤ scheduled_departure`), not the window edges. The grace
also cannot affect the consecutive-visit headway check, which compares the
outward-facing edges governed by the buffers.

The asymmetry is deliberate and is how transit adherence is normally judged:
running early strands riders who arrived on time, so it is not tolerated past
the buffer; running a little late is unavoidable, so it is.

| | Arriving | Departing |
|---|---|---|
| before the window | `ARRIVE_EARLY` | `DEPART_EARLY` |
| inside the window | `ARRIVE_ON_TIME` | `DEPART_ON_TIME` |
| after the window | `ARRIVE_LATE` | `DEPART_LATE` |

Both windows are closed intervals — the endpoints count as on time.

## 3. Window consistency
<!-- anchor: window-consistency -->

The arrival window ends at `scheduled_arrival`; the departure window begins at
`scheduled_departure`. They must not overlap, or one instant would be
simultaneously a valid arrival and a valid departure and the verdict would be
ambiguous:

```
arrival_window.end  ≤  departure_window.start
      ⟺  scheduled_arrival ≤ scheduled_departure
```

Because each buffer extends *away* from the other, no buffer setting can create
an overlap within a visit — only a schedule with a departure before its own
arrival could. Touching at exactly one point is allowed and expected: that is a
zero-dwell visit, where scheduled arrival and departure are the same instant.

A second check covers what buffers *can* break: consecutive visits to the same
stop must stay separated once the buffers are applied, or "the nearest
scheduled visit" becomes ambiguous.

```
next_visit.arrival_window.start  ≥  previous_visit.departure_window.end
```

On the Red Line, visits to a stop are ~40 minutes apart, so the 120 s defaults
have wide margin; buffers of 20 minutes each way trip the check. Both
validations run on every schedule refresh, and their results surface on the
**Schedule health** diagnostic sensor. `tests/test_observations.py::TestValidation`
covers them.

## 4. The client's own late rule — recorded, not used

`StopTimeForDisplay` is the only place the decompiled client classifies
adherence:

```java
    public boolean isLate() {
```

Its rule is: `ride.state is Active` **and** `expectedArrivalTime − scheduled >
300000 ms`. It is *predictive* — it compares the server's ETA against the
schedule — and it is binary, with no early or on-time branch and no notion of
departure.

None of that is used here. This integration measures what the bus **did**
(a geofence crossing, timed) rather than what the server **expects**. That is
the only way to judge departures at all, and it is what "arrive/depart
early/on-time/late" most naturally means. Consequently these counters will not
agree with the late badge a rider sees in the app, by design.

Also unused, for the same reason: `lateBySec`, `expectedArrivalTime`, the
`stopStatus` variants, and `RideState`.

## 5. The reduction

```
time_locality(now, arrival_window, departure_window, geo) -> TimeLocality
```

| geo state | condition | result |
|---|---|---|
| `NOT_AT_STOP` | — | `NA` |
| `AT_STOP` | `now < arrival_window.start` | `ARRIVE_EARLY` |
| `AT_STOP` | `now ∈ arrival_window` | `ARRIVE_ON_TIME` |
| `AT_STOP` | `now > arrival_window.end` | `ARRIVE_LATE` |

While a bus is at a stop the verdict always describes its **arrival**. A bus
still standing at a stop has not departed, however overdue — so departure is
never inferred from a single sample. It is classified on the leaving edge:

```
on AT_STOP -> NOT_AT_STOP:  classify_departure(now, departure_window)
```

## 6. Stickiness
<!-- anchor: stickiness -->

Required behaviour: *a state that leaves `NA` is latched until it returns to
`NA`.* Per (stop, bus):

* `NA` → `ARRIVE_*` latches that verdict and increments its counter **once**.
* While latched, later samples neither re-classify nor re-count; the reported
  state stays the latched verdict even as the bus overstays.
* The `AT_STOP` → `NOT_AT_STOP` edge classifies the departure and increments
  its counter **once**, then the latch returns to `NA` and re-arms.

The departure window is **pinned at latch time**, so a bus dwelling long enough
for a later visit to become "nearest" is still judged against the visit it
actually arrived for.

Latches are keyed by **(stop, bus)** — buses carry stable ids — so two buses at
one stop are tracked independently, and a bus that vanishes from the feed
mid-latch is dropped **without** counting a departure, since none was observed.

Each (stop, bus, visit) therefore contributes at most one arrival and one
departure, which is what keeps the totals interpretable.

## 7. When a counter fires — the complete set
<!-- anchor: firing-cases -->

For **one stop and one bus**, exactly two things increment a counter: crossing
into the geofence, and crossing back out. Nothing else does.

Let `A` = scheduled arrival, `D` = scheduled departure, `E` = early buffer,
`L` = late buffer, `t_in` = the first poll that sees the bus inside, `t_out` =
the first poll that sees it outside again.

```
arrival window   [A − E,  A]        departure window  [D,  D + L]
```

| | `t_in < A − E` | `A − E ≤ t_in ≤ A` | `t_in > A` |
|---|---|---|---|
| **`t_out < D`** | early + early | on time + early | late + early |
| **`D ≤ t_out ≤ D+L`** | early + on time | on time + on time | late + on time |
| **`t_out > D+L`** | early + late | on time + late | late + late |

All nine pairs are reachable whenever the visit has a real dwell. On a
zero-dwell visit (`A == D`) the `late + early` cell is impossible, since it
would need `A < t_in ≤ t_out < A`.

Every complete visit therefore contributes **exactly two** counts: one arrival,
one departure.

### Cases that fire nothing
<!-- anchor: no-fire -->

| Case | Behaviour |
|---|---|
| Bus never enters the geofence — passes by, or the stop is skipped | nothing counted; there is no "missed visit" counter |
| Bus dwelling, poll after poll | arrival counted once on entry, then held; repeats are silent |
| Bus position goes stale (older than the freshness bound) | observation is not built; a latch is **held**, not released — a dropout is not a departure |
| Bus disappears from the feed while inside | latch dropped, arrival stays counted, **no departure** — we never saw it leave |
| Bus enters and leaves entirely between two polls | invisible; both counts missed. Observed dwells on this route are 3–5 minutes against a 30 s poll, so this needs a non-stopping pass-through |
| First poll after a Home Assistant restart | a bus already inside is **adopted without counting** — see below |

### Priming after a restart
<!-- anchor: priming -->

Counters are restored from Home Assistant; latches are not, because they live
in memory. Without care, a bus standing inside a geofence across a restart
would be counted as arriving a second time for a visit already recorded.

The first poll of a session therefore latches whatever it finds **without
incrementing**. The bus's eventual departure is still counted normally. The
cost is that a bus arriving during that very first poll has its arrival missed
— an undercount of at most one, chosen over a double count, since these are
cumulative statistics.

### Geofence flicker
<!-- anchor: flicker -->

A bus hovering on the geofence boundary while GPS noise pushes it across would
otherwise book a departure and a fresh arrival on each oscillation — four
counts where two belong, and the only failure mode here that *inflates*
counters rather than dropping them.

A crossing is therefore only acted on once `confirm_polls` consecutive
observations agree, and is timestamped at the first of them. See
[`51-semantics-geo-locality.md`](51-semantics-geo-locality.md#debounce).

## 8. Sampling granularity
<!-- anchor: sampling -->

Measured against the live feed:

| Layer | Cadence |
|---|---|
| Bus position reports (`when`) | a new fix roughly every **11 s** |
| Server snapshot (`timestamp`) | regenerates roughly every **5 s** |
| Lag (snapshot − fix) | 4–6 s |

So the data is not cached at 30 s; the client's 30 s refresh is a UI choice.
The poll interval is configurable and defaults to 30 s. It bounds the precision
of every observed time: a 30 s poll quantises arrival and departure instants to
±30 s, which is well inside a 120 s buffer but would matter if the buffers were
tightened toward a minute.
