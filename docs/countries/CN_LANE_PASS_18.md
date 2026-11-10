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
