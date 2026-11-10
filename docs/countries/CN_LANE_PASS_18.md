# China — research pass (iteration 18)

**Part A, the search plan, was written on 2026-11-10 before any search of this pass was run.**
Lanes and order are those of `CN_SYSTEMATIC_SWEEP.md`. Inclusion rule version `2026-10-30.1`,
unchanged. Window 2022-01-01 to 2026-11-10. Coverage vocabulary as in `US_LANE_PASS_18.md`.

| | |
|---|---|
| Geography | the 31 mainland provincial-level units; Hong Kong and Macau as their own units; Taiwan is not part of the system |
| Languages | Simplified Chinese and English, both mandatory where marked: a lane marked zh+en run in one language cannot be `declared_search_complete` |

## Part A — plan (written before searching)

### A.1 Lanes

| Lane | Universe kind | Languages | Universe | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|---|---|
| CN1 | report archive | zh | Every NBS monthly energy production release (能源生产情况), 2022-01 to latest; read only for production changes explicitly attributed to a disruption | stats.gov.cn release listing, each release opened | none; enumeration only | 7 |
| CN2 | report archive | zh+en | NEA, State Grid and China Southern Grid public notices on major outages, orderly power use (有序用电) and emergency responses. Planned demand management is logged apart from actual disruption | nea.gov.cn; sgcc.com.cn; csg.cn listings by ordinary access | for each year Y in 2022-2026: `有序用电 限电 Y年`; `大面积停电 Y年`; `电网 应急响应 停电 Y` (15, carried from iteration 17) plus `site:nea.gov.cn 停电 应急`; `site:sgcc.com.cn 停电 抢修 恢复供电`; `site:csg.cn 停电 恢复供电` | 4, 5 |
| CN3 | declared query set | zh | Provincial official reporting, split by province for source volume only: Guangdong, Shandong, Inner Mongolia, Shanxi, Xinjiang, Sichuan, Jiangsu, Zhejiang, Henan | provincial government and energy-bureau domains | for each province P: `P 有序用电 限电 通知 政府`; `P 大面积停电 应急响应 政府` | 5 |
| CN4 | report archive | zh+en | Sinopec, PetroChina/CNOOC, CNOOC, China Shenhua, State Power Investment: exchange and investor-relations notices of production suspension, refinery interruption or mine suspension | HKEX and SSE where reachable; company notice pages | for each company C: `C 停产 公告`; `C 事故 装置 停车`; `C production suspension announcement` | 1, 6, 7 |
| CN5 | declared query set | zh | Xinhua, People's Daily, Caixin, The Paper; lane credit only for those four outlets | via search | for each year Y in 2022-2026: `炼油厂 火灾 停产 Y年 新华社 财新 澎湃`; `煤矿 事故 停产 Y年 新华社 财新 澎湃`; `天然气 管道 爆炸 Y年 新华社 财新 澎湃` | 1, 3, 6 |
| CN6 | declared query set | en | International corroboration: Reuters, Bloomberg, AP, S&P Global, major industry press. Each candidate then gets a Chinese-language search | via search | for each year Y in 2022-2026: `China power rationing Y`; `China refinery fire shut Y`; `China coal mine accident output Y` | 1-7 |

### A.2 Threshold and safety

Mine accidents with no material supply effect, local distribution outages, planned rationing and
safety shutdowns without reported production impact do not qualify. Admin-1 precision only. No
plant-level vulnerability, dependency or grid-topology content. Province order is research order,
never a ranking of infrastructure.

### A.3 Recovery

Each accepted record gets a follow-up pass: service restoration, production resumption, official
close-out, operator restart. Observed only.

### A.4 Budget, resilience, review

As `US_LANE_PASS_18.md` A.3.

## Part B — execution (written after the pass, 2026-11-10)

**This pass did not finish.** A shared limit of 200 web searches per turn was reached about two-thirds of the way through. Direct page requests still worked. The limit was not worked around, and every lane it stopped says so. A new turn is needed to run the remaining queries: `scripts/research_tools.py next cn`.

| Lane | Execution | Source window | Covered through | Queries | Languages run |
|---|---|---|---|---|---|
| CN1 | enumerated_complete | publisher_not_yet_released | 2026-09-30 | 0 of 0 | zh |
| CN2 | partial; stopped by search limit | inaccessible | not reached | 3 of 18 | zh |
| CN3 | declared_search_complete | no_census_exists | 2026-11-10 | 18 of 18 | zh |
| CN4 | partial | inaccessible | not reached | 15 of 15 | en, zh |
| CN5 | declared_search_complete | no_census_exists | 2026-11-10 | 15 of 15 | zh |
| CN6 | declared_search_complete | no_census_exists | 2026-11-10 | 15 of 15 | en, zh |

Candidates 47: accepted after blind review 1, rejected 14, duplicate 12, held 16, out of scope 4.

**Chinese-language work.** CN3, CN5 and the NBS enumeration ran in Chinese. CN1 read 53 of 53 monthly NBS releases, through a summarising reader, and found no release that attributes a change to a disruption. The Excel tables were not opened. CN2's National Energy Administration listing was read; its accident bulletins stop in 2021.

**Corpus audit.** Two Yunnan aluminium records held: clause 4 requires rotating outages and the sources report industrial curtailment. Their episode dissolved.

**Enterprise lane.** Fifteen queries ran. Notice archives (HKEX, SSE and most company pages) were not reachable, so this is not an enumeration.

### Limitations, per lane

- **CN1**: Nothing in the universe is unread, but each page was read through WebFetch, which returns a model's reading of the page rather than the raw text; the model declined to reproduce full bodies, so the per-release result rests on its answer to a fixed question asking for every causal phrase verbatim. The attached Excel data tables were not opened. The October 2026 release is not yet published.
- **CN2**: State Grid's site did not respond and NEA's general news listing is script-only, so both are unread; China Southern Grid's company-news archive is reachable (20 items a page, paged as index_N.html, by year) but only 3 pages (60 titles) were sampled, and none of the 15 year queries ran before the shared search limit was hit. No English query is declared in the plan and none was run, so the zh+en requirement is not met.
- **CN3**: A declared query set, not a census: each query returned about 10 results and only 5 result pages were opened; provincial energy-bureau notice listings were not enumerated. The 'P 大面积停电 应急响应 政府' query returns emergency plans (预案) for almost every province, often from other provinces, and is a poor instrument for finding events.
- **CN4**: The notice archives themselves were not enumerated: HKEX and SSE listings are interactive or script-only, and of the five company notice pages only PetroChina's was reachable, showing its 20 most recent titles (2026-04-29 to 2026-11-05, all routine governance, none about a suspension) with no visible pagination. Annual-report PDFs were not opened. All 15 declared queries ran in both languages, but they are a keyword probe of an archive lane, not a reading of it.
- **CN5**: A 15-string query set through a general search engine is not a search of the four outlets' archives: Caixin returned no result in any of the 18 searches and People's Daily only a handful, so lane credit rests almost entirely on The Paper and Xinhua.
- **CN6**: All 15 declared English queries ran and were dispositioned, but this is a query set, not a census, and the wire syndication sites carrying most Reuters and Bloomberg coal stories (mining.com, miningweekly, engineeringnews) refused access, so those articles were judged from headlines. Seen in result lists and not pursued: 2024 Shanxi safety-inspection output curbs (a regulatory campaign, not a discrete event), two mine accidents of 23 Oct 2024 in Hebei and Shanxi, and a reported 2024 output fall in one Heilongjiang city.
