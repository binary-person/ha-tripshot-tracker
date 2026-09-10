---
id: semantics.geo-locality
title: Geo locality — at-stop determination
kind: semantics
apk_refs:
  - path: com/tripshot/common/models/Stop.java
    symbol: location
    sha256: 4d6e9d7e11716c62c2636cd7ee326c2d6b207fc204b781e23ba2a02a3a4c6f22
  - path: com/tripshot/common/models/Shape.java
    symbol: Circle
    sha256: f9b3b657eabfa83e5c58deb61da4f55883f648a3daa5a1f7a1dbdd07cf275e31
depends_on: [api.models.schedule, api.models.live]
---

# Geo locality

Reduces `(bus position, stop position, radius) -> AT_STOP | NOT_AT_STOP`.

## 1. The geofence is ours
<!-- anchor: geofence-size -->

The API does publish a per-stop geofence — `Stop.geofence` is a `Shape`, and a
circular one serialises as `{"Circle": 60}`, the number being a radius in
metres:

```java
    public static final class Circle extends Shape {
```

Observed values on the Red Line: **60 m** at Eastman Living Center, **72 m** at
Rush Rhees Library Back Side.

**It is not used.** The geofence is a configuration setting instead, expressed
as a diameter in feet:

```
radius_m = diameter_ft × 0.3048 / 2
```

Default **500 ft diameter → 76.2 m radius**, which is comparable to the
vendor's own 60–72 m but under our control and uniform across stops. Defining
it ourselves means a change to the operator's geofence cannot silently shift
the statistics.

Stop *positions* still come from the API — `Stop.location`, wire keys `lt` and
`lg`.

## 2. The containment test
<!-- anchor: containment -->

```
hav(x)  = sin²(x / 2)
a       = hav(φ₂ − φ₁) + cos(φ₁)·cos(φ₂)·hav(λ₂ − λ₁)
d       = 2·R·asin(√a)        R = 6371009.0 m
AT_STOP ⟺ d ≤ radius_m
```

Great-circle distance on a sphere of mean earth radius. The comparison is
inclusive (`≤`), so a bus exactly on the boundary is at the stop — our choice,
and the natural reading of "within the geofence".

Stops must be far enough apart that geofences do not overlap, or one bus could
be at two stops at once. On the Red Line the two stops are 4,019 m apart, against
a 76.2 m radius — a factor of ~53. `tests/test_locality.py`
asserts the separation exceeds two radii.

## 3. Which position is tested

From `V2LiveStatus.vehicleStatuses[]`:

| Field | Use |
|---|---|
| `vehicleId` | stable id; latches are keyed by it |
| `name` / `gtfsName` | the fleet number a person would recognise, e.g. `2603` |
| `location` | `{lt, lg}` — the position tested |
| `when` | when the **bus** reported it, not when we fetched it |

`accuracy`, `bearing` and `speed` are parsed by neither this integration nor
used to widen the radius.

## 4. Staleness
<!-- anchor: staleness -->

`when` can be arbitrarily old — an unfiltered region-wide capture held fixes
three weeks stale next to fixes two seconds old. A stale fix parked inside a
geofence would pin a permanent `AT_STOP`, so positions older than
`position_max_age_sec` (default **120 s**, configurable) are ignored.

Buses report roughly every 11 s, so 120 s is about ten missed reports —
comfortably tolerant of a brief gap while still catching a bus that has gone
quiet.

When a bus's position goes stale mid-visit the latch is **held**, not forced to
`NA`. A GPS dropout is not evidence of departure, and counting one would
corrupt the statistics. The cost is that a bus which ends its run inside a
geofence stays latched until it reappears elsewhere or leaves the feed.

## 5. Debouncing a crossing
<!-- anchor: debounce -->

The containment test is instantaneous, and a bus parked near the boundary can
be pushed across it by ordinary GPS noise. Each oscillation would otherwise
book a **departure and a fresh arrival** — four counts where two belong. It is
the only failure mode here that *inflates* counters rather than dropping them,
and inflation is far harder to notice after the fact.

A crossing is therefore acted on only once `confirm_polls` consecutive
observations agree. The default is **2**. Setting it to **1** acts on the first
poll, which is the off switch — the field counts polls, so `0` is not a
coherent value and the form rejects it.

The event is **timestamped at the first observation that saw the crossing**,
not at the poll that confirmed it. Confirmation delays recognition by a poll
but costs no accuracy in the recorded time — which matters, because that time
is what the arrival and departure windows are judged against.

```
poll 1   inside            settled: at stop
poll 2   outside           pending departure, seen 1/2  -> nothing counted
poll 3   inside            flicker withdrawn            -> nothing counted
poll 4   outside           pending departure, seen 1/2
poll 5   outside           confirmed                    -> departure counted,
                                                           timestamped poll 4
```

Priming after a restart is exempt: it adopts whatever the first poll finds,
immediately and without counting, so there is nothing to debounce.

The trade is a genuine visit shorter than `confirm_polls` intervals becomes
invisible. At the default 30 s poll that is a stop of under a minute, against
observed dwells of 3–5 minutes — but it is the reason to lower the poll
interval rather than raise the confirmations if a route has brief stops.

