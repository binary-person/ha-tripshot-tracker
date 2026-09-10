---
id: api.transport
title: HTTP transport, headers and serialization
kind: transport
apk_refs:
  - path: com/tripshot/android/rider/RiderModule.java
    symbol: providesTripshotService
    sha256: d237de4eebd0a370436684048f4c1e8038ec94378ba3f4ede0b0c76c04812cd9
  - path: com/tripshot/android/rider/RiderModule.java
    symbol: provideObjectMapper
    sha256: 7a353d833df601590cfcee89c3f862a07582862f406c4dec336edca2aceb9178
  - path: com/tripshot/android/rider/RiderModule.java
    symbol: providedBaseUrlInterceptor
    sha256: 7b41fbcf17853f63cfcbdca8284946e9c87ee39392909decec52e15aaed744ad
  - path: com/tripshot/android/rider/BuildConfig.java
    symbol: BASE_URL
    sha256: 8926116cbfdec97f0cfc1fda9d3df91d69db54ea963adffec78b64739046471d
  - path: com/tripshot/android/rider/BuildConfig.java
    symbol: VERSION_NAME
    sha256: 8dc7c129abdfb73671fe6a0b99ce8fcb197351abd50cd602f511004f06c2f204
  - path: com/tripshot/android/rider/BuildConfig.java
    symbol: VERSION_CODE
    sha256: 01f07d480ed502a438dc9efe3edcbce7ac950d60d875371b82684a17f25e73ef
  - path: com/tripshot/android/utils/BaseUrlInterceptor.java
    symbol: update
    sha256: d92192f0ce066aab3dd9ff81473bfd5293e7f53556f588268b181701faf04fa8
  - path: com/tripshot/android/utils/BaseUrlInterceptor.java
    symbol: intercept
    sha256: f75ca1dd15a8cb02c364a0eb26a0539420bae2ed46761866e348aa76478ea657
  - path: com/tripshot/android/rider/RiderApplication.java
    symbol: baseUrlInterceptor
    sha256: db23046bc84319e8889d8a56e1a997a633ce7291b32848e598e60125a4bc2831
  - path: com/tripshot/android/services/UserStore.java
    symbol: getUserAuthBearerToken
    sha256: 0b405c497cb13709bf26fd949514c51062f9d9a5fe20e1cddecedc50c6ebb541
  - path: com/tripshot/android/services/TripshotService.java
    symbol: draftRequestOnDemandRide
    sha256: e832207be172bb3c182078f03c881e8c62bb3fee4335bb3a39c29dd5950e03af
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getPackedBadgeData
    sha256: d0908fc17bb12ca25ca99ab122cb45eaa8af280f197c31e43ca0fb704aae9ef1
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getSharedRouteDetails
    sha256: 4712f2faeaf16ce90231aafd88e4463629096ecece70a0551b21009b94b3da2c
  - path: com/tripshot/android/services/TripshotService.java
    symbol: getReservationPlanForDate
    sha256: 1d1a0133f7e9776b6e22514cc87256d46ec10f44051f1c41debbdebe6bb9f851
  - path: com/tripshot/common/TripshotJacksonModule.java
    symbol: setupModule
    sha256: 7fba02ae92f932305beab2ef8fd794d4af336b80bf7d26848e88b7ef75cbf884
  - path: com/tripshot/common/TripshotDeserializers.java
    symbol: findBeanDeserializer
    sha256: f6173a2dc1dd52120dbf862f9c79747baf5a71747bc6af4cc673ffdc1fe263df
  - path: com/tripshot/common/TripshotSerializers.java
    symbol: findSerializer
    sha256: bdf9e8d515e1ef6bd05c7d29b37902cfa10fefc89ae1fa4769eb4d5ea08d92a9
  - path: com/tripshot/common/utils/TimeOfDay.java
    symbol: toJson
    sha256: 33c2cec5a8cc5414ad70c8ccd21eee732a2dd3f945afba8043a53b4dc1fcb090
  - path: com/tripshot/common/utils/TimeOfDay.java
    symbol: fromString
    sha256: 41354ff9cc9ffe48172db64d6282d035137fc1739d77c457c7b036ba11b8679e
  - path: com/tripshot/common/utils/LocalDate.java
    symbol: LocalDate
    sha256: 2e6fbbb8ecf650b32d09168be431df1dc4be855108c68e3dfe5ced27e7688eef
  - path: com/tripshot/common/utils/LocalDate.java
    symbol: StringDeserializer
    sha256: bce40b1585f25c28cad4252f842aa5e88d889320628081c6ef9981ddd20b9c26
  - path: com/tripshot/common/utils/LocalDateTime.java
    symbol: StringDeserializer
    sha256: 4ec9d27052a033245abd908b995c2774877e66106b5dce48f993ee8c2067b2bb
  - path: com/tripshot/common/utils/RgbColor.java
    symbol: parseUnchecked
    sha256: ce65eb88eb1dee83e80614177319bd9e06387e78067ba7ea50621d4e2a91e081
  - path: com/tripshot/common/utils/Padding.java
    symbol: twoPad
    sha256: 197226b436e5871870fbe36f298ef223bb64a237bea375cc4b9d5289c1fd9d3f
  - path: com/tripshot/common/models/RideId.java
    symbol: toJson
    sha256: 7e9574c35678554a4d4980f2b918d8259587f8d4778133ae44f69185d1bcf5fa
  - path: com/tripshot/common/models/ShiftId.java
    symbol: fromString
    sha256: e4323d8cc5990ee38e5b836889312ffbbb8e3f43a24e51d3feef35ed1c594311
  - path: com/tripshot/common/models/Instance.java
    symbol: getInstanceId
    sha256: e5813e118542223c461de7b75242ecb1097748e7f4374be198c416ec1530c691
  - path: com/tripshot/common/resort/FlightId.java
    symbol: getScheduledDepartureDate
    sha256: 49ef69b0e16208279284ebc05b737d96f991ce893bdfed7acbb4b68270ed03e3
  - path: com/tripshot/common/models/CalculateFutureStartDateResponse.java
    symbol: getDate
    sha256: ffaf3fe8f2901ac659f22156c504e629a8edf8d515c5e70f71a51c833cfcda68
depends_on: []
---

All evidence below is verbatim decompiled Java from `nocommit/jadx/sources/`. Paths in headings and citations are relative to that root.

## 1. Base URL and host selection

The default base URL is a build constant.

`com/tripshot/android/rider/BuildConfig.java`:

```java
    public static final String BASE_URL = "https://api.tripshot.com";
```

It is injected into a single shared `BaseUrlInterceptor` singleton.

`com/tripshot/android/rider/RiderModule.java`:

```java
    @Provides
    @Singleton
    public BaseUrlInterceptor providedBaseUrlInterceptor() {
        return new BaseUrlInterceptor(BuildConfig.BASE_URL);
    }
```

`com/tripshot/android/utils/BaseUrlInterceptor.java` constructor stores it as both the current and the default base URL:

