# United Arab Emirates — first systematic research pass (iteration 19)

**Part A, the search plan, was written on 2026-11-11 before any incident search for this country
was run.** The source audit that precedes it (`AE_SOURCE_AUDIT.md`) tested how each source is
reached and ran four searches to locate sources; it researched no incident.

**Safety first.** The campaign-status lane records attacks on UAE energy facilities during the
2026 war, with the campaign's state **uncertain** and no reported end, and recommends applying the
campaign policy from 2026-01-01 (`data/candidates/gulf19/campaign_status.json`). Until the lead
rules otherwise, every kinetic or sabotage record dated 2026 is treated as a campaign record. This
pass collects only that an event occurred, its date and date precision, the broad infrastructure
class, the country, and the effect reported at the time (within 7 days). It does **not** collect
restart, operating rate, repair progress, remaining capacity, current outage or facility
condition, coordinates, routes, method or defences, even where public, in any field. Company
results documents for 2026 periods are not opened. A page whose address or title states later
status is not cited. Nothing about the nuclear power site is researched or recorded beyond the
national generation figure in the profile.

| | |
|---|---|
| Window | 2022-01-01 to 2026-11-11 |
| Geography | the seven emirates; two jointly administered areas are drawn and never used |
| Event geography | country level by default for kinetic or security events; emirate level for non-conflict grid and weather events reported across an emirate (`AE_SOURCE_AUDIT.md` §1) |
| Rule | `inclusion_threshold.json` version `2026-10-30.1`, unchanged |
| Languages | Arabic and English, both mandatory for every lane |
| Declared queries | 36 in total (AE1 10, AE2 4, AE3 4, AE4 18) |

## Part A — plan (written before searching)

### A.1 Lanes

| Lane | Universe kind | Languages | Universe | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|---|---|
| AE1 | declared query set | ar+en | National statements: Ministry of Energy and Infrastructure and other federal statements as carried by WAM. WAM renders by script and cannot be enumerated or opened by ordinary access, so this is a query set, not an archive; a WAM citation is `opened: false` unless a person opens it | wam.ae (script-only shell on home, search and both article patterns; search restricted to the domain returns titles); moei.gov.ae (connection closed, three attempts); u.ae energy pages (readable; context, no event notices) | for each year Y in 2022-2026: `وام وزارة الطاقة والبنية التحتية بيان انقطاع إمدادات الطاقة Y`; `WAM UAE Ministry of Energy and Infrastructure statement energy supply disruption Y` | 1, 2, 3, 4, 5, 7 |
| AE2 | report archive | ar+en | ADNOC group, for historical qualifying disruptions in oil, gas, LNG, refining and processing. Routine and planned maintenance is not an event. Enumerated universe: ADNOC Gas Annual Report 2023 and Integrated Reports 2024 and 2025, read for incident occurrence only. 2026 quarterly documents, results releases and data books are outside the universe and are not opened. ADX refusal is a documented limitation | adnocgas.ae/en/investor-relations/results-reports (static list, readable); adnocgas.ae announcements (page loads, "service unavailable"); borouge.com company announcements (paged, readable); adnoc.ae (HTTP 403); adx.ae (HTTP 403) | `ADNOC fire explosion refinery gas plant shutdown force majeure`; `ADNOC Gas ADX disclosure incident production halted`; `أدنوك حريق انفجار مصفاة مصنع غاز توقف الإنتاج`; `أدنوك للغاز إفصاح سوق أبوظبي للأوراق المالية حادث قوة قاهرة` | 1, 2, 3, 7 |
| AE3 | report archive | ar+en | Electricity utilities and regulators, major events only, including the April 2024 storm if a source reports a qualifying energy effect (customers affected, a plant forced offline, or an operator emergency declaration). Enumerated universe: EWEC media releases 2020-12-22 to date; Etihad Water and Electricity news by year 2022-2026; SEWA news listing | ewec.ae/media-releases (one long page, readable; finish the unread tail from offset 100000); etihadwe.ae/en/MediaCenter/Pages/News.aspx (year filter, readable); sewa.gov.ae/en/news-and-events (13 items, readable); doe.gov.ae news (zero results to ordinary access); dewa.gov.ae (HTTP 403); dfm.ae disclosures (script-only); taqa.com (CAPTCHA) | `UAE storm April 2024 power outage customers DEWA SEWA statement`; `أمطار أبريل 2024 انقطاع الكهرباء الشارقة دبي هيئة الكهرباء بيان`; `UAE power outage DEWA SEWA EWEC Etihad Water and Electricity statement customers affected`; `انقطاع التيار الكهربائي الإمارات هيئة كهرباء ومياه بيان المتأثرين` | 4, 5 |
| AE4 | declared query set | ar+en | Arabic and English media by year, and event-occurrence queries for attacks reported on UAE energy facilities (January 2022, and March to May 2026): occurrence, date, class and effect at the time only | via search. Readable for follow-up reading: thenationalnews.com/business/energy/ (dated addresses); khaleejtimes.com section and search listing; gulfnews.com/business/energy; albayan.ae/economy. Not reachable: aletihad.ae (timed out), alkhaleej.ae (HTTP 403), reuters.com (refused by the fetch tool), spglobal.com (HTTP 403) | for each year Y in 2022-2026: `UAE refinery gas plant power station fire outage shutdown Y`; `الإمارات حريق مصفاة محطة كهرباء انقطاع توقف Y`. Then once each: `Abu Dhabi attack fuel facility 17 January 2022`; `هجوم أبوظبي 17 يناير 2022 منشأة نفطية`; `UAE energy facility attack March 2026`; `UAE energy facility attack April 2026`; `UAE energy facility attack May 2026`; `استهداف منشأة طاقة في الإمارات مارس 2026`; `استهداف منشأة طاقة في الإمارات أبريل 2026`; `استهداف منشأة طاقة في الإمارات مايو 2026` | 1-5, 7 |

