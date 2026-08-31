# Iteration 9 review — multi-source pipeline reconstruction & source expansion

A **data / GIS / source-integrity** iteration. Theme: *complete the network from real sources, not
from visual guesswork*, and *topology may be known when geometry is not*.

The headline result is that the pipeline network was never a source problem. It was an extraction
problem, and the extraction was discarding roughly six times more route geometry than it kept.

## Baseline

| | main (iteration 8) |
|---|---|
| production ESDI / as_of | 17.86 / 2026-08-30 |
| frozen regression ESDI | 18.49 (as-of 2026-08-28) |
| context gas routes | 220 features, 29,832 km, **160 connected components** |
| context oil routes | 75 features, 12,630 km, **53 connected components** |
| analytic lines | transmission 5,066 · gas 2,575 · oil 205 |
| context payload | 67.5 kB + 24.0 kB |

## 1. Root causes — all four were ETL, none were the source

Measured **before** any fix (`PIPELINE_GAP_AUDIT.md`) precisely so source gaps and extraction gaps
could be told apart.

| Cause | Measured loss |
|---|---|
| **50 km minimum applied per OSM WAY** | gas 2,206 ways / 18,007 km (33.4%) and oil 426 / 4,725 km (24.0%) discarded. **65 named routes destroyed outright**, 107 truncated — TAP 81% missing, Baku–Tbilisi–Ceyhan 82%, OPAL 77%, Transalpine 70%, Druzhba and Urengoy–Pomary–Uzhhorod both cut. |
| **No relation awareness at all** | Every cached Overpass response contained only `way` elements. 478 pipeline route relations exist; **8,819 of 9,024 member ways — 161,899 km — never reached the output.** |
| **A hole in the query bands** | The four bands left **56°E–120°E unqueried**. 91 relations / **71,522 km** were never asked for: Сияние Севера (8,376 km), Уренгой–Новопсков, Омск–Иркутск, СРТО–Торжок. |
| **De-duplication against the analytic feed** | **17,535 km** of trunk — Druzhba, Urengoy–Pomary–Uzhhorod, Palkino–Primorsk — deleted from the context layer, so enabling *Gas pipelines* without *Grid & pipeline network* showed no Russian backbone at all. |

## 2. Source audit

Full matrix and licence verdicts in `PIPELINE_SOURCE_AUDIT.md`. The decisions that mattered:

- **Overpass relations, not a Geofabrik PBF.** The whole relation corpus for the Europe–Far East
  corridor is 21.7 MB in ~30 s, against multi-GB extracts plus a compiled parser dependency for
  the same relations. Rejected on cost, not capability.
- **GEM GGIT (Nov 2025) / GOIT (June 2026) are CC BY 4.0, verified verbatim, raw redistribution
  permitted.** The obstacle is a form-gated download, which is an *access* control, not a licence
  restriction. Two ungated paths were deliberately **not** used: the public CDN GeoJSON omits
  `RouteAccuracy` (so quality could not be labelled honestly) and the routes GitHub repo has no
  LICENSE file and contains re-imported OSM. A vendor-snapshot procedure with checksums is
  documented instead of pretending CI can fetch it.
- **ENTSOG has no pipeline entity.** It models operator ↔ connection point ↔ balancing zone only.
  It can prove `OPERATOR_A connects_to OPERATOR_B at POINT_X`, and must never be forced into a
  pipeline claim — the trap §14 warned about. Its `tpMapX/Y` are schematic layout coordinates, not
  lat/lon.
- **GIE storage/LNG deferred** (no coordinates at all — an inventory pass, not a network one).
  **AGSI/ALSI rejected** despite having the most permissive licence in the audit, because a
  personal API key is incompatible with "rebuildable by anyone".

## 3. Reconstruction

`fetch_osm_pipelines.py` + `build_pipeline_network.py`. The governing rule is
**reconstruct the route first, then judge it**: assemble from relation members, *then* apply the
trunk threshold, *then* simplify. 84 routes (8,405 km) exist only because assembly precedes the
filter.

Connection evidence is hierarchical and distance is never sufficient on its own:

- segments join **only on exactly-shared endpoints** — OSM asserting a shared node. Independently
  verified across all routes: 5,191 endpoint coincidences, **all exactly equal, max offset 0.0 m**;
  no join survives on rounding.
- the single distance rule (`weld`, ≤100 m) applies **only between components of the same
  relation**, where identity is already established. 573 welds, max 99.9 m, all recorded per
  route. The named-way path does **not** weld — a shared name string is not OSM asserting one
  pipeline.
- anything else stays a visible gap.

**The context layer is self-contained.** Overlap with the analytic feed is marked
(`analytic_overlap`, 214 routes / ~127,000 km) and left in place; the *frontend* suppresses the
double-draw only while the analytic layer is also on. The pipeline no longer decides what to
withhold.

## 4. Result

| | old | new |
|---|---|---|
| gas routes | 220 | **375** (219 relation-derived, 156 named-way) |
| gas length across routes | 29,832 km | **164,563 km** |
| gas distinct network | — | **141,335 km** |
| gas continuous end-to-end | — | 228 of 375 |
| oil routes | 75 | **89** |
| oil length across routes | 12,630 km | **51,385 km** |
| oil distinct network | — | **51,108 km** |
| oil continuous end-to-end | — | 64 of 89 |
| payload (gzipped) | ~25 kB | **141 + 39 kB** |

Systems that appear for the first time: **Сияние Севера** (8,376 km), **СРТО–Торжок** (2,000 km),
**Уренгой–Новопсков**, **Омск–Иркутск**, **Сургут–Полоцк**, **Бухара–Урал**. ESPO and Druzhba are
now single continuous components; TAP and OPAL are whole.

**Twenty largest old gaps** — every one dispositioned `FIXED — OSM relation reconstruction`; none
required GEM geometry, because none was a source gap.

## 5. Smoothing

Topology-preserving generalisation only: stitch source members, then Douglas-Peucker. No spline,
no Bézier, no Chaikin, no nearest-neighbour connector.

Benchmarked after stitching:

| tolerance | ~km | vertices | payload | length error |
|---|---|---|---|---|
| 0.005° | 0.6 | 28,897 | 1.14 MB | −1.60% |
| **0.010°** | **1.1** | **17,239** | **916 kB** | **−2.50%** |
| 0.020° | 2.2 | 10,090 | 788 kB | −3.61% |
| 0.040° (old) | 4.4 | 6,135 | 717 kB | −5.07% |

0.01° chosen: payload is dominated by properties rather than vertices, so the aggressive end buys
almost nothing and doubles the error. Both `route_length_km` (source) and `drawn_length_km`
(after simplification) are published, because they differ by ~2.4% and a reader should not have to
guess which the map shows.

## 6. Topology from operator sources

54 sourced connection assertions in `data/curated/pipeline_topology.csv`, each a named point with
a source URL and a source tier. **These never become geometry** — two tests enforce it: the file
may carry no coordinates, and the geometry builder may not import it.

Three findings worth carrying:
- **GEM's wiki status fields are stale.** It reports Ukraine transit as operating in August 2026;
  transit through Sudzha stopped 1 January 2025 and Eustream confirms the Veľké Kapušany halt.
  Where a tracker and a TSO disagree on status, the TSO wins.
- **Status must be modelled separately from existence.** Yamal–Europe and the Brotherhood corridor
  are physically intact and carrying zero contracted transit.
- **Names mislead.** Ukhta–Torzhok terminates at Gryazovets, not Torzhok. CPC's Novorossiysk
  terminal is a separate node from Transneft's Sheskharis.

## 7. Independent GIS red-team

Reproduced the shipped GeoJSON **byte-for-byte** (475 pipeline_ids, 0 differences), confirmed the
two hardest claims with zero counterexamples, and returned **SHIP WITH FIXES — 6 DEFECT, 4 RISK**.
All are fixed; each is verified below by re-measurement.

