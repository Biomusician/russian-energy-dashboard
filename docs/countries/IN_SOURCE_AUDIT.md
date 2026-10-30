# India (IN) — source audit

Lane: INDIA source audit, written 2026-10-30. **Nothing here is ingested, and no published number
changes.** This document records what each candidate source *is*, what it may legally and safely
be used for, and an adoption decision. Readiness per sector is in
[IN_INDEX_READINESS.md](IN_INDEX_READINESS.md); sourced context figures are in
`data/candidates/in_profile.json`. Incident research is a separate lane and is not done here.

India is in the five-country set because of **total primary energy production and the scale of
its electricity system** (EIA: 22.35 quadrillion Btu produced in 2024, about 78% of it coal). It is
**not** an oil-export analogue: India imports roughly nine-tenths of the crude it refines (PPAC).

Read the companion framing first: [../GLOBAL_METHODOLOGY.md](../GLOBAL_METHODOLOGY.md). This audit
**corrects three cells of its §4.1 India row** (§0, finding 1).

**Safety posture applied throughout.** Infrastructure appears only as public descriptive context
(name, operator, class, capacity, status, state/UT) from sources that already publish it. No source
was assessed for criticality, vulnerability, redundancy, chokepoints or security, and nothing here
says anything about them. Fields that come close to that line are named per source and marked
**never read**: plant coal-stock days (NPP Sub-report 2), pipeline utilisation percentages
(PPAC Ready Reckoner), inter-regional transfer capacity (CEA executive summary), reservoir levels
(NPP Sub-report 6), PNGRB route maps, and anything about strategic petroleum reserves. Nuclear
units appear only as operational status. No incident coordinates are recorded.

---

## 0. Summary

### Findings that change the plan

1. **The global matrix over-rates India in three cells.**
   - *Refining is not READY.* Three official refining totals for the same date range disagree:
     **MoPNG 248.866 MMTPA** (stale page, pre-2023 plant figures), **PPAC Ready Reckoner
     258.1 MMTPA** (nameplate, April 2026, "22 operational refineries"), and **PPAC
     installed-capacity page 267.116 MMT** (as on 1 April 2026). The 9.0 MMTPA gap is **HRRL
     Barmer/Pachpadra**, which the Ready Reckoner simultaneously calls "commissioning … underway"
     (refining chapter) and "achieved commercial operations" (foreword), and which has **no
     crude-processing row** in FY 2025-26. The denominator is excellent once that one status is
     decided; until then it is two bases.
   - *Generation is not READY at state level.* CEA's monthly state tables are explicitly
     "**including allocated shares in joint & central sector utilities**": they are
     **entitlements**, not plants located in the state. Delhi shows 3,664 MW of coal on that
     basis. They cannot be a regional physical denominator. The national fuel totals are fine.
   - *Transmission is not verifiable from here.* Every Grid-India host (grid-india.in,
     www., report., webapi., and the legacy posoco.in) reset the TLS handshake from this
     environment. Everything said about GD reports below is secondhand and marked so.
2. **CEA removes long-outage units from "installed capacity".** The September 2026 report states
   that 2,825 MW coal, 4,400.84 MW gas and 100 MW nuclear "under outage for very long time" were
   removed temporarily from 30.04.2025, and a further 370 MW coal/lignite, 978.4 MW gas and
   300.861 MW diesel from 31.08.2026, to be added back when they generate. **A long disruption
   therefore shrinks the official denominator.** Any capacity share built on CEA totals must add
   these back, or a long outage scores as less exposure than a short one.
3. **India publishes observed outages at unit level, daily, with an archive back to at least
   2018** (National Power Portal Sub-reports 10–15: forced/planned outage MW, start time, expected
   return, free-text reason, and a re-commissioning list). This is the observed-restoration
   evidence Russia never had. It is also a near-census of *routine* outages: on 28-10-2026 the
   ≥500 MW report alone listed tube leaks, fan faults and several **"RSD/low schedule"** (reserve
   shutdown for low demand — an economic choice, not a disruption). Adopting it forces an
   event definition before it forces anything else (see readiness doc).
4. **PPAC publishes refinery-wise crude processing monthly** (FY 2025-26: 271,991 TMT, 23
   rows, provisional). It is an observed-throughput series at plant level, usable as recovery
   evidence at monthly resolution. Capacity utilisation averaged 106% of nameplate in FY 2025-26,
   so nameplate is a conservative basis.
