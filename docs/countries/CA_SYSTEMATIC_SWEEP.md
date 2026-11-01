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

Executed 2026-10-31 by two research lanes (grid; facility) and one independent review. Counts
only; per-record notes stay in the local queue.

### B.1 Result

**PARTIAL. None of the seven lanes is complete.** Three are limited by what their sources have
published so far. Four are limited by this run: the per-turn web-search budget, shared by every
research agent, ran out before the facility lanes started, and two sites refused automated
access. Neither limit was worked around. The pass is published as partial, and the Canada page
says so.

| | Count |
|---|---|
| Candidates examined | 65 |
| Accepted after independent review | 3 (2 confirmed, 1 corrected) |
| Rejected | 18 |
| Held | 28 |
| Duplicate | 16 |

The Canada corpus went from 26 records to 29.

### B.2 Lane by lane

| Lane | Status | Accepted | Held | Rejected | Duplicate | Why not complete |
|---|---|---|---|---|---|---|
| CG1 Canadian Disaster Database | partial | 0 | 1 | 4 | 4 | the public extract ends at 2022-12-22; 2023-2026 events are not yet in the source |
| CG2 NERC | partial | 2 | 9 | 1 | 2 | every in-window report read; no report covering 2026 exists yet; one FERC presentation refused access |
| CH1 Environment Canada | partial | 1 | 5 | 8 | 8 | 2022-2025 editions read in full; no 2026 edition yet |
| CP1 CER / TSB | partial | 0 | 12 | 4 | 1 | CER incident file enumerated through 2026-09-25 (463 incidents screened); TSB refused automated access |
| CR1 refineries, upgraders, gas plants | partial | 0 | 1 | 1 | 0 | query set not run (search budget); 6 of 17 facilities checked |
| CU1 wildfire and weather shut-ins | partial | 0 | 0 | 0 | 1 | regulator, provincial and operator sources not enumerated; 2022 not examined |
| CL1 export terminals | partial | 0 | 0 | 0 | 0 | three terminals checked through public pages only; three not checked |

Counts are final dispositions after independent review.

### B.3 What was accepted

- **Two Alberta Level 3 Energy Emergency Alerts** (28-29 August 2023 and 8 July 2024), both
  from NERC's *State of Reliability*. No firm load was shed in either.
- **The Ontario half of the 5-6 April 2023 ice storm.** The reviewer replaced the lane's
  evidence, a dead link plus a Wikipedia figure, with Hydro One's own release: about 120,000
  customers without power at one time. The Ontario and Quebec records now form one
  `named_hazard` episode, the first Canadian episode added under the iteration-16 rule.

### B.4 Why so much is held

- **CP1, 12 held.** In the CER file, ten mainline or loop releases carry an "interruption of
  operations" flag but have no public report of a shutdown or its effect. Is the flag alone
  enough for clause 3? That is an owner question.
- **CP1, two cross-border shutdowns.** Keystone (2022) and Line 5 (2026) failed in the United
  States. Whether either stopped Canadian flow is not stated.
- **CG2, 9 held.** NERC attributes most Canadian alerts only to "a BA in Canada" or "non-US
  entities". The independent reviewer found that 17 of 2024's 21 Level 3 alerts came from two
  non-US entities. Nine of those were procedural: one operator's rules require the declaration
  before it asks neighbours for help. Counting every EEA-3 under clause 5 would make Canada's
  count depend on procedure. That is an owner decision on the rule.
- **CH1, 5 held.** Environment Canada gives "affected" figures, not peaks. Four stories have no
  utility peak available yet. One gives a cumulative figure only.

### B.5 Corrections to existing records (independent review)

- **The Toronto flood of 16 July 2024.** A parenthetical "nearly 170,000" was not on the cited
  page, so it was removed. The 167,000 peak stands.
- **The Alberta load shed of 5 April 2024** is confirmed as NERC's only 2024 firm load shed. One
  conflict is open: S&P gives 09:16 as the end time, the Market Surveillance Administrator 09:19.

### B.6 What the next pass must do

- Run CR1's query set, CU1's regulator and provincial sources, and CL1's remaining terminals
  in a turn with search budget.
- Re-run CG1, CG2 and CH1 when their sources publish 2023+ (CDD), 2026 (NERC) and 2026
  (Environment Canada).
- Get the TSB record through a route the TSB offers.
- Part A did not write out CR1's query set. This is the same gap as the US R1 lane, and the
  next plan must list the queries.

