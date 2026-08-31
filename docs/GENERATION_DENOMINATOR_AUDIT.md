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

Published baseline: **ESDI 17.86**, generation score **0.02 %** on **219,992 MW**, which implies
**44 MW** of decay-weighted disrupted generating capacity.

| Scenario | Denominator | Generation score | ESDI | Δ |
|---|---:|---:|---:|---:|
| Published (WRI, ~2018 census) | 219,992 MW | 0.0200 % | 17.8647 | — |
| GEM Aug-2026 operating basis | 251,687 MW | 0.0175 % | 17.8641 | −0.0006 |
| WRI less GEM-retired (the naive "−23 GW" fix) | 197,001 MW | 0.0223 % | 17.8653 | +0.0005 |
| Hypothetical: denominator halved | 109,996 MW | 0.0400 % | 17.8694 | +0.0047 |
| Hypothetical: generation disruption forced to **zero** | n/a | 0.0000 % | 17.8600 | −0.0047 |

**Maximum movement across every scenario, including deleting the sector outright: ±0.0047.**
The headline is published to two decimal places. The denominator error *cannot* move it.

Regionally the same holds, and more strongly: **no region has a non-zero generation intensity**,
so no regional figure is exposed to the denominator either.

### What that does and does not mean

It does **not** mean the denominator is correct. It means the denominator is currently
**analytically inert**, because measured generation disruption is 44 MW against a fleet of
~220 GW — four thousandths of one percent. The error is real; it has nowhere to propagate.

Two consequences, and they point opposite ways:

- **The scoring risk is nil**, so the §22 instruction not to deploy a correction costs nothing.
- **The disclosure defect is real and should be treated as one.** `electric_generation_mw:
  219992` is published in `snapshot.json` and rendered in the UI as a plain figure. It is a
  ~2018 census with no vintage attached, and a reader has no way to know that. That is fixable
  without touching a score — see Recommendation.

If generation disruption ever becomes material (a sustained campaign against power stations
rather than the substation-focused pattern to date), this conclusion expires immediately. The
sensitivity should be re-run whenever the generation sector score exceeds ~1 %.

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

1. **Do not change the denominator.** Confirmed by measurement, not by instruction alone — the
   maximum achievable movement is 20× smaller than the published precision.
2. **Disclose the vintage.** Publish the denominator's basis and census date alongside the value
   (`"basis": "WRI GPPD, Russian rows dated to 2018, no retirement field"`), so the figure cannot
   be read as current. This is a labelling change and touches no score.
3. **Acquire GIPT before attempting the historical series**, not after.
4. **Re-run this audit whenever the generation sector score exceeds ~1 %**, at which point the
   inertness argument no longer holds.

## Provenance

- WRI Global Power Plant Database v1.3.0, `output_database/global_power_plant_database.csv`,
  CC BY 4.0. Russian subset: 545 plants, 228,220 MW. Fetched by `pipeline/build_assets.py`.
- GEM Global Integrated Power Tracker figures quoted from
  [POWER_SOURCE_RECONCILIATION.md](POWER_SOURCE_RECONCILIATION.md) (iteration 9), CC BY 4.0.
  **Not re-verified in iteration 10** — GIPT was not acquired, and these enter this document as
  sensitivity inputs only, never as a denominator.