5. **Licensing is per website, not per government.** The Government Open Data License – India
   (GODL) applies to data published under it (data.gov.in). The ministry and agency sites audited
   here (PPAC verified; CEA and NPP partially) carry the standard GIGW website copyright policy:
   reproduction **"after taking proper permission"** by email, with source acknowledged. So raw
   redistribution of PPAC/CEA files is **not** open by default; derived facts with citation are the
   safe default until permission is obtained or a GODL mirror on data.gov.in is confirmed.
   data.gov.in itself refused connections from this environment (ECONNREFUSED / HTTP 503), so no
   GODL mirror could be confirmed.
6. **Cause taxonomy gap.** The project's `causes` are kinetic_strike, sabotage, cyber, technical,
   sanctions, maintenance, unknown. India's recurrent disruption classes — cyclone/flood/heat
   (weather), fuel supply shortfall at power stations, and economic reserve shutdown — have no
   class. Filing them under `technical` or `unknown` would mis-weight them.

### Decisions

| Decision | Sources |
|---|---|
| **Adopt** | EIA International (public domain, context profile); GEM GGIT/GOIT (CC BY 4.0, attributes only); GEM GCPT (CC BY 4.0 per GEM terms — confirm on the release file); OSM for transmission context (ODbL); Natural Earth admin-1 (public domain, with two attribute fixes) |
| **Derived-facts-only** | PPAC installed refinery capacity; PPAC refinery-wise crude processing; PPAC production / import / LNG tables; PPAC Ready Reckoner FY 2025-26; CEA installed-capacity report (national fuel totals only); CEA executive summary; NPP daily generation Sub-reports 2/10–15 (selected fields); Ministry of Coal Annual Report 2025-26; PIB press releases; Grid-India GD reports (*pending access*) |
| **Discovery-only** | MoPNG refining page; PNGRB authorisations; PPAC/PNGRB pipeline-structure table; CEA transmission and substation reports; CEA Thermal Broad Status; Ministry of Power; Coal India Ltd; GEM GCMT (licence notice conflict); Energy Institute; state SLDCs and discoms; data.gov.in (unreachable) |
| **Reject (as denominator)** | WRI GPPD (India rows = 57% of current capacity, 2019 vintage); MoPNG 248.9 MMTPA total (stale); CEA state tables as physical regional denominator |

---

## How each entry is laid out

Provider · dataset · sector · coverage · temporal range · cadence · machine access ·
authentication · licence/terms · **raw redistribution** · geography precision · status semantics ·
capacity semantics · known biases · language · **adoption decision**. "Verified" means read in this
session on 2026-10-30; "secondhand" means taken from a search snippet or another document and not
read at source.

---

## 1. Petroleum — Ministry of Petroleum and Natural Gas (MoPNG)

### 1.1 MoPNG *Refining capacity* page (mopng.gov.in/en/refining/refining-capacity)

- **Dataset:** refinery-wise nameplate table, 23 refineries grouped PSU (18) / JV (2) / private (3). Verified.
- **Sector:** refining. **Coverage:** all refineries incl. Reliance Jamnagar (DTA 33.0 + SEZ 35.2) and Nayara Vadinar (20.0).
- **Temporal range / cadence:** single undated snapshot; no as-of date in the table.
- **Machine access:** HTML table, scrapeable. **Auth:** none.
- **Licence:** site copyright policy not separately read; GIGW default assumed (permission on request).
- **Raw redistribution:** not granted by default.
- **Geography:** town name only (no state column).
- **Status semantics:** none; Nagapattinam/Cauvery Basin shown as "0.000@".
- **Capacity semantics:** "Name Plate Capacity (MMTPA)"; total **248.866**.
- **Known biases:** **stale.** HPCL Mumbai 7.5 and Visakh 8.3, Guwahati 1.0, Bongaigaon 2.35 are older than PPAC's April 2026 figures (9.5, 15.0, 1.2, 2.7); Bina still filed as the Bharat Oman JV. Narrative text says "248.9 MMTPA at present".
- **Language:** English (Hindi version exists).
- **Decision: discovery-only / reject as denominator.** Useful only to show that "official capacity" has at least three values.

## 2. Petroleum Planning & Analysis Cell (PPAC)

PPAC site licence (verified, ppac.gov.in/website-policies): GIGW standard — material may be reproduced
free of charge **after taking permission by email**, reproduced accurately, source prominently
acknowledged; third-party copyright excluded. Historical downloads on several pages sit behind a
**member login** ("Download Historical Report" opens a sign-in modal); current-year files and the
JSON behind the tables are public.

### 2.1 Installed refinery capacity (ppac.gov.in/infrastructure/installed-refinery-capacity)

