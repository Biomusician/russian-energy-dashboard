# Methodology

Every parameter referenced here lives in [`methodology/scoring.json`](../methodology/scoring.json).
That file is the single source of truth; this document explains it.

---

## 1. What the index measures

**Energy System Disruption Exposure Index (ESDI)**, 0–100.

> The share of the tracked installed base sitting at facilities disrupted recently
> enough to still be plausibly impaired, weighted by evidence strength, cause, and
> elapsed time.

### Why exposure and not capacity loss

The brief asked for "estimated capacity unavailable". We cannot honestly produce it.

Open reporting on strikes against Russian energy infrastructure reliably states *that*
a facility was hit and *when*. It very rarely states how much throughput was removed or
for how long. Of 127 region-assigned events in the current dataset, **zero** carry a
quantified capacity effect from their sources.

Three options were available:

1. Estimate the loss per event. Rejected — it would be invention dressed as analysis,
   and the estimate would drive the headline number.
2. Score only the events that quantify their impact. Rejected — that scores almost
   nothing, and silently treats unquantified events as harmless.
3. Measure exposure: how much capacity sits at disrupted sites. **Chosen.** It uses
   only facts the sources actually assert (this facility was hit, on this date, and it
   has this published capacity), and it treats quantified and unquantified events
   consistently.

The index is named for what it measures, and the UI repeats the distinction next to the
headline figure. Where a source *does* quantify a loss, the figure is carried on the
incident record and displayed — it just is not what drives the score.

---

## 2. How a score is built

### Per event

```
weight(event, t) = confidence × cause × 0.5 ^ (days_elapsed / half_life)
```

| Factor | Values | Rationale |
|---|---|---|
| `confidence` | confirmed 1.0 · probable 0.75 · possible 0.45 · unverified 0.2 | Evidence strength for whether the event occurred. Weak evidence is down-weighted, not discarded. |
| `cause` | strike/sabotage 1.0 · cyber 0.8 · technical 0.8 · sanctions 0.6 · maintenance 0.15 · unknown 0.7 | Scheduled maintenance is planned downtime, not degradation. Sanctions bite gradually rather than removing capacity outright. |
| `half_life` | evidence-driven (§5) | Set by observed → estimated → modelled recovery evidence. |

Events below a 0.01 contribution are dropped so the time series does not carry a long
meaningless tail. When a facility carries no recovery record, an explicit `status` on
the event itself (repaired 0.1 · degraded 0.7 · active/unknown 1.0) still applies as a
fallback multiplier.

### Per facility

The **strongest single live contribution wins** — not the sum of a facility's events.

A refinery hit four times in a month is heavily disrupted, but it cannot be more than
100% disrupted. Summing would let repeated strikes on one site outweigh the entire rest
of the sector, which is both wrong and easy to do accidentally.

### Per sector

```
sector_exposure = Σ over facilities ( facility_capacity ÷ national_base × facility_weight )
sector_index    = min(1, sector_exposure) × 100
```

### Composite

```
ESDI = Σ (sector_weight × sector_index) ÷ Σ sector_weight     — over covered sectors only
```

Sector weights: refining 0.35, **electric generation 0.20**, **transmission 0.10**, oil
logistics 0.20, gas 0.10, coal 0.05. These are a judgement about systemic importance, not
a measured quantity. Electric power was split into two sectors in iteration 3 because
generation and transmission are not commensurable (see §3).

**Sectors without a capacity base are excluded and the weights renormalised**, rather
than counted as zero. Counting an unmeasurable sector as zero would treat "we cannot
measure this" as "nothing is wrong here", which understates the composite. There is a
test for this.

---

## 3. Denominators

