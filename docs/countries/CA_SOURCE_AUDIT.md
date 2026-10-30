# Canada — source audit

Lane: CANADA source audit, written 2026-10-30. **Nothing here is ingested, and no published
number changes.** This document records what each candidate source *is*, what it may legally
and safely be used for, and an adoption decision. Readiness per sector is in
[CA_INDEX_READINESS.md](CA_INDEX_READINESS.md); sourced context figures are in
`data/candidates/ca_profile.json`. Incident research is a separate lane and is not done here.

Read the companion global framing first: [../GLOBAL_METHODOLOGY.md](../GLOBAL_METHODOLOGY.md)
(§2 decay outside a conflict, §3 transmission proxy, §4 denominators). This audit refines the
Canada row of its §4.1 matrix with what was actually verified.

---

## 0. Summary

| Decision | Sources |
|---|---|
| **adopt** | StatCan energy tables via WDS (25-10-0063, -0086, -0015, -0022, -0029, -0046, -0036); CER *Pipeline Throughput and Capacity* (attributes only, key-point coordinates dropped); CER *Refinery Crude Runs*; CER *LNG Exports*; CER *Estimated Crude Oil Production by Province* and *Marketable Natural Gas Production*; Natural Earth admin-1 (13 units, ISO codes correct) |
| **derived-facts-only** | CER pipeline incident data (province/date/type/interruption only — **latitude/longitude never read**); CER provincial/territorial energy profiles; NACEI facility layers (frozen 2016–2017); WRI GPPD (Canada); GEM trackers pending acquisition; AER ST-series; AESO, IESO, Hydro-Québec, BC Hydro data |
| **discovery-only** | BC Energy Regulator data centre; CER *Pipeline Profiles* web app; Canadian Disaster Database; TSB pipeline occurrence data |
| **reject** | CER interactive pipeline *map* data (reproduction prohibited); OSM for refineries/LNG/processing (same reasons as Russia, see SOURCES.md §3); AER ST53 (sold) |

Four findings that matter more than any single row:

1. **Canada has what Russia lacks: an official, annual, province-by-type generating-capacity
   census (StatCan 25-10-0022, 2006–2025).** That supplies the temporal denominator
   GENERATION_DENOMINATOR_AUDIT.md says Russia cannot construct — at aggregate level. A
   facility-level numerator still needs a unit-level source (GEM GIPT).
2. **Canada's official per-facility energy-infrastructure registry (NACEI) is frozen at
   2016–2017 vintage**, with no status or retirement field — the same defect as WRI GPPD, and
   GPPD's 1,159 Canadian rows are themselves 97% NRCan-sourced, so they are **not independent**.
   NACEI still lists six Alberta coal plants (6,425 MW coal) though Alberta ended coal-fired
   generation in June 2024.
3. **The CER incident dataset is regulator-grade and machine-readable, but only ~8% of its
   2022+ records involve any interruption to pipeline operations** (36 of 463), and it covers
   only federally regulated (interprovincial/international) pipelines. It is a strong
   recovery-evidence source and a weak disruption register. **It publishes incident
   latitude/longitude; those columns must never be read.**
4. **Grid-operator and utility data in Canada are mostly not openly licensed.** AESO and BC
   Hydro restrict reuse to non-commercial/unmodified; IESO's licence is non-sublicensable;
   Hydro-Québec's open data is CC BY-NC 4.0 and its outage feed is live-only (no history).
   Nothing at national level resembles the US OE-417 / EAGLE-I pair.

---

## 1. Licences — exact terms

### Open Government Licence – Canada, version 2.0 (federal)

Read verbatim at <https://open.canada.ca/en/open-government-licence-canada> on 2026-10-30.

- Grants: *copy, modify, publish, translate, adapt, distribute or otherwise use the
  Information*, worldwide, royalty-free, **including for commercial purposes**.
- Condition: acknowledge the source with the provider's attribution statement, else the default
  *"Contains information licensed under the Open Government Licence – Canada."*, and link the
  licence where possible.
- Not granted: personal information; third-party rights the provider cannot license; names,
  crests, logos, official symbols; information under other IP rights (patents, trade-marks,
  official marks).
- No-endorsement clause: no use suggesting official status or endorsement.
- **Raw redistribution: permitted.** Compatible in practice with this project's CC BY / ODbL
  mix; the obligation is the attribution string plus licence link.