- **Dataset:** refinery-wise capacity, '000 MT, "as on 1.04.2026"; XLSX current report (`1786541385_Refining-capacity-April-2026.xlsx`). Verified.
- **Sector:** refining. **Coverage:** 24 rows, 22 producing + CPCL Cauvery Basin (0, "under capacity augmentation") + **HRRL Pachpadra 9,000**. PSU, JV and private all included — Reliance (two Jamnagar entries) and Nayara Vadinar are in the same table on the same basis.
- **Temporal range / cadence:** annual (1 April). Historical file login-gated.
- **Machine access:** HTML + XLSX. **Auth:** none for current; login for history.
- **Licence:** PPAC GIGW policy. **Raw redistribution:** permission required.
- **Geography:** state column per refinery (state-level precision; CPCL Manali entered as "Chennai").
- **Status semantics:** none; "0" capacity used for a plant under augmentation; HRRL included at full capacity with no status flag.
- **Capacity semantics:** '000 MT per annum; basis not stated on the page. The Ready Reckoner calls the same figures "nameplate". **Total 267,116** — 9.0 MMTPA above the Ready Reckoner's 258.1 (the HRRL row).
- **Known biases:** source is "Oil Companies" (self-reported); no retirement or status field. The Ready Reckoner's Table 4.1 carries throughput by year since 2020-21 for the same plant list, which bounds when each plant was producing, but capacity history needs earlier editions.
- **Language:** English.
- **Decision: derived-facts-only** — curate per-refinery name, operator, state, capacity into a cited curated CSV; settle HRRL status explicitly (see readiness).

### 2.2 Refinery-wise crude oil processing (ppac.gov.in/production/crude-processing)

