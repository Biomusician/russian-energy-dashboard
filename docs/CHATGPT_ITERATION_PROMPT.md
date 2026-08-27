# Prompt for iterating with ChatGPT

Paste everything below the line into ChatGPT. It is self-contained — it carries enough
state that ChatGPT does not need the repository to give useful direction, and it asks
for output in a form you can hand straight back to Claude Code.

---

I am building an open-source-only intelligence dashboard that tracks degradation of
energy infrastructure in western Russia and Belarus, aggregated to administrative
region, covering 2022 to the present. An MVP exists and works. I want your help
deciding what to do next, not help writing code.

## What exists

**Stack.** Python 3.13 stdlib-only ETL → static JSON → Vite + React + TypeScript +
MapLibre → Vercel static hosting. No database, no server, no API keys. The map renders
its own GeoJSON on a dark ground with no basemap, so the page makes zero external
network requests. A GitHub Action rebuilds the dataset daily and commits it, which
triggers redeploy.

**Data, all real and cited — nothing synthetic.**

| Layer | Count | Source | Licence |
|---|---|---|---|
| Administrative regions | 69 | Natural Earth 10m admin-1 | Public domain |
| Power plants | 432 (179,662 MW) | WRI Global Power Plant DB v1.3 | CC BY 4.0 |
| Substations ≥220 kV | 1,173 | OpenStreetMap | ODbL |
| Transmission ≥330 kV | 4,913 | OpenStreetMap | ODbL |
| Gas / oil pipelines | 2,553 / 178 | OpenStreetMap | ODbL |
| Struck facilities | 39 | Wikipedia strike tables | CC BY-SA |
| Events 2022–2026 | 128 (127 region-assigned), 137 citations | Wikipedia + curated CSV | Mixed |
| Refinery inventory | 30 refineries, 247.0 MTPA | Wikipedia | CC BY-SA |

**The index.** "Energy System Disruption Exposure Index" (ESDI), 0–100. It measures
*the share of tracked installed capacity sitting at facilities disrupted recently
enough to still be plausibly impaired*, weighted by evidence confidence, cause type,
and exponential time decay with a per-asset-class repair half-life.

It deliberately does **not** claim to measure capacity lost. Of 127 events, **zero**
have a quantified capacity effect in their sources — open reporting says *that* a
refinery was hit, almost never *how much* throughput went away. Exposure is what the
data honestly supports.

Per facility the strongest single live contribution wins rather than the sum, so a site
hit four times cannot exceed being fully disrupted.

Current values: ESDI 15.4; refining 31.0; oil logistics 11.0; electric power 0.0; gas
and coal have no capacity base and are excluded from the composite with weights
renormalised. Peak was 26.5 on 11 July 2026.

**Honesty features already built in.** The UI shows coverage (127 enumerated vs 305
reported strikes ≈ 42%) and the quantified-capacity ratio (0/127) at the same visual
weight as the headline number. Sectors without a denominator show "n/a — no capacity
base", never 0. Four requested regional-effect categories that cannot be derived render
as "not modelled" with reasons. Build-time parser warnings appear in the app. Automated
tests fail the build if out-of-scope fields (range-to-target, incident coordinates) or
occupied Ukrainian territory ever enter the data.

## Known weaknesses, my own assessment

1. **Repair half-lives (14–120 days by asset class) are pure assumption** with no
   evidence base, and are the single largest lever on every score.
2. **Refining denominator (247 MTPA / 30 refineries) is known low**, so refining
   exposure percentages are inflated by perhaps 20–30%.
3. **Coverage is 42%.** The missing events exist only in prose reporting.
4. **Electric power sub-index is effectively empty** — one event. Strikes on generation
   and grid are poorly represented in structured open sources.
5. **Regional scores are contributions to the national total, not regional
   intensities** — chosen to avoid a fake denominator, but not the intuitive reading.
6. **Sector weights** (refining 0.35, electric 0.30, oil logistics 0.20, gas 0.10, coal
   0.05) are a judgement, unvalidated.
7. **Confidence is derived from citation count**, so two outlets syndicating one wire
   report scores as "confirmed".

## Hard constraints — do not propose anything that breaks these

- **Public, open, unclassified sources only.** No commercial database scraping, no
  proprietary datasets.
- **No fabricated or estimated data presented as observed.** If a value is unknown it
  stays null and the UI says so. This is non-negotiable and is the project's main
  design principle.
- **Analytic and monitoring tool, not a targeting tool.** No current unit positions, no
  readiness, no vulnerability or defensive-gap assessment, no ranking of undamaged
  assets, no range-to-target data. Administrative-region aggregation is the deliberate
  ceiling on locational precision.
- **Free-tier hosting.** Static output, no server-side compute, no paid APIs.
- Windows development machine; no Docker, no Postgres.

## What I want from you

Work through these in order. Be specific and concrete — I will hand your answer to a
coding agent, so vagueness costs me a round trip.

1. **Challenge the index design.** Is exposure-with-time-decay the right formulation
   for this data? What are the strongest objections an energy analyst or an OSINT
   methodologist would raise? Is there a better-established measure I should be using
   instead, and if so what does it need that I do not have?

2. **Attack the repair half-lives.** Suggest evidence-based values for Russian refinery
   units, oil pumping stations, terminals, substations and thermal plants after
   drone/missile damage — with reasoning and any public sources you know of. Where the
   evidence does not exist, say so rather than guessing, and tell me how to express that
   uncertainty in the model (bands? sensitivity ranges? user-adjustable?).

3. **Name specific open data sources** for my biggest gaps, with URLs and a note on
   format and licence:
   - Russian electricity generation and grid disruption events
   - a complete Russian refinery inventory with regional assignment and capacity
   - gas processing and coal throughput baselines by region
   - refinery repair and restart durations

4. **Propose a defensible design for the four unmodelled regional-effect categories**
   (industrial impact, civilian electricity reliability, military-industrial
   implications, cross-region dependencies) — or argue that some of them should stay
   unmodelled, which is an acceptable answer. For each one you think is buildable, say
   what data it needs and what the indicator would actually mean.

5. **Rank the next five work items** by analytic value per unit of effort, assuming one
   developer with an AI coding agent and a few days.

6. **Tell me what I have got wrong** that I have not listed. Particularly: is measuring
   regional scores as contributions-to-national going to mislead readers, and is the
   42% coverage figure more honest or more damaging to present prominently?

Format your answer as numbered sections matching the above. For anything you want built,
write it as a concrete instruction I can paste to a coding agent, including which
assumption it replaces and how I would verify the result.
