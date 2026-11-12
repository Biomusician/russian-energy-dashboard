# Oman — first systematic research pass (iteration 19)

**Part A, the search plan, was written on 2026-11-11 before any incident search for Oman was run.**
The source audit that precedes it (`OM_SOURCE_AUDIT.md`) used four searches, all to locate report
endpoints; none was an incident query. Oman has had no research pass of any kind. Its recommended
reporting environment is `corporate_disclosure`: the ministry, the regulator and the national news
agency could not be read by ordinary access, so the lanes below are the closest public
equivalents. **This pass is not expected to complete.**

**Safety first.** This pass collects publicly reported, historical disruption at governorate
precision at most. For a kinetic or sabotage event it collects only that it occurred, its date and
date precision, the broad infrastructure class, the country (a governorate only for an event dated
before 2026), and the effect reported within 7 days. It does **not** collect restart, repair progress, operating rate,
remaining capacity, current outage or current facility condition for such an event, in any field,
and does not cite a page whose address or title states it. `conflict_campaigns.json` records
"Attacks on Omani energy facilities, 2026" (from 2026-01-01) with status `uncertain`, and
uncertain is treated as active. **Every kinetic or sabotage candidate dated on or after
2026-01-01 is therefore a campaign record:** `recovery` not researched, `date_end` null,
`geography_precision` `country`, with no governorate, facility or operator (the lead's precision
ruling for Oman, 2026-11-11). Other events are placed by governorate. The pass never records
coordinates, distances, routes, weapon or method detail, grid topology, line-level or station-level
detail, pipeline routes, cargo, vessel or shipping-route material, or any description of a facility
or a governorate as largest, key, critical or sole. Musandam is recorded as a governorate like any
other.

| | |
|---|---|
| Window | 2022-01-01 to 2026-11-11 |
| Geography | the 11 governorates; Natural Earth codes OM-BA and OM-SH are joined by name (`OM_SOURCE_AUDIT.md` §1) |
| Rule | `inclusion_threshold.json` version `2026-10-30.1`, unchanged |
| Languages | Arabic and English, both mandatory for every lane: a lane run in one language only is partial |
| Declared queries | 30 in total (OM1 2, OM2 2, OM3 2, OM4 4, OM5 20) |

## Part A — plan (written before searching)

### A.1 Lanes

| Lane | Universe kind | Languages | Universe | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|---|---|
| OM1 | report archive | ar+en | Ministry of Energy and Minerals: statements of a disruption, and the oil, gas and refinery tables it supplies to the NCSI Monthly Statistical Bulletin, read only for a change the publication itself attributes to a disruption. A numeric series with no attribution yields context, never an incident | ncsi.gov.om/publications (static, paged; bulletin PDFs on api.ncsi.gov.om, bilingual); mem.gov.om returned a script-only shell on 2026-11-11 and omannews.gov.om a certificate error: try each once by ordinary access, record the result, do not work around | `وزارة الطاقة والمعادن بيان توقف الإنتاج`; `Oman Ministry of Energy and Minerals statement production disruption` | 1, 2, 3, 7 |
| OM2 | report archive | ar+en | OQ group and PDO: historical qualifying interruptions in upstream, refining, gas processing and petrochemical operations, as stated in annual and sustainability reports 2022-2025 and in company releases. Routine maintenance and planned turnarounds are not events. The exchange's disclosure history and OQ Gas Networks' investor pages are documented limitations | oq.com/en/investors/financial-statements-and-reports (static list; annual reports 2021-2025 on assets.oq.com, the 2025 file exceeds the fetch limit); oq.com/en/news-and-media/newsroom (year filter 2019-2026, first page static); oqep.om/reports; PDO sustainability reports as published on edoman.om (2022 and 2025 located; pdo.co.om listings are script-only); msx.om disclosure listing (script-loaded) and oqgn.om (terms gate): try once, record | `OQ PDO Oman unplanned shutdown production halted`; `أوكيو تنمية نفط عمان توقف الإنتاج حريق` | 1, 3, 7 |
| OM3 | report archive | ar+en | Oman LNG: historical material interruptions of LNG production stated in its annual reports 2022-2025, and national LNG context. Nothing about cargoes, vessels or shipping routes is read or recorded | omanlng.co.om/en/Pages/annual-reports.aspx (static list, 2009-2025; PDFs for 2022, 2023, 2024; the 2025 edition is a web page that returned no body text on 2026-11-11) | `Oman LNG plant production halted`; `الشركة العمانية للغاز الطبيعي المسال توقف الإنتاج` | 1, 2 |
| OM4 | report archive | ar+en | Power: Nama Power and Water Procurement annual reports 2022-2025 and 7-Year Statements, read for a major generation or outage event; the regulator's findings on any nationwide or multi-governorate interruption; tropical-cyclone effects on electricity where a source gives a qualifying figure. From OETC only national totals, never line-level, station-level or constraint data | omanpwp.om/annual-report (static, four pages) and /7-year-statement-electricity plus /7-year-statement archive; apsr.om returned a script-only shell and omangrid.com empty report listings on 2026-11-11: try each once, record | `Oman power outage regulator investigation findings APSR`; `هيئة تنظيم الخدمات العامة نتائج التحقيق انقطاع الكهرباء`; `Oman cyclone electricity customers without power`; `إعصار انقطاع الكهرباء عن المشتركين سلطنة عمان` | 4, 5 |
| OM5 | declared query set | ar+en | Arabic and English media by year: Oman Daily, Al-Watan, Al-Shabiba (Arabic); Oman Observer, Times of Oman, Muscat Daily (English); Reuters and S&P Global where a result is readable. State-published titles carry the agency and regulator text; two outlets carrying one agency text are one source | via search; result pages opened by ordinary access on omandaily.om, omanobserver.om, alwatan.om, shabiba.com, timesofoman.com. muscatdaily.com (403), spglobal.com (403) and reuters.com (refused by the fetch tool) are recorded as blocked and their results stay unopened | for each year Y in 2022-2026: `Oman power outage Y`; `انقطاع الكهرباء سلطنة عمان Y`; `Oman refinery gas plant fire shutdown Y`; `حريق مصفاة محطة غاز سلطنة عمان Y` | 1-5, 7 |

