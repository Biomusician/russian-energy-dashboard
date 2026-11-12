# Qatar — first systematic research pass (iteration 19)

**Part A, the search plan, was written on 2026-11-11 before any incident search for Qatar was run.**
The source audit that precedes it ([QA_SOURCE_AUDIT.md](QA_SOURCE_AUDIT.md)) tested how each source
is reached and read national statistics only; it researched no incident. Inclusion rule version
`2026-10-30.1` (`data/curated/systems/inclusion_threshold.json`), unchanged. Window 2022-01-01 to
2026-11-11.

**Safety first.** A campaign is recorded for Qatar (`conflict_campaigns.json`,
`qa-2026-attacks-on-energy-facilities`, status `uncertain`, treated as active, from 2026-01-01). For
any kinetic or sabotage event this pass collects only that it occurred, its date and date
precision, the broad infrastructure class, and the effect reported at the time (within 7 days).
Such records are placed at **country level**: Qatar is small, and a municipality would name the
facility. The pass does **not** collect restart, repair progress, current operating rate, remaining
capacity, current outage or current facility condition, even where public, in any field, and does
not cite a page whose address or title states later status. It never collects train-by-train LNG
capacity, any measure of another party's dependence on particular trains or on shipping routes,
tanker or route material, coordinates, weapon or defence detail, pipeline routes or grid topology.
Routine and planned maintenance is not an event. A change in an annual or monthly total with no
stated cause is context, never an event.

| | |
|---|---|
| Window | 2022-01-01 to 2026-11-11 |
| Geography | country level for kinetic and security events; one of the 7 municipalities drawn by Natural Earth for a non-conflict event only where a safety reviewer finds it non-identifying |
| Rule | `inclusion_threshold.json` version `2026-10-30.1`, unchanged |
| Languages | Arabic and English, both mandatory for every lane |
| Declared queries | 30 in total (QA1 4, QA2 6, QA3 20) |

## Part A — plan (written before searching)

### A.1 Lanes

| Lane | Universe kind | Languages | Universe | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|---|---|
| QA1 | report archive | ar+en | QatarEnergy and QatarEnergy LNG (formerly Qatargas): historical operational disruptions stated by the operator. The LNG company's news archive, enumerated in full for 2022-2026; QatarEnergy's own releases as carried by QNA; the two companies' annual sustainability reports 2022-2025 for incident statements, if a reader can open them. Routine maintenance is not an event | `https://www.qatarenergylng.qa/Media/News` (static; 26 pages of 10 at `/Media/News/pageindex563/N`; year categories 2015-2026): enumerate titles, open only those that state a disruption. `https://www.qatarenergylng.qa/Sustainability/Annual-Sustainability-Reports` (listing static; PDFs over the fetch limit or HTTP 403: a documented limitation). `qatarenergy.qa` news listing and item pages are script-only: SOURCE_BLOCKED, not worked around; direct report PDFs under `/en/MediaCenter/Publications/` are 31-91 MB. Annual national totals at `data.gov.qa` (`production-qe-dataset`, `export-qe-dataset`) are context only | `قطر للطاقة بيان توقف الإنتاج حادث`; `QatarEnergy statement production halted incident`; `قطر للطاقة تعلن حالة القوة القاهرة`; `QatarEnergy declares force majeure` | 1, 2, 3, 7 |
| QA2 | declared query set | ar+en | Electricity and water: KAHRAMAA major emergency or outage reporting, as statements carried by QNA and the press. No grid topology, no substation or zone detail. A water-only interruption is outside the rule; a water statement is read only where it reports a power-and-water plant forced offline | no census exists: `https://km.qa/MediaCenter/Pages/News.aspx` renders "No News Found" (the `www` host fails TLS). QNA article pages are static and dated, `https://www.qna.org.qa/ar-QA/News-Area/News/YYYY-MM/DD/slug` and `/en/News-Area/News/YYYY-MM/DD/slug`; QNA listings and search are script-only. KAHRAMAA Annual Statistics Reports (`https://km.qa/MediaCenter/Publications/SR2023-English.pdf` verified) and `data.gov.qa` KAHRAMAA datasets carry no outage table: context only | `كهرماء بيان انقطاع التيار الكهربائي`; `KAHRAMAA statement power outage`; `كهرماء انقطاع الكهرباء عن مناطق واسعة`; `Qatar blackout KAHRAMAA widespread power cut`; `كهرماء بيان انقطاع المياه محطة تحلية`; `KAHRAMAA statement water supply interruption desalination plant` | 4, 5 |
| QA3 | declared query set | ar+en | Arabic and English media by year 2022-2026: Al-Raya, Al-Sharq, Al-Watan, The Peninsula, Gulf Times, QNA, and international reporting (Reuters, S&P Global, Al Jazeera) as it appears in search results. Includes event-occurrence queries for any attack reported on a Qatari energy facility: occurrence, date, class and effect at the time only | via search. Supplementary enumeration, English: `https://thepeninsulaqatar.com/category/Energy?page=N` (65 pages of 18; dated addresses `/article/DD/MM/YYYY/slug`, day first): read titles only for 2022-2026 and open those that state a disruption in Qatar. Arabic: `https://al-sharq.com/category/اقتصاد/N` and `/category/محليات/N` are paged but run to more than 10,000 pages, so they are not a census and are used only to open items a query finds. Reuters (host refused by the fetch tool) and S&P Global (HTTP 403) are SOURCE_BLOCKED: search results only, `opened: false` | for each year Y in 2022-2026: `قطر حريق منشأة نفطية أو غازية Y`; `Qatar gas plant OR refinery fire shutdown Y`; `استهداف منشآت الطاقة في قطر Y`; `Qatar energy facility attack reported Y` | 1-7 |