- **Dataset:** monthly crude processed per refinery, TMT; `PT_crude_processing_current 2025-26.xls`, modified 01-09-2026. Verified via the page's own JSON endpoint.
- **Coverage:** every refinery in §2.1 except HRRL (no row) — FY 2025-26 grand total **271,991 TMT**.
- **Temporal range / cadence:** monthly, fiscal-year files; FY 2023-24 onward selectable without login.
- **Machine access:** HTML table filled by a POST to `AjaxController/getCrudeProcessingData` (CSRF token from the page); XLS. **Auth:** none for current years.
- **Licence:** PPAC GIGW. **Raw redistribution:** permission required.
- **Geography:** state in the row label.
- **Status semantics:** throughput only; a month of zero or a sharp dip is an *observation*, but the cause (planned turnaround, unplanned outage, crude availability) is not stated.
- **Capacity semantics:** this is **throughput**, not capacity. Annual throughput exceeds nameplate (utilisation 106% in FY 2025-26 per Ready Reckoner).
- **Known biases:** provisional and revised later; monthly resolution hides outages shorter than a few weeks; HMEL Bathinda appears under the "HPCL" block and MRPL under "ONGC" (parent-company grouping, not ownership class).
- **Language:** English.
- **Decision: derived-facts-only.** Use as **observed recovery evidence** (return of a plant's monthly run to its pre-event level), never as a loss estimate inside the exposure index.

### 2.3 Production, import/export and LNG tables

| Table | Verified content (FY = April–March) | Notes |
|---|---|---|
| Indigenous crude oil (`getProduction`, page id 3) | FY 2025-26: crude 25.98 MMT, condensate 1.97, total **27.95 MMT**; modified 01-06-2026 | By regime (nomination/PSC), not by state on this view |
| Natural gas production (`getGasProduction`, page id 170, unit MMSCM) | FY 2025-26 gross **34,776 MMSCM**, net 34,326; onshore by state, offshore by basin (Mumbai Offshore 14,258; Eastern Offshore 10,589) | **72% of gross output is offshore and has no state** — a state denominator for gas production is structurally incomplete |
| Import/Export (`getImportExports`) | FY 2025-26 crude imports **246,601 TMT** (updated 21-10-2026) | Ready Reckoner Table 8.24 gives **245.8 MMT** for the same year — revision, not error; cite the vintage |
| LNG imports (`1781164918_NG-H_LNG_Import.xlsx`) | FY 2025-26 **25.98 MMT / 34,427 MMSCM** (P); FY 2024-25 26.96 MMT | Conversion stated as 1 MMT = 1,325 MMSCM |

Machine access: JSON endpoints behind HTML, XLS/XLSX for current files; history login-gated.
Licence: PPAC GIGW. Geography: national (gas: state + offshore basin). Language: English.
**Decision: derived-facts-only** (context profile; never a scoring input).

### 2.4 PPAC Ready Reckoner FY 2025-26 (annual PDF, ~32 MB) and monthly *Snapshot*

- **Dataset:** compendium. Verified tables: 4.1 refinery capacity + processing by year (2020-21 → 2025-26); 4.3 imported vs indigenous crude processed (imported share 90.5% in FY 2025-26); 3.9 LNG terminals (8 terminals, operator, capacity on 01.04.2026, **total 53.5 MMTPA**); 3.10 LNG imports; 8.24 crude import quantity; oil and gas at-a-glance tables.
- **Cadence:** annual (Ready Reckoner); monthly (Snapshot; Sept 2026 edition downloaded, not mined).
- **Machine access:** PDF only; table extraction works but needs checking.
- **Licence / redistribution:** PPAC GIGW; permission required.
- **Internal inconsistencies found:** LNG terminal capacity **53.5 MMTPA** in Table 3.9 vs **52.7 MMTPA** in the chapter text; HRRL status contradicts itself between foreword and refining chapter (§0).
- **Fields never read:** pipeline-wise capacity **utilisation** tables (chapter 4/pipelines), strategic reserve passages.
- **Language:** English.
- **Decision: derived-facts-only.** The best single citable document for the profile.

### 2.5 Gas pipeline structure (`1790853647_9_Pipeline-Structure-Web.xlsx`, source PNGRB)

- **Dataset:** common-carrier natural-gas pipeline network by operator: operational length and **authorised** capacity, partially commissioned, under construction. Two sheets (30.09.2024, 30.06.2026). Verified.
- **Content (30.06.2026):** operational 19,030.48 km; total operational incl. partially commissioned 27,598.48 km; GAIL 13,075 km operational.
- **Capacity semantics:** MMSCMD, footnoted as an **arithmetic sum per entity** — not a network throughput and not additive in any physical sense (same trap as Russia's GEM capacities).
- **Geography:** operator level only — **no route, no state**.
- **Decision: discovery-only** (operator inventory context).

## 3. Petroleum and Natural Gas Regulatory Board (PNGRB)

- **Dataset:** authorisation letters for natural-gas pipelines (`ngpl-auth.html`) and petroleum-product pipelines (`pppl-auth.html`): pipeline name, endpoints, authorised entity, letters (grant, amendment, extension, termination). Some entries link a "Route Map". Verified (listing pages).
- **Cadence:** as issued. **Machine access:** HTML lists + scanned/text PDFs. **Auth:** none.
- **Licence:** not read; GIGW default assumed. **Raw redistribution:** not assumed.
- **Geography:** endpoint place names. **Route maps: never digitised** (schematic, and drawing routes from them is outside this project's descriptive scope).
- **Status semantics:** legal authorisation status (granted / extended / terminated), not physical operating status.
- **Data bank / statistics pages** returned near-empty HTML (JS-rendered); not assessed.
- **Decision: discovery-only** (pipeline names and operators for crosswalk to GEM GGIT/GOIT).

## 4. Electricity — Central Electricity Authority (CEA)

The CEA site was rebuilt (Java backend, `jsessionid`); **every `cea.nic.in/wp-content/uploads/…`
PDF link now returns 404**, including links still indexed by search engines. Reports are served
from `/api/dashboardReports/download-pdf/en/<uuid>` and `/download-excel/en/<uuid>`, discoverable
from `/reports/dashboardView?…subSubHeadingId=<id>&lang=en`. Any ingestion must resolve UUIDs from the
listing page, not hard-code file URLs. CEA website policy: copyright policy is a linked PDF that was
not retrievable; GIGW default assumed. Bilingual English/Hindi throughout.

### 4.1 Installed Capacity report (monthly, listing id 10014)

- **Dataset:** "All India installed capacity (in MW) of power stations (utilities)" as on month end; PDF + XLSX; listing back to 2014. September 2026 report verified (10 pages).
- **Coverage:** utilities only (captive excluded); **total 558,896.39 MW on 30.09.2026**; coal 225,067.50 (40.27%), lignite 6,370, gas 19,144.02, diesel 288.34, nuclear 8,780, hydro incl. PSP 52,064.66, RES 247,181.86 (solar 171,051.46; wind 59,201.07). Off-grid RE included since August 2021.
- **Cadence:** monthly. **Machine access:** PDF + XLSX by UUID. **Auth:** none.
- **Licence / raw redistribution:** GIGW default, permission assumed required.
- **Geography:** regions → states/UTs, **but state rows include "allocated shares in joint & central sector utilities"**, plus pseudo-rows "Central – Unallocated", "NLC", "DVC". **Entitlement geography, not physical location.**
- **Status semantics:** installed = commissioned; **long-outage units removed temporarily** (2,825 MW coal + 4,400.84 MW gas + 100 MW nuclear from 30.04.2025; 370 MW coal/lignite + 978.4 MW gas + 300.861 MW diesel from 31.08.2026). Monthly additions and retirements are listed (Sept 2026: Udangudi TPP Unit-1, 660 MW, added 05-09-2026).
- **Capacity semantics:** MW nameplate; RES sector split "provisional"; RES figures "as per MNRE".
- **Known biases:** the removal rule (above); RES by MNRE, conventional by CEA — two compilers.
- **Language:** English with Hindi headings.
- **Decision: derived-facts-only, national fuel totals only.** Reject the state tables as a physical denominator.

### 4.2 Executive Summary (monthly, listing id 10071)

- **Dataset:** 66-page monthly compendium: generation targets/achievements, capacity additions, transmission line and substation additions, cumulative transmission ckm by voltage and ownership. March 2026 edition verified.
- **Content used:** FY 2025-26 generation **1,847.94 BU** vs FY 2024-25 1,828.88 BU (+1.04%); thermal 1,307.13 vs 1,363.07 BU. **Caveat:** these were read from PDF text extraction where table columns interleave; the column assignment is confirmed only by the arithmetic (1,828.88 × 1.0104 = 1,847.9), not visually.
- Transmission ≥220 kV cumulative **506,513 ckm up to March 2026** (national, by voltage/ownership, **no state split in this table**).
- **Never read:** inter-regional transfer capacity table.
- **Decision: derived-facts-only** (context).

### 4.3 Other CEA listings (not mined)

| Listing | What it is | Decision |
|---|---|---|
| Generation Reports (monthly actual / tentative), Daily Fuel Reports | Station-level monthly generation; daily fuel | Discovery-only. Fuel/coal-stock fields **never read** |
| SubStations (id 10051), Transmission Lines (id 10052) | Monthly completions ≥220 kV since 2015; growth summaries | Discovery-only (inventory growth, not status) |
| Thermal Broad Status (id 10020) | Under-construction thermal projects, monthly since 2007 | Discovery-only (commissioning dates for a census-at-date) |
| General Review (id 10084), Annual Report (10083) | Annual statistics incl. the material formerly in *Growth of Electricity Sector* | **Not retrieved in this audit** |
| Coal Reports (id 10056) | Coal statement / imports, **last 2024-02** | Discovery-only; stale |

## 5. National Power Portal (npp.gov.in) — CEA daily generation reports

- **Provider:** CEA Operation Performance Monitoring Division, hosted on NPP.
- **Dataset:** 16 daily sub-reports, PDF + XLS, at `npp.gov.in/public-reports/cea/daily/dgr/DD-MM-YYYY/dgrN-YYYY-MM-DD.pdf`. Verified: Sub-report 2 (region/state/station/unit-wise generation; 58 pages), 10 (daily maintenance report, coal/lignite/nuclear), 11 (same, units ≥500 MW), 14 (re-commissioning of thermal/nuclear units), 15 (units that went out of grid that day). Archive confirmed for 16-10-2018.
- **Sector:** electric generation (conventional: coal, lignite, gas, nuclear, hydro; **not** solar/wind).
- **Coverage:** monitored conventional capacity (Northern Region total 82,086.72 MW on 29-10-2026 in Sub-report 2). Unit threshold not stated on the pages read; Sub-report 15 lists units down to 6 MW.
- **Temporal range / cadence:** daily, archive ≥ 2018.
- **Machine access:** static URLs by date; PDF and XLS. **Auth:** none.
- **Licence:** NPP copyright text (verified) excludes third-party material from reproduction permission but the page does not state an affirmative grant; treat as GIGW.
- **Raw redistribution:** not assumed — derived facts only.
- **Geography:** **station grouped under its physical state** in Sub-report 2 (unlike §4.1). State-level aggregation is direct; no coordinates needed or read.
- **Status semantics:** per unit: planned / forced (major) / forced (minor) / other maintenance MW, outage date-time, expected or actual sync date, free-text reason ("WATER WALL TUBE LEAKAGE", "COAL FEEDING PROBLEM IN PLANT", **"RSD/LOW SCHEDULE"**, "CONSERVATION OF MAIN FUEL/RSD", "OVERHAULING WORKS").
- **Capacity semantics:** unit MW (monitored capacity).
- **Known biases:** utility-submitted, reason text not standardised; **economic reserve shutdowns appear alongside forced outages** and must be filtered; high volume (dozens of units per day).
- **Fields never read:** Sub-report 2 "COAL STOCK IN DAYS" (a fuel-state field), Sub-report 6 hydro reservoir levels.
- **Language:** English.
- **Decision: derived-facts-only, lagged and aggregated.** Use as (a) the physical-location conventional fleet register (station, unit, MW, state) and (b) observed outage start/return evidence. Publish only state-level aggregates with a lag, never a live per-unit availability feed — the project is a historical monitor, not a status board.

## 6. Grid Controller of India (Grid-India, formerly POSOCO) and RLDCs

- **Access result (verified negative):** `grid-india.in`, `www.grid-india.in`, `report.grid-india.in`, `webapi.grid-india.in` and `posoco.in` all failed the TLS handshake (connection reset during schannel handshake; curl exit 35) on 2026-10-30, and WebFetch got ECONNRESET. Likely geo- or bot-filtering. **Nothing below was read at source.**
- **Secondhand content:** monthly operational reports carry grid-disturbance events with category, region/utility and load loss (a trade-press summary of the January 2026 report cites a GD-1 event in Delhi with 846 MW load loss). GD categories follow the CEA Grid Standards Regulations 2010: GD-1 is loss of less than 10% of antecedent generation or load in a regional grid, GD-2 10% to under 20%, rising to GD-5; the higher of generation or load loss is used. RLDCs classify occurrences into grid incidents (GI) and disturbances (GD).
- **Sector:** transmission / grid. **Geography:** regional grid, state and named substation (substation names **would not be recorded** — state and region only).
- **Status semantics:** event-level; restoration time reportedly included.
- **Licence:** unknown (site unreachable).
- **Language:** English.
- **Decision: derived-facts-only, pending access.** Requires a human with working access (possibly from India) to confirm format, archive depth and terms. RPC protection-committee minutes (e.g. erpc.gov.in) contain detailed tripping analyses; only date, region/state, category, MW and duration should ever be taken — sequence-of-events detail is outside scope.

## 7. Ministry of Power (powermin.gov.in)

- Returned an 8 KB JS shell to curl, then an empty body. Not assessed. Its statistics are republished from CEA and via PIB.
- **Decision: discovery-only** (press releases via PIB).

## 8. Coal — Ministry of Coal and Coal India Ltd

### 8.1 Ministry of Coal Annual Report 2025-26 (chapter PDFs, coal.nic.in)

- **Verified content (ch. 2):** FY 2024-25 raw coal production **1,047.52 MT** against a target of 1,080.2 MT; company-wise CIL 781.06, SCCL 69.01, captive & others 197.46; FY 2025-26 to December 2025 721.65 MT. Dispatch FY 2024-25 1,025.33 MT. Ch. 9: coal demand FY 2024-25 1,267.13 MT. State-wise resources (geological, not production).
- **Cadence:** annual report; monthly "statistics at a glance"; PIB releases (FY 2025-26 captive/commercial 210.46 MT, verified, PIB 02-04-2026).
- **Machine access:** PDF; the "Coal Directory of India" chapters as XLSX (2024-03 uploads seen). **Auth:** none.
- **Licence:** not read; GIGW default assumed.
- **Geography:** company and state tables exist in the Coal Directory (not mined here); subsidiary-to-state mapping is not one-to-one (some subsidiaries span states).
- **Status semantics:** production, not capacity; mine "capacity" appears only as sanctioned project capacity.
- **Known biases:** fiscal year; provisional figures revised in the Coal Directory a year later. **FY 2025-26 all-India total was not found** in the material read.
- **Language:** English/Hindi.
- **Decision: derived-facts-only** (context; production-share denominator by state if the Coal Directory state table is curated).

### 8.2 Coal India Ltd (coalindia.in)

- Connection failed (curl exit 6) from this environment. Subsidiary production is published monthly by CIL and republished by the Ministry. **Decision: discovery-only** until reachable.

## 9. State SLDCs and discoms

Not audited individually (out of time and search budget; see Provenance). They publish load-shedding
and outage notices of uneven form, often in Hindi or the state language, and none was found to
carry a stated inclusion rule. **Decision: discovery-only** — useful to the incident lane for
corroboration, not as a systematic source.

## 10. Global Energy Monitor trackers

GEM's GGIT/GOIT terms were verified verbatim as CC BY 4.0 in an earlier iteration
(`docs/SOURCES.md` §7). The GCPT and GCMT project pages fetched today **do not state a licence**,
and the GCMT page footer reads "All Rights Reserved". Confirm the licence on the downloaded release
file before ingesting either. All are form-gated (human-in-the-loop, as the repo's GEM importer
already models). No GEM geometry or coordinates would be ingested — attributes and state only.

| Tracker | Verified today | India relevance | Decision |
|---|---|---|---|
| **GCPT** (coal plants) | July 2026 release; units ≥30 MW; bi-annual | Unit-level coal fleet with start year, retired year and status: the exact axis the Russia generation audit says is missing. Cross-checks CEA's removal of long-outage units | **Adopt** (licence to confirm on file) |
| **GCMT** (coal mines) | August 2026 release (second version of May 2026 data); production and capacity (Mtpa); statuses operating / inactive / proposed / construction / closed since 2015; India named | Mine-level production by state, independent of the Ministry's fiscal-year tables | **Discovery-only** until the licence conflict is resolved |
| **GIPT** | not re-checked | All-fuel unit census incl. solar/wind, which NPP does not cover | Discovery-only (same acquisition as for Russia) |
| **GGIT / GOIT** | licence verified earlier | India gas and crude/product pipelines; crosswalk to PNGRB names | **Adopt**, attributes only |

## 11. WRI Global Power Plant Database v1.3 — measured from the repo's cached copy

`data/raw/wri_gppd.csv`, India rows: **1,589 plants, 316,089 MW** — 57% of CEA's 558,896 MW
(30.09.2026). Coal 204,919 MW (CEA: 225,068). `year_of_capacity_data` is **2019** for 492 rows and
empty for 1,097; commissioning year empty for 1,093, newest 2018. Sources: Wiki-Solar 729 rows,
CEA 492, CDM 109. Generation columns 2013–2019 from CEA for 437 plants. India was among the
countries touched in GPPD's last data commit (2022-01-26, per `docs/SOURCES.md` §2), but the
capacity vintage is still 2019 and there is no status or retirement field.
**Decision: reject as a denominator**; CC BY 4.0 context at most.

## 12. EIA

- **International Energy Statistics, API v2** (`api.eia.gov/v2/international/data/`, verified with the public demo key): India 2024 primary energy production **22.349 quad Btu** (563.2 Mtoe), consumption 37.490 quad Btu; coal production 1,012,946 thousand t (17.34 quad Btu); dry gas 35.94 bcm; crude incl. lease condensate 590 kb/d; electricity capacity 531.46 GW; generation 2,051.8 BkWh. Calendar year.
- **Country Analysis Brief: India** (last updated 6 Feb 2025, verified HTML): 2023 data — coal 71.3% of generation (Table 1 shows 71%), 1,805 TWh (Table 1: 1,802.2), nameplate refining just under 5.2 million b/d (2024).
- **Licence (verified, eia.gov/about/copyrights_reuse.php):** public domain; attribution requested.
- **Caveat:** EIA generation (2,051.8 BkWh, calendar 2024) is far above CEA's FY 2024-25 1,828.88 BU; scope differs (EIA appears to include captive/gross generation). **Never mix EIA and CEA levels in one series.**
- **Decision: adopt for the context profile**, with calendar-year labels.

## 13. Energy Institute — *Statistical Review of World Energy*

The downloads page returned HTTP 403 to automated fetch. Terms of reuse **not verified**.
**Decision: discovery-only** (cross-check of national totals by a human).

## 14. OpenStreetMap in India — one Overpass count query, 2026-10-30

| Selector (inside India's admin_level 2 area) | Count |
|---|---|
| `power=line`, voltage includes 400/500/765/800 kV (ways) | **11,806** |
| `power=substation`, voltage includes 220/400/765 kV | **2,946** |
| `man_made=pipeline` + `substance=gas` (ways) | 99 |
| `man_made=pipeline` + `substance~oil` (ways) | 25 |
| `industrial=oil_refinery` | **0** |
| `power=plant` + `plant:source=coal` | 279 |
| `landuse=industrial` + `industrial=mine` + `resource=coal` | 46 |

The HV grid is well mapped; pipelines are nearly absent (99 gas ways against PNGRB's 19,030 km
operational) and refineries carry no refinery tag — the same pattern `docs/SOURCES.md` §3 found
in Russia. Indian voltage classes (765/400/220 kV, ±800/±500 kV HVDC) differ from the Soviet
bands in `scoring.json`'s `voltage_weight`. Note that the query uses OSM's own India area, whose
boundary may differ from the official Indian depiction. **Decision: adopt for transmission
context only (ODbL); reject for refineries and pipelines.**

## 15. Natural Earth admin-1 — measured from the repo's cached copy

36 India units, post-2020 (Ladakh separate from Jammu and Kashmir; Dadra and Nagar Haveli and
Daman and Diu merged). **Attribute defects:** Himachal Pradesh `type_en` = "Union Territory" (it is
a state); Gujarat `type_en` empty. ISO codes should be checked against the current ISO 3166-2:IN
list rather than trusted (the Russia build already carries its own code table for the same
reason). **Boundary caution:** Natural Earth's default admin-0 view differs from India's official
map depiction in Jammu & Kashmir, Ladakh and Arunachal Pradesh, and display of India's external
boundary is legally sensitive in India; Natural Earth ships point-of-view fields (`FCLASS_IN` is
present in the cached file). This needs a project-owner decision before any India map ships.
**Decision: adopt (public domain), with a curated code/type table.**

## 16. data.gov.in and the GODL

- data.gov.in refused connections (ECONNREFUSED; `www.` returned 503) to curl and WebFetch. The gazette notification PDF could not be read.
- **Secondhand terms** (OSM wiki page *Open Geospatial Data from Government of India*, read today): worldwide, royalty-free, non-exclusive licence to use, adapt, publish and create derivative works for lawful commercial and non-commercial purposes; attribution naming provider, source and licence with a URL/DOI; described there as ODbL-compatible. Other secondary summaries add the usual exclusions (personal and sensitive data, official names/crests/logos) and no-endorsement.
- **The key point:** GODL covers datasets *published on data.gov.in*. The same figures on PPAC or CEA sites are under those sites' GIGW copyright policy. A PPAC or CEA table becomes openly redistributable only if its data.gov.in mirror is found and cited.
- **Decision: discovery-only** until reachable; then check for mirrors of PPAC refinery capacity, CEA installed capacity and Coal Directory tables.

## 17. Press Information Bureau (PIB)

Ministry press releases (verified: Coal, 02-04-2026, release ID 2248300) carry official figures
with dates, in English plus Hindi and regional languages. **Decision: derived-facts-only** — good
for dated restoration and production statements; secondary to the underlying statistics.

---

## Out of scope — recorded so it is not re-proposed

- Strategic petroleum reserve capacities, fill levels or locations (mentioned in the Ready Reckoner foreword) — never recorded.
- Plant coal stock in days, reservoir levels, pipeline utilisation, inter-regional transfer capacity, PNGRB route maps, RPC tripping-sequence analyses.
- Any ranking of intact Indian facilities by size or importance; any "largest single" framing.

## Cross-cutting findings

1. **Fiscal year.** PPAC, CEA, Ministry of Coal and PIB report April–March fiscal years ("FY 2025-26" = 1 Apr 2025 – 31 Mar 2026); EIA and GEM use calendar years. Every figure must carry its year type.
2. **Provisional by default.** PPAC marks FY 2025-26 data provisional; crude imports moved from 245.8 to 246.6 MMT between the Ready Reckoner and the 21-10-2026 table. Cite the file date.
3. **Allocation vs location.** CEA state capacity is entitlement-based; NPP Sub-report 2 is location-based. A regional denominator must come from the latter (plus MNRE/GEM for RE).
4. **Denominators that move with disruption.** CEA's removal of long-outage units is the clearest case anywhere in the five-country set of an official denominator that shrinks during an outage.
5. **URL instability.** CEA's migration broke every indexed file URL; PPAC file names carry upload timestamps. Store the listing page and retrieval date with every snapshot.
6. **Language.** National statistical sources are English (Hindi in parallel). State-level and local outage reporting is frequently Hindi or the state language — an incident-coverage issue for the other lane, not a denominator issue.

## Provenance

Retrieved 2026-10-30 from this machine. Verified at source: PPAC (installed capacity page and
XLSX; crude processing, crude production, gas production, import/export JSON; LNG XLSX; pipeline
XLSX; Ready Reckoner FY 2025-26 PDF; website policy), MoPNG refining page, CEA (installed capacity
Sept 2026 PDF + XLSX; executive summary March 2026 PDF; report listings), NPP (Sub-reports 2, 10,
11, 14, 15; published-reports page; copyright text), Ministry of Coal (Annual Report 2025-26 ch. 2,
3, 9; PIB 02-04-2026), PNGRB authorisation listings, EIA API v2 and India brief and reuse terms,
GEM GCPT/GCMT landing pages, OSM Overpass (one count query), repo copies of WRI GPPD and Natural
Earth. **Not reachable:** Grid-India (all hosts), data.gov.in, Coal India, Energy Institute (403),
Ministry of Power (empty body). The session's shared web-search budget was exhausted part-way
through, so Grid-India's report formats and the SLDC/discom landscape could not be researched
further; they are marked secondhand or not audited above.
