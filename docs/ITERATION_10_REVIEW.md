# Iteration 10 review — multi-source network integrity

**Theme:** make the network entities, connections, and source quality real.

The short version: the registry and the multi-source model landed, ENTSOG gave the node
architecture an independent authority to rest on, and **two independent red-teams found
thirty-four defects between them — including one that was changing a published score and one
that had made a headline conclusion in this iteration's own audit false.** Both are fixed. The
most valuable output of this iteration is not a feature; it is the list of things that were
wrong and are now measured.

## What shipped

| | |
|---|---|
| **Canonical registry** | 36 curated entities (2 system · 7 corridor · 24 pipeline · 3 branch), 438 auto-derived. Many-to-many source mapping, structural `entity_level`/`parent_id`, closed vocabularies. |
| **Temporal status** | 27 records across 15 entities, three kinds tracked separately (16 commercial flow · 7 physical · 4 operational), each an interval with its own source. |
| **Sourced aliases** | 80 aliases in 7 types with provenance. Eight unsourced nicknames removed. |
| **Canonical nodes** | 34, **all** `geography_precision: none`. Six independently confirmed by ENTSOG with EIC codes. |
| **GEM ingestion** | 1,917 rows for the monitored area, attributes only. 65 proposed mappings, 3 canonical. |
| **ENTSOG topology** | 68 interconnections at the RU/BY/UA boundary, 36 distinct points, 53 with EIC. |
| **Dossier topology** | 29 entities list documented connections; all 54 assertions classified. |
| **Route dossier** | Identity, hierarchy, temporal status, geometry completeness, source mappings with evidence. |
| **Alias search** | Дружба, Barátság, Сила Сибири, BPS-2 all resolve, naming which alias matched. |
| **Tests** | 214 Python (from 185) + 96 frontend. |

### Canonical coverage — measured in kilometres, not entities

| | |
|---|---:|
| Distinct mapped pipe geometry | 189,979 km |
| — attached to a **curated** canonical entity | **53,884 km (28.2 %)** |
| — attached to an auto-derived entity | 71.8 % |
| — with **no** canonical identity | **0 km** (was 20.4 %) |

36 curated entities of 474 is 7.6 % by count. **28.2 % by kilometre is the honest figure**, and
the network must not be described as canonically reconciled end to end.

## The defects that mattered

### A scoring bug was changing the published index

`_facility_registry` used to `continue` on an `asset_id` it had already seen. Incidents arrive
date-sorted, so the **earliest** incident fixed a facility's capacity and every later one was
discarded — including a later `linked_asset_id`. Novocherkasskaya GRES was struck twice; the
second record linked it to a 2,214 MW plant and was thrown away. A station with a confirmed live
disruption contributed **0 MW**.

Fixed by folding capacity fields across every incident, first non-null per field. Disrupted
generation **44 → 154 MW**; generation sector **0.02 % → 0.07 %**. Verified to change exactly one
field on one facility.

### The generation audit's conclusion was false, twice over

This iteration published "the denominator cannot move the headline". Both red-teams overturned it
independently:

1. It was measured at **one timestep of a 245-step series**. Across the series a realistic
   correction moves ESDI by up to **0.0287**, and regional ordering changes from 2025-07-26.
2. It rested on the 44 MW the bug above was suppressing. With the bug fixed, the **current-date**
   sensitivity is **0.0165** — above publication precision on its own.

And the claim "no region has a non-zero generation intensity" was simply **false**: it came from
reading `regional_intensity.electric_generation` instead of `regional_intensity.sectors.
electric_generation`, and was never measured. Moscow Oblast publishes **0.29** on a 14,589 MW WRI
denominator, its regional composite is **100 % generation-driven**, and it moves ~12 % under a
realistic correction — an order of magnitude more than the national headline. The vintage caveat
had been attached to the one place the error is smallest; it is now on the regional figures too.

**The denominator is still not corrected**, because a present-day fleet applied backwards across
2022–2026 would assert 2026 retirements in 2022 — a different error, not a fix. It is now
recorded as a **known material defect awaiting per-unit commissioning and retirement dates**, not
as a curiosity.

### Six geometry defects, all shipping

| | Effect |
|---|---|
| `weld()` re-joined chains across junctions `stitch()` deliberately refused to walk — a zero-length "gap" is a shared node | 119 bad welds |
| `_simplify` ran an **open-line** algorithm over **closed** chains, so first == last and the component fell below 2 points | **646 components / 201 km deleted outright** |
| A way listed twice in a relation was used twice | 1,320 km drawn twice |
| `distinct_network_km` apportioned length by member-way **count** and was **order-dependent** | 5,638 km spread on identical data; gas overstated 2,235 km |
| 183 named-way routes were built *after* the registry ran | 244 features with `canonical_pipeline_id: null` while the docstring claimed full coverage |
| The gap ledger counted every mutually-nearest pair twice, and never reported a component's larger separations | total inflated 26 %, band shares biased small |

`distinct_network_km` is now an exact union of measured way lengths: **gas 139,100.2 km, oil
50,878.5 km** — matching the red-team's independent computation to 0.1 km. The gap ledger now
uses a minimum spanning tree per route (N−1 gaps, each counted once), and its band distribution
matches their independent spanning-tree check exactly.

