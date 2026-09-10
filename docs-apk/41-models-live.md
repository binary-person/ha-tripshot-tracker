---
id: api.models.live
title: Live status models
kind: model
apk_refs:
  - path: com/tripshot/common/models/V2LiveStatus.java
    symbol: V2LiveStatus
    sha256: 00dede6e3953f7f3761448cbd4ab026cd9b4124edde26c8cb22ac9dff9f8ad53
  - path: com/tripshot/common/models/FullV2LiveStatus.java
    symbol: FullV2LiveStatus
    sha256: 2647af1aff07bda73c985f2542ff5aa244990d06b09bed2cf076f87908c36000
  - path: com/tripshot/common/models/LiveStatusFilter.java
    symbol: LiveStatusFilter
    sha256: 309156b051a5e7e9925acd7690991d2306d034aa8abbecf64625f1f1965f59d1
  - path: com/tripshot/common/models/V2Ride.java
    symbol: V2Ride
    sha256: 92defdae115fb62bcacd173c51084411cff6e8a5e8e411950a244e760ea0f0fa
  - path: com/tripshot/common/models/FullV2Ride.java
    symbol: FullV2Ride
    sha256: bc7d3f8bd39d7197164ed60e469e7c35f567fe56592e95d65778fb22f9934793
  - path: com/tripshot/common/models/V2StopStatus.java
    symbol: V2StopStatus
    sha256: 808fde8d14a61cb792e18bf57e17ba673c0cc515bf508f4d438cfad473db2a2d
  - path: com/tripshot/common/models/FullV2StopStatus.java
    symbol: FullV2StopStatus
    sha256: 6f9319d8e98cfdcbb573914ea2d888f5a43d6f42ca7cac47df0155ad7f473758
  - path: com/tripshot/common/models/Vehicle.java
    symbol: Vehicle
    sha256: dd347496f5aff8c46fb56495151049e6be80bd2997a9da0a89908846d4b39ce6
  - path: com/tripshot/common/models/VehicleStatus.java
    symbol: VehicleStatus
    sha256: 5a69647c72c9b152dd862a814fa9ed92f0fa3c22d7077dbb9325d683a6615e19
  - path: com/tripshot/common/models/FullVehicleStatus.java
    symbol: FullVehicleStatus
    sha256: 95fa3531931e82601ce81c8f100b7b3a62a3fe317291e00583645b330ae3d8a1
  - path: com/tripshot/common/models/RideState.java
    symbol: RideState
    sha256: 2a00716807e27620a00c8611bc36937c5aca36777769547a0c0e62b4c2d0945d
  - path: com/tripshot/common/models/RideId.java
    symbol: RideId
    sha256: 2ea094c3100ed8aeeb1432ca154ebef062a1f84f8fd4dd8a600734daca5abaa1
  - path: com/tripshot/common/models/VisitType.java
    symbol: VisitType
    sha256: 3ce2653ca0cd1deaf62b3c5e1a72829a4aee1dc8dcca6495a9d5aaee283e317c
  - path: com/tripshot/common/models/StopByRequestStatus.java
    symbol: StopByRequestStatus
    sha256: adc6b15cdb29ab1b75132535bce57fec344cb69bc4bfb53a7f67dd528b0cf1fe
  - path: com/tripshot/common/models/RideDirection.java
    symbol: RideDirection
    sha256: 2df7770699862ff449bf525ed438c5225a96d47d543f8bfdc9af3981863db966
  - path: com/tripshot/common/models/VehicleType.java
    symbol: VehicleType
    sha256: fde994d64a03ca297c28b7c98b45e8698ea97d44cafa2fd4780ee8e33673519c
  - path: com/tripshot/common/models/StopStatusKey.java
    symbol: StopStatusKey
    sha256: 836299997ec141584c92a1d11684b73dff13b33d42c4de600c6e962ba35c34dc
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getV2LiveStatusPublic
    sha256: 693652a59e7cf575070693a45a7000c36de8982f9cbf1119338fbe5dc23eba26
depends_on: [api.transport]
---

# Live status models

Reverse-engineered from TripShot Rider v127 (jadx output under `nocommit/jadx/sources/`).
This page covers the **live / real-time** side only: the `liveStatus` request and response
graph. Static schedule types (`Route`, `Stop`, `Via`, `ScheduledRide`, `RouteServiceBundle`,
`Geofence`) are documented elsewhere and are only referenced by name here.

Every field table below is derived from the `@JsonCreator` constructor of the class, which is
the authoritative deserialization contract. Guava `Optional<T>` in a creator parameter means
the JSON member may be absent or `null`.

## How to read the tables

| Column | Meaning |
| --- | --- |
| JSON property | Literal `@JsonProperty` value on the creator parameter |
| Java type | Type as it appears in the decompiled creator |
| Opt? | `yes` = `Optional<T>` creator parameter (absent/null accepted); `no` = plain parameter |
| Notes | Null-check / default behaviour visible in the constructor body |

A parameter that is *not* `Optional<T>` but is passed through `Preconditions.checkNotNull(...)`
will throw if the wire omits it. A non-`Optional` parameter with **no** null check (for example
`V2StopStatus.*.scheduledDepartureTime`) is stored as-is and may end up `null` at runtime.

## Transport recap

Two endpoints deserialize into this graph (`com/tripshot/android/services/TripshotService.java`):

```java
    @POST("/v2/liveStatus")
    Observable<FullV2LiveStatus> getV2LiveStatus(@Query("regionId") UUID uuid, @Body LiveStatusFilter liveStatusFilter);

    @POST("/v1/p/liveStatus")
    Observable<V2LiveStatus> getV2LiveStatusPublic(@Query("regionId") UUID uuid, @Body LiveStatusFilter liveStatusFilter);
```

`/v1/p/liveStatus` (public/anonymous) yields the base types documented here.
`/v2/liveStatus` (authenticated) yields the `Full*` subclasses, which add a few extra fields
(see "Authenticated `Full*` variants" below).

The Jackson mapper is configured in `com/tripshot/android/rider/RiderModule.java`:

```java
    public ObjectMapper provideObjectMapper() {
        ObjectMapper objectMapper = new ObjectMapper();
        objectMapper.registerModule(new KotlinModule.Builder().nullIsSameAsDefault(true).build());
        objectMapper.registerModule(new TripshotJacksonModule());
        objectMapper.registerModule(new GuavaModule());
        objectMapper.setVisibility(objectMapper.getVisibilityChecker().with(JsonAutoDetect.Visibility.NONE));
        SimpleDateFormat simpleDateFormat = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'");
        simpleDateFormat.setTimeZone(TimeZone.getTimeZone("UTC"));
        objectMapper.setDateFormat(simpleDateFormat);
        objectMapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
        objectMapper.configure(SerializationFeature.FAIL_ON_EMPTY_BEANS, false);
        return objectMapper;
    }
```

Two consequences that matter for everything below:

- `FAIL_ON_UNKNOWN_PROPERTIES = false` — the server may send fields the APK models do not
  declare, and the client silently drops them. Several such fields exist (see
  "Wire fields with no model counterpart").
- All `java.util.Date` fields are parsed with the fixed pattern
  `yyyy-MM-dd'T'HH:mm:ss.SSS'Z'` in UTC (exactly three fractional digits).

## V2LiveStatus — response body

Source: `com/tripshot/common/models/V2LiveStatus.java`.

The class models **three** top-level members only.

