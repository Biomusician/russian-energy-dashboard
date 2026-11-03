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

*(Filled in after the lanes run. Counts only.)*
