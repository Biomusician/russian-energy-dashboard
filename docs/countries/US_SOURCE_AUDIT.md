# United States — source audit

Lane: UNITED STATES source audit, written 2026-10-30. **Nothing here is ingested, and no
published number changes.** This document records what each candidate source *is*, what it may
legally and safely be used for, and an adoption decision. Readiness per sector is in
[US_INDEX_READINESS.md](US_INDEX_READINESS.md); sourced context figures are in
`data/candidates/us_profile.json`. Incident research is a separate lane and is not done here.

Read the companion global framing first: [../GLOBAL_METHODOLOGY.md](../GLOBAL_METHODOLOGY.md).
This audit refines the United States row of its §4.1 matrix with what was actually verified, and
**corrects three cells** of it (see §0, finding 6).

**Safety posture applied throughout.** Infrastructure appears here only as public descriptive
context (name, operator, class, capacity, status, admin region) from datasets that already
publish it. Several US federal datasets publish facility or incident **latitude/longitude**
(EIA-860M, PHMSA incident files, NOAA Storm Events). Every one of them also carries **state and
county** fields, so the US needs no point-in-polygon step at all: **coordinate columns are never
read**, and that is stated per source below. No source was assessed for, and nothing here says
anything about, criticality, vulnerability, redundancy or security of any facility.

---

## 0. Summary

| Decision | Sources |
|---|---|
| **adopt** | EIA *Refinery Capacity Report* (per-refinery XLSX + Tables 1/11/13); EIA *Refinery Utilization and Capacity* (monthly, PADD); EIA-860M monthly generator inventory; EIA-860 annual; EIA *Monthly Energy Review* (context); EIA *U.S. Liquefaction Capacity* file; EIA underground storage field-level capacity (NGQS RP7); EIA *Annual Coal Report* + mine-level `coalpublic` files; EIA bulk files (no key); EAGLE-I county outage history (CC BY 4.0, derived aggregates only); Natural Earth admin-1 |
| **adopt-derived-facts-only** | DOE OE-417 annual summaries (state, dates, event type, demand loss, customers — acquisition path unresolved, §2.1); DOE/CESER situation reports (state-level outage and restoration figures); PHMSA incident data (state/county, dates, cause, shutdown/restart — **lat/long never read**); EIA state-to-state gas pipeline capacity; NERC reliability and event-analysis reports; ERCOT public data; GEM GOIT/GGIT (US rows) |
| **discovery-only** | EIA Open Data API v2 (key-gated; the same data are in keyless bulk files); EIA International Energy Statistics (context only); NOAA Storm Events (hazard attribution only); FERC (eLibrary, LNG lists, joint FERC–NERC event reports); CAISO; California Energy Commission; GEM GIPT / Global Coal Plant Tracker / Coal Mine Tracker (cross-check only); OpenStreetMap; Texas PUC |
| **reject** | WRI GPPD (frozen, no status field, superseded for the US by its own upstream); EIA-757 processing-plant file as a *denominator* (2017 vintage); PHMSA National Pipeline Mapping System geodata (access-restricted and its value is route geometry); any facility-level substation/line geodata (HIFLD and similar) on safety grounds; NERC GADS/TADS (not public) |

Six findings that matter more than any single row:

1. **The US refining registry passes the test Russia's fails.** EIA's per-refinery file for
   1 January 2026 gives operable **atmospheric crude distillation capacity in barrels per
   calendar day for 124 sites, and those 124 values sum to exactly 18,160,493 b/cd — the national
   Table 1 total — with zero missing values.** The same file carries barrels per stream day
   (sum 19,157,174, also exact) and an operating/idle split (18,126,493 / 34,000). One source,
   one basis, one census, mandatory reporting (Form EIA-820, ~100% response). Numerator and
   denominator can be drawn from it on a single basis by construction.
2. **But "130 operable refineries" is not 130 crude units.** Since 2024 the EIA-820 frame
   includes non-refinery operators of downstream processes. Six of the 130 respondents (all in
   Texas or Louisiana) have **no crude distillation capacity at all**. A denominator must be
   defined on crude distillation capacity, not on the refinery count — the same trap as
   Tobolsk in the Russian registry. Separately, the annual census lags: Valero Benicia
   (145,000 b/cd) is in the 1 January 2026 census but stopped refining in early 2026; EIA's
   *monthly* PADD-level operable capacity already dropped to 18,015 thousand b/cd in March 2026.
