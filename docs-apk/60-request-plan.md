---
id: integration.request-plan
title: Request plan — endpoints, parameters and cadence
kind: semantics
apk_refs:
  - path: com/tripshot/android/rider/ExploreFragment.java
    symbol: STOPS_REFRESH_INTERVAL
    sha256: 765a50646eabcf974b76bd635022b364f1e4fdc4fcd2282f571b971df5d9b619
  - path: com/tripshot/common/models/LiveStatusFilter.java
    symbol: LiveStatusFilter
    sha256: 309156b051a5e7e9925acd7690991d2306d034aa8abbecf64625f1f1965f59d1
  - path: com/tripshot/common/models/RideId.java
    symbol: fromString
    sha256: 9b9657b3739e1fd2a8368eb486ed851b0f40ab88cbf414439f955887e78dd090
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getV2LiveStatusPublic
    sha256: 693652a59e7cf575070693a45a7000c36de8982f9cbf1119338fbe5dc23eba26
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getRouteServiceBundlePublic
    sha256: fa8bd11ee83a297a2cc36559eec1b08fb9b14762caf1afffa4b6ae16e8dd8309
depends_on: [api.discovery, api.endpoints.public, api.transport]
---

# Request plan

Exactly two things are read: **the published schedule** and **bus positions**.
No endpoint outside the public `/p/` set is called, and no credential is ever
sent.

## Bootstrap (once per config entry)

| # | Call | Purpose |
|---|---|---|
| 1 | `GET /v1/global/advertisedInstance?appType=RiderApp` | list instances → pick transit system |
| 2 | `GET /v1/global/discovery?name=<name>` | resolve `apiBaseUrl`; **404 ⇒ default host** |
| 3 | `GET /v1/p/route?startDay=D&endDay=D` | list routes → pick line |

See [`20-discovery.md`](20-discovery.md). Thereafter every request carries
`X-Instance-Id` and `X-Tripshot-Build` ([`10-transport.md`](10-transport.md)).

## Schedule refresh (every 300 s)

```java
    private static final int STOPS_REFRESH_INTERVAL = 300000;
```

```java
    @GET("/v1/p/routeServiceBundle?withScheduledRides=true&embedStops=true&withRoutes=true")
    Observable<RouteServiceBundle> getRouteServiceBundlePublic(@Query("routeId") UUID uuid, @Query("withNavigation") boolean z, @Query("startDay") LocalDate localDate, @Query("endDay") LocalDate localDate2);
```

> **The three flags in that path template must be sent explicitly.**
> <!-- anchor: pinned-params -->
> The client pins `withScheduledRides`, `embedStops` and `withRoutes` inside
> the annotation rather than passing them as `@Query` arguments, so a
> reimplementation that treats the path as just `/v1/p/routeServiceBundle`
> silently drops all three. The API then answers **HTTP 200** with a
> structurally similar but hollow payload:
>
> | | with the flags | without |
> |---|---|---|
> | `routes` | 1 | **0** |
> | `scheduledRides` | 24 | **0** |
> | `vias` / `viaStops` | 8 / 4 | 8 / 4 |
> | `ViaStop.stop` | embedded object | **bare id string** |
> | bytes | 29,251 | 3,048 |
>
> `embedStops` is the one that bites: the vias still look right, but each
> `stop` is an id rather than the object carrying name and location, so every
> stop is skipped and the schedule comes out empty. Guarded by
> `tests/test_endpoints.py` and by a loud error in `build_schedule` when a
> `ViaStop.stop` arrives as a string.

Sent as the three pinned flags plus
`routeId=<route>&withNavigation=false&startDay=D&endDay=D`, with `D` today in
the transit system's timezone formatted `YYYY-MM-DD`.

On a day the route does not run the response carries no `routeServices` at
all. The stops are then taken from the last known schedule, or — on a first
setup that lands on such a day — from a single widened request with
`endDay = startDay + 7`, made purely to learn the stops. See
[`45-schedule-visits.md`](45-schedule-visits.md#no-service-days).

Consumed:

* `routeServices[].vias[]` → `ViaStop` entries give each stop's `stopId`,
  `name` and `location`. (`geofence` is read past — the geofence is ours; see
  [`51-semantics-geo-locality.md`](51-semantics-geo-locality.md).)
* `scheduledRides[][]` → `ScheduledStop` entries, merged into physical visits
  per [`45-schedule-visits.md`](45-schedule-visits.md).
* `routes[]` → `regionId` and the display name. (`lateNoticeWarnTimeSec` is
  **not** read — thresholds are configured, not inherited.)

## Position refresh (configurable, default 30 s)

```java
    @POST("/v1/p/liveStatus")
    Observable<V2LiveStatus> getV2LiveStatusPublic(@Query("regionId") UUID uuid, @Body LiveStatusFilter liveStatusFilter);
```

```java
public final class LiveStatusFilter {
    private final ImmutableSet<RideId> rideIds;
    private final ImmutableSet<UUID> vehicleIds;
```

**Only the top-level `timestamp` and `vehicleStatuses[]` are parsed** —
`vehicleId`, `name`, `location`, `when`. The response's `rides[]`, with the vendor's `stopStatus`,
`expectedArrivalTime` and `lateBySec`, is ignored entirely.

### Why the request is still filtered

An empty filter returns the whole region. Measured against UofR:

| Filter | Response | Rides |
|---|---|---|
| `{"rideIds":[],"vehicleIds":[]}` | **4,573,655 B** | 436 (all routes) |
| today's Red Line ride ids | **145,807 B** | 24 (this route only) |

A 4.5 MB body every 30 s would be abusive, and the filter also scopes
`vehicleStatuses` to buses serving this route — which is what makes the bus
count meaningful. Filtering is what the client does too.

Ride ids are built as `"<scheduledRideId>:<YYYY-MM-DD>"` from the schedule
refresh — `RideId` is composite, not a UUID:

```java
    public static RideId fromString(String str) {
```

They are used **only** to scope the request; the rides themselves are not read.

### Cadence, measured

Polling the filtered endpoint every ~3 s for a minute:

| Layer | Cadence |
|---|---|
| Bus position (`when`) | new fix roughly every **11 s** |
| Server snapshot (`timestamp`) | regenerates roughly every **5 s** |
| Lag (snapshot − fix) | 4–6 s |

The feed is not cached at 30 s — 30 s is the client's UI refresh
(`ACTIVE_TRIP_REFRESH_INTERVAL`), and is the default here, configurable from
10 s upward. Polling faster than ~11 s cannot surface a newer bus position;
polling slower quantises observed arrival and departure times to the interval.

## Endpoints deliberately not used

| Endpoint | Reason |
|---|---|
| `GET /v1/region` | not a `/p/` endpoint; `regionId` is read off public payloads |
| `GET /v1/p/vehicle` | roster only, carries no position |
| `GET /v2/p/shared/route/{id}/live` | route-scoped and lighter (159 KB) but carries no bus positions |
| everything with `@Headers({"X-Auth-Type: user"})` | authenticated |
| every login / signup / OIDC / SAML path | out of scope by construction |
