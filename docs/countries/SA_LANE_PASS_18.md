# Saudi Arabia — research pass (iteration 18)

**Part A, the search plan, was written on 2026-11-10 before any search of this pass was run.**
Lanes and order are those of `SA_SYSTEMATIC_SWEEP.md`. Inclusion rule version `2026-10-30.1`,
unchanged. Window 2022-01-01 to 2026-11-10. Coverage vocabulary as in `US_LANE_PASS_18.md`.

**Safety first.** An attack campaign is recorded as active (`conflict_campaigns.json`). This pass
collects event occurrence, the effect reported at the time and the admin-1 historical record. It
does **not** collect restart, current operating rate, repair progress, remaining capacity, current
outage or current facility condition, even where public, in any field.

## Part A — plan (written before searching)

### A.1 Lanes

| Lane | Universe kind | Languages | Universe | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|---|---|
| SA1 | report archive | ar+en | Ministry of Energy statements as carried by SPA | spa.gov.sa; moenergy.gov.sa public search or index pages by ordinary access | for each year Y in 2022-2026: `وزارة الطاقة مصدر مسؤول استهداف Y`; `Saudi energy ministry statement attack facility Y` | 1, 2, 3, 7 |
| SA2 | report archive | ar+en | Aramco annual reports 2022-2025; investor disclosures for incident occurrence. Tadawul refusal is a documented limitation | aramco.com annual reports; saudiexchange.sa by ordinary access | `Aramco Tadawul announcement incident`; `أرامكو إعلان تداول حادث` | 1, 7 |
| SA3 | report archive | ar+en | GASTAT and JODI production releases, read only for disruption-attributed commentary. A numeric series with no attribution yields context, never an incident | stats.gov.sa; jodidata.org | none; enumeration only | 7 |
| SA4 | report archive | en | OPEC Monthly Oil Market Report: production changes attributed to a disruption | opec.org archive, official downloadable monthly PDFs by ordinary access | none; enumeration only | 7 |
| SA5 | declared query set | ar+en | International and regional reporting | via search; Arabic query for each English family | for each year Y in 2022-2026: `Saudi refinery fire shut Y`; `Saudi Aramco facility attack Y`; `Saudi power outage Y`; and `حريق مصفاة السعودية Y`; `انقطاع الكهرباء السعودية Y` | 1-7 |

### A.2 Safety

Citations published more than 7 days after a covered event, and addresses that announce status, stay
in the local queue. Every published Saudi record is read end to end by a safety reviewer in this pass.

### A.3 Budget, resilience, review

As `US_LANE_PASS_18.md` A.3.

## Part B — execution (written after the pass, 2026-11-10)

**This pass did not finish.** A shared limit of 200 web searches per turn was reached about two-thirds of the way through. Direct page requests still worked. The limit was not worked around, and every lane it stopped says so. A new turn is needed to run the remaining queries: `scripts/research_tools.py next sa`.

| Lane | Execution | Source window | Covered through | Queries | Languages run |
|---|---|---|---|---|---|
| SA1 | not_started; stopped by search limit | inaccessible | not reached | 0 of 10 | none |
| SA2 | partial; stopped by search limit | inaccessible | 2025-12-31 | 0 of 2 | en |
| SA3 | partial | current_through_end_date | not reached | 0 of 0 | en |
| SA4 | not_started | inaccessible | not reached | 0 of 0 | none |
| SA5 | partial; stopped by search limit | no_census_exists | not reached | 10 of 25 | ar, en |

Candidates 13: accepted after blind review 0, rejected 6, duplicate 1, held 3, out of scope 3.

**Campaign safety (brief §49-55).** Occurrence only. Restart, operating rate, repair progress and current outage status were deliberately not collected, including Aramco's 2026 interim reports. The Arabic status check was added this pass. Citations that named status, weapon-independent throughput or a later date were moved back to the local queue.

**Result.** No new event passed. Two lanes could not start: every SPA, ministry and OPEC route refused access, and the declared queries were stopped by the search limit. Annual reports for FY2022-25 were read in English, and GASTAT releases do not attribute changes to a disruption.

**Corpus audit.** Five records' text or citations tightened. No record's recovery status is published while the campaign is recorded as active.

### Limitations, per lane

- **SA1**: Nothing was searched or read in this pass: all ten declared queries were refused by the shared search limit (five attempted, none performed), and SPA (HTTP 403) and the ministry site (no response) refused ordinary access once each. The four English year queries for 2022-2025 have still never been run in any pass.
- **SA2**: The Tadawul announcement list refused access (HTTP 403) and was not read; neither declared query ran (shared search limit); the Arabic annual reports were not read (English editions only). Aramco's 2026 interim reports and results releases were deliberately not opened: they are outside the declared 2022-2025 annual-report universe and would carry current operating information during the active campaign.
- **SA3**: Only two monthly IPI release PDFs were read in full (March and April 2026, English), so no continuous span is covered and covered_through is null. The 2022-2025 monthly releases, the Arabic editions and GASTAT's petroleum-and-gas statistics were not read, and the search listing did not show a complete 2022-2025 series on the pages opened. JODI's Saudi metadata page was not reached.
- **SA4**: All three official OPEC addresses tried (current page, the MOMR download host, the legacy publications page) refused automated access with HTTP 402. No issue was read and no workaround was attempted; the lane needs a person to open the PDFs in a browser.
- **SA5**: Only the 2022 and 2023 query combinations ran (10 of 25, both languages); the shared session search limit refused the 2024 set and prevented 2025 and 2026 entirely, and no follow-up search ran.
