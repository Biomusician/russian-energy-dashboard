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
| Fragmented (>1 component) | 178 | 32 | **210** |
| Components | 1,689 | 294 | 1,983 |
| **Distinct mapped pipe geometry** | 139,100 km | 50,879 km | **189,979 km** |
| Sum of route lengths (double-counts hierarchy) | 164,360 km | 51,317 km | 215,677 km |

Across those 210 routes there are **1,519 gaps** totalling **≈43,200 km** of straight-line
separation, of which ≈29,000 km sits in gaps over 50 km.

That total is a **lower bound on missing pipe**: it measures the shortest straight line between
two component endpoints, and real pipe does not run in straight lines. It is never drawn.

### How a gap is counted

The gaps reported are the **N−1 edges of a minimum spanning tree** over each route's components —
the set that would have to be closed to make the route continuous, each counted **once**.

An earlier version of this analysis had every component report its own nearest neighbour
independently. That double-counted every mutually-nearest pair (1,000 "adjacencies" for 651 real
ones, inflating the total by 26 %) and simultaneously *under*-counted large separations, because
a component's biggest gap was never reported at all. Both errors are fixed; the band shares below
moved materially as a result.

## Classification

Each gap is banded by what a separation of that size can plausibly *be*, not by round numbers.

| Band | Range | n | Share | What it most likely is |
|---|---|---:|---:|---|
| `noise` | < 0.5 km | 283 | 18.6 % | Endpoints that nearly coincide — an OSM node not quite shared |
| `artefact` | 0.5–5 km | 313 | 20.6 % | A missing way or two, with the corridor mapped either side |
| `section` | 5–50 km | 725 | 47.7 % | A genuinely unmapped run; too long to be a topology slip |
| `major` | > 50 km | 198 | 13.0 % | A whole limb absent — subsea crossings, or mapping that stops at a frontier |

### Why the `noise` band is not simply welded away

Two separate rules keep these open, and neither is squeamishness.

**Zero-length gaps are junctions, not gaps.** `stitch()` stops a chain at any node where three or
more ways meet, so a chain cannot run out along one string and back along its twin. Those chains
end on the *same coordinate*, so a naive weld saw a zero-length gap and undid the decision one
line later — it was doing this 119 times. `weld()` now refuses any gap of exactly zero.

**Named-way routes are never welded at all.** The remaining sub-kilometre gaps are overwhelmingly
on `osm_named_ways` routes — components grouped by a shared name string rather than by relation
membership. A shared name is not OSM asserting that two pieces are one pipeline, so joining them
would be exactly the proximity rule this project refuses. (An earlier draft of this document said
these were "cross-relation adjacencies"; that was wrong — `gaps_for_route` only ever compares
components of the *same* route, so a cross-relation adjacency is structurally impossible here.)

Raising the weld tolerance until the picture tidies up is how a coincidence becomes an asserted
connection. Any of these that is real should be closed by evidence — an OSM fix upstream, or a
sourced assertion in `pipeline_topology.csv` — not by a wider constant.

## Worst routes by maximum gap

| Max gap | Components | Route |
|---:|---:|---|
| 812 km | 3 | Surgut–Polotsk — mapping is largely Russian-side; the Belarusian run is absent |
| 524 km | 23 | 中俄东线天然气管道 (Power of Siberia, Chinese side) |
| 459 km | 24 | Yamal–Europe — heavily fragmented across four countries |
| 430 km | 3 | Ямбург — Поволжье |
| 414 km | 2 | Ukhta–Torzhok 1 |
| 345 km | 9 | SRTO–Torzhok |
| 339 km | 7 | Urengoy–Pomary–Uzhhorod — the Ukrainian transit trunk |

Major export corridors are **among** the most fragmented, because they cross borders and long
sparsely-mapped stretches. Note the qualifier: ranked by *total* gap-kilometres rather than by
worst single gap, the most fragmented object is the BOTAŞ national network — a Turkish
distribution system carried as context — and about a third of all gap-kilometres sit on routes
with no analytic overlap at all. Fragmentation is not a property of importance.

## Analytic exposure

**78 of the 210 fragmented routes overlap the analytic layer** (43 of them with a `major` gap).

A fragmented analytic route means the drawn line understates the pipeline's extent. It does
**not** mean the pipeline is severed, damaged, or interrupted — the gap is in the *mapping*, not
in the pipe. This is why `route_length_km` (topological, from the source) is carried separately
from `drawn_length_km` (what is rendered): the difference between them is exactly this ledger.

## Measurement caveats

- **`distinct_network_km` is an exact union of member-way lengths**, each way counted once. Two
  parallel physical strings with distinct way ids correctly remain two pipes; only parent/child
  reuse of the *same* way deduplicates. Until iteration 10 this figure apportioned route length
  by member-way *count*, which was order-dependent and overstated gas by ~2,235 km.
- **`drawn_length_km` is not de-duplicated.** Where two OSM ways trace the same physical pipe,
  both are drawn. Measured overdraw across the corpus is on the order of 10 %, concentrated in a
  handful of routes (Омск — Иркутск is the worst single case).
- **`detailed_geometry_km` is measured on simplified geometry**, so it understates the source by
  roughly 2 %.
- **Gap counts rose in iteration 10** (828 → 1,519) because 646 closed-loop components that were
  previously *deleted* by an open-line simplifier are now retained, and because the weld fix
  stopped merging chains across junctions. The network did not fragment; the measurement stopped
  hiding fragments.

## Disposition

No gap is closed. The defensible routes forward, in preference order:

1. **Fix upstream.** Where a gap is an OSM artefact, the repair belongs in OSM and arrives here
   on the next fetch.
2. **Assert topology without geometry.** Where the connection is documented but the line is not
   mapped, record it in `pipeline_topology.csv` with its source. `TOPOLOGY MAY BE KNOWN WHEN
   GEOMETRY IS NOT` — the connection becomes queryable, and now visible in the route dossier,
   without a fabricated line.
3. **Import better geometry.** Note that 698 of 1,917 GEM rows for this area carry GEM's own
   straight-line or schematic geometry, so GEM is not automatically an improvement —
   `GENERALIZED != MAPPED`.
4. **Leave it open.** The default, and frequently the right answer.

Explicitly **not** on this list: interpolating between endpoints, raising the weld tolerance to
make components meet, or drawing a straight line because two endpoints are close.
