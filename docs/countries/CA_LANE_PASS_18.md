# Canada — research pass (iteration 18)

**Part A, the search plan, was written on 2026-11-10 before any search of this pass was run.**
Lanes, order and definitions are those of `CA_LANE_COMPLETION_17.md`. Inclusion rule version
`2026-10-30.1`, unchanged. Window 2022-01-01 to 2026-11-10. Coverage vocabulary as in
`US_LANE_PASS_18.md`.

## Part A — plan (written before searching)

### A.1 Lanes

| Lane | Universe kind | Universe | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|---|
| CG1 | census | Every event in the Canadian Disaster Database mentioning utilities, power or energy | Open Government CDD extract; re-check for a newer edition | none | 1-7 |
| CG2 | report archive | Every NERC State of Reliability report and event-analysis report naming a Canadian entity | nerc.com; re-check | none | 4, 5 |
| CG3 | report archive | Grid-alert or load-shed notices from AESO; IESO and Hydro-Québec emergency or major-outage records | AESO, IESO, Hydro-Québec: RSS, cached archive, downloadable and annual reports, system-event PDFs by ordinary access | `site:aeso.ca grid alert 2026`; `IESO emergency 2026`; `Hydro-Québec panne majeure 2026` | 5 |
| CH1 | report archive | Every story in Environment Canada's top ten weather stories 2022-2026; for each, a utility peak | canada.ca; utility and operator data for 2026 majors | for each held or 2026 story: `<utility> customers without power <storm> Y` | 5, 7 |
| CP1 | census | Every CER-regulated rupture or operations interruption; every TSB pipeline investigation | CER incident CSV; TSB public feeds, downloadable investigation index or government open-data mirror by ordinary access | none | 3 |
| CR1 | declared query set | The query set, every year | carried from iteration 17 (15 run); re-check 2026-11-03 onward | `Canada refinery fire shut 2026` | 1 |
| CU1 | declared query set | Wildfire or weather production shut-ins with a stated volume in Alberta, BC or Saskatchewan | AER, Alberta, BC and Saskatchewan public authorities, operator statements | for each year Y in 2022-2026: `wildfire oil sands production shut in Y`; `Alberta wildfire barrels per day offline Y` (five carried from iteration 17) | 7 |
| CL1 | declared query set | LNG Canada, Westridge (Trans Mountain), Canaport, RIPET, Pembina Prince Rupert, Whiffen Head | per terminal; operator releases, CER, provincial sources | for each terminal T: `"T" shutdown OR suspended OR outage`; and for each year Y in 2022-2026 where the terminal operated: `"T" outage Y` | 1, 2 |

### A.2 Recovery audit

Every published `EVIDENCE_FOUND` record is checked for: actual restoration, estimate, partial
restoration, first-report bias. `NOT_YET_RESEARCHED` records get a recovery search.

### A.3 Threshold

CER "interruption" rows stay under the unresolved threshold question: adjudicate evidence, do not
auto-publish. Wildfire near a site is not a production interruption.

### A.4 Budget, resilience, review

As `US_LANE_PASS_18.md` A.3.

## Part B — execution (written after the pass, 2026-11-10)

**This pass did not finish.** A shared limit of 200 web searches per turn was reached about two-thirds of the way through. Direct page requests still worked. The limit was not worked around, and every lane it stopped says so. A new turn is needed to run the remaining queries: `scripts/research_tools.py next ca`.

| Lane | Execution | Source window | Covered through | Queries | Languages run |
|---|---|---|---|---|---|
| CG1 | enumerated_complete (carried) | publisher_not_yet_released | 2022-12-22 | 0 of 0 | en |
| CG2 | enumerated_complete (carried) | publisher_not_yet_released | 2025-12-31 | 0 of 0 | en |
| CG3 | partial; stopped by search limit | rolling_archive_gap | 2025-12-31 | 0 of 3 | en, fr |
| CH1 | partial | publisher_not_yet_released | 2025-12-31 | none declared | en, fr |
| CP1 | partial | inaccessible | 2026-10-22 | 0 of 0 | en |
| CR1 | partial; stopped by search limit | no_census_exists | 2026-11-03 | 15 of 16 | en |
| CU1 | partial | no_census_exists | 2026-06-01 | 9 of 10 | en |
| CL1 | partial | no_census_exists | not reached | 22 of 33 | en |

Candidates 28: accepted after blind review 3, rejected 5, duplicate 3, held 17, out of scope 0.

**Corpus audit.** One record held (no opened source named the region for the emergency declaration). Recovery kinds corrected where the source gave a near-complete figure. Generation-loss and storm records now state their sources without an implied peak.

**Terminals.** Bare terminal tokens do not work as search strings; a re-run should use full facility names. One Nova Scotia terminal has no qualifying event found.

### Limitations, per lane

- **CG1**: Carried forward. The publisher has issued no edition after the 2022 extract, so 2023-2026 is absent from the source, not unsearched. The xlsx was not re-downloaded (the site firewall refused a scripted client in iteration 17; not retried), so 'no newer edition' rests on the dataset page's resource list and modified date.
- **CG2**: Carried forward. No State of Reliability covering 2026 operations exists yet, and no event report on a 2026 event naming a Canadian entity has been published; the documents were not re-read this pass because the listings are unchanged.
- **CG3**: None of the three declared 2026 queries ran (shared search budget exhausted before this agent's first search). Unread: AESO July-November 2026 (MSA Q3 report not yet released), IESO before 2026-08-08 (rolling 90-day archive, no ordinary-access history), IESO and Hydro-Québec annual reports, and the Régie de l'énergie filing behind Hydro-Québec's 2025 distribution report, which may list major events.
- **CH1**: No 2026 ECCC edition exists, so 2026 is outside the census source; 2026 coverage is three utility archives read in part, and no search ran. A 2026 storm at a utility not read, or one the utility issued no release for, would not be found.
- **CP1**: The TSB half is an index, not a reading: report bodies and the occurrence dataset are served only from tsb.gc.ca (HTTP 403 on every address tried), and it is unknown whether the portal lists every TSB pipeline investigation. The CER file has not been refreshed since 2026-11-01 and stops at 2026-10-22.
- **CR1**: Fifteen of 16 declared queries ran, through 2026-11-03. The 2026 re-check declared for this pass did not run because the search limit was reached.
- **CU1**: One declared query (2025, second string) was never run and the 2026 re-run did not happen, so search coverage of June-November 2026 rests on three fetched pages, not on queries. The authority and operator half is thin: AER's media centre was read only for May-November 2026 (3 of about 45 listing pages; 2022-2025 unread), BC Energy Regulator page 1 of 53 only, Saskatchewan's news search returned nothing relevant and was not enumerated, and Suncor (403) and Cenovus (script-only) release archives could not be read. BC and Saskatchewan shut-ins were not searched in substance: both declared strings name Alberta or the oil sands.
- **CL1**: Pembina Prince Rupert had one general (variant) query and no year queries; Whiffen Head 2022 and 2023 were not run; RIPET and Canaport year queries ran as written but the bare tokens matched unrelated subjects, so those years are run-but-uninformative rather than searched in substance.
