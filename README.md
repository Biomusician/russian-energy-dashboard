# Energy Disruption Monitor — Western Russia, Siberia & Belarus

An open-source-only dashboard tracking publicly reported degradation of energy
infrastructure across **Belarus, western Russia and the Siberian Federal District**,
aggregated to administrative region (80 monitored units, Crimea included), from 2022 to the present.

Every number traces to a public source. Where the data does not support a number, the
dashboard says so rather than estimating one. Observed facts, external estimates and
modelled assumptions are kept visibly distinct throughout.

Crimea is shown as a **separately identified occupied unit** — internationally recognised
as Ukraine, under Russian occupation, distinct styling and status. Since iteration 4 it
**contributes to the headline Monitored-Area index** (through the sectors where it has
qualifying events and a compatible denominator) while never being labelled a Russian region.
Surrounding countries and the Black Sea are drawn as display-only context.

> **Status:** MVP + iterations 1–4 + **iteration 5** (a first-class analytic-vs-context scope
> model; a continental oil/gas trunk **network context** layer + major rivers + a broadened,
> data-driven country layer, all lazy-loaded and never scored; **175 events / ~57% coverage**
> via a candidate-event queue; **6 recovery episodes** with the median now shown; LNG/gas/coal
> inventory depth with gas & coal kept honestly uncovered; and a `schema_version` +
> `data_manifest.json` data contract). See
> [docs/ITERATION_5_REVIEW.md](docs/ITERATION_5_REVIEW.md) and
> [docs/ZERO_COUNT_AUDIT.md](docs/ZERO_COUNT_AUDIT.md).

**Live site:** **https://russian-energy-dashboard.vercel.app** · **Deployment:** static
Vite + MapLibre on Vercel, rebuilt daily by a GitHub Action; push-to-`main` auto-deploys.
Zero external runtime requests. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Run locally:
`.venv\Scripts\python.exe -m pipeline.run` then `cd web && ..\scripts\npm.cmd run dev`.

---

## What it is, precisely

The headline figure is the **Energy System Disruption Exposure Index (ESDI)**. It
answers one question:

> What share of the tracked installed base sits at facilities disrupted recently
> enough to still be plausibly impaired, weighted by evidence strength, cause, and
> time elapsed?

**It is not a measurement of lost throughput or lost generation.** Open reporting
almost never states how much capacity a given event removed. Of the 175 region-assigned
events currently in the dataset, **zero** carry a quantified capacity effect — and the
dashboard shows that ratio in its top ribbon rather than burying it. An exposure
measure is what this data can honestly support; a "capacity offline" figure is not.

### Scope boundary

This is a damage-assessment and monitoring tool. It models publicly reported disruption
to energy infrastructure, aggregated to administrative region. It contains no current
unit positions, no readiness state, no vulnerability or defensive-gap assessment, and
no ranking of undamaged assets.

One upstream source (the Wikipedia strike table) publishes a "distance from
Ukrainian-controlled territory" column for each facility. **The parser deliberately does
not read it.** It describes reach rather than damage, contributes nothing to a
degradation assessment, and is the one field in that table with obvious
operational-planning value. `tests/test_pipeline.py` fails the build if any
range-to-target field ever appears in emitted data.

---

## Architecture

```
data/curated/*.csv ──┐
Natural Earth ───────┤
WRI Power Plant DB ──┼──► pipeline/ (Python 3.13, stdlib only) ──► data/processed/*.json
OpenStreetMap ───────┤                                                      │
Wikipedia ───────────┘                                                      │
                                                                web/public/data/ (mirrored)
                                                                            │
                                                    web/ (Vite + React + TS + MapLibre)
                                                                            │
                                                                    Vercel (static)
```

Three deliberate choices:

**No database.** The dataset is ~1,980 assets (plus a curated infrastructure supplement) and ~175 events. Static JSON regenerated
by a scheduled job *is* the backend. A Postgres instance here would be infrastructure
to maintain in exchange for nothing.

**No basemap.** The map renders our own GeoJSON on a flat dark ground. Every tile
provider worth using needs an API key, a billing relationship, or an attribution
banner, and streets and terrain add nothing underneath an administrative choropleth.
The deployed page therefore makes **zero external network requests** and works offline.

**Stdlib-only ETL.** No pandas, geopandas, shapely or requests. Point-in-polygon,
Douglas–Peucker simplification and Wikitext parsing are each a few dozen readable
lines. The GitHub Action needs no build toolchain and cannot break on a wheel that
stops publishing for Python 3.13.

---

## Setup

