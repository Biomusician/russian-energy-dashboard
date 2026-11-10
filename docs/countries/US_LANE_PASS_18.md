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

## Part B — execution (written after the pass, 2026-11-10)

**This pass did not finish.** A shared limit of 200 web searches per turn was reached about two-thirds of the way through. Direct page requests still worked. The limit was not worked around, and every lane it stopped says so. A new turn is needed to run the remaining queries: `scripts/research_tools.py next us`.

| Lane | Execution | Source window | Covered through | Queries | Languages run |
|---|---|---|---|---|---|
| G1 | enumerated_complete (carried) | publisher_not_yet_released | 2025-12-31 | none declared | en |
| G2 | partial | inaccessible | 2025-12-31 | none declared | en |
| H1 | partial | current_through_end_date | 2026-11-10 | none declared | en |
| H2 | enumerated_complete | publisher_not_yet_released | 2026-08-26 | none declared | en |
| U1 | partial | inaccessible | not reached | none declared | en |
| P1 | partial | inaccessible | 2026-11-03 | none declared | en |
| L1 | partial; stopped by search limit | no_census_exists | not reached | 30 of 90 | en |
| R1 | partial; stopped by search limit | no_census_exists | 2026-11-03 | 15 of 16 | en |
| C1 | declared_search_complete (carried) | no_census_exists | 2026-11-03 | 10 of 10 | en |

Candidates 29: accepted after blind review 1, rejected 18, duplicate 1, held 6, out of scope 3.

**Corpus audit.** One record held (a mine closure with no reported supply effect). Recovery kinds lowered from complete to partial where the source gave a percentage or one utility. Effects corrected where a figure was one island's, or not stated as a peak. One record left a named-storm episode because its only citation names no storm.

**Recovery research.** DOE situation reports, NERC event reports and OE-417 annual summaries were read for records marked not yet researched. An OE-417 restoration entry is the filer's end of the reportable event, and is recorded as partial with that caveat. Records with no finding remain "not yet researched" or "researched, no public evidence", as stated.

**LNG lane.** Three of nine terminals searched. Six terminals remain, and the rest were stopped by the search limit. Terminals not operating in a year are not applicable and are not counted as run.

### Limitations, per lane

- **G1**: DOE has published no 2026 OE-417 file as of 2026-11-10 (the three 2026 file names return the portal's HTML shell; server Last-Modified is still 2026-10-08), so 2026-01-01 to 2026-11-10 cannot be enumerated from this source. The execution value restates iteration 17's finding in the two-dimension vocabulary (every published row read; the gap is the publisher's); it is not new coverage, and the 2025 file was verified by size and date header, not re-read.
- **G2**: ferc.gov refused access again (HTTP 403), so FERC's own major-event pages, including any review of the 2026 winter storms, remain unread. NERC has published nothing since 2026-11-03, no event-analysis report on a 2026 event, and no State of Reliability report covering 2026.
- **H1**: Marked partial, not enumerated_complete, only because iteration 16 listed but did not open every report of the Ian, Helene and Fiona series; nothing from this pass is unread.
- **H2**: NHC has not published reports for Atlantic Dolly, Edouard, Fay, Gonzalo, Hanna, Isaias and Josephine, nor for eastern-Pacific Douglas, Elida, Fausto, Karina, Lowell, Marie and the storms after Norbert. Of the four US-affecting storms that were unpublished on 2026-11-03, one (Arthur) is now out; Edouard, Isaias and Lowell are still unpublished. Josephine (21-22 Oct 2026) was not assessed for US effects because no search could be run.
- **U1**: BSEE's newsroom refused access for the third pass running, so its storm shut-in releases are unenumerated; a release for a smaller storm (Alberto 2024; Arthur, Bertha, Edouard, Josephine 2026) could be missing. The public alternatives opened give no new shut-in event since 2026-11-03 and cannot show that BSEE issued none.
- **P1**: The incident data files, the only complete list of reportable pipeline incidents, are still unread: phmsa.dot.gov refuses the landing pages and the zip, and DOT's open-data portal only links back to them. A trunk-line shutdown that drew neither a corrective action order nor any other enforcement case is therefore invisible to this lane.
- **L1**: Three of nine terminals were searched (Sabine Pass, Cameron, Cove Point); twelve queries for terminals not yet operating in the window were not applicable. The rest were not run because the search limit was reached.
- **R1**: Fifteen of 16 declared queries ran, through 2026-11-03. The 2026 re-check declared for this pass did not run because the search limit was reached.
- **C1**: Carried from iteration 17 with no new work: 10 of 10 declared queries, which is a completed query set and not a census. Nothing covers 2026-11-04 to 2026-11-10, and MSHA's mine data retrieval system, the enumerable source for this class, has still not been downloaded or parsed. The execution value is the two-dimension name for iteration 17's '10 of 10'; it is not new coverage.