| JSON property | Java type | Opt? | Notes |
| --- | --- | --- | --- |
| `rides` | `List<? extends V2Ride>` | no | copied into `ImmutableList`; also indexed into `rideMap` keyed by `V2Ride.getRideId()` |
| `vehicleStatuses` | `List<? extends VehicleStatus>` | no | copied into `ImmutableList` |
| `timestamp` | `Date` | no | `Preconditions.checkNotNull`; server-side generation time of the snapshot |

`rideMap` (`ImmutableMap<RideId, ? extends V2Ride>`) is derived client-side via
`Maps.uniqueIndex`, not a wire field. Because `uniqueIndex` throws on duplicate keys, the server
is expected never to repeat a `rideId` in one response.

```java
    @JsonCreator
    public V2LiveStatus(@JsonProperty("rides") List<? extends V2Ride> list, @JsonProperty("vehicleStatuses") List<? extends VehicleStatus> list2, @JsonProperty("timestamp") Date date) {
        this.rides = ImmutableList.copyOf((Collection) list);
        this.vehicleStatuses = ImmutableList.copyOf((Collection) list2);
        this.rideMap = Maps.uniqueIndex(list, new Function<V2Ride, RideId>() { // from class: com.tripshot.common.models.V2LiveStatus.1
            @Override // com.google.common.base.Function
            public RideId apply(V2Ride v2Ride) {
                return v2Ride.getRideId();
            }
        });
        this.timestamp = (Date) Preconditions.checkNotNull(date);
    }
```

### Confirmation against the observed wire shape

The five top-level members observed on the wire are `timestamp`, `date`, `vehicles`, `rides`,
`vehicleStatuses`. Checked against the class:

| Wire member | In `V2LiveStatus`? | Evidence |
| --- | --- | --- |
| `timestamp` | yes | creator parameter `@JsonProperty("timestamp") Date` |
| `rides` | yes | creator parameter `@JsonProperty("rides")` |
| `vehicleStatuses` | yes | creator parameter `@JsonProperty("vehicleStatuses")` |
| `date` | **no** | no such creator parameter or field; dropped by `FAIL_ON_UNKNOWN_PROPERTIES=false` |
| `vehicles` | **no** | no such creator parameter or field; dropped |

The rider app obtains vehicle records from a *separate* endpoint and joins them to the live
status client-side. `com/tripshot/android/rider/models/V2LiveStatusWithVehicles.java` is a
client-only holder:

```java
    public V2LiveStatusWithVehicles(V2LiveStatus v2LiveStatus, Iterable<? extends Vehicle> iterable) {
```

The vehicle list comes from `@GET("/v1/p/vehicle")`
(`Observable<List<Vehicle>> getVehiclesPublic(@Query("regionId") UUID uuid)`) or
`@GET("/v1/vehicle")`. So `vehicles` being inlined in the `liveStatus` response is a server
capability the v127 client does not use.

### FullV2LiveStatus (authenticated `/v2/liveStatus`)

Same three properties, narrowed element types:

```java
    @JsonCreator
    public FullV2LiveStatus(@JsonProperty("rides") List<FullV2Ride> list, @JsonProperty("vehicleStatuses") List<FullVehicleStatus> list2, @JsonProperty("timestamp") Date date) {
        super(list, list2, date);
    }
```

## LiveStatusFilter — request body

Source: `com/tripshot/common/models/LiveStatusFilter.java`.

This class has **no** `@JsonCreator`; it is serialize-only from the client's point of view. The
two `@JsonProperty` getters define the wire shape (implicit names `rideIds` / `vehicleIds`).

| JSON property | Java type | Opt? | Notes |
| --- | --- | --- | --- |
| `rideIds` | `ImmutableSet<RideId>` | n/a (write-only) | each element serialized via `RideId.toJson()` (see `RideId`) |
| `vehicleIds` | `ImmutableSet<UUID>` | n/a (write-only) | plain UUID strings |

```java
public final class LiveStatusFilter {
    private final ImmutableSet<RideId> rideIds;
    private final ImmutableSet<UUID> vehicleIds;

    public LiveStatusFilter(Collection<RideId> collection, Collection<UUID> collection2) {
        this.rideIds = ImmutableSet.copyOf((Collection) collection);
        this.vehicleIds = ImmutableSet.copyOf((Collection) collection2);
    }

    @JsonProperty
    public ImmutableSet<RideId> getRideIds() {
        return this.rideIds;
    }

    @JsonProperty
    public ImmutableSet<UUID> getVehicleIds() {
        return this.vehicleIds;
    }
}
```

Both sets are non-null but may be empty; the app does send an empty `vehicleIds`
(`new LiveStatusFilter(immutableSetKeySet, ImmutableSet.of())` in
`com/tripshot/android/rider/models/TripPlannerViewModel.java`). The code shows no other request
members — there is no "all rides" flag in this class.

## V2Ride — elements of `rides`

Source: `com/tripshot/common/models/V2Ride.java`.

| JSON property | Java type | Opt? | Notes |
| --- | --- | --- | --- |
| `rideId` | `RideId` | no | `checkNotNull`; composite string, see `RideId` |
| `regionId` | `UUID` | no | `checkNotNull` |
| `routeId` | `UUID` | no | `checkNotNull` |
| `routeServiceId` | `UUID` | no | `checkNotNull` |
| `routeName` | `String` | no | `checkNotNull` |
| `color` | `RgbColor` | no | `checkNotNull`; annotation is `@JsonProperty(TypedValues.Custom.S_COLOR)` and `TypedValues.Custom.S_COLOR == "color"` |
| `vehicleName` | `Optional<String>` | yes | stored via `orNull()` |
| `scheduledStart` | `Date` | no | `checkNotNull` |
| `driverId` | `Optional<UUID>` | yes | |
| `vehicleId` | `Optional<UUID>` | yes | join key into `vehicleStatuses` / `/v1/p/vehicle` |
| `state` | `RideState` | no | `checkNotNull`; polymorphic wrapper object |
| `rideHistory` | `List<RideEvent>` | no | `ImmutableList.copyOf` |
| `stopStatus` | `List<? extends V2StopStatus>` | no | the polymorphic per-stop list; also indexed into `stopStatusMap` by `StopStatusKey` |
| `overflow` | `Optional<? extends List<RideId>>` | yes | list of other rides absorbing overflow riders |
| `vias` | `List<Via>` | no | schedule-side type; `Via.ViaStop` entries are extracted into `viaStops` and `stopMap` |
| `loopOptions` | `Optional<RideLoopOptions>` | yes | `isExactTimes()` gates `isLastStop(...)` |
| `deviceMarkedDown` | `boolean` | no | primitive |
| `liveDataAvailable` | `boolean` | no | primitive; see dedicated section below |
| `lateBySec` | `Optional<Integer>` | yes | see dedicated section below |
| `lastDeviceStatus` | `Optional<? extends DeviceStatus>` | yes | |
| `navigationId` | `UUID` | no | `checkNotNull` |
| `userNavigationId` | `UUID` | no | `checkNotNull` |
| `effectiveNavigationId` | `Optional<UUID>` | yes | |
| `distanceOffRouteMeters` | `double` | no | primitive; note the getter name asymmetry below |
| `riderCount` | `int` | no | primitive |
| `userRiderCount` | `Optional<Integer>` | yes | **defaults to `riderCount`** when absent: `optional9.or(Integer.valueOf(i)).intValue()` |
| `bikeCount` | `int` | no | primitive |
| `direction` | `RideDirection` | no | `checkNotNull` |
| `payInfo` | `Optional<PayInfo>` | yes | `com.tripshot.common.payments.PayInfo` |
| `obsolete` | `boolean` | no | primitive |