| # | Finding | Disposition |
|---|---|---|
| 1 | **Douglas-Peucker used distance to the INFINITE LINE.** When a chain's anchors are close, every interior point scores ~0 and the excursion is deleted whole, collapsing the chain below two points where it is silently dropped. **690 components / 216 km erased**, including 25.7 km of Уренгой–Петровск drawn as an 80 m stub. | **Fixed** — point-to-segment with the projection clamped. Verified: the metric now returns 9.999 where it returned 0.0. |
| 2 | `stitch()` walked through junctions arbitrarily, so a chain could run out along one string and back along its twin — **757 km drawn for ~379 km** of corridor. | **Fixed** — degree-aware: chains stop where 3+ ways meet. Self-overlaid components 7 → **0**. |
| 3 | **Generic nouns became routes.** Every way named "перемычка" (jumper) across a 3,000 km corridor formed one **153-component** "route" with an id and a length. | **Fixed** — bare descriptive nouns rejected; a name-group whose bbox dwarfs its own pipe is dropped. Largest route 153 → 125 components (a genuine BOTAŞ relation). |
| 4 | Superroutes **and** their child relations both emitted, double-counting **13.5%** of network length. | **Fixed by disclosure** — both published: sum-across-routes 164,563 km vs `distinct_network_km` 141,335 km (gas). |
| 5 | `route_quality` was hardcoded `osm_mapped` across a **100:1 fidelity range** (one route averages 173 km between vertices; another contains a 632 km straight run) while the UI styled it as a confidence signal. | **Fixed** — measured from source vertex spacing before simplification. The dasharray and legend became live rather than dead code. |
| 6 | `weld()` was called from the named-way path, where the "same relation" justification does not hold — **67 joins rested on a shared name string**. | **Fixed** — the named-way path no longer welds. Verified 0 welds on named-way routes. |
| 7 | Weld provenance computed then discarded. | **Fixed** — `welds`, `max_weld_km`, `source_vertex_spacing_km`, `drawn_length_km` ship on every feature and in the quality report. |
| 8 | "Junctions survive simplification" was false (11.1% do). | **Fixed** — comment corrected; nothing downstream relies on junction coordinates. |
| 9 | `route_length_km` billed 5,206 km never drawn. | **Fixed** — `drawn_length_km` published alongside. |
| 10 | Refined-products rule had two holes, and **my own comment was factually wrong**: Exolum tags 235 members `substance=oil` and **zero** as `fuel`, so only the NAME rule catches it, not the vote. | **Fixed** — named-way path routed through the resolver, "Produktenleitung" added, comment corrected. |

Claims the red-team **confirmed**: threshold-after-assembly (84 routes exist only because of it),
exact-endpoint-only stitching (max offset 0.0 m), weld tolerance (max 99.87 m by true haversine,
0 over), simplification ordering (1,522 of 1,529 components within the 1.11 km bound), and that
nothing was deleted for analytic overlap.

## 8. Substance discipline

Found in my own output while compiling the before/after audit and fixed before the red-team ran:
Exolum's 3,123 km **"Canalización de Derivados del Petróleo"** — a Spanish *refined products*
network — was classified as crude oil. Two rules now prevent it: the substance vote runs over raw
member values (a dominant `fuel` tag excludes the route), and a name stating the system carries
products excludes it outright. NATO's CEPS (5,091 km) and Exolum are both correctly out.

Water, ethylene, hydrogen, CO₂, steam and refined products never enter either class.

## 9. Scoring — unchanged, and one defect deliberately not fixed

**Production ESDI 17.86** (as_of 2026-08-30) and **frozen regression ESDI 18.49** (as-of
2026-08-28) are both unchanged, verified after every pipeline change. The context network never
touches ESDI, rankings, regional intensity, incident counts, recovery or denominators, and tests
enforce it.

**A real denominator defect was found and NOT corrected** (`POWER_SOURCE_RECONCILIATION.md`):
WRI GPPD has **no status field** and is frozen at 2022-01-26, so the electric-generation
denominator carries roughly **23 GW of Russian capacity that GEM reports as retired**. Coal
reconciles as GEM-operating 37,278 + GEM-retired 10,839 ≈ WRI 46,072 MW; wind is 42 MW against
2,605 MW. Per §30 this is documented rather than silently fixed: changing it moves every
historical ESDI value and requires a frozen replay plus an independent methodology red-team. The
immediately-safe step — flagging WRI records GEM marks retired — needs no denominator change.

