# Non-conflict recovery: options (iteration 16)

**Research only. Nothing here is deployed.** The country systems publish observed recovery
evidence where a source states it and nothing modelled. Choosing a model is an owner decision
(`GLOBAL_METHODOLOGY.md` §8). This document gathers the evidence that decision needs.

The figures below were measured on 2026-10-31 from `data/curated/systems/{us,ca}/events.json`,
using a throwaway script that is not part of the build. They are a snapshot for this argument,
not live numbers. `CURRENT_STATE.md` holds the live numbers.

## 1. The question

The theatre's ESDI decays an event's weight over an assumed reconstitution horizon, because
open reporting almost never says when a struck facility came back. Would the same machinery fit
the United States and Canada, where outages are mostly weather and equipment failure, and the
operators, utilities and regulators who run them often say when they came back?

## 2. What is actually observed

### Coverage of recovery evidence

| | US (138 records) | Canada (26 records) |
|---|---|---|
| Observed recovery evidence (a cited report of restart or restoration, not an estimate) | 64 | 22 |
| Sourced estimate only | 10 | 2 |
| Researched, no public evidence | 7 | 0 |
| Not yet researched | 57 | 2 |

### US recovery evidence by cause and class

| Cause × class | Records | Observed | Not yet researched |
|---|---|---|---|
| natural hazard × grid | 53 | 24 | 28 |
| technical × refining/processing | 14 | 8 | 5 |
| technical × pipelines | 14 | 10 | 2 |
| unknown × refining/processing | 9 | 0 | 5 |
| technical × LNG/terminals | 8 | 5 | 0 |
| natural hazard × production | 8 | 4 | 4 |
| technical × grid | 7 | 2 | 5 |
| every other cell | ≤ 6 each | | |

- **Twelve of the sixteen US cause × class cells hold six records or fewer.**
- **Canada has one cell with more than three records:** natural hazard × grid, 18 records.

### Days from event to the first observed recovery evidence

This measures the time to the *first* report of recovery, not to full recovery. Most
facility evidence is a *partial* restart, so it is a lower bound on recovery time, not an
estimate of it.

| Class | US n | US median (range) | CA n | CA median (range) |
|---|---|---|---|---|
| grid | 24 | 4 (0–11) | 7 | 3 (0–8) |
| pipelines | 15 | 17 (4–199) | 1 | 7 |
| refining/processing | 7 | 7 (0–220) | 1 | 77 |
| LNG/terminals | 8 | 3 (1–248) | — | — |
| production | 3 | 4 (3–6) | 2 | 5 |
| coal | 2 | 399 (339–459) | — | — |

### How recovery is described

- **Kinds of evidence:** the US's 64 observed records are 5 full restarts, 14 service-restored, 31
  partial restarts, 12 partial restorations and 2 "no supply lost". Full
  reconstitution is observed for a small minority of facility events.
- **Units are not one quantity.** The US records report customers (48 records), MW (9), b/d and
  bbl/d (9), bcf/d (3), Mt/y LNG (2), "people" (2), and percentages of Gulf production. No unit
  can be decayed against a denominator the way the ESDI's capacity shares are.
- **End dates:** 29 US records and 5 Canadian records carry a sourced `date_end`.

## 3. Options

### A. No modelled decay

An event stays unresolved until a source reports recovery, and the observed date is used as
reported.

- **Stale unresolved events.** Of the 57 unresearched US records, 28 are hurricane grid
  outages. Research says those usually restore within days, but none of these 28 has a
  restoration source yet. Under A they read as unresolved indefinitely.
  The mitigation is a research task, not a model: "not yet researched" is already a distinct
  state, and the UI says so. Research effort goes where a reader would otherwise be misled.
- **Arbitrary-fallback risk:** none.
- **Comparability:** honest but uneven. A country with better restoration reporting looks
  "more recovered". This is the same reporting-environment caveat that already governs counts,
  and it is already stated beside them.
- **Sparse samples:** irrelevant, because nothing is fitted.

### B. A class-specific duration, estimated from the data

- **Stale events:** solved on paper, by asserting that something nobody has reported has happened.
- **Fallback risk:** high. Grid's 24 US observations would support an estimate. Every other
  class has 15 or fewer, and their ranges span two orders of magnitude (pipelines 4–199 days).
  A median of 17 days applied to a pipeline that took 199 is the
  estimate-presented-as-observation this project exists to avoid.
- **Comparability:** a fitted US curve applied to Canada assumes the two share outage dynamics,
  which nothing here tests.
- **Sparse samples:** the dominant problem. The figures also measure the first report of
  recovery, a biased stand-in for the duration itself.

### C. A fallback by cause × class

C has B's problems, made worse. Most cells hold six records or fewer, so C would rest on
samples of 1–6, and it multiplies the number of parameters an owner has to defend.

### D. A sourced estimate for one event, where a source gives one

An operator's "expected back by …" or a regulator's estimated restoration time, shown and
labelled as an estimate.

- **Already done.** It is the `estimate` kind (10 US and 2 Canadian records) and travels with
  its label.
- **Fallback risk:** none, because nothing is filled in where no source gives an estimate.
- **Weakness:** an estimate that later proved wrong stays visible until research replaces it.
  Re-checking estimates belongs in the research cadence.

### E. Hybrid, observed first

Observed recovery where it exists, then a sourced estimate (D), then a modelled fallback (B or C)
for what remains, each labelled by kind.

- **The `kind` machinery already supports it.** The theatre does this, with the modelled tier
  published alongside its sensitivity.
- **Its value depends entirely on the modelled tier,** which inherits B's and C's
  sparse-sample problems for every class except US grid.
- **It only makes sense once a country number exists for the model to feed.** No country
  index exists, and none is approved.

## 4. Recommendation (not deployed)

**Keep A + D: observed recovery, plus sourced estimates labelled as estimates. No modelled
decay.** This is the current behaviour, so adopting it changes no published value.

1. **The country systems publish no index**, so a decay model would have nothing to decay. Its
   only visible effect would be to move events from "no recovery evidence" to
   "probably recovered" without a source. That is the estimate-as-observation failure.
2. **The data cannot support B, C or E yet.** Only one cell, US grid with 24 observations,
   comes near a usable sample, and even there the figure is time to the first report.
3. **Coverage, not a model, is the fix for the stale-unresolved problem.** Put the next
   research effort on the 28 unresearched US hurricane grid records and the 5 unresearched
   US refinery records. Together they are 33 of the 57 unresearched records.

**Revisit B, C or E only if both hold:**

- the owner approves a country index that needs a recovery term;
- each class to be modelled has around 30 or more observed full-recovery durations, not
  first-report durations.

At the current rate of evidence, that is several sweeps away for every class except grid.

## 5. Owner decisions this leaves open

1. Adopt A + D formally as the non-conflict recovery rule. It is the de facto rule today, but
   it was never decided.
2. Should an unresolved non-conflict event age out of "unresolved" after a stated period, with
   no claim that it recovered, purely as a display policy? This would be the recovery
   counterpart of the source re-check limits. It must never alter acceptance or numbers.
