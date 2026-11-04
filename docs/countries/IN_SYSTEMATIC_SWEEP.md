# India — first systematic research pass (iteration 17)

**Part A, the search plan, was written on 2026-11-03 before any search of this pass was run.**
India has had targeted searches only. Its reporting environment is `mixed_regulatory`: the grid
operator and the CEA publish grid-disturbance reports under the Grid Standards, which is the
nearest thing to a census. **This pass is not expected to complete.**

| | |
|---|---|
| Window | 2022-01-01 to 2026-11-03 |
| Geography | the 28 states and 8 union territories (2023 ISO revision); disputed areas per `system.json` rulings |
| Rule | `inclusion_threshold.json` version `2026-10-30.1`, unchanged |
| Languages | English, plus Hindi for the national-media lane |

## Part A — plan (written before searching)

### A.1 Lanes

| Lane | Universe | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|
| IN1 | Grid-India (formerly POSOCO) and CEA grid-disturbance and grid-incident reports in the window | grid-india.in reports; cea.nic.in grid-disturbance reports | none; enumeration only | 4, 5 |
| IN2 | Ministry of Power releases on major outages and supply emergencies | pib.gov.in (Ministry of Power) | for each year Y: `site:pib.gov.in power outage grid disturbance Y` | 4, 5 |
| IN3 | PPAC and the Ministry of Petroleum and Natural Gas: refinery and pipeline disruption statements | ppac.gov.in; mopng.gov.in; pib.gov.in (MoPNG) | for each year Y: `refinery shutdown India fire Y`; `pipeline leak India supply disrupted Y` | 1, 3 |
| IN4 | Ministry of Coal and Coal India: mine accidents and production suspensions | coal.gov.in; coalindia.in | for each year Y: `Coal India mine accident production suspended Y` | 6 |
| IN5 | PNGRB: gas pipeline incidents and supply interruptions | pngrb.gov.in | `PNGRB pipeline incident` | 3 |
| IN6 | State operators and authorities: SLDC and state discom notices of load shedding or major outages | state SLDC and discom sites, via search | for each year Y: `load shedding state power cut hours Y India`; `बिजली कटौती ग्रिड फेल Y` | 5 |
| IN7 | Credible national media: PTI, The Hindu, Indian Express, Times of India, Mint | via search | for each year Y: `India power plant outage MW Y`; `India refinery fire unit shut Y` | 1, 4 |

### A.2 Safety, review and budget

Admin-1 precision only; no vulnerability or dependency language. Split agents, fixed search
caps, progress written after each lane, blind three-role review before import.

## Part B — execution record

Run on 2026-11-03 against the plan as committed in `a7f3a36`. The research log (`data/curated/systems/in/research_log.json`) is the record; this section restates it as counts.

**0 of 7 lanes complete** for the window 2022-01-01 to 2026-11-03. A lane is complete only if its declared universe was searched to the end of the window; none was.

### B.1 Dispositions

candidates 22 · accepted 1 · rejected 4 · duplicate 1 · held 11 · out of scope 3

3 lane-accepted candidates went to blind review: 1 published, 2 held (the IOCL leak turns on whether isolating a pipeline section meets clause 3, an owner question; the GAIL record is held by the safety role because a citation's address names a site finer than admin-1, the owner question on citation URLs). Both stay in the local queue.

### B.2 Lane by lane

| Lane | Status | Covered through | Why not complete |
|---|---|---|---|
| IN1 | partial | not started | Census endpoint unreachable: every Grid-India / POSOCO / RLDC host tried refused the connection from this environment (as in the iteration-16 source audit), and CEA does not publish a grid-disturbance report listing (Grid Management and NPC division pages carry only an SOP and one 2020 extract). No year of the window was enumerated. |
| IN2 | partial | 2026-11-03 | All five plan queries ran, but the search engine ignored the site:pib.gov.in operator and returned no pib.gov.in page for any year, so the lane's universe (PIB Ministry of Power releases) was not actually enumerated. Results were secondary coverage, RPC agendas and foreign grids. |
| IN3 | partial | 2026-11-03 | All ten plan queries ran, but the lane's declared universe is PPAC / MoPNG / PIB-MoPNG statements and none of those endpoints was enumerated; the queries returned media coverage only, weighted to a few repeated stories. No follow-up searches were possible within the cap. |
| IN4 | partial | 2026-11-03 | All five plan queries ran, but coal.gov.in and coalindia.in were not enumerated (Coal India's site was unreachable in the iteration-16 audit) and results were dominated by pre-window incidents (Talcher 2019, Lalmatia 2016) for every year. Finding nothing in 2022-2025 is not evidence of no events. |
| IN5 | partial | not started | Not run. |
| IN6 | partial | not started | Not run. |
| IN7 | partial | 2026-11-03 | All ten plan queries ran, but results were not restricted to the five named outlets, were dominated by repeated undated stories, and the 30-search cap left no budget to follow up 403 or snippet-only items. The refinery queries surfaced no new in-window refinery event beyond those logged in IN3. |

### B.3 What the next pass must do

Run the lanes marked not started first, then the partial lanes from their `covered_through` date. Refusals (HTTP 402/403, login walls, script-rendered listings) are not worked around; a lane that depends on one stays partial and says so.

