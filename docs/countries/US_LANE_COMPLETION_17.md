# United States — lane completion pass (iteration 17)

**Part A, the search plan, was written on 2026-11-03 before any search of this pass was run.**
It re-declares the nine lanes of the iteration-16 sweep (`US_SYSTEMATIC_SWEEP.md`) with the
completion contract iteration 16 lacked: a declared universe per lane, the exact queries or
endpoints, the window, and what "complete" means for that lane. Definitions (A.2 of the
iteration-16 plan) and the inclusion rule (`inclusion_threshold.json` version `2026-10-30.1`) are
unchanged. No new event class.

**A lane is complete only if its declared universe was searched across the whole window
2022-01-01 to 2026-11-03.** A lane whose source has not yet published part of the window is
partial with `covered_through` set, however thoroughly the published part was read. A lane that
yields no new record is not thereby complete, and a lane that yields many is not thereby
complete either.

## Part A — plan (written before searching)

### A.1 Lanes

| Lane | Universe (what complete means) | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|
| G1 | Every row of the DOE OE-417 annual summaries 2022-2025 (enumerated in iteration 16, carried forward) and of the current-year 2026 file if DOE publishes one | `https://doe417.pnnl.gov/summaries/` listing; `{YYYY}_Annual_Summary.xls(x)` | none; enumeration only | 4, 5 |
| G2 | Every NERC *State of Reliability* report covering 2022-2026 events; every report on NERC's event-analysis page dated in the window; FERC/NERC joint inquiry reports | nerc.com SOR and event-analysis pages; ferc.gov major-event pages | none; enumeration only | 4, 5 |
| H1 | Every DOE CESER emergency situation report in the window (complete in iteration 16, carried forward) | CESER situation-report archive | none | 1, 2, 5, 7 |
| H2 | Every NHC Tropical Cyclone Report for a 2022-2026 Atlantic or eastern-Pacific cyclone with US landfall or US tropical-storm-force impact | `nhc.noaa.gov/data/tcr/index.php?season=YYYY&basin=atl` and `basin=epac`, each year | none; enumeration only | 5, 7 |
| U1 | Every BSEE Gulf storm shut-in statistics release in the window; every EIA *Today in Energy* article on weather-driven production shut-ins or freeze-offs | bsee.gov newsroom (storm statistics); eia.gov/todayinenergy | EIA site search: "freeze-offs", "shut in production", "hurricane production" | 7 |
| P1 | Every PHMSA corrective action order (hazardous liquid and gas transmission) issued 2022-01-01 to the newest public data date | PHMSA enforcement data and CAO listings; incident data file | none; enumeration only | 3 |
| L1 | Every US LNG export terminal operating in the window: Sabine Pass, Cameron, Corpus Christi, Freeport, Calcasieu Pass, Cove Point, Elba Island, Plaquemines, Golden Pass | per terminal | for each terminal T and each year Y: `"T" LNG outage Y`; `"T" LNG trip OR shutdown Y` | 1, 2 |
| R1 | Every CSB investigation in the window; and the query set below, run for every year | csb.gov investigations list | for each year Y in 2022-2026: `refinery fire shut down unit Y`; `refinery outage crude unit Y`; `gas processing plant explosion shut Y` | 1 |
| C1 | Any coal-mine event EIA or MSHA reports as cutting supply | eia.gov coal reports; msha.gov fatality and accident alerts | for each year Y: `coal mine shut production fire Y`; `coal mine flooding idled Y` | 6 |

R1 and C1 have no census source. Even with every query run, they are complete only for the
declared query set, never for "every refinery event", unless the owner accepts a declared
query set as a complete enumeration for these classes (ITERATION_16_REVIEW §12 item 5). Until
then they are recorded as **partial, by construction**, with the reason.

### A.2 Search budget and resilience

The per-turn web-search budget is shared by every agent. This pass splits the work by source
family (grid and hazard: G1, G2, H2, U1; facility: P1, L1, R1, C1). Each agent has a fixed
search cap and writes its lane log after every source family, so a cap hit loses nothing already
done. Enumeration lanes use direct fetches of the listed endpoints, not searches.

### A.3 Review

Every lane-accepted candidate goes through the iteration-17 blind three-role review
(REVIEW_GOVERNANCE.md): evidence, safety and taxonomy reviewers each see the sources and the
proposed record, not the researcher's rationale.

## Part B — execution record

*(Filled in after the lanes run. Counts only.)*