Derived, `@JsonIgnore`, not on the wire: `stopStatusMap`, `viaStops`, `stopMap`, `getAcceptTime()`,
`getCurrentStopStatus()`, `getNextStopStatus()`, `isLastStop(...)`.

```java
    @JsonCreator
    public V2Ride(@JsonProperty("rideId") RideId rideId, @JsonProperty("regionId") UUID uuid, @JsonProperty("routeId") UUID uuid2, @JsonProperty("routeServiceId") UUID uuid3, @JsonProperty("routeName") String str, @JsonProperty(TypedValues.Custom.S_COLOR) RgbColor rgbColor, @JsonProperty("vehicleName") Optional<String> optional, @JsonProperty("scheduledStart") Date date, @JsonProperty("driverId") Optional<UUID> optional2, @JsonProperty("vehicleId") Optional<UUID> optional3, @JsonProperty("state") RideState rideState, @JsonProperty("rideHistory") List<RideEvent> list, @JsonProperty("stopStatus") List<? extends V2StopStatus> list2, @JsonProperty("overflow") Optional<? extends List<RideId>> optional4, @JsonProperty("vias") List<Via> list3, @JsonProperty("loopOptions") Optional<RideLoopOptions> optional5, @JsonProperty("deviceMarkedDown") boolean z, @JsonProperty("liveDataAvailable") boolean z2, @JsonProperty("lateBySec") Optional<Integer> optional6, @JsonProperty("lastDeviceStatus") Optional<? extends DeviceStatus> optional7, @JsonProperty("navigationId") UUID uuid4, @JsonProperty("userNavigationId") UUID uuid5, @JsonProperty("effectiveNavigationId") Optional<UUID> optional8, @JsonProperty("distanceOffRouteMeters") double d, @JsonProperty("riderCount") int i, @JsonProperty("userRiderCount") Optional<Integer> optional9, @JsonProperty("bikeCount") int i2, @JsonProperty("direction") RideDirection rideDirection, @JsonProperty("payInfo") Optional<PayInfo> optional10, @JsonProperty("obsolete") boolean z3) {
```

Serialization asymmetry worth flagging: the read side is `@JsonProperty("distanceOffRouteMeters")`
(two `f`s) but the getter is

```java
    @JsonProperty
    public double getDistanceOfRouteMeters() {
        return this.distanceOffRouteMeters;
    }
```

which implies the *serialized* name is `distanceOfRouteMeters` (one `f`). Only the creator name
matters when parsing server responses.

### `V2Ride.lateBySec` — what the code does and does not establish

```java
    @JsonProperty("lateBySec") Optional<Integer> optional6, ...
        this.lateBySec = optional6.orNull();
```

```java
    @JsonProperty
    public Optional<Integer> getLateBySec() {
        return Optional.fromNullable(this.lateBySec);
    }
```

What the code establishes:

- The field is optional/nullable: `Optional<Integer>` in the creator, stored via `orNull()`, and
  handed back as `Optional`. Absent and `null` are indistinguishable to the client.
- It is an integer count of **seconds**, by name only. Nothing in the decompiled code converts,
  clamps, or sign-checks it.

What the code does **not** establish, and must not be assumed:

- **Sign convention.** No decompiled code compares `lateBySec` to zero, negates it, or formats it,
  so there is no in-APK evidence of whether negative values mean "early" or whether the server
  only ever emits values `>= 0`.
- **Which reference point it is measured against** (next stop, current stop, whole-ride
  schedule adherence). The class carries no companion field naming the reference.
- **When it is present.** There is no code path that requires it, defaults it, or asserts it.

Most important: **`getLateBySec()` is never read anywhere in the app.** A repo-wide grep over
`nocommit/jadx/sources/com/tripshot/` finds `getLateBySec()` only inside `V2Ride.hashCode()`,
`V2Ride.equals()`, `FullV2Ride.hashCode()` and `FullV2Ride.equals()`. No view, view-model or
formatter consumes it. The lateness the rider UI displays is computed client-side instead, in
`com/tripshot/android/rider/models/StopTimeForDisplay.java`:

```java
            } else if (!(optional.get().getState() instanceof RideState.Active) || expectedArrivalTime == null || expectedArrivalTime.getTime() - dateOnDate.getTime() <= PeriodicWorkRequest.MIN_PERIODIC_FLEX_MILLIS) {
```

where `dateOnDate` is the stop's scheduled time materialized on the ride's local date and
`androidx.work.PeriodicWorkRequest.MIN_PERIODIC_FLEX_MILLIS == 300000`. So the app's own "late"
badge means: ride state is `Active` **and** `expectedArrivalTime` exceeds the scheduled time by
more than 5 minutes. A consumer wanting behaviour identical to the app should replicate that
computation from `V2StopStatus` rather than trust `lateBySec`.

### `V2Ride.liveDataAvailable`

```java
    @JsonProperty("liveDataAvailable") boolean z2, ...
        this.liveDataAvailable = z2;
```

```java
    @JsonProperty
    public boolean isLiveDataAvailable() {
        return this.liveDataAvailable;
    }
```

What the code establishes:

- It is a required primitive `boolean` (not `Optional`). Jackson will default a missing member to
  `false`, so "absent" and "explicitly false" are indistinguishable.
- It gates UI that presents realtime information. Concrete uses:
  - `com/tripshot/android/rider/views/OnRouteScheduledStepView.java` shows
    `"Live data is currently not available for this ride."` when `!v2Ride.isLiveDataAvailable()`.
  - `com/tripshot/common/plan/CommuteOption.java#isAnyLiveDataUnavailable(...)` returns true if any
    ride on the itinerary has it false.
  - `com/tripshot/android/rider/views/StopOnRideStopView.java` only renders an estimate when the
    stop is `V2StopStatus.Awaiting` **and** `isLiveDataAvailable()` **and** the ride state is
    `Accepted` or `Active`.
  - `StopTimeForDisplay.create(...)` copies it straight through into the display model.

What the code does **not** establish:

- **Why** it is false. The class carries a separate `deviceMarkedDown` boolean and a separate
  `lastDeviceStatus`, and there is no code deriving one from the other, so `liveDataAvailable`
  cannot be read as "the onboard device is down".
- Any relation to `VehicleStatus.liveDataAvailable`. They are distinct fields on distinct objects;
  no decompiled code ORs, ANDs or cross-checks them. `SharedRouteDetailViewModel` and
  `StopOnRideCardFragment` check the *vehicle status* flag; `OnRouteScheduledStepView` and
  `CommuteOption` check the *ride* flag.
- Whether `expectedArrivalTime` values are meaningless when it is false. The app keeps parsing and
  storing them either way; it merely suppresses some UI.

Safe reading: `liveDataAvailable == false` means "the app should not present this ride's realtime
estimates as live"; nothing stronger is provable from the APK.

### FullV2Ride (authenticated `/v2/liveStatus`)

Adds four properties on top of `V2Ride` and narrows `stopStatus` to `List<FullV2StopStatus>` and
`lastDeviceStatus` to `Optional<FullDeviceStatus>`:

| JSON property | Java type | Opt? |
| --- | --- | --- |
| `driverName` | `Optional<String>` | yes |
| `boardingCode` | `Optional<String>` | yes |
| `wait` | `Optional<Wait>` | yes |
| `avaConfig` | `Optional<AvaConfig>` | yes |

```java
    @JsonCreator
    public FullV2Ride(@JsonProperty("rideId") RideId rideId, @JsonProperty("regionId") UUID uuid, @JsonProperty("routeId") UUID uuid2, @JsonProperty("routeServiceId") UUID uuid3, @JsonProperty("routeName") String str, @JsonProperty(TypedValues.Custom.S_COLOR) RgbColor rgbColor, @JsonProperty("driverName") Optional<String> optional, @JsonProperty("vehicleName") Optional<String> optional2, @JsonProperty("scheduledStart") Date date, @JsonProperty("driverId") Optional<UUID> optional3, @JsonProperty("vehicleId") Optional<UUID> optional4, @JsonProperty("state") RideState rideState, @JsonProperty("rideHistory") List<RideEvent> list, @JsonProperty("stopStatus") List<FullV2StopStatus> list2, @JsonProperty("overflow") Optional<? extends List<RideId>> optional5, @JsonProperty("vias") List<Via> list3, @JsonProperty("loopOptions") Optional<RideLoopOptions> optional6, @JsonProperty("deviceMarkedDown") boolean z, @JsonProperty("liveDataAvailable") boolean z2, @JsonProperty("lateBySec") Optional<Integer> optional7, @JsonProperty("lastDeviceStatus") Optional<FullDeviceStatus> optional8, @JsonProperty("navigationId") UUID uuid4, @JsonProperty("userNavigationId") UUID uuid5, @JsonProperty("effectiveNavigationId") Optional<UUID> optional9, @JsonProperty("distanceOffRouteMeters") double d, @JsonProperty("riderCount") int i, @JsonProperty("userRiderCount") Optional<Integer> optional10, @JsonProperty("bikeCount") int i2, @JsonProperty("direction") RideDirection rideDirection, @JsonProperty("boardingCode") Optional<String> optional11, @JsonProperty("payInfo") Optional<PayInfo> optional12, @JsonProperty("wait") Optional<Wait> optional13, @JsonProperty("obsolete") boolean z3, @JsonProperty("avaConfig") Optional<AvaConfig> optional14) {
```

## V2StopStatus — elements of `V2Ride.stopStatus`

Source: `com/tripshot/common/models/V2StopStatus.java`. This is the most important type in the
live graph: it is the per-stop realtime state of one ride.

### Polymorphic encoding

```java
@JsonSubTypes({@JsonSubTypes.Type(Awaiting.class), @JsonSubTypes.Type(Present.class), @JsonSubTypes.Type(Departed.class), @JsonSubTypes.Type(Skipped.class), @JsonSubTypes.Type(Canceled.class)})
@JsonTypeInfo(include = JsonTypeInfo.As.WRAPPER_OBJECT, use = JsonTypeInfo.Id.NAME)
public interface V2StopStatus extends Serializable {
```

`use = Id.NAME` with `include = As.WRAPPER_OBJECT` means the type discriminator is **the single
key of a wrapping object**, and its value is the actual payload object. The name comes from each
implementation's `@JsonTypeName`. So an element of `stopStatus` looks like:

```json
{ "Departed": { "stopId": "...", "scheduledDepartureTime": "...", "...": "..." } }
```

and never like `{"type":"Departed", ...}`. The five legal wrapper keys are exactly:
`Awaiting`, `Present`, `Departed`, `Skipped`, `Canceled` (American spelling, one `l`).

Note the annotation lists the subtypes in the order Awaiting, Present, Departed, Skipped,
Canceled, but the class bodies in the file appear in the order Awaiting, Present, Departed,
Canceled, Skipped. Order carries no wire meaning.

### Interface contract (fields every variant must expose)

```java
    @JsonProperty("byRequest")
    StopByRequestStatus getByRequestStatus();

    @JsonIgnore
    StopStatusKey getKey();

    @JsonProperty("scheduledAt")
    TimeOfDay getLocalScheduledDepartureTime();

    @JsonProperty
    Date getScheduledDepartureTime();

    @JsonProperty
    UUID getStopId();

    @JsonProperty
    int getViaIdx();

    @JsonProperty("visitType")
    VisitType getVisitType();

    @JsonProperty
    boolean isTimepoint();
```

So the **common seven** wire fields carried by all five variants are:
`stopId`, `scheduledDepartureTime`, `scheduledAt`, `timepoint`, `byRequest`, `viaIdx`, `visitType`.
Everything else is variant-specific.

`getKey()` is `@JsonIgnore` and derived: `new StopStatusKey(getStopId(), getScheduledDepartureTime())`.
Two more derived, non-wire helpers exist on the interface:

```java
    @JsonIgnore
    default LocalStopStatusKey getLocalStopStatusKey() {
        return new LocalStopStatusKey(getStopId(), getLocalScheduledDepartureTime());
    }

    @JsonIgnore
    default StopOnRideKey getStopOnRideKey(RideId rideId) {
        return new StopOnRideKey(rideId, getStopId(), getLocalScheduledDepartureTime());
    }
```

### Field presence matrix

| Field | Awaiting | Present | Departed | Skipped | Canceled |
| --- | --- | --- | --- | --- | --- |
| `stopId` | yes | yes | yes | yes | yes |
| `scheduledDepartureTime` | yes | yes | yes | yes | yes |
| `scheduledAt` | yes | yes | yes | yes | yes |
| `timepoint` | yes | yes | yes | yes | yes |
| `byRequest` | yes | yes | yes | yes | yes |
| `viaIdx` | yes | yes | yes | yes | yes |
| `visitType` | yes | yes | yes | yes | yes |
| `expectedArrivalTime` | yes | yes | yes | — | — |
| `arrivalTime` | — | yes | yes | — | — |
| `departureTime` | — | — | yes | — | — |
| `selectedBay` | — | yes | — | — | — |

`selectedBay` is unique to `Present`. `departureTime` is unique to `Departed`. `Skipped` and
`Canceled` have identical creator parameter lists (differing only in the class name) and carry
only the common seven.

### Variant: `Awaiting`

`@JsonTypeName("Awaiting")` — the vehicle has not yet reached this stop.

| JSON property | Java type | Opt? | Notes |
| --- | --- | --- | --- |
| `stopId` | `UUID` | no | `checkNotNull` |
| `scheduledDepartureTime` | `Date` | no | **no null check** — assigned directly, may be null |
| `scheduledAt` | `TimeOfDay` | no | `checkNotNull`; local wall-clock `HH:mm:ss` |
| `expectedArrivalTime` | `Date` | no | `checkNotNull` — the ETA; mandatory for this variant |
| `timepoint` | `boolean` | no | primitive |
| `byRequest` | `Optional<StopByRequestStatus>` | yes | defaults to `StopByRequestStatus.ALWAYS_VISIT` |
| `viaIdx` | `int` | no | primitive; index into `V2Ride.vias` |
| `visitType` | `Optional<VisitType>` | yes | defaults to `VisitType.DROPOFF_OR_PICKUP` |

