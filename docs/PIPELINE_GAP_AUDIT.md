# Pipeline gap audit — why the context network is broken

Measured against the **cached Overpass responses the ETL actually receives** (`data/raw/ctxnet_*.json`,
`data/raw/osm_pipeline_*.json`) and the **shipped output** (`web/public/data/context_*_network.geojson`),
plus a fresh probe of OSM pipeline route relations (`data/raw/osm_pipeline_relations.json`).

Written **before** any fix, so that source gaps and ETL gaps could be told apart. The answer is
blunt: **the gaps are overwhelmingly ETL-created.** The source data is far more complete than what
the dashboard draws.

## Baseline being audited

| | gas | oil |
|---|---|---|
| context routes shipped | 220 | 75 |
| context payload | 67.5 kB | 24.0 kB |
| analytic lines (separate layer) | 2,575 | 205 |
| route_quality values present | `osm_mapped` (295 features, the only value) | |

---

## Root cause 1 — the 50 km minimum is applied to each OSM **way**, not to the route

A trunk line is not one OSM way. It is a chain of ways split wherever any tag changes — a diameter
change, a different operator segment, a bridge, a country border. The filter throws away each piece
for being small, then the route is judged by whichever pieces happened to survive.

| | qualifying ways | total length | kept (≥50 km) | **dropped (<50 km)** |
|---|---|---|---|---|
| gas | 2,459 | 53,862 km | 253 ways / 35,855 km | **2,206 ways (89.7%) / 18,007 km (33.4%)** |
| oil | 516 | 19,675 km | 90 ways / 14,950 km | **426 ways (82.6%) / 4,725 km (24.0%)** |

Consequences measured on the *named* routes:

- **65 named routes are destroyed outright** — every member way is under 50 km, so the route
  vanishes although its members total ≥50 km. Includes `Ropovod Družba` (162 km in 16 ways),
  `Westdeutsche Anbindungsleitung (WEDAL)` (189 km in 18 ways), Baku–Tbilisi–Ceyhan's Georgian
  section (247 km in 14 ways).
- **107 named routes are drawn but incomplete.** The most damaged:

| route | missing | of total |
|---|---|---|
| Trans Adriatic Pipeline | 704 km | 868 km (81%) |
| Baku–Tbilisi–Ceyhan | 870 km | 1,058 km (82%) |
| OPAL | 314 km | 410 km (77%) |
| Transalpine Ölleitung | 312 km | 445 km (70%) |
| Trans Austria Gasleitung I/II | 233 / 238 km | ~63% each |
| EUGAL | 200 km | 412 km (49%) |
| Дружба | 187 km | 1,596 km (12%) |
| Уренгой — Помари — Ужгород | 130 km | 886 km (15%) |

These are not source gaps. OSM has the geometry; the filter discards it.

## Root cause 2 — no relation awareness at all

Every cached Overpass response contains **only `way` elements**. No relation was ever requested, by
either the context builder or the analytic fetch. Both also require `["name"]` **on the way**, so a
member way that inherits its identity from its parent route is invisible even when it is long.

A probe of the same corridor found **478 `type=route` + `route=pipeline` relations**, with 9,917
members and 9,024 member ways carrying geometry.

| measure | value |
|---|---|
| relation member ways with geometry | 9,024 |
| of those, shorter than 50 km | 7,918 (87.7%) |
| **absent from the shipped context output** | **8,819 (97.7%) — 161,899 km** |

The routes lost this way are precisely the systems the dashboard exists to show:

| relation | km absent | members | substance |
|---|---|---|---|
| Сияние Севера (Northern Lights) | 8,376 (all) | 137 | gas |
| Yamal — Lubmin | 6,582 of 9,028 | 131 | gas |
| Уренгой — Помары — Ужгород | 3,728 of 4,483 | 64 | gas |
| Уренгой — Новопсков | 3,348 (all) | 56 | gas |
| Сургут – Полоцк | 3,169 (all) | 56 | oil |
| Омск — Иркутск | 3,028 (all) | 27 | oil |
| Восточная Сибирь – Тихий океан (ESPO) | 2,687 of 4,723 | 24 | oil |
| СРТО — Торжок | 2,000 (all) | 24 | gas |
| Дружба | 1,841 | 32 | oil |

