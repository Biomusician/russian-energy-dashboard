# Saudi Arabia — first systematic research pass (iteration 17)

**Part A, the search plan, was written on 2026-11-03 before any search of this pass was run.**
Saudi Arabia has had targeted searches only, and has an attack campaign recorded as active
(`conflict_campaigns.json`). **The safety review here is stricter than elsewhere:** the pass
looks for event occurrence only, never for facility restart, operating rate, repair progress or
current status, and the active-campaign rules in CURRENT_EVENT_PUBLICATION_POLICY.md apply to
every candidate before review. **This pass is not expected to complete.**

| | |
|---|---|
| Window | 2022-01-01 to 2026-11-03 |
| Geography | the 13 provinces |
| Rule | `inclusion_threshold.json` version `2026-10-30.1`, unchanged |
| Languages | Arabic and English, both mandatory for SA1 and SA5 |

## Part A — plan (written before searching)

### A.1 Lanes

| Lane | Universe | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|
| SA1 | Ministry of Energy statements, as carried by the Saudi Press Agency | spa.gov.sa; moenergy.gov.sa | for each year Y: `وزارة الطاقة مصدر مسؤول استهداف Y`; `Saudi energy ministry statement attack facility Y` | 1, 2, 3, 7 |
| SA2 | Saudi Aramco disclosures: Tadawul announcements and annual-report incident statements | saudiexchange.sa announcements; aramco.com | `Aramco Tadawul announcement incident`; `أرامكو إعلان تداول حادث` | 1, 7 |
| SA3 | GASTAT and JODI production releases, read only for production effects explicitly attributed to a disruption | stats.gov.sa; jodidata.org | none; enumeration only | 7 |
| SA4 | OPEC Monthly Oil Market Report: production changes the report attributes to a disruption | opec.org MOMR archive | none; enumeration only | 7 |
| SA5 | International reporting: Reuters, Bloomberg, AP, S&P Global, Argus | via search | for each year Y: `Saudi refinery fire shut Y`; `Saudi Aramco facility attack Y`; `Saudi power outage Y` | 1-7 |

### A.2 Safety

Event occurrence and the effect reported at the time only. No restart, recovery, operating-rate,
repair or dependency content is recorded even in the local queue's published fields. Late
citations (more than 7 days after a covered event) and status-bearing citation addresses stay in
the queue.

### A.3 Review and budget

Split agents, fixed search caps, progress after each lane, blind three-role review before import.

## Part B — execution record

Run on 2026-11-03 against the plan as committed in `a7f3a36`. The research log (`data/curated/systems/sa/research_log.json`) is the record; this section restates it as counts.

**0 of 5 lanes complete** for the window 2022-01-01 to 2026-11-03. A lane is complete only if its declared universe was searched to the end of the window; none was.

### B.1 Dispositions

candidate counts are kept in the local research queue (iteration 20 safety review)

No candidate was accepted by a lane; most were duplicates of published records, and the rest stay in the local queue with their reasons.

### B.2 Lane by lane

| Lane | Status | Covered through | Why not complete |
|---|---|---|---|
| SA1 | partial | 2026-11-03 | SPA and the ministry site could not be enumerated directly (SPA renders by script; moenergy.gov.sa did not respond), so the lane depends on search; four English year-queries were not run under the 15-search cap; the 2022 Arabic query was run unfiltered and the first attempt was cut off (counted). |
| SA2 | partial | 2026-11-03 | Both queries were run (search covers all years), but the Tadawul announcement list refused automated access (403) and aramco.com's news list rendered only its latest item, so the declared universe was not enumerated; the 2022-2025 annual reports were not read. |
| SA3 | partial | 2022-01-01 | JODI's universe carries no attribution text by design, so it can never supply an attributed production effect; GASTAT's energy release listing was not reached. Not searched across the window. |
| SA4 | partial | 2022-01-01 | The MOMR archive refused automated access (HTTP 402 on both the legacy and current addresses). No issue was read. |
| SA5 | partial | 2026-11-03 | 6 of the plan's 15 SA5 queries were run before the 15-search personal cap; 2023 and 2024 had no query; several outlets refused (402/login wall). |

### B.3 What the next pass must do

Run the lanes marked not started first, then the partial lanes from their `covered_through` date. Refusals (HTTP 402/403, login walls, script-rendered listings) are not worked around; a lane that depends on one stays partial and says so.