```java
        @JsonCreator
        public Awaiting(@JsonProperty("stopId") UUID uuid, @JsonProperty("scheduledDepartureTime") Date date, @JsonProperty("scheduledAt") TimeOfDay timeOfDay, @JsonProperty("expectedArrivalTime") Date date2, @JsonProperty("timepoint") boolean z, @JsonProperty("byRequest") Optional<StopByRequestStatus> optional, @JsonProperty("viaIdx") int i, @JsonProperty("visitType") Optional<VisitType> optional2) {
            this.stopId = (UUID) Preconditions.checkNotNull(uuid);
            this.scheduledDepartureTime = date;
            this.localScheduledDepartureTime = (TimeOfDay) Preconditions.checkNotNull(timeOfDay);
            this.expectedArrivalTime = (Date) Preconditions.checkNotNull(date2);
            this.timepoint = z;
            this.byRequestStatus = optional.or(StopByRequestStatus.ALWAYS_VISIT);
            this.viaIdx = i;
            this.visitType = optional2.or(VisitType.DROPOFF_OR_PICKUP);
        }
```

`Awaiting` is the variant the app treats as "next stop": `V2Ride.getNextStopStatus()` returns the
first `Awaiting` element whose `byRequestStatus != StopByRequestStatus.VISIT_NOT_REQUESTED`.

### Variant: `Present`

`@JsonTypeName("Present")` — the vehicle is currently at the stop (arrived, not yet departed).

| JSON property | Java type | Opt? | Notes |
| --- | --- | --- | --- |
| `stopId` | `UUID` | no | `checkNotNull` |
| `scheduledDepartureTime` | `Date` | no | **no null check** |
| `scheduledAt` | `TimeOfDay` | no | `checkNotNull` |
| `expectedArrivalTime` | `Date` | no | `checkNotNull` — retained even after arrival |
| `arrivalTime` | `Date` | no | `checkNotNull` — actual arrival |
| `timepoint` | `boolean` | no | primitive |
| `byRequest` | `Optional<StopByRequestStatus>` | yes | defaults to `ALWAYS_VISIT` |
| `viaIdx` | `int` | no | primitive |
| `visitType` | `Optional<VisitType>` | yes | defaults to `DROPOFF_OR_PICKUP` |
| `selectedBay` | `Optional<UUID>` | yes | stored via `orNull()`; **only variant with this field** |

```java
        @JsonCreator
        public Present(@JsonProperty("stopId") UUID uuid, @JsonProperty("scheduledDepartureTime") Date date, @JsonProperty("scheduledAt") TimeOfDay timeOfDay, @JsonProperty("expectedArrivalTime") Date date2, @JsonProperty("arrivalTime") Date date3, @JsonProperty("timepoint") boolean z, @JsonProperty("byRequest") Optional<StopByRequestStatus> optional, @JsonProperty("viaIdx") int i, @JsonProperty("visitType") Optional<VisitType> optional2, @JsonProperty("selectedBay") Optional<UUID> optional3) {
            this.stopId = (UUID) Preconditions.checkNotNull(uuid);
            this.scheduledDepartureTime = date;
            this.localScheduledDepartureTime = (TimeOfDay) Preconditions.checkNotNull(timeOfDay);
            this.expectedArrivalTime = (Date) Preconditions.checkNotNull(date2);
            this.arrivalTime = (Date) Preconditions.checkNotNull(date3);
            this.timepoint = z;
            this.byRequestStatus = optional.or(StopByRequestStatus.ALWAYS_VISIT);
            this.viaIdx = i;
            this.visitType = optional2.or(VisitType.DROPOFF_OR_PICKUP);
            this.selectedBay = optional3.orNull();
        }
```

`V2Ride.getCurrentStopStatus()` returns the first `Present` element, so at most one stop is
expected to be `Present` at a time (the code takes the first and ignores any others).
`selectedBay` is a bay UUID; bay records live in the schedule-side `StopBay` / `StopBaysByStop`
types, which this page does not cover.

### Variant: `Departed`

`@JsonTypeName("Departed")` — the vehicle has served and left the stop. This is the only variant
carrying `departureTime`, and it is the widest variant (10 wire fields).

| JSON property | Java type | Opt? | Notes |
| --- | --- | --- | --- |
| `stopId` | `UUID` | no | `checkNotNull` |
| `scheduledDepartureTime` | `Date` | no | **no null check** |
| `scheduledAt` | `TimeOfDay` | no | `checkNotNull` |
| `expectedArrivalTime` | `Date` | no | `checkNotNull` — the last ETA, retained after the fact |
| `arrivalTime` | `Date` | no | `checkNotNull` — actual arrival |
| `departureTime` | `Date` | no | `checkNotNull` — actual departure; **only variant with this field** |
| `timepoint` | `boolean` | no | primitive |
| `byRequest` | `Optional<StopByRequestStatus>` | yes | defaults to `ALWAYS_VISIT` |
| `viaIdx` | `int` | no | primitive |
| `visitType` | `Optional<VisitType>` | yes | defaults to `DROPOFF_OR_PICKUP` |

No `selectedBay`: whatever bay was selected while `Present` is not carried forward once the
status becomes `Departed`.

```java
        @JsonCreator
        public Departed(@JsonProperty("stopId") UUID uuid, @JsonProperty("scheduledDepartureTime") Date date, @JsonProperty("scheduledAt") TimeOfDay timeOfDay, @JsonProperty("expectedArrivalTime") Date date2, @JsonProperty("arrivalTime") Date date3, @JsonProperty("departureTime") Date date4, @JsonProperty("timepoint") boolean z, @JsonProperty("byRequest") Optional<StopByRequestStatus> optional, @JsonProperty("viaIdx") int i, @JsonProperty("visitType") Optional<VisitType> optional2) {
            this.stopId = (UUID) Preconditions.checkNotNull(uuid);
            this.scheduledDepartureTime = date;
            this.localScheduledDepartureTime = (TimeOfDay) Preconditions.checkNotNull(timeOfDay);
            this.expectedArrivalTime = (Date) Preconditions.checkNotNull(date2);
            this.arrivalTime = (Date) Preconditions.checkNotNull(date3);
            this.departureTime = (Date) Preconditions.checkNotNull(date4);
            this.timepoint = z;
            this.byRequestStatus = optional.or(StopByRequestStatus.ALWAYS_VISIT);
            this.viaIdx = i;
            this.visitType = optional2.or(VisitType.DROPOFF_OR_PICKUP);
        }
```

### Variant: `Skipped`

`@JsonTypeName("Skipped")` — the stop was passed without being served. Carries **only** the common
seven: no `expectedArrivalTime`, no `arrivalTime`, no `departureTime`, no `selectedBay`.

| JSON property | Java type | Opt? | Notes |
| --- | --- | --- | --- |
| `stopId` | `UUID` | no | `checkNotNull` |
| `scheduledDepartureTime` | `Date` | no | **no null check** |
| `scheduledAt` | `TimeOfDay` | no | `checkNotNull` |
| `timepoint` | `boolean` | no | primitive |
| `byRequest` | `Optional<StopByRequestStatus>` | yes | defaults to `ALWAYS_VISIT` |
| `viaIdx` | `int` | no | primitive |
| `visitType` | `Optional<VisitType>` | yes | defaults to `DROPOFF_OR_PICKUP` |