3. **EIA-860M fixes, for the US, exactly the defect GENERATION_DENOMINATOR_AUDIT.md found
   in Russia.** The September 2026 file lists 28,484 operating-sheet generators with
   nameplate, net summer and net winter MW, status (OP/SB/OS/OA), operating month/year and
   planned retirement dates, and a **Retired sheet of 7,321 generators with retirement
   month/year back to 2002**. A census-at-date is therefore constructible. Tested: rebuilding
   in-service net summer capacity at 1 January 2022 from this single 2026 file gives
   **1,149.5 GW against EIA's published end-2021 figure of 1,145.9 GW (+0.3%)**. The residual
   is expected (current ratings applied backwards; status history not dated).
4. **Several primary US sources are not machine-reachable from this machine, which matters
   for a scheduled GitHub Action.** PHMSA and FERC return HTTP 403 (Akamai) to non-browser
   clients; the OE-417 summary host (`www.oe.netl.doe.gov`) resolved to an IPv6 address only
   and was unreachable; one EIA landing page returned 403 while its XLSX downloaded fine. Every
   adopted source below states its access path.
5. **EIA has stopped republishing OE-417.** The *Electric Power Monthly* "Appendix B" (major
   disturbances, historically a mirror of OE-417) is listed as **"Suspended"** on the October
   2026 release page. The only path is DOE's own summary site.
6. **Corrections to GLOBAL_METHODOLOGY §4.1 (US row).** (a) Gas processing: EIA's plant-level
   file is a **2017** census released January 2019 — INCOMPLETE as a denominator, not
   EXPERIMENTAL. (b) Coal supply: mine-level files carry *production*; productive capacity is
   published only by **state** (832.8 MMst, 2024) — EXPERIMENTAL, not READY. (c) BSEE daily
   Gulf shut-in statistics were **not verified** in this lane (web search budget exhausted
   before it could be checked); the cell should read "candidate, unverified" until checked.

---

## 1. Primary official — federal statistical (EIA)

Licence for all EIA rows, verified on <https://www.eia.gov/about/copyrights_reuse.php>:
*"U.S. government publications are in the public domain and are not subject to copyright
protection."* and *"You may use and/or distribute any of our data, files, databases,
reports"*. Requested acknowledgement includes the publication date ("Source: U.S. Energy
Information Administration (Oct 2008)"). **Exceptions:** photographs (privately licensed) and
the EIA logo (trademark); third-party copyrighted material within reports needs the owner's
permission. **Raw redistribution: yes** for data files. Note that EIA statistics sometimes
incorporate third-party inputs (e.g. the liquefaction file cites company websites and trade
press); the *compiled table* is still EIA's public-domain publication.

### 1.1 EIA Refinery Capacity Report (Form EIA-820)

| Field | Finding |
|---|---|
| Provider / product | EIA, *Refinery Capacity Report*, <https://www.eia.gov/petroleum/refinerycapacity/> |
| Sector | refining |
| Coverage | All operating and idle petroleum refineries in the 50 states, DC, PR and territories; since 2024 also non-refinery operators of distillation, reforming, cracking, coking, hydrotreating. 130 respondents on 1 Jan 2026 |
| Temporal | Annual census as of 1 January; issues listed 2016–2026 on the page, survey dating to 1983 (EIA-820), not conducted for 1996 and 1998. Table 13 lists permanent shutdowns 1990–2026 with dates of last operation and shutdown; Table 11 lists new/shutdown/reactivated refineries for the prior year with dates |
| Cadence | Annual (released June 26, 2026; next June 2027) |
| Machine access | **XLSX** per-refinery long-format file (`refcap26.xlsx`, columns CORPORATION, COMPANY_NAME, STATE_NAME, SITE, PADD, PRODUCT, SUPPLY, QUANTITY); PDF tables. Keyless direct download worked |
| Auth | none |
| Licence / redistribution | Public domain (EIA). Raw file may be committed |
| Geography | Refiner + site name + **state** + PADD. No coordinates |
| Status semantics | Operating vs idle capacity per refinery (idle = "distillation units completely idle but not permanently shutdown on January 1"); shutdowns with dates in Tables 11/13. Status is a 1 January snapshot — a mid-year closure appears only in the next issue |
| Capacity semantics | Operable **atmospheric crude oil distillation** capacity in **barrels per calendar day (b/cd)** and **barrels per stream day (b/sd)**; downstream charge and production capacities separately (mostly b/sd). Respondents report b/cd; for imputed non-respondents EIA takes b/cd from the January EIA-810 and **derives b/sd as b/cd ÷ 0.95** (Explanatory Notes) |
| Verified numbers | 124 sites with crude capacity; Σ operable = **18,160,493 b/cd** (= Table 1); Σ b/sd = 19,157,174; idle 34,000 b/cd (two sites); 6 frame members with no crude capacity. Per-site b/cd ÷ b/sd ratio ranges 0.40–0.996; 10 sites sit at exactly 0.95 (consistent with the imputation rule) |
| Known biases | Annual lag (Benicia, §0.2); "refinery" count inflated by 2024 frame change; b/sd partly derived; capacity is *operable*, not demonstrated |
| **Decision** | **ADOPT** — refining denominator, and the numerator's capacity basis (b/cd crude distillation, from this file only) |