```java
    public BaseUrlInterceptor(String str) {
        this.defaultBaseUrl = str;
        setBaseUrl(str);
    }
```

### 1.1 `update()` host-selection rules

`update()` takes the **instance name** (not the instance id) and maps it to a host. The argument is lowercased first, so all `startsWith`/`endsWith`/`equals` checks below are effectively case-insensitive.

`com/tripshot/android/utils/BaseUrlInterceptor.java`:

```java
    public void update(String str) {
        String lowerCase = str.toLowerCase();
        if (lowerCase.startsWith("msft-us-stage") || lowerCase.startsWith("microsoft-us-stage") || lowerCase.equalsIgnoreCase("microsoft training")) {
            setBaseUrl("https://microsoft-us-stage.tripshot.com");
            return;
        }
        if (lowerCase.equals("microsoft svc") || lowerCase.equals("microsoft-svc")) {
            setBaseUrl("https://microsoft-svc.tripshot.com");
            return;
        }
        if (lowerCase.startsWith("msft-us") || lowerCase.startsWith("microsoft-us") || lowerCase.equalsIgnoreCase("boys and girls club")) {
            setBaseUrl("https://microsoft-us.tripshot.com");
            return;
        }
        if (lowerCase.endsWith("-emea")) {
            setBaseUrl("https://apple-emea.tripshot.com");
        } else if (lowerCase.endsWith("-apac")) {
            setBaseUrl("https://apple-apac.tripshot.com");
        } else {
            setBaseUrl(this.defaultBaseUrl);
        }
    }
```

Rules, in evaluation order (first match wins):

| # | Condition on `instanceName.toLowerCase()` | Resulting base URL |
|---|---|---|
| 1 | starts with `msft-us-stage`, or starts with `microsoft-us-stage`, or equals `microsoft training` | `https://microsoft-us-stage.tripshot.com` |
| 2 | equals `microsoft svc` or `microsoft-svc` | `https://microsoft-svc.tripshot.com` |
| 3 | starts with `msft-us`, or starts with `microsoft-us`, or equals `boys and girls club` | `https://microsoft-us.tripshot.com` |
| 4 | ends with `-emea` | `https://apple-emea.tripshot.com` |
| 5 | ends with `-apac` | `https://apple-apac.tripshot.com` |
| 6 | otherwise (fallback) | `defaultBaseUrl` = `https://api.tripshot.com` |

Note the ordering matters: rule 1 (`msft-us-stage`) is checked before rule 3 (`msft-us`), which is a strict prefix of it.

### 1.2 Who calls `update()`

`com/tripshot/android/rider/RiderApplication.java` — a persisted base URL preference wins over name-derived selection:

```java
        Instance instanceOrNull = this.userStore.getInstance().orNull();
        FullUser fullUserOrNull = this.userStore.getAuthenticatedUser().orNull();
        String strOrNull = this.prefsStore.getBaseUrl().orNull();
        if (strOrNull != null) {
            this.baseUrlInterceptor.setBaseUrl(strOrNull);
        } else if (instanceOrNull != null) {
            this.baseUrlInterceptor.update(instanceOrNull.getName());
            this.prefsStore.setBaseUrl(Optional.of(this.baseUrlInterceptor.getBaseUrl()));
        }
```

### 1.3 Per-request URL rewriting, and the two globally-pinned paths

The interceptor rewrites scheme/host/port of every outgoing request. Two discovery paths are always forced back to the **default** base URL (`https://api.tripshot.com`), regardless of the currently selected instance host.

`com/tripshot/android/utils/BaseUrlInterceptor.java`:

```java
    @Override // okhttp3.Interceptor
    public Response intercept(Interceptor.Chain chain) throws IOException {
        HttpUrl httpUrl;
        Request request = chain.request();
        if (Objects.equal(request.url().encodedPath(), "/v1/global/discovery") || Objects.equal(request.url().encodedPath(), "/v1/global/advertisedInstance")) {
            httpUrl = HttpUrl.get(this.defaultBaseUrl);
        } else {
            httpUrl = HttpUrl.get(getBaseUrl());
        }
        return chain.proceed(request.newBuilder().url(request.url().newBuilder().scheme(httpUrl.scheme()).host(httpUrl.host()).port(httpUrl.port()).build()).build());
    }
```

Only scheme, host and port are replaced — path and query are preserved. The `Retrofit.baseUrl(...)` value is therefore only a bootstrap; the interceptor is authoritative at request time.

## 2. Request headers added by the client

All request headers for the main API client are added by an anonymous `Interceptor` inside `providesTripshotService`. This is the whole method, quoted verbatim from `com/tripshot/android/rider/RiderModule.java`:

```java
    @Provides
    @Singleton
    public TripshotService providesTripshotService(@ForApplication Context context, BaseUrlInterceptor baseUrlInterceptor, ObjectMapper objectMapper, final UserStore userStore) {
        try {
            PackageInfo packageInfo = this.application.getPackageManager().getPackageInfo(this.application.getPackageName(), 0);
            final String str = "Android Rider " + packageInfo.versionName + RemoteSettings.FORWARD_SLASH_STRING + packageInfo.versionCode;
            Retrofit.Builder builder = new Retrofit.Builder();
            builder.baseUrl(baseUrlInterceptor.getBaseUrl());
            builder.addCallAdapterFactory(RxJava3CallAdapterFactory.create());
            builder.addConverterFactory(JacksonConverterFactory.create(objectMapper));
            OkHttpClient.Builder builder2 = new OkHttpClient.Builder();
            builder2.connectTimeout(10L, TimeUnit.SECONDS);
            builder2.readTimeout(10L, TimeUnit.SECONDS);
            builder2.writeTimeout(10L, TimeUnit.SECONDS);
            builder2.cache(new Cache(context.getCacheDir(), 4194304L));
            builder2.addInterceptor(baseUrlInterceptor);
            builder2.addInterceptor(new Interceptor() { // from class: com.tripshot.android.rider.RiderModule.2
                @Override // okhttp3.Interceptor
                public Response intercept(Interceptor.Chain chain) throws IOException {
                    Request.Builder builderNewBuilder = chain.request().newBuilder();
                    Instance instanceOrNull = userStore.getInstance().orNull();
                    if (instanceOrNull != null) {
                        builderNewBuilder.addHeader("X-Instance-Id", String.valueOf(instanceOrNull.getInstanceId()));
                    }
                    String strHeader = chain.request().header("X-Timeout");
                    builderNewBuilder.removeHeader("X-Timeout");
                    if (strHeader != null) {
                        int i = Integer.parseInt(strHeader);
                        chain = chain.withReadTimeout(i, TimeUnit.SECONDS).withWriteTimeout(i, TimeUnit.SECONDS);
                    }
                    String strOrNull = userStore.getUserAuthBearerToken().orNull();
                    if (strOrNull != null) {
                        builderNewBuilder.addHeader("Authorization", "Bearer " + strOrNull);
                    }
                    builderNewBuilder.addHeader("X-Tripshot-Build", str);
                    Response responseProceed = chain.proceed(builderNewBuilder.build());
                    String strHeader2 = responseProceed.header("X-Session-Ending");
                    if (strHeader2 != null) {
                        try {
                            userStore.setSessionEndingSeconds(Math.max(0, Integer.parseInt(strHeader2)));
                        } catch (NumberFormatException unused) {
                            Log.d(RiderModule.TAG, "unexpected X-Session-Ending header: " + strHeader2);
                        }
                    }
                    String strHeader3 = responseProceed.header("X-Token");
                    if (strHeader3 != null) {
                        userStore.setUserAuthBearerToken(strHeader3);
                    }
                    if (!responseProceed.isSuccessful()) {
                        Log.d(RiderModule.TAG, "during http request, url=" + responseProceed.request().url() + ", code=" + responseProceed.code() + ", message=" + responseProceed.message());
                    }
                    if (responseProceed.code() == 401) {
                        try {
                            Log.d(RiderModule.TAG, "got 401, logging out user");
                            userStore.logoutUser();
                        } catch (IOException e) {
                            Log.e(RiderModule.TAG, "while logging out user", e);
                        }
                    }
                    return responseProceed;
                }
            });
            HttpLoggingInterceptor httpLoggingInterceptor = new HttpLoggingInterceptor();
            httpLoggingInterceptor.setLevel(HttpLoggingInterceptor.Level.BASIC);
            builder2.addInterceptor(httpLoggingInterceptor);
            builder2.addInterceptor(new ChuckerInterceptor.Builder(context).collector(new ChuckerCollector(context, false)).build());
            builder.client(builder2.build());
            return (TripshotService) builder.build().create(TripshotService.class);
        } catch (PackageManager.NameNotFoundException unused) {
            throw new IllegalStateException("missing package info");
        }
    }
```