| Sector | Base | Source |
|---|---|---|
| Refining | **280.6 MTPA** | 35-refinery national inventory: Wikipedia's *List of oil refineries* (30) + a sourced curated supplement (5), audited in iteration 2. A `refinery_reconciliation` block reports this as **85.0% of the ~330 MTPA national estimate** (gap 49.4), an explicit lower bound — not padded toward 330 with unlike facilities |
| Electric generation | **219,992 MW** | Sum of WRI plant capacities inside the AOI (thermal + hydro + nuclear + other), capacity basis like refining |
| Transmission | **event-burden, not capacity** | No open capacity denominator exists. A voltage-weighted count of disrupted substations/lines is scored against a documented **saturation constant of 8 weighted concurrent events = 100**. Network inventory (substations, lines) is *context, not a denominator*; the measure is never expressed as "% offline" |
| Oil logistics | Refining base (proxy) | No published throughput denominator exists; flagged as a proxy in the emitted metadata |
| Gas, coal | *none* | Excluded from the composite |

**Regional Disruption Intensity** (iteration 3) scores a region's disruption against its
**own** base, but only for sectors that have a regional denominator — **electric generation**
(regional installed MW) and **transmission** (regional saturation). Refining and oil
logistics have no per-region base, so they are reported as **missing, never scored as
zero**. This is distinct from **Contribution to National Exposure**, which uses the national
denominator. The two are separate, switchable rankings, never conflated.

**Refining denominator audit (iteration 2).** The base parse missed several major
refineries (Moscow, Ilsky, Slavyansk, TAIF-NK, Mari El). A curated, de-duplicated,
sourced supplement (`data/curated/refineries_supplement.csv`) added them: **247.0 →
280.6 MTPA**, which lowered refining exposure 34.3 → 30.2 and ESDI 16.7 → 14.7 — an
honest correction from a more complete denominator, not a re-tune. It is **still a lower
bound**: mini-refineries and some mid-size plants remain absent (the true national total
is ~330 MTPA), so refining exposure percentages remain somewhat inflated. Refining
exposure is measured against *tracked major refining capacity* and labelled as such.

Barrels-per-day figures convert at 0.136 tonnes/barrel (1 bbl/d = 49.6 t/yr).
Cross-check: Omsk at 22.0 MTPA in the strike table converts to ~443,000 bbl/d, matching
its published capacity within 3%. There is a test for this.

---

## 4. Regional scores — two explicit framings

There are **two** regional measures, kept separate and switchable in the UI (iteration 3),
because they answer different questions and conflating them was misleading:

**Contribution to National Exposure** — (disrupted capacity in region) ÷ (national base).
This is the default and the one that sums to the national ESDI. It is deliberate: our only
regional refining capacities come from the set of refineries known to have been struck, so
a regional refining denominator built from them would make every affected region 100%
disrupted by construction. Contribution avoids that fake denominator, and reads as "how
much of the *national* base is impaired here".

**Regional Disruption Intensity** — disruption measured against the **region's own** base,
but *only* for sectors that have a genuine regional denominator: **electric generation**
(regional installed MW, from WRI) and **transmission** (regional saturation). Sectors with
no per-region base — refining, oil logistics — are reported as **missing, never scored as
zero**, so "we have no regional denominator" is never silently rendered as "no disruption".

Treating unknown as zero here would be the same error §2 avoids in the composite; a test
enforces the missing-not-zero behaviour.

---

## 5. Recovery / reconstitution — incident-level, evidence over assumption

**Iteration 2 moved recovery from facility-level to incident-level.** Each disruption has
its own recovery trajectory; recovery from one strike never resolves a later one. A
facility hit repeatedly shows the strongest *still-live* incident, not a single state
smeared backwards through time. Recovery records in `data/curated/recovery.csv` key on
`incident_id`.

Recovery states: `impaired`, `partial_restart`, `substantially_restored`,
`fully_reconstituted`, `unknown`. **A partial restart ("operations resumed") is recorded
and displayed but never treated as full reconstitution, and never invents a
restored-capacity percentage.**

### Evidence precedence (rule-based, not a confidence multiplier)