```java
        @JsonCreator
        public Skipped(@JsonProperty("stopId") UUID uuid, @JsonProperty("scheduledDepartureTime") Date date, @JsonProperty("scheduledAt") TimeOfDay timeOfDay, @JsonProperty("timepoint") boolean z, @JsonProperty("byRequest") Optional<StopByRequestStatus> optional, @JsonProperty("viaIdx") int i, @JsonProperty("visitType") Optional<VisitType> optional2) {
            this.stopId = (UUID) Preconditions.checkNotNull(uuid);
            this.scheduledDepartureTime = date;
            this.localScheduledDepartureTime = (TimeOfDay) Preconditions.checkNotNull(timeOfDay);
            this.timepoint = z;
            this.byRequestStatus = optional.or(StopByRequestStatus.ALWAYS_VISIT);
            this.viaIdx = i;
            this.visitType = optional2.or(VisitType.DROPOFF_OR_PICKUP);
        }
```

### Variant: `Canceled`

`@JsonTypeName("Canceled")` — the stop visit was cancelled. Same seven fields as `Skipped`; the
two are distinguishable only by the wrapper key.

| JSON property | Java type | Opt? | Notes |
| --- | --- | --- | --- |
| `stopId` | `UUID` | no | `checkNotNull` |
| `scheduledDepartureTime` | `Date` | no | **no null check** |
| `scheduledAt` | `TimeOfDay` | no | `checkNotNull` |
| `timepoint` | `boolean` | no | primitive |
| `byRequest` | `Optional<StopByRequestStatus>` | yes | defaults to `ALWAYS_VISIT` |
| `viaIdx` | `int` | no | primitive |
| `visitType` | `Optional<VisitType>` | yes | defaults to `DROPOFF_OR_PICKUP` |

```java
        @JsonCreator
        public Canceled(@JsonProperty("stopId") UUID uuid, @JsonProperty("scheduledDepartureTime") Date date, @JsonProperty("scheduledAt") TimeOfDay timeOfDay, @JsonProperty("timepoint") boolean z, @JsonProperty("byRequest") Optional<StopByRequestStatus> optional, @JsonProperty("viaIdx") int i, @JsonProperty("visitType") Optional<VisitType> optional2) {
            this.stopId = (UUID) Preconditions.checkNotNull(uuid);
            this.scheduledDepartureTime = date;
            this.localScheduledDepartureTime = (TimeOfDay) Preconditions.checkNotNull(timeOfDay);
            this.timepoint = z;
            this.byRequestStatus = optional.or(StopByRequestStatus.ALWAYS_VISIT);
            this.viaIdx = i;
            this.visitType = optional2.or(VisitType.DROPOFF_OR_PICKUP);
        }
```

Nothing in the decompiled code distinguishes the semantics of `Skipped` vs `Canceled` — no
comparison, no differing UI branch was found for the pair. The distinction is server-side.

### FullV2StopStatus (authenticated `/v2/liveStatus`)

`com/tripshot/common/models/FullV2StopStatus.java` repeats the same five `@JsonTypeName` subtypes,
each extending its `V2StopStatus.*` counterpart with an identical creator signature that simply
delegates to `super(...)`. The interface adds one member:

```java
public interface FullV2StopStatus extends V2StopStatus, Serializable {
    Optional<StopTallies> getTallies();
```

and in every subtype the implementation is `@JsonIgnore` returning `Optional.absent()`, e.g.:

```java
        @Override // com.tripshot.common.models.FullV2StopStatus
        @JsonIgnore
        public Optional<StopTallies> getTallies() {
            return Optional.absent();
        }
```

So `FullV2StopStatus` adds **no** wire fields over `V2StopStatus` in v127: `tallies` is
`@JsonIgnore`d and hardcoded absent.

## Vehicle — elements of the (separately fetched) vehicle list

Source: `com/tripshot/common/models/Vehicle.java`. As established above, `Vehicle` is **not**
parsed out of the `liveStatus` response by this client; it comes from `/v1/p/vehicle` or
`/v1/vehicle` and is joined client-side. The same class would parse a `vehicles` array if one
were wired up.

| JSON property | Java type | Opt? | Notes |
| --- | --- | --- | --- |
| `vehicleId` | `UUID` | no | `checkNotNull`; join key to `VehicleStatus.vehicleId` and `V2Ride.vehicleId` |
| `name` | `String` | no | `checkNotNull` |
| `capacity` | `int` | no | primitive |
| `bicycleCapacity` | `int` | no | primitive |
| `wifiAvailable` | `boolean` | no | primitive |
| `vehicleType` | `VehicleType` | no | `checkNotNull` |
| `deviceId` | `Optional<String>` | yes | onboard device identifier, a string not a UUID |
| `vendorId` | `Optional<UUID>` | yes | |
| `photoId` | `Optional<UUID>` | yes | |
| `vehicleCode` | `int` | no | primitive; human-facing numeric code |
| `safeDistancing` | `boolean` | no | primitive |

```java
    @JsonCreator
    public Vehicle(@JsonProperty("vehicleId") UUID uuid, @JsonProperty("name") String str, @JsonProperty("capacity") int i, @JsonProperty("bicycleCapacity") int i2, @JsonProperty("wifiAvailable") boolean z, @JsonProperty("vehicleType") VehicleType vehicleType, @JsonProperty("deviceId") Optional<String> optional, @JsonProperty("vendorId") Optional<UUID> optional2, @JsonProperty("photoId") Optional<UUID> optional3, @JsonProperty("vehicleCode") int i3, @JsonProperty("safeDistancing") boolean z2) {
        this.vehicleId = (UUID) Preconditions.checkNotNull(uuid);
        this.name = (String) Preconditions.checkNotNull(str);
        this.capacity = i;
        this.bicycleCapacity = i2;
        this.wifiAvailable = z;
        this.vehicleType = (VehicleType) Preconditions.checkNotNull(vehicleType);
        this.deviceId = optional.orNull();
        this.vendorId = optional2.orNull();
        this.photoId = optional3.orNull();
        this.vehicleCode = i3;
        this.safeDistancing = z2;
    }
```

## VehicleStatus — elements of `vehicleStatuses`

Source: `com/tripshot/common/models/VehicleStatus.java`. This is the live position record.

| JSON property | Java type | Opt? | Notes |
| --- | --- | --- | --- |
| `vehicleId` | `UUID` | no | `checkNotNull`; join key to `Vehicle` / `V2Ride.vehicleId` |
| `name` | `String` | no | `checkNotNull`; duplicated from `Vehicle.name` |
| `location` | `LatLng` | no | `checkNotNull`; object with keys **`lt`** / **`lg`** (see scalar encodings) |
| `accuracy` | `double` | no | primitive; unit not stated anywhere in the decompiled code (metres is the natural reading, but that is an inference, not evidence) |
| `when` | `Date` | no | `checkNotNull`; timestamp of the fix — compare against `V2LiveStatus.timestamp` to age it |
| `bearing` | `Optional<Double>` | yes | stored via `orNull()`; no range/units assertion in code |
| `speed` | `Optional<Double>` | yes | stored via `orNull()`; no units assertion in code |
| `liveDataAvailable` | `boolean` | no | primitive; see below |
| `visibility` | — | — | **NOT a field of this class** — see "Wire fields with no model counterpart" |

```java
    @JsonCreator
    public VehicleStatus(@JsonProperty("vehicleId") UUID uuid, @JsonProperty("name") String str, @JsonProperty("location") LatLng latLng, @JsonProperty("accuracy") double d, @JsonProperty("when") Date date, @JsonProperty("bearing") Optional<Double> optional, @JsonProperty("speed") Optional<Double> optional2, @JsonProperty("liveDataAvailable") boolean z) {
        this.vehicleId = (UUID) Preconditions.checkNotNull(uuid);
        this.name = (String) Preconditions.checkNotNull(str);
        this.location = (LatLng) Preconditions.checkNotNull(latLng);
        this.accuracy = d;
        this.when = (Date) Preconditions.checkNotNull(date);
        this.bearing = optional.orNull();
        this.speed = optional2.orNull();
        this.liveDataAvailable = z;
    }
```