### 2.1 `X-Instance-Id`

Added **only when a selected `Instance` exists** in the `UserStore`:

```java
                    Instance instanceOrNull = userStore.getInstance().orNull();
                    if (instanceOrNull != null) {
                        builderNewBuilder.addHeader("X-Instance-Id", String.valueOf(instanceOrNull.getInstanceId()));
                    }
```

The value is the decimal string of the instance id. `getInstanceId()` returns a primitive `int`:

`com/tripshot/common/models/Instance.java`:

```java
    public int getInstanceId() {
```

So the header is e.g. `X-Instance-Id: 1234`.

### 2.2 `Authorization: Bearer <token>`

Added **only when a user auth bearer token is present**:

```java
                    String strOrNull = userStore.getUserAuthBearerToken().orNull();
                    if (strOrNull != null) {
                        builderNewBuilder.addHeader("Authorization", "Bearer " + strOrNull);
                    }
```

The token source is a Guava `Optional<String>` on the store:

`com/tripshot/android/services/UserStore.java`:

```java
    Optional<String> getUserAuthBearerToken();
```

Acquiring that token is the login path and is **out of scope** for this document.

### 2.3 `X-Tripshot-Build`

Added **unconditionally on every request** through this client:

```java
                    builderNewBuilder.addHeader("X-Tripshot-Build", str);
```

`str` is computed once, at client-construction time:

```java
            PackageInfo packageInfo = this.application.getPackageManager().getPackageInfo(this.application.getPackageName(), 0);
            final String str = "Android Rider " + packageInfo.versionName + RemoteSettings.FORWARD_SLASH_STRING + packageInfo.versionCode;
```

`RemoteSettings.FORWARD_SLASH_STRING` is a plain slash:

`com/google/firebase/sessions/settings/RemoteSettings.java`:

```java
    public static final String FORWARD_SLASH_STRING = "/";
```

So the format string is `"Android Rider " + versionName + "/" + versionCode`.

`packageInfo.versionName` / `packageInfo.versionCode` come from the installed package manifest, which for this build is generated from:

`com/tripshot/android/rider/BuildConfig.java`:

```java
    public static final int VERSION_CODE = 541;
    public static final String VERSION_NAME = "127";
```

**Concrete value for this build:**

```
X-Tripshot-Build: Android Rider 127/541
```

