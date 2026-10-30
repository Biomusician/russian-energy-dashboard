# Global architecture (iteration 14)

How the dashboard went from one theatre to six monitored systems without moving the theatre.
Read with `GLOBAL_METHODOLOGY.md` (what may be computed and compared) and
`COUNTRY_ONBOARDING.md` (how to add a country).

## The one-paragraph version

A **system** is what the dashboard monitors as a unit. The original one is the
**Russia, Belarus & Crimea theatre** and it is unchanged: same pipeline, same paths, same index,
same URLs. Five **country systems** (Canada, China, India, Saudi Arabia, United States) sit
beside it, each built from curated per-country sources into its own payload directory. One
registry (`pipeline/systems.py`) says which systems exist; one generated manifest
(`global/manifest.json`) tells the frontend. The frontend holds no country constants. No country
system has an index this iteration, and the payloads say so with `null`, never `0`.

## Data layout

```
data/
  candidates/<id>.json            research queue: NOT committed, never read by the build
  candidates/<id>_profile.json    lane-compiled context (copied into curated by hand)
  candidates/README.md            why, and the queue's disposition counts (committed)
  curated/                        theatre sources, unchanged
  curated/systems/
    inclusion_threshold.json      the versioned major-disruption standard
    <id>/system.json              sector states + reasons, reporting environment,
                                  geography rulings, sources, research gaps
    <id>/profile.json             sourced energy-system context
    <id>/events.json              REVIEWED events (written by scripts/import_candidates.py)
    review_edits.json             reviewer edits the import applies, each with its reason
  processed/                      theatre payload root, unchanged
  processed/global/manifest.json  every system: id, name, root, evidence readiness, headline
  processed/global/world.geojson  light admin-0 world for the home page
  processed/systems/<id>/         system.json, events.json, regions.geojson
web/public/data/                  mirror of processed/, subtrees included
```

**Why the theatre did not move.** `data/processed/` is the theatre's root. Hundreds of tests, the
iteration-13 staging contract and every link shared since iteration 8 assert on it. Moving it
would have bought symmetry and risked all of that. `systems.root("ru")` is `""`.

## The pipeline

`pipeline/run.py` builds the theatre exactly as before, then calls
`build_systems.build(snapshot)`, then mirrors everything once.

`pipeline/build_systems.py`, per country:

1. reads `system.json`, `profile.json`, `events.json`;
2. takes first-level units from Natural Earth 10m admin-1 (default edition: line of actual
   control), applying the 2023 ISO code changes for India and adding Hong Kong and Macau to
   China from admin-0;
3. **validates** — and fails the build on — a missing sector state, a state claiming a value
   (SCORED/EXPERIMENTAL) when nothing is computed, an event in a unit the map cannot draw, an
   unlabelled cause or class, an unsourced or unreviewed event, an event dated after the build;
4. emits `system.json` (with `index: null`, `headline: null`, `no_index_reason`),
   `events.json` (whitelisted fields only, no coordinates) and `regions.geojson` (unit polygons
   with a `recorded_events` count; disputed, unassigned units carry `null`).

Then once: `global/world.geojson` and `global/manifest.json`.

**World map and Crimea.** Natural Earth's admin-0 Russia polygon contains Crimea. The world layer
is therefore built with Russia drawn from its admin-1 units and Crimea and Sevastopol as their
own features: `a3: "UKR"`, `status: "occupied"`. A test fails if anything drawn at Crimea's centre
is labelled Russian.

**Identity.** `pipeline/ids.py`: short ids unchanged; long ids keep a readable prefix plus a hash
of the whole slug (no more silent merges at 60 characters); the one id published under the old
rule is grandfathered; cross-system identity is `<system>:<id>`; collisions go to
`parser_warnings`.

## The review gate and the red-team corrections

`scripts/import_candidates.py` is the only path from a research queue to a published event. It
applies `review_edits.json` (exact-text replacements with reasons; a stale edit fails the import
rather than silently publishing what it was written to remove), then holds any record that is
not lane-accepted, has no source URL, lies outside the system's geography, or trips the scope
scan (coordinates, distances, dependency and vulnerability language, defence and weapon detail,
cyber technique). A held record is printed for a person to read; nothing is auto-fixed.

