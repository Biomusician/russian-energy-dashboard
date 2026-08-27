# Prompt for iterating with ChatGPT (after iteration 3)

Paste everything below the line into ChatGPT. It is self-contained and asks for output
you can hand straight back to a coding agent.

---

I am developing an open-source-only intelligence dashboard tracking degradation of
energy infrastructure in **Belarus + western Russia + the Siberian Federal District**,
aggregated to administrative region, 2022–present, with **Crimea** shown separately as a
context unit. An MVP and three iterations exist and work. I want help deciding what to do
next, not help writing code.

## Stack & architecture (unchanged, working)

Python 3.13 stdlib-only ETL → static JSON → Vite + React + TypeScript + MapLibre →
Vercel static hosting. No database, no server, no API keys, and **no basemap/tiles** —
the map draws its own Natural Earth GeoJSON (regions, surrounding countries, ocean) on a
dark ground with HTML label overlays, so the deployed page makes **zero external runtime
requests**. A GitHub Action rebuilds the dataset daily.

## Current state (iteration 3)

- **Geography:** 80 regions (six western Russian FDs + Siberian FD + Belarus) plus
  **Crimea** as a separately-identified context unit (internationally Ukrainian, distinct
  dashed styling, excluded from the Russia+Belarus ESDI, tracked everywhere else). Far
  Eastern FD defined but disabled. Surrounding countries + Black Sea are display-only.
  Map now declutters by zoom (asset dots fade in above a minzoom; labels have deterministic
  priorities + greedy de-overlap) and has a third **"Current activity"** camera preset that
  frames only the admin regions with unresolved disruption (admin geography, no coordinates).
- **Data:** ~1,950 assets; **132 events** (now episode-modelled — a multi-day strike is one
  episode, `episode_id` + start/end dates); **35-refinery / 280.6 MTPA** inventory.
- **Index (ESDI 15.86):** share of *tracked capacity at disrupted sites*, evidence- and
  recency-weighted. **Not measured capacity loss** (0/132 events carry a quantified loss).
- **Electric power is split into two sectors** with different bases:
  **electric generation** (capacity/MW basis, currently 0.07) and **transmission**
  (an **event-burden** measure — voltage-weighted disrupted-node count against a documented
  saturation constant of 8 weighted concurrent events = 100; network inventory is *context,
  not a denominator*; currently 11.92, from a recent 500 kV strike). Never "% offline".
- **Recovery** is incident/episode-level with rule-based evidence precedence. The "typical
  recovery" median is gated on **≥5 distinct episodes**; with **3** observed episodes today
  it is honestly suppressed ("< 5 episodes — no median"). Partial restart ≠ full
  reconstitution; low-confidence estimates shown but not scored.
- **Rankings** offer eight explicit switchable metrics, including **Contribution to
  National Exposure** (national denominator) vs **Regional Disruption Intensity** (regional
  denominator), plus a transparent sortable **Active Burden table** (unresolved / oldest /
  median age / backlog / sectors) instead of another composite. Regional intensity scores
  only sectors that have a regional denominator (generation MW, transmission saturation);
  refining/oil-logistics are flagged **missing, never zero**.
- **Effects** is now three visibly-badged layers — **observed effect / structural exposure
  (incl. region population as "potentially exposed") / analytic proxy** — so a proxy never
  reads as a measurement. **CREA** fossil-fuel export revenue is ingested as a deterministic
  monthly-snapshot CSV (reporting month, snapshot date, source, revision status) and shown
  as **observed economic context, explicitly not attributed to strikes**.
- **Costs → "Repair burden":** leads with the observed **reconstitution burden** (open
  facilities, summed remaining reconstitution days, partial vs full) — useful without
  inventing dollars. A **Sources evidence matrix** shows event/recovery/cost coverage per
  sector to separate "little data" from "low disruption".
- **77 tests pass; deterministic rebuild confirmed.**

## Known weaknesses (my own assessment)

