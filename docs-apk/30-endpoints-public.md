---
id: api.endpoints.public
title: Public (unauthenticated) endpoint catalog
kind: endpoint
apk_refs:
  - path: com/tripshot/android/services/TripshotService.java
    symbol: discoverService
    sha256: 9fa97f6f68d0910af5ae1a727cbb93e7b961bb2c803964519ed234ef00edb547
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getInstanceByName
    sha256: 0baaf5cc223e4b38244198b9e6b2d003d04791c595d72e745e6e784e45db0fbc
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getPublicInstances
    sha256: 61add88610773f9522c633d903f1209cee8ba295d896a9579d2a733a893688af
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getPublicApps
    sha256: c251b7e711c7d69b0ffcde795ce4d1baf058a9718f0ff2d43ce077a66ca1aadc
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getRoutePublic
    sha256: 2958f26e87f0a1fcb07861d25be88732cc73a3eec5faba8a6516a1a99bbe4514
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getRoutesPublic
    sha256: f032d5fbcf831c1f9b885b3f526f880ab3c73691686c421e7e00b8c4b8aceac0
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getRoutesForRouteGroupPublic
    sha256: 29fd23bb2724ede3aaa0afd93b3f0f42e82859fbc8494376ff1cca52a71f591a
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getRouteServiceBundlePublic
    sha256: fa8bd11ee83a297a2cc36559eec1b08fb9b14762caf1afffa4b6ae16e8dd8309
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getSharedRoutesPublic
    sha256: 2bea0592556f96ca55020e8703c0614d7e6d2f5ddd15e864895c29e1ec9c0d0f
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getSharedRouteDetailsPublic
    sha256: fe64408e9e32dd7c6872d30278d7b41a46b17e829d5c880f5a60b14eb31013c6
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getLiveRouteDetailsPublic
    sha256: 386bd19307a58368c6cfa6ab7a93728b4c37dd9fc4f5402bfad4ddab040fd7ce
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getSharedTripPublic
    sha256: f9d986747fa4dad8f2d22508059bdd8b471314ef4b239b1d6d1a51a8c4b71966
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getRidePublic
    sha256: 3e9a5783ec1af360b9a52bc2fc92e3799b9fb5afe2d044532571f72fd5f0f539
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getPublicBundledRide
    sha256: fad0df2923b77b85a73cf66cafa53acc5a072253cbb1b1dd8a6689951701af4c
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getV2LiveStatusPublic
    sha256: 693652a59e7cf575070693a45a7000c36de8982f9cbf1119338fbe5dc23eba26
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getVehiclePublic
    sha256: ef5998b5b768207cce6e11ad468ba5c83c95829641f06b4a8090ccb3f5e94ba4
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getVehiclesPublic
    sha256: a6c269b97d4a89b66862646366f0e27ee1fb20cdd450dbab11347219851802ec
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getCommutePlanPublic
    sha256: 36ba0bdd9e6d94207f0979ae8c7ad1d282a17de1882ddc0553e68f3c04fcbe3e
depends_on: []
---

# Public (unauthenticated) endpoint catalog

Scope: endpoints declared on the Retrofit interface `TripshotService`
(`nocommit/jadx/sources/com/tripshot/android/services/TripshotService.java`, line 265,
`public interface TripshotService`) that carry **no** `@Headers({"X-Auth-Type: user"})`
annotation and that are either