## 10. Other source opportunities

- **Coal**: the repo has no mine or terminal inventory at all. GEM Coal Mine Tracker (Aug 2026)
  gives 453 Mtpa Russian operating capacity with ownership chains and aliases; Coal Terminals
  (Dec 2024 — the page's "Jan 2026" is wrong) gives 30 operating terminals / 363 Mt **nameplate**,
  not throughput. Adding an inventory does **not** activate Coal in ESDI.
- **Underground gas storage**: GIE Storage DB has the right fields and no coordinates — a context
  asset class for a later pass.
- **Satellite corroboration**: FIRMS is openly licensed but deferred, because corroborating an
  incident requires facility-precision queries this project deliberately does not hold, and a
  scheduled sweep over a facility list is a strike-detection pipeline whatever it is called.
  Copernicus rejected on scope — SWIR/SAR change detection assesses damage rather than
  corroborating reporting.

## 11. Gates

| Gate | Result |
|---|---|
| Current-date build | ✅ as_of 2026-08-30, ESDI 17.86 |
| Frozen regression, isolated | ✅ 18.49, unchanged from iterations 7–8 |
| Python tests | ✅ **181** (was 158) |
| Frontend tests | ✅ **96** |
| Typecheck / production build | ✅ clean |
| Pipeline continuity QA | ✅ emitted as `pipeline_network_quality.json` + snapshot `network_coverage` |
| Licensing audit | ✅ `PIPELINE_SOURCE_AUDIT.md` |
| GIS red-team | ✅ 6 DEFECT + 4 RISK, all fixed |

## 12. Limitations — aggressive

- **The infinite-line simplification bug still exists in three other callers**
  (`build_assets`, `build_context`, `geo.simplify_ring`). Fixing them would alter region, river and
  analytic-line geometry this iteration did not touch and did not re-verify, so it is recorded
  rather than changed. It should be the first thing a geometry pass addresses.
- **147 gas routes and 25 oil routes remain fragmented.** After relation reconstruction these are
  genuine source gaps — OSM has not mapped those stretches — but the dataset cannot currently
  distinguish "unmapped in OSM" from "no pipeline there". A GEM ingestion would resolve some.
- **No GEM geometry was ingested.** The licence permits it; the form gate means a human must
  acquire it. Until then every route is OSM-derived and `gem_traced` / `gem_generalized` remain
  unpopulated vocabulary.
- **Route quality is inferred from vertex density, not stated by the source.** OSM has no
  accuracy field. A sparsely-drawn but accurate route is indistinguishable from a coarse sketch;
  only GEM's `RouteAccuracy` would settle it.
- **13.5% of route length is shared between superroutes and their children.** Disclosed via
  `distinct_network_km` rather than resolved — deciding which of a superroute and its children is
  the canonical entity needs a curated registry, not a heuristic.
- **The canonical pipeline registry is partial.** `pipeline_id` is OSM-derived
  (`osm-rel-*` / `osm-name-*`); there is no cross-source identity layer joining OSM to GEM project
  IDs or ENTSOG points, because no second geometry source was ingested. The 54 topology
  assertions use their own uppercase system names and are **not yet joined** to `pipeline_id`.
- **Topology assertions are not surfaced in the UI.** They are curated, tested and documented, but
  a reader cannot yet see "this connection is known but the route is unmapped" on the map. That is
  the honest Type-C treatment §10 asked for and it is not built.
- **ENTSOG was audited but not ingested.** Its topology is real and key-free, but without a
  pipeline entity it needs a curated pipeline↔point mapping to be useful, which is editorial work
  this iteration did not do.
- **`largest_route_components: 125`** is BOTAŞ's Turkish national network modelled as one
  relation. It is a legitimate relation, but treating a national network as a single "route" is a
  modelling mismatch the registry should eventually resolve.
- **Named-way routes (156 gas / 27 oil) rest on name equality**, which is the weakest identity in
  the dataset. The bbox guard removes the worst artefacts, but a proper-name collision between two
  genuinely different pipelines would still merge them.
