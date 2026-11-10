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
