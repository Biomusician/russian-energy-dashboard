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

## Part B — execution (written after the pass, 2026-11-10)

**This pass did not finish.** A shared limit of 200 web searches per turn was reached about two-thirds of the way through. Direct page requests still worked. The limit was not worked around, and every lane it stopped says so. A new turn is needed to run the remaining queries: `scripts/research_tools.py next in`.

| Lane | Execution | Source window | Covered through | Queries | Languages run |
|---|---|---|---|---|---|
| IN1 | partial | inaccessible | not reached | 6 of 6 | en |
| IN2 | not_started; stopped by search limit | inaccessible | not reached | 0 of 5 | none |
| IN3 | partial; stopped by search limit | inaccessible | 2026-07-31 | 0 of 10 | en |
| IN4 | partial; stopped by search limit | rolling_archive_gap | not reached | 0 of 5 | en |
| IN5 | partial | current_through_end_date | 2026-11-09 | 3 of 3 | en |
| IN6 | partial; stopped by search limit | no_census_exists | not reached | 16 of 34 | en, hi |
| IN7 | not_started | inaccessible | not reached | 0 of 10 | none |

Candidates 52: accepted after blind review 2, rejected 18, duplicate 8, held 24, out of scope 0.

**Grid-India alternatives (brief §44).** Three passes, the same result: all six Grid-India and regional dispatch hosts refused the connection. No alternative can serve as a census. CEA publishes no event listing, and its 2025-26 annual report carries no grid-disturbance count. The five Regional Power Committees publish downstream discussion papers, but were unreachable or refused. Their papers would be a discovery aid at most, and they count MW of load loss while clause 5 is stated in customers. No proxy is recommended, and no MW-to-customer equivalent was invented.

**Fuel-supply cause (brief §47): not added.** After reading, only one record per country is actually attributed to fuel shortage, both from 2022, so it does not yet recur as a category. What a cause definition would have to settle is listed in `docs/ITERATION_18_REVIEW.md` §15. Those records stay held.

**Official enumeration.** 54 MoPNG monthly production reports read: the only source reached that attributes refinery changes to causes, at month level, and it stops doing so after June 2024. PNGRB listings read at title level: no incident stream exists.

**Corpus audit.** One record held (a refinery fire during commissioning, where no opened source states processing halted). Summaries corrected where a source's clause was misread.

### Limitations, per lane

- **IN1**: The Grid-India/RLDC universe is unread for the whole window 2022-01-01 to 2026-11-10: all six hosts refused the connection for the third pass running. No RPC, parliamentary or ministry document was opened either (refused, HTTP 403 or script-only), so no event-level alternative was read.
- **IN2**: Nothing in this lane was read. Every PIB endpoint tried (listing, RSS, a release page) and the Ministry of Power site returned HTTP 403 to ordinary fetches, and the five declared queries were refused by the shared search budget. The whole universe, 2022-01-01 to 2026-11-10, remains unsearched.
- **IN3**: Unread: PIB-MoPNG releases (403); the MoPNG Monthly Cabinet Summaries (44 listed, February 2021 to September 2024, image-only scans; 1 fetched, none read); PPAC's report archive (300+ entries listed, 1 monthly report read); MoPNG What's New pages 2-6 of 6. Monthly Production Reports for October 2022 and July 2024 are missing from the ministry's listing. None of the ten declared queries ran: the search limit was reached.
- **IN4**: Unread: Ministry of Coal releases before 13 November 2025; 31 of 35 in-window Monthly Summaries (none is published after February 2025, and October to December 2023 are missing from the listing); Coal India annual reports and subsidiary reports (script-only listing); the ministry's Accident Portal page; PIB. The DGMS, which holds mine-accident records, is outside this lane's named sources. None of the five declared queries ran: the search limit was reached.
- **IN5**: Listings were read at TITLE level only (480 notices, 75 press releases, 54 case studies, 21 incident analyses, 9 reports); just 4 PNGRB PDFs were opened, so an incident mentioned only inside a document body is unseen. Not read: PNGRB annual reports (not found on the site), the orders/complaints-disputes listing (146 feed items), the monthly data-bank NGPL MIS reports, the 2026 Statistical Booklet, 38 of 40 anonymised case studies, and the Oct 2026 High-Level Expert Committee report on pipeline supply security (deliberately not opened: its subject is network resilience, which the scope boundary forbids collecting).
- **IN6**: Only 16 of 34 declared queries ran (all 10 year queries in English and Hindi, and the Uttar Pradesh, Maharashtra and Tamil Nadu pairs) before the session's shared search limit stopped the pass; the Karnataka, Delhi, Bihar, Jharkhand, Punjab, Haryana, Rajasthan, West Bengal and Assam pairs and both follow-ups did not run. No SLDC or discom notice was opened: Maharashtra SLDC report addresses returned 404, its report lists are script-only, its 2025 disturbance compendium exceeds the fetch size limit, and the Delhi SLDC site refused the connection, so every opened source is press.
- **IN7**: None of the five credited outlets was searched or read: the search tool refuses all five domains to its user agent, and that refusal was not worked around. The lane universe is therefore entirely unread for 2022-01-01 to 2026-11-10; the unrestricted discovery run earns no lane credit and left one declared string (refinery 2026) unrun.
