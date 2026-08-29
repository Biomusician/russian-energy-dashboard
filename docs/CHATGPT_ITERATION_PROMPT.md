# Prompt for iterating with ChatGPT (after iteration 4)

Paste everything below the line into ChatGPT. It is self-contained and asks for output
you can hand straight back to a coding agent.

---

I am developing an open-source-only intelligence dashboard tracking degradation of
energy infrastructure in **Belarus + western Russia + the Siberian Federal District +
occupied Crimea**, aggregated to administrative region, 2022–present. An MVP and four
iterations exist and are deployed. I want help deciding what to do next, not help writing
code.

## Stack & architecture (unchanged, working)

Python 3.13 stdlib-only ETL → static JSON → Vite + React + TypeScript + MapLibre →
Vercel static hosting. No database, no server, no API keys, and **no basemap/tiles** —
the map draws its own Natural Earth GeoJSON (regions, surrounding countries, ocean) on a
dark ground with HTML label overlays, so the deployed page makes **zero external runtime
requests**. A GitHub Action rebuilds the dataset daily.

## Current state (iteration 4)

- **Geography & scope:** 80 regions (six western Russian FDs + Siberian FD + Belarus) plus
  **Crimea**. The headline is the **Monitored-Area ESDI** (Belarus + monitored Russian
  regions + Crimea). Crimea is a separately-identified **occupied** unit — internationally
  Ukrainian, distinct dashed styling and sovereignty status — that **now contributes to the
  index** through the sectors where it has qualifying events and a compatible denominator
  (transmission, oil logistics), excluded from refining/generation for lack of a base.
  Inclusion is an analytic choice, never a sovereignty claim; Crimea is never the Russian
  choropleth. Other annexed oblasts stay excluded. Far Eastern FD defined but disabled.
- **Index (ESDI ~16.3):** share of *tracked capacity at disrupted sites*, evidence- and
  recency-weighted; not measured loss. Sectors: refining (capacity), electric generation
  (capacity/MW), transmission (event-burden vs a saturation constant), oil logistics
  (proxy). **Gas and coal are uncovered** (no defensible denominator).
- **Data:** ~1,950 assets + a curated infrastructure supplement; **134 events**;
  35-refinery / 280.6 MTPA inventory (85% of the ~330 estimate, disclosed).
- **Facet counts + data-driven UI (new):** the pipeline emits whole-corpus `facet_counts`
  per dimension (assets/lines/incidents kept separate). Left-rail filters show a control
  **iff the whole corpus has a record for it** — never off the moving slice — so nine dead
  toggles are hidden and any category reappears automatically once sourced data arrives.
- **Zero-count audit (new):** every taxonomy zero researched, classified and either
  ingested or hidden (see the audit doc). Resolved gaps: **LNG** (5 AOI terminals, cited,
  admin-region precision) and **gas processing** (Orenburg + Astrakhan GPPs, plus two
  documented drone strikes). Gas has records but stays score-0/uncovered — record count is
  not the sector score; incompatible units (LNG MTPA, processing/pipeline bcm) are never
  summed.
- **Also present from earlier iterations:** episode-modelled recovery with a 5-episode
  median gate; eight ranking metrics incl. contribution-vs-intensity + an Active Burden
  table; three-layer Effects + CREA observed economic context; Repair-burden tab; Sources
  evidence matrix; map decluttering + three camera presets.
- **90 tests pass; deployed to Vercel, daily GitHub Action refresh.**

## Known weaknesses (my own assessment)

1. **Gas is uncovered.** LNG liquefaction (MTPA), processing (bcm/y) and pipeline (bcm/y)
   are incompatible units I refuse to sum, so gas carries records but no score — the index
   understates gas-sector disruption (incl. real GPP strikes). No defensible single-basis
   gas denominator has emerged.
2. **LNG/gas/coal coverage is partial.** 5 LNG terminals + 2 GPPs are a floor, not a census.
   **Coal** infrastructure (Kuzbass, Baltic coal terminals) is a documented, un-ingested
   data gap; its toggle is hidden.
3. **Curated infrastructure is analyst-snapshotted**, admin-region placed (region centroid,
   `precision: "region"`), release-dated — not a live GEM/GGIT download.
4. **Observed-recovery episodes are thin (3 distinct)** — the "typical" median stays
   suppressed. Growing this from public restart reporting is still a top data gap.
5. **Transmission rests on a chosen saturation constant (8)** — a labelled convention, not a
   measured network limit; no open-source calibration yet. Crimea's two fresh substation
   strikes are a large share of the *active* transmission burden because that sector is thin.
6. **Zero causes remain** (sabotage, cyber, maintenance, unknown) and the unverified
   confidence tier — hidden after research (partisan-claim sourcing / no physical effect /
   out of scope / plausible absence). Documented, not cosmetically removed.
7. **The WebGL map canvas is pixel-unverified in my headless environment**; the canvas
   initialises with a live WebGL2 context and all tabs/geometry are verified via the DOM.

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

1. **A defensible gas measure.** Gas is uncovered because I refuse to sum LNG MTPA,
   processing bcm/y and pipeline bcm/y. Propose either (a) separate gas *sub-measures* kept
   distinct (e.g. an LNG-liquefaction exposure and a gas-processing exposure, each with its
   own basis), or (b) a single defensible basis, or (c) confirm gas should stay uncovered.
   Give the exact data model, the open sources, and how I'd verify it — without inventing a
   composite denominator.

2. **Finish the LNG/gas/coal inventory.** I ingested 5 LNG terminals and 2 GPPs as cited
   analyst snapshots. Give a reproducible way to complete the AOI inventory (more gas
   processing, coal export terminals, coal in Kuzbass) — ideally a GEM/GGIT download path
   that works in a headless daily job, or confirm analyst snapshots are the right call and
   give the exact facility list with capacities, regions and sources.

3. **Deeper event coverage beyond the Wikipedia table.** Most events come from one
   structured table; I just found real gas-plant strikes it omits. Give a low-fabrication
   method to systematically catch strikes on gas/LNG/coal/power infrastructure from prose
   reporting (Reuters, Astra, regional governors, General Staff) with a human-sign-off gate
   and mandatory citations.

4. **Recovery corpus growth** toward n≈15–20 distinct episodes from public restart/repair
   reporting, with exact fields, an `episode_id` mapping and a sign-off gate — still the
   change most likely to un-suppress the "typical recovery" median honestly.

5. **Rank the next five work items** by analytic-credibility value per unit of effort.

6. **What am I getting wrong that I haven't listed?** Especially: is bringing Crimea into
   the index through transmission + oil-logistics the right call, or does its large share of
   the thin transmission burden overstate it; and is the data-driven "hide zero toggles"
   behaviour ever hiding something a reader should still see?

Format as numbered sections. For anything you want built, write it as a concrete
instruction I can paste to a coding agent, including which assumption it replaces and how
I would verify the result.