Query count: QA1 4 (2 ar, 2 en); QA2 6 (3 ar, 3 en); QA3 4 per year for five years, 20 (10 ar,
10 en). **Total 30.** No follow-up query is declared. A query that is refused or not reached is
listed in the lane log as not run.

### A.2 Safety

- Kinetic and sabotage candidates dated from 2026-01-01: `geography_precision: "country"`,
  `admin1_code: null`, `date_end: null`, `recovery.research_status: "NOT_YET_RESEARCHED"` exactly as
  the brief's schema shows, and `facility_name` only if the facility's own name is what the source
  reports as hit. Earlier kinetic or security candidates, if any are found, are also placed at
  country level.
- Citations published more than 7 days after a covered event, and addresses or titles that announce
  status, stay in the local queue and are not opened.
- The two attack-occurrence queries per year in QA3 will return pages that also carry later status,
  export-route and shipping material for 2026. The researcher reads the dated occurrence and the
  effect stated at the time, and nothing else on the page.
- A non-conflict candidate is given a municipality only on a safety reviewer's finding that the
  municipality does not identify the facility. Otherwise it is country level. Al-Shahaniya is
  recorded under QA-RA with the note in the audit's ruling 1.
- Every candidate, including rejects, is read end to end by a safety reviewer before import.

### A.3 Evidence and independence

- Al-Raya and Gulf Times share a publisher; Al-Sharq and The Peninsula share a group; QNA's Arabic
  and English items are one text. Each pair is one source. A newspaper item that reproduces QNA is
  a syndicated copy.
- QNA datelines omit the year: take it from the address. Al-Sharq and The Peninsula write the day
  first in the address; Al-Raya writes the year first. Gulf Times and Al-Watan addresses carry no
  date: read it from the page.
- Keep the Arabic title in Arabic, with `language: "ar"` and an English gloss in `title_en`. A Hijri
  date in a source is kept in `source_date_text` with `date_calendar: "hijri"`.

### A.4 Budget, resilience, review

Fixed search cap as assigned to the Wave B researcher; enumeration by direct fetch first, search
second. The lane log is written after each lane. Blind three-role review before import, as in
`SA_LANE_PASS_18.md` A.3.

## Part B — execution (written after the pass, 2026-11-11)

**This pass did not finish.** 0 of 3 lanes ran as far as declared; 3 were stopped by the shared limit of 200 web searches per turn, which was not worked around. Each lane states below what did not run. A blocked source (HTTP 402 or 403, login wall, script-only page) was recorded as blocked and left.

| Lane | Execution | Source window | Covered through | Queries | Items read | Languages required | Languages run |
|---|---|---|---|---|---|---|---|
| QA1 | partial; stopped by search limit | current_through_end_date | 2026-11-11 | 2 of 4 | 45 of 45 | ar, en | ar, en |
| QA2 | partial; stopped by search limit | no_census_exists | 2026-11-11 | 3 of 6 | 107 of 107 | ar, en | ar, en |
| QA3 | partial; stopped by search limit | no_census_exists | 2026-11-10 | 7 of 20 | 192 | ar, en | ar |

Candidates 12: accepted after blind review 1, rejected 4, duplicate 1, held 6, out of scope 0. Published records in this system after the pass: 1.

**Result.** One attack record is published at country level. A second is with the owner: its only capacity statement is a share of national export capacity, which the safety rule keeps out of every field, and without it the record states damage only. The utility's site forbids linking and was never cited. The safety reviewer noted that this class in this country is one site.

**Review.** Every published record was reviewed blind by three independent roles (evidence, safety, taxonomy), reconciled, and confirmed by all three on the text the import gate publishes. A hold from any role held the record.

### Limitations, per lane

- **QA1**: The two force-majeure queries did not run (search cap). The operator's own newsroom is script-only, so its statements were seen only as press copies and search-result summaries. a facility's own sustainability reports (31-91 MB) and the LNG company's 2024 and 2025 reports were not read.
- **QA2**: Three of six declared queries did not run (search cap), including both water-and-power queries, so no power-and-water plant outage was searched for at all. A query set is not a census of outages. The news agency could not be enumerated and none of its Qatar items surfaced in the results.
- **QA3**: Seven of twenty declared strings were run, all Arabic; no English string and no 2026-tagged string was run, so the lane is partial in both language and year. The search engine ignored the year in every string and returned 2026 material each time, so the 2022-2025 strings say little about 2022-2025: finding nothing for those years is the result of seven queries and one newspaper category, not evidence that nothing happened. Every article was read through a summarising fetch tool, not as raw text.
