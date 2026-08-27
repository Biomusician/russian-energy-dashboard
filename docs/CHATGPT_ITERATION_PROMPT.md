# Prompt for iterating with ChatGPT (after iteration 2)

Paste everything below the line into ChatGPT. It is self-contained and asks for output
you can hand straight back to a coding agent.

---

I am developing an open-source-only intelligence dashboard tracking degradation of
energy infrastructure in **Belarus + western Russia + the Siberian Federal District**,
aggregated to administrative region, 2022–present, with **Crimea** shown separately as a
context unit. An MVP and two iterations exist and work. I want help deciding what to do
next, not help writing code.

## Stack & architecture (unchanged, working)

Python 3.13 stdlib-only ETL → static JSON → Vite + React + TypeScript + MapLibre →
Vercel static hosting. No database, no server, no API keys, and **no basemap/tiles** —
the map draws its own Natural Earth GeoJSON (regions, surrounding countries, ocean) on a
dark ground with HTML label overlays, so the deployed page makes **zero external runtime
requests**. A GitHub Action rebuilds the dataset daily.

## Current state (iteration 2)

- **Geography:** 80 regions (six western Russian FDs + Siberian FD + Belarus), plus
  **Crimea** as a separately-identified context unit — internationally Ukrainian,
  distinct dashed styling, **excluded from the Russia+Belarus ESDI**, but tracked in
  Recent/timeline/Recovery/coverage. The other four annexed oblasts stay fully excluded.
  Far Eastern FD is defined but disabled. Surrounding context countries + Black Sea are
  drawn as display-only geography.
- **Data:** ~1,950 assets; **133 events** with citations; **35-refinery / 280.6 MTPA**
  national inventory (audited up from 247).
- **Index (ESDI, now 14.7):** share of *tracked capacity at disrupted sites*, evidence-
  and recency-weighted. **Not measured capacity loss** (0/133 events carry a quantified
  loss). ESDI fell 16.7 → 14.7 this iteration, mostly from the honest denominator audit.
- **Recovery is now incident-level** with **rule-based evidence precedence**: observed
  full/substantial reconstitution (conf ≥ medium) > credible sourced estimate (≥ medium)
  > modelled fallback. A **partial restart is never treated as full reconstitution**; a
  **low-confidence estimate is shown but does not drive scoring**. Observed corpus grew
  from n=1 to **n=4** (22, 72, 73, 98 days; 1 full reconstitution, 1 partial restart, 2
  estimates). The median un-suppresses only at n≥3.
- **Four separated concepts:** exposure, assessed degradation (quantified only),
  recovery, confidence/coverage. Seven analytical tabs. Observed/estimated/modelled have
  a consistent visual language (green solid / amber half / muted dashed).

## Known weaknesses (my own assessment)

1. **Observed-recovery n=4 is still thin** (one is a duplicated day-range strike, so ~3
   distinct). Median-of-few.
2. **Electric-power exposure ≈0.** Curated substation events decayed out and carry
   transmission throughput, not generation MW, so they don't move a generation-MW index.
3. **Refining denominator (281 MTPA) is still a lower bound** vs ~330 MTPA true;
   refining exposure percentages remain somewhat inflated.
4. **Strategic/war-sustainment indicators are still a refining/logistics-exposure
   proxy** — no CREA / external economic data ingested yet (no stable public machine-
   readable endpoint found; CREA revises historical figures).
5. **Costs tab is empty** of dollar figures (per-facility repair costs rarely public).
6. **Regional scores are contributions to the national total**, not regional
   intensities.
7. **The WebGL map canvas is visually unverified** in my environment (headless has no
   WebGL); the HTML overlays and all tabs are screenshot-verified.

## Hard constraints — do not propose anything that breaks these

- Public, open, unclassified sources only. Never present an estimate as an observation
  (unknown stays null and the UI says so). Analytic/monitoring tool, **not targeting**:
  no unit positions, readiness, vulnerability/gap analysis, ranking of undamaged assets,
  range-to-target, ingress/egress, tactical routing, or precise incident coordinates.
  Crimea is an exception only to the *geographic* exclusion, not to these limits.
  Free-tier static hosting; Windows dev machine, no Docker/Postgres.

## What I want from you (numbered, concrete — I paste your answer to a coding agent)

1. **Electricity sub-index.** Substation strikes (transmission throughput) don't fit a
   generation-MW denominator. Design the most defensible open-source-only approach:
   a separate transmission-disruption sub-measure? a customer-minutes proxy? or keep
   electric ≈0 until generation-plant strikes with MW arrive? Give the exact data model
   and how to source it.

2. **CREA / economic ingestion.** Tell me precisely which CREA public products
   (Russia fossil-fuel export tracker, refinery-throughput) are reproducibly ingestible
   today, their cadence and format, and how to represent them honestly (observed
   external indicator vs inferred consequence of strikes — the data usually can't prove
   causation). If no stable machine-readable export exists, propose a deterministic
   monthly-snapshot ingestion instead.

3. **Refinery denominator.** Should I push to the full ~330 MTPA (adds many mini-
   refineries and curation) or hold the audited 281 MTPA lower bound with the caveat
   shown? If pushing, give a sourced list of the missing Russian refineries with
   capacities.

4. **Recovery corpus.** Give a concrete, low-fabrication-risk method to grow the observed
   restoration corpus toward n≈15–20 from public reporting (Reuters/Moscow Times restart
   dates), with the exact fields and a human-sign-off gate.

5. **Rank the next five work items** by analytic value per unit of effort.

6. **What am I getting wrong that I haven't listed?** Especially: is the incident-level
   recovery precedence sound; is the contributions-to-national regional framing
   misleading; and is the Crimea treatment (tracked but excluded, dashed styling,
   explicit status) the right call?

Format as numbered sections. For anything you want built, write it as a concrete
instruction I can paste to a coding agent, including which assumption it replaces and how
I would verify the result.
