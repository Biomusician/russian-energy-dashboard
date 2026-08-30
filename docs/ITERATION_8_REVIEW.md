# Iteration 8 review — infrastructure symbology, trend views & analyst-workflow UX

A **feature / UX** iteration: make the dashboard faster to read, easier to navigate, and more
useful for daily analysis **without diluting its evidence discipline**. Visualisation, navigation,
derived comparison and presentation only — no change to what the data means or how it is scored.

This document covers both the development pass and the **release gate** that followed it. The
gate found one architectural mistake (a frozen payload staged as the release build) and one real
defect (a structurally incomplete recovery count); both are described in full below rather than
quietly fixed, because both were the kind of error that looks like working software.

---

## 1. Production date vs frozen reference — the distinction that governs every number here

Two builds are legitimate and **deliberately produce different headlines**:

| Build | Command | as_of | ESDI | Purpose |
|---|---|---|---|---|
| **Production / release** | `python -m pipeline.run` | build day (2026-08-30) | **17.86** | What ships. Moves with time decay. |
| **Regression / comparison** | `python -m pipeline.run --as-of 2026-08-28` | 2026-08-28 | **18.49** | Frozen methodology comparison across iterations. |

The gap is **time decay over two days**, not a defect and not a scoring change.

**What went wrong mid-iteration.** To keep the frontend work provably score-neutral, the frozen
build was committed *as the release payload*. That is wrong: the frozen date exists only for
apples-to-apples comparison, and shipping it would have frozen the live dashboard at a stale date
and misreported the present indefinitely. The release payload is now the current-date build.

**Frozen-score invariant, proven.** Iteration-8 code, run at the frozen date, reproduces
iteration 7's frozen headline exactly:

```
iteration 7 frozen (2026-08-28)  ESDI 18.49   refining 33.35  transmission 21.37  oil_logistics 9.50
iteration 8 frozen (2026-08-28)  ESDI 18.49   refining 33.35  transmission 21.37  oil_logistics 9.50
```

Re-verified after every pipeline change in the gate, including the new recovery-evidence dataset —
which is why that addition is safe to call presentation-only. The comparison run was reverted and
the release tree left holding the current-date build (verified: `git status` clean, snapshot
`as_of` 2026-08-30).

**Guard against a repeat.** `test_release_payload_is_a_current_date_build_not_a_frozen_reference`
fails the suite when the committed payload's `as_of` lags its `build_time` by more than a day —
the signature of a frozen build — with a message naming the fix. A developer can no longer merge a
regression payload as the release build by accident. (Confirmed it actually fires: it failed on the
frozen tree and passes on the production tree.)

`docs/CURRENT_STATE.md` is regenerated from the production payload and reports **as_of 2026-08-30,
ESDI 17.86**, keeping the iteration-8 wording fixes.

---

## 2. Recovery-evidence completeness — a real defect, found by the gate

**The claim under audit:** "What changed" derived its recovery count from
`snapshot.live_disruptions[].recovery.observed_date`.

**The finding: that source is structurally incomplete for this question.** `live_disruptions` is a
CURRENT-IMPAIRMENT view — it contains only facilities whose disruption weight is still `> 0`, and
is truncated to the top 80 by weight. A facility that has **fully recovered** decays to zero weight
and drops out entirely. So the panel was blind to precisely the episodes it existed to report:

```
observed-restoration episodes in the corpus : 9
                    visible in live_disruptions : 1     <- what the panel could see
                    resolved_count in that array : 0     <- by construction
```

A convenient "1 restoration" answer looked like working software. It was a 1-of-9 undercount.

**The fix.** The pipeline now emits `snapshot.recovery_events`: the complete dated
restoration-evidence log, built from the same `recovery_by_incident` map that `recovery_stats`
already counts, deduplicated by (episode, date-kind) on the same principle. **25 events** now
surface where 1 did. It is presentation/data-access only — the frozen ESDI is unchanged at 18.49.