The final safety red team found, and this iteration fixed: a substation named as a capital
city's in-feed with the size of the dependency; pipeline and plant placements below admin-1;
network inventories and a cascading-failure description in sensitive areas; "largest facility"
framing; a Saudi per-refinery capacity table shipped during an attack campaign on those plants;
and a committed candidate queue that, read per facility, recorded which attacks had no reported
effect. The queue files are now uncommitted, the table is gone, and each text fix is a recorded
edit. The analytic-honesty red team found that every kind of recovery evidence rendered as
"evidence found", that a missing `opened` flag counted as a source read, and that a region view
could say "none found" beside a multi-region event naming that region; all three are fixed and
tested.

## The artifact contract

Everything above is declared in `pipeline/artifacts.py` (`SYSTEM_PAYLOADS`, `GLOBAL_PAYLOADS`),
which feeds `required_paths()`. The refresh's staging list, `verify_staged.py` and the tests read
it. There is no second list. The mirror copies `global/` and `systems/` as whole trees and prunes
them, so a payload the build stops producing cannot linger.

## The frontend

```
main.tsx -> Root.tsx -> useRoute()
   home     -> global/GlobalHome.tsx      (manifest + world.geojson only)
   theatre  -> App.tsx  (lazy chunk)       the original dashboard
   country  -> global/CountryView.tsx (lazy chunk, keyed on id)
```

**Routing (`global/router.ts`).**

| URL | Opens |
|---|---|
| bare (`/`) | global home |
| `?sys=ru…` | theatre |
| any theatre parameter, no `sys` (`?m=ev`, `?r=RU-PER`, …) | theatre — every pre-14 link that carried view state (a bare pre-14 link now opens the home) |
| `?sys=<country>[&r=<code>]` | that country (validated against the manifest by the view) |

The theatre now writes `sys=ru` at the front of its own URL, so its untouched default view no
longer reloads as the home page. Navigation between systems is `pushState`, so Back walks the
trail; within a view, state changes use `replaceState` as before.

**Loading.** The home fetches the manifest and the world layer. A country view fetches its three
files with an `AbortController`; switching aborts the old load, and the view is keyed on the id,
so a late response for the country just left cannot land on the one just opened (tested with a
3-second delayed response). A failed payload shows an error inside that view only; the picker
and every other system keep working (tested with a forced 500).

**Bundles.** The theatre (235 kB) and the country view (14 kB) are separate chunks; the home page
downloads neither. MapLibre (1 MB) is shared and loaded by whichever view draws a map.

**As-of builds.** A historical `--as-of` build reconstructs each country's record as of that date (later events are excluded and counted in `excluded_after_as_of`); only an event dated after the actual build day fails the build. The frozen 2026-08-28 regression found the original refusal.

**What the views refuse.** The home shows no counts and no scores side by side, and colours every
monitored system the same. A country view puts "No index" where the theatre shows its ESDI, with
the reason. Its choropleth classes come from that country's own range (never a scale shared across countries), and the legend prints the numbers and says the colour is recorded events, not a rate of disruption. Recovery is labelled by kind (full restart, partial, service restored, estimate, nothing lost). The event record's review date is shown apart from the rebuild date, with a stale notice past a declared limit, and the eight-point onboarding gate is published with each item's status. The PNG export draws the count, reporting environment, colour key and caveats into the image.

## Tests

- **Python** (`tests/test_pipeline.py`, "Iteration 14" sections): registry order, manifest
  carries no rankable figure, no country score, every sector stated, events whitelisted /
  region-scoped / sourced / scope-scanned, counts consistent, every unit present (incl. Wyoming,
  Colorado, the 2023 Indian codes), China excludes Taiwan, Crimea never Russian on the world
  map, antimeridian-safe bounds, the build never reads the candidate queue, the build refuses a
  sector claiming a score, the import gate holds what it should. The served-data safety gates now
  recurse into the subtrees.
- **Browser** (`web/e2e/global.e2e.ts`): the home page, all five countries, deep links, the
  picker across all six systems with Back, the race, error containment, PNG per country,
  print/PDF for all seven pages, two responsive sizes, and three map goldens (win32 only).
- **Unit** (`web/src/global/router.test.ts`): the routing table above.
