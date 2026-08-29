# Iteration 5 review — Eurasian network context, rivers, gas/coal depth, data-contract hardening

Follows [ITERATION_4_REVIEW.md](ITERATION_4_REVIEW.md). Theme: **put the monitored energy
system in its real network and geographic context, then improve the data underneath the
analysis** — without letting any of that new visibility enter the degradation model. Read
the limitations before quoting a number.

The one governing rule of this pass: **map visibility ≠ analytic inclusion.** A continent
of context pipelines, a broadened country layer, and major rivers were all added as
*display* geography; none of them can move ESDI, rankings, regional intensity, recovery, or
incident counts. That separation is now a first-class part of the data model and is
regression-tested.

## Starting baseline (verified from the repo + live payload)

| | Value |
|---|---|
| Git SHA (iteration 4 tip) | `ea8c02f` |
| ESDI | **16.02** (as-of 2026-08-29) / 16.3 at the fixed reference as-of 2026-08-28 |
| Events | 134 · coverage 43.9% |
| Assets | ~1,955 point assets + a 7-row curated supplement |
| Recovery | 3 distinct observed episodes (median suppressed) |
| Tests | 90 python |
| Payload | 4.4 MB static data |

## Headline movement

| | Value |
|---|---|
| **New ESDI** | **18.26** (as-of 2026-08-29) / 18.57 at ref 2026-08-28 — vs **`esdi_all_sectors` 15.52** if gas & coal count present-at-zero; the +2.74 renormalisation uplift is now disclosed |
| Events | 134 → **175** · coverage 43.9% → **57.4%** |
| Recovery | 3 → **5** distinct observed episodes (Unecha demoted to a flow-restart in red-team) → median **72 days** |
| Tests | 90 → **108 python + 10 vitest** |
| Payload | 4.4 → 4.9 MB total; **eager first-load 4.89 MB + 146 KB lazy** (rivers + networks) |

### ESDI decomposition (§40, at the fixed reference as-of 2026-08-28: 16.3 → 18.57, +2.27)

Measured at a **frozen as-of** so time decay never contaminates the attribution:

- **Refining +4.47** (29.21 → 33.68). Three refineries that are already in the national
  refining denominator — **Novoshakhtinsk (8.568 MTPA), Orsk (5.659), Mari El (1.2)** — are
  now documented as struck and, via explicit asset links, contribute their **tracked
  capacity as exposure**, exactly as wiki-sourced strikes on the same refineries would. No
  invented "affected capacity": the quantified-capacity count stays **0**.
- **Transmission +3.78** (17.59 → 21.37). ~5 new substation strikes joined the sparse,
  event-burden transmission sector.
- **oil logistics, electric generation, gas, coal: unchanged.** New oil-terminal/pipeline
  and power/gas events add to *event count and coverage* but not to those capacity-based (or
  uncovered) scores — honest, because we hold no capacity for those facilities.
- **Denominator changes:** none (refining denominator stays 280.6 MTPA; the linked
  refineries were already in it — this is exposure, not a new denominator).
- **Sector activation:** none. Gas and coal stay uncovered.
- **Time decay:** the 16.02 "today" vs 16.3 reference is one day of ordinary decay.

No weights were retuned. The scoring changes were put through an independent red-team pass
(see **Red-team** below).

## Context geography (§9–§11, §27)

- **Country set is now geographic, not a hand-picked allowlist.** `build_context.py` draws
  **every** Natural Earth 50m admin-0 country whose geometry falls inside the context frame
  — **71 countries** — with two deliberate exclusions: **Russia and Belarus** (drawn as
  analytic regions) and Natural Earth's "Siachen Glacier" non-country feature.
- **Extent widened** from the old 5–130°E box to a real Eurasian frame **(-12°E … 170°E,
  34°N … 82°N)**, so the Russia–Europe network reads end to end. This is a *data* expansion;
  the default camera stays the analytic Full AOI.
- **Country labels are data-driven.** The hardcoded `COUNTRY_MINZOOM` dictionary is gone;
  each country carries a `label_min_zoom` derived from Natural Earth **LABELRANK**, and the
  frontend reveals major states at continental zoom and smaller ones on zoom-in, with greedy
  collision de-overlap. A zero-energy-data country (Mongolia, China) still gets a border and
  a label — regression-tested.
- **§10 political-boundary discipline preserved.** Natural Earth files Crimea inside the
  *Russian* polygon; because Russia is excluded from context, Crimea is never painted as
  ordinary Russian context — it renders only as its own separately-identified occupied unit,
  and the broadened admin-0 layer does not overwrite that. RUS/BLR-in-context and
  Crimea-`special` are both test-asserted.

## Rivers (§13)