Confidence decides *whether* a recovery claim overrides the model, via clear rules in
`methodology/scoring.json` (`recovery_precedence`), not by scaling a repair time by a
percentage:

1. **Observed full reconstitution**, confidence ≥ medium → closes the incident (capped
   at the residual from the reconstitution date).
2. **Observed substantial restoration**, ≥ medium → observed days become the horizon.
3. **A credible sourced estimate**, ≥ medium → its central value becomes the horizon
   (kind = estimated).
4. **Partial restart** → display only; records the restart date, does not accelerate
   decay, never implies full recovery.
5. **A low-confidence estimate** (< medium) → shown in the UI but does **not** drive the
   decay curve; scoring falls back to the modelled horizon.
6. Otherwise → the modelled per-sector fallback below.

The decay half-life is then set by whichever rule fired. Priority: **observed >
credible sourced estimate > modelled**. The `kind` (observed / estimated / modelled) is
carried on every recovery number and rendered in visibly different language. **A sourced
restart never looks like a guess, and a low-confidence guess never drives the index.**

A reconstitution horizon `H` (disruption → substantially restored) maps to a half-life
of `H / 3.3219`, so impairment is ~10% (the residual) at `H`.

### Modelled fallback horizons (days)

Used only when no observed or estimated evidence exists.

| Class | Horizon | Class | Horizon |
|---|---|---|---|
| Transmission line | 46 | Refinery | 150 |
| Oil/gas pipeline | 70 | Coal | 150 |
| Oil terminal, substation | 100 | Gas processing, thermal plant | 200 |
| LNG terminal | 300 | Nuclear, hydro | 400 |

These are **assumptions, not measurements**, and remain the single largest lever on any
score where no evidence exists. They were set so the implied half-lives match the
original MVP model (keeping the index continuous) — a refinery unit hit today is ~50%
"still impaired" at ~6 weeks and ~10% at ~5 months, broadly consistent with reported
timelines. No systematic dataset of Russian repair durations was consulted because none
is openly available. **Replacing these with curated observed durations is the highest-
value model improvement**, and the framework now makes each such replacement visible as
an "observed" record.

Current observed corpus (iteration 3): **6 recovery records → 3 distinct observed
episodes** (22, 72, 98 days; 3 full reconstitutions, 1 partial restart), plus estimates.
Records are deduplicated by `episode_id` — a multi-day strike is one episode, so the
iteration-2 "72/73-day" pair collapses to a single 72-day episode. The "typical recovery"
median is shown **only at ≥ 5 distinct episodes**; below that the UI reports
"records / episodes" and the honest label "< 5 episodes — no median", never a "typical".
The dashboard shows this whole breakdown rather than hiding how much rests on assumption.

## 5a. Crimea and the area of interest (iteration 2)

The blanket occupied-territory exclusion is narrowly, deliberately superseded **for
Crimea only**. Crimea is added as a **separately identified context unit** (`UA-CR`),
not a Russian federal subject:

- It is **internationally recognised as Ukraine** and is **excluded from the
  Russia+Belarus ESDI denominator and composite** — enforced in `build_index` and by a
  test. Its own regional exposure is computed and shown, but never feeds the national
  index.
- It **is** tracked in Recent, the timeline, Recovery, Sources, coverage and filters,
  because its disruption is relevant to the picture.
- The map **does not adjudicate sovereignty by colour or polygon membership**: Crimea
  gets a distinct dashed outline and neutral fill, and its status is stated in words in
  the hover card, legend and scope note.
- Every analytic/safety limit (no coordinates, no range-to-target, no facility-level
  asset deck, no targeting) applies to Crimea exactly as elsewhere. The exception is
  only to the geographic exclusion.
- The other four annexed oblasts (Donetsk, Luhansk, Zaporizhzhia, Kherson) remain fully
  excluded and resolve as `excluded_occupied`.

Surrounding **context countries and the Black Sea** are drawn from Natural Earth 50m as
display-only geography — no infrastructure is ingested and nothing there is scored. The
**Far Eastern Federal District remains structurally supported but analytically
disabled** pending sufficient event/coverage justification.

