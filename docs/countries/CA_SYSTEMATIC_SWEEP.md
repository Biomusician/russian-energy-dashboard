# Canada — systematic research sweep (iteration 16)

**Part A, the search plan, was written on 2026-10-31 before any search of this pass was run.**
It follows the US sweep's procedure (`US_SYSTEMATIC_SWEEP.md`), which is the template: same
dispositions, same dual review, same rule that "complete" means every declared lane executed.

## Part A — plan (written before searching)

| | |
|---|---|
| Window | 2022-01-01 to 2026-10-31 |
| Geography | the 10 provinces and 3 territories |
| Qualifying rule | `inclusion_threshold.json` version `2026-10-30.1`, unchanged; the US sweep's A.2 definitions apply word for word (peak customers out at one time in one province, ≥100,000; EEA3 or firm load shed; hazard path never evidence; regulator-reported shut-in volumes) |
| Record unit | one record per affected province per grid event; one per facility event otherwise |
| Known weakness carried forward | the 100,000-customer floor rejects province-wide outages in small provinces (an open methodology question, not changed here) |

### Source lanes

| Lane | Source family | Enumeration | Clauses |
|---|---|---|---|
| CG1 | Public Safety Canada, Canadian Disaster Database | every event 2022-2026 whose record mentions utilities, power or energy | 1-7 |
| CG2 | NERC event reports and State of Reliability (Canadian entities) | every in-window report naming a Canadian entity | 4, 5 |
| CH1 | Environment and Climate Change Canada, "Canada's top ten weather stories" (2022-2025) | every story; for each, provincial utility peak outage figures | 5, 7 |
| CP1 | Canada Energy Regulator pipeline incident data; Transportation Safety Board pipeline investigations | every CER-regulated incident reported as a rupture or line shutdown; every TSB pipeline investigation | 3 |
| CR1 | Refineries, upgraders, gas plants: the same query set for every year 2022-2026 | year by year | 1 |
| CU1 | Wildfire- and weather-driven production shut-ins (Alberta and BC government updates, AER, operator statements) | every reported shut-in with a stated volume | 7 |
| CL1 | Export terminals (LNG Canada, Westridge, crude and LPG marine terminals) | each terminal checked for reported unplanned suspensions | 1, 2 |

A lane that cannot be executed across the whole window makes the pass PARTIAL with the reason.

## Part B — execution record

*(Filled in after the lanes run. Counts only.)*