### 1.2 EIA Refinery Utilization and Capacity / Petroleum Supply Monthly (Form EIA-810)

| Field | Finding |
|---|---|
| Product | Monthly operable crude distillation capacity (calendar day), operating and idle capacity, gross input, utilisation; <https://www.eia.gov/dnav/pet/pet_pnp_unc_dcu_nus_m.htm> |
| Coverage / geography | US and **PADD** (and PADD sub-districts); **not refinery-level** |
| Temporal / cadence | Monthly; latest data August 2026 (PSM released 30 Oct 2026) |
| Verified numbers | Operable capacity Mar–Aug 2026: 18,015 / 18,015 / 18,027 / 18,027 / 18,044 / 18,012 thousand b/cd; idle 107 → 2; utilisation 91.6–97.6% |
| Access / licence | HTML/XLS series, bulk file, API; public domain |
| Use | Monthly correction of the annual census's lag at PADD level; **observed aggregate throughput** as context for recovery (never attributed to a single plant) |
| **Decision** | **ADOPT** (context and lag check). PADDs are not admin regions — never map PADD values onto states |

### 1.3 EIA-860M Preliminary Monthly Electric Generator Inventory

| Field | Finding |
|---|---|
| Product | <https://www.eia.gov/electricity/data/eia860m/> |
| Sector | electric_generation (and coal-fired generation as a subset) |
| Coverage | Plants ≥ 1 MW combined nameplate; Puerto Rico since March 2018 |
| Temporal / cadence | Monthly, ~1-month lag (Sept 2026 data released 23 Oct 2026; next 24 Nov 2026); archive back to July 2015; **Retired sheet lists generators retired since 2002** (from March 2017 data) |
| Machine access | XLSX, keyless (14 MB). Sheets: Operating, Planned, Retired, Canceled or Postponed, plus `_PR` sheets |
| Licence | Public domain (EIA); raw redistribution permitted |
| Geography | Plant State, **County**, Balancing Authority. Also Latitude/Longitude and Google/Bing map links — **never read** (county is sufficient) |
| Status semantics | Operating sheet: OP 26,235 / SB 1,497 / OS 536 / OA 216 generators. Planned: P, L, T, U, V, TS. Retired sheet: retirement month/year. Operating month/year on every generator; planned retirement year on 518 operating generators |
| Capacity semantics | **Nameplate**, **net summer** and **net winter** MW per generator; DC net capacity and MWh for storage. Operating-sheet sums: nameplate 1,417,017 MW, net summer 1,324,125 MW (65 non-numeric cells), net winter 1,366,459 MW. OP-only net summer 1,300,414 MW |
| Caveats | EIA: capacities are "preliminary estimates" and are corrected "without specific acknowledgment" later. Retired tab from the annual EIA-860 is *not* comprehensive; the 860M Retired tab is. Uprates/derates are not dated historically |
| Verified test | Census-at-date rebuild for 1 Jan 2022: 1,149.5 GW vs MER end-2021 1,145.9 GW (+0.3%); 48.1 GW of that 2022 base has since retired |
| **Decision** | **ADOPT** — generation denominator (net summer basis recommended, see readiness doc), census-at-date from the Retired sheet. Archive the monthly files to make each vintage citable |