1. path-scoped under a `/p/` segment (the server's "public" variants), or
2. one of the four global / instance discovery endpoints.

The interface declares 323 `@GET`/`@POST`/`@PUT`/`@DELETE` methods in total. 14 of them have a
`/p/` path segment; all 14 are documented here, plus the 4 discovery endpoints — 18 endpoints total.

## Auth-annotation audit

`X-Auth-Type` occurs 78 times in `TripshotService.java`, always as
`@Headers({"X-Auth-Type: user"})` or `@Headers({"X-Auth-Type: user", "X-Timeout: 30"})`. The
string does not occur anywhere else in the decompiled sources under
`nocommit/jadx/sources/`, so no client-side interceptor in this APK is observed reading it; how it
is honoured is not visible from the client.

Checked explicitly, and **none** of the 18 endpoints below carry `X-Auth-Type: user`:

| Endpoint method | line of `@`-annotation | `X-Auth-Type: user`? |
| --- | --- | --- |
| `discoverService` | 422 | no |
| `getInstanceByName` | 630 | no |
| `getPublicApps` | 765 | no |
| `getPublicInstances` | 771 | no |
| `getCommutePlanPublic` | 538 | no |
| `getLiveRouteDetailsPublic` | 640 | no |
| `getPublicBundledRide` | 768 | no |
| `getRidePublic` | 833 | no |
| `getRoutePublic` | 848 | no |
| `getRouteServiceBundlePublic` | 857 | no |
| `getRoutesForRouteGroupPublic` | 866 | no |
| `getRoutesPublic` | 869 | no |
| `getSharedRouteDetailsPublic` | 889 | no (has `X-Timeout: 30`) |
| `getSharedRoutesPublic` | 898 | no |
| `getSharedTripPublic` | 904 | no |
| `getV2LiveStatusPublic` | 964 | no |
| `getVehiclePublic` | 1026 | no |
| `getVehiclesPublic` | 1036 | no |

Endpoints that **do** carry `@Headers({"X-Auth-Type: user"})` are authenticated and are out of
scope for this file; they are excluded, not documented. Note that the immediately following
declaration after several public methods is such an excluded authenticated method — e.g. line 967
`@Headers({"X-Auth-Type: user"})` follows `getV2LiveStatusPublic`, and line 1029 follows
`getVehiclePublic`. The `/p/` grep and the header grep were run over the same file, so the two
sets do not overlap.

## Type notes

Resolved from the import block of `TripshotService.java`:

- `@Nullable` is `javax.annotation.Nullable` (line 250).
- `Observable` is `io.reactivex.rxjava3.core.Observable` (line 245).
- `Response` is `retrofit2.Response` (line 254).
- `LocalDate` is **`com.tripshot.common.utils.LocalDate`** (line 221), not a `java.time` or Joda type.
- `UUID` is `java.util.UUID` (line 249).
- `DiscoveredService` is `com.tripshot.android.models.DiscoveredService` (line 8); `CommutePlan` /
  `CommutePlanRequest` are under `com.tripshot.common.plan` (lines 178-179); `SharedRide`,
  `SharedRouteDetails`, `SharedRouteLiveData`, `SharedRoutesBundle` are under
  `com.tripshot.common.shared` (lines 214-217); the remaining model types (`AppType`,
  `BundledRide`, `Instance`, `LiveStatusFilter`, `RideId`, `Route`, `RouteServiceBundle`,
  `V2LiveStatus`, `V2Ride`, `Vehicle`) are under `com.tripshot.common.models`.

Decompiled parameter names are jadx placeholders (`str`, `uuid`, `z`, `localDate`, …); the wire
names are the `@Path` / `@Query` string literals, which are what this catalog treats as
authoritative. Primitive `boolean z` parameters are non-nullable by type and are always sent.

## Global / instance discovery

Four endpoints used before any instance is selected or any user is signed in.

### `GET /v1/global/discovery`

- Method: `discoverService`
- Query: `name` (`String`), not nullable-annotated
- Response: `Observable<DiscoveredService>`
- No `@Headers`

```java
    @GET("/v1/global/discovery")
    Observable<DiscoveredService> discoverService(@Query("name") String str);
```

### `GET /v1/global/instance`

- Method: `getInstanceByName`
- Query: `name` (`String`); `applicationId` (`String`, `@Nullable`)
- Response: `Observable<Response<Instance>>` — wrapped in `retrofit2.Response`, so the client sees
  the raw HTTP status
- No `@Headers`

```java
    @GET("/v1/global/instance")
    Observable<Response<Instance>> getInstanceByName(@Query("name") String str, @Nullable @Query("applicationId") String str2);
```

### `GET /v1/global/advertisedInstance`

- Method: `getPublicInstances`
- Query: `appType` (`String`), not nullable-annotated
- Response: `Observable<List<Instance>>`
- No `@Headers`

```java
    @GET("/v1/global/advertisedInstance")
    Observable<List<Instance>> getPublicInstances(@Query("appType") String str);
```

### `GET /v1/instance/publicApp`

- Method: `getPublicApps`
- Parameters: none
- Response: `Observable<List<AppType>>`
- No `@Headers`

```java
    @GET("/v1/instance/publicApp")
    Observable<List<AppType>> getPublicApps();
```

## Routes and route services (`/p/`)

### `GET /v1/p/route/{routeId}`

- Method: `getRoutePublic`
- Path: `routeId` (`UUID`)
- Response: `Observable<Route>`
- No `@Headers`

```java
    @GET("/v1/p/route/{routeId}")
    Observable<Route> getRoutePublic(@Path("routeId") UUID uuid);
```

### `GET /v1/p/route` (by day range / region)

- Method: `getRoutesPublic`
- Query: `startDay` (`LocalDate`); `endDay` (`LocalDate`); `regionId` (`UUID`, `@Nullable`)
- Response: `Observable<List<Route>>`
- No `@Headers`

```java
    @GET("/v1/p/route")
    Observable<List<Route>> getRoutesPublic(@Query("startDay") LocalDate localDate, @Query("endDay") LocalDate localDate2, @Nullable @Query("regionId") UUID uuid);
```

### `GET /v1/p/route` (by route group)

Same path template as above — two overloads differing only in query parameters.

- Method: `getRoutesForRouteGroupPublic`
- Query: `routeGroupId` (`UUID`), not nullable-annotated
- Response: `Observable<List<Route>>`
- No `@Headers`

```java
    @GET("/v1/p/route")
    Observable<List<Route>> getRoutesForRouteGroupPublic(@Query("routeGroupId") UUID uuid);
```

### `GET /v1/p/routeServiceBundle?withScheduledRides=true&embedStops=true&withRoutes=true`

The three query parameters `withScheduledRides`, `embedStops` and `withRoutes` are hardcoded in the
annotation, not passed as arguments.

- Method: `getRouteServiceBundlePublic`
- Query (from parameters): `routeId` (`UUID`); `withNavigation` (`boolean`); `startDay`
  (`LocalDate`); `endDay` (`LocalDate`) — none nullable-annotated
- Response: `Observable<RouteServiceBundle>`
- No `@Headers`

```java
    @GET("/v1/p/routeServiceBundle?withScheduledRides=true&embedStops=true&withRoutes=true")
    Observable<RouteServiceBundle> getRouteServiceBundlePublic(@Query("routeId") UUID uuid, @Query("withNavigation") boolean z, @Query("startDay") LocalDate localDate, @Query("endDay") LocalDate localDate2);
```

## Shared routes and trips (`/p/`)

"Shared" routes are identified by `String` ids rather than `UUID` in these signatures.

### `GET /v1/p/shared/route`

- Method: `getSharedRoutesPublic`
- Query: `startDay` (`LocalDate`); `endDay` (`LocalDate`); `regionId` (`UUID`); `sourceId`
  (`List<String>`, repeated); `includePreviousDayRidesSpanningMidnight` (`boolean`) — none
  nullable-annotated
- Response: `Observable<SharedRoutesBundle>`
- No `@Headers`

```java
    @GET("/v1/p/shared/route")
    Observable<SharedRoutesBundle> getSharedRoutesPublic(@Query("startDay") LocalDate localDate, @Query("endDay") LocalDate localDate2, @Query("regionId") UUID uuid, @Query("sourceId") List<String> list, @Query("includePreviousDayRidesSpanningMidnight") boolean z);
```

### `GET /v3/p/shared/route/{routeId}?breakupExactLoops=true`

`breakupExactLoops=true` is hardcoded in the annotation. This is the only public endpoint with a
`@Headers` annotation.

- Method: `getSharedRouteDetailsPublic`
- Path: `routeId` (`String`)
- Query: `day` (`LocalDate`, `@Nullable`); `forUserId` (`UUID`, `@Nullable`);
  `includePreviousDayRidesSpanningMidnight` (`boolean`)
- Response: `Observable<SharedRouteDetails>`
- `@Headers({"X-Timeout: 30"})`

```java
    @Headers({"X-Timeout: 30"})
    @GET("/v3/p/shared/route/{routeId}?breakupExactLoops=true")
    Observable<SharedRouteDetails> getSharedRouteDetailsPublic(@Path("routeId") String str, @Nullable @Query("day") LocalDate localDate, @Nullable @Query("forUserId") UUID uuid, @Query("includePreviousDayRidesSpanningMidnight") boolean z);
```

### `GET /v2/p/shared/route/{routeId}/live`

- Method: `getLiveRouteDetailsPublic`
- Path: `routeId` (`String`)
- Query: `day` (`LocalDate`, `@Nullable`); `forUserId` (`UUID`, `@Nullable`);
  `includePreviousDayRidesSpanningMidnight` (`boolean`)
- Response: `Observable<SharedRouteLiveData>`
- No `@Headers`

```java
    @GET("/v2/p/shared/route/{routeId}/live")
    Observable<SharedRouteLiveData> getLiveRouteDetailsPublic(@Path("routeId") String str, @Nullable @Query("day") LocalDate localDate, @Nullable @Query("forUserId") UUID uuid, @Query("includePreviousDayRidesSpanningMidnight") boolean z);
```

### `GET /v1/p/shared/trip/{day}/{tripId}`

Note the unusual `@Path("day") @Nullable LocalDate` — the `day` path segment is annotated nullable
even though it is part of the path template.

- Method: `getSharedTripPublic`
- Path: `day` (`LocalDate`, `@Nullable`); `tripId` (`String`)
- Query: `forUserId` (`UUID`, `@Nullable`)
- Response: `Observable<SharedRide>`
- No `@Headers`

```java
    @GET("/v1/p/shared/trip/{day}/{tripId}")
    Observable<SharedRide> getSharedTripPublic(@Path("day") @Nullable LocalDate localDate, @Path("tripId") String str, @Nullable @Query("forUserId") UUID uuid);
```

## Rides (`/p/`)

### `GET /v2/p/ride/{rideId}`

- Method: `getRidePublic`
- Path: `rideId` (`RideId`)
- Response: `Observable<V2Ride>`
- No `@Headers`

```java
    @GET("/v2/p/ride/{rideId}")
    Observable<V2Ride> getRidePublic(@Path("rideId") RideId rideId);
```

### `GET /v2/p/ride/{rideId}?bundled=true`

`bundled=true` is hardcoded in the annotation; same path base as `getRidePublic` but a different
response shape.

- Method: `getPublicBundledRide`
- Path: `rideId` (`RideId`)
- Query: `forUserId` (`UUID`), not nullable-annotated
- Response: `Observable<BundledRide>`
- No `@Headers`

```java
    @GET("/v2/p/ride/{rideId}?bundled=true")
    Observable<BundledRide> getPublicBundledRide(@Path("rideId") RideId rideId, @Query("forUserId") UUID uuid);
```

## Live status (`/p/`)

### `POST /v1/p/liveStatus`

A `POST` despite being a read; the filter travels in the body. Note the version asymmetry: the
authenticated sibling at line 961 is `@POST("/v2/liveStatus")` while the public variant is `/v1/p/`.

- Method: `getV2LiveStatusPublic`
- Query: `regionId` (`UUID`), not nullable-annotated
- Body: `LiveStatusFilter`
- Response: `Observable<V2LiveStatus>`
- No `@Headers`

```java
    @POST("/v1/p/liveStatus")
    Observable<V2LiveStatus> getV2LiveStatusPublic(@Query("regionId") UUID uuid, @Body LiveStatusFilter liveStatusFilter);
```

## Vehicles (`/p/`)

### `GET /v1/p/vehicle/{vehicleId}`

- Method: `getVehiclePublic`
- Path: `vehicleId` (`UUID`)
- Response: `Observable<Vehicle>`
- No `@Headers`

```java
    @GET("/v1/p/vehicle/{vehicleId}")
    Observable<Vehicle> getVehiclePublic(@Path("vehicleId") UUID uuid);
```

### `GET /v1/p/vehicle`

- Method: `getVehiclesPublic`
- Query: `regionId` (`UUID`), not nullable-annotated
- Response: `Observable<List<Vehicle>>`
- No `@Headers`

```java
    @GET("/v1/p/vehicle")
    Observable<List<Vehicle>> getVehiclesPublic(@Query("regionId") UUID uuid);
```

## Trip planning (`/p/`)

### `POST /v2/p/commutePlan`

- Method: `getCommutePlanPublic`
- Body: `CommutePlanRequest`
- Response: `Observable<CommutePlan>` (the authenticated sibling at line 535,
  `@POST("/v2/commutePlan")`, returns `FullCommutePlan`)
- No `@Headers`

```java
    @POST("/v2/p/commutePlan")
    Observable<CommutePlan> getCommutePlanPublic(@Body CommutePlanRequest commutePlanRequest);
```

## Boundary notes / ambiguities

- **`getVehiclesByCodePublic` is named "Public" but its path has no `/p/` segment.** At line 1033
  the annotation is `@GET("/v1/vehicle")` with no `@Headers`. It is therefore outside the `/p/`
  grep that defines this catalog's scope, and nothing in the client tells us whether that path
  accepts unauthenticated requests. Not documented as public.

  ```java
    @GET("/v1/vehicle")
    Observable<List<Vehicle>> getVehiclesByCodePublic(@Query("code") List<Integer> list);
  ```

- **Absence of `X-Auth-Type: user` is not proof of unauthenticated access.** Many endpoints without
  that header are plainly rider-scoped (e.g. `@GET("/v1/commuteJournal/{userId}")` at line 532).
  The two criteria used here — a `/p/` path segment and the global/instance discovery paths — are
  the only signals the client actually exposes. Whether the server enforces anything is not
  observable from the decompiled code.

- **Two methods share `GET /v1/p/route`.** `getRoutesPublic` and `getRoutesForRouteGroupPublic`
  have identical path templates and differ only in query parameters.

- **Two methods share the `GET /v2/p/ride/{rideId}` base.** `getRidePublic` and
  `getPublicBundledRide`; the latter pins `?bundled=true` in the annotation.

- **`X-Timeout` is only a client-side hint as far as this file shows.** It appears in `@Headers`
  alongside `X-Auth-Type` elsewhere in the interface; no consumer of the literal is present in the
  decompiled sources, so its effect is not documented here.

- Line numbers cited throughout refer to
  `nocommit/jadx/sources/com/tripshot/android/services/TripshotService.java` as decompiled by jadx
  from TripShot Rider v127 (versionCode 541); jadx sorts interface members alphabetically by method
  name, so line order is not source order.
