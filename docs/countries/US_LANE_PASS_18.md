# United States — research pass (iteration 18)

**Part A, the search plan, was written on 2026-11-10 before any search of this pass was run.**
Lanes, order and definitions are those of `US_LANE_COMPLETION_17.md`. Inclusion rule
`inclusion_threshold.json` version `2026-10-30.1`, unchanged. Window 2022-01-01 to 2026-11-10.

Iteration 18 replaces the binary lane status with two independent dimensions
(`docs/GLOBAL_METHODOLOGY.md` "Research coverage vocabulary"): **execution** (what the analyst
did) and **source window** (what the publisher has made available). A declared query set fully run
is `declared_search_complete`, never a census.

## Part A — plan (written before searching)

### A.1 Lanes

| Lane | Universe kind | Universe | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|---|
| G1 | census | Every row of the DOE OE-417 annual summaries 2022-2025 and any 2026 file DOE has published | `https://doe417.pnnl.gov/summaries/` | none; re-check the listing for a 2026 file | 4, 5 |
| G2 | report archive | Every NERC State of Reliability report and event-analysis report in the window; FERC/NERC joint inquiry reports | nerc.com; ferc.gov major-event pages by ordinary access only | none; re-check for releases since 2026-11-03 | 4, 5 |
| H1 | report archive | Every DOE CESER emergency situation report released 2026-10-31 to 2026-11-10 (earlier reports carried forward from iteration 16) | CESER situation-report listing | none; enumeration | 1, 2, 5, 7 |
| H2 | report archive | Every NHC Tropical Cyclone Report for a 2022-2026 cyclone with US landfall or US tropical-storm-force impact | `nhc.noaa.gov/data/tcr/` season indexes | none; re-check 2026 storms | 5, 7 |
| U1 | report archive | Every BSEE Gulf storm shut-in release in the window; every EIA Today in Energy article on weather shut-ins | bsee.gov by ordinary access; public government alternatives (DOE situation reports, NOAA, EIA) logged separately and never credited as BSEE | none; enumeration | 7 |
| P1 | census | Every PHMSA corrective action order; PHMSA incident data files | PHMSA enforcement data file; data.transportation.gov / phmsa.dot.gov published CSV, API or bulk endpoint if one is reachable by ordinary access | none; enumeration | 3 |
| L1 | declared query set | Sabine Pass, Cameron, Corpus Christi, Freeport, Calcasieu Pass, Cove Point, Elba Island, Plaquemines, Golden Pass | per terminal; operator disclosures, FERC public documents, EIA, Reuters/AP/S&P where public | for each terminal T and each year Y in 2022-2026: `"T" LNG outage Y`; `"T" LNG trip OR shutdown Y` (Sabine Pass queries carried from iteration 17) | 1, 2 |
| R1 | declared query set | CSB investigations list; the query set, every year | csb.gov | carried from iteration 17 (15 run); re-check 2026-11-03 onward: `refinery fire shut down unit 2026` | 1 |
| C1 | declared query set | The query set, every year | eia.gov; msha.gov | carried from iteration 17 (10 run) | 6 |

### A.2 Recovery research (not a lane; logged per pass)

For each published record whose recovery is `NOT_YET_RESEARCHED`: operator restoration statement,
EIA or regulator follow-up, reputable reporting. Observed or sourced estimate only; no modelled
decay. Absence after a real search becomes `RESEARCHED_NO_PUBLIC_EVIDENCE`.

### A.3 Budget, resilience, review

Workers split by lane; each writes its log after every source family. Refused access (402, 403,
login walls, bot challenges, script-only listings) is recorded and never worked around. Every
lane-accepted record goes through blind three-role review (`REVIEW_GOVERNANCE.md` §7) and
confirmation before import.