**A semantic trap handled explicitly.** The log holds 11 dated *observed restorations*, but
`recovery_stats.observed_restoration_episodes` is 9. Both are right; they answer different
questions. Two records carry a real restoration date while their duration is modelled or absent —
genuine evidence, but not a median sample. Each row therefore carries
`counts_toward_observed_episodes`, the UI reports both numbers ("N of these are a measured
restoration duration"), and a test asserts the counted subset reconciles exactly with
`recovery_stats`. "Evidence arrived" can never be read as "duration measured".

**Fixture coverage** (all five cases the gate required, plus boundaries):

| Case | Covered |
|---|---|
| A. live unresolved incident + new recovery observation | ✅ |
| B. **fully resolved** incident + new recovery observation | ✅ (the case the old source could not see) |
| C. old observation outside the window | ✅ |
| D. partial / service restoration | ✅ (labelled "partial restart", never a full restoration) |
| E. physical reconstitution | ✅ |

**Guards:** `test_recovery_events_is_complete_not_a_live_disruptions_subset` asserts the log is
strictly richer than anything `live_disruptions` could expose, is deduplicated, sorted, and
reconciles with `recovery_stats`; `test_recovery_events_carry_no_location_beyond_admin_region`
keeps the log free of coordinates.

**Deploy-window honesty.** A CDN edge can briefly serve a payload predating `recovery_events`.
That renders as "Restoration evidence is unavailable in this data payload — not zero" with an
em-dash count, never as `0`. Unknown is not none (modelling rule 7).

---

## 3. ESDI-delta window semantics — what "30-day change" actually compares

The index series is **weekly**, so a "30-day change" can never be an exact 30-day observation.
`data.windowRef()` resolves the request and reports the truth:

```
requestedWindowDays   30              90
actualComparisonDays  35              91          <- the real span, at the latest date
comparisonDate        the nearest EARLIER weekly step
comparisonStep        always <= the scrubber step  (no future leakage, by construction)
truncatedBySeriesStart  true when the series starts less than a window back
```

One helper backs **all four** change surfaces — the map choropleth, "What changed", the dossier
sparklines and the comparison tray — so they cannot disagree. The UI states the real span
("Actual comparison span: 35 days (asked for 30)") and the map legend and tray tooltips do the
same, instead of asserting an exact 30-day observation.

Tested at the latest date, a scrubbed historical date, near the start of the series (clamps and
flags truncation), at step 0, for out-of-range steps, and for **no future leakage at every step**.

---

## 4. "What changed" obeys the scrubber

Every window is half-open `(windowStart, scrubberDate]`, anchored on the timeline position, never
wall-clock now:

- new incidents, recovery evidence, and the ESDI delta all end at the scrubber;
- nothing dated after the scrubber can appear (asserted across the whole series);
- the window END is inclusive and the START exclusive, so adjacent windows never double-count;
- rows with a missing date are skipped rather than throwing.

**Consistency fix found while testing:** "What changed" read the raw corpus while every other view
(Recent tab, map, ribbon) reads the FILTERED set — so filtering the rail to refineries still
reported substation events. Both the event list and the recovery log now apply the active class
filter, threaded to the tabs as `TabProps.activeClasses`.

---

## 5. URL / deep-link state

Encoded: choropleth surface, activity window, timeline **date** (resolved via `stepFor`, so it
survives a rebuild that changes step counts), selected region, layer toggles, filter subsets,
comparison set, camera. Only non-default values are written, so an untouched dashboard keeps a
clean URL.

Hostile-input handling (all tested): unknown metric/activity/date → ignored; absurd zoom → clamped
to the map's real range (0–9); off-globe centre → clamped to valid lat/lon; non-numeric camera →
dropped; repeated compare list → de-duplicated then capped at 3; junk, empty, oversized and
`__proto__` keys → no throw. Applied at load: a deep-linked region that no longer exists is
dropped rather than left selected, and a filter subset that intersects to nothing falls back to
"all" rather than showing an unexplainable empty map.

**Scope:** the link vocabulary has no asset-position key at all — a selected asset is never
encoded by coordinates; only a region code and a camera frame exist.

---

## 6. Icon system

One registry (`src/icons.ts`) drives the map, the left-rail filter rows and the legend, so they
cannot drift. Grammar, one channel per meaning: **SHAPE** = infrastructure function, **COLOUR** =
class identity, **dashed FRAME** = administrative-region placement, **stacked backplate** =
several assets on one centroid. Disruption never enters the glyph; it stays on the region shading
and halo.

Icons rasterise **locally** (inline SVG → data-URI → canvas → `addImage`), so no glyph service,
sprite sheet or CDN is introduced. Declutter is deterministic via `symbol-sort-key` (class →
capacity/voltage → struck → precision) — display decluttering, never a target-value rank.

**Coverage and fallback (audited):** all 15 taxonomy classes and all 10 classes the build actually
renders as points have a deliberate shape; line-only classes (transmission, oil/gas pipelines)
carry legend glyphs. An unrecognised future class routes to a distinct `asset-unknown` id and
draws a **hollow diamond** — visibly a fallback, never another class's icon and never a silent
return to the old generic dot. `unknownPointClasses()` gives the signal, and a test asserts the
built dataset yields none.

---

## 7. Region-centroid collisions — corrected

**Audit:** of 35 curated region-precision assets, **14 sit on a centroid shared with another**,
across 9 colliding points — four LNG terminals land on one Leningrad point; three GPPs on one
Khanty-Mansi point. With collision declutter on, exactly one drew, so the map asserted a single
facility where the data holds several.

**Treatment:** one marker per centroid, carrying a "stacked cards" backplate that reads as
multiplicity, and the hover card and dossier sub-card **name every co-located asset** ("4 assets
share this administrative centroid — this marker stands for all of them, not one facility").
Hidden members stay in the source so their identity, selection and search remain addressable, and
selecting one highlights the marker actually drawn for it.

Members are **not displaced**. Jittering them into distinct pixels would fabricate geography the
dataset does not have — the opposite of what the precision model exists to protect.

---

## 8. Performance

| | main (before) | iteration 8 | delta |
|---|---|---|---|
| app JS | 286.98 kB (87.81 gz) | 319.16 kB (98.29 gz) | **+32.2 kB raw / +10.5 kB gz** |
| app CSS | 84.03 kB (13.30 gz) | 87.47 kB (13.90 gz) | +3.4 kB raw / +0.6 kB gz |
| maplibre vendor | 1053.01 kB | 1053.01 kB | unchanged |

The entire icon system, four trend surfaces, comparison tray, sparklines, search and URL state
cost **~10.5 kB gzipped**.

Initial data payload ~4.8 MB across 12 eager files, dominated by pre-existing geometry
(`assets_lines.geojson` 2.3 MB, `assets.json` 0.6 MB); rivers and the continental pipeline
networks (143 kB) stay lazy, loaded only on toggle. `snapshot.json` grew ~29 kB raw for
`recovery_events`.

**Icon rasterisation does no repeated work:** `prewarmIcons()` memoises a single module-scope
promise, so the rasterisation runs **once per page load** regardless of rerenders; the layer-adding
effect early-returns if the layers already exist; and the impossible stacked-but-not-region-placed
pairing is skipped (48 images instead of 64). Nothing calls `setStyle`, so registered images are
never discarded and re-registered.

---

## 9. Rivers — a real pre-existing defect, fixed

The `rivers` layer used `["zoom"]` nested inside a `case`. MapLibre **rejects** that, and
`addLayer` reports the error via the error event rather than throwing — so the layer was silently
absent and its toggle errored with "Cannot style non-existing layer". This shipped in iterations
5–7.

Proven against MapLibre's own style validator:

```
OLD (pre-fix)     : INVALID -> layers[0].paint.line-opacity: "zoom" expression may only be used
                               as input to a top-level "step" or "interpolate" expression.
FIXED (shipping)  : VALID
```

Reformulated as a top-level zoom `interpolate` with the per-feature reveal gate moved into the
stop outputs, preserving the intended behaviour (each river appears at its own scalerank-derived
zoom). No score or facet is affected — rivers are context geography and are never scored.

**Second defect fixed in passing:** `asset-symbols` had `minzoom: 3.4`, above the Full-AOI home
view (~z2.1), so the home view showed no infrastructure at all. Lowered to 2; collision declutter
keeps the wide view sparse.

---

## 10. Scope discipline

No coordinates, distances, ranges, bearings or routes in any card — enforced in one shared
component (`AssetDetail.tsx`) that both the map hover card and the dossier sub-card render
through, so they cannot diverge. No ranking of unstruck assets, no vulnerability score, no
distance-to-event, no prospective-target affordance. Search matches public names only and never
indexes or exposes a coordinate; picking a region-centroid asset is zoom-capped so it is never
framed as a precise fix.

The verbal invariants hold in UI copy: **region-centroid placement ≠ facility coordinate**, **map
visibility ≠ analytic inclusion**, **unknown ≠ zero**, **activity ≠ impairment**, **ESDI delta ≠
observed physical damage**, **Crimea's analytic inclusion ≠ a sovereignty statement**.

---

## 11. Independent UX / analytic red-team

An independent adversarial pass was run against the **production build**, with access to the
running app, the source and the shipped data. Initial verdict: **DO NOT SHIP — 4 DEFECT, 9
UX-AMBIGUITY.** Every finding was reproduced before being acted on. All defects and all
significant ambiguities are fixed; the four MINORs judged worth fixing were fixed too.

### Defects

| # | Finding | Disposition |
|---|---|---|
| 1 | The map's most-read line disclaimed **order-of-battle** concepts — "permanent and administrative basing", "no current unit positions, readiness" — vocabulary inherited from a sibling ORBAT project. It disclaimed things that do not exist in this product while omitting the two caveats that do. | **Fixed.** Rewritten in `MapPanel` and `Methodology` to the real boundary (centroid placement, modelled index, no undamaged-asset assessment). Verified no such word appears anywhere in the rendered UI. |
| 2 | The infrastructure-type filter did **not** apply to the exposure choropleth, so one screen asserted "Krasnodar · 0 events" beside "exposure 3.3". | **Fixed by disclosure.** ESDI is precomputed across all classes; recomputing it per filter would be a scoring change, which §1 forbids. The legend now states the index covers all classes and points at "Recorded events", which *does* follow the filter. |
| 3 | Shared-centroid representatives were `members[0]`, chosen before and independently of the class filter. Groups are class-mixed, so **both struck refineries** (Novoshakhtinsk, Orsk) drew as coal-terminal and gas-processing glyphs — and vanished entirely under a "refineries only" filter while their cards still promised a marker. | **Fixed.** The representative is now the most salient member *passing the active filter* (shared `assetPrio`). Regression-tested against the shipped data; verified live that the refinery draws under `?cls=refinery`. |
| 4 | The ribbon showed as-at-build recovery counts beside a time-scrubbed index with nothing to distinguish them — "18 events to date" next to "52 currently impaired". | **Fixed.** The three ribbon stats and the Overview row carry the existing amber `· current` marker plus a tooltip. |

### Ambiguities

| # | Finding | Disposition |
|---|---|---|
| 5 | The delta axis said "improved / worsened", and **a region with no new events always falls** because the index decays on a modelled half-life — so a month with four refinery strikes displayed as broad improvement. | **Fixed.** Relabelled "index fell / index rose"; the decay behaviour is stated in both the legend and the rail. |
| 6 | At the home view icons rendered ~6 px at 50% opacity, where shape, the dashed precision frame and the stack plate are all imperceptible — including the precision distinction the scope rules require. | **Fixed.** z2 size 0.26 → 0.42, opacity 0.5 → 0.75. |
| 7 | The stack backplate merged into one box at map sizes and read as a selection highlight. | **Fixed.** Offset widened to 4 units and filled with the page ground. |
| 8 | Shape and colour collisions: refinery vs gas processing (both banded columns); LNG vs oil terminal (washed-out snowflake, adjacent teals); three classes effectively invisible on the ground; substation and thermal in one amber family, with substations 73% of point assets. | **Fixed.** Gas processing redrawn as sphere + flare; LNG tank de-opacified with a heavier snowflake; contrast lifted 2.65–4.74 → 4.50–9.22 for the three dark classes; substation moved to the grid slate, 169° from thermal. |
| 9 | Search flew to **z7 on a region centroid**, asserting a precision the card denies and writing it into the shareable URL, where the qualifying card does not travel. | **Fixed.** Region-precision assets now frame their region bbox (verified z5.9). |
| 10 | The delta legend had no ticks, and "unchanged" was indistinguishable from "no events ever recorded" — both `±0.00`. | **Fixed.** Added ≤−3 / 0 / ≥+3 ticks and a hover line: "no recorded events here — nothing to change, not a measured zero". |
| 11 | Activity halos — the loudest mark on the map — had no legend entry and share the kinetic-strike red. | **Fixed.** Legend row added with the disambiguating sentence. |
| 12 | Camera controls occluded the scope note below ~1580 px viewport. | **Fixed.** Left-anchored and wrapping. |
| 13 | A flat 10 px hit target around ~1,900 assets tiled the AOI and stole every region hover, making the choropleth's own per-region values unreadable. | **Fixed.** Hit radius now scales with zoom (3.5 px at z2 → 10 px at z6). |

### Minors fixed

14 network preset framed to 145°E where the trunks were invisible (tightened, widths lifted);
15 rivers reveal interpolated *between* gated outputs so a river appeared at ~30% opacity below
its own reveal zoom (converted to `step`; colour lifted off the choropleth teals); 16 hover card
leaked when the pointer left the canvas; 17 comparison tray undiscoverable and non-collapsible
(rail hint with live pinned count + collapse control); 18 layout collapsed below ~1180 px (now
scrolls); 19 copy — unconditional plurals, "Lng Terminal" acronym casing, and search rows lacking
a region.

### What the red-team confirmed as sound

Zero third-party runtime requests and **zero console messages of any kind** across ~15
navigations, layer toggles and lazy loads; no coordinate, distance, bearing or route anywhere in
the UI, with `AssetDetail.tsx` acting as a single enforced chokepoint; no prospective-targeting
affordance, with all four ranking metrics retrospective; URL state round-tripping correctly with
defaults kept out; the shared-centroid disclosure wording; and "What changed" — singled out as
"the strongest thing in the product" for holding its three measures deliberately separate and for
its window honesty.

---

## 12. Gates

| Gate | Result |
|---|---|
| Current-date pipeline build | ✅ as_of 2026-08-30, ESDI 17.86 |
| Frozen regression build, isolated from release artifacts | ✅ 18.49, reverted; tree clean |
| Frozen invariant (iter 7 == iter 8) | ✅ 18.49 == 18.49 |
| Python tests | ✅ **158** (was 155) |
| Frontend tests | ✅ **90** (was 33, was 10 pre-iteration) |
| Typecheck (`tsc -b`) | ✅ clean |
| Production `vite build` | ✅ clean |
| Debug artifacts stripped | ✅ `__map` absent from production JS; no `window.__*` globals |
| Zero third-party runtime requests | ✅ verified in bundle and live |
| Independent UX red-team | ✅ run; 4 DEFECT + 9 UX-AMBIGUITY all fixed (§11) |
| Clean git tree | ✅ |

---

## 13. Limitations (aggressive)

- **The frozen reference is a convention, not a lock.** `--as-of` defaults to `date.today()`, so
  the frozen comparison point only exists when someone passes it. The new guard prevents a frozen
  payload from *shipping*, but nothing forces a future iteration to run the comparison at all. A
  committed frozen-date config would make the reference self-enforcing; out of scope here because
  it touches pipeline configuration.
- **`live_disruptions` is still capped at 80** for its own (current-impairment) purpose. That cap
  is correct for that view, but it is exactly the kind of convenience that caused this
  iteration's defect. Any future consumer must ask whether it wants *current impairment* or *the
  complete record* — `recovery_events` is now the answer for the latter.
- **Recovery evidence depends on dated records.** An episode whose restoration was reported
  without a date cannot appear in any window. The panel says "absence of evidence is not
  restoration" rather than implying completeness, but the corpus limitation is real.
- **Region-centroid stacking is disclosed, not resolved.** Four LNG terminals still share one
  point; the marker says so and names them, but the map cannot show them separately without
  inventing locations, which is forbidden. The honest treatment is the ceiling here.
- **Weekly series granularity.** Every "30/90-day" change is really 28–35 / 84–91 days. The UI
  states the actual span, but a reader skimming the label alone could still carry away "30 days".
- **The multi-line corpus name** (`Ust-Luga Multimodal Complex\n* …`) is a data-shape quirk
  handled in presentation via `displayName()`. The underlying record is untouched; a future data
  pass should decide whether that entry is one asset or four.
- **Headless verification friction.** The in-app browser pane pauses MapLibre's render loop when
  hidden, so map assertions require forcing a paint and screenshots are ground truth. A test-harness
  artifact, not a product behaviour, but it makes automated map checks slower and more manual than
  they should be.
