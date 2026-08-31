# Power & coal inventory source reconciliation

Evaluation of Global Energy Monitor's trackers against the WRI Global Power Plant Database that
currently supplies the generation inventory and the electric-generation denominator.

**Nothing here changes a score.** Iteration 9 brief §30 forbids altering an analytic denominator
without a frozen replay and an independent methodology red-team. This document records what was
measured and what it implies, so the change can be made deliberately in a later pass.

## The finding that matters: WRI has no status field

WRI GPPD has no operating/retired column at all. GEM does. Comparing GEM's **August 2026** Global
Integrated Power Tracker operating capacity against the WRI file the pipeline currently fetches,
for Russia + Belarus:

| Technology | WRI n | WRI MW | GEM operating MW | Δ |
|---|---|---|---|---|
| Coal | 96 | 46,072 | 37,278 | −8,794 |
| Oil and gas | 283 | 115,124 | 124,628 | +9,504 |
| Nuclear | 10 | 28,168 | 32,183 | +4,015 |
| Hydropower | 105 | 45,591 | 52,425 | +6,834 |
| Utility solar | 64 | 1,074 | 2,340 | +1,266 |
| Wind | 3 | 42 | 2,605 | **+2,563** |
| Bioenergy | 3 | 580 | 154 | −426 |
| Geothermal | 3 | 74 | 74 | 0 |
| **Total** | **569** | **236,755** | **251,687** | **+14,932** |

GEM separately reports **22,831 MW retired** in Russia plus 50 MW mothballed, and 160 MW retired
in Belarus. The coal arithmetic is the clearest illustration: GEM operating 37,278 + GEM retired
10,839 ≈ WRI's 46,072 MW. **WRI's fleet is a pre-retirement snapshot, so the live
electric-generation denominator currently includes roughly 23 GW of capacity that has since
retired, with no field capable of revealing it.**

That is a correctness problem, not a freshness preference.

The deltas are not uniform, which is why the recommendation is class-specific rather than a
wholesale swap:
- **Wind and solar**: WRI predates the entire post-2021 build (42 MW of wind against 2,605 MW).
- **Coal**: GEM is *lower* and more correct — the gap is retirements.
- **Nuclear, hydro, gas**: modest upward corrections plus real status semantics.

## Freshness

The pipeline fetches `output_database/global_power_plant_database.csv` on a 30-day cache. That
file's last data-touching commit is **2022-01-26** and it updated AUS/IND/USA/GBR only. So the
monthly refresh has been re-downloading an identical, four-and-a-half-year-frozen file. WRI's own
README states the database is "not currently maintained… no planned updates".

## Recommendation — (D) class-specific mix, executed as a staged migration

Not a straight swap, and not "keep WRI".

1. **Add GEM GIPT as a supplement** alongside WRI and emit a reconciliation report to
   `data/review/` (matched / WRI-only / GEM-only / status conflicts).
2. **Use it immediately for one thing that needs no denominator change: flag WRI records GEM
   marks as retired.** That is a correctness fix available without touching a score.
3. **Only then** switch the denominator, in a numbered iteration, publishing both bases so
   historical index values stay comparable.
4. **Keep WRI permanently as a cross-check and provenance witness** — its per-plant `url` field is
   a genuine asset GEM's summary layer does not replicate — demoted from primary, with its 2022
   freeze stated in the UI.

### Risks that must be handled at migration time

- **Denominator discontinuity.** Every ESDI value in the series shifts. Both bases must be
  published; this is a versioned methodology change, never a silent swap.
- **Plant-level → unit-level.** GEM is unit-level, WRI plant-level. `capacity_affected_mw` and
  `linked_asset_id` (e.g. `wri-WRI1003791` on the Rostov NPP record) are plant-scoped. Naive
  adoption produces one asset row per unit and inflates facility counts. A station roll-up key is
  required; GEM's schema supports the grouping.
- **Canonical matching.** Extend the existing `refineries_canonical.csv` / `refinery_registry.py`
  alias pattern rather than inventing a second mechanism. Ambiguous matches go to `data/review/`,
  never auto-merged (modelling rule 6).
- **ID churn.** At least one curated incident references a `wri-` id. Keep WRI ids as aliases on
  the merged record; do not delete them.
- **Vintage provenance is unreliable at the source.** GEM's tracker pages and its own download
  catalogue contradict each other on release dates (GOGPT: page "Aug 2026" vs catalogue "Jan
  2026"; GNPT: "Aug 2026" vs "Sep 2025"; the Coal Terminals page claims Jan 2026 while its
  citation string, catalogue and summary tables all say **December 2024**). **Record the release
  stamp from inside the downloaded file, never from a web page.**

## Coal

The repo currently has **no coal mine and no coal terminal inventory at all**, so adding one is
additive and carries none of the denominator risk above.

- **GEM Global Coal Mine Tracker (August 2026)** — adopt. ~7,000 mines, ≥1 Mtpa threshold.
  Verified Russia: **453 Mtpa operating**, 15 mothballed, 96 proposed; surface 346 / underground
  106; thermal 280 / metallurgical 107 / both 66. Brings a real status vocabulary, ownership
  chains, and local-language aliases directly reusable by the canonical registry. Caveat to carry:
  workforce and methane figures are partly **machine-learning estimates**, and must be flagged
  estimated rather than observed — the same distinction `recovery.csv` already makes.
- **GEM Global Coal Terminals Tracker (December 2024)** — adopt **with a prominent vintage
  warning**. Verified Russia: **30 operating terminals, 363 Mt capacity**. Note this is
  **nameplate handling capacity, not observed throughput** — GEM says so explicitly, and labelling
  it throughput would overstate what it means. At ~20 months old in an active sanctions and
  logistics environment it is a structural inventory, not a current-state indicator.
- **Global Coal Plant Tracker** — do **not** ingest separately; it is already folded into GIPT and
  ingesting both would double-count the same Russian fleet.

**Adding a coal inventory does not activate Coal in ESDI.** Inventory completeness and disruption
measurement are separate questions; coal remains an uncovered sector until it has a defensible
denominator and disruption evidence.

## Licence position

All GEM trackers are **CC BY 4.0, verified verbatim**, with raw redistribution permitted and no
NonCommercial/NoDerivatives rider. The obstacle is the form-gated download, which is an access
control, not a licence restriction — so the correct pattern is to **vendor a snapshot** with
checksums and a manifest (see `PIPELINE_SOURCE_AUDIT.md`), not to abandon the source. Attribution
must name the tracker and its release, and must state that the data was modified where we filter
or simplify it.