Query count: AE1 5 × 2 = 10; AE2 4; AE3 4; AE4 5 × 2 + 2 + 3 × 2 = 18. Total 36. A lane searched
in one of its two languages is `partial`. A query set is never a census.

### A.2 Safety

Event occurrence and the effect reported at the time only. For a kinetic or sabotage record:
`recovery` stays not researched, `date_end` null, `geography_precision` `country`,
`admin1_code` null, and `facility_name` only if the facility's own name is what the source
reports as hit. Citations published more than 7 days after such an event, and addresses or titles
that announce status, stay in the local queue. Attacks on ships are not attacks on a country's
energy infrastructure and are out of scope. No query names a route, a strait, a weapon or a
defence system, and none asks which facility matters most.

The January 2022 event is a single event outside the 2026 campaign. It is still placed at country
level under the event-geography rule unless the lead rules that emirate level is safe for it.

### A.3 Budget, resilience, review

Search cap as set by the lead for Wave B; the 36 declared queries are the whole set and none is
added during the pass. Enumerate the readable listings first (AE2, AE3), then run AE4, then AE1.
The output files are written after each lane so another agent can resume. When the cap is
reached or a search is refused, stop searching, finish from direct page requests, and record
exactly which declared queries did not run. Blocked endpoints are recorded once and not retried
or worked around. Blind three-role review before import, as in `SA_LANE_PASS_18.md`.

## Part B — execution (written after the pass, 2026-11-11)

**This pass did not finish.** 0 of 4 lanes ran as far as declared; 4 were stopped by the shared limit of 200 web searches per turn, which was not worked around. Each lane states below what did not run. A blocked source (HTTP 402 or 403, login wall, script-only page) was recorded as blocked and left.

| Lane | Execution | Source window | Covered through | Queries | Items listed or read | Languages required | Languages run |
|---|---|---|---|---|---|---|---|
| AE1 | partial; stopped by search limit | inaccessible | not reached | 1 of 10 | - | ar, en | ar |
| AE2 | partial; stopped by search limit | publisher_not_yet_released | 2025-12-31 | 1 of 4 | 73 | ar, en | ar, en |
| AE3 | partial; stopped by search limit | rolling_archive_gap | 2026-11-05 | 2 of 4 | 269 | ar, en | ar, en |
| AE4 | partial; stopped by search limit | no_census_exists | not reached | 8 of 18 | - | ar, en | ar, en |

Candidates 21: accepted after blind review 0, rejected 2, duplicate 1, held 15, out of scope 3. Published records in this system after the pass: 0.

**Result.** No record from this pass is published. 15 candidates are held: by a reviewer, by the lead, by the import gate, or for an owner decision (ITERATION_19_REVIEW.md, section 27). What each one is stays in the local review queue. The emirate utilities' and regulators' pages returned no dated outage with a qualifying figure.

**Review.** Every published record was reviewed blind by three independent roles (evidence, safety, taxonomy), reconciled, and confirmed by all three on the text the import gate publishes. A hold from any role held the record.

### Limitations, per lane

- **AE1**: The shared search allowance ran out before every declared query was run. Not run in every language its plan requires.
- **AE2**: The shared search allowance ran out before every declared query was run. At least one source in this lane refused automated access and was not worked around.
- **AE3**: The shared search allowance ran out before every declared query was run. Official statements were read as carried by other publishers, not on the issuing body's own site. The listings that could be read were read in part: by title, or for their newest pages only. Some declared documents were not read.
- **AE4**: The shared search allowance ran out before every declared query was run. At least one source in this lane refused automated access and was not worked around. No complete public list of events exists for this lane, so a search that finds nothing is not a year shown to be quiet.