Every CER and NRCan dataset audited below carries `license_id: ca-ogl-lgo` in the open.canada.ca
CKAN metadata (checked by API, not by page text).

### Statistics Canada Open Licence

Read at <https://www.statcan.gc.ca/en/reference/licence>. StatCan data are under **its own
licence**, not OGL–Canada, although open.canada.ca labels StatCan tables `ca-ogl-lgo`.

- Grants: use, reproduce, publish, **freely distribute, or sell** the Information and
  value-added products; sublicensing on consistent terms. Raw redistribution permitted.
- Attribution: *"Source: Statistics Canada, <name of product>, <reference date>"* for the data;
  *"Adapted from Statistics Canada, <product>, <reference date>. This does not constitute an
  endorsement by Statistics Canada of this product."* for derived products.
- Restrictions worth noting for this project: reproduce accurately; **do not merge with other
  data to identify individuals, businesses or organizations**; no implied endorsement. The
  re-identification clause is not engaged by national/provincial aggregates, but it is a reason
  never to try to back out suppressed (`x`) cells.

### Open Government Licence – Alberta, version 2.0

open.alberta.ca/licence returned HTTP 520 twice during this audit; the text was read from the
Open Definition copy (<https://opendefinition.org/licenses-md/inreview/OGL-AB-2.0/>). Same
grant as OGL–Canada (commercial use allowed, default attribution *"Contains information licensed
under the Open Government Licence – Alberta."*), **plus one extra exemption: "Information or
Records that are not accessible under applicable laws"**, and Alberta governing law / Alberta
courts. **Re-verify against open.alberta.ca before relying on it.**

**Critical:** OGL–Alberta covers the Government of Alberta's open-data portal. **The Alberta
Energy Regulator and AESO are not under it** — see their own rows below.

### Non-open terms met in this audit

| Provider | Terms (read 2026-10-30) | Consequence |
|---|---|---|
| AER (`aer.ca/copyright-disclaimer`) | Reproduction "without charge or further permission" for non-commercial use, with source identified and not presented as official; **copying for commercial redistribution prohibited** without written permission | derived facts only |
| AESO (`aeso.ca/legal`) | "may be used and copied for non-commercial, personal or educational purposes … provided that the material is **not modified**"; any other use needs written permission | derived facts only; raw redistribution no |
| IESO (`ieso.ca/en/Terms-of-Use`) | limited, non-exclusive, **non-sublicensable, non-transferable** licence to use and reproduce, with copyright notice; other use needs written permission | derived facts only |
| Hydro-Québec open data | **CC BY-NC 4.0** on every dataset in the Opendatasoft catalogue (26 datasets, API checked) | derived facts only unless the project is certain it stays non-commercial |
| BC Hydro (`bchydro.com/siteinfo/legal.html`) | content "may not be copied without the express permission"; online re-use "strictly prohibited" | discovery only |
| BC Energy Regulator | page footer "© Province of British Columbia. All rights reserved."; licence for the data centre not stated on the page | discovery only until a licence is confirmed |

---

## 2. Source-by-source audit

Column order in each block follows the lane brief. "Precision" is the finest geography the
source publishes; what this project may *use* is admin-1 (province/territory) at most.

### 2.1 Statistics Canada — energy tables via the Web Data Service (WDS)

| Field | Value |
|---|---|
| Provider | Statistics Canada |
| Products | 25-10-0063 *Supply and disposition of crude oil and equivalent* (monthly, 2016-01 → 2026-08); 25-10-0086 *Natural gas supply and disposition, monthly* (2016-01 → 2026-08; successor to archived 25-10-0055); 25-10-0015 *Electric power generation, monthly, by type* (2008-01 → 2026-08); 25-10-0022 *Installed plants, annual generating capacity by type* (2006 → 2025); 25-10-0023 *Conventional thermal capacity by principal fuel* (2006 → 2025); 25-10-0029 *Supply and demand of primary and secondary energy, TJ, annual* (1995 → 2024); 25-10-0046 *Coal, monthly production and exports* (2008-01 → 2026-08); 25-10-0036 *NGL and sulphur from processing plants* (1989 → 2026-08); 25-10-0081 *Petroleum products supply and disposition* (2019 → 2026-08) |
| Sector | all — production, refinery input, generation, capacity, gas, coal, primary energy |
| Coverage | Canada + provinces/territories (crude table: 11 provinces + "Atlantic provinces"; coal: 5 provinces) |
| Temporal | as above; monthly tables released ~2 months after reference month (Aug-2026 data released 2026-10-30) |
| Cadence | monthly / annual; WDS refreshes each business day at 08:30 ET |
| Machine access | REST/JSON at `https://www150.statcan.gc.ca/t1/wds/rest/` — `getCubeMetadata`, `getDataFromCubePidCoordAndLatestNPeriods`, `getFullTableDownloadCSV`. **Batch responses are not returned in request order — match on `productId` + `coordinate`** (found the hard way in this audit). Limits: 25 req/s per IP, 50 req/s total; HTTP 409 possible 00:00–08:30 ET while tables are locked |
| Auth | none |
| Licence | Statistics Canada Open Licence (§1) |
| Raw redistribution | **yes**, with the StatCan source line |
| Precision | province/territory — exactly the project's admin-1 unit |
| Status semantics | per-cell `statusCode` / `securityLevelCode`: e.g. 25-10-0015 *conventional steam turbine* returns `null` with statusCode 1 ("..", not available) for recent months; 25-10-0046 *bituminous metallurgical* returns `null` with securityLevelCode 1 (**suppressed for confidentiality**). A null here is "suppressed/unavailable", **never zero** |
| Capacity semantics | 25-10-0022: installed generating capacity, kW, by class of producer and type, **annual census** — no facility detail. No refining or processing capacity in these tables |
| Known biases | suppression of small-producer cells; revisions; crude table splits bitumen into **in-situ vs mined**, **non-upgraded bitumen vs synthetic crude** (upgrader output), and reports *equivalent products* (condensate, pentanes plus) **outside** "crude oil production". Identity verified on 2025 annual sums: crude total = net field production + synthetic crude; net field = heavy + light/medium + non-upgraded bitumen |
| Language | English and French (bilingual metadata) |
| **Decision** | **ADOPT** — denominators (generation capacity by province-year), observed aggregate production series (production-dip evidence for upstream/wildfire episodes at province-month level), and all national context figures |

### 2.2 Canada Energy Regulator (CER)

CER publishes 85 datasets on open.canada.ca (CKAN `organization:cer-rec`), all `ca-ogl-lgo`.
The ones that matter:

#### 2.2a Pipeline Throughput and Capacity Data (`dc343c43`)

| Field | Value |
|---|---|
| Product | Guide BB filings: throughput and capacity at **key points** for major CER-regulated pipelines — Enbridge Mainline, Trans Mountain (current + archived pre-May-2024 product categories), Keystone, Cochin, Trans-Northern, Southern Lights, Norman Wells, Line 9, Montreal, Westspur, Suffield, NGTL, TC Mainline, Foothills, Alliance, Westcoast, TQM, M&NE, Brunswick; plus oil apportionment |
| Sector | oil_logistics (trunk oil/liquids), gas (transmission) |
| Coverage | CER-regulated systems only (interprovincial/international). **Provincially regulated lines (most gathering and intra-Alberta mileage) are absent** |
| Temporal | 2006-01 → 2026-06-30 |
| Cadence | quarterly (oil monthly values, gas daily values) |
| Machine access | per-pipeline CSV at `cer-rec.gc.ca/open/energy/throughput-capacity/*.csv`, data dictionaries provided |
| Auth / Licence / Redistribution | none / OGL–Canada / **yes** |
| Precision | **key-point latitude/longitude** columns are present. These are measurement points on infrastructure; the project does not need them and **must not ingest them** (admin-1 only; no building-level coordinates). Assign key points to provinces by the curated name, not by coordinate |
| Status semantics | none per system; **`Available Capacity` vs `Nameplate Capacity` with `Reason For Variance`** — the dictionary says available capacity is impacted by "unplanned outages, maintenance, downstream constraints, or pressure restrictions" |
| Capacity semantics | oil: nameplate and available, 10³ m³/d, monthly; gas: capacity and throughput, 10³ m³/d and GJ/d, daily. **Capacities at successive key points on one system are not additive** |
| Biases | company-defined key points; product categorisation changes (TMX May 2024); quarterly lag |
| Language | English/French |
| **Decision** | **ADOPT (attributes only, coordinates dropped)** — the best open *observed* restoration signal Canada has for trunk pipelines. Utilisation figures are shown only at system level as descriptive context, never ordered into a list of which line "matters" |

#### 2.2b Pipeline incident data (`fd17f08f` summary; `7dffedc4` comprehensive)

| Field | Value |
|---|---|
| Product | Incidents at CER-regulated pipelines and facilities under the Onshore Pipeline Regulations and Processing Plant Regulations; comprehensive file has **102 columns** |
| Sector | oil_logistics, gas (pipelines; 3 processing incidents since 2022) |
| Coverage | CER-regulated only; 2,034 records |
| Temporal | 2008-01-01 → 2026-08-31 |
| Cadence | description says quarterly; CKAN metadata says monthly (`P1M`) — the provider's own metadata disagree |
| Machine access | CSV (`pipeline-incidents-comprehensive-data.csv`) + data dictionary; DOI 10.35002/ycrm-a941; visualisation source on GitHub |
| Auth / Licence / Redistribution | none / OGL–Canada / legally yes — **but see safety handling** |
| Precision | **`Latitude`, `Longitude` per incident**, plus nearest populated centre and province |
| Status semantics | `Status` (e.g. Closed); `Significant` yes/no; **`Duration of interruption of pipeline operations`** ∈ {No pipeline interruption, Short-term interruption, Long-term interruption}; `Closed Date` is regulatory closure, **not** restoration |
| Capacity semantics | none; released volume (m³), often "Not Provided" |
| Profile of 2022+ (463 records, computed this audit, coordinates not read) | types: Fire 147, Operation Beyond Design Limits 119, Release of Substance 91, Adverse Environmental Effects 59, Serious Injury 51, Explosion 8; **interruption: none 412, short-term 33, long-term 3, blank 15**; top "why" category *Natural or Environmental Forces* (110); provinces BC 185, AB 171, ON 43, QC 22, SK 21, MB 11, NB 6, NT 3, plus **one record with Province = "Maine"** (data-quality defect) |
| Biases | safety/environment reporting rule, not disruption reporting — most records are no-outage events; only CER-regulated assets |
| Language | separate English and French files |
| **Decision** | **DERIVED-FACTS-ONLY.** Read only: incident number, reported/occurrence date, province, incident type, what/why categories, interruption duration class, facility type, substance class. **Never read `Latitude`/`Longitude`**: the importer should select columns by name and fail closed if it would emit them, consistent with the existing coordinate test in `tests/test_pipeline.py`. Use (a) as a recovery-evidence source for incidents found elsewhere (short-term vs long-term interruption) and (b) as a coverage benchmark — not as an incident feed, since 92% of rows are not disruptions |

The CER *interactive pipeline map* page states its pipeline data "may not be reproduced,
published, distributed, or transferred in whole or in part" — **reject** that data; the open
CSV above is a different product under OGL–Canada.

#### 2.2c Refinery Crude Runs in Canada (`5c0099e0`)

| Field | Value |
|---|---|
| Product | weekly crude runs and **percent of capacity** for three regions: Ontario; Quebec & Eastern Canada; Western Canada |
| Sector | refining |
| Temporal / cadence | 1990-01 → 2026-09-15 (latest row read); weekly, ~6-week lag |
| Access / auth / licence | CSV / none / OGL–Canada, redistribution yes |
| Precision | **3 regions, not provinces** — "Quebec & Eastern Canada" merges QC, NB, NL (and NS) |
| Capacity semantics | capacity is implied (`volume ÷ percent`): week ending 2026-09-15 → Ontario 68.5, Quebec & Eastern 114.7, Western 112.1 thousand m³/d; **total ≈ 295 thousand m³/d ≈ 1.86 million b/d** (derived in this audit). Whether "Western Canada" includes upgraders is **not stated** in the dictionary; the magnitude (≈0.7 million b/d) matches refineries only (CER's Alberta profile gives 569 thousand b/d for Alberta's five refineries), so upgraders appear excluded — **inference, not confirmed** |
| Biases | regional aggregation hides single-plant outages in a 3-region total; percent-of-capacity basis undefined (operable vs nameplate) |
| **Decision** | **ADOPT** as observed regional refining-utilisation evidence and a cross-check on any refinery denominator. Not a per-plant source |

#### 2.2d LNG exports (`4ff317bb`), gas/NGL/crude/refined-product exports, crude-by-rail

| Field | Value |
|---|---|
| Product | monthly LNG exports by terminal (`Kitimat`, plus small truck/ISO-container flows at Delta, Vancouver, Highgate Springs, etc.); imports only to Aug 2024 (CER stopped authorising imports Aug 2022) |
| Temporal | 2009-07 → 2026-08 (monthly file); **annual file ends 2024** — use the monthly file |
| Finding | first `Kitimat` row: **June 2025**. 2025 exports 3.14 billion m³ (gas equivalent) of which Kitimat 3.05; Jan–Aug 2026 9.54 billion m³ |
| Licence / redistribution | OGL–Canada / yes. Detail file has price/value columns marked "Confidential" for some rows |
| **Decision** | **ADOPT** for LNG context and as observed export-flow evidence at the single export terminal |

#### 2.2e Production datasets, pipeline key attributes, provincial profiles

- *Estimated Crude Oil Production by Province* (`f83f252c`) — monthly, 2000 → **2024-12** (lags
  StatCan). *Historical Provincial Marketable Natural Gas Production* (`3bb59253`) — monthly,
  2000 → 2025-12. **ADOPT** as cross-checks; StatCan is primary.
- *Major Canadian Oil and Natural Gas Pipelines: Key Attributes* (`16282d1a`) — pipeline name,
  operator, parent, start year, CER-regulated length (km), commodity, **capacity in prose**
  (e.g. "approximately 1.6 Bcf/d" at a border key point), interconnections. **ADOPT as
  descriptive context only** (name/operator/class/capacity/status). The
  `Major interconnected pipelines` column is connectivity information; it may be stored as
  topology text per the existing rule ("topology known ≠ geometry known") but **never used to
  reason about alternate routes or redundancy**.
- *Provincial and Territorial Energy Profiles* (HTML, 14 pages). **DERIVED-FACTS-ONLY.** They
  carry per-province refinery and upgrader lists with capacities (e.g. Alberta: 4 upgraders
  ≈1.4 million b/d bitumen; 5 refineries 569 thousand b/d; ≈500 gas processing field plants).
  **Vintage trap:** every page says "Date modified 2026-03-26", but the content is 2021–2023
  data (electricity 2021; "LNG Canada … on track to enter service by mid-2025" as of March
  2024). The modification date is CMS churn, exactly the WRI trap in SOURCES.md §2. Cite the
  data year, never the page date. Terms: canada.ca "Terms and conditions" (Crown copyright,
  generally OGL-compatible for government web content — **not verified line by line**).
- *Pipeline Profiles* web app — **DISCOVERY-ONLY** (same data as 2.2a/2.2b, packaged).
- *Electricity generation and capacity in Canada* (`2cdf43fc`) — 2005–2016 only. **Reject**
  (superseded by StatCan 25-10-0022).

### 2.3 Natural Resources Canada (NRCan)

#### 2.3a NACEI — North American Cooperation on Energy Information mapping layers

| Field | Value |
|---|---|
| Provider | NRCan with US DOE and Mexico SENER |
| Products (Canada rows, ArcGIS REST attribute query, `returnGeometry=false`) | Power Plants ≥100 MW (**247** plants, 125,146 MW); Renewable Plants ≥1 MW (1,049); **Refineries (21: 14 "Refinery", 2 "Asphalt Refinery", 5 "Upgrader")**; Natural Gas Processing Plants (718: AB 601 from AER ST50, BC 84 from BCOGC, SK 32, NS 1); LNG Terminals (1 — Canaport import); Natural Gas Underground Storage (57: ON 34, AB 12, SK 8, QC 2, BC 1); border crossings (gas, liquids, electricity) |
| Temporal | **frozen**: `Period` 2015-06 → 2017-08 (power plants mostly 201708 / 201612; refineries "2016", source CAPP; gas plants 2017). open.canada.ca records published 2017-11-21, metadata last touched 2021-05-19 |
| Cadence | none since 2017 |
| Access | NRCan ArcGIS REST service, XLSX and SHP downloads (endpoints deliberately not recorded here: every layer carries facility coordinates) |
| Auth / Licence | none / OGL–Canada |
| Raw redistribution | legally yes. **Safety: every layer carries facility latitude/longitude and street address or legal land description** (gas plants use legal land descriptions). Ingest attributes only: name, owner/operator, type, capacity, province, period |
| Status / retirement | **no status field, no retirement field** — every row is "existing at 2016–2017" |
| Capacity semantics | refineries: **atmospheric distillation (`AD_Mbpd`)** plus downstream unit capacities (vacuum, cracking, reforming, coking, asphalt), 2016; power: `Total_MW` with per-fuel MW split; gas plants: `Capa_MMcfd` (licensed inlet capacity — the 718 plants sum to ~57,400 MMcf/d against national production of ~19.5 Bcf/d in 2025, i.e. **licensed nameplate including inactive plants, not operating capacity**) |
| Known biases | stale; Alberta coal (6 plants, 6,425 MW coal-MW) still present though retired/converted by June 2024; Come By Chance listed as a crude refinery (since converted to renewable diesel per CER); later refineries (e.g. Sturgeon) absent; LNG layer predates LNG Canada |
| Upgrader treatment | **the "Refineries" layer explicitly includes upgraders** ("including upgraders and asphalt refineries") with `Type` distinguishing them; the 5 upgrader rows sum to 1,430.5 thousand b/d AD capacity vs 1,845.1 for the 14 refineries. A naive sum of the layer (3,320.6) would **overstate Canadian refining by ~80%** |
| Language | separate English and French layers/files |
| **Decision** | **DERIVED-FACTS-ONLY** — a 2016 facility seed list and a capacity-basis reference, never a current denominator. Filter on `Type == "Refinery"` |

#### 2.3b Energy Fact Book

The 2025–2026 and Spring 2026 editions are PDFs at `energy-information.canada.ca`. **Fetching
failed in this environment with "unable to verify the first certificate"** (incomplete TLS
chain); the audit did not weaken TLS to get around it. Search snippets indicate a primary-energy
production chart for 2024 with and without uranium. **Not read, so no figure is taken from it.**
Expected status once readable: **DERIVED-FACTS-ONLY** (secondary compilation of StatCan/CER
data; cite the underlying table instead).

#### 2.3c Older NRCan atlas layers

"Generating Stations 2007", "Utility Generating Stations 1997", 1968 maps — **reject**
(historical).

### 2.4 Alberta Energy Regulator (AER) — ST-series

| Field | Value |
|---|---|
| Products | ST98 *Alberta Energy Outlook* (annual, 2026-09-29); ST3 *Energy Resource Industries Monthly Statistics*; **ST13** *Gas Plant/Gas Gathering System Statistics* (ST13A annual PDF; ST13B monthly CSV/PDF by facility and subtype; ST13C monthly CSV; files 2017–2026); ST26 *Coal Industry Monthly*; **ST39** *Mineable Oil Sands Plant Statistics Monthly Supplement* (PDF + XLS, 2017 → July 2026 issue, 3 months in arrears); ST50 (gas processing plant capacity list — not on the current listing page; NACEI cites it as of 2016); **ST53** in-situ statistics — **sold through IPSS** per the ST39 page |
| Sector | upstream (oil sands mined/in-situ), gas processing, coal |
| Precision | facility-level (ST13B, ST39); province only for this project |
| Status semantics | volumetric receipts/dispositions/process by month — a zero month is *observed* non-operation only if the facility reported; not a status field |
| Capacity semantics | ST13 has **no capacity fields**; capacity lived in ST50 |
| Terms | AER copyright: non-commercial reproduction allowed with attribution; **commercial redistribution prohibited** without permission; "free or ordered for a fee" per report. **Not OGL–Alberta** |
| Language | English |
| **Decision** | **DERIVED-FACTS-ONLY** for ST13B/ST39/ST98/ST3 (monthly facility volumes are observed restoration evidence for upstream shut-ins; publish only derived province-month facts and citations, not the tables). **REJECT ST53** (paid) |

### 2.5 AESO — Alberta Electric System Operator

| Field | Value |
|---|---|
| Products | Current Supply Demand (CSD, assets > 5 MW, real-time), historical CSD generation (data request), AIES Gen Capacity API (**generation capacity and outages submitted to the AESO**), asset list API, transmission outage reports (daily/monthly/long-range), interchange outage report |
| Machine access | API via an Azure APIM developer portal with an "API Access Instructions" PDF. **Whether a key/registration is required was not verified** (web search budget exhausted before the instructions could be located) — assume registration |
| Terms | non-commercial, **unmodified** copying only; other use needs written permission (`aeso.ca/legal`) |
| Precision | asset level |
| Status semantics | AIES Gen Capacity carries submitted outage capacity — closest thing in Canada to India's CEA forced-outage list, for one province |
| **Decision** | **DERIVED-FACTS-ONLY** (cite outage start/end facts at province level; never redistribute the feed; no unit-level outage table published by this project) |

### 2.6 IESO (Ontario)

Generator Output and Capability by unit (≥20 MW), hourly: daily XML at
`reports-public.ieso.ca/public/GenOutputCapability/`, monthly CSV May 2019 → present, XLSX
archive 2010 → Apr 2019. Transmission outage reports (today; planned 1 day–24 months). No API
key mentioned. **Terms: non-sublicensable, non-transferable licence** with a copyright line.
Unit-level hourly capability is observed outage evidence. **DERIVED-FACTS-ONLY.** Note: IESO
planned-transmission-outage reports describe *future* outages of named elements — **do not
ingest**; nothing forward-looking about grid elements belongs in this project.

### 2.7 Hydro-Québec

Opendatasoft portal `donnees.hydroquebec.com` (API v2.1, no auth), 26 datasets, **all CC BY-NC
4.0**: production by source (hourly history), demand, imports/exports, hydrometric flows.
`pannes-interruptions` (ongoing outages and planned interruptions) holds **0 stored records** —
it is a live feed with **no history**. **DERIVED-FACTS-ONLY** (NC licence); the outage feed is
**not usable** for a 2022+ historical series without our own archiving, which would be building
a live outage tracker — out of scope.

### 2.8 BC Hydro and BC Energy Regulator

- **BC Hydro** — website terms prohibit re-use without permission. Outage map is live only.
  **DISCOVERY-ONLY.**
- **BC Energy Regulator (formerly BC Oil and Gas Commission)** — 132 reports/datasets: facility
  index CSV, **plant capacities (zipped CSV)**, well production, permitted facility/pipeline
  geography (ArcGIS), pipeline incident map, drilling kicks and blowouts. Licence not stated on
  the data-centre page (footer "All rights reserved"). Plant capacities would be the BC
  gas-processing denominator. **DISCOVERY-ONLY until a licence is confirmed**; do not ingest the
  geographic layers (facility locations).

### 2.9 LNG — facility status (verification requested by the brief)

- **LNG Canada (Kitimat) is operating.** CER monthly LNG exports show the first `Kitimat` volume
  in **June 2025**; press coverage records the first cargo departing on **30 June 2025**
  (search results, e.g. gCaptain — not read in full; the CER series is the citable fact). Initial design capacity **14 Mtpa from two trains** (CER BC profile).
- Woodfibre LNG (2.1 Mtpa, completion expected 2027) and Cedar LNG (3.3 Mtpa, FID June 2024)
  are not operating per the CER BC profile (content dated ~March 2024; **re-verify**).
- Canaport (Saint John, NB) is an **import** terminal (regas 1.2 Bcf/d per NACEI 2017 and CER).
- No provincial LNG statistics beyond the CER export series were found.

### 2.10 Global Energy Monitor

Already used by the project (GGIT/GOIT, CC BY 4.0, see SOURCES.md §7). GEM's licence page
states *Creative Commons Attribution 4.0 International*. **Global Integrated Power Tracker,
September 2026 release** — unit-level capacity, status, start year, **retirement date**; this is
the one open source with the temporal axis Canada's facility layer lacks. Form-gated (same human
acquisition step already modelled for GGIT). Coal Plant Tracker, Coal Mine Tracker and Oil &
Gas Extraction Tracker are the analogous sources for coal and upstream. **Canadian coverage was
not confirmed** on the GIPT page (it lists no country breakdown) — confirm on acquisition.
**DERIVED-FACTS-ONLY until a citable release is acquired; then ADOPT as the facility-level
generation layer**, crosswalked to StatCan province totals.

### 2.11 WRI Global Power Plant Database (Canada rows, from the repo's cached copy)

1,159 plants, **143,579 MW**; `source` = Natural Resources Canada for 1,125 rows (97%), i.e.
**derived from the same NRCan/NACEI compilation — not an independent check**;
`commissioning_year` populated for only **29** rows (max 2014); `year_of_capacity_data` mostly
2016–2017; no generation reported; no status/retirement field; 15 coal plants, 9,772 MW.
StatCan's 2025 census is 155.9 GW. **DERIVED-FACTS-ONLY / reject as denominator** — the same
frozen-census defect documented for Russia, with no offsetting advantage over NACEI.

### 2.12 OpenStreetMap

ODbL, Overpass as for Russia. Not probed for Canada in this audit. Two Canada-specific issues
for whoever does: (1) Canadian bulk transmission classes are **735/500/345/315/240/230 kV**;
the Russia selector `voltage >= 330 kV` would drop Ontario's 230 kV, Alberta's 240 kV and
Hydro-Québec's 315 kV networks, and the scoring `voltage_weight` bands would map 735 kV to the
750 class by the `>=` rule; (2) the repo's tag probe found zero `industrial=oil_refinery` in
Russia — re-probe before assuming the same in Canada. **DISCOVERY-ONLY** pending a probe;
display-only context network at best.

### 2.13 Natural Earth admin-1

Checked in the repo's cached `ne_10m_admin_1.geojson`: **13 Canadian units** (10 provinces, 3
territories), `iso_3166_2` codes CA-BC … CA-PE all correct, French names present. No
swapped-code defect of the Moscow kind. **ADOPT** (public domain).

