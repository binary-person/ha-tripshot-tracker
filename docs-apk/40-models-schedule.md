---
id: api.models.schedule
title: Schedule and stop models
kind: model
apk_refs:
  - path: com/tripshot/common/models/RouteServiceBundle.java
    symbol: RouteServiceBundle
    sha256: 4651fd8a8859563ae28eb00bf9ca56195184aa8dd5b7a7c2166b2cb50540ac04
  - path: com/tripshot/common/models/FullRouteServiceBundle.java
    symbol: FullRouteServiceBundle
    sha256: 5a2e1a7d3f4d1de106dcabd152af134bc2a0ab40a2eabfcfb27139a8b191b933
  - path: com/tripshot/common/models/RouteService.java
    symbol: RouteService
    sha256: 566ac63d7afefe3c0ff1a91979a036821ccc48121b617e7c9cb023af5f85c2d4
  - path: com/tripshot/common/models/Route.java
    symbol: Route
    sha256: 045548f3b933279af46caf32524981566530facd8cf96d0466a14b9c2250e8f7
  - path: com/tripshot/common/models/Stop.java
    symbol: Stop
    sha256: dad29543fa50f7379865080e024197eaad5f86552a412abf41198db610070b0c
  - path: com/tripshot/common/models/Via.java
    symbol: Via
    sha256: 5e224176f77729a2b93d1e49cfdb749cde765d442465f854c119a9aa43b9a8f0
  - path: com/tripshot/common/models/ScheduledRide.java
    symbol: ScheduledRide
    sha256: 37d3d92d0bf6412543a6bfff4cd48c3c8e24d6d7bffdd547196dfac7ae977535
  - path: com/tripshot/common/models/ScheduledStop.java
    symbol: ScheduledStop
    sha256: 1b8ce20707cae283c12f23440674847bede90eaa7135ee013e2d7a58a86b48c6
  - path: com/tripshot/common/models/Shape.java
    symbol: Shape
    sha256: bc4ac7b4fc09b60e7193bb6e8c04d1a4ee0a5154af31f60a5fa9a03f621955c8
  - path: com/tripshot/common/models/AbsoluteShape.java
    symbol: AbsoluteShape
    sha256: 7a1555d981c9e43692b06756d564919468f7ea0c39e36b78d4848762753599f9
  - path: com/tripshot/common/models/VisitType.java
    symbol: VisitType
    sha256: 3ce2653ca0cd1deaf62b3c5e1a72829a4aee1dc8dcca6495a9d5aaee283e317c
  - path: com/tripshot/common/models/StopByRequestStatus.java
    symbol: StopByRequestStatus
    sha256: adc6b15cdb29ab1b75132535bce57fec344cb69bc4bfb53a7f67dd528b0cf1fe
  - path: com/tripshot/common/utils/LatLng.java
    symbol: LatLng
    sha256: 69fb0560f3eaff483f5595426dd2cce72088eae15f73a9bc18a6556d1e1a594a
depends_on: [api.transport]
---

# Schedule and stop models

Static / schedule side of the TripShot data model. All types are Jackson-annotated
POJOs in `com.tripshot.common.models` (plus `com.tripshot.common.utils.LatLng`).

Conventions used throughout this document:

- A constructor parameter typed `com.google.common.base.Optional<T>` means the JSON
  field is **optional / nullable**. The corresponding getter returns
  `Optional.fromNullable(field)`, and the backing field carries `@Nullable`.
- A plain (non-`Optional`) reference parameter is **required**: every one is passed
  through `Preconditions.checkNotNull(...)` in the constructor body, so a missing or
  null JSON value throws.
- `@JsonCreator` parameter names are authoritative for **deserialization** (which is
  all a read-only client cares about). Where a getter's `@JsonProperty` name differs
  from the creator name, both are called out.
- `TimeOfDay` serializes as the string `"HH:MM:SS"` and `LocalDate` as a date string;
  the serializer internals are documented elsewhere. `TimeOfDay` permits hour values
  `0..47`, so a value past midnight on the service day is expressible (e.g. `"25:10:00"`).

## Naming caveat: there is no `Geofence` class

There is **no** `Geofence` type in this APK. `find -iname 'Geofence*.java'` over the
decompiled tree returns only `com/google/android/gms/location/Geofence.java` (Play
Services). The stop arrival radius is carried by `Stop.geofence`, whose Java type is
`com.tripshot.common.models.Shape` — documented below. A second, absolutely-positioned
variant, `AbsoluteShape`, exists and is used for on-demand zones, not for stops.

