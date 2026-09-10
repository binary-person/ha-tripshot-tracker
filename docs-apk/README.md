---
id: docs.index
title: docs-apk index and derivation model
kind: meta
apk_refs: []
depends_on: [apk.provenance]
---

# docs-apk

Everything here is derived from one APK — `TripShot_127_APKPure.apk`, hashed in
[`00-provenance.md`](00-provenance.md). No vendor documentation was consulted.

## Pages

| Page | id | What it settles |
|---|---|---|
| [`00-provenance.md`](00-provenance.md) | `apk.provenance` | which artifact, which tool, citation convention |
| [`10-transport.md`](10-transport.md) | `api.transport` | base URL, headers, timeouts, Jackson wire formats |
| [`20-discovery.md`](20-discovery.md) | `api.discovery` | instance list → base URL → region |
| [`30-endpoints-public.md`](30-endpoints-public.md) | `api.endpoints.public` | the unauthenticated endpoint catalog |
| [`40-models-schedule.md`](40-models-schedule.md) | `api.models.schedule` | Route, Stop, Via, ScheduledRide, Shape |
| [`41-models-live.md`](41-models-live.md) | `api.models.live` | V2LiveStatus, V2Ride, the five stop-status variants |
| [`45-schedule-visits.md`](45-schedule-visits.md) | `schedule.visits` | turning stop entries into physical visits; validation vs the published timetable |
| [`50-semantics-time-locality.md`](50-semantics-time-locality.md) | `semantics.time-locality` | the two buffers, and what early / on-time / late mean |
| [`51-semantics-geo-locality.md`](51-semantics-geo-locality.md) | `semantics.geo-locality` | our geofence, and what at-stop means |
| [`60-request-plan.md`](60-request-plan.md) | `integration.request-plan` | which calls the integration makes, and how often |

## Derivation model

Three kinds of node, two kinds of edge:

```
  APK symbol  ──derived_from──  doc  ──depends_on──  doc
                                 ▲
                                 └──cites──  source file
```

* A doc declares its evidence in frontmatter `apk_refs` (`path` + `symbol`) and
  its prerequisites in `depends_on`.
* Integration code cites a doc with `doc: <id>` in a comment or docstring, so
  the reasoning behind a line of code is one grep away.
* A citation may name a section: `doc: <id>#<anchor>`. Sections declare stable
  anchors with `<!-- anchor: name -->` under the heading — anchors rather than
  heading text, so retitling a section does not break citations while deleting
  one does.

```python
# doc: semantics.time-locality#priming — the first cycle only adopts
# what it finds, so a restart mid-dwell cannot double-count an arrival.
```

`path` is relative to `nocommit/jadx/sources/`. `symbol` is a string that
literally occurs in that file — a class, method, or field name. Symbols rather
than line numbers, because jadx emits interface members alphabetically and line
numbers move on re-decompilation while symbols do not.

## One command

```console
$ python3 tools/derive.py
graph -> docs-apk/graph.json
  12 docs, 88 apk refs, 15 code files, 153 edges
  no drift
```

Writes `docs-apk/graph.json` — nodes, edges, and the counts above — so an agent
can load one file and see how every claim connects to its evidence and to the
code that relies on it. Exit status is non-zero if anything is wrong.

`graph.json` is **generated and gitignored**. Run the command above before
reading it: a committed copy could silently disagree with the tree it claims to
describe, which is the exact failure this tool exists to catch.

### What it catches

| Check | Reported as |
|---|---|
| a cited file or symbol no longer exists in the APK | `DRIFT missing-file` / `missing-symbol` |
| the cited code changed since the hash was recorded | `DRIFT` with both hashes |
| `depends_on` names an unknown doc id | `PROBLEM` |
| code cites a doc id that does not exist | `PROBLEM` |
| duplicate or missing doc ids, malformed frontmatter | `PROBLEM` |
| code cites a section anchor that no longer exists | `PROBLEM`, listing the anchors that do |
| a doc has two `## N.` sections with the same number | `PROBLEM` — catches a section inserted without renumbering |
| a doc declares the same anchor twice | `PROBLEM` |
| a doc no code relies on | a `note:` line, not a failure |

Each `apk_refs` entry stores a `sha256` over just the lines of the cited file
that mention the symbol. Hashing the matching lines rather than the whole file
means unrelated churn in a 1,000-line decompiled class does not cause false
alarms, while a change to the cited construct does.

### Re-hashing after a deliberate change

```console
$ python3 tools/derive.py --update-hashes
```

Recomputes and writes back every `sha256`. Run it when you intentionally
re-point a citation — and read the diff, because that is the moment a real
behavioural change would otherwise be rubber-stamped.

### On a fresh clone

`nocommit/` is gitignored, so the APK and its decompilation are absent. The tool
reports those refs as `unverifiable` and still emits the graph; structural
checks (`depends_on`, code citations, duplicate ids) run regardless. To restore
full verification, put the APK back at `nocommit/` and re-run the jadx command
in [`00-provenance.md`](00-provenance.md).
