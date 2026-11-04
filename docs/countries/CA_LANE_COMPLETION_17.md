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

Run on 2026-11-03 against the plan as committed in `a7f3a36`. The research log (`data/curated/systems/ca/research_log.json`) is the record; this section restates it as counts.

**0 of 8 lanes complete** for the window 2022-01-01 to 2026-11-03. A lane is complete only if its declared universe was searched to the end of the window; none was.

### B.1 Dispositions

candidates 56 · accepted 6 · rejected 12 · duplicate 11 · held 27 · out of scope 0

6 lane-accepted candidates went to blind review: all 6 published (some with corrections every role confirmed).

### B.2 Lane by lane

| Lane | Status | Covered through | Why not complete |
|---|---|---|---|
| CG1 | partial | 2022-12-22 | The source has published nothing after 2022-12-22. The newest edition is the one iteration 16 enumerated; 2023-2026 is absent from the source, not unsearched. |
| CG2 | partial | 2025-12-31 | Every published SOR and event report was covered, but no SOR covering 2026 exists yet; covered_through is the end of the latest operating year NERC has reported. |
| CG3 | partial | 2025-12-31 | AESO is enumerated completely through 2025-12-31 from its own records, but it has published no list for 2026 (its live feeds are empty and keep no archive); 2026 rests on one search that found nothing. IESO publishes no archive of its emergency declarations (the notice archive keeps 90 days), so IESO coverage rests on searches. Hydro-Québec's archive is complete as a list of releases but HQ did no |
| CH1 | partial | 2025-12-31 | No 2026 edition exists, so January-November 2026 is outside this source; two holds remain without a utility peak; and two iteration-16 rejections rest on ECCC wording rather than a utility figure. |
| CP1 | partial | 2026-10-22 | CER file enumerated across the window to its latest reported date (2026-10-22) and every screened row dispositioned (this pass re-emits the 10 interruption-flag rows; the other 41 keep their iteration-16 dispositions, unchanged). Partial because the TSB half was refused (HTTP 403), the CER file stops at 2026-10-22, and no public-report check of the interruption rows was possible within the lane (n |
| CR1 | partial | 2026-11-03 | All 15 declared queries run (every year 2022-2026). Partial by construction (plan A.1: no census source; a declared query set is complete only if the owner accepts it), and because several result pages refused fetch (moosejawtoday, oilandgas360, energynow, Biofuels Digest) and some results were undated archive items. |
| CU1 | partial | 2026-06-01 | Five of ten declared queries run (2022 both, 2026 both, 2024 one); 2023 and 2025 not searched; no AER/provincial/operator enumeration; partial by construction in any case (no census source). |
| CL1 | partial | not started | Not executed: the personal search cap was spent on CR1 and CU1 in the instructed order, and the one direct fetch (LNG Canada news) was refused. |

### B.3 What the next pass must do

Run the lanes marked not started first, then the partial lanes from their `covered_through` date. Refusals (HTTP 402/403, login walls, script-rendered listings) are not worked around; a lane that depends on one stays partial and says so.