Requires Python 3.13 and Node 24. Node is vendored under `tools/node/` (gitignored) and
reached through `scripts/node.cmd` / `scripts/npm.cmd`, so nothing touches PATH.

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install pytest
```

Build the dataset — this downloads from Natural Earth, WRI, Overpass and Wikipedia, and
caches everything under `data/raw/` (gitignored):

```bash
.venv\Scripts\python.exe -m pipeline.run
```

Run the dashboard:

```bash
cd web && ..\scripts\npm.cmd install && ..\scripts\npm.cmd run dev
```

Run the tests:

```bash
.venv\Scripts\python.exe -m pytest
```

---

## Data flow

| Stage | Location | Committed? |
|---|---|---|
| Raw downloads | `data/raw/` | No — large, regenerable, third-party licensed |
| Analyst-curated events | `data/curated/incidents.csv` | Yes — this is source truth |
| Scoring parameters | `methodology/scoring.json` | Yes |
| Processed output | `data/processed/` | Yes — so Vercel can serve it without running Python |
| Frontend copy | `web/public/data/` | Yes — mirrored by the pipeline |

`data/processed/` is a **build artifact that is nonetheless committed**, because Vercel
builds only the frontend. A clean rebuild is deterministic given the same upstream
sources. Never hand-edit processed JSON; fix the curated source and rebuild.

---

## Sources

| Layer | Source | Licence |
|---|---|---|
| Administrative boundaries | Natural Earth 10m admin-1 | Public domain |
| Generation (MW, fuel, location) | WRI Global Power Plant Database v1.3 | CC BY 4.0 |
| Substations, transmission, pipelines | OpenStreetMap via Overpass | ODbL |
| Strike events, refinery capacities | English Wikipedia | CC BY-SA 4.0 |
| Everything else | `data/curated/incidents.csv` | Per-row source URLs |

Full detail and per-source caveats: [docs/SOURCES.md](docs/SOURCES.md).

---

## Recovery / reconstitution (iteration 1)

Repair is no longer a flat half-life. Each disrupted facility's decay is driven by the
strongest available evidence, and the **kind travels with every number**:

- **Observed** — a source reported how long restoration actually took (green, solid).
- **Estimated** — a source gave a reconstitution window (amber, half-filled).
- **Modelled** — neither exists; a generic per-sector assumption is used (muted, dashed).

Confirmed reconstitution collapses a facility's contribution. Recovery evidence lives in
`data/curated/recovery.csv` (source required per row). The dashboard's **Recovery tab**
shows unresolved counts, median observed restoration (with sample size), impairment age,
and the observed/estimated/modelled mix.

The four analytic concepts — **exposure**, **assessed degradation** (quantified only),
**recovery**, and **confidence/coverage** — are kept structurally distinct in the data
and across the seven-tab analytical panel (Overview · Rankings · Recent · Recovery ·
Effects · Repair burden · Sources).

---

## Documentation

- [docs/ITERATION_5_REVIEW.md](docs/ITERATION_5_REVIEW.md) — **current state**: analytic/context scope model, network context + rivers, event/recovery growth, gas/coal depth, data contract
- [docs/ITERATION_4_REVIEW.md](docs/ITERATION_4_REVIEW.md) — Crimea in the index, facet-driven UI, zero-count audit, LNG/gas coverage
- [docs/ZERO_COUNT_AUDIT.md](docs/ZERO_COUNT_AUDIT.md) — every taxonomy/filter zero: researched, classified, ingested or hidden
- [docs/ITERATION_3_REVIEW.md](docs/ITERATION_3_REVIEW.md) — generation/transmission split, regional intensity, episode recovery, CREA context, three-layer Effects
- [docs/ITERATION_2_REVIEW.md](docs/ITERATION_2_REVIEW.md) — Crimea, context geography, incident-level recovery, denominator audit
- [docs/ITERATION_1_REVIEW.md](docs/ITERATION_1_REVIEW.md) — Siberia, recovery framework, 7-tab panel
- [docs/METHODOLOGY.md](docs/METHODOLOGY.md) — how the index and recovery model are computed, and every assumption
- [docs/SCHEMA.md](docs/SCHEMA.md) — data model and field definitions
- [docs/SOURCES.md](docs/SOURCES.md) — provenance and licensing
- [docs/COST_SOURCES.md](docs/COST_SOURCES.md) — candidate open sources for repair cost & economic effects
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — GitHub + Vercel + daily refresh
- [docs/MVP_REVIEW.md](docs/MVP_REVIEW.md) — the original MVP review
- [docs/CHATGPT_ITERATION_PROMPT.md](docs/CHATGPT_ITERATION_PROMPT.md) — prompt for iterating elsewhere

---

## Known limits, stated up front

- **Coverage is ~57%.** The dataset enumerates 175 region-assigned events; the source
  benchmark reports 305 strikes on Russian oil facilities in total. The gap is events
  that appear only in prose reporting, which this pipeline does not parse.
- **Observed recovery is 6 distinct episodes** (13 records deduplicated by `episode_id`),
  spanning refining, oil logistics and gas processing. The "typical recovery" median
  un-suppresses at **≥5 distinct episodes**, so it is now shown (47 days) with its sample size.
- **Siberian event coverage is n=1** (Omsk). The region is fully populated structurally
  but has barely been struck yet.
- **Refining and oil logistics dominate.** They are the sectors with structured open
  data. Electric power is split into **generation** (capacity basis, ≈0 — barely struck)
  and **transmission** (an event-burden proxy, never "% offline"). Gas and coal are now
  inventoried (LNG, gas-processing, coal mines and terminals) but stay **uncovered** in the
  composite — incompatible units are never summed, and an inventory is not disruption; their
  weights are redistributed rather than counted as zero.
- **Modelled reconstitution horizons are assumptions, not measurements** — the single
  weakest input where no evidence exists. All live in `methodology/scoring.json`.
- **Four of the nine requested regional effect categories are not modelled** and are
  displayed as such, with reasons, rather than filled with plausible numbers.

These are expanded in [docs/ITERATION_1_REVIEW.md](docs/ITERATION_1_REVIEW.md).
