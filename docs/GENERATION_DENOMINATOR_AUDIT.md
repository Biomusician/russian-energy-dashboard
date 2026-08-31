# Generation denominator audit

**Nothing in this document changes a published number.** Iteration 10 §22/§32 require the
corrected denominator to be produced as a *sensitivity*, not deployed. Reproduce with:

```bash
.venv\Scripts\python.exe -m pipeline.audit_generation_denominator
```

## The question, correctly framed

Iteration 9 found that the WRI Global Power Plant Database — which supplies
`denominators.electric_generation_mw` — carries roughly **23 GW that GEM records as retired**
([POWER_SOURCE_RECONCILIATION.md](POWER_SOURCE_RECONCILIATION.md)). The tempting conclusion is
"subtract 23 GW".

That conclusion is wrong in *both* directions, and the reason is temporal.

| | |
|---|---|
| WRI's newest Russian commissioning year | **2018** |
| WRI's newest generation data | 2019 |
| WRI `year_of_capacity_data` for Russian rows | **empty on all 545** |
| WRI last data-touching commit | 2022-01-26 (AUS/IND/USA/GBR only) |
| WRI retirement field | **does not exist** |
| GEM operating status vintage | **August 2026** |
| ESDI series window | 2022 → present |

So WRI over-counts by including plants retired after its census **and** under-counts by missing
everything commissioned 2019–2026. And GEM's status is a single 2026 observation: applying it
across the series would assert that a plant retired in 2024 was already gone in 2022.

**The denominator is not one number that is wrong by 23 GW. It is a census at a date, and the
index needs the census as it stood at each scoring date.**

## Present-day sensitivity

The generation sector score is a capacity share (disrupted ÷ installed), so it is exactly
inversely proportional to the denominator and each scenario is one multiplication. The composite
renormalises over covered sectors (weights: refining 0.35, generation 0.20, transmission 0.10,
oil logistics 0.20; gas and coal are uncovered, not zero-disruption).

Baseline: generation **0.07 %** on **219,992 MW** — about **154 MW** of decay-weighted disrupted
generating capacity.

**Maximum movement at today's date, including deleting the sector outright: ±0.0165.** The
headline is published to two decimal places, so **the denominator can change it today.**

## Full-history sweep

Today is one step in a 245-step national series and 80 regional series. Sweeping every timestep
under each scenario (`sweep()` in the audit script):

| Scenario | Max \|ΔESDI\| national | Date | Max \|ΔESDI\| regional | Region |
|---|---:|---|---:|---|
| GEM Aug-2026 operating basis | **0.0287** | 2025-11-29 | 0.0287 | RU-MOS |
| WRI less GEM-retired | 0.0267 | 2025-11-29 | 0.0267 | RU-MOS |
| Denominator halved (bound) | 0.2282 | 2025-11-29 | 0.2282 | RU-MOS |
| Sector deleted (absolute bound) | 0.2282 | 2025-11-29 | 0.2282 | RU-MOS |

**Regional ordering first changes on 2025-07-26.** National generation disruption peaked at
0.44 % around 2025-11-29 — six times today's level.

## Regional exposure — the largest effect, and the one nearly missed

**Moscow Oblast (RU-MOS) publishes `regional_intensity.electric_generation = 0.29` against an
`installed_mw` of 14,589 — a WRI-derived regional denominator.** Its regional composite is
100 % generation-driven (`covered_sectors: ["electric_generation"]`), so it moves with the
denominator roughly one-for-one: about ±12 % under the realistic scenarios, an order of magnitude
more than the national headline.

**78 regions publish `installed_mw` from this same 2018 census.** An earlier draft of this
document asserted that "no region has a non-zero generation intensity"; that was **false** — it
came from reading the wrong key (`regional_intensity.electric_generation` rather than
`regional_intensity.sectors.electric_generation`) and was never measured. The regional exposure
is the *largest* effect of the stale denominator, not the absent one.

## A scoring bug was suppressing the number this audit measures

The independent analytic red-team found that `_facility_registry` in `build_index.py` used to
`continue` on an `asset_id` it had already seen. Incidents arrive date-sorted, so the **earliest**
incident fixed a facility's capacity and every later one was discarded — including a later
`linked_asset_id`.

