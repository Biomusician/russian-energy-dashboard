# Prompt for iterating with ChatGPT (after iteration 1)

Paste everything below the line into ChatGPT. It is self-contained and asks for output
you can hand straight back to a coding agent.

---

I am developing an open-source-only intelligence dashboard tracking degradation of
energy infrastructure in **Belarus + western Russia + the Siberian Federal District**,
aggregated to administrative region, 2022–present. An MVP and one iteration exist and
work. I want help deciding what to do next, not help writing code.

## What exists

**Stack.** Python 3.13 stdlib-only ETL → static JSON → Vite + React + TypeScript +
MapLibre → Vercel static hosting. No database, no server, no API keys, no basemap (the
choropleth is the map; zero external requests at runtime). A GitHub Action rebuilds the
dataset daily.

**Geography (iteration 1).** 79 administrative regions: six western Russian federal
districts + Siberian FD + Belarus. The Far Eastern FD is defined but not enabled (one
config line). Occupied Ukrainian territory is excluded and tested against.

**Data, all real and cited — nothing synthetic.** ~1,924 infrastructure assets (WRI
power plants, OSM substations/lines), 128 disruption events with 137+ citations
(Wikipedia strike tables + curated CSV), 30-refinery national inventory (247 MTPA).

**The index.** "Energy System Disruption Exposure Index" (ESDI), 0–100, currently 16.7.
It measures *the share of tracked capacity sitting at facilities disrupted recently
enough to still be plausibly impaired*, weighted by confidence, cause, and an
evidence-driven time decay. **It deliberately does NOT claim to measure capacity lost**
— 0 of 128 events carry a quantified capacity effect in their sources, and the ribbon
says so.

**Four separated concepts:** exposure, assessed degradation (quantified only),
recovery/reconstitution, and confidence/coverage.

**Recovery framework (iteration 1, the big new thing).** Decay half-life is
evidence-driven in priority order **observed > estimated > modelled**, the kind carried
on every number so a sourced restart never looks like a guess. Confirmed reconstitution
collapses a facility's contribution. Currently: **1 observed** restoration (Kuibyshev,
~72 days), **2 estimated** windows (Omsk, Moscow Refinery), **32 modelled** fallback.

**UI.** 7-tab right panel — Overview, Rankings (affected regions only, 6 metrics),
Recent (Top 10 with deterministic template summaries), Recovery, Effects (physical +
strategic/war-sustainment proxies + "not modelled" rows), Costs (schema foundation,
near-empty), Sources/Confidence. Observed/estimated/modelled have a distinct visual
language (green solid / amber half / muted dashed).

## Known weaknesses (my own assessment)

1. **Modelled reconstitution horizons** are still assumptions and the biggest lever
   where no evidence exists (now flagged per facility).
2. **Observed-recovery sample is n=1**, so "median observed restoration" is a
   median-of-one, shown with its n.
3. **Siberian event coverage is n=1** (Omsk) — the region is populated structurally but
   barely has events yet.
4. **Coverage is ~42%** overall; missing events exist only in prose reporting.
5. **Electric power ≈ 0**, **gas/coal have no capacity denominator**.
6. **Strategic/war-sustainment indicators are a refining/logistics-exposure proxy**, not
   observed revenue.
7. **Regional scores are contributions to the national total**, not regional
   intensities.
8. **Costs tab is near-empty** — per-facility repair costs are rarely public.
9. Refining denominator (247 MTPA) is low, inflating refining-exposure percentages.

## Hard constraints — do not propose anything that breaks these

- **Public, open, unclassified sources only.** No commercial-DB scraping.
- **Never present an estimate as an observation.** Unknown stays null and the UI says
  so. This is the project's core principle.
- **Analytic/monitoring tool, not targeting.** No current unit positions, readiness,
  vulnerability/gap analysis, ranking of undamaged assets, range-to-target,
  ingress/egress, or tactical sustainment routing. Admin-region aggregation is the
  deliberate precision ceiling.
- **Free-tier hosting**, static output, no server compute.
- Windows dev machine; no Docker/Postgres.

## What I want from you (numbered, concrete — I paste your answer to a coding agent)

1. **The recovery framework.** Critique the observed>estimated>modelled decay design.
   Should a single observed restart really set a facility's whole decay curve? How
   should recovery-record confidence discount an estimate? Should medians be suppressed
   below a minimum sample size, and if so what n?

2. **Modelled reconstitution horizons.** Propose evidence-based full-reconstitution
   horizons (days) for: refinery CDU vs secondary units, oil pumping station, oil
   terminal/storage, gas processing, thermal plant, substation, transmission line. Cite
   public evidence (Reuters/Moscow Times restart reporting, CREA, etc.) where it exists,
   and say "no evidence — keep as assumption" where it does not.

3. **CREA integration.** I want to replace the proxy strategic indicators with observed
   data from the Centre for Research on Energy and Clean Air (Russian fossil-fuel export
   revenue + refinery throughput). Tell me exactly which CREA datasets/endpoints to use,
   their update cadence and format, and how to express the resulting indicators
   (revenue pressure, refining utilization) honestly with dates and provenance.

4. **Growing coverage past 42%.** Give a concrete, low-fabrication-risk method to
   extract the prose-only strike events (the main Wikipedia "Attacks in Russia" article
   is 298k chars, no tables) into structured records with mandatory human sign-off.

5. **Rank the next five work items** by analytic value per unit of effort (one developer
   + AI coding agent, a few days each).

6. **What am I getting wrong that I haven't listed?** Specifically: is the
   contributions-to-national regional framing misleading; is showing a median-of-one
   defensible; and should the Far Eastern FD be enabled now or left off?

Format as numbered sections matching the above. For anything you want built, write it as
a concrete instruction I can paste to a coding agent, including which assumption it
replaces and how I would verify the result.
