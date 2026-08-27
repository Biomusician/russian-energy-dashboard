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
weight(event, t) = confidence × cause × status × 0.5 ^ (days_elapsed / half_life)
```

| Factor | Values | Rationale |
|---|---|---|
| `confidence` | confirmed 1.0 · probable 0.75 · possible 0.45 · unverified 0.2 | Evidence strength for whether the event occurred. Weak evidence is down-weighted, not discarded. |
| `cause` | strike/sabotage 1.0 · cyber 0.8 · technical 0.8 · sanctions 0.6 · maintenance 0.15 · unknown 0.7 | Scheduled maintenance is planned downtime, not degradation. Sanctions bite gradually rather than removing capacity outright. |
| `status` | active 1.0 · degraded 0.7 · repaired 0.1 · unknown 1.0 | Applied when a source explicitly states recovery state, overriding pure time decay. |
| `half_life` | 14–120 days by asset class | See §5. |

Events below a 0.01 contribution are dropped so the time series does not carry a long
meaningless tail.

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

Sector weights: refining 0.35, electric power 0.30, oil logistics 0.20, gas 0.10, coal
0.05. These are a judgement about systemic importance, not a measured quantity.

**Sectors without a capacity base are excluded and the weights renormalised**, rather
than counted as zero. Counting an unmeasurable sector as zero would treat "we cannot
measure this" as "nothing is wrong here", which understates the composite. There is a
test for this.

---

## 3. Denominators

| Sector | Base | Source |
|---|---|---|
| Refining | 247.0 MTPA | 30-refinery national inventory parsed from Wikipedia's *List of oil refineries* |
| Electric power | 179,662 MW | Sum of WRI plant capacities inside the AOI |
| Oil logistics | Refining base (proxy) | No published throughput denominator exists; flagged as a proxy in the emitted metadata |
| Gas, coal | *none* | Excluded from the composite |

**The refining denominator is known to be low.** Russia's full refining base is larger
than 247 MTPA; the inventory covers major refineries and omits smaller and
mini-refineries. Refining exposure is therefore measured against *tracked major
refining capacity* and is labelled as such. A larger denominator would lower the
reported exposure percentage.

Barrels-per-day figures convert at 0.136 tonnes/barrel (1 bbl/d = 49.6 t/yr).
Cross-check: Omsk at 22.0 MTPA in the strike table converts to ~443,000 bbl/d, matching
its published capacity within 3%. There is a test for this.

---

## 4. Regional scores

Regional exposure is each region's **contribution to the national figure** —
(disrupted capacity in region) ÷ (national base) — not disruption measured against the
region's own base.

This is deliberate. Our only regional refining capacities come from the set of
refineries known to have been struck, so a regional denominator built from them would
make every affected region 100% disrupted by construction. Framing regional scores as
contributions to the national total avoids the fake denominator entirely, is
interpretable ("how much of the national refining base is impaired here"), and makes
regional scores sum to the national one.

Where a genuine regional denominator exists — installed MW, from WRI — it is used for
the `generation_margin` effect indicator.

---

## 5. Repair half-lives — the weakest assumption

| Class | Days | Class | Days |
|---|---|---|---|
| Transmission line | 14 | Refinery | 45 |
| Oil/gas pipeline | 21 | Coal | 45 |
| Oil terminal, substation | 30 | Gas processing, thermal plant | 60 |
| LNG terminal | 90 | Nuclear, hydro | 120 |

These encode how quickly each class of asset is typically returned to service. **They
are assumptions, not measurements.** They are the single largest lever on every score:
halving the refinery half-life roughly halves refining exposure at any given date.

They were chosen so that a refinery unit hit today is ~50% "still impaired" at six
weeks and ~12% at three months, which is broadly consistent with reported repair
timelines — but no systematic dataset of Russian refinery repair durations was
consulted, because none is openly available. **This is the first thing to replace with
evidence.**

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

1. **"West of the SFD division"** is read as the six federal districts west of the
   Siberian Federal District boundary — Central, Northwestern, Southern, North
   Caucasian, Volga, Ural — plus Belarus. 69 regions. Change
   `AOI_FEDERAL_DISTRICTS` in `pipeline/config.py` to alter it.

   This is an interpretation. "SFD" most plausibly means Siberian Federal District, and
   its western boundary is the only natural east–west divider in that phrase. If
   Southern Federal District was meant, the AOI is wrong and should be revisited.

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