### 1.4 EIA-860 annual

Final 2025 data released 10 Sep 2026; detailed files 2001–2025 (860A/860B 1990–2000), ZIP of
XLSX. Generator file split Operable / Proposed / Retired-and-Canceled; its Retired tab only
covers retirements reported in the latest cycle. Public domain. **ADOPT** as the annual
"final" check on 860M; 860M is the operational source.

### 1.5 EIA Electric Power Monthly

Latest release 23 Oct 2026 (August 2026 data). Table 6.1 gives utility-scale net summer capacity
**1,318,809 MW at end-August 2026** with additions/retirements. **Appendix B (major
disturbances) is "Suspended".** Public domain. **ADOPT** for context only.

### 1.6 EIA Monthly Energy Review (MER)

Released 29 Oct 2026. Keyless CSV per table (`/totalenergy/data/browser/csv.php?tbl=…`). Source
of every national figure in `us_profile.json`. 2025 annual values are the latest EIA estimates
and are revisable. Public domain. **ADOPT** (context only, never a scoring input).

### 1.7 EIA Open Data API v2

<https://www.eia.gov/opendata/>. Free, but **requires a registered API key**; the Terms of
Service (<https://www.eia.gov/opendata/terms-of-service.php>) require EIA attribution, forbid
modifying content while attributing it to EIA, and allow EIA to block access without stating
numeric limits. No redistribution clause beyond the public-domain policy. Routes include
electricity (incl. `operating-generator-capacity`), petroleum (`pnp`), natural gas, coal,
**nuclear-outages**, international. **The same datasets are in keyless bulk ZIPs** (updated
twice daily). **DISCOVERY-ONLY** as a build dependency: a key breaks "rebuildable by anyone",
the same reasoning by which this repo rejected the GIE API (PIPELINE_SOURCE_AUDIT.md). Use bulk
files and direct XLSX instead.

### 1.8 EIA International Energy Statistics

Available via the API `international` route and bulk files. Useful only for **cross-country
context** (rankings appear in EIA's FAQ, e.g. US = 22% of world oil production in 2023). Not
read table-by-table in this lane. **DISCOVERY-ONLY / context.**

### 1.9 EIA U.S. Liquefaction Capacity

| Field | Finding |
|---|---|
| Product | `U.S.liquefactioncapacity_2026_Q3.xlsx`, released 1 Oct 2026, quarterly (landing page returned 403 to automated fetch; the XLSX downloaded) |
| Coverage | Large-scale LNG **export** projects permitted by FERC/MARAD and DOE: existing, commissioning, under construction, approved-not-FID |
| Status / dates | Per train: status (Commercial operation / Commissioning / Under construction), in-service date (first commissioning cargo), commercial-service date (FERC order) |
| Capacity | **Two bases per train**: baseload nameplate and peak nameplate, in Bcf/d and Mtpa; some Mtpa are company-supplied (flagged `^`), conversion factor 48.079 otherwise |
| Verified sums | Commercial operation: 20 rows, baseload **11.42 Bcf/d**, peak 14.27. Commissioning: 4 rows (Plaquemines 1 & 2, Corpus Christi Stage 3, Golden Pass T1), baseload 4.64, peak 6.79. Under construction: 15 rows, baseload 14.96 |
| Caveat | **2025 exports averaged 15.1 Bcf/d — above the 11.42 Bcf/d "commercial operation" baseload.** Status ≠ exporting: trains export during commissioning, and actual output can exceed baseload. A denominator restricted to "commercial operation" + baseload would let a disruption exceed 100% |
| Geography | State (and "Offshore") only |
| **Decision** | **ADOPT** for LNG liquefaction, with an explicit basis rule (readiness doc §5) |

### 1.10 EIA natural gas: storage, pipelines, processing

- **Underground storage, field level** (NGQS report RP7, annual, latest Feb 2026; aggregate
  capacity report released 21 May 2026 for Nov 2025): working gas **design** capacity and
  **demonstrated peak** capacity, by field and state. 2025 changes: design +26 Bcf (+0.6%),
  demonstrated +6 Bcf (+0.1%). Totals were not stated on the landing page and the NGQS table was
  not opened. Public domain. **ADOPT** (storage denominator, design-capacity basis).
- **State-to-state pipeline capacity** (`EIA-StatetoStateCapacity_Jan2026.xlsx`): capacity of
  pipelines crossing state lines, borders and offshore. This is boundary-crossing capacity,
  not a registry of pipelines. **ADOPT-DERIVED-FACTS-ONLY** (context at state level).
- **Processing plants** (NGQS RP9): "location and capacity for all U.S. natural gas processing
  plants", **released 31 January 2019, data year 2017**. A state-level annual series of volumes
  processed exists (released 30 Oct 2026). **REJECT as a denominator** (stale census, no
  retirement axis — the WRI GPPD lesson); state volumes are context only.

### 1.11 EIA coal

- *Annual Coal Report* 2024 (released 19 Nov 2025; 2025 due Nov 2026): 512.5 MMst produced,
  **524 producing mines**, **productive capacity 832.8 MMst — published by state (Table 11)**.
  PDF + XLSX.
- Mine-level `coalpublic{YYYY}.xlsx`, 1983–2024 (EIA-7A + MSHA): production, company, mine,
  operation type, labour hours. **Capacity is not a field** as described; state and county
  confirmation pending on ingest.
- "Coal-fired electric power plants" file **discontinued after the Sep 2026 release** as a
  duplicate of 860M.
- Public domain. **ADOPT** (mine supply on a production basis; coal power via 860M).

---

## 2. Primary official — federal, incident and emergency

### 2.1 DOE OE-417 Electric Emergency Incident and Disturbance Report

| Field | Finding |
|---|---|
| Provider | DOE, sponsored by CESER (formerly Office of Electricity); summaries at `https://www.oe.netl.doe.gov/OE417_annual_summary.aspx` |
| Sector | transmission / grid (also generation-loss and fuel-supply emergencies) |
| Coverage | Mandatory filings by utilities, BAs and reliability coordinators when alert criteria are met (load shed, uncommanded loss, physical/cyber events, fuel emergencies, public appeals) |
| Temporal | Archives back to 2000; annual summaries in PDF and Excel |
| Fields (per secondary descriptions; **not verified on the live page**) | Date/Time Event Began, Date/Time of Restoration, Area Affected (state/county text), NERC Region, Alert Criteria, Event Type, Demand Loss (MW), Number of Customers Affected |
| Access | **Unreachable from this machine**: DNS returned only an IPv6 address and neither WebFetch nor curl (IPv4/IPv6) connected. The new reporting app (`doe417.pnnl.gov`) is a filing interface, not a data portal. EIA's mirror (EPM Appendix B) is suspended |
| Licence | DOE federal work — public domain is the expectation; **not verified on a terms page** (page unreachable) |
| Status semantics | Event start and restoration timestamps — an **observed duration** per event, which is exactly the recovery evidence this project privileges |
| Known biases | Threshold-based (small events absent); restoration fields are often blank or "unknown" in practice (to be measured on acquisition); "Area Affected" is free text; filings are preliminary |
| Safety | Event types include physical attack and vandalism. Use only state, dates, event-type class, demand loss and customers. **Do not build any per-facility or attack-pattern layer** |
| **Decision** | **ADOPT-DERIVED-FACTS-ONLY**, contingent on a working acquisition path (manual download into `data/raw/`, like GEM, until the host is reachable from CI) |

### 2.2 DOE CESER situation reports (ISER / ESF-12)

Event-driven PDFs on energy.gov, marked **TLP:CLEAR, "Report Distribution: Public"**. Verified
example: Hurricane Milton Situation Report #7 (16 Oct 2024): state-level customer outages with
timestamp, peak outages and % restored (Florida: 68,926 out, peak 3,365,661, 98% restored),
port and fuel-terminal status in prose, emergency fuel waivers. Seven reports over 7 days.
Federal public domain (expected; no separate terms page found). Not a time series and not
machine-readable; issued only for activated events. No 2025–2026 index page was located.
**ADOPT-DERIVED-FACTS-ONLY**: observed restoration figures (state level), with `kind=observed`.
Whether historical sitreps name individual refineries' shutdown/restart status was **not
verified** in this lane.

### 2.3 EAGLE-I county outage history (ORNL / DOE CESER)

| Field | Finding |
|---|---|
| Product | *EAGLE-I recorded electricity outages*, figshare `10.6084/m9.figshare.24237376` (v4, 2026-02-25); per-year DOIs at ORNL (2025: `10.13139/ORNLNCCS/3012826`) |
| Coverage | County-level customers-out at 15-minute intervals, 2014–2025; 3,044 of 3,226 counties by 2022; ~92% of customers by 2022 (Scientific Data 11:271, 2024) |
| Fields | FIPS, county, state, customers out, timestamp; plus MCC (modelled customer counts), DQI, coverage history |
| Licence | **CC BY 4.0** on figshare (verified via figshare API). The ORNL catalogue page states "All rights reserved" for its own site content; cite the figshare record |
| Size | ~1.0–1.44 GB **per year** of CSV — **do not commit raw**; commit derived county/state aggregates |
| Biases | No cause field; outages < 15 min unreliable; small/rural utilities under-captured; **zero rows omitted, so a missing row can mean zero or a collection gap** (unknown ≠ zero) |
| **Decision** | **ADOPT (derived aggregates only)** — the systematic, observed consequence and restoration series for the grid |

### 2.4 PHMSA pipeline incident and annual-report data (US DOT)

Assessed carefully against the safety boundary.

- **What exists**: incident ("accident") files for gas distribution, gas transmission and
  gathering, hazardous liquids and LNG facilities, and operator annual reports (mileage by state
  and commodity) as bulk ZIPs, back to 2004/2010 by form version (forms F 7000-1, F 7100.2).
- **Access**: `www.phmsa.dot.gov` returned **403 (Akamai) to every automated request**, so the
  live pages, field lists and terms could not be read in this lane. Field content stated here
  (operator, state/county, commodity, cause, shutdown and restart date/time, release volume,
  cost, and incident latitude/longitude) is from form knowledge and must be **verified on
  acquisition**.
- **Licence**: US DOT federal work; public domain expected; not verified on a terms page.
- **Safety**: the files carry **incident coordinates** — never read; reduce to state/county.
  Their value to this project is *what failed, when, and when it restarted*, which is
  historical and public. They are **not** to be used to characterise pipeline condition,
  integrity or exposure of intact systems.
- **Bias**: reporting thresholds are cost/volume based; most incidents are small and cause no
  service disruption — needs an inclusion threshold (e.g. shutdown reported) before any event
  enters a register.
- **Decision: ADOPT-DERIVED-FACTS-ONLY** (state/county, dates, cause class, shutdown/restart
  duration as `kind=observed`). **NPMS (National Pipeline Mapping System) geodata: REJECT** —
  its value is route geometry, and (from prior knowledge, not re-verified because the PHMSA
  site blocked automated access) GIS distribution is restricted to operators and officials.

### 2.5 NOAA NCEI Storm Events Database

Bulk gzipped CSV at `ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/` (details, fatalities,
locations); 2026 details file stamped `c20261026`. Event type, begin/end date, state, county/zone
FIPS, damage estimates, narratives; some begin/end lat/long — **never read**. NOAA data are
federal public domain. **DISCOVERY-ONLY**: hazard attribution of an energy event (which storm,
which counties, which dates). Never an energy-impact source.

---

## 3. Operator and regulator (non-statistical)

| Source | What it offers | Licence / terms (verified where stated) | Access | Decision |
|---|---|---|---|---|
| **FERC** | eLibrary dockets, LNG terminal lists, Form 714 (BA demand), joint FERC–NERC event reports (e.g. winter-storm inquiries) | Federal work; **pages returned 403 to automated fetch**, terms not read. FERC withholds **CEII** (critical energy infrastructure information) by rule — this project must never seek it | browser only | **DISCOVERY-ONLY** |
| **NERC** | State of Reliability, Summer/Winter Reliability Assessments, LTRA, major-event analyses | Site states "Copyright © 2026 … **All rights reserved.**" Terms page text not retrievable. GADS/TADS outage data are **not public** | PDF | **ADOPT-DERIVED-FACTS-ONLY** (dated facts with citation; no raw copying). GADS/TADS: **REJECT** (unavailable) |
| **ERCOT** | Grid conditions, capacity reports, event reports | Terms §5 (<https://www.ercot.com/help/terms>): public contents may be "used, reproduced, and redistributed" **unmodified** with notices; **raw data** may be used "in compilations, charts, and analyses without maintaining such notices" | web/API | **ADOPT-DERIVED-FACTS-ONLY** |
| **Texas PUC** | Rulemakings, event reports | Not verified | web | **DISCOVERY-ONLY** |
| **CAISO** | Outage reports, OASIS | Terms (<https://www.caiso.com/privacy-terms-of-use>): no copying "except as authorized"; reuse requires notices and credit; API terms: "CAISO owns all right, title and interest in … CAISO Data" | web/API | **DISCOVERY-ONLY** |
| **California Energy Commission** | Energy almanac (power plants, petroleum market) | Conditions of use: credit required; "**Use or modification … for commercial or profit-making purposes is prohibited**"; third-party material prohibited | web | **DISCOVERY-ONLY** (non-commercial clause is incompatible with an open repo) |

---

## 4. Structured open datasets (non-government)

| Source | Finding | Decision |
|---|---|---|
| **GEM GOIT / GGIT** (US rows) | CC BY 4.0, verified verbatim in this repo (PIPELINE_SOURCE_AUDIT.md). Same access problem as for Russia: citable releases are form-gated; the ungated `map-data` branch is a **live backend export with no release identifier**. Capacity fields are partial | **ADOPT-DERIVED-FACTS-ONLY** for pipeline capacity context, stamped provisional exactly as the Russian import is |
| **GEM GIPT** (Sept 2026 release) | Unit-level status, start year, retirement date. Licence page not rendered in this fetch; CC BY 4.0 per this repo's earlier verification. For the US it is a re-compilation of what EIA-860M publishes first-hand | **DISCOVERY-ONLY** (cross-check of 860M) |
| **GEM Global Coal Plant Tracker / Coal Mine Tracker** | As GIPT; EIA-860M and EIA-7A are the upstream | **DISCOVERY-ONLY** |
| **WRI GPPD** | Frozen; last data commit 2022-01-26 touched USA rows (repo finding); **no status or retirement field**; WRI says "not currently maintained" | **REJECT** for the US: EIA-860M supersedes it on every axis |
| **OpenStreetMap** (ODbL) | Power lines/substations/pipelines; share-alike | **DISCOVERY-ONLY**. Not needed for any US denominator; no new US facility geometry layer recommended |
| **Natural Earth admin-1** (public domain) | US states + DC; PR as a separate admin-0 | **ADOPT** (geometry). Join on USPS/FIPS codes; verify codes on ingest as was necessary for Russia |
| **HIFLD and similar facility geodata** | Substation and line geometry at facility level | **REJECT** on safety grounds — its value is facility-level geometry of grid nodes. Open availability in 2026 not verified |

---

## 5. High-quality secondary

| Source | Use | Decision |
|---|---|---|
| EIA *Today in Energy* articles | Dated facts with EIA attribution (e.g. 67807: refining capacity 2026; 67864: global LNG 2025) | **ADOPT-DERIVED-FACTS-ONLY** (context) |
| *Scientific Data* EAGLE-I descriptor (CC BY 4.0) | Coverage and bias statement for EAGLE-I | reference |
| Trade press (OGJ, Hydrocarbon Engineering, Reuters, Argus/Platts free pages) | Refinery fire/outage/restart reporting with dates | **DISCOVERY-ONLY** at audit level; the incident lane decides per item |

## 6. Discovery-only / not verified in this lane

Search budget was exhausted before these could be checked; they are **candidates, not
findings**: BSEE hurricane shut-in statistics (offshore production), USCG port-condition notices,
NRC daily power-reactor status (nuclear outages; the EIA API's `nuclear-outages` route exists),
TCEQ air-emission event reports (Texas facility upsets with start/end times), California refinery
outage reporting, EIA-861 customer counts by state, EIA working and shell storage capacity,
US Census cartographic boundaries (public-domain alternative to Natural Earth).

---

## 7. Attribution string (if any of the adopted sources are ingested)

> Energy data: **U.S. Energy Information Administration** (public domain), release dates per
> file. Outage history: **EAGLE-I**, Oak Ridge National Laboratory / DOE CESER, CC BY 4.0.
> Boundaries: **Natural Earth** (public domain).

## Provenance

Every number above was read in this lane on 2026-10-30 from the cited page or file. Files
downloaded for verification were kept in the session scratchpad, not the repo. Not re-verified
here: GEM licence text (taken from this repo's earlier audit); OE-417 field list (secondary
descriptions only); PHMSA field list and terms (site blocked automated access).