(Derived from `BuildConfig.VERSION_NAME` / `BuildConfig.VERSION_CODE`; the runtime value is read from `PackageInfo`, not from `BuildConfig` directly. No `AndroidManifest.xml` was present under `nocommit/jadx/resources/` in this decompile to cross-check the manifest's own `android:versionName` / `android:versionCode`.)

### 2.4 `X-Timeout` — a request-side pseudo-header, stripped before the wire

`X-Timeout` is **not** a header the server ever sees from this client. It is declared statically on selected Retrofit methods via `@Headers`, read by the interceptor, then removed from the outgoing request and used purely to widen the OkHttp per-call read/write timeouts.

Interceptor logic, in order:

```java
                    String strHeader = chain.request().header("X-Timeout");
                    builderNewBuilder.removeHeader("X-Timeout");
                    if (strHeader != null) {
                        int i = Integer.parseInt(strHeader);
                        chain = chain.withReadTimeout(i, TimeUnit.SECONDS).withWriteTimeout(i, TimeUnit.SECONDS);
                    }
```

Precise semantics:

1. The value is read from the **original** request (`chain.request()`).
2. `removeHeader("X-Timeout")` is applied to the new request builder, so the header is dropped from what is actually sent.
3. If present, the value is parsed as an integer **number of seconds** and applied via `chain.withReadTimeout(...)` / `chain.withWriteTimeout(...)`, replacing the client-wide 10 s read/write timeouts **for this call only**. The connect timeout is *not* overridden.
4. `Integer.parseInt` is unguarded here — a non-numeric value would throw `NumberFormatException` out of the interceptor.
5. Because the removal happens on the builder unconditionally, the header is stripped even when absent (a no-op).

Declaration sites in `com/tripshot/android/services/TripshotService.java`:

```java
    @Headers({"X-Timeout: 30"})
    @POST("/v1/onDemandRideRequestDraft")
    Observable<DraftOnDemandRideResponse> draftRequestOnDemandRide(@Body OnDemandRideRequest onDemandRideRequest, @Query("asDevice") boolean z);

    @Headers({"X-Auth-Type: user", "X-Timeout: 30"})
    @POST("/v1/onDemandRideRequestDraft?asAdmin=true")
    Observable<DraftOnDemandRideResponseForAdmin> draftRequestOnDemandRideAsAdmin(@Body OnDemandRideRequest onDemandRideRequest);
```

```java
    @Headers({"X-Timeout: 120"})
    @GET("/v4/badgeData")
    Call<ResponseBody> getPackedBadgeData();
```

```java
    @Headers({"X-Timeout: 30"})
    @GET("/v3/shared/route/{routeId}?breakupExactLoops=true")
    Observable<SharedRouteDetails> getSharedRouteDetails(@Path("routeId") String str, @Nullable @Query("day") LocalDate localDate, @Nullable @Query("forUserId") UUID uuid, @Query("includePreviousDayRidesSpanningMidnight") boolean z);

    @Headers({"X-Timeout: 30"})
    @GET("/v3/p/shared/route/{routeId}?breakupExactLoops=true")
    Observable<SharedRouteDetails> getSharedRouteDetailsPublic(@Path("routeId") String str, @Nullable @Query("day") LocalDate localDate, @Nullable @Query("forUserId") UUID uuid, @Query("includePreviousDayRidesSpanningMidnight") boolean z);
```

```java
    @Headers({"X-Timeout: 30"})
    @POST("/v1/onDemandRideRequest")
    Observable<OnDemandRideResponse> requestOnDemandRide(@Body OnDemandRideRequest onDemandRideRequest, @Query("asDevice") boolean z);

    @Headers({"X-Auth-Type: user", "X-Timeout: 30"})
    @POST("/v1/onDemandRideRequest?asAdmin=true")
    Observable<OnDemandRideResponseForAdmin> requestOnDemandRideAsAdmin(@Body OnDemandRideRequest onDemandRideRequest);
```

That is the complete set of `X-Timeout` declarations in the decompiled sources: 7 `@Headers` occurrences in `TripshotService.java` (lines 435, 439, 713, 884, 888, 1193, 1197), plus the two interceptor lines in `RiderModule.java` (264-265). There are no other references to the string `X-Timeout` anywhere in the sources.

### 2.5 `X-Auth-Type` (adjacent finding, not interceptor-added)

`X-Auth-Type: user` also appears in `@Headers` on `TripshotService` methods. Unlike `X-Timeout`, **nothing in the interceptor removes it**, so it is transmitted to the server as a real header. Example:

```java
    @Headers({"X-Auth-Type: user"})
    @POST("/v1/resort/checkInDraft")
    Observable<Response<DraftResortCheckInSuccess>> draftCheckInResortOrderItems(@Body DraftResortCheckInRequest draftResortCheckInRequest);
```

### 2.6 Other clients built in the same module

Three other OkHttp/Retrofit clients exist in `RiderModule.java` and add a **subset** of the same headers:

- `providesAppStatusService` — adds only `X-Tripshot-Build` (same `str`), no instance id, no auth, no `X-Timeout` handling, no cache.
- `providesPicasso` — adds `X-Instance-Id`, `Authorization: Bearer`, and `X-Tripshot-Build` under the same conditions, but has **no** `X-Timeout` handling and **no** response-header reactions.
- `providesTokenTransitService` — a different host (`https://api.tokentransit.com`) with `Token-Transit-Api-Key`, `Token-Transit-Api-Version: 2020-05-21`, `Cookie: user_session_id=...`, `Token-Transit-Passes-State`. Out of scope here.

## 3. Response headers the client reacts to

All three reactions live in the same `RiderModule.2` interceptor, after `chain.proceed(...)`.

### 3.1 `X-Session-Ending`

```java
                    String strHeader2 = responseProceed.header("X-Session-Ending");
                    if (strHeader2 != null) {
                        try {
                            userStore.setSessionEndingSeconds(Math.max(0, Integer.parseInt(strHeader2)));
                        } catch (NumberFormatException unused) {
                            Log.d(RiderModule.TAG, "unexpected X-Session-Ending header: " + strHeader2);
                        }
                    }
```

Parsed as an integer, clamped to a minimum of `0`, and stored as a seconds count. Malformed values are logged and ignored (no store write).

`com/tripshot/android/services/UserStore.java`:

```java
    void setSessionEndingSeconds(int i);
```

### 3.2 `X-Token`

```java
                    String strHeader3 = responseProceed.header("X-Token");
                    if (strHeader3 != null) {
                        userStore.setUserAuthBearerToken(strHeader3);
                    }
```

Any response carrying `X-Token` **rotates the stored bearer token** verbatim (no parsing, no validation). Subsequent requests use the new value in `Authorization: Bearer <token>`.

`com/tripshot/android/services/UserStore.java`:

```java
    void setUserAuthBearerToken(String str) throws IOException;
```

### 3.3 Non-success logging and the 401 → logout behavior

```java
                    if (!responseProceed.isSuccessful()) {
                        Log.d(RiderModule.TAG, "during http request, url=" + responseProceed.request().url() + ", code=" + responseProceed.code() + ", message=" + responseProceed.message());
                    }
                    if (responseProceed.code() == 401) {
                        try {
                            Log.d(RiderModule.TAG, "got 401, logging out user");
                            userStore.logoutUser();
                        } catch (IOException e) {
                            Log.e(RiderModule.TAG, "while logging out user", e);
                        }
                    }
                    return responseProceed;
```

Any HTTP **401** on this client triggers `userStore.logoutUser()`. There is no retry and no token refresh — the 401 response is still returned to the caller. `IOException` from the logout is swallowed (logged only).

`com/tripshot/android/services/UserStore.java`:

```java
    void logoutUser() throws IOException;
```

## 4. Timeouts and cache

`com/tripshot/android/rider/RiderModule.java`, in `providesTripshotService`:

```java
            OkHttpClient.Builder builder2 = new OkHttpClient.Builder();
            builder2.connectTimeout(10L, TimeUnit.SECONDS);
            builder2.readTimeout(10L, TimeUnit.SECONDS);
            builder2.writeTimeout(10L, TimeUnit.SECONDS);
            builder2.cache(new Cache(context.getCacheDir(), 4194304L));
```

| Setting | Value |
|---|---|
| connect timeout | 10 s (never overridden by `X-Timeout`) |
| read timeout | 10 s default; per-call override via `X-Timeout` |
| write timeout | 10 s default; per-call override via `X-Timeout` |
| OkHttp `Cache` | `context.getCacheDir()`, `4194304L` bytes = **4 MiB** |

The same 10/10/10 s values and the same 4 MiB cache are used by `providesPicasso` and `providesTokenTransitService`; `providesAppStatusService` uses 10/10/10 s with **no** cache.

Logging interceptors present on the main client (both after the header interceptor):

```java
            HttpLoggingInterceptor httpLoggingInterceptor = new HttpLoggingInterceptor();
            httpLoggingInterceptor.setLevel(HttpLoggingInterceptor.Level.BASIC);
            builder2.addInterceptor(httpLoggingInterceptor);
            builder2.addInterceptor(new ChuckerInterceptor.Builder(context).collector(new ChuckerCollector(context, false)).build());
```

## 5. Retrofit call adapter and converter factory

`com/tripshot/android/rider/RiderModule.java`:

```java
            Retrofit.Builder builder = new Retrofit.Builder();
            builder.baseUrl(baseUrlInterceptor.getBaseUrl());
            builder.addCallAdapterFactory(RxJava3CallAdapterFactory.create());
            builder.addConverterFactory(JacksonConverterFactory.create(objectMapper));
```

Imports confirming the concrete classes:

```java
import retrofit2.Retrofit;
import retrofit2.adapter.rxjava3.RxJava3CallAdapterFactory;
import retrofit2.converter.jackson.JacksonConverterFactory;
```

- **Call adapter:** `retrofit2.adapter.rxjava3.RxJava3CallAdapterFactory.create()` — service methods return `io.reactivex.rxjava3.core.Observable<T>` / `Completable`. A few methods bypass RxJava and return raw `retrofit2.Call<ResponseBody>` (e.g. `getPackedBadgeData()`, `getSfmtaTile(...)`).
- **Converter:** `retrofit2.converter.jackson.JacksonConverterFactory.create(objectMapper)` using the singleton `ObjectMapper` from §6 — this governs `@Body` request bodies and response bodies.
- `JacksonConverterFactory` supplies only body converters, not a `stringConverter`. `@Path` / `@Query` parameters therefore fall through to Retrofit's built-in `toString()` conversion. This is why `LocalDate` appears as an **object** in JSON bodies but as a `yyyy-MM-dd` **string** in URLs (see §6.4).
- `builder.baseUrl(...)` is seeded from the interceptor's current base URL, but `BaseUrlInterceptor.intercept` rewrites scheme/host/port on every call (§1.3), so the Retrofit base URL is not what determines the destination host at runtime.

The same call-adapter + converter pair is used by `providesAppStatusService` and `providesTokenTransitService`.

## 6. Jackson `ObjectMapper` configuration

`com/tripshot/android/rider/RiderModule.java`:

```java
    @Provides
    @Singleton
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

| Setting | Value | Consequence |
|---|---|---|
| `KotlinModule` | `.nullIsSameAsDefault(true)` | JSON `null` for a Kotlin parameter with a default uses the default instead of failing/assigning null |
| `TripshotJacksonModule` | registered | custom (de)serializers, see §7 |
| `GuavaModule` | registered | `Optional`, `ImmutableList`, `ImmutableMap`, etc. |
| visibility | `getVisibilityChecker().with(JsonAutoDetect.Visibility.NONE)` | **all** auto-detection off for every property type — nothing is (de)serialized unless explicitly annotated (`@JsonProperty`, `@JsonValue`, `@JsonCreator`, …) |
| date format | `SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")`, `TimeZone.getTimeZone("UTC")` | `java.util.Date` on the wire is e.g. `2026-09-09T14:03:27.000Z`. The `Z` is a **literal**, not an offset specifier; the formatter's timezone is forced to UTC so the rendered value is genuinely UTC |
| `DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES` | `false` | unknown response fields are silently ignored (server may add fields freely) |
| `SerializationFeature.FAIL_ON_EMPTY_BEANS` | `false` | serializing a bean with no visible properties emits `{}` rather than throwing — relevant because visibility is `NONE` |

There is a second, separate mapper for Token Transit (`provideTokenTransitObjectMapper`, `@Named("tokenTransitObjectMapper")`) which registers `GuavaModule`, `KotlinModule(nullIsSameAsDefault=true)` and `TokenTransitJacksonModule`, uses the same visibility and the same two feature flags, but sets **no** date format. Out of scope here.

## 7. `TripshotJacksonModule` and the custom scalar wire formats

### 7.1 The module

`com/tripshot/common/TripshotJacksonModule.java`, in full:

```java
package com.tripshot.common;

import com.fasterxml.jackson.databind.Module;
import com.fasterxml.jackson.databind.module.SimpleModule;

/* JADX INFO: loaded from: classes5.dex */
public final class TripshotJacksonModule extends SimpleModule {
    @Override // com.fasterxml.jackson.databind.module.SimpleModule, com.fasterxml.jackson.databind.Module
    public void setupModule(Module.SetupContext setupContext) {
        setupContext.addDeserializers(new TripshotDeserializers());
        setupContext.addSerializers(new TripshotSerializers());
    }
}
```

**Important:** the module registers exactly two provider objects. `TimeOfDay`, `LocalDate`, `RgbColor`, `RideId` and `ShiftId` are **not** registered in this module — their wire format comes from `@JsonValue` / `@JsonCreator` annotations on the classes themselves. Only `LocalDateTime` is registered in the module among the scalar types.

### 7.2 `TripshotSerializers` (the complete serializer registration)

`com/tripshot/common/TripshotSerializers.java`:

```java
public final class TripshotSerializers extends Serializers.Base {
    @Override // com.fasterxml.jackson.databind.ser.Serializers.Base, com.fasterxml.jackson.databind.ser.Serializers
    public JsonSerializer<?> findSerializer(SerializationConfig serializationConfig, JavaType javaType, BeanDescription beanDescription) {
        Class<?> rawClass = javaType.getRawClass();
        if (Either.class.isAssignableFrom(rawClass)) {
            return new Either.JacksonSerializer();
        }
        if (OnDemandServiceRestriction.class.isAssignableFrom(rawClass)) {
            return new OnDemandServiceRestriction.JacksonSerializer();
        }
        return super.findSerializer(serializationConfig, javaType, beanDescription);
    }
}
```

Only two custom **serializers** exist module-wide: `Either` and `OnDemandServiceRestriction`.

### 7.3 `TripshotDeserializers` (the complete deserializer registration)

`com/tripshot/common/TripshotDeserializers.java`:

```java
public final class TripshotDeserializers extends Deserializers.Base {
    @Override // com.fasterxml.jackson.databind.deser.Deserializers.Base, com.fasterxml.jackson.databind.deser.Deserializers
    public JsonDeserializer<?> findBeanDeserializer(JavaType javaType, DeserializationConfig deserializationConfig, BeanDescription beanDescription) throws JsonMappingException {
        Class<?> rawClass = javaType.getRawClass();
        if (rawClass == Tuple2.class) {
            return new Tuple2.JacksonDeserializer(javaType);
        }
        if (rawClass == Either.class) {
            return new Either.JacksonDeserializer(javaType);
        }
        if (rawClass == DirectionsStep.class) {
            return new DirectionsStep.JacksonDeserializer();
        }
        if (rawClass == DirectionsLeg.class) {
            return new DirectionsLeg.JacksonDeserializer();
        }
        if (rawClass == DirectionsRoute.class) {
            return new DirectionsRoute.JacksonDeserializer();
        }
        if (rawClass == DirectionsResponse.class) {
            return new DirectionsResponse.JacksonDeserializer();
        }
        if (rawClass == DistanceMatrixResponse.class) {
            return new DistanceMatrixResponse.JacksonDeserializer();
        }
        if (rawClass == DistanceMatrixElement.class) {
            return new DistanceMatrixElement.JacksonDeserializer();
        }
        if (rawClass == PreboardOption.class) {
            return new PreboardOption.JacksonDeserializer();
        }
        if (rawClass == PreboardResult.class) {
            return new PreboardResult.JacksonDeserializer();
        }
        if (rawClass == GbfsDiscovery.class) {
            return new GbfsDiscovery.JacksonDeserializer();
        }
        if (rawClass == GbfsFreeBikeStatusFeed.class) {
            return new GbfsFreeBikeStatusFeed.JacksonDeserializer();
        }
        if (rawClass == GbfsStationInfoFeed.class) {
            return new GbfsStationInfoFeed.JacksonDeserializer();
        }
        if (rawClass == GbfsStationStatusFeed.class) {
            return new GbfsStationStatusFeed.JacksonDeserializer();
        }
        if (rawClass == IncidentKey.class) {
            return new IncidentKey.JacksonDeserializer();
        }
        if (rawClass == Unit.class) {
            return new Unit.JacksonDeserializer();
        }
        if (rawClass == OnDemandServiceRestriction.class) {
            return new OnDemandServiceRestriction.JacksonDeserializer();
        }
        if (rawClass == ReservationFailureReason.class) {
            return new ReservationFailureReason.JacksonDeserializer();
        }
        if (rawClass == ParkingReservationFailureReason.class) {
            return new ParkingReservationFailureReason.JacksonDeserializer();
        }
        if (rawClass == UseVoucherError.class) {
            return new UseVoucherError.JacksonDeserializer();
        }
        if (rawClass == UserVehicleUpdateFailureReason.class) {
            return new UserVehicleUpdateFailureReason.JacksonDeserializer();
        }
        if (rawClass == UserProfileUpdateFailureReason.class) {
            return new UserProfileUpdateFailureReason.JacksonDeserializer();
        }
        if (rawClass == FlexError.class) {
            return new FlexError.JacksonDeserializer();
        }
        if (rawClass == SharedRoute.class) {
            return new SharedRoute.JacksonDeserializer();
        }
        if (rawClass == UseReservationFailureReason.class) {
            return new UseReservationFailureReason.JacksonDeserializer();
        }
        if (rawClass == PickupFailureReason.class) {
            return new PickupFailureReason.JacksonDeserializer();
        }
        if (rawClass == SignupFailure.class) {
            return new SignupFailure.JacksonDeserializer();
        }
        if (rawClass == LocalDateTime.class) {
            return new LocalDateTime.StringDeserializer();
        }
        if (rawClass == ActivatePassFailure.class) {
            return new ActivatePassFailure.JacksonDeserializer();
        }
        if (rawClass == UndoFirstContactFailure.class) {
            return new UndoFirstContactFailure.JacksonDeserializer();
        }
        if (rawClass == ReservationPreboardFailure.class) {
            return new ReservationPreboardFailure.PolymorphicDeserializer();
        }
        return super.findBeanDeserializer(javaType, deserializationConfig, beanDescription);
    }
}
```

Of these, the only **scalar** is `LocalDateTime`. The rest are envelopes (`Tuple2`, `Either`, `Unit`), external-feed shapes (GBFS, Google Directions / Distance Matrix), or polymorphic error/result unions.

### 7.4 `TimeOfDay` — wire format `"HH:MM:SS"` (string)

`com/tripshot/common/utils/TimeOfDay.java`.

Serialization is `@JsonValue` on `toJson()`, which delegates to `toString()`:

```java
    @JsonValue
    public String toJson() {
        return toString();
    }

    public String toString() {
        return Padding.twoPad(getHour()) + ":" + Padding.twoPad(getMin()) + ":" + Padding.twoPad(getSec());
    }
```

`Padding.twoPad` zero-pads to two digits (`com/tripshot/common/utils/Padding.java`):

```java
    public static String twoPad(int i) {
        if (i < 10) {
            return ThreeDSStrings.DEFAULT_SDK_COUNTER_VALUE + i;
        }
        return String.valueOf(i);
    }
```

(`ThreeDSStrings.DEFAULT_SDK_COUNTER_VALUE` is the string `"0"` — jadx has folded an unrelated constant with the same value into this position.)

Deserialization is `@JsonCreator` on `fromString`, which is a **strict fixed-offset substring parse**, not the lenient `parse()`:

```java
    @JsonCreator
    public static TimeOfDay fromString(String str) {
        try {
            return new TimeOfDay(Integer.parseInt(str.substring(0, 2)), Integer.parseInt(str.substring(3, 5)), Integer.parseInt(str.substring(6, 8)));
        } catch (IndexOutOfBoundsException e) {
            throw new IllegalArgumentException("failed to parse TimeOfDay : " + str, e);
        } catch (NumberFormatException e2) {
            throw new IllegalArgumentException("failed to parse TimeOfDay : " + str, e2);
        }
    }
```

Characters at indices 0-1, 3-4, 6-7 are read as hour/min/sec; the separators at index 2 and 5 are not validated. The input must be at least 8 characters, i.e. exactly the `HH:MM:SS` shape.

Range constraints from the constructor — note **hour may be up to 47**, encoding times past midnight on a service day:

```java
    public TimeOfDay(int i, int i2, int i3) {
        Preconditions.checkArgument(i >= 0);
        Preconditions.checkArgument(i < 48);
        Preconditions.checkArgument(i2 >= 0);
        Preconditions.checkArgument(i2 < 60);
        Preconditions.checkArgument(i3 >= 0);
        Preconditions.checkArgument(i3 < 60);
        this.hour = i;
        this.min = i2;
        this.sec = i3;
    }
```

So values like `"25:30:00"` are legal on the wire. The separate lenient `TimeOfDay.parse(String)` (accepting `9`, `9:30`, `9:30pm`, …) is **not** wired to Jackson for this type — it is only reachable from UI code and from `LocalDateTime.StringDeserializer` (§7.7).

As a Retrofit `@Query` parameter, `TimeOfDay` serializes via `toString()` — the same `HH:MM:SS` form:

```java
    Observable<ParkingReservationAvailability> getParkingReservationAvailability(@Path("parkingLotId") UUID uuid, @Query("startDay") LocalDate localDate, @Query("startTime") TimeOfDay timeOfDay, @Query("endDay") LocalDate localDate2, @Query("endTime") TimeOfDay timeOfDay2);
```

### 7.5 `LocalDate` — an OBJECT in JSON bodies, a `yyyy-MM-dd` STRING in URLs

`com/tripshot/common/utils/LocalDate.java`.

**Default (JSON body) form is an object.** There is no `@JsonValue` on this class. Instead there is a `@JsonCreator` property-based constructor plus three `@JsonProperty` getters:

```java
    @JsonCreator
    public LocalDate(@JsonProperty("year") int i, @JsonProperty("month") int i2, @JsonProperty("day") int i3) {
        boolean z = false;
        Preconditions.checkArgument(i2 >= 1 && i2 <= 12, "invalid month, month" + i2);
        if (i3 >= 1 && i3 <= daysInMonth(i2, i)) {
            z = true;
        }
        Preconditions.checkArgument(z, "invalid day for month, month=" + i2 + ", day=" + i3);
        this.year = i;
        this.month = i2;
        this.day = i3;
    }
```

```java
    @JsonProperty
    public int getYear() {
        return this.year;
    }

    @JsonProperty
    public int getMonth() {
        return this.month;
    }

    @JsonProperty
    public int getDay() {
        return this.day;
    }
```

Because the mapper's auto-detection visibility is `NONE` (§6), these three explicit `@JsonProperty` getters are the *only* serialized properties. The default wire form is therefore:

```json
{"year": 2026, "month": 9, "day": 9}
```

`month` is **1-based** (1 = January) and `day` is validated against the month, with correct leap-year handling:

```java
    public static int daysInMonth(int i, int i2) {
        if (((i2 % 4 != 0 || i2 % 100 == 0) && i2 % 400 != 0) || i != 2) {
            return DAYS_PER_MONTH[i - 1];
        }
        return 29;
    }
```

An example of a model that uses the plain object form (no serializer override), `com/tripshot/common/models/CalculateFutureStartDateResponse.java`:

```java
    @JsonCreator
    public CalculateFutureStartDateResponse(@JsonProperty("date") LocalDate localDate) {
        this.date = localDate;
    }

    @JsonProperty("date")
    public final LocalDate getDate() {
        return this.date;
    }
```

**String form exists but is opt-in per field.** `LocalDate` carries two nested Jackson classes that are *not* registered in `TripshotJacksonModule`; they must be named explicitly with `@JsonSerialize(using=…)` / `@JsonDeserialize(using=…)`:

```java
    /* JADX INFO: loaded from: classes8.dex */
    public static final class StringDeserializer extends JsonDeserializer<LocalDate> {
        /* JADX WARN: Can't rename method to resolve collision */
        @Override // com.fasterxml.jackson.databind.JsonDeserializer
        public LocalDate deserialize(JsonParser jsonParser, DeserializationContext deserializationContext) throws IOException {
            JsonNode jsonNode = (JsonNode) jsonParser.getCodec().readTree(jsonParser);
            if (jsonNode.isTextual()) {
                try {
                    return LocalDate.fromString(jsonNode.asText());
                } catch (IllegalArgumentException unused) {
                    throw JsonMappingException.from(jsonParser, "expecting date");
                }
            }
            throw JsonMappingException.from(jsonParser, "expecting string");
        }
    }

    /* JADX INFO: loaded from: classes8.dex */
    public static final class StringSerializer extends JsonSerializer<LocalDate> {
        @Override // com.fasterxml.jackson.databind.JsonSerializer
        public void serialize(LocalDate localDate, JsonGenerator jsonGenerator, SerializerProvider serializerProvider) throws IOException {
            jsonGenerator.writeString(localDate.toString());
        }
    }
```

The string form is `toString()`:

```java
    public String toString() {
        return Padding.fourPad(getYear()) + "-" + Padding.twoPad(getMonth()) + "-" + Padding.twoPad(getDay());
    }
```

and is parsed by fixed-offset substrings:

```java
    public static LocalDate fromString(String str) {
        try {
            return new LocalDate(Integer.parseInt(str.substring(0, 4)), Integer.parseInt(str.substring(5, 7)), Integer.parseInt(str.substring(8, 10)));
        } catch (IndexOutOfBoundsException e) {
            throw new IllegalArgumentException("failed to parse LocalDate : " + str, e);
        } catch (NumberFormatException e2) {
            throw new IllegalArgumentException("failed to parse LocalDate : " + str, e2);
        }
    }
```

The complete set of opt-in string-form usages found in the decompile:

- `com/tripshot/common/resort/FlightDay.java` — both fields:
  ```java
    public FlightDay(@JsonProperty(ImagesContract.LOCAL) @JsonDeserialize(using = LocalDate.StringDeserializer.class) LocalDate local, @JsonProperty("utc") @JsonDeserialize(using = LocalDate.StringDeserializer.class) LocalDate utc) {
  ```
- `com/tripshot/common/resort/FlightId.java` — deserialize on the creator parameter and serialize on the getter:
  ```java
    public FlightId(@JsonProperty("airline") String airlineCode, @JsonProperty("number") int i, @JsonProperty("suffix") String suffix, @JsonProperty(HttpHeaders.ReferrerPolicyValues.ORIGIN) String originAirportCode, @JsonProperty("destination") String destinationAirportCode, @JsonProperty("scheduledDepartureDate") @JsonDeserialize(using = LocalDate.StringDeserializer.class) LocalDate scheduledDepartureDate) {
  ```
  ```java
    @JsonSerialize(using = LocalDate.StringSerializer.class)
  ```
- `com/tripshot/common/resort/PseudoOpenServiceRide.java`:
  ```java
    @JsonDeserialize(using = LocalDate.StringDeserializer.class)
  ```

`LocalDate.StringSerializer` is referenced in exactly one place (`FlightId`); `StringDeserializer` in three.

**URL form.** As a Retrofit `@Path` or `@Query` parameter, `LocalDate` bypasses Jackson entirely (`JacksonConverterFactory` provides no `stringConverter`, §5), so Retrofit's built-in `toString()` conversion applies and the value is the `yyyy-MM-dd` string:

```java
    Observable<Journal> getCommuteJournal(@Path("userId") UUID uuid, @Query("startDay") LocalDate localDate, @Query("endDay") LocalDate localDate2);
```

```java
    Observable<ReservationPlan> getReservationPlanForDate(@Path("planId") UUID uuid, @Path("date") LocalDate localDate);
```

**Summary for `LocalDate`:**

| Position | Wire form |
|---|---|
| JSON body field (default) | object `{"year":Y,"month":M,"day":D}`, month 1-based |
| JSON body field annotated with `LocalDate.StringSerializer` / `StringDeserializer` | string `"YYYY-MM-DD"` (only in `FlightDay`, `FlightId`, `PseudoOpenServiceRide`) |
| `@Path` / `@Query` parameter | string `"YYYY-MM-DD"` via `toString()` |

### 7.6 `RgbColor` — wire format `"#RRGGBB"` (uppercase hex string)

`com/tripshot/common/utils/RgbColor.java`.

Serialization via `@JsonValue`:

```java
    @JsonValue
    public String toJson() {
        return toString();
    }
```

```java
    public String toString() {
        return "#" + Padding.twoPad(Integer.toHexString(getRed())).toUpperCase() + Padding.twoPad(Integer.toHexString(getGreen())).toUpperCase() + Padding.twoPad(Integer.toHexString(getBlue())).toUpperCase();
    }
```

Output is always a leading `#` followed by 6 uppercase hex digits, e.g. `"#00AAFF"`.

Deserialization via `@JsonCreator`:

```java
    @JsonCreator
    public static RgbColor parseUnchecked(String str) {
        try {
            return parse(str);
        } catch (ParseException e) {
            throw new RuntimeException(e);
        }
    }
```

```java
    public static RgbColor parse(String str) throws ParseException {
        Matcher matcher = HEX_COLOR_PATTERN_RRGGBB.matcher(str);
        if (matcher.matches()) {
            return new RgbColor(Integer.parseInt(matcher.group(1), 16), Integer.parseInt(matcher.group(2), 16), Integer.parseInt(matcher.group(3), 16));
        }
        Matcher matcher2 = HEX_COLOR_PATTERN_RGB.matcher(str);
        if (matcher2 != null) {
            return new RgbColor(Integer.parseInt(matcher2.group(1), 16), Integer.parseInt(matcher2.group(2), 16), Integer.parseInt(matcher2.group(3), 16));
        }
        throw new ParseException("invalid hex color: " + str, 0);
    }
```

Accepted input patterns (leading `#` optional, case-insensitive — flag `2` is `Pattern.CASE_INSENSITIVE`):

```java
    private static final Pattern HEX_COLOR_PATTERN_RRGGBB = Pattern.compile("^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$", 2);
    private static final Pattern HEX_COLOR_PATTERN_RGB = Pattern.compile("^#?([0-9a-f])([0-9a-f])([0-9a-f])$", 2);
```

Note a latent bug worth recording: the 3-digit branch tests `matcher2 != null` rather than `matcher2.matches()`, so a non-matching string reaches `matcher.group(1)` and throws `IllegalStateException` instead of the intended `ParseException`. The `throw new ParseException(...)` line is effectively unreachable. Also note the 3-digit form is expanded as `#abc` → red=0x0a, green=0x0b, blue=0x0c (no digit doubling).

### 7.7 `RideId` — wire format `"<uuid>:<YYYY-MM-DD>"` (string)

`com/tripshot/common/models/RideId.java`. A composite key of a scheduled-ride UUID plus a service day, flattened to a single colon-delimited string.

```java
    @JsonCreator
    public static RideId fromString(String str) {
        String[] strArrSplit = str.split(":");
        if (strArrSplit.length != 2) {
            throw new IllegalArgumentException("invalid ride id, externalized=" + str);
        }
        return new RideId(UUID.fromString(strArrSplit[0]), LocalDate.fromString(strArrSplit[1]));
    }
```

```java
    @JsonValue
    public String toJson() {
        return this.scheduledRideId.toString() + ":" + this.day.toString();
    }
```

`toString()` is identical to `toJson()`, so `@Path`/`@Query` use of a `RideId` produces the same string. Example:

```
5f2e1c30-8a4b-4e1f-9c2d-0b7a6d5e4f31:2026-09-09
```

Note that inside `RideId` the `LocalDate` is rendered by `LocalDate.toString()` (the `YYYY-MM-DD` string form), **not** the `{year,month,day}` object form — the `@JsonValue` on `RideId` short-circuits any nested Jackson handling.

### 7.8 `ShiftId` — same shape as `RideId`

`com/tripshot/common/models/ShiftId.java`:

```java
    @JsonCreator
    public static ShiftId fromString(String str) {
        String[] strArrSplit = str.split(":");
        return new ShiftId(UUID.fromString(strArrSplit[0]), LocalDate.fromString(strArrSplit[1]));
    }
```

```java
    @JsonValue
    public String toJson() {
        return this.scheduledShiftId.toString() + ":" + this.day.toString();
    }
```

Wire form `"<scheduledShiftId uuid>:<YYYY-MM-DD>"`. Unlike `RideId` there is no length check on the split.

### 7.9 `LocalDateTime` — wire format `"YYYY-MM-DDTHH:MM:SS"` (string, deserialize only)

This is the one scalar actually registered in `TripshotJacksonModule` (§7.3: `if (rawClass == LocalDateTime.class) return new LocalDateTime.StringDeserializer();`).

`com/tripshot/common/utils/LocalDateTime.java`:

```java
    public static final class StringDeserializer extends JsonDeserializer<LocalDateTime> {
        /* JADX WARN: Can't rename method to resolve collision */
        @Override // com.fasterxml.jackson.databind.JsonDeserializer
        public LocalDateTime deserialize(JsonParser jp, DeserializationContext ctx) throws IOException {
            Intrinsics.checkNotNullParameter(jp, "jp");
            Intrinsics.checkNotNullParameter(ctx, "ctx");
            JsonNode jsonNode = (JsonNode) jp.getCodec().readTree(jp);
            if (jsonNode.isTextual()) {
                String strAsText = jsonNode.asText();
                Intrinsics.checkNotNullExpressionValue(strAsText, "asText(...)");
                List listSplit$default = StringsKt.split$default((CharSequence) strAsText, new char[]{'T'}, false, 0, 6, (Object) null);
                if (listSplit$default.size() != 2) {
                    throw JsonMappingException.from(jp, "expecting single T delimiter");
                }
                try {
                    LocalDate localDateFromString = LocalDate.fromString((String) listSplit$default.get(0));
                    try {
                        TimeOfDay timeOfDay = TimeOfDay.parse((String) listSplit$default.get(1));
                        Intrinsics.checkNotNull(localDateFromString);
                        Intrinsics.checkNotNull(timeOfDay);
                        return new LocalDateTime(localDateFromString, timeOfDay);
                    } catch (IllegalArgumentException unused) {
                        throw JsonMappingException.from(jp, "expecting time");
                    }
                } catch (IllegalArgumentException unused2) {
                    throw JsonMappingException.from(jp, "expecting date");
                }
            }
            throw JsonMappingException.from(jp, "expecting string");
        }
    }
```

Split on a single literal `T`; the left half goes through `LocalDate.fromString` (strict `YYYY-MM-DD`) and the right half through the **lenient** `TimeOfDay.parse` (which accepts `9`, `09:30`, `09:30:00`, `9:30pm`, and strips whitespace). No timezone or offset is present or accepted.

`LocalDateTime` is a Kotlin class with **no** `@JsonValue`, no `@JsonProperty`, and no registered serializer. Given the mapper's `Visibility.NONE`, serializing a `LocalDateTime` would emit `{}` (allowed only because `FAIL_ON_EMPTY_BEANS` is `false`). It appears to be a response-only type.

### 7.10 Other `@JsonValue` scalars (not exhaustively documented)

Beyond the above, `@JsonValue` appears on ~35 classes under `com/tripshot/common/utils/` and `com/tripshot/common/models/`. The large majority are string-valued enums (`DayOfWeek`, `AppType`, `VehicleType`, `RideDirection`, `AlertPriority`, `NotificationMethod`, `AuthMethod`, `BadgeType`, `StopByRequestStatus`, `PointOfInterestType`, `Namespace`, `V2Namespace`, …) plus the composite-key types documented above. They are not registered through `TripshotJacksonModule`; each carries its own annotations.

## 8. Things not found / not determinable from the decompile

- **No `AndroidManifest.xml`** was present under `nocommit/jadx/` (only `resources/` and `sources/` directories; no manifest file found). The runtime `packageInfo.versionName` / `packageInfo.versionCode` used to build `X-Tripshot-Build` could therefore only be cross-checked against `BuildConfig`, not against the manifest itself.
- **No `TimeOfDay` serializer or deserializer is registered in `TripshotJacksonModule`** — the wire format comes purely from `@JsonValue` / `@JsonCreator` on the class. Same for `LocalDate`, `RgbColor`, `RideId` and `ShiftId`. Only `LocalDateTime` is registered there among scalar types.
- **No serializer exists for `LocalDateTime`** anywhere in the decompiled sources; only `LocalDateTime.StringDeserializer`.
- **`X-Auth-Type` is never read by any interceptor** in the decompiled sources; its only occurrences are the `@Headers` declarations on `TripshotService` methods, so its meaning is server-side and could not be determined from the APK.
- **The set of `X-Timeout` values is exactly `30` and `120`**; no other values appear.