### 2.14 Other national registers checked

- **Canadian Disaster Database** (Public Safety Canada, OGL–Canada, XLSX). Inclusion rule is
  disaster-scale (≥10 killed, ≥100 affected/evacuated, etc.). **Metadata coverage ends
  2022-01-01** (extract named `CDD_Extract_2022`) although the record was modified 2026-02-10.
  Useless for the 2022+ window as it stands. **DISCOVERY-ONLY.**
- **TSB Pipeline Occurrence Database (PODS)** — OGL–Canada, monthly, 1979 →. The CSV URL
  returned **HTTP 403** (Azure Application Gateway) to a plain request; not worked around.
  Overlaps CER incidents. **DISCOVERY-ONLY**; assume it also carries coordinates until checked.

---

## 3. How each source treats Canada's specific structure

| Structure | StatCan | CER | NACEI | AER | GPPD / GEM |
|---|---|---|---|---|---|
| **Oil sands mining vs in-situ** | separate rows (2025: in-situ 1.94, mined 1.77 million b/d raw bitumen) | profiles: counts (8 mines, 26 thermal in-situ ops in AB) | not covered | ST39 mined (monthly), ST53 in-situ (paid) | GEM GOGET (extraction) — not checked |
| **Upgraders** | output as *synthetic crude oil production* (1.31 million b/d, 2025); *bitumen sent for further processing* is the upgrader input; refinery inputs listed separately by crude type | profiles list upgraders **separately** from refineries (AB 4 upgraders ≈1.4 million b/d bitumen; SK Lloydminster 81.5 thousand b/d heavy oil); crude-runs appears to exclude them (inference) | `Type = "Upgrader"` inside the Refineries layer | ST39 covers integrated mining+upgrading plants | n/a |
| **Refineries** | refinery *input* only (1.77 million b/d, 2025); no capacity | 17 refineries ≈1.93 million b/d (as of 2024, Canada profile); weekly regional runs and % capacity | 14 + 2 asphalt (2016) | Alberta's in AB profile | n/a |
| **Conventional production** | heavy and light/medium crude rows | provincial production estimates | n/a | ST3 | GOGET |
| **Trunk pipelines** | not covered | throughput/capacity, incidents (CER-regulated only) | border crossings only | provincial pipelines (AER licensing) | GGIT/GOIT routes |
| **Gas processing** | NGL/sulphur output (25-10-0036) | ~500 AB field plants (profile) | 718 plants, licensed capacity, 2017 | ST13 volumes, ST50 capacity (dated) | GGIT does not cover processing comprehensively — not checked |
| **Electricity by province** | capacity by type (annual) and generation (monthly) for all 13 | profiles (2021 data) | ≥100 MW plants (2017) | — | GIPT unit-level with dates |

**An upgrader is not a refinery.** It converts bitumen to synthetic crude, which then goes to
refineries. Counting both would double-count the same barrel's processing and would put
upstream (oil-sands) disruption inside the refining sector. The Russia registry already set the
precedent of excluding a non-fuels plant (Tobolsk) from the refining denominator; upgraders
should be excluded the same way and carried as an upstream/upgrading class.

---

## 4. What was not verified (stated, not implied)

- NRCan Energy Fact Book — not read (TLS chain failure; not bypassed).
- Alberta OGL — read from the Open Definition copy, not open.alberta.ca (HTTP 520).
- AESO API registration requirement — not confirmed.
- TSB PODS columns — not read (HTTP 403).
- GEM GIPT Canadian coverage — not confirmed; GIPT not acquired.
- OSM Canada tagging — not probed.
- canada.ca terms for CER profile pages — not read line by line.
- Saskatchewan / Nova Scotia / New Brunswick coal-retirement schedules beyond what CER profiles
  (2021-vintage) and the federal regulation text state.
- The web-search budget for this session was exhausted part-way through; remaining checks used
  direct fetches of known URLs only.
