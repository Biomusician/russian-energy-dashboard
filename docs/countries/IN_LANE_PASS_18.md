# India — research pass (iteration 18)

**Part A, the search plan, was written on 2026-11-10 before any search of this pass was run.**
Lanes and order are those of `IN_SYSTEMATIC_SWEEP.md`. Inclusion rule version `2026-10-30.1`,
unchanged. Window 2022-01-01 to 2026-11-10. Coverage vocabulary as in `US_LANE_PASS_18.md`.
Languages: English; Hindi where marked (en+hi).

## Part A — plan (written before searching)

### A.1 Lanes

| Lane | Universe kind | Languages | Universe | Endpoint / enumeration | Queries (run exactly) | Clauses |
|---|---|---|---|---|---|---|
| IN1 | census | en | Grid-India and CEA grid-disturbance reports. Grid-India/RLDC hosts refused in iterations 16 and 17. This pass re-tests ordinary access, then produces an evidence comparison of CEA documents, RPC meeting minutes, government mirrors, annual disturbance reports and parliamentary or ministry reports on coverage, granularity, date consistency, completeness and machine accessibility. RPC minutes are NOT accepted as a census by this plan | grid-india.in; cea.nic.in; nrpc, wrpc, srpc, erpc, nerpc sites; sansad.in | `grid disturbance report CEA India annual`; `RPC protection sub-committee grid disturbance minutes Y` for each year Y | 4, 5 |
| IN2 | report archive | en | PIB Ministry of Power releases on major outages and supply emergencies | pib.gov.in listing by ordinary access; search results never credited as enumeration | for each year Y: `site:pib.gov.in power outage grid disturbance Y` (carried) | 4, 5 |
| IN3 | report archive | en | PPAC, MoPNG and PIB-MoPNG refinery and pipeline disruption statements | ppac.gov.in; mopng.gov.in; pib.gov.in | carried from iteration 17 (10 run) | 1, 3 |
| IN4 | report archive | en | Ministry of Coal and Coal India mine accidents and production suspensions | coal.gov.in; coalindia.in; pib.gov.in | carried from iteration 17 (5 run) | 6 |
| IN5 | report archive | en | PNGRB public material on pipeline incidents, service interruption and emergency notices | pngrb.gov.in; annual reports and public notices | `PNGRB pipeline incident`; `PNGRB emergency notice gas supply interruption`; `PNGRB annual report incident` | 3 |
| IN6 | declared query set | en+hi | SLDC, discom and state energy department notices of major qualifying load-shed or outage, by operator family: Uttar Pradesh, Maharashtra, Tamil Nadu, Karnataka, Delhi, Bihar, Jharkhand, Punjab, Haryana, Rajasthan, West Bengal, Assam | state SLDC and discom sites | for each year Y in 2022-2026: `load shedding state power cut hours Y India`; `बिजली कटौती ग्रिड फेल Y`; for each family F: `F SLDC load shedding major outage`; `F बिजली कटौती ग्रिड फेल` | 5 |
| IN7 | declared query set | en | PTI, The Hindu, Indian Express, Times of India, Mint. Lane credit only for those five outlets; other media aid discovery and are logged separately | via search | for each year Y: `India power plant outage MW Y`; `India refinery fire unit shut Y` | 1, 4 |

### A.2 Cause taxonomy

Several held records raise a fuel-supply shortfall. This pass does not add the cause. It documents
whether the category recurs across India and China and writes a proposal; affected records stay
held until the owner rules.

### A.3 Recovery

Each accepted record: load restoration, plant restart, refinery return, pipeline service
resumption. Observed or sourced estimate only.

### A.4 Budget, resilience, review

As `US_LANE_PASS_18.md` A.3.
