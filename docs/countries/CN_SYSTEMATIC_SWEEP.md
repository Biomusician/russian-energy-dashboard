# China — first systematic research pass (iteration 17)

**Part A, the search plan, was written on 2026-11-03 before any search of this pass was run.**
China has had targeted searches only. Its reporting environment is `media_only`: no regulator
publishes an outage or incident register, so the lanes below are the closest public equivalents.
**This pass is not expected to complete.** The plan exists so that the next pass can, and so that
whatever this pass does is a declared process rather than a sample.

| | |
|---|---|
| Window | 2022-01-01 to 2026-11-03 |
| Geography | the 31 mainland provincial-level units; Hong Kong and Macau as their own units; Taiwan is not part of the system |
| Rule | `inclusion_threshold.json` version `2026-10-30.1`, unchanged |
| Languages | Chinese (simplified) and English, both mandatory: a lane run in one language only is partial |

## Part A — plan (written before searching)

### A.1 Lanes

| Lane | Universe | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|
| CN1 | National statistics: NBS monthly industrial output releases for electricity, crude processing, coal and gas, read for national or provincial production effects explicitly attributed to a disruption | stats.gov.cn monthly releases | none; enumeration only | 7 |
| CN2 | National Energy Administration and grid companies (State Grid, China Southern Grid): public notices of major outages, orderly power use (有序用电) and emergency responses | nea.gov.cn; sgcc.com.cn; csg.cn news | for each year Y: `有序用电 限电 Y年`; `大面积停电 Y年`; `电网 应急响应 停电 Y` | 4, 5 |
| CN3 | Provincial outage and disruption reporting: provincial energy bureaus and government notices of power rationing or grid emergencies | provincial government sites, via search | for each year Y: `省 拉闸限电 Y年`; `省 电力供应 紧张 停电 Y年` | 5 |
| CN4 | Major state enterprises: Sinopec, PetroChina, CNOOC, China Shenhua, State Power Investment exchange announcements of facility incidents or production suspensions | HKEX and SSE announcement search | for each company C: `C 停产 公告`; `C 事故 装置 停车` | 1, 6, 7 |
| CN5 | Credible Chinese-language media: Xinhua, People's Daily, Caixin, The Paper (澎湃) | via search | for each year Y: `炼油厂 火灾 停产 Y年`; `煤矿 事故 停产 Y年`; `天然气 管道 爆炸 Y年` | 1, 3, 6 |
| CN6 | International corroboration: Reuters, Bloomberg, S&P Global reporting of Chinese energy disruptions | via search | for each year Y: `China power rationing Y`; `China refinery fire shut Y`; `China coal mine accident output Y` | 1-7 |

### A.2 Safety

Admin-1 precision only. No plant-level vulnerability, no grid topology, no dependency language.
The reporting environment is a stated caveat on every count.

### A.3 Review and budget

Split agents, fixed search caps, progress written after each lane. Blind three-role review before
import (REVIEW_GOVERNANCE.md).

## Part B — execution record

Run on 2026-11-03 against the plan as committed in `a7f3a36`. The research log (`data/curated/systems/cn/research_log.json`) is the record; this section restates it as counts.

**0 of 6 lanes complete** for the window 2022-01-01 to 2026-11-03. A lane is complete only if its declared universe was searched to the end of the window; none was.

### B.1 Dispositions

candidates 13 · accepted 0 · rejected 2 · duplicate 2 · held 9 · out of scope 0

No candidate was accepted by a lane, so nothing went to review; the 9 held candidates stay in the local queue with their reasons.

### B.2 Lane by lane

| Lane | Status | Covered through | Why not complete |
|---|---|---|---|
| CN1 | partial | 2026-10-19 | Enumeration only, by fetch. Two of roughly 57 monthly releases in the window were read (June and September 2026). Neither attributes any change to a cause: the June 2026 release reports raw coal down 9.7% y/y (the Liushenyu aftermath, already in the corpus) and crude processing down 17.7% y/y, both without a stated cause. The release format states figures only, so this lane is unlikely to yield ca |
| CN2 | partial | 2026-11-03 | All 15 plan queries run, but the endpoints nea.gov.cn, sgcc.com.cn and csg.cn news were not enumerated directly, and the US-indexed search tool returned mostly provincial and municipal orderly-power-use PLANS and foreign blackouts rather than Chinese event reporting. |
| CN3 | partial | 2026-11-03 | All 10 plan queries run, but results came almost entirely from English-language wire and analyst coverage; no provincial government or energy-bureau notice was found and opened for any year, so the lane's declared universe (provincial official notices) was not reached. |
| CN4 | partial | 2022-01-01 | Not started: the search cap was reached first. HKEX and SSE announcement search was not enumerated directly either (those are interactive search forms, not static listings). |
| CN5 | partial | 2026-11-03 | Only the refinery-fire query family was run (5 of 15 queries); the coal-mine and gas-pipeline families were not run because the personal 30-search cap was reached. The refinery query itself returned almost entirely foreign refineries and no Xinhua, People's Daily, Caixin or The Paper page. |
| CN6 | partial | 2022-01-01 | Not started: the personal 30-search cap was spent on CN2, CN3 and part of CN5 in the plan's lane order. Some Reuters/Bloomberg syndications were opened incidentally in CN3 and are recorded there. |

### B.3 What the next pass must do

Run the lanes marked not started first, then the partial lanes from their `covered_through` date. Refusals (HTTP 402/403, login walls, script-rendered listings) are not worked around; a lane that depends on one stays partial and says so.