1. **Observed-recovery episodes are still thin (n=3 distinct)** — the median stays
   suppressed. Growing this corpus from public restart reporting is still the #1 data gap.
2. **Transmission exposure rests on a chosen saturation constant (8).** It is labelled a
   proxy and produces a bounded, comparable signal, but the constant is a convention, not a
   measured network limit. I have no open-source calibration for it.
3. **Refining denominator held at 85% (280.6 / ~330 MTPA)** as a disclosed lower bound. I
   chose not to pad toward 330; refining exposure percentages are against tracked capacity.
4. **Regional intensity only covers 2 sectors** (generation, transmission) — the ones with a
   regional denominator. Refining and oil-logistics have no per-region base, so a
   refinery-heavy region shows them as "missing", not scored.
5. **CREA context is only 2 metrics and manually snapshotted.** It is honest but sparse, and
   the monthly snapshot is analyst-maintained rather than automated.
6. **Costs has no dollar figures** (rarely public); the reconstitution burden stands in.
7. **The WebGL map canvas is pixel-unverified in my headless environment** (the pane doesn't
   composite, so raster screenshots time out). The canvas *does* initialise with a live
   WebGL2 context, and all tabs/geometry are verified through the rendered DOM.

## Hard constraints — do not propose anything that breaks these

- Public, open, unclassified sources only. Never present an estimate as an observation
  (unknown stays null and the UI says so). Analytic/monitoring tool, **not targeting**:
  no unit positions, readiness, vulnerability/gap analysis, ranking of undamaged assets,
  range-to-target, ingress/egress, tactical routing, or precise incident coordinates.
  Crimea is an exception only to the *geographic* exclusion, not to these limits.
  Free-tier static hosting; Windows dev machine, no Docker/Postgres.
- **Credibility and interpretability over feature count.** The dashboard has enough
  features. Prefer fixing a denominator, tightening an evidence category, or making a
  measure more legible to adding another view. The evidence ladder is
  **observation > sourced estimate > transparent proxy > model > unknown** — but never
  force a weaker category where "unknown" is the more defensible answer.

## What I want from you (numbered, concrete — I paste your answer to a coding agent)

1. **Recovery corpus growth.** Give a concrete, low-fabrication-risk method to grow the
   observed *distinct-episode* restoration corpus toward n≈15–20 from public reporting
   (restart/repair dates in Reuters, Moscow Times, regional operators), with exact fields,
   an `episode_id` mapping, and a human-sign-off gate. This is the change most likely to
   un-suppress the median honestly.

2. **Transmission saturation constant.** Is there any open-source way to *calibrate or
   justify* the "8 weighted concurrent events = 100" constant (e.g. historical simultaneous
   substation-strike counts), or should it remain an explicitly-labelled convention with a
   sensitivity note? If calibratable, give the sourcing and the exact method.

3. **Regional intensity denominators.** Can per-region **refining capacity** and
   **oil-logistics throughput** be sourced openly and reproducibly, to complete the regional
   intensity measure for those two sectors? If yes, give the sources and the data model; if
   no, confirm that "missing, not zero" is the right permanent treatment.

4. **CREA breadth & cadence.** Which additional CREA public products are reproducibly
   snapshot-ingestible (refinery throughput, price-cap compliance, discount to Brent), at
   what cadence, and how should each be labelled to stay clearly *observed context* rather
   than *strike effect*? Should the monthly snapshot stay analyst-maintained or is there a
   stable machine-readable export now?

5. **Rank the next five work items** by analytic-credibility value per unit of effort.

6. **What am I getting wrong that I haven't listed?** Especially: is the transmission
   event-burden model defensible; is splitting "contribution" from "intensity" actually
   clearer to a reader or just more knobs; and is the three-layer Effects framing
   (observed / structural / proxy) the right way to stop a proxy reading as a measurement?

Format as numbered sections. For anything you want built, write it as a concrete
instruction I can paste to a coding agent, including which assumption it replaces and how
I would verify the result.
