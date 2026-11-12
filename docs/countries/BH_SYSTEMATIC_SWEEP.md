# Bahrain — first systematic research pass (iteration 19)

**Part A, the search plan, was written on 2026-11-11 before any search of this pass was run.**
Bahrain has never been researched. Its reporting environment is provisionally `media_only`: no
operator, authority or regulator page reached publishes event-level outage or incident reports
(`BH_SOURCE_AUDIT.md`). **A small corpus is the expected result. Few records found is not few
disruptions:** there is no register to count against, so coverage will read "unknown".

**Safety first.** This pass collects, for any event, only that it occurred, its date and date
precision, the broad infrastructure class, the country and (only where the rule below allows) the
governorate, and the effect reported at the time, within 7 days. It does **not** collect restart
dates, repair progress, operating rate, remaining capacity or current outage status of any facility,
nor coordinates, distances, weapon or method detail, defences, shipping or export-route material,
grid topology or substation-level material, even where public. If `conflict_campaigns.json` records
a campaign for Bahrain, every kinetic or sabotage candidate follows
`CURRENT_EVENT_PUBLICATION_POLICY.md` §1-§3 before review: `recovery` stays not researched,
`date_end` stays null, and a page whose address or title states later status is not cited.
**Bahrain is a microstate: every kinetic or security event is recorded at COUNTRY level. An
industrial or natural-hazard event uses a governorate only where a safety reviewer finds it
non-identifying. No event is ever placed in the abolished Central governorate (BH-16).**

| | |
|---|---|
| Window | 2022-01-01 to 2026-11-11 |
| Geography | country level by default; the 4 current governorates (Capital, Muharraq, Northern, Southern) only under the rule above; Natural Earth draws 5 |
| Rule | `inclusion_threshold.json` version `2026-10-30.1`, unchanged |
| Languages | Arabic and English, both mandatory in every lane: a lane run in one language only is partial |
| Declared queries | 24 in total (BH1 5, BH2 4, BH3 15) |

## Part A — plan (written before searching)

### A.1 Lanes

| Lane | Universe kind | Languages | Universe | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|---|---|
| BH1 | report archive | ar+en | Hydrocarbons: Bapco Energies group, Bapco Refining, Bapco Upstream and Bapco Gas press releases, and Ministry of Oil and Environment statements as carried by the Bahrain News Agency. Sought: a material interruption of production, refining or gas processing, or a major industrial incident with a reported effect. Routine and planned maintenance is not an event. Official annual series on data.gov.bh are read for context only; a numeric change with no stated cause yields no incident | bapco.net/en/page/press-releases (static, paged by a "Next" link; verified 2026-11-11); bapcoenergies.com/media-centre/press-releases and /ar/media-centre/press-releases by ordinary access (a bot-manager challenge was met on 2026-11-11: if met again, record SOURCE_BLOCKED and do not follow it); bna.bh by ordinary access (HTTP 405 on 2026-11-11: record and move on) | `بابكو مصفاة حريق توقف وحدة بيان`; `بابكو للغاز بناغاز حادث توقف الإنتاج`; `البحرين استهداف منشأة نفطية بيان رسمي`; `Bapco Refining fire unit shutdown statement`; `Bahrain oil gas facility attack official statement` | 1, 2, 3, 7 |
| BH2 | report archive | ar+en | Electricity: Electricity and Water Authority statements of a major outage, a generation interruption or a grid emergency. National or governorate scale only; no substation-level, feeder-level or interconnector material is recorded. Planned interruptions for maintenance are not events | ewa.bh/ar/news?page=1 to 9 (79 items on 2026-11-11) and ewa.bh/en/news?page=1 to 8 (69 items); read every item title and date, open only items that concern supply interruption. The listing begins in 2024, so 2022-2023 rest on the queries alone | `هيئة الكهرباء والماء انقطاع التيار الكهربائي بيان`; `هيئة الكهرباء والماء خلل فني محطة إنتاج الكهرباء انقطاع`; `EWA Bahrain power outage statement`; `Bahrain blackout Electricity and Water Authority generation fault` | 4, 5 |
| BH3 | declared query set | ar+en | Arabic and English media by year: Al-Ayam, Akhbar Al Khaleej, Al-Watan, Gulf Daily News, Bahrain News Agency copies, and international corroboration (Reuters, S&P Global). A translation or a syndicated copy of one statement is one account | via search. Direct reading where a result is on akhbar-alkhaleej.com or gdnonline.com (both readable); alayam.com and alwatannews.net returned HTTP 403, reuters.com is refused by the fetch tool and spglobal.com returned HTTP 403 on 2026-11-11, so their results are used only if the page opens by ordinary access | for each year Y in 2022-2026: `البحرين حريق مصفاة توقف الإنتاج Y`; `البحرين انقطاع الكهرباء Y`; `Bahrain refinery gas plant power outage incident Y` | 1-5, 7 |

