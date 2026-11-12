# Kuwait — first systematic research pass (iteration 19)

**Part A, the search plan, was written on 2026-11-11 before any incident search for Kuwait was run.**
The source audit that precedes it ([KW_SOURCE_AUDIT.md](KW_SOURCE_AUDIT.md)) tested how each source
is reached and read national statistics only; it researched no incident. Inclusion rule version
`2026-10-30.1` (`data/curated/systems/inclusion_threshold.json`), unchanged. Window 2022-01-01 to
2026-11-11.

**Safety first.** A campaign is recorded for Kuwait (`conflict_campaigns.json`,
`kw-2026-attacks-on-energy-facilities`, status `uncertain`, treated as active, from 2026-01-01). For
any kinetic or sabotage event this pass collects only that it occurred, its date and date
precision, the broad infrastructure class, and the effect reported at the time (within 7 days).
Such records are placed at **country level**, for every date in the window: Kuwait's refineries,
terminals and most large power and water plants sit in two or three governorates, so a governorate
and a class together would name the facility. The pass does **not** collect recovery, restart,
repair progress, current operating rate, remaining capacity, current outage or current facility
condition, even where public, in any field, and does not cite a page whose address or title states
later status. It never collects per-facility capacity, tanker, cargo or route material,
coordinates, weapon or defence detail, pipeline routes or grid topology, and it attributes nothing
to a field in the Partitioned Zone. Routine and planned maintenance is not an event. Scheduled,
routine load shedding with no dated qualifying loss is not an event. A change in an annual or
monthly total with no stated cause is context, never an event.

| | |
|---|---|
| Window | 2022-01-01 to 2026-11-11 |
| Geography | country level for attacks and sabotage; one of the 6 governorates drawn by Natural Earth for other events; offshore and Partitioned Zone events with no clear side are country level |
| Rule | `inclusion_threshold.json` version `2026-10-30.1`, unchanged |
| Languages | Arabic and English, both mandatory for every lane |
| Declared queries | 30 in total (KW1 2, KW2 4, KW3 4, KW4 20) |

## Part A — plan (written before searching)

### A.1 Lanes

