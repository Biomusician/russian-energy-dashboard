# Saudi Arabia — research pass (iteration 19, Gulf deepening)

**Part A, the search plan, was written on 2026-11-11 before any search of this pass was run.**
Lanes and order are those of `SA_SYSTEMATIC_SWEEP.md` and `SA_LANE_PASS_18.md`. Inclusion rule
version `2026-10-30.1`, unchanged. Window 2022-01-01 to 2026-11-11. Coverage vocabulary as in
`US_LANE_PASS_18.md`.

**Why this pass exists.** Iteration 18's Saudi pass was stopped by the shared search limit with
SA1 not started and SA5 run for 2022 and 2023 only. This pass declares exactly the queries that
pass did not run, plus direct enumeration of the archives that can be read. It does not rebuild
the Saudi system and re-opens no published record.

**Safety first.** An attack campaign is recorded as active (`conflict_campaigns.json`, checked
2026-11-11). This pass collects event occurrence, the effect reported at the time and the admin-1
historical record. It does **not** collect restart, current operating rate, repair progress,
remaining capacity, current outage or current facility condition, even where public, in any field.
Aramco's 2026 interim reports and results releases are not opened. Nothing about export routes,
vessel movements, pipeline routes or grid topology is read or written down.

## Part A — plan (written before searching)

### A.1 Lanes

`Y` stands for the years named in each row.

| Lane | Universe kind | Languages | Universe | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|---|---|
| SA1 | report archive | ar+en | Ministry of Energy statements as carried by SPA | spa.gov.sa and moenergy.gov.sa by ordinary access (both refused on 2026-11-10; tried once more) | for each Y in 2022-2026: `وزارة الطاقة مصدر مسؤول استهداف Y`; `Saudi energy ministry statement attack facility Y` (10) | 1, 2, 3, 7 |
| SA2 | report archive | ar+en | Aramco annual reports 2022-2025, Arabic editions, for incident occurrence. 2026 interim documents are outside the universe | aramco.com annual reports (Arabic PDFs) by ordinary access; saudiexchange.sa (refused on 2026-11-10; tried once more) | `Aramco Tadawul announcement incident`; `أرامكو إعلان تداول حادث` (2) | 1, 7 |
| SA3 | report archive | ar+en | GASTAT monthly industrial production releases 2022-2025, read only for disruption-attributed commentary. A numeric series with no attribution yields context, never an incident | stats.gov.sa release listing | none; enumeration only | 7 |
| SA4 | report archive | en | OPEC Monthly Oil Market Report: production changes attributed to a disruption | opec.org (HTTP 402 on 2026-11-10 and 2026-11-11; tried once more, then recorded as blocked) | none; enumeration only | 7 |
| SA5 | declared query set | ar+en | International and regional reporting, the years iteration 18 did not reach | via search; Arabic first | for each Y in 2024, 2025, 2026: `حريق مصفاة السعودية Y`; `انقطاع الكهرباء السعودية Y`; `Saudi refinery fire shut Y`; `Saudi Aramco facility attack Y`; `Saudi power outage Y` (15) | 1-7 |

Declared queries: 27 (SA1 10, SA2 2, SA5 15).

### A.2 Safety

Citations published more than 7 days after a covered event, and addresses that announce status, stay
in the local queue. A 2026 kinetic or sabotage candidate records occurrence, date, class, region and
the effect reported at the time only; its recovery is not researched. Every Saudi record that would
be published is read end to end by a safety reviewer.

### A.3 Budget, resilience, review

The shared search allowance is nearly spent and this pass has a hard cap stated in its task. Order:
enumerate SA2 and SA3 by direct reading; then SA5 in the order written, 2026 first; then SA1. A
declared query that does not run is logged as not run, with `stopped_by: search_limit`, never
substituted. The output file is written after each lane. Blind three-role review before import
(`REVIEW_GOVERNANCE.md`).
