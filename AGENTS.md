# AGENTS.md

Instructions for AI agents working in this repository. Read this before
changing anything.

## What this is

A Home Assistant integration that measures per-stop schedule adherence for a
TripShot transit route, plus the reverse-engineering notes it was derived from.

Two properties make this repo unusual, and both are load-bearing:

1. **Every API fact is derived from a decompiled Android client**, written up in
   `docs-apk/`, with each claim citing the symbol it came from.
2. **Code cites those docs inline**, and a tool checks the whole chain — APK
   symbol → doc → source file — and fails on drift.

Do not break either. If you learn something new about the API, document it in
`docs-apk/` with a citation *and then* use it.

## Start here

```bash
python3 -m venv .venv
.venv/bin/pip install pytest pytest-homeassistant-custom-component
.venv/bin/python -m pytest tests/ -q     # 398 tests
python3 tools/derive.py                  # graph + drift check, must say "no drift"
```

`docs-apk/graph.json` is generated and gitignored — run `tools/derive.py` first,
then read it to see how docs, evidence and code connect.

## Hard rules

- **Public endpoints only.** Only paths containing `/p/`, plus the `/v1/global/`
  discovery endpoints. Everything carrying `@Headers({"X-Auth-Type: user"})` in
  the decompiled client is out of scope.
- **Never construct a credential.** `api.py` has no code path that can emit an
  `Authorization` header. Keep it that way. No login, signup, OIDC or SAML.
- **Do not use the vendor's adherence verdicts.** `expectedArrivalTime`,
  `lateBySec`, `stopStatus` and `RideState` are deliberately unparsed —
  adherence is computed here from the published schedule and observed
  positions. This is a product decision, not an oversight.
- **`custom_components/tripshot_tracker/brand/` is outside the MIT grant.** It
  reproduces TripShot's icon so Home Assistant shows the right one; those files
  belong to TripShot, Inc. The carve-out is stated in `LICENSE` and explained
  in `NOTICE`. Regenerate with `tools/make_brand.py` (needs the extracted APK
  resources); do not relicense them, and keep the carve-out accurate if the
  brand folder changes.
- **`nocommit/` is gitignored scratch** holding the APK, its decompilation and
  captured responses. Never commit anything from it. Never move a captured
  response into the repo except as a trimmed fixture under `tests/fixtures/`.
- **Do not weaken a test to make it pass.** Several tests exist because a real
  bug got past review here; the list is below.

## Layout

```
custom_components/tripshot_tracker/   the integration
  const.py         pure: constants and config keys
  locality.py      pure: geo + time reductions
  schedule.py      pure: timetable -> physical stop visits
  tracker.py       pure: sticky state machine + counters
  observations.py  pure: bus/stop joins, schedule validation
  models.py        pure: live-feed parsing
  endpoints.py     pure: request shapes
  overrides.py     pure: hard-coded timetable corrections
  api.py           aiohttp client
  coordinator.py   polling, wiring
  sensor.py        entities
  config_flow.py   setup + options
  diagnostics.py   downloadable dump
docs-apk/          derived documentation (see its README)
tools/derive.py    graph + drift detection
tests/             see Testing
examples/          sample automations + how to install them
nocommit/          gitignored scratch
```

The eight modules marked *pure* import neither Home Assistant nor aiohttp, and
`tests/test_layering.py` enforces it — including that the list itself stays
complete. Keep it that way: it is what makes the logic testable without a Home
Assistant install. If you need HA inside one of them, the logic belongs in
`coordinator.py` or `sensor.py` instead.

## The derivation contract

A doc in `docs-apk/` carries YAML frontmatter:

```yaml
---
id: semantics.time-locality
title: ...
kind: semantics
apk_refs:
  - path: com/tripshot/common/models/ScheduledStop.java   # under nocommit/jadx/sources/
    symbol: waitTimeSec                                   # literal string in that file
    sha256: <filled by tools/derive.py>
depends_on: [schedule.visits]
---
```

Code cites a doc, optionally a section:

```python
# doc: semantics.time-locality#priming — the first cycle only adopts
# what it finds, so a restart mid-dwell cannot double-count an arrival.
```

Sections declare anchors with `<!-- anchor: priming -->` under the heading —
anchors rather than heading text, so retitling does not break a citation while
deleting does.

After editing a doc's citations: `python3 tools/derive.py --update-hashes`, and
**read the diff it prints**. A hash moving means the cited APK code changed,
which is the moment to check whether the doc is still true.

