# Canada — lane completion pass (iteration 17)

**Part A, the search plan, was written on 2026-11-03 before any search of this pass was run.**
It re-declares the seven lanes of the iteration-16 sweep (`CA_SYSTEMATIC_SWEEP.md`) with the
completion contract, writes out the query sets iteration 16 left unwritten, and adds one lane
(CG3, operator grid records). Definitions and the inclusion rule are unchanged.

**Complete means the declared universe was searched across 2022-01-01 to 2026-11-03.** A source
that has not published part of the window leaves its lane partial with `covered_through`.

## Part A — plan (written before searching)

### A.1 Lanes

| Lane | Universe (what complete means) | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|
| CG1 | Every event in the Canadian Disaster Database whose record mentions utilities, power or energy | Open Government CDD extract (newest edition) | none; enumeration only | 1-7 |
| CG2 | Every NERC *State of Reliability* report covering 2022-2026; every NERC event-analysis report naming a Canadian entity | nerc.com | none | 4, 5 |
| CG3 | Every grid-alert or load-shed notice published by AESO, and the IESO and Hydro-Québec emergency or major-outage records, in the window | AESO grid alert history; IESO and Hydro-Québec news archives | `site:aeso.ca grid alert Y`; `IESO emergency Y`; `Hydro-Québec panne majeure Y` for each year Y | 5 |
| CH1 | Every story in Environment Canada's "top ten weather stories" editions covering 2022-2026; for each, a utility peak figure | canada.ca top-ten pages | for each story with outages: `<utility> customers without power <storm> Y` | 5, 7 |
| CP1 | Every CER-regulated incident reported as a rupture or with an operations interruption, from the newest CER incident file; every TSB pipeline investigation | CER incident data; tsb-bst.gc.ca pipeline investigations list | none; enumeration only | 3 |
| CR1 | The query set below, run for every year, over refineries, upgraders and gas plants | — | for each year Y in 2022-2026: `Canada refinery fire shut Y`; `oil sands upgrader outage Y`; `gas plant explosion Alberta OR "British Columbia" shut Y` | 1 |
| CU1 | Every wildfire or weather production shut-in with a stated volume in Alberta, BC or Saskatchewan | AER and provincial government updates; operator statements | for each year Y: `wildfire oil sands production shut in Y`; `Alberta wildfire barrels per day offline Y` | 7 |
| CL1 | Every export terminal: LNG Canada, Westridge (Trans Mountain), Canaport, RIPET, Pembina Prince Rupert, Whiffen Head | per terminal | for each terminal T: `"T" shutdown OR suspended OR outage` | 1, 2 |

CR1 and CU1 have no census source; they are partial by construction unless the owner accepts a
declared query set as complete (as for US R1 and C1).

### A.2 Search budget, resilience, review

As in the US plan (`US_LANE_COMPLETION_17.md` A.2-A.3): split agents, fixed caps, progress
written after each source family, blind three-role review before import.

## Part B — execution record

*(Filled in after the lanes run. Counts only.)*
