---
id: api.discovery
title: Instance discovery and base-URL resolution
kind: discovery
apk_refs:
  - path: com/tripshot/android/rider/InstanceActivity.java
    symbol: discoverService
    sha256: 0d61d3f53c0e810787195d313071e6a065710a7648dd41c2425c1e5ffaef845a
  - path: com/tripshot/android/utils/BaseUrlInterceptor.java
    symbol: update
    sha256: d92192f0ce066aab3dd9ff81473bfd5293e7f53556f588268b181701faf04fa8
  - path: com/tripshot/android/models/DiscoveredService.java
    symbol: apiBaseUrl
    sha256: 9ed76c6f7887d96ea80f5d4df3592b04e002c0fb4dbb66f560efb6f912d2878d
  - path: com/tripshot/common/models/AppType.java
    symbol: RIDER
    sha256: 8391ce503b744a40b4011154d7b0a3dadde0f66938f57271b9e8a20972c74828
depends_on: [api.transport, api.endpoints.public]
---

# Instance discovery

A TripShot deployment is an **instance** (a tenant). Before any transit data can be
requested, the client must resolve which instance the user wants and which API host
serves it. This is the only bootstrap path, and it is fully unauthenticated.

## Step 1 — enumerate advertised instances

```java
@GET("/v1/global/advertisedInstance")
Observable<List<Instance>> getPublicInstances(@Query("appType") String str);
```

`appType` comes from the `AppType` enum's wire name, not the constant name:

```java
public enum AppType {
    RIDER("RiderApp"),
    ADMIN("AdminApp"),
    SIGNAGE("Signage"),
```

So the rider app sends `?appType=RiderApp`. This request goes to the **default** host
(`https://api.tripshot.com`) because no instance is selected yet.

Each element carries `instanceId`, `name`, `displayName`, `advertisedNames`,
`secondaryNames`, and `baseLocation`. The instance targeted by this repo:

| Field | Value |
|---|---|
| `instanceId` | `526` |
| `name` | `UofR` |
| `displayName` | `University of Rochester Shuttle` |
| `secondaryNames` | `["University of Rochester"]` |
| `userAllowedAuthMethods` | `[]` |

`userAllowedAuthMethods: []` means this instance offers **no rider login at all** —
there is no authenticated mode to stay out of.

## Step 2 — resolve the API base URL

```java
@GET("/v1/global/discovery")
Observable<DiscoveredService> discoverService(@Query("name") String str);
```

`DiscoveredService` carries `apiBaseUrl` and `oidcRedirectHostname`.

The response may be **404**, which is not an error. `InstanceActivity` wraps the call
in `RxFunctions.map404ToAbsent` and falls back to the compiled-in default:

```java
this.instanceSubscription = RxFunctions.map404ToAbsent(this.tripshotService.discoverService(this.instance)).cache().doOnNext(new Consumer<Optional<DiscoveredService>>() {
    public void accept(Optional<DiscoveredService> optional) {
        boolean zIsPresent = optional.isPresent();
        InstanceActivity instanceActivity = InstanceActivity.this;
        if (zIsPresent) {
            instanceActivity.baseUrlInterceptor.setBaseUrl(optional.get().getApiBaseUrl());
```

```java
        } else {
            instanceActivity.baseUrlInterceptor.setBaseUrl(BuildConfig.BASE_URL);
```

`GET /v1/global/discovery?name=UofR` returns **404**, so `UofR` resolves to the
default host `https://api.tripshot.com`. This is normal, not a misconfiguration.

## Step 3 — name-derived host override

Independently of discovery, `BaseUrlInterceptor.update()` maps certain instance-name
patterns onto dedicated hosts:

```java
    public void update(String str) {
        String lowerCase = str.toLowerCase();
        if (lowerCase.startsWith("msft-us-stage") || lowerCase.startsWith("microsoft-us-stage") || lowerCase.equalsIgnoreCase("microsoft training")) {
            setBaseUrl("https://microsoft-us-stage.tripshot.com");
            return;
        }
```

```java
        if (lowerCase.endsWith("-emea")) {
            setBaseUrl("https://apple-emea.tripshot.com");
        } else if (lowerCase.endsWith("-apac")) {
            setBaseUrl("https://apple-apac.tripshot.com");
        } else {
            setBaseUrl(this.defaultBaseUrl);
        }
    }
```

`UofR` matches no prefix or suffix rule, so it takes the `else` branch — the default
host again, agreeing with Step 2.

## Resolved bootstrap for this repo

| Step | Call | Result |
|---|---|---|
| 1 | `GET api.tripshot.com/v1/global/advertisedInstance?appType=RiderApp` | `instanceId=526`, `name=UofR` |
| 2 | `GET api.tripshot.com/v1/global/discovery?name=UofR` | `404` → fall back to default |
| 3 | `BaseUrlInterceptor.update("UofR")` | no rule matches → default |
| — | **Effective base URL** | `https://api.tripshot.com` |
| — | **Header sent thereafter** | `X-Instance-Id: 526` |

## Region

Instance-scoped endpoints take a `regionId`. `GET /v1/region` is **not** a `/p/`
endpoint, so the region list is not fetched. The region UUID is instead read off
public payloads that already embed it (`Stop.regionId`, `Route.regionId`):

| Instance | regionId |
|---|---|
| `UofR` | `ca558ddc-d7f2-4b48-9cac-deea1134f820` |
