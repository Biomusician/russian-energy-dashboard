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

*(Filled in after the lanes run. Counts only.)*