`VehicleStatus.liveDataAvailable` is used to decide whether to draw/trust the vehicle marker, e.g.
`com/tripshot/android/rider/TripDetailMapFragment.java` and
`com/tripshot/android/rider/models/SharedRouteDetailViewModel.java` require
`vehicleStatus.isLiveDataAvailable()` (and a non-`Complete`, non-`Cancelled` ride state) before
raising late-notice UI. It is a **different field** from `V2Ride.liveDataAvailable`; no code
relates the two.

Known decompilation defect (does not affect the wire contract): `VehicleStatus.equals(Object)`
casts the argument to `FullVehicleStatus` rather than `VehicleStatus`.

### FullVehicleStatus (authenticated `/v2/liveStatus`)

Adds three properties:

| JSON property | Java type | Opt? |
| --- | --- | --- |
| `capacity` | `int` | no |
| `batteryLevel` | `Optional<Double>` | yes |
| `batteryCharging` | `Optional<Boolean>` | yes |

```java
    @JsonCreator
    public FullVehicleStatus(@JsonProperty("vehicleId") UUID uuid, @JsonProperty("name") String str, @JsonProperty("location") LatLng latLng, @JsonProperty("accuracy") double d, @JsonProperty("when") Date date, @JsonProperty("capacity") int i, @JsonProperty("batteryLevel") Optional<Double> optional, @JsonProperty("batteryCharging") Optional<Boolean> optional2, @JsonProperty("bearing") Optional<Double> optional3, @JsonProperty("speed") Optional<Double> optional4, @JsonProperty("liveDataAvailable") boolean z) {
        super(uuid, str, latLng, d, date, optional3, optional4, z);
```

## RideState — `V2Ride.state`

Source: `com/tripshot/common/models/RideState.java`. Not a Java `enum`: it is an abstract class
with six singleton-like subclasses, encoded exactly like `V2StopStatus` (wrapper object, name id).

```java
@JsonSubTypes({@JsonSubTypes.Type(Pending.class), @JsonSubTypes.Type(Scheduled.class), @JsonSubTypes.Type(Accepted.class), @JsonSubTypes.Type(Active.class), @JsonSubTypes.Type(Complete.class), @JsonSubTypes.Type(Cancelled.class)})
@JsonTypeInfo(include = JsonTypeInfo.As.WRAPPER_OBJECT, use = JsonTypeInfo.Id.NAME)
public abstract class RideState implements Serializable {
    public abstract String getName();
```

| Wrapper key (`@JsonTypeName`) | `getName()` | Payload |
| --- | --- | --- |
| `Pending` | `"Pending"` | empty array/list |
| `Scheduled` | `"Scheduled"` | empty array/list |
| `Accepted` | `"Accepted"` | empty array/list |
| `Active` | `"Active"` | empty array/list |
| `Complete` | `"Complete"` | empty array/list |
| `Cancelled` | `"Cancelled"` | empty array/list |

Note the spelling: ride state is **`Cancelled`** (two `l`s) while the stop status variant is
**`Canceled`** (one `l`). This asymmetry is real and load-bearing for a parser.

Every subtype has the same payload-less creator, which takes a `List<Object>` — i.e. the value
inside the wrapper is a (typically empty) JSON array, not an object:

```java
    @JsonTypeName("Active")
    public static class Active extends RideState {
        private static final long serialVersionUID = 1;

        @JsonCreator
        public Active(List<Object> list) {
            super();
        }

        @Override // com.tripshot.common.models.RideState
        public String getName() {
            return "Active";
        }
```

So `"state": {"Active": []}`. All six subclasses are byte-identical apart from the name.

## RideId — composite, not a plain UUID

Source: `com/tripshot/common/models/RideId.java`.

**`RideId` is a composite of a scheduled-ride UUID and a local calendar date, serialized as a
single colon-joined string.** It is not a UUID and cannot be parsed as one.

- Wire form: `"<scheduledRideId UUID>:<LocalDate>"`, e.g.
  `"3f1c9d20-1111-4444-8888-0123456789ab:2026-09-09"`.
- `LocalDate.toString()` is `Padding.fourPad(year) + "-" + Padding.twoPad(month) + "-" + Padding.twoPad(day)`,
  i.e. `YYYY-MM-DD`.
- `@JsonValue` on `toJson()` makes it a JSON **string** in both directions; `@JsonCreator` on the
  static `fromString(String)` parses it. It splits on `":"` and requires exactly two parts.
- It is `Comparable` (by UUID then date) and used as an `ImmutableMap` key in `V2LiveStatus.rideMap`.

The same ride recurs on multiple service days: the UUID identifies the *scheduled* ride pattern,
the date pins the instance.

```java
public final class RideId implements Serializable, Comparable<RideId> {
    private static final long serialVersionUID = 1;
    private final LocalDate day;
    private final UUID scheduledRideId;

    public RideId(UUID uuid, LocalDate localDate) {
        this.scheduledRideId = (UUID) Preconditions.checkNotNull(uuid);
        this.day = (LocalDate) Preconditions.checkNotNull(localDate);
    }

    @JsonCreator
    public static RideId fromString(String str) {
        String[] strArrSplit = str.split(":");
        if (strArrSplit.length != 2) {
            throw new IllegalArgumentException("invalid ride id, externalized=" + str);
        }
        return new RideId(UUID.fromString(strArrSplit[0]), LocalDate.fromString(strArrSplit[1]));
    }

    public UUID getScheduledRideId() {
        return this.scheduledRideId;
    }

    public LocalDate getDay() {
        return this.day;
    }

    @JsonValue
    public String toJson() {
        return this.scheduledRideId.toString() + ":" + this.day.toString();
    }
```

## Supporting enums

### VisitType (`visitType` on every `V2StopStatus` variant)

`com/tripshot/common/models/VisitType.java` — `@JsonValue` on `getName()`, `@JsonCreator` on
`fromName(String)` which matches case-insensitively and **throws** on anything else.

| Constant | Wire value |
| --- | --- |
| `DROPOFF_OR_PICKUP` | `"DropOffOrPickup"` (also the default when `visitType` is absent) |
| `DROPOFF_ONLY` | `"DropOffOnly"` |
| `PICKUP_ONLY` | `"PickupOnly"` |

```java
public enum VisitType {
    DROPOFF_OR_PICKUP("DropOffOrPickup"),
    DROPOFF_ONLY("DropOffOnly"),
    PICKUP_ONLY("PickupOnly");
```

### StopByRequestStatus (`byRequest` on every `V2StopStatus` variant)

`com/tripshot/common/models/StopByRequestStatus.java` (Kotlin). `@JsonValue` on the `rawValue`
field; the `@JsonCreator` companion maps unknown strings to `UNKNOWN` rather than throwing.

| Constant | Wire value |
| --- | --- |
| `ALWAYS_VISIT` | `"av"` (also the default when `byRequest` is absent) |
| `VISIT_REQUESTED_TO_DRIVER` | `"vd"` |
| `VISIT_NOT_REQUESTED` | `"vn"` |
| `UNKNOWN` | `"UNKNOWN"` (the value of `com.braintreepayments.api.BinData.UNKNOWN`; also the fallback for unrecognized input) |

