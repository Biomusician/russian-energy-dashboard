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

Run on 2026-11-03 against the plan as committed in `a7f3a36`. The research log (`data/curated/systems/us/research_log.json`) is the record; this section restates it as counts.

**0 of 9 lanes complete** for the window 2022-01-01 to 2026-11-03. A lane is complete only if its declared universe was searched to the end of the window; none was.

### B.1 Dispositions

candidates 78 · accepted 3 · rejected 25 · duplicate 38 · held 8 · out of scope 3

4 lane-accepted candidates went to blind review: 3 published, 1 held (Hurricane Lee in Maine: whether the reported customer figure meets the threshold is an owner question).

### B.2 Lane by lane

Lane H1 was declared in Part A but not assigned to an agent in this iteration. It is recorded as partial, covered through 2026-10-31 (its iteration-16 completion), and the plan-commit test is what caught the omission.

| Lane | Status | Covered through | Why not complete |
|---|---|---|---|
| G1 | partial | 2025-12-31 | 2022-2025 enumerated in full (iteration 16, carried forward, re-verified unchanged). 2026 has no published OE-417 annual summary, so the lane's universe for 2026-01-01 to 2026-11-03 cannot be searched. |
| G2 | partial | 2025-12-31 | Every in-window report on NERC's event-analysis page and every SOR published to date was read (iteration 16; re-verified today as unchanged). Partial because no SOR yet covers 2026 events and ferc.gov refuses automated access (403, not worked around), so the FERC side of the universe cannot be enumerated. |
| H1 | partial | 2026-10-31 | Complete through 2026-10-31 in iteration 16 and carried forward, as the plan declares; not re-run for 2026-11-01 to 2026-11-03, so not complete for this window. |
| H2 | partial | 2026-06-16 | Every published TCR in the declared universe was read and every US energy effect it documents was dispositioned. Partial because NHC has not yet published the TCRs for four 2026 US-affecting storms (Arthur, Edouard, Isaias; Lowell in the eastern Pacific). |
| U1 | partial | 2026-11-03 | The EIA half is covered through 2026-11-03 and every weather shut-in article dispositioned. Partial because BSEE refused automated access again (HTTP 403 on a single polite retry), so BSEE's storm shut-in releases still cannot be enumerated, and because the plan's site-search strings could only be run through a general eia.gov-restricted search. |
| P1 | partial | 2026-11-03 | The CAO universe itself is enumerated across the whole window: the raw file is current to 2026-11-03 and lists 30 CAO cases opened 2022-01-01 onward, exactly the 30 iteration 16 dispositioned; no CAO was opened or issued after 21 Sep 2026. Marked partial only because the plan's second endpoint, the PHMSA incident data files, refused the fetch (HTTP 403). LEAD may rule the lane complete, since the  |
| L1 | partial | 2026-11-03 | Only Sabine Pass (10 of the plan's 90 queries) was run before the personal search cap; the other eight terminals were not searched in this pass. Even fully run, per-terminal news search is not a census of terminal outages. |
| R1 | partial | 2026-11-03 | All 15 plan queries were run and both CSB lists read, but R1 has no census source: it is complete only for the declared query set, never for 'every refinery event' (plan A.1; partial by construction until the owner rules, ITERATION_16_REVIEW s.12 item 5). |
| C1 | partial | 2026-11-03 | All 10 plan queries were run, but C1 has no census source (MSHA and EIA publish no list of mine events that cut supply): complete only for the declared query set, partial by construction until the owner rules (plan A.1). |

### B.3 What the next pass must do

Run the lanes marked not started first, then the partial lanes from their `covered_through` date. Refusals (HTTP 402/403, login walls, script-rendered listings) are not worked around; a lane that depends on one stays partial and says so.