---

## 6. Regional effect categories

Derived from data:

| Category | Definition |
|---|---|
| Generation margin | Impaired MW ÷ region's own installed MW |
| Fuel production | Impaired refining MTPA ÷ national refining base |
| Logistics | Weighted count of impaired oil-logistics nodes |
| Heating season exposure | Impaired thermal generation, October–April only |
| Repair burden | Count of facilities with impairment still decaying |
| Recurrence | Mean recorded events per affected facility |

**Not modelled** — emitted as `null` with a reason, and displayed in the UI as "not
modelled" rather than omitted:

| Category | Why |
|---|---|
| Industrial impact | No open regional industrial-consumption data ingested |
| Civilian electricity reliability | No outage-duration or customer-minutes-lost source |
| Military-industrial implications | Would require mapping defence production to energy supply — out of scope |
| Cross-region dependencies | Requires grid topology and inter-regional flow data |

A missing row would read as "nothing happening", which is a different and wrong claim
from "we have no data". Hence the explicit null.

---

## 7. Assumptions

1. **Area of interest (locked in iteration 1).** Belarus, the six western Russian
   federal districts (Central, Northwestern, Southern, North Caucasian, Volga, Ural)
   and the **Siberian Federal District** — 79 regions. The original brief's ambiguous
   "west of the division" phrasing has been retired in favour of this explicit list.
   The **Far Eastern Federal District** is defined in `FE_REGIONS` but not enabled;
   adding `"Far Eastern"` to `AOI_FEDERAL_DISTRICTS` in `pipeline/config.py` turns it
   on with no other change. Buryatia and Zabaykalsky Krai are treated as Far Eastern
   (they were transferred there from Siberia in 2018), so they are currently out of
   scope; Natural Earth's metadata still miscalls them Siberian.

2. **Occupied Ukrainian territory is excluded** — Crimea, Sevastopol, and the four
   oblasts claimed in 2022. They are internationally recognised as Ukraine and are not
   Russian federal subjects. Natural Earth files Crimea and Sevastopol under Russia;
   the pipeline overrides that. There is a test.

3. **Natural Earth's `region` field is unusable** and is not used. It predates the 2010
   creation of the North Caucasian Federal District and files the entire Southern FD
   under "Volga". The federal-district mapping is carried in `pipeline/config.py`
   instead. Natural Earth's ISO codes for the two Moscow entities are also swapped
   relative to the official standard, so the join key is the region *name*.

4. **Lines are assigned to the region containing their midpoint.** A 500 kV line can
   cross four oblasts. Lines are counted, never used as a capacity input, so a
   misassigned line cannot move a score.

5. **Month-precision dates are anchored to the first of the month** for decay
   arithmetic. The precision is preserved on the record and shown in the UI.

6. **Attribution is reported, never asserted.** Events from strike reporting carry
   `attribution_confidence = "probable"`, reflecting media reporting of responsibility
   rather than independent confirmation.

7. **Unenumerated event series are counted, not invented.** Where a source says a
   facility was hit "at least 16 times" without listing dates, only the extractable
   bounding dates become events; the count is recorded separately and the UI flags the
   series as undercounted. There is a test.

---

## 8. Coverage

The dashboard states its own coverage in the top ribbon: **127 enumerated events
against a reported total of 305** (~42%).

The benchmark comes from the source article's own tabulation of reported strikes on
Russian oil facilities by war year. It is used only to state coverage and is never an
input to any score.

The gap is events reported only in prose. The main Wikipedia article covering attacks
in Russia is 298,000 characters with zero structured tables; parsing it into incidents
reliably is beyond MVP scope and would risk fabricated records.

**Sparse 2022 coverage is correct, not a gap.** The benchmark records 3 strikes in the
first war year and 13 in the second. A near-empty 2022 reflects reality.