- Source: **Natural Earth 50m `rivers_lake_centerlines`** (public domain). **95 major river
  lines** loaded (scalerank ≤ 5); ~13 systems labelled.
- Emphasis is data-driven by **scalerank** (largest systems reveal first), not a hand-drawn
  list. Labels are de-duplicated **by name and by geometric proximity** and restricted to the
  AOI latitude band, so the Volga/Danube/Ob/Irtysh/Lena/Amur read cleanly without a
  name-soup. Payload **52 KB**, lazy-loaded, off by default.
- Rivers are pure context: a test asserts they carry no `asset_class`/`sector`/`region_code`
  and can never enter a score.

## Oil & gas network context (§3–§8)

- **A separate ingestion path** (`pipeline/build_context_network.py`), distinct from the
  analytic OSM feed. **Source: OpenStreetMap via Overpass (ODbL)**, tiled over western/eastern
  Europe, the Black Sea / Caucasus / Türkiye corridor, and the Russian Far East; filtered to
  **named `usage=transmission` trunks ≥ 50 km**, deduplicated against the analytic OSM lines
  by way id (§6 — one corridor, one line).
- **220 gas + 75 oil trunk context routes**, `scope="context"`, **0.09 MB** combined.
- **Gas: 68 KB, 220 routes. Oil: 28 KB, 75 routes.** Countries traversed span Atlantic
  Europe → all-Russia → the Far East export corridors.
- **GEM GGIT/GOIT are the authoritative trackers but are not ingested.** Their bulk data is
  delivered behind a per-request download form with no stable CI-fetchable URL (scout-verified
  this pass), so per §4 OSM is the automatable feed and **GEM is the cited cross-reference** in
  SOURCES/attribution. Cadence is honest: OSM refreshes monthly at most; the daily CI does not
  pretend otherwise.
- **Route-quality (§5).** OSM geometry is traced, so every route is `route_quality="osm_mapped"`
  and drawn solid. The field and a dashed companion treatment for `route_quality="approximate"`
  are in place, reserved for a future GEM snapshot — no code change needed to activate the
  distinction.
- **Kept out of scoring (§7/§15).** `build_index` never reads these files; context routes carry
  no region and generate no incident. The facet layer counts them as a **separate**
  `context_route_class` (gas 220, oil 75) from the analytic `line_class` (gas 2,577 lines), so a
  continent of context can never imply thousands of disruption records. Four regression tests
  enforce this.

## Gas / LNG inventory & methodology (§18–§20)

- **LNG inventory 5 → 7.** Added the **Kaliningrad Marshal Vasilevskiy import FSRU** (kept
  distinct from liquefaction — its capacity is in the note, never summed) and Magnitogorsk
  small-scale. A completeness audit found the five original terminals already capture
  ~100% of *operating large-scale liquefaction* in the AOI; the remaining gap is
  proposed/suspended projects (Murmansk, Obsky, Arctic LNG 1/3), documented but **not
  ingested** (not producing).
- **Gas-processing inventory 2 → 12.** Added Sosnogorsk, the SIBUR West-Siberian complex,
  and the LUKOIL/Rosneft/Tatneft plants — capacities in **bcm/y**, kept in the note.
- **Gas methodology decision: stays UNCOVERED.** LNG liquefaction (MTPA), gas processing
  (bcm/y) and pipeline flow (bcm/y) are incommensurable and are never summed. A single "Gas"
  composite is not defensible, so gas is exposed only as separate, clearly-labelled
  sub-measures and its 0.10 weight is renormalised away. **This is the honest result** — gas
  carries records but scores 0, which the UI states plainly. (Red-teamed; see below.)
- **Sharper reason (from the red-team):** the incommensurability argument only rules out a
  *single* gas composite. Gas *processing* alone is internally commensurable (all 12 GPPs are
  bcm/y) and could in principle be its own scored sub-sector — the real blocker is that (a) the
  bcm/y capacities live in free-text notes, not a structured column, and (b) there is no
  reconciled national bcm/y denominator (refining has one at 85% coverage; gas processing has
  none). So gas stays uncovered because its **denominator is not yet reconciled**, not merely
  because of unit-mixing. Activating a gas-processing sub-sector once a denominator exists is
  the cleanest future step.

## Coal (§21)

- **Inventory 0 → 13.** 7 mines (Kuzbass/Kemerovo, Krasnoyarsk, Irkutsk, Komi/Vorkuta,
  Novosibirsk) + 6 export terminals (Ust-Luga/Rosterminalugol, Lavna, Murmansk, Taman,
  Tuapse, Azov), cited, admin-region precision.
- **Taxonomy cleaned:** the generic `coal` class split into `coal_mine` + `coal_terminal`
  (both roll up to the coal sector); coal-fired **generation stays under electric generation**
  — no double count (test-enforced).