### Source-integrity defects

- `reconcile_gem` stamped **name equality** as `exact` — which is auto-mergeable, and is precisely
  the failure its own docstring forbids. Nothing it produces is `exact` any more.
- It wrote `aggregates` where a GEM segment is `part_of` the canonical entity, inverting the
  hierarchy on 54 of 66 rows.
- **16 proposals are now demoted automatically** by a contradiction check: `DRUZHBA ← P2020` is a
  **cancelled** Unecha–Wilhelmshaven project, `POWER_OF_SIBERIA ← P3208` is cancelled, `BPS_1 ←
  P5333` is retired, two ESPO candidates are China-only. Each is the RV-009 failure; the check now
  catches the class rather than the instance.
- Provisional GEM rows had reached the curated source map unmarked, and `--release` on a map-data
  export would have laundered unversioned data into a citation. Now a hard refusal.
- Two user-facing disclaimers denied doing what the product visibly does (the dossier renders
  commercial-flow status under a footer saying it never reports operational status). Rewritten to
  state the real boundary: dated sourced status, never a live reading.

## What the review queue caught that a matcher would not have

| Row | Case | Disposition |
|---|---|---|
| RV-005 | "Caspian Pipeline" is CPC — proven by endpoints and a shareholder list that *is* the consortium | ACCEPTED |
| RV-008 | OSM maps Ukhta–Torzhok **3** as built; GEM records string 3 as **proposed** | **UNRESOLVED** |
| RV-009 | "Yamal Europe 2" is a **cancelled** Belarus→Slovakia project | **REJECTED** |
| RV-010 | Three OSM relations named "Nord Stream"; r2006544 has zero unique ways | **UNRESOLVED** |
| RV-011 | 25 routes / 17,870 km are entirely other routes' ways — correct hierarchy, wrong to sum | ACCEPTED |

RV-008 is the one to read twice: two sources disagree about whether a pipeline is *built*, and
the model keeps the disagreement rather than resolving it.

## Deliberately deferred

**GIE gas storage / LNG inventory (§20) and GEM coal mine + terminal inventory (§21):
evaluated and deferred to a dedicated inventory pass.** Neither is half-ingested; no partial
files exist.

- **GIE AGSI+/ALSI** requires a free API key, which is human-mediated acquisition like GEM's form.
  Storage *levels* are also close to an operational-status feed and need a scope decision before
  ingestion, not after.
- **GEM Global Coal Mine Tracker (Aug 2026)** — verified Russia: 453 Mtpa operating, 15
  mothballed, 96 proposed. Adoptable, form-gated, and carries ML-estimated workforce/methane
  figures that must be flagged estimated rather than observed.
- **GEM Global Coal Terminals Tracker (Dec 2024)** — 30 operating terminals, 363 Mt **nameplate
  handling capacity, not observed throughput**. At ~20 months old it is a structural inventory,
  not a current-state indicator.

Adding either would not activate its sector in ESDI: inventory completeness and disruption
measurement are separate questions, and coal has neither a defensible denominator nor disruption
evidence.

**Also not done:** GEM route geometry precedence (§9). 698 of 1,917 GEM rows carry GEM's own
straight-line geometry; no precedence rule has been written, so none was applied and **no GEM
geometry is ingested at all**. `GENERALIZED != MAPPED`.

## Known weaknesses carried forward

1. **Drawn geometry is not de-duplicated.** Where two OSM ways trace the same physical pipe, both
   are drawn (~10 % overdraw, concentrated in a few routes; Омск — Иркутск is the worst).
2. **65 GEM mappings remain proposed, not canonical.** Promotion is a one-pass human review.
3. **28.2 % canonical coverage by kilometre.** The rest is identified but not curated.
4. **`high → gem_traced`** may overstate: GEM offers a `very high (within meters)` tier, and 94 %
   of rows we call "traced" are the tier below it. The source value is preserved verbatim.
5. **Antimeridian is unhandled** (latent — no vertex currently past 170°E, but the fetch corridor
   extends to 180°).
6. **Simplification is in degrees**, so tolerance is ~3.4× looser E–W than N–S at 73°N.
7. **`source_date` on 21 of 27 status rows is the curation date**, not a publication date. Now
   labelled "recorded" rather than "source" where the two coincide.

## Numbers to carry forward

- Frozen 2026-08-28 replay: **ESDI 18.49 → 18.50**. The generation denominator is untouched
  (219,992 MW, sensitivity-only as required); the +0.01 is entirely the capacity-linkage fix.
  That is a correctness change to a published score, not a methodology change, and it is the
  right outcome — the previous value counted a 2,214 MW disruption as 0 MW. Shipping a known
  scoring bug to preserve a constant would have been the wrong trade.
- Production build: current-date **2026-08-31, ESDI 17.57** (from 17.86 — one day of decay plus
  the same linkage fix).
- Network extent: **gas 139,100 km, oil 50,879 km** distinct mapped pipe.
- Gaps: **210 fragmented routes, 1,519 gaps, ≈43,200 km** straight-line lower bound, 78 routes
  overlapping the analytic layer.