Novocherkasskaya GRES was struck twice. The first record carried no link; the second linked it to
a **2,214 MW** inventoried plant. The second was thrown away, and a station with a confirmed live
disruption contributed **0 MW**.

Fixed: capacity fields are now folded across every incident for a facility, first non-null per
field. Effects:

- Decay-weighted disrupted generation: **44 MW → 154 MW** (3.5×).
- Generation sector score: **0.02 % → 0.07 %**.
- National ESDI on 2026-08-31: **17.86 → 17.57** (most of that difference is one extra day of
  decay; the linkage fix raises generation and lowers nothing).
- Current-date denominator sensitivity: **0.0047 → 0.0165**, i.e. from below publication
  precision to above it.

**The earlier "analytically inert" conclusion was therefore doubly wrong:** it was scoped to a
single timestep, and it rested on a number a bug was suppressing 3.5×.

## Historical sensitivity — NOT computed, and why

Addendum §12: *"Do NOT retroactively apply 2026 operating status across 2022–2026. If historical
status dates are insufficient, say so and stop at the present-day sensitivity."*

They are insufficient. Building a census-at-date needs, per generating unit: capacity, a
commissioning date, and a retirement date. Against the sources actually in this repo:

| Requirement | WRI GPPD (in repo) | Status |
|---|---|---|
| Capacity MW | present | ok |
| Commissioning year | **275 of 545 plants (50 %); 35 % of capacity undated** | insufficient |
| Retirement year | **field does not exist** | fatal |
| Unit-level granularity | plant-level only | insufficient |

WRI dates only 14 Russian plants at 2015 or later and none after 2018, so it cannot even bound
the post-2018 build-out. **A historical census cannot be constructed from what is here, and no
historical sensitivity is reported. Constructing one from present-day status would be
fabrication, so it was not done.**

### What would close it

GEM's **Global Integrated Power Tracker** carries per-unit `Start year` and `Retired year`, which
is exactly the missing axis. It is form-gated like GGIT/GOIT, so it needs the same
human-in-the-loop acquisition the pipeline importer already models. With that file:

1. Crosswalk WRI plant ↔ GEM unit at **unit level**, rolled up to a station key (§13 of the
   addendum: crosswalk at the lowest defensible level). Ambiguous matches go to
   `data/review/`, never auto-merged.
2. Build `installed_mw(t)` as a step function from commissioning and retirement years.
3. Replay the frozen 2026-08-28 regression build on that basis and publish **both** series.

Until then the honest position is the one stated above: a dated census, its vintage disclosed.

## Recommendation

1. **Do not change the denominator in this iteration** — but not because it is harmless. It is
   not: it moves published values nationally and materially more regionally. A corrected
   present-day denominator applied backwards across 2022-2026 would assert 2026 retirements in
   2022, which is a different error, not a fix. The blocker is the missing temporal basis, and
   this is now a **known material defect awaiting a source**, not a curiosity.
2. **Disclose the vintage.** Publish the denominator's basis and census date alongside the value
   (`"basis": "WRI GPPD, Russian rows dated to 2018, no retirement field"`), so the figure cannot
   be read as current. This is a labelling change and touches no score.
3. **Acquire GIPT before attempting the historical series**, not after.
4. **Disclose the vintage on REGIONAL figures too**, not only the national one — that is where
   the exposure is largest.
5. **Re-run `sweep()` whenever generation incidents are added.** Break-even for moving the second
   decimal is a generation score near 0.17 %, not the 1 % an earlier draft guessed.

## Provenance

- WRI Global Power Plant Database v1.3.0, `output_database/global_power_plant_database.csv`,
  CC BY 4.0. Russian subset: 545 plants, 228,220 MW. Fetched by `pipeline/build_assets.py`.
- GEM Global Integrated Power Tracker figures quoted from
  [POWER_SOURCE_RECONCILIATION.md](POWER_SOURCE_RECONCILIATION.md) (iteration 9), CC BY 4.0.
  **Not re-verified in iteration 10** — GIPT was not acquired, and these enter this document as
  sensitivity inputs only, never as a denominator.