- **Scoring decision: coal SECTOR stays unsupported (score 0).** Research found **no
  kinetic/sabotage disruption to AOI coal infrastructure** — the widely-reported port strikes
  were oil/gas, not the coal terminals. Inventory is not disruption, so the toggles appear but
  the sector does not score.

## Events (§23–§24)

- **Candidate queue introduced** (`data/candidate/candidate_incidents.csv`): 49 candidates
  from a parallel sector-focused OSINT pass — **41 accepted, 8 held/rejected**, each with a
  decision reason. Only accepted rows enter scoring; held candidates (an unconfirmed
  "repelled" TurkStream claim, partisan-only sabotage, a weather outage) never score
  (test-enforced).
- **Events 134 → 175 across 15 under-covered regions** (Rostov/Novoshakhtinsk, Oryol/Stalnoy
  Kon, Krasnodar CPC + Sochi depots, Voronezh, Kaluga, Smolensk, Saratov, Mari El, Tambov,
  Belgorod, Volgograd, Vladimir, Kostroma, Bryansk, occupied Crimea oil + grid). **Coverage
  43.9% → 57.4%.** Duplicates and cross-slug fragments (Primorsk, Sheskharis, Novocherkassk,
  Feodosia) were reconciled to the existing facility nodes; no exact `(asset_id, date)`
  duplicate survives.

## Recovery (§25–§26)

- **Observed episodes 3 → 5**, so the median crosses the ≥5 gate at **72 days** from genuine
  episodes `[2, 22, 72, 98, 205]`. (Pre-red-team this read 6 episodes / 47 days; the red-team
  correctly flagged the Druzhba/Unecha record — flows rerouted while the pumping station itself
  was destroyed — as a *flow restart*, not a facility reconstitution, so it was demoted to
  `partial_restart`.) Not curated to the threshold. The median is now labelled honestly as
  **mixed-facility-type** (a 2-day terminal restart pooled with a 205-day gas-plant repair),
  not "typical recovery".
- **Non-refinery spread gained:** oil logistics (Primorsk, Novorossiysk/Sheskharis, Druzhba/
  Unecha) and gas processing (Astrakhan, Orenburg) now carry recovery evidence — previously
  refinery-only.
- **Model-vs-observation calibration (§26).** Observed *substantial-restoration* durations sit
  **below** the modelled *full-reconstitution* horizons, which is expected (a substantial
  restart precedes full reconstitution): refinery observed 22–98 d vs modelled 150; oil
  terminal 2 d vs 100; oil pipeline 7 d vs 70. The one exceedance — gas processing 205 d vs
  200 — is n=1. **Conclusion: the modelled horizons are directionally reasonable; the samples
  are far too small to refit, so no horizon was changed** (§26).

## Data contract (§17, §35)

- `schema_version` (=2) on the snapshot + a `data_manifest.json` listing every emitted file
  with size + an `optional` flag.
- The frontend tolerates schema N and N-1, renders best-effort on skew, and **lazy-loads**
  the optional context layers (rivers, networks) — a missing/late optional file degrades to an
  empty layer, never a white screen. Vitest covers schema N/N-1/forward/unsupported,
  `grabOptional` on 404/throw/present, and the lazy-loader's cache + missing-file fallback.

## Performance (§33)

- **Eager first-load ≈ 4.89 MB** (the 12 core files) — the continental context adds nothing to
  it, because rivers (52 KB) and the pipeline networks (96 KB) are **lazy-loaded on first
  toggle** (§16). The dominant eager file remains the analytic `assets_lines.geojson` (2.0 MB),
  unchanged.
- JS bundle grew ~2.6 KB. Context network geometry is simplified to ~4 km; trunk shapes are
  preserved.

## Documentation drift fixed (§32)

- `CLAUDE.md`: current-state pointer moved from ITERATION_2_REVIEW → ITERATION_5_REVIEW.
- `README.md`: event count 128/132 → 175; assets ~1,900 → ~1,980; coverage 43% → 57%;
  recovery "3 distinct episodes, suppressed" → "6 distinct episodes, median shown at 47 d";
  region count 79 → 80; gas/coal now-inventoried-but-uncovered wording.
- `docs/ZERO_COUNT_AUDIT.md`: coal row moved from "DATA GAP, deferred" to resolved
  (coal_mine 7, coal_terminal 6; sector correctly zero).
- METHODOLOGY / SCHEMA / SOURCES / CHATGPT prompt updated for the scope model, context
  network, gas/coal decisions and the new fields.

## Red-team (§37)

An independent adversarial agent reproduced the build (ESDI 18.26, all tests green), decomposed
every sub-index by hand, and traced each change through the code. It **validated the three
changes most at risk of being wrong** and surfaced honesty gaps I then closed.

