# Pipeline gap ledger

What is missing from the drawn network, measured rather than estimated. Reproduce with:

```bash
.venv\Scripts\python.exe -m pipeline.analyse_pipeline_gaps --ledger
```

Per-route detail: [`data/review/pipeline_gap_ledger.csv`](../data/review/pipeline_gap_ledger.csv).

**Nothing in this analysis closes a gap.** No geometry is written, no component is joined, no
route is interpolated. `UNRESOLVED GAP > INVENTED LINE`. The purpose is to make the network's
incompleteness legible and classified, so a human can decide what is worth sourcing.

## Headline

| | Gas | Oil | Total |
|---|---:|---:|---:|
| Routes | 375 | 89 | 464 |
| Fragmented (>1 component) | 147 | 25 | **172** |
| Components | 1,129 | 163 | 1,292 |
| Drawn geometry | 160,566 km | 50,365 km | 210,931 km |

Across those 172 routes there are **1,000 component adjacencies**. The straight-line distance
across all of them totals **≈29,150 km**, of which **≈20,900 km** sits in gaps over 50 km.

That total is a **lower bound on missing pipe, and deliberately so**: it measures the shortest
straight line between two component endpoints, and real pipe does not run in straight lines. It
is reported as a bound, never as a length, and it is never drawn.

## Classification

Each adjacency is banded by what a gap of that size can plausibly *be*, not by round numbers.

| Band | Range | n | Share | What it most likely is |
|---|---|---:|---:|---|
| `noise` | < 0.5 km | 204 | 20.4 % | Endpoints that nearly coincide — an OSM node not quite shared between two ways |
| `artefact` | 0.5–5 km | 276 | 27.6 % | A missing way or two, with the corridor mapped either side |
| `section` | 5–50 km | 366 | 36.6 % | A genuinely unmapped run; too long to be a topology slip |
| `major` | > 50 km | 154 | 15.4 % | A whole limb absent — subsea crossings, or mapping that stops at a frontier |

### The `noise` band, and why it was not simply welded

| Sub-band | n |
|---|---:|
| < 100 m | 54 |
| 100–200 m | 68 |
| 200–300 m | 38 |
| 300–500 m | 44 |

The 54 adjacencies under 100 m are already inside the weld tolerance but were **not** welded,
because welding is restricted to components of the *same* relation. These are cross-relation
adjacencies: two different pipelines whose endpoints happen to nearly touch, typically at a
compressor station or a junction. Welding them would fuse distinct pipelines into one, which is
a worse error than leaving them apart — `PROXIMITY != CONNECTION`.

The 150 adjacencies between 100 m and 500 m were **not** closed by raising the tolerance. Raising
a threshold until the picture looks tidier is how a proximity coincidence becomes an asserted
connection. Any of these that is real should be closed by evidence — an OSM fix upstream, or a
sourced topology assertion in `pipeline_topology.csv` — not by a wider constant.

## Worst routes by maximum gap

| Max gap | Components | Route | Reading |
|---:|---:|---|---|
| 812 km | 3 | Surgut–Polotsk | Mapping is largely Russian-side; the Belarusian run is absent |
| 512 km | 7 | 西气东输四线 (West–East Gas Pipeline 4) | Outside the monitored area; carried as context |
| 430 km | 3 | Ямбург — Поволжье | Long unmapped mid-section |
| 414 km | 22 | Yamal–Europe | Heavily fragmented across four countries |
| 414 km | 2 | Ukhta–Torzhok 1 | Two components with the middle absent |
| 345 km | 9 | SRTO–Torzhok | |
| 339 km | 7 | Urengoy–Pomary–Uzhhorod | The Ukrainian transit trunk |
| 324 km | 7 | Ямбург — Елец 2 | |
| 294 km | 12 | Уренгой — Новопсков | |
| 253 km | 6 | Omsk–Irkutsk | |

These are the *named trunk lines*, which is the point worth absorbing: fragmentation is not
concentrated in obscure local pipe. The most significant export corridors in the dataset are
among the most fragmented, because they cross borders and long sparsely-mapped stretches.

## Analytic exposure

**75 of the 172 fragmented routes overlap the analytic layer** (42 of them with a `major` gap).
This is the number that constrains what the map may be used to say.

A fragmented analytic route means the drawn line understates the pipeline's extent. It does
**not** mean the pipeline is severed, damaged, or interrupted — the gap is in the *mapping*, not
in the pipe. Any reading of a break in a drawn line as a break in infrastructure would be a
category error, and the UI must not invite it. This is why `route_length_km` (topological, from
the source) is carried separately from `drawn_length_km` (what is rendered): the difference
between them is exactly this ledger.

## Disposition

No gap is closed in this iteration. The defensible routes forward, in preference order:

1. **Fix upstream.** Where a gap is an OSM artefact, the correct repair is in OSM, and it
   arrives here on the next fetch. This costs nothing here and helps everyone.
2. **Assert topology without geometry.** Where the connection is documented but the line is not
   mapped, record it in `pipeline_topology.csv` with its source. `TOPOLOGY MAY BE KNOWN WHEN
   GEOMETRY IS NOT` — the connection becomes queryable without a fabricated line being drawn.
3. **Import better geometry.** GEM carries traced routes for some of these; the importer and
   reconciler exist. Note that 698 of 1,917 GEM rows for this area carry GEM's own
   straight-line/schematic geometry, so GEM is not automatically an improvement —
   `GENERALIZED != MAPPED`, and a schematic line must never overwrite a traced one.
4. **Leave it open.** The default, and frequently the right answer.

What is explicitly **not** on this list: interpolating between endpoints, raising the weld
tolerance to make components meet, or drawing a straight line because two endpoints are close.