Clause 6 (coal) is not searched: coal is not applicable to Oman (`OM_INDEX_READINESS.md` §6).

### A.2 Safety

Event occurrence and the effect reported at the time only, as in the safety paragraph above.
Citations published more than 7 days after a kinetic or sabotage event, and addresses or titles
that announce status, stay in the local queue. For non-conflict events (technical, natural
hazard), observed restoration may be recorded as the brief allows, with the cause held at class
level: a named line, station or unit is never recorded. Every candidate is read end to end by a
safety reviewer before import.

### A.3 Budget, resilience, review

Thirty declared queries, run exactly as written; a follow-up search is declared in the lane log
before it is run and counted. Enumerate the listings in the "Endpoint" column directly before
searching. The worker writes its lane log and candidate file after every source family. Refused
access (403, certificate error, terms gate, script-only listing) is recorded and never worked
around. A query set fully run is `declared_search_complete`, never a census; a lane run in one
language is `partial`. Every lane-accepted record goes through blind three-role review
(`REVIEW_GOVERNANCE.md` §7) and confirmation before import.

## Part B — execution (written after the pass, 2026-11-11)

**This pass did not finish.** 0 of 5 lanes ran as far as declared; 5 were stopped by the shared limit of 200 web searches per turn, which was not worked around. Each lane states below what did not run. A blocked source (HTTP 402 or 403, login wall, script-only page) was recorded as blocked and left.

| Lane | Execution | Source window | Covered through | Queries | Items read | Languages required | Languages run |
|---|---|---|---|---|---|---|---|
| OM1 | partial; stopped by search limit | current_through_end_date | not reached | 0 of 2 | 4 of 58 | ar, en | ar, en |
| OM2 | partial; stopped by search limit | current_through_end_date | 2025-12-31 | 0 of 2 | 5 of 14 | ar, en | en |
| OM3 | partial; stopped by search limit | current_through_end_date | 2024-12-31 | 0 of 2 | 2 of 4 | ar, en | en |
| OM4 | partial; stopped by search limit | current_through_end_date | 2025-12-31 | 3 of 4 | 5 of 9 | ar, en | ar, en |
| OM5 | partial; stopped by search limit | no_census_exists | not reached | 7 of 20 | 64 | ar, en | ar |

Candidates 14: accepted after blind review 1, rejected 3, duplicate 0, held 7, out of scope 3. Published records in this system after the pass: 1.

**Result.** One grid event is published, accepted under clause 5 on stated extent with no customer count (see the correction note in OM_SOURCE_AUDIT.md). Ministry, regulator and operator publication pages were mostly script-only or larger than the fetch tool reads; the annual reports that were read carry no outage narrative.

**Review.** Every published record was reviewed blind by three independent roles (evidence, safety, taxonomy), reconciled, and confirmed by all three on the text the import gate publishes. A hold from any role held the record.

### Limitations, per lane

- **OM1**: The listing at ncsi.gov.om/publications?page=N is static but mixes all publication types at six per page with no working type filter, so the other issues were not located.
- **OM2**: Five of fourteen reports were read. Nine were not: four are over the fetch size limit, one timed out twice, two have links that resolve to cover images, and the two OQEP annual reports have no reachable address. The exchange's disclosure history and the gas-network company's investor pages remain unread.
- **OM3**: Two of four editions were read, both in English. The 2022 edition is over the size limit in both languages and the 2025 edition returns no body text. Cargo, vessel and delivery passages were not recorded.
- **OM4**: Three of four declared queries were run, the cap; the English cyclone query was not. Two of four annual reports are over the fetch size limit and one 7-Year Statement issue is not listed. The regulator's site is unreadable, so whether it publishes investigation reports or interruption statistics is still not established; its statements were read only as the press carried them. No transmission-company document was read. The interconnection and reinforcement passages of the 7-Year Statements and all per-plant rows were not recorded.
- **OM5**: Seven of twenty declared queries ran, all Arabic; no English query ran, so the lane is partial in language as well as in count. The year token barely filters: every power query returned the same 2022 and mid-2026 pages, and the fire strings returned no Omani refinery or gas-plant incident at all, so 2023 and 2024 are years in which the queries found nothing, not years shown to be quiet.
