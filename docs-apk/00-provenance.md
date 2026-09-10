---
id: apk.provenance
title: APK provenance and decompilation method
kind: meta
apk_refs:
  - path: com/tripshot/android/rider/BuildConfig.java
    symbol: VERSION_NAME
    sha256: 8dc7c129abdfb73671fe6a0b99ce8fcb197351abd50cd602f511004f06c2f204
  - path: com/tripshot/android/rider/BuildConfig.java
    symbol: APPLICATION_ID
    sha256: e7c9b95b7751df9eb1290e19d3bca7a2cecafcb89420ea2fae976429db713360
depends_on: []
---

# APK provenance

Every factual claim in `docs-apk/` derives from this one artifact. Nothing here is
sourced from vendor documentation, GTFS feeds, or observation of the app at runtime.

| Property | Value |
|---|---|
| File | `TripShot_127_APKPure.apk` |
| SHA-256 | `2aaaf84dade2cdd414d67a01a738e99283c22701b4a2c3ce5db94638b22d3766` |
| Size | 50,633,330 bytes |
| `applicationId` | `com.tripshot.rider` |
| `versionName` | `127` |
| `versionCode` | `541` |
| Flavor | `tripshotProd` (`FLAVOR_brand=tripshot`, `FLAVOR_environment=prod`) |
| Build type | `release` |
| dex files | 9 (`classes.dex` … `classes9.dex`) |

```java
public static final String APPLICATION_ID = "com.tripshot.rider";
public static final String BASE_URL = "https://api.tripshot.com";
public static final String BUILD_TYPE = "release";
public static final String FLAVOR = "tripshotProd";
public static final int VERSION_CODE = 541;
public static final String VERSION_NAME = "127";
```

## Decompilation

```
jadx 1.5.6 -d nocommit/jadx --no-res --show-bad-code -j 8 TripShot_127_APKPure.apk
```

Produced 26,753 `.java` files. jadx exits `3` (partial decompilation failures in
unrelated third-party code); no failure affected any file cited by these docs.

The app is **not obfuscated** — original package and member names survive under
`com.tripshot.{common,android,rider}`, which is why field-level citation is possible.

## Scratch layout (gitignored)

`nocommit/` holds everything that must not be committed: the APK itself, the jadx
output, extracted dex, and captured API responses used to cross-check the models.

```
nocommit/
  TripShot_127_APKPure.apk
  jadx/sources/com/tripshot/...   <- all apk_refs paths are relative to jadx/sources/
  extract/                        <- raw classes*.dex
  *.json                          <- captured public responses (cross-check only)
```

Because `nocommit/` is gitignored, a fresh clone cannot verify APK hashes. The
derivation tool reports those refs as `unverifiable` rather than failing — see
[`README.md`](README.md).

## Citation convention

`apk_refs[].path` is always relative to `nocommit/jadx/sources/`.
`apk_refs[].symbol` is a string that literally occurs in that file (a class, method,
or field name). Line numbers are deliberately **not** used as anchors: jadx emits
interface members in alphabetical order, so line numbers are unstable across
re-decompilation while symbols are not.