| Lane | Universe kind | Languages | Universe | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|---|---|
| KW1 | report archive | ar+en | Oil sector operators and ministry: Kuwait Petroleum Corporation, KNPC, KOC, KIPIC and the Ministry of Oil. Statements about a dated operational disruption, and the KNPC annual reports for fiscal years 2021-22 to 2025-26, read for incident occurrence only. Routine maintenance and turnarounds are not events | `https://www.knpc.com/en/media-center/publications/reports/annual-reports` (static listing of PDF reports; fiscal year 2023-24 is not listed; PDFs not yet opened, so a size or access failure is a documented limitation). No statement list can be enumerated: `https://www.kpc.com.kw/PublicStatements` and `/Publications?filter=AnnualReport` render "Loading..." only; `https://www.kockw.com/sites/EN/Pages/Media%20Center/News%20And%20Events/Allitems.aspx` and `/annual-report.aspx` render no items; `kipic.com.kw` fails TLS; `www.moo.gov.kw` does not answer. All four are SOURCE_BLOCKED and not worked around. Statements are read as carried by the press | `مؤسسة البترول الكويتية بيان حادث حريق توقف وحدات`; `Kuwait Petroleum Corporation KNPC KOC statement fire incident units shut` | 1, 2, 3, 7 |
| KW2 | report archive | ar+en | Electricity: the Ministry of Electricity, Water and Renewable Energy. Major outages, and emergency or programmed-cut announcements that give a dated qualifying loss (megawatts shed, a plant of the rule's size forced offline, or customers cut), including the summer 2024 and 2025 load-shedding episodes if a source gives a qualifying figure. No area schedule below the governorate, no substation, feeder or line detail. A water-only interruption is outside the rule | `https://www.mew.gov.kw/ar/media-center/news/` and `https://www.mew.gov.kw/en/media-center/news/` (static, one long page each, newest 2026-11-05, with a pager 1-4; items at `/ar/NewsDetails?fromurl=news&&newsname=CODE`): enumerate titles dated 2022-01-01 to 2026-11-11 in both languages, open only those that state an outage, a programmed or emergency cut, a plant fault or a storm effect. The list is out of date order and thin before late 2024, so it is an archive with a known gap, not a census. `https://www.mew.gov.kw/en/about/statistics/` carries no outage table and no file: context only | `وزارة الكهرباء والماء والطاقة المتجددة بيان انقطاع التيار الكهربائي`; `Kuwait Ministry of Electricity statement power outage`; `الكويت القطع المبرمج للكهرباء الأحمال ميغاواط`; `Kuwait programmed power cuts load shedding megawatts` | 4, 5 |
| KW3 | declared query set | ar+en | Official statements as carried by the Kuwait News Agency (KUNA), Arabic and English: oil companies, the oil ministry, the electricity ministry, the fire force. A press copy of a KUNA statement is the same source, not a second one | no census exists and no listing is readable: `https://www.kuna.net.kw/Default.aspx?language=ar` and `?language=en` return a title only, and article addresses of the form `https://www.kuna.net.kw/ArticleDetails.aspx?id=N&language=ar` returned no body for the two numbers tried. SOURCE_BLOCKED for enumeration. A KUNA item found by a query is cited `opened: false` unless its text is actually read | `كونا بيان حريق منشأة نفطية الكويت`; `KUNA statement fire oil facility Kuwait`; `كونا وزارة الكهرباء انقطاع التيار عن مناطق`; `KUNA electricity ministry power outage areas statement` | 1-7 |
| KW4 | declared query set | ar+en | Arabic and English media by year 2022-2026: Al-Qabas, Al-Rai, Al-Anba, Al-Jarida, Arab Times, Kuwait Times, and international reporting (Reuters, S&P Global, Al Jazeera) as it appears in search results. Includes occurrence-only queries for any attack reported on a Kuwaiti energy facility: occurrence, date, class and effect at the time only | via search. To open a known date, Arabic: `https://www.aljarida.com/archive/YYYY/M/D` (static, day by day, 2007-2026; not run as a census). Supplementary, Arabic: `https://www.alraimedia.com/نفط` (static, 9 items, no pager seen: latest items only). English: `https://www.arabtimesonline.com/news/category/kuwait/` and `https://kuwaittimes.com/kuwait` (static first page only; undated addresses). `alqabas.com` returns a title only and `alanba.com.kw` returns HTTP 403: SOURCE_BLOCKED, search results only, `opened: false`. Reuters and S&P Global were not tested by this lane and are recorded as blocked in the Qatar audit: search results only, `opened: false` | for each year Y in 2022-2026: `الكويت حريق مصفاة أو منشأة نفطية Y`; `Kuwait refinery OR oil facility fire shutdown Y`; `استهداف منشآت الطاقة في الكويت Y`; `Kuwait energy facility attack reported Y` | 1-7 |

Query count: KW1 2 (1 ar, 1 en); KW2 4 (2 ar, 2 en); KW3 4 (2 ar, 2 en); KW4 4 per year for five
years, 20 (10 ar, 10 en). **Total 30.** No follow-up query is declared. A query that is refused or
not reached is listed in the lane log as not run. Order of work: enumerate KW2 and the KW1 report
listing first; then run queries in the order KW4 (2026 back to 2022, Arabic first), KW2, KW3, KW1.

### A.2 Safety

- Every kinetic or sabotage candidate, whatever its date: `geography_precision: "country"`,
  `admin1_code: null`, `admin1_codes_affected: []`, an id of the form
  `kw-<date>-<asset-class>-attack-<n>`, and `summary`, `effect` and `threshold_basis` that name no
  facility, operator, town, industrial area or governorate.
- Kinetic and sabotage candidates dated from 2026-01-01: `date_end: null` and
  `recovery.research_status: "NOT_YET_RESEARCHED"` exactly as the brief's schema shows. Recovery,
  restart, repair and operating status are not collected for them at all.
- Citations published more than 7 days after a covered event, and addresses or titles that announce
  status, stay in the local queue and are not opened.
- The two attack-occurrence queries per year in KW4 will return pages that also carry later status,
  export-route and shipping material for 2026. The researcher reads the dated occurrence and the
  effect stated at the time, and nothing else on the page. A count of attacks given by a source is
  context for the lane's `finding`, not a set of records.
- The KNPC report for fiscal year 2025-26 covers months inside the campaign. From it, only
  occurrence, date, class and the effect stated at the time may be taken; nothing about damage
  extent, repair, restart or throughput afterwards.
- A non-conflict candidate is placed in a governorate. An area list in an electricity announcement
  is read only to find the governorates and the stated loss; it is not copied.
- An event in the Partitioned Zone is placed by the boundary Natural Earth draws where the source
  makes the side clear, and at country level otherwise. Offshore events are country level.
- An attack on a tanker, a ship or a port as shipping is out of scope: one line, `out_of_scope`.
- Every candidate, including rejects, is read end to end by a safety reviewer before import.

## Part B — execution (written after the pass, 2026-11-11)

**This pass did not finish.** 0 of 4 lanes ran as far as declared; 3 were stopped by the shared limit of 200 web searches per turn, which was not worked around. Each lane states below what did not run. A blocked source (HTTP 402 or 403, login wall, script-only page) was recorded as blocked and left.

| Lane | Execution | Source window | Covered through | Queries | Items listed or read | Languages required | Languages run |
|---|---|---|---|---|---|---|---|
| KW1 | partial | rolling_archive_gap | 2026-03-31 | 2 of 2 | 4 of 5 | ar, en | ar, en |
| KW2 | partial; stopped by search limit | rolling_archive_gap | 2026-11-05 | 2 of 4 | 655 of 655 | ar, en | ar, en |
| KW3 | partial; stopped by search limit | no_census_exists | not reached | 2 of 4 | - | ar, en | ar |
| KW4 | partial; stopped by search limit | no_census_exists | not reached | 9 of 20 | - | ar, en | ar |

Candidate counts are kept in the local research queue (iteration 20 safety review). Published records in this system after the pass: 5.

**Result.** 5 records from this pass are published. Additional candidates remain under review: by a reviewer, by the lead, by the import gate, or for an owner decision (ITERATION_19_REVIEW.md, section 27). What each one is stays in the local review queue. The ministry's Arabic and English listings were read by title for the window.

**Review.** Every published record was reviewed blind by three independent roles (evidence, safety, taxonomy), reconciled, and confirmed by all three on the text the import gate publishes. A hold from any role held the record.

### Limitations, per lane

- **KW1**: Not run as far as declared in this pass.
- **KW2**: The shared search allowance ran out before every declared query was run. At least one document was too large for the fetch tool or timed out.
- **KW3**: The shared search allowance ran out before every declared query was run. Not run in every language its plan requires. No complete public list of events exists for this lane, so a search that finds nothing is not a year shown to be quiet.
- **KW4**: The shared search allowance ran out before every declared query was run. Not run in every language its plan requires. The listings that could be read were read in part: by title, or for their newest pages only. No complete public list of events exists for this lane, so a search that finds nothing is not a year shown to be quiet.
