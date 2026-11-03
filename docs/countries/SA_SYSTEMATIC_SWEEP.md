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

*(Filled in after the lanes run. Counts only.)*