`tools/derive.py` fails on: a missing file or symbol, a changed hash, an unknown
`depends_on` id, a citation to a doc or anchor that does not exist, duplicate
ids or anchors, and duplicate `## N.` section numbers.

## Testing

Two suites, one command:

- **Logic** (`test_locality`, `test_schedule`, `test_tracker`,
  `test_observations`, `test_models`, `test_endpoints`, `test_layering`,
  `test_static`) — needs only `pytest`.
- **Wiring** (`test_ha_setup`, `test_ha_event`, `test_api_http`,
  `test_config_flow`, `test_coordinator_paths`, `test_entity_lifecycle`,
  `test_diagnostics`, `test_config_schema`) — needs
  `pytest-homeassistant-custom-component`.

Coverage is gated at 90% in CI. That floor exists because a NameError shipped
in the event-firing path: the logic tests stopped at the tracker returning a
verdict and the setup tests stopped at entities existing, so nothing ever
executed the line. **A runtime path with no test is how bugs leave this
repo** — if you add one, execute it.
  `tests/conftest.py` binds the package as a synthetic `tsx` module so the pure
  modules import without Home Assistant.
- **Wiring** (`test_ha_setup`) — needs
  `pytest-homeassistant-custom-component`. Sets up a real config entry and
  checks entities exist, are attached to devices, hang off the route device,
  are named as expected, and that **Home Assistant logs no deprecation
  warnings**. Skipped cleanly if the plugin is absent.

`tests/test_schedule.py` transcribes the operator's published timetable and
asserts the derived visits reproduce it. That timetable is the source of truth;
the API is trusted only insofar as it matches. Do not edit those tables to make
a test pass.

## Before you finish

```bash
.venv/bin/python -m pytest tests/ -q     # all pass
python3 tools/derive.py                  # "no drift", exit 0
.venv/bin/python -m compileall -q custom_components/
```

If you changed a doc's citations, also run `--update-hashes` and review the
diff. If you changed anything user-facing, update `README.md`, and check the
counts quoted there still match.

## Bugs found here, and what now guards them

Each of these was found during development and has a test pinning it. They are
worth reading because they show the shape of mistake this codebase invites.

| What broke | Why | Guard |
|---|---|---|
| Setup failed with "no scheduled service" | The client pins `withScheduledRides`/`embedStops`/`withRoutes` **inside the Retrofit path**; sending the bare path returns HTTP 200 with a hollow payload | `test_endpoints.py`, plus a loud error when `ViaStop.stop` arrives as a string |
| One arrival counted four times | A vehicle is attached to every ride in its block | gate on `RideState.Active`, `test_observations.py` |
| One arrival counted twice | A one-poll feed dropout deleted the latch, which was then recreated | grace-based expiry, `test_tracker.py` |
| Adherence windows inverted twice a year | Arithmetic on a `ZoneInfo` datetime is wall-clock, so a window spanned −3000 s across a DST boundary | instants stored in UTC, `TestDaylightSaving` |
| Integration would not load at all | `async_timeout` is not a Home Assistant dependency | stdlib `asyncio.timeout` |
| Weekend install failed setup entirely | A day the route does not run returns an empty bundle, which was treated as an error | `stops_only()`, `TestNoServiceDay` |
| Entity devices about to stop working | `via_device` in `DeviceInfo` is deprecated | explicit route device + `via_device_id`, `test_ha_setup.py` |
| Automations never fired | `CountedVerdict.is_arrival` called a deleted `_is_arrival`, so every verdict raised NameError *after* bumping the counter — counters rose, no event ever reached the bus | `test_ha_event.py` drives a real visit and captures the bus; `test_static.py` runs pyflakes |

Two general lessons from that list: **the API answers HTTP 200 for several
distinct failures**, so check the shape of a response and not just its status;
and **verify against a running system rather than by reading code** — most of
these were found by real traffic or a real Home Assistant, not by inspection.

## Judgement calls

Where the APK did not settle an answer, the reasoning is recorded next to the
thing it governs rather than in a separate list — the derivation-strength notes
in `docs-apk/45-schedule-visits.md`, the grace rationale in
`docs-apk/50-semantics-time-locality.md#grace`, and the debounce trade-off in
`docs-apk/51-semantics-geo-locality.md#debounce`.

If you make a similar call, document it the same way: beside the code or doc it
affects, saying what was inferred and what the evidence for it was.