```java
public enum StopByRequestStatus {
    ALWAYS_VISIT("av"),
    VISIT_REQUESTED_TO_DRIVER("vd"),
    VISIT_NOT_REQUESTED("vn"),
    UNKNOWN(BinData.UNKNOWN);
```

`V2Ride.getNextStopStatus()` skips `Awaiting` stops whose status is `VISIT_NOT_REQUESTED`.

### RideDirection (`V2Ride.direction`)

| Constant | Wire value |
| --- | --- |
| `INBOUND` | `"Inbound"` |
| `OUTBOUND` | `"Outbound"` |
| `NON_DIRECTIONAL` | `"NonDirectional"` |

Case-insensitive `@JsonCreator`; throws `IllegalArgumentException` on unknown values.

### VehicleType (`Vehicle.vehicleType`)

`bus`, `ferry`, `lightRail`, `subway`, `rail`, `cableTram`, `aerialLift`, `funicular`,
`trolleyBus`, `monoRail`, `cutaway`, `minivan`, `car`, `unknown`.

## Scalar encodings used above

| Java type | JSON form | Evidence |
| --- | --- | --- |
| `java.util.Date` | string `yyyy-MM-dd'T'HH:mm:ss.SSS'Z'`, UTC | mapper `setDateFormat` in `RiderModule.provideObjectMapper()` |
| `com.tripshot.common.utils.TimeOfDay` | string `HH:mm:ss` (zero-padded, local wall clock, no date) | `@JsonValue toJson()` → `toString()` = `twoPad(hour)+":"+twoPad(min)+":"+twoPad(sec)` |
| `com.tripshot.common.utils.LocalDate` | string `YYYY-MM-DD` | `toString()` = `fourPad(year)+"-"+twoPad(month)+"-"+twoPad(day)` |
| `com.tripshot.common.utils.LatLng` | object `{"lt": <double>, "lg": <double>}` | `@JsonCreator public LatLng(@JsonProperty("lt") double d, @JsonProperty("lg") double d2)`, with range preconditions |
| `com.tripshot.common.utils.RgbColor` | string, parsed by `RgbColor.parseUnchecked` (`@JsonCreator`), emitted by `@JsonValue toJson()` | hex forms validated by `HEX_COLOR_PATTERN_RRGGBB` |
| `RideId` | string `"<uuid>:<YYYY-MM-DD>"` | see `RideId` |
| `StopStatusKey` | object `{"stopId": <uuid>, "departureTime": <Date>}` when serialized as a value | note the creator property is `departureTime` while the getter is `getScheduledDepartureTime()` |

`TimeOfDay` accepts hours >= 24 elsewhere in the app (`TimeOfDay.extendedFromDate`), so an
`HH` field greater than `23` is plausible for after-midnight service; the parser is
`TimeOfDay.fromString`.

## Wire fields with no model counterpart

`FAIL_ON_UNKNOWN_PROPERTIES = false` means the server can and does send more than the APK models.
Cross-checking the v127 models against a captured `/v1/p/liveStatus` response
(`nocommit/live.json` in this repo — **wire evidence, not code evidence**) shows these
unmodelled members. They are listed so a re-implementation is not surprised by them; the APK
tells us nothing about their semantics.

| Location | Wire member | Status in APK v127 |
| --- | --- | --- |
| top level | `date` (object `{year, month, day}`) | not modelled by `V2LiveStatus` |
| top level | `vehicles` (array of vehicle records) | not modelled by `V2LiveStatus`; the client fetches `/v1/p/vehicle` instead |
| `vehicles[]`, `vehicleStatuses[]` | `visibility` (string, `"PublicRider"` observed) | **no `visibility` field and no `Visibility` enum exist anywhere in the decompiled sources** — see the note below |
| `vehicles[]` | `gtfsName`, `shortName`, `deleted`, `regionId`, `wheelchairCapacity`, `seatsPerWheelchair`, `infantSeatCapacity`, `toddlerSeatCapacity` | not in `Vehicle`'s creator |
| `vehicleStatuses[]` | `gtfsName`, `vestigeViewLiveFeed` | not in `VehicleStatus`'s creator |
| `rides[]` | `headwayDefinedTripId`, `acceptingDeviceId`, `shiftId`, `fullRideHistory`, `replacedBy`, `relatedToOriginal`, `relatedTo`, `impromptu`, `lastMonitorUpdate`, `lastEtaUpdate`, `scheduledEnd`, `vehicleShortName`, `vehicleCapacity`, `apcRiderCount`, `tags`, `reservedSeating`, `capacity`, `bicycleCapacity`, `wheelchairCapacity`, `seatsPerWheelchair`, `shortName` | not in `V2Ride`'s creator (some are `FullV2Ride`-only, e.g. `boardingCode`, `wait`, `avaConfig`, which the public endpoint also emitted in this capture) |
| `rides[].stopStatus[].Awaiting` | `riderStatus` (string; `"OnTime"`, `"Delayed"`, `"Unknown"` observed) | not in `V2StopStatus.Awaiting`'s creator |

### On `visibility` / `PublicRider`

The task brief expected a `Visibility` enum with values such as `PublicRider`. **No such type
exists in the decompiled APK.** Exhaustive checks performed:

- `grep -rl "PublicRider" nocommit/jadx/sources/` → no hits (the only hits under `nocommit/`
  are the JSON wire captures `live.json` and `routelive.json`).
- No `Visibility.java` under `com/tripshot/`; the only `Visibility` symbols in the tree belong
  to AndroidX/Kotlin (`androidx.transition.Visibility`, `kotlin.reflect.KVisibility`, …).
- Neither `Vehicle` nor `VehicleStatus` (nor `FullVehicleStatus`) declares a `visibility`
  creator parameter, field, or getter.

Therefore: `visibility` is a **server-side wire field that APK v127 silently discards**, and the
set of its legal values **cannot be enumerated from the APK**. `"PublicRider"` is the only value
observed in the captured response; treat the enum domain as unknown.

## Ambiguities and things the APK does not settle

1. **`lateBySec` semantics** — sign convention, reference point, and presence rules are not
   derivable; the field is parsed but never read. (Detail above.)
2. **`visibility` enum domain** — the field is not modelled at all; only `"PublicRider"` observed.
3. **`accuracy`, `speed`, `bearing` units** on `VehicleStatus` — no unit is asserted, converted, or
   labelled anywhere in the decompiled code paths reviewed.
4. **`Skipped` vs `Canceled`** — identical payloads; no decompiled branch distinguishes them.
5. **`scheduledDepartureTime` nullability** — declared non-`Optional` on all five `V2StopStatus`
   variants but assigned with no `checkNotNull`, unlike every other non-optional field there. A
   server omitting it yields a `null` `Date` and a later NPE in `getKey()` /
   `new StopStatusKey(...)`. Whether the server can omit it is unknown.
6. **`distanceOffRouteMeters` vs `distanceOfRouteMeters`** — read and write names differ (see
   `V2Ride`).
7. **`Cancelled` (RideState) vs `Canceled` (V2StopStatus)** — deliberate-looking spelling split;
   both confirmed verbatim from `@JsonTypeName`.
8. **`V2LiveStatus.timestamp` vs `VehicleStatus.when`** — the code never compares them, so no
   staleness threshold is derivable from the APK.