**215 relations are ≥150 km.** Only a fraction of any of them reaches the map.

Note for implementation: **255 of 478 relations carry no `substance` tag on the relation itself**
(50 oil / 124 gas derivable from relation tags alone; 304 unresolved). Substance must be derived
from member ways, not assumed.

## Root cause 3 — the Overpass bands leave a hole across Siberia

The four context bands are:

```
europe_w  34–72N,  -10–12E
europe_e  34–72N,   12–32E
south     34–48N,   25–56E
far_east  42–78N,  120–160E
```

Longitudes **56°E–120°E are not covered by any band**, and 32–56°E is covered only below 48°N.
That is the whole of Western and Central Siberia and the northern Urals corridor.

**91 relations — ~71,522 km — fall entirely outside every band**, including Сияние Севера (8,376 km),
Уренгой — Новопсков (3,348 km), Омск — Иркутск (3,028 km), СРТО — Торжок (2,000 km),
Бухара — Урал (2,307 km), Ямбург — Поволжье (1,974 km), СРТО — Урал (1,967 km).

The hole was survivable only because the builder assumed the **analytic** layer (19–120°E) would
cover it — which is the architectural error in root cause 4.

Separately, **17 named routes appear in more than one band** (Transalpine Ölleitung, MEGAL Nord,
Mitteleuropäische Rohölleitung, STEGAL…), so a single corridor is assembled from two independent
query results with no route-level identity to rejoin them.

## Root cause 4 — de-duplication against the analytic feed guts the context layer

`build_context_network.build(analytic_osm_ids=…)` drops any way already present in the analytic
feed, on the reasoning "one corridor, one line". But the two layers are **independently toggled in
the UI**: `showGasNetwork` does not imply `showLines`.

**100 trunk ways — 17,535 km — are removed from the context layer for this reason alone**, among
them Дружба (11 ways), Уренгой — Помары — Ужгород (7), Przyjaźń (3), Палкино — Приморск (3),
Краснодарский край — Крым (3), Макат — Северный Кавказ (3+3).

So a reader who enables **Gas pipelines** and leaves **Grid & pipeline network** off — the natural
way to look at the export system — sees a context layer with the Russian trunk backbone deleted
from it.

## Resulting connectivity of what ships today

| | features | connected components | dangling endpoints | fully isolated segments |
|---|---|---|---|---|
| gas | 220 | **160** | 314 | 121 |
| oil | 75 | **53** | 108 | 39 |

Roughly one component per feature: the shipped "network" is not a network. Note this measures
exact-coordinate endpoint sharing — the only connection evidence the current output actually
carries.

## Disposition: source gap vs ETL gap

| cause | nature | km affected (gas + oil) |
|---|---|---|
| per-way 50 km filter | **ETL** | 22,732 km discarded from qualifying ways |
| no relation reconstruction | **ETL** | 161,899 km of relation members never emitted |
| band hole 56–120°E | **ETL** | ~71,522 km of relations never queried |
| analytic de-duplication | **ETL** | 17,535 km removed from the context layer |
| `["name"]` required per way | **ETL** | included in the above |
| genuine source gaps | source | to be quantified after reconstruction |

Every measured cause is an extraction defect. **No fix in this audit requires inventing geometry** —
it requires asking OSM for what it already has, assembling routes before judging their length, and
letting the context layer stand on its own.

## What this audit does not yet answer

- How much of the remaining discontinuity is a **true** source gap (unmapped in OSM) once relations
  are reconstructed. That is measured after the rebuild, in `docs/ITERATION_9_REVIEW.md`.
- Whether GEM GGIT/GOIT can fill any genuine source gap under a licence that permits it.
- Whether ENTSOG can supply topology where geometry is genuinely absent.