**Confirmed sound (attacked, held up):**
- **No refinery double-count.** Each of the three linked refineries is in the refining
  denominator exactly once, and none appears in the wiki strike table — so no second exposure
  path exists. The numerator draws capacity from the *same* source as the denominator.
- **No coal double-count**; inventory-without-score is coherent (generation vs mine/terminal are
  distinct assets in distinct sectors).
- **Analytic/context separation is airtight.** `build_index` never receives the context files;
  context routes carry no region and no capacity and cannot reach any aggregation.

**Findings closed this pass:**

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | HIGH | The headline renormalises gas+coal away (÷0.85), a silent **+2.74 (~18%)** uplift; gas is *not* unmeasured (it has documented strikes). | **Disclosed.** `esdi_all_sectors` (15.52) + the gap + a note now ship in the snapshot and show in the Methodology modal. |
| 2 | MED | `SECTOR_BASIS` advertised gas/coal as `event_burden`, a measure `_share` implements only for transmission — a footgun that could silently zero-score a sector. | **Fixed.** Gas/coal relabelled `uncovered` in config + scoring.json, with a comment and a test. |
| 3 | MED-HIGH | Transmission (10% of ESDI) is **~95% one theatre** — Taman 500 kV (54%) + occupied-Crimea substations (45%) — scaled by an arbitrary saturation constant (8); read as "% of Russia's grid" it misleads. | **Disclosed.** `transmission_concentration` (top contributors + occupied share + a note) now ships and shows in the Methodology modal. |
| 4 | MED | The recovery median blended flow-restarts with reconstitutions; the Druzhba/Unecha record logged a *destroyed* pumping station as "substantially restored". | **Fixed + relabelled.** Unecha demoted to `partial_restart` (→ 5 episodes, median 72); the median is now labelled "mixed facility types" in the UI and doc. |
| 5 | LOW | "Three refineries" overstates — Mari El's single Oct-2025 strike has decayed to ~0 by the as-of, so the refining rise is essentially Novoshakhtinsk + Orsk (both Aug 2026). | **Documented** (see Limitations). |
| 6 | MED | The wiki-vs-curated dedup is by `asset_id` string only; a refinery that were ever *both* wiki-struck and given a capacity-bearing curated incident would double-count (does not fire today — the 3 linked refineries are absent from the wiki table). | **Documented as a known latent fragility**; an explicit facility-identity invariant is the recommended next hardening. |

The red-team's single most important point — *don't let the headline silently absorb the
renormalisation uplift* — is now addressed by shipping both figures with the reason gas/coal
are excluded.

## Production (§39)

_(Deployed SHA, live verification and any production-only defects — filled in at deploy.)_

## Limitations — read before quoting

- **The refining rise reflects *linked* refineries, not a model change.** It is exactly the
  exposure treatment wiki strikes already get, and no capacity loss is claimed. Two nuances the
  red-team drew out: (a) only the three struck-and-net-new refineries were point-mapped, so
  curated strikes on *other* inventoried refineries still under-count until similarly linked;
  and (b) of the three, **Mari El's single Oct-2025 strike has already decayed to ~0** by the
  as-of, so the +4.47 is essentially Novoshakhtinsk + Orsk (both Aug 2026).
- **Oil-terminal / power / gas / coal events raise coverage and counts but not capacity-based
  exposure**, because we hold no per-facility capacity for them (oil logistics is a proxy;
  generation needs MW; gas/coal are uncovered). Coverage rose to 57% largely through events
  that, honestly, do not move the capacity sectors.
- **Gas and coal remain uncovered.** Gas carries real strikes (incl. GPP hits) that add 0 to
  the index — deliberate honesty, not a claim they did not matter. Coal has inventory but no
  disruption evidence.
- **Recovery is still thin (5 episodes).** The 72-day median pools a 2-day terminal restart
  with a 205-day gas-plant repair across sectors; it is labelled mixed-facility-type, not a
  sector norm. Only the cross-sector median clears the gate; no single sector has ≥5 episodes.
- **The context network is OSM-only.** It is real traced geometry but not the GEM census;
  coverage is "major named transmission trunks ≥ 50 km", so some corridors are absent and all
  routes render as `osm_mapped` (the mapped/approximate distinction awaits a GEM snapshot).
- **The WebGL map is pixel-unverified in the headless environment.** The map canvas
  initialises with a live WebGL2 context and all tabs/controls/data are verified via the DOM
  and network, but the GL `load` event needs compositing the headless pane does not do, so
  toggle-triggered rendering and lazy-fetch are verified on the live production browser instead
  (see Production).
- **Admin-region precision throughout.** No incident coordinates, no range-to-target, no
  facility-level geometry for sensitive sites; context pipeline routes are published OSM
  geography, not targeting data. Scope tests cover the whole served payload.