## Naming caveat: there is no `arrivalRadiusMeters` field

`grep -rin 'arrivalradius'` over the entire decompiled tree returns **zero hits**. No
`Via`, `ViaStop`, `NavVia`, `ScheduledStop`, `Stop`, or any other class in this APK
exposes a per-via `arrivalRadiusMeters`. The only radius on the schedule side is
`Shape.Circle.radiusMeters` (a `double`, **metres**), reached via `Stop.geofence`. See
[Geo radius for "at stop" determination](#geo-radius-for-at-stop-determination).

---

## RouteServiceBundle

Response body of `GET /v1/p/routeServiceBundle` (the unauthenticated/public variant).
The authenticated `GET /v1/routeServiceBundle` returns `FullRouteServiceBundle`, a
subclass that only narrows the `routes` element type.

Verbatim from `com/tripshot/android/services/TripshotService.java`:

```java
    @GET("/v1/routeServiceBundle?withScheduledRides=true&embedStops=true&withRoutes=true")
    Observable<FullRouteServiceBundle> getRouteServiceBundle(@Query("routeId") UUID uuid, @Query("withNavigation") boolean z, @Query("startDay") LocalDate localDate, @Query("endDay") LocalDate localDate2);

    @GET("/v1/p/routeServiceBundle?withScheduledRides=true&embedStops=true&withRoutes=true")
    Observable<RouteServiceBundle> getRouteServiceBundlePublic(@Query("routeId") UUID uuid, @Query("withNavigation") boolean z, @Query("startDay") LocalDate localDate, @Query("endDay") LocalDate localDate2);
```

| JSON property | Java type | Optional? | Meaning |
|---|---|---|---|
| `routeServices` | `List<RouteService>` | required | The route-service (schedule pattern) records matching the query. |
| `scheduledRides` | `List<List<ScheduledRide>>` | required (may be empty) | Outer list is **index-aligned with `routeServices`**: `scheduledRides[i]` is the set of rides for `routeServices[i]`. |
| `routes` | `List<? extends Route>` | required | Route metadata for the `routeId`s referenced by the route services. `FullRouteServiceBundle` narrows this to `List<FullRoute>`. |

Constructor-enforced invariant and post-processing:

- `Preconditions.checkArgument(scheduledRides.isEmpty() || scheduledRides.size() == routeServices.size())`
  — so `scheduledRides` is either entirely absent/empty or exactly parallel to `routeServices`.
- Each inner ride list is **sorted client-side** by the first mutually-present
  `ScheduledStop.arrivalTime` (see the inline `Comparator<ScheduledRide>`); the server's
  ordering is not preserved.
- `stops`, `stopMap`, and `routeMap` are `@JsonIgnore` derived indexes, not wire fields.
  `stops`/`stopMap` are built by walking every `RouteService.vias`, keeping each
  `Via.ViaStop`'s embedded `Stop`, de-duplicated by `stopId` in first-seen order. This
  is why the `embedStops=true` query parameter matters: without embedded stops there
  would be no `Stop` objects at all.

```java
    @JsonCreator
    public RouteServiceBundle(@JsonProperty("routeServices") List<RouteService> list, @JsonProperty("scheduledRides") List<List<ScheduledRide>> list2, @JsonProperty("routes") List<? extends Route> list3) {
```

### FullRouteServiceBundle

Authenticated variant. Same three wire fields; `routes` elements are `FullRoute`.

```java
    @JsonCreator
    public FullRouteServiceBundle(@JsonProperty("routeServices") List<RouteService> list, @JsonProperty("scheduledRides") List<List<ScheduledRide>> list2, @JsonProperty("routes") List<FullRoute> list3) {
```

---

## RouteService

One service pattern for a route: an effective date window, a day-of-week mask, and the
ordered `vias` (stops and waypoints) that the route traverses. `final class`.

| JSON property | Java type | Optional? | Meaning |
|---|---|---|---|
| `routeServiceId` | `UUID` | required | Primary key. |
| `routeId` | `UUID` | required | FK into `RouteServiceBundle.routes`. |
| `startDate` | `LocalDate` | required | First date the pattern can be effective. |
| `endDate` | `Optional<LocalDate>` | **optional** | Last effective date; absent means open-ended. Constructor asserts `endDate >= startDate` when present. |
| `daysOfWeek` | `Set<DayOfWeek>` | required | Days the pattern normally runs (`com.tripshot.common.utils.DayOfWeek`). |
| `excludedDays` | `Set<LocalDate>` | required (may be empty) | Dates suppressed despite the day-of-week mask. |
| `extraDays` | `Set<LocalDate>` | required (may be empty) | Additional service dates. |
| `vias` | `List<Via>` | required | Ordered traversal list; polymorphic (see [Via](#via)). |
| `loopOptions` | `Optional<LoopOptions>` | **optional** | Present for headway/loop services. `LoopOptions(startTime: TimeOfDay, endTime: TimeOfDay, exactTimes: boolean, roundTripTimeSec: int)`. |
| `legs` | `Optional<? extends List<RouteLeg>>` | **optional** | Navigation geometry; populated only when `withNavigation=true`/`withNav=true`. `RouteLeg(startPoint: NavVia, endPoint: NavVia, steps: List<RouteStep>)`. |
| `overflow` | `Optional<? extends List<RideId>>` | **optional** | Overflow ride references. |
| `etaAvailable` | `boolean` | required (primitive) | Whether ETAs are published for this service. Getter is `isEtaAvailable()`. |
| `version` | `UUID` | required | Optimistic-concurrency / cache version token. |

Derived, `@JsonIgnore`, not on the wire: `viaStops` (the `vias` filtered to
`Via.ViaStop`, order preserved), `stops` (their embedded `Stop`s, order preserved,
**not** de-duplicated), `stopMap` (`stopId -> Stop`).

The `version` JSON key appears in the decompiled source as
`@JsonProperty(ThreeDSStrings.VERSION_KEY)`; that constant is
`public static final String VERSION_KEY = "version"` in
`com/cardinalcommerce/shared/cs/utils/ThreeDSStrings.java`. This is a jadx
constant-pool matching artifact — the original literal is `"version"`.

```java
    @JsonCreator
    public RouteService(@JsonProperty("routeServiceId") UUID uuid, @JsonProperty("routeId") UUID uuid2, @JsonProperty("startDate") LocalDate localDate, @JsonProperty("endDate") Optional<LocalDate> optional, @JsonProperty("daysOfWeek") Set<DayOfWeek> set, @JsonProperty("excludedDays") Set<LocalDate> set2, @JsonProperty("extraDays") Set<LocalDate> set3, @JsonProperty("vias") List<Via> list, @JsonProperty("loopOptions") Optional<LoopOptions> optional2, @JsonProperty("legs") Optional<? extends List<RouteLeg>> optional3, @JsonProperty("overflow") Optional<? extends List<RideId>> optional4, @JsonProperty("etaAvailable") boolean z, @JsonProperty(ThreeDSStrings.VERSION_KEY) UUID uuid3) {
```

---

## Route

Route-level metadata. Non-final `class` (subclassed by `FullRoute`); implements
`com.tripshot.common.shared.SharedRoute`.

| JSON property | Java type | Optional? | Meaning |
|---|---|---|---|
| `routeId` | `UUID` | required | Primary key. |
| `regionId` | `UUID` | required | Owning region. |
| `name` | `String` | required | Internal/admin name. |
| `announcedAs` | `Optional<String>` | **optional** | TTS override for announcements. |
| `shortName` | `String` | required | Short label; may be the empty string. `getSynthesizedShortName()` falls back to the upper-cased first character of `name`. |
| `headsign` | `String` | required | Headsign text; may be empty. `getSynthesizedHeadsign()` falls back to `publicName`. |
| `publicName` | `String` | required | Rider-facing name. `getDisplayName()` (`@JsonIgnore`) returns this. |
| `color` | `RgbColor` | required | Route colour. `RgbColor` is `@JsonValue`-serialized to/from a string (`parseUnchecked` / `toJson`). |
| `inbound` | `Optional<Boolean>` | **optional** | Direction flag; absent for non-directional routes. |
| `groupId` | `Optional<UUID>` | **optional** | Route-group membership. |
| `lateNoticeWarnTimeSec` | `int` | required (primitive) | Lateness threshold in **seconds** before a late-notice warning. |
| `description` | `String` | required | Free-text description. |
| `routeUrl` | `Optional<String>` | **optional** | External URL for the route. |
| `routeType` | `RouteType` | required | GTFS-like mode enum. |
| `enableReservationsPrepurchasePasses` | `boolean` | required (primitive) | Reservation/pass-prepurchase flag. Note: the getter `getEnableReservationsPrepurchasePasses()` carries **no** `@JsonProperty`, unlike every other getter on this class. |

`RouteType` (Kotlin enum, `@JsonCreator fromRawValue`, unknown values map to `UNKNOWN`
rather than throwing): `Tram`, `Subway`, `Rail`, `Bus`, `Ferry`, `CableCar`, `Gondola`,
`Funicular`, `Trolleybus`, `Monorail`, `Unknown`.

The `color` JSON key appears as `@JsonProperty(TypedValues.Custom.S_COLOR)`; that
constant is `public static final String S_COLOR = "color"` in
`androidx/constraintlayout/core/motion/utils/TypedValues.java` — again a jadx
constant-matching artifact for the literal `"color"`.

```java
    @JsonCreator
    public Route(@JsonProperty("routeId") UUID uuid, @JsonProperty("regionId") UUID uuid2, @JsonProperty("name") String str, @JsonProperty("announcedAs") Optional<String> optional, @JsonProperty("shortName") String str2, @JsonProperty("headsign") String str3, @JsonProperty("publicName") String str4, @JsonProperty(TypedValues.Custom.S_COLOR) RgbColor rgbColor, @JsonProperty("inbound") Optional<Boolean> optional2, @JsonProperty("groupId") Optional<UUID> optional3, @JsonProperty("lateNoticeWarnTimeSec") int i, @JsonProperty("description") String str5, @JsonProperty("routeUrl") Optional<String> optional4, @JsonProperty("routeType") RouteType routeType, @JsonProperty("enableReservationsPrepurchasePasses") boolean z) {
```

---

## Stop

A physical stop. Embedded inside `Via.ViaStop` when the request carries
`embedStops=true`.

| JSON property (creator) | Java type | Optional? | Meaning |
|---|---|---|---|
| `stopId` | `UUID` | required | Primary key. |
| `regionId` | `UUID` | required | Owning region. |
| `location` | `LatLng` | required | Stop position. JSON keys inside are `lt`/`lg` — see [LatLng](#latlng). |
| `name` | `String` | required | Display name; may be the empty string, in which case `getDisplayName()` returns `address.getAddress()`. |
| `ttsStopName` | `Optional<String>` | **optional** | Text-to-speech override for the stop name. |
| `description` | `String` | required | Free text. |
| `address` | `StopAddress` | required | `StopAddress(address: String, tags: Set<AddressTag>)`. |
| `photoIds` | `List<UUID>` | required (may be empty) | Photo references. |
| `yard` | `boolean` | required (primitive) | Stop is a vehicle yard. Getter `isYard()`. |
| `terminal` | `boolean` | required (primitive) | Stop is a route terminal. Getter `isTerminal()`. |
| `hasParking` | `boolean` | required (primitive) | Parking available. Stored as `parkingAvailable`; getter is `isParkingAvailable()` **without** `@JsonProperty`, so the read key is `hasParking` but the write key differs. |
| `onDemand` | `boolean` | required (primitive) | Stop is usable by on-demand service. Stored as `onDemandStop`; getter `isOnDemandStop()` also lacks `@JsonProperty`. |
| `groupParent` | `Optional<StopGroupType>` | **optional** | If present, this stop is the parent of a stop group. `StopGroupType`: `DistinctNames`, `CoalesceNames`. |
| `parentId` | `Optional<UUID>` | **optional** | Parent stop in a stop group. |
| `geofence` | `Shape` | **required** | The stop's geofence — a `Shape.Circle` (radius in metres, implicitly centred on `location`) or a `Shape.Polygon` (relative vertices). See below. |
| `usage` | `Optional<? extends Iterable<StopUsedBy>>` | **optional** | Defaults to the empty set when absent. `StopUsedBy`: `UsedByFixedRoute`, `UsedByOnDemand`, `Unknown`. The getter returns a plain `ImmutableSet`, not an `Optional`. |
| `airportInfo` | `Optional<StopAirportInfo>` | **optional** | `StopAirportInfo(airportCode: String, terminal: String)`. |

Note the field declaration `private Shape geofence;` is the only non-`final` field on
`Stop`; it is still `checkNotNull`-guarded in the constructor.

`Stop` also carries pure-logic helpers with no wire presence: `sharesGroupWith(Stop)`,
`masks(Stop)` (true when this stop is the other's parent **and**
`groupParent == COALESCE_NAMES`), and `allowedByServiceRestrictions(...)`.

```java
    @JsonCreator
    public Stop(@JsonProperty("stopId") UUID uuid, @JsonProperty("regionId") UUID uuid2, @JsonProperty("location") LatLng latLng, @JsonProperty("name") String str, @JsonProperty("ttsStopName") Optional<String> optional, @JsonProperty("description") String str2, @JsonProperty("address") StopAddress stopAddress, @JsonProperty("photoIds") List<UUID> list, @JsonProperty("yard") boolean z, @JsonProperty("terminal") boolean z2, @JsonProperty("hasParking") boolean z3, @JsonProperty("onDemand") boolean z4, @JsonProperty("groupParent") Optional<StopGroupType> optional2, @JsonProperty("parentId") Optional<UUID> optional3, @JsonProperty("geofence") Shape shape, @JsonProperty("usage") Optional<? extends Iterable<StopUsedBy>> optional4, @JsonProperty("airportInfo") Optional<StopAirportInfo> optional5) {
```

---

## Via

Polymorphic element of `RouteService.vias`. `abstract class Via implements Serializable`.

Jackson type handling — verbatim class-level annotations:

```java
@JsonSubTypes({@JsonSubTypes.Type(ViaWaypoint.class), @JsonSubTypes.Type(ViaStop.class)})
@JsonTypeInfo(include = JsonTypeInfo.As.WRAPPER_OBJECT, use = JsonTypeInfo.Id.NAME)
public abstract class Via implements Serializable {
```

`As.WRAPPER_OBJECT` + `Id.NAME` means each element of `vias` is a **single-key object**
whose key is the subtype's `@JsonTypeName` and whose value is the subtype's own object:

```
{"ViaStop":     {"stop": {...}, "visitType": "DropOffOrPickup"}}
{"ViaWaypoint": {"waypointLocation": {"lt": 37.1, "lg": -122.3}}}
```

Dispatch in code goes through `Via.Visitor` (`fromStop(ViaStop)` /
`fromWaypoint(ViaWaypoint)`) or `instanceof Via.ViaStop` checks.

### Via.ViaStop — `@JsonTypeName("ViaStop")`

| JSON property | Java type | Optional? | Meaning |
|---|---|---|---|
| `stop` | `Stop` | required | The embedded stop (present because the endpoints pin `embedStops=true`). |
| `visitType` | `VisitType` | required | Whether riders may board, alight, or both here. |

```java
        @JsonCreator
        public ViaStop(@JsonProperty("stop") Stop stop, @JsonProperty("visitType") VisitType visitType) {
```

Note `ViaStop.hashCode()` hashes only `stop` while `equals()` compares `stop` **and**
`visitType` — an inconsistency in the decompiled source, harmless for read-only use.

### Via.ViaWaypoint — `@JsonTypeName("ViaWaypoint")`

| JSON property | Java type | Optional? | Meaning |
|---|---|---|---|
| `waypointLocation` | `LatLng` | required | A shaping point with no rider activity. |

```java
        @JsonCreator
        public ViaWaypoint(@JsonProperty("waypointLocation") LatLng latLng) {
```

There is **no** radius, dwell, or arrival field on either `Via` variant.

### Related: NavVia

`NavVia` (used by `RouteLeg.startPoint` / `endPoint`, only populated with
`withNavigation=true`) is a separate hierarchy with the same
`WRAPPER_OBJECT` + `Id.NAME` scheme and three variants:
`NavViaStop{stopId: UUID}`, `NavViaWaypoint{waypointLocation: LatLng}`,
`NavViaStartPoint{startPointLocation: LatLng}`. It references stops by id only — it does
not embed `Stop` and carries no radius either.

---

## ScheduledRide

One scheduled trip of a `RouteService`. `final class`.

| JSON property (creator) | Java type | Optional? | Meaning |
|---|---|---|---|
| `scheduledRideId` | `UUID` | required | Primary key. `equals`/`hashCode` use this alone. |
| `routeServiceId` | `UUID` | required | FK to the owning `RouteService`. |
| `stops` | `List<Optional<ScheduledStop>>` | required | Per-stop schedule entries. **Entries may be null/absent.** The getter is named `getScheduledStops()` and annotated bare `@JsonProperty`, so the serialized key is `scheduledStops` while the read key is `stops`. |

### `stops` is index-aligned with the route service's ViaStops, and entries can be absent

The list element type is `Optional<ScheduledStop>` — a JSON `null` at position *i* means
"this ride does not serve the *i*-th stop of the pattern". This is positional, not
sparse: index *i* of `stops` corresponds to index *i* of
`RouteService.getViaStops()` (the `vias` filtered to `ViaStop`, order preserved).
Evidence, from `com/tripshot/android/rider/models/ExactTimetable.java`:

```java
            while (i3 < routeService.getViaStops().size()) {
                Optional<ScheduledStop> optional = denormalizedScheduledRide.getScheduledStops().get(i3);
                Stop stop = routeService.getViaStops().get(i3).getStop();
```

Consumers must therefore skip absent entries. `ScheduledRide` itself does so:

- `getStartTime()` — first **present** entry's `arrivalTime`; throws
  `IllegalStateException("scheduled ride with no stop times")` if the whole list is absent.
- `getEndTime()` — same, iterating `reverse()`.
- The `RouteServiceBundle` sort comparator only compares positions where **both** rides
  have a present entry.

```java
    @JsonCreator
    public ScheduledRide(@JsonProperty("scheduledRideId") UUID uuid, @JsonProperty("routeServiceId") UUID uuid2, @JsonProperty("stops") List<Optional<ScheduledStop>> list) {
```

---

## ScheduledStop

**This is the per-stop element type of `ScheduledRide.stops`** (as
`Optional<ScheduledStop>`). File: `com/tripshot/common/models/ScheduledStop.java`.
Do not confuse it with `ScheduledStopKey`, `StopArrivalTime`, or the rider-side
wrapper `DenormalizedScheduledStop` (an app view model, not a wire type).

| JSON property (creator) | Java type | Optional? | Meaning |
|---|---|---|---|
| `stop` | `UUID` | required | The stop id. Field and getter are `stopId`; the getter is explicitly `@JsonProperty("stop")`, so the wire key is `stop` in **both** directions. |
| `arrivalTime` | `TimeOfDay` | required | Scheduled arrival, wire format `"HH:MM:SS"`, hour range `0..47`. |
| `waitTimeSec` | `int` | required (primitive) | Scheduled dwell at the stop, in **seconds**. Constructor enforces `Preconditions.checkArgument(waitTimeSec >= 0)`. |
| `timepoint` | `boolean` | required (primitive) | Whether this stop is a published timepoint. Getter `isTimepoint()`. |

### arrivalTime + waitTimeSec

`arrivalTime` is the **scheduled arrival instant** at the stop (as a time-of-day on the
service date; combine with the service `LocalDate` and region time zone via
`TimeOfDay.onDate(localDate, timeZone)` to get an absolute instant).

`waitTimeSec` is the scheduled dwell in seconds, constrained non-negative. The
**scheduled departure instant is `arrivalTime + waitTimeSec`**; a stop with
`waitTimeSec == 0` departs at its arrival instant.

Evidence caveat — state this honestly: no decompiled client code performs that addition.
`getWaitTimeSec()` has exactly one call site outside `ScheduledStop`'s own
`hashCode`/`equals`, and it merely copies the value through when shifting a loop ride
forward by `roundTripTimeSec` (`ExactTimetable.java:191`). The
arrival + dwell = departure reading follows from the field names, the `>= 0` guard, and
the fact that `arrivalTime` is the only time on the record; it is not directly computed
anywhere in this APK.

```java
    @JsonCreator
    public ScheduledStop(@JsonProperty("stop") UUID uuid, @JsonProperty("arrivalTime") TimeOfDay timeOfDay, @JsonProperty("waitTimeSec") int i, @JsonProperty("timepoint") boolean z) {
```

---

## Shape (the type of `Stop.geofence`)

There is no class named `Geofence`. `Stop.geofence` is typed
`com.tripshot.common.models.Shape` — a polymorphic, **relative** (centre-less) shape.

```java
@JsonSubTypes({@JsonSubTypes.Type(Circle.class), @JsonSubTypes.Type(Polygon.class)})
@JsonTypeInfo(include = JsonTypeInfo.As.WRAPPER_OBJECT, use = JsonTypeInfo.Id.NAME)
public abstract class Shape implements Serializable {
```

Same `WRAPPER_OBJECT` + `Id.NAME` scheme as `Via`. Both variants use `@JsonValue`, so the
wrapped payload is a **bare scalar/array**, not an object:

| Variant | `@JsonTypeName` | Payload | Java type | Meaning |
|---|---|---|---|---|
| `Shape.Circle` | `"Circle"` | bare number, e.g. `{"Circle": 60.0}` | `double radiusMeters` | Radius in **metres**. Implicitly centred on the owner's location (`Stop.location` for a stop geofence). |
| `Shape.Polygon` | `"Polygon"` (from `KmlPolygon.GEOMETRY_TYPE`) | bare array of `LatLng` | `ImmutableList<LatLng> vertices` | Polygon vertices. |

`Circle` exposes two `@JsonCreator` factories (`double` and `int` overloads), so both
`{"Circle": 60}` and `{"Circle": 60.0}` parse. `Polygon` uses a static
`@JsonCreator fromVertices(List<LatLng>)`.

```java
    @JsonTypeName("Circle")
    public static final class Circle extends Shape {
        private static final long serialVersionUID = 1;
        private final double radiusMeters;

        public Circle(double d) {
            this.radiusMeters = d;
        }

        @JsonCreator
        public static Circle fromRadiusMeters(double d) {
            return new Circle(d);
        }

        @JsonCreator
        public static Circle fromRadiusMeters(int i) {
            return new Circle(i);
        }

        @JsonValue
        public double getRadiusMeters() {
            return this.radiusMeters;
        }
```

```java
    @JsonTypeName(KmlPolygon.GEOMETRY_TYPE)
    public static final class Polygon extends Shape {
        private static final long serialVersionUID = 1;
        private final ImmutableList<LatLng> vertices;

        public Polygon(List<LatLng> list) {
            this.vertices = ImmutableList.copyOf((Collection) list);
        }

        @JsonCreator
        public static Polygon fromVertices(List<LatLng> list) {
            return new Polygon(list);
        }

        @JsonValue
        public ImmutableList<LatLng> getVertices() {
            return this.vertices;
        }
```

Concrete instance from the app's own test service, confirming metres and the scalar
payload (`com/tripshot/android/services/TestTripshotService.java:1792`): a `Stop` is
constructed with `new Shape.Circle(60.0d)` as its geofence.

### AbsoluteShape — the absolutely-positioned sibling

`AbsoluteShape` is a distinct hierarchy with the same wrapper scheme but a self-contained
centre, plus a `contains(LatLng)` method. It is used for `OnDemandZone.geofence`, **not**
for `Stop.geofence`.

| Variant | `@JsonTypeName` | Fields | Notes |
|---|---|---|---|
| `AbsoluteShape.Circle` | `"Circle"` | `center: LatLng` (key `center`), `radiusMeters: double` (**wire key `radius`**) | `contains()` is `SphericalUtil.computeDistanceBetween(center, p) < radiusMeters` — metres, strict `<`. |
| `AbsoluteShape.Polygon` | `"Polygon"` | `vertices: List<LatLng>` via `@JsonValue` | `contains()` is `PolyUtil.containsLocation(p, vertices, true)` (geodesic). |

```java
        @JsonCreator
        public Circle(@JsonProperty("center") LatLng latLng, @JsonProperty("radius") double d) {
```

### Geo radius for "at stop" determination

Putting the above together, the geo radius available on the schedule side is:

- **Source:** `Stop.geofence`, type `Shape`, **required** (never null).
- **Circle case:** `radiusMeters`, a `double` in **metres**, delivered as a bare number
  under the `"Circle"` wrapper key. It has no centre of its own — the centre is the
  stop's own `location` (`Stop.location`, a `LatLng`). The parallel
  `AbsoluteShape.Circle.contains()` implementation shows the intended predicate:
  great-circle distance from the centre strictly less than `radiusMeters`.
- **Polygon case:** `vertices`, a list of `LatLng`. Note `Shape` (unlike
  `AbsoluteShape`) provides **no** `contains()` method, so a client must implement
  containment itself; for `Shape.Polygon` the vertices' interpretation relative to the
  stop is not established by any code in this APK — flagging that as **ambiguous**.
- **There is no `arrivalRadiusMeters` field** anywhere in the APK, on `Via`/`ViaStop` or
  otherwise. If an "arrival radius" concept exists server-side, it is not exposed under
  that name to this client.

---

## VisitType

`enum VisitType` — `@JsonValue` on `getName()`, `@JsonCreator fromName(String)` with
case-insensitive matching. Unknown values **throw** `IllegalArgumentException`.

| Java constant | Wire value | Meaning |
|---|---|---|
| `DROPOFF_OR_PICKUP` | `"DropOffOrPickup"` | Riders may board and alight. |
| `DROPOFF_ONLY` | `"DropOffOnly"` | Alight only. |
| `PICKUP_ONLY` | `"PickupOnly"` | Board only. |

```java
public enum VisitType {
    DROPOFF_OR_PICKUP("DropOffOrPickup"),
    DROPOFF_ONLY("DropOffOnly"),
    PICKUP_ONLY("PickupOnly");
```

```java
    @JsonCreator
    public static VisitType fromName(String str) {
```

---

## StopByRequestStatus

Kotlin enum (`StopByRequestStatus.kt`). `@JsonValue` is on the `rawValue` **field**;
`@JsonCreator fromRawValue(String)` matches `rawValue` exactly (`Intrinsics.areEqual`,
case-**sensitive**) and falls back to `UNKNOWN` instead of throwing.

| Java constant | Wire value | Meaning |
|---|---|---|
| `ALWAYS_VISIT` | `"av"` | The stop is always served. |
| `VISIT_REQUESTED_TO_DRIVER` | `"vd"` | A stop-by-request has been made and relayed to the driver. |
| `VISIT_NOT_REQUESTED` | `"vn"` | Request stop, not requested for this trip. |
| `UNKNOWN` | `"unknown"` (from `BinData.UNKNOWN`) | Unrecognized / fallback value. |

```java
    @JvmStatic
    @JsonCreator
    public static final StopByRequestStatus fromRawValue(String str) {
        return INSTANCE.fromRawValue(str);
    }
```

Scope note: this enum is **not** referenced by any schedule-side type. Its only
consumers in the APK are `V2StopStatus`, `V2Ride`, and `FullV2StopStatus` — the live
side, documented elsewhere. The `"unknown"` wire value comes from
`com.braintreepayments.api.BinData.UNKNOWN`, another jadx constant-matching artifact.

---

## LatLng

The location type used by `Stop.location`, `Via.ViaWaypoint.waypointLocation`, and
`Shape.Polygon.vertices`. Package is `com.tripshot.common.utils`, **not** `...models`,
and it is not `com.google.android.gms.maps.model.LatLng`.

**The JSON keys are `lt` and `lg`, not `lat`/`lng`** — on both read and write (the
getters carry explicit `@JsonProperty("lt")` / `@JsonProperty("lg")`).

| JSON property | Java type | Optional? | Meaning |
|---|---|---|---|
| `lt` | `double` | required (primitive) | Latitude. Validated `-90.0 <= lt <= 90.0`, else `IllegalArgumentException`. |
| `lg` | `double` | required (primitive) | Longitude. Validated `-180.0 <= lg <= 180.0`. |

Both are also exposed as public final-style fields (`public final double latitude;`,
`public final double longitude;`). `toString()` formats as `"%.6f,%.6f"`.

```java
    @JsonCreator
    public LatLng(@JsonProperty("lt") double d, @JsonProperty("lg") double d2) {
```

---

## Nullability summary

Every optional (nullable) wire field on the documented schedule-side types:

| Class | Optional fields |
|---|---|
| `RouteServiceBundle` | none (`scheduledRides` may be an empty list, but the key is not `Optional`) |
| `RouteService` | `endDate`, `loopOptions`, `legs`, `overflow` |
| `Route` | `announcedAs`, `inbound`, `groupId`, `routeUrl` |
| `Stop` | `ttsStopName`, `groupParent`, `parentId`, `usage` (defaults to empty set), `airportInfo` |
| `Via.ViaStop` | none |
| `Via.ViaWaypoint` | none |
| `ScheduledRide` | none — but **`stops` list entries are individually nullable** (`Optional<ScheduledStop>`) |
| `ScheduledStop` | none |
| `Shape.Circle` / `Shape.Polygon` | none |
| `LatLng` | none |

Notably **not** optional: `Stop.geofence`, `Stop.location`, `Stop.address`,
`ScheduledStop.arrivalTime`, `ScheduledStop.waitTimeSec`, `Via.ViaStop.visitType`.