Clause 6 (coal) is not applicable: Bahrain has no coal sector (`BH_INDEX_READINESS.md` §6).

### A.2 Safety

- Occurrence and the effect reported at the time only. A citation published more than 7 days after
  a kinetic or sabotage event, or whose address or title states status, stays in the local queue.
- Geography: `geography_precision` is `country` and `admin1_code` is null for every kinetic,
  sabotage or security event. For technical and natural-hazard events the researcher proposes a
  governorate only when the source itself names a current governorate; the safety reviewer decides
  whether it is non-identifying, and country level is the fallback. `BH-16` is never used.
- `facility_name` is filled only when the facility's own name is what the source reports. No
  locality, district, island or industrial-area name goes into a summary.
- Not read, even if a result offers it: per-station generation rows, crude-origin and crude-import
  series, station capacity tables, network diagrams (`BH_SOURCE_AUDIT.md` §5).
- A masthead Hijri date is kept as `source_date_text` with `date_calendar: "hijri"`; the Gregorian
  date is the `normalized_date`.

### A.3 Budget, resilience, review

- 24 declared queries, run exactly as written, each once. No follow-up search outside the declared
  set; a lead found in a result is pursued by direct fetch only.
- Enumerate first (BH2 listing, BH1 press-release pages), then search. Write the candidate file and
  the lane log after each lane, so the pass can be resumed.
- If the shared search limit stops the pass, record exactly which declared queries did not run. A
  lane run in one language is `partial`. A refused source was not searched.
- The lane log states, per lane, that the result is a count of records found. BH2 states its
  `source_window` as `rolling_archive_gap` for 2022-2023; BH3 is a query set and is never a census.
- Every candidate is read end to end by a safety reviewer before import; blind three-role review as
  in `SA_LANE_PASS_18.md`.

## Part B — execution (written after the pass, 2026-11-11)

**This pass did not finish.** 0 of 3 lanes ran as far as declared; 3 were stopped by the shared limit of 200 web searches per turn, which was not worked around. Each lane states below what did not run. A blocked source (HTTP 402 or 403, login wall, script-only page) was recorded as blocked and left.

| Lane | Execution | Source window | Covered through | Queries | Items read | Languages required | Languages run |
|---|---|---|---|---|---|---|---|
| BH1 | partial; stopped by search limit | inaccessible | not reached | 0 of 5 | 8 | ar, en | en |
| BH2 | partial; stopped by search limit | rolling_archive_gap | 2026-11-11 | 0 of 4 | 148 of 148 | ar, en | ar, en |
| BH3 | partial; stopped by search limit | no_census_exists | not reached | 9 of 15 | - | ar, en | ar |

Candidates 9: accepted after blind review 0, rejected 3, duplicate 0, held 3, out of scope 3. Published records in this system after the pass: 0.

**Result.** One attack record was reviewed and is with the owner: the opened sources report a force-majeure declaration and disrupted operations but no shutdown or throughput cut, which is what clause 1 asks for, and they do not clearly tie the dated fire to the facility. Bahrain therefore has no published record. The electricity authority's site forbids linking and was never cited. The safety reviewer noted that where a country has one facility of a class, the class and the country name it whatever the text says.

**Review.** Every published record was reviewed blind by three independent roles (evidence, safety, taxonomy), reconciled, and confirmed by all three on the text the import gate publishes. A hold from any role held the record.

### Limitations, per lane

- **BH1**: Only the first page of the refining company's English press-release listing could be read: 8 items dated 2024-06-02 to 2025-07-31; the total number of items is not shown and later pages are script-driven. The group's media centre (English and Arabic) and the state news agency refused automated access, so no Arabic listing was read and nothing from 2022-2023 or from 2026 was enumerated. The lane's five declared queries were not run: the task assigned the whole search allowance to BH3. This is a count of items read, not a census.
- **BH2**: Both listings were read in full by title and date (Arabic 79 of 79, English 69 of 69); no title concerned a supply interruption, so no item was opened. The listings begin in February 2024, so 2022 and 2023 cannot be enumerated here and rest on the lane's four declared queries, which were not run: the task assigned the whole search allowance to BH3.
- **BH3**: A query set, never a census: 9 of 15 declared queries ran, all Arabic, so the lane was searched in one of its two required languages and the 2026 outage query did not run. Fifteen result pages were requested and thirteen read. Domestic Arabic papers were not reached (two are refused, the readable one has no search); every page read is foreign or English-language press carrying an official Bahraini statement. This is a count of records found.
