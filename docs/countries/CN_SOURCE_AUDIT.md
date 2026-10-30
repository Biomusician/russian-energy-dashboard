# China (CN) — source audit

**Status: candidate research, not ingested.** Nothing here is a scoring input, and no code path reads
this file. Compiled 2026-10-30 by the China source-audit lane. Companion document:
[CN_INDEX_READINESS.md](CN_INDEX_READINESS.md). Sourced context figures live in
`data/candidates/cn_profile.json`.

Scope is the same as the rest of the project: publicly reported disruption to energy
infrastructure, aggregated to administrative region (province level for China). Sources were
assessed for how well they describe the installed base and how they would support historical,
public, open-source monitoring. They were not assessed for anything else. Sources whose main value
would be targeting-relevant are rejected. Strategic reserve storage is out of scope entirely
(§ "Out of scope").

## How to read this document

- **Verified** means the page was fetched during this audit (2026-10-30) and the quoted figure,
  field or behaviour was read from it.
- **NOT VERIFIED** means the statement comes from general knowledge or a secondary source and was
  not checked against the primary source in this pass. Do not cite it as fact until it is checked.
- **Access failures** were observed from this audit environment on 2026-10-30. A refused connection
  from one vantage point does not prove geo-blocking. It does mean an unattended scheduled job
  (the GitHub Action) cannot be assumed to reach the site.
- The audit's web-search allowance ran out partway through. Several items below are therefore
  marked NOT VERIFIED that a follow-up pass could close.
- Chinese names are given in the original. **Any English gloss in square brackets is this audit's
  own translation, not an official one**, unless the source itself supplies an English title.

## Summary table

| # | Source | Sector(s) | Decision |
|---|---|---|---|
| 1 | NBS Statistical Communiqué (annual) | all, national | **adopt** (context and completeness checks) |
| 2 | NBS monthly *Energy Production* release | coal, oil, gas, refining throughput, power | **adopt** (context, national only) |
| 3 | NBS *China Statistical Yearbook*, energy chapter | all, national and provincial | **derived-facts-only** |
| 3b | NBS *China Energy Statistical Yearbook* (中国能源统计年鉴) | all, provincial balances | **discovery-only** (NOT VERIFIED, print/paid) |
| 4 | NBS data portal (data.stats.gov.cn) | provincial monthly output | **discovery-only** (unreachable) |
| 5 | NEA power statistics releases and press conferences | power | **adopt** (national context and completeness checks) |
| 6 | NDRC | policy, refined-product prices | **discovery-only** |
| 7 | China Electricity Council (CEC) | power, grid | **discovery-only** (unreachable) |
| 8 | General Administration of Customs (GACC) | LNG, crude imports | **discovery-only** (unreachable) |
| 9 | SOE annual, CSR and ESG reports | per company | **derived-facts-only** |
| 10 | Provincial authorities | provincial | **discovery-only** (NOT VERIFIED) |
| 11 | MEM / National Mine Safety Administration accident cases | coal mines, chemicals | **discovery-only** (incident lane, restoration evidence) |
| 12a | GEM Global Coal Plant Tracker | coal power | **adopt** (denominator candidate) |
| 12b | GEM Global Coal Mine Tracker | coal supply | **adopt** (denominator candidate, province must be derived) |
| 12c | GEM Global Integrated Power Tracker | generation | **adopt** (denominator candidate) |
| 12d | GEM Global Solar Power Tracker | solar | adopt via GIPT; distributed solar is aggregate only |
| 12e | GEM GGIT / GOIT | gas, oil pipelines, LNG | **adopt** (same provisional caveats as Russia) |
| 13 | WRI Global Power Plant Database v1.3 | generation | **reject** as a denominator |
| 14 | EIA Country Analysis Brief: China | all | **adopt** (context only) |
| 15 | Energy Institute Statistical Review | all, national | **discovery-only** (unreachable, terms NOT VERIFIED) |
| 16 | OpenStreetMap | grid, pipelines | **derived-facts-only** (counts and context; legal caveats) |
| 17 | Natural Earth admin-1 | boundaries | **adopt** (with a scope decision on one polygon) |
| 18 | English Wikipedia *List of oil refineries*, China section | refining | **reject** as a denominator |

---

## 1. National Bureau of Statistics (国家统计局, NBS) — Statistical Communiqué

- **Provider / product:** NBS, *Statistical Communiqué of the People's Republic of China on the 2025
  National Economic and Social Development*, published 2026-02-28.
  `https://www.stats.gov.cn/english/PressRelease/202602/t20260228_1962661.html` (verified)
- **Sector:** All. Table 4 is *Output of Major Energy Products*: coal, crude oil, natural gas,
  electricity by thermal, hydro, nuclear, wind and solar. It also gives year-end installed
  generating capacity by type and total energy production and consumption.
- **Coverage:** National totals only. No provincial breakdown.
- **Temporal range / cadence:** Annual, published about two months after year end.
- **Machine accessibility:** HTML page in English and Chinese. Fetchable without authentication
  from this environment. There is no API.
- **Authentication:** None.
- **Licence / terms:** Official government publication. No open licence statement was seen.
  **Raw redistribution:** not established. Treat as citable figures (derived facts), not a
  redistributable dataset.
- **Geography precision:** National.
- **Status semantics:** Note 1: "All figures in this Communiqué are preliminary statistics." The
  energy totals are described as preliminary estimates. They are revised in the Yearbook.
- **Capacity semantics:** Installed generating capacity at year end, in 10,000 kW. 2025:
  3,891.34 million kW, of which thermal 1,539.04, hydro 448.02, nuclear 62.48, wind 640.01 and
  solar 1,201.73 million kW. Note 28 says some capacity, such as geothermal, is not listed.
  Thermal includes coal, oil, gas, waste heat and pressure, and biomass (note 27).
- **Known biases:** This is a **whole-economy** scope, and it differs from the monthly release
  (source 2). See the scope warning under source 2. Figures are preliminary.
- **Language:** English and Chinese.
- **Decision: adopt**, as sourced national context and as the completeness reference that any
  facility inventory must be reconciled against.

## 2. NBS — monthly *Energy Production* release (能源生产情况)

- **Product:** For example *Energy Production in December 2025*,
  `https://www.stats.gov.cn/english/PressRelease/202601/t20260120_1962355.html`, and *Energy
  Production in September 2026*,
  `http://www.stats.gov.cn/english/PressRelease/202610/t20261020_1965661.html` (both verified).
- **Sector:** Raw coal, crude oil, **crude oil processing (refinery throughput)**, natural gas,
  electricity generation, plus monthly year-on-year rates by power source.
- **Coverage:** National only, for **industrial enterprises above designated size** (规模以上工业).
  Per the release, these are enterprises with annual main business revenue of 20 million yuan or
  more.
- **Cadence:** Monthly, about the 15th to 20th of the following month. The January and February
  figures are usually combined.
- **Machine accessibility:** HTML in English and Chinese. Fetchable. No API. Full-year totals
  appear only in the December release, and full-year figures by power source are absent from it.
- **Licence / redistribution:** As source 1. Derived facts only.
- **Status / capacity semantics:** Throughput and output, not capacity. Refinery *throughput* is
  never a refining *capacity* denominator.
- **Known biases — a scope trap of the same kind as the refinery-basis lesson.**
  1. The scope (enterprises above designated size) changes every year. NBS calculates
     year-on-year growth on a like-for-like enterprise set, so its stated growth rates "may differ
     from the data published for the previous year". **Growth rates and levels from different
     releases cannot be chained.**
  2. Levels differ from the Communiqué for the same year. For 2025, electricity was
     **9,715.9 billion kWh** in the monthly release against **10,575.25 billion kWh** in the
     Communiqué, a gap of about 8%. The other products differ only slightly: coal 4.83 billion t
     against 4.85, gas 261.9 bcm against 262.06, crude 216.05 Mt against 216.087. The electricity
     gap is the largest, and is consistent with distributed and small generators sitting below
     the revenue threshold. **That explanation is this audit's inference.** A number from one
     scope must never be divided by a number from the other.
- **Observation (context only, not interpreted):** Crude oil processing for January to September
  2026 is **513.60 Mt, −6.8% y/y**, and September 2026 is −8.4% y/y. These are the release's own
  figures. This audit does not interpret them, and incident research is another lane's job.
- **Language:** English and Chinese.
- **Decision: adopt** for national context and throughput series only.

## 3. NBS — *China Statistical Yearbook 2025* (中国统计年鉴), energy chapter

- **Product:** `https://www.stats.gov.cn/sj/ndsj/2025/indexeh.htm` (English) and `indexch.htm`
  (Chinese). Chapter 9, Energy, has tables 9-1 to 9-19. They include 9-14 *Electricity
  Consumption by Region*, 9-15 *Installed Capacity of Power Generation* (national) and **9-19
  *Output of Main Energy Products by Region*** (分地区主要能源产品产量). There is also 13-13
  *Output of Main Industrial Products by Region*. All were verified from the yearbook's
  navigation frame.
- **Coverage:** Provincial (31 provincial-level units) for output and consumption. The yearbook
  data year is the year before the edition, so the 2025 edition covers 2024.
- **Cadence:** Annual, published around the fourth quarter.
- **Machine accessibility: poor.** In both the English and Chinese online editions, **every table
  in the energy chapter is a JPG image**. No XLS was listed for any of the chapter's 19 tables.
  Extraction would need OCR, and an OCR'd number is an estimate of a number. Explanatory notes
  are PDF. The printed and CD-ROM edition is sold commercially (NOT VERIFIED whether the CD has
  spreadsheets).
- **Licence / redistribution:** Not stated. Derived facts only.
- **Status / capacity semantics:** Output and consumption are revised figures that supersede the
  Communiqué. Capacity is national only (9-15). **No provincial installed-capacity table was
  found in this chapter.**
- **Decision: derived-facts-only.** Hand-transcribed provincial totals could serve as a
  completeness check, with a recorded transcription source. They are not suitable for automated
  ingestion.

### 3b. *China Energy Statistical Yearbook* (中国能源统计年鉴)

Provincial energy balances. Published by China Statistics Press as a priced print edition.
**NOT VERIFIED in this pass** (not fetched). **Decision: discovery-only.** It is not open and is
not redistributable.

## 4. NBS data portal (国家数据, data.stats.gov.cn)

- Hosts the national and provincial monthly series (分省月度数据), including provincial output of
  industrial products.
- **Access:** `https://data.stats.gov.cn/english/` returned **HTTP 404**, and
  `.../english/easyquery.htm?cn=E0101` returned **HTTP 403** from this environment on 2026-10-30.
  Terms could not be read.
- **Decision: discovery-only** until it can be reached and its terms read. If it becomes
  reachable, provincial monthly crude-processing and generation series would be the best
  available official **provincial throughput** context. They would still be throughput, not
  capacity.

## 5. National Energy Administration (国家能源局, NEA)

- **Products:** The monthly 全国电力统计数据 [national power statistics] release, for example
  《国家能源局发布2026年1-9月份全国电力统计数据》
  `https://www.nea.gov.cn/20261026/7e48f52542c94c0f99c166262453627d/c.html` (verified). There is
  an annual 全国电力工业统计数据 [national power-industry statistics] release in January, and
  quarterly press conferences (新闻发布会, for example `https://www.nea.gov.cn/xwfb/202610zb/index.htm`).
- **Coverage:** National. Total capacity and capacity by type, utilisation hours, investment.
- **Machine accessibility: poor for the tables.** The release text gives a few headline figures:
  4.13 billion kW total at end-September 2026 (+11.2%), solar 1.31 billion kW, wind
  0.70 billion kW, and 2,174 utilisation hours from January to September. **The full statistical
  table is embedded as a PNG image.** Hydro, thermal, coal, gas and nuclear capacity are in the
  image only. The site itself was reachable.
- **Licence / redistribution:** No open licence was seen. Derived facts only.
- **Status / capacity semantics:** Installed capacity, cumulative, at the end of the month. The
  utilisation-hours figure is for plants of **6,000 kW and above** (NOT VERIFIED for 2026; the
  scope is from secondary reporting on the 2025 annual release).
- **Known biases:** NEA capacity growth is very large: +16.1% in 2025 according to NBS, and
  +11.2% y/y to September 2026. A static denominator goes stale within months. See the readiness
  document.
- **Language:** Chinese. The NEA site has no English statistics.
- **Decision: adopt** for national context and as the completeness reference for a generation
  inventory. Transcribe from the text, not by OCR of the image, where possible.

## 6. National Development and Reform Commission (国家发展和改革委员会, NDRC)

- `https://www.ndrc.gov.cn/` was reachable. It publishes refined-product price notices (for
  example 国内成品油价格不作调整, 2026-10-15), energy policy instruments, and power-market rule
  consultations. Its 发改数据 [NDRC data] section showed only grain-procurement and price indices.
  **It publishes no energy datasets.**
- Refining-capacity caps are policy statements. EIA reports a government cap of 20 million b/d
  by 2025 (source 14). The original Chinese instrument was NOT VERIFIED in this pass.
- **Decision: discovery-only.** Useful for policy-driven supply events, such as production
  curbs, and never as a denominator.

## 7. China Electricity Council (中国电力企业联合会, CEC)

- Known publications (NOT VERIFIED in this pass): 电力工业统计快报 [power industry statistical
  bulletin], 中国电力行业年度发展报告 [annual development report of China's power industry],
  monthly data. These are reportedly the only routinely published source of national
  transmission line length and substation capacity by voltage class.
- **Access: `https://www.cec.org.cn/` and `http://www.cec.org.cn/` refused the connection
  (ECONNREFUSED) from this environment.** `https://english.cec.org.cn/` returned an essentially
  empty page.
- **Decision: discovery-only.** Try again from another vantage point before relying on it. Its
  terms are unknown, and parts of its data are reportedly member-only (NOT VERIFIED).

## 8. General Administration of Customs (海关总署, GACC)

- The primary source for LNG and crude **import** volumes.
- **Access: `http://english.customs.gov.cn/...` reset the connection (ECONNRESET).** In this
  pass, LNG import figures were obtainable only through secondary press, much of it paywalled.
  TASS (2026-01-20) attributes "76.64 million tons of LNG in 2024" to "official statistics".
  Search snippets attributed 68.43 Mt for 2025 to GACC, but the pages could not be opened (403 or
  paywall), so **that 2025 figure is NOT VERIFIED** and is not used.
- **Decision: discovery-only.** Imports are trade context, not infrastructure state.

## 9. State-owned enterprise reporting

| Company | Site tested | Result | What is published (as observed) |
|---|---|---|---|
| Sinopec (中国石化) | `sinopec.com/listco/en/` | **fetch failed** (twice) | — |
| PetroChina / CNPC (中国石油) | `petrochina.com.cn/ptr/` | **ECONNRESET** | — |
| CNOOC Ltd (中国海洋石油) | `cnoocltd.com` | reachable | Annual-report and ESG links labelled in Chinese ("CN" filenames); English section exists; results PDFs |
| State Grid (国家电网) | `sgcc.com.cn` | **fetch failed** | — |
| China Southern Power Grid (中国南方电网) | `csg.cn` | reachable | 2025 CSR report (2025年企业社会责任报告), **Chinese only**, June 2026 PDF; English news section |
| China Energy Investment (国家能源投资集团, CHN Energy) | `ceic.com` | reachable | Company-level operating capacity as of June 2026: 40,205 万千瓦 [about 402 GW], stated as about 9.9% of national; coal production capacity 7 亿吨/年 [700 Mt/yr] and 78 producing mines at end-2025 |

- **Coverage:** Company-level aggregates. Plant-level capacity is published inconsistently, and
  usually only for flagship sites in press items.
- **Listed-company annual reports:** Sinopec Corp, PetroChina and CNOOC Ltd file annual reports
  with HKEX (HKEXnews), which would be a more reliable mirror than the company sites. **Not
  accessed in this pass.** Those reports state company-wide crude-processing capacity and
  throughput. Refinery-by-refinery capacity is generally not tabulated (NOT VERIFIED for the 2025
  reports).
- **Naming:** Subsidiary refineries appear as, for example, 中国石化镇海炼化分公司, while English
  usage varies ("Zhenhai Refining & Chemical", "Zhenhai Refinery"). The crosswalk key must be the
  Chinese legal entity name, with English as an alias. **No translation in this document is
  official unless the company publishes it.**
- **Licence:** All rights reserved, by default. Raw redistribution is not permitted.
- **Decision: derived-facts-only.** Cite individual figures with URL and date. Never bulk-ingest.

## 10. Provincial authorities

Provincial statistical bureaux (省统计局) publish provincial communiqués and yearbooks.
Provincial development-and-reform commissions and energy bureaux (省发改委/能源局) publish project
approvals and supply notices. At least one, Beijing, runs an English site
(`tjj.beijing.gov.cn/EnglishSite/`, seen in search results, not fetched). **None were audited
individually in this pass.** Formats and access vary by province. **Decision: discovery-only.**
They are the most plausible route to provincial capacity figures, and assembling 31 of them on a
common basis is a substantial project of its own.

## 11. Ministry of Emergency Management (应急管理部, MEM) and National Mine Safety Administration (国家矿山安全监察局, NMSA)

- `https://www.chinamine-safety.gov.cn/` was reachable. Its 事故查处 → 事故案例 [accident handling
  → accident cases] section (`/zfxxgk/fdzdgknr/sgcc/sgalks/`) listed five coal-mine accident
  case reports, all **published 2025-12-03**, and identified only by a day-month code such as
  "8·21" or "6·6". **The year has to be read from the report body.** The publication lag can be
  months.
- `https://www.mem.gov.cn/` was reachable. It has 事故及灾害查处 [accident and disaster
  investigation] at `/gk/sgcc/` and 灾害事故信息 [disaster and accident information] at
  `/xw/zhsgxx/`. Contents not inspected.
- **Language:** Chinese only.
- **Decision: discovery-only** (for the incident lane). These are official accident investigation
  reports. They are also the most likely published source of **suspension and resumption**
  (停产整顿 / 复产) evidence for coal mines, which is the restoration evidence that sector needs.

## 12. Global Energy Monitor (GEM) trackers — CC BY 4.0

GEM's catalog API (`https://api.globalenergymonitor.org/catalog/metadata/...`) states **"Distributed
under a Creative Commons Attribution 4.0 International License"** for the coal-plant and coal-mine
trackers (verified). The tracker landing pages carry an "All Rights Reserved" site footer. That
footer covers the website, and the dataset licence is the one the API states. Downloads are
**form-gated**: the same human-in-the-loop acquisition the repo already models for GGIT/GOIT and
GIPT (`docs/PIPELINE_SOURCE_AUDIT.md`, `docs/GENERATION_DENOMINATOR_AUDIT.md`).

**⚠ Release identifiers disagree.** The Global Coal Plant Tracker landing page says "most recent
release … July 2026". The catalog API's metadata for the same tracker says "January 2026
release". Whatever is acquired must be labelled from the **file's own** release stamp. Neither web
page should be trusted for that, and the importer's `--release` discipline applies.

### 12a. Global Coal Plant Tracker (GCPT)
- **Fields (verified, 54):** unit and location IDs; **Plant name, Unit name, Plant name (other),
  Plant name (local)**; **Subnational unit (province, state)**, Major area (prefecture), Local area
  (county), coordinates with Location accuracy; **Status; Capacity (MW); Start year; Retired
  year**; Owner and Parent with GEM entity IDs; **SOE status, % State Ownership**; Captive, CHP;
  "China capacity payment recipient".
- **Coverage:** Units of **30 MW and above**; operating units, units proposed since 2010, units
  retired since 2000. 111 countries.
- **Status semantics:** GEM's shared status taxonomy, published as the catalog's `status-taxonomy`
  entry. Its categories were not re-read in this pass, and the importer must map them from the
  file rather than from memory.
- **Capacity semantics:** Unit nameplate MW.
- **Language:** English names, plus a **local-script name field**. Chinese characters are
  preserved, which supports a Chinese-name crosswalk.
- **Decision: adopt** as the strongest China denominator candidate. It is unit-level and dated
  (start and retire years) with a province field. That is exactly the temporal axis
  `GENERATION_DENOMINATOR_AUDIT.md` found missing for Russia. **Coordinates are not needed and
  should be dropped at import.** Province comes from `Subnational unit`.

### 12b. Global Coal Mine Tracker (GCMT) — May 2026 release (per API)
- **Fields (verified, 72):** `status`, `status_detail`, `capacity_mtpa`, `production_mtpa`,
  `year_of_production`, `opening_year`, `closing_year`, `mine_type`, `coalfield`,
  `mine_name_non_eng`, `location_non_eng`, `mine_name_akas`.
- **⚠ The catalog lists no subnational/province field.** Province would have to be derived from
  coordinates (point-in-polygon, which the stdlib pipeline already does) or parsed from
  `location_non_eng`. Derived province is a derivation, and should be labelled as one.
- **⚠ No accident or incident field.** Expected, and fine: incidents come from other sources.
- **Capacity semantics:** `capacity_mtpa` (design capacity) and `production_mtpa` with its own
  year. **These are two different bases.** Pick one and use it for both numerator and
  denominator (the refinery lesson).
- **Coverage:** GEM tracks mines above a size threshold (NOT VERIFIED for the current release).
  CHN Energy alone reports 78 producing mines, and China's mine count is in the thousands, so
  completeness against NBS national output must be measured before use.
- **Decision: adopt** as a denominator candidate, with the province derivation and completeness
  caveats.

### 12c. Global Integrated Power Tracker (GIPT) — September 2026 release (per landing page)
- Unit-level for thermal; fields include capacity, status, ownership, fuel, **start year,
  retirement date** and geolocation (verified from landing page). It integrates the coal, gas,
  oil, nuclear, bioenergy, geothermal, solar, wind and hydro trackers.
- **Decision: adopt** as the generation denominator candidate, subject to the solar caveat in 12d.

### 12d. Global Solar Power Tracker — February 2026 release
- Utility-scale **≥1 MW** is tracked per facility. Distributed solar under 1 MW appears **only as
  national aggregates**, for 31 countries (verified). The page says China has "1,000+ GWac of
  operating solar".
- **Basis warning:** GEM is **AC**. NBS and NEA solar capacity (1,201.73 million kW at end-2025) is
  reported without an AC/DC qualifier. Chinese practice is commonly understood to report DC
  module capacity (**NOT VERIFIED** in this pass). Do not reconcile GEM solar to NEA solar without
  resolving this. It is the same kind of basis mismatch as refinery nameplate against
  strike-table capacity.

### 12e. GGIT / GOIT
- Already used for Russia. The provisional-snapshot caveats in `docs/SOURCES.md` §7 apply
  unchanged. GGIT also covers LNG terminals (as used for other regions; China terminal fields NOT
  VERIFIED in this pass).
- **Decision: adopt** on the same terms as Russia. GEM geometry stays un-ingested, and only
  attributes are used.

## 13. WRI Global Power Plant Database v1.3 — measured from the repo's cached copy

Computed from `data/raw/wri_gppd.csv`, rows with `country == "CHN"`:

| | WRI GPPD (CHN) | NBS, end-2025 |
|---|---:|---:|
| Plants | 4,235 | — |
| Total capacity | **1,415,067 MW** | **3,891,340 MW** |
| Solar | 54,802 MW (1,318 plants) | 1,201,730 MW |
| Wind | 50,990 MW | 640,010 MW |
| Coal | 955,718 MW | (thermal 1,539,040 MW) |
| Hydro | 259,026 MW | 448,020 MW |
| Nuclear | 33,402 MW | 62,480 MW |
| Newest `commissioning_year` | 2018 | — |
| Rows with any commissioning year | 1,086 of 4,235 | — |
| `year_of_capacity_data` populated | 0 of 4,235 | — |
| Status / retirement field | **none** | — |

WRI covers about **36% of China's end-2025 installed capacity**, and about **5% of its solar**.
Its main sources are the UNFCCC CDM registry (1,760 rows), Wiki-Solar (1,194) and GCPT (874). It is
frozen, so every Russian defect is present for China, magnified by China's growth rate.
**Decision: reject** as a denominator. Retain only as a historical cross-reference.

## 14. EIA — *Country Analysis Brief: China* (last updated May 2025)

- `https://www.eia.gov/international/content/analysis/countries_long/china/pdf/China-2025.pdf`
  (verified, text extracted with `pypdf`).
- **Key figures, with EIA's years:** total refinery capacity **19 million b/d in 2024**, and a
  government cap of 20 million b/d by 2025. Crude runs 14.2 million b/d in 2024 (about 75.5%
  utilisation). Smaller independent refineries processing imported fuel oil, "over 400,000 b/d".
  29 LNG regasification terminals with 6.2 Tcf capacity in 2023. LNG imports 3.5 Tcf in 2023.
  Underground gas storage 0.94 Tcf (aggregate). Coal production 4.8 billion short tons in 2023,
  with Shanxi at 1.4 billion short tons. "China, the world's top coal producer and consumer".
- **Basis:** EIA's refinery capacity is a **secondary** figure citing Reuters. The brief states no
  basis: nameplate or operable, CDU or total, and whether independents are included. The 2024
  cap and capacity are in **b/d**, while Chinese official policy is in **tonnes per year**, and
  the conversion depends on crude density.
- **Licence:** US federal government work. EIA describes its content as public domain (NOT
  re-verified in this pass).
- **Decision: adopt** for context only. It is a brief, not a dataset.

## 15. Energy Institute — *Statistical Review of World Energy*

- `https://www.energyinst.org/statistical-review` returned **HTTP 403** from this environment.
  Edition and terms could not be read in this pass.
- **Decision: discovery-only**, until its terms of use (attribution and redistribution of the
  consolidated dataset) are read from the source. It would be the natural single-basis
  cross-country comparator for the five-country extension.

## 16. OpenStreetMap in China

- **Legal and quality constraints** (verified from `https://wiki.openstreetmap.org/wiki/China`, a
  community summary and **not legal advice**): "private surveying and mapping activities without
  authorization" are illegal in mainland China. The page notes this "seems to outlaw the entire
  OSM project and any participation or contribution". It says enforcement may be active "near
  sensitive facilities". Mainland map services use the obfuscated **GCJ-02** coordinate system,
  and the page asks mappers not to import such data. The state imagery service (天地图 Tianditu)
  may not be used for tracing. A 2015 State Council regulation is reported to prohibit storing
  map data outside China. The legal status of *consuming* existing OSM data outside China was not
  established here.
- **Measured coverage (Overpass, 2026-10-30, `ISO3166-1=CN` admin area, counts only):**

  | Selector | Count |
  |---|---:|
  | `power=line`, voltage ≥ 500 kV (500/660/750/800/1000/1100 kV) | 21,954 ways |
  | `power=substation`, voltage ≥ 500 kV | 1,714 ways |
  | `industrial=oil_refinery` | **1** |

  These counts show that tagging exists, and nothing more. **Completeness is unknown**: there is
  no open official line-length or substation count to compare against, because CEC was
  unreachable. Given the legal position, OSM in China is more likely to be traced from imagery
  than surveyed. Its accuracy is unmeasured.
- **Safety note:** The project uses OSM for **region-level context only**. In China, OSM's
  coverage is itself shaped by state restrictions on sensitive sites. The analytic layer must
  never be used to infer what is *missing* from the map. That would be a vulnerability-style
  inference, and it is out of scope.
- **Decision: derived-facts-only.** Region-level counts and context lines are acceptable as
  display context, under ODbL. OSM is not a denominator for any sector. It should not be used for
  refineries (one feature), the same conclusion the Russia probe reached.

## 17. Natural Earth admin-1 (public domain) — measured from the repo's cached copy

From `data/raw/ne_10m_admin_1.geojson`:

- `adm0_a3 == "CHN"` has **32 features**: 22 provinces, 5 autonomous regions, 4 municipalities
  (31 provincial-level units, matching NBS's provincial frame), **plus a "Paracel Islands"
  (西沙群岛) polygon** with code `CN-X01~` and no type.
- Hong Kong (18 districts) and Macau are separate admin-0 units (`HKG`, `MAC`). Taiwan is a
  separate admin-0 (`TWN`, 22 units). NBS mainland statistics exclude all three.
- Natural Earth uses de facto boundaries by default (verified on naturalearthdata.com).
- **Name mismatches to handle in the join** (the Russian precedent is to join on a curated key,
  not on NE's codes): NE uses "Inner Mongol", while NBS English uses "Inner Mongolia". NE uses
  "Xizang", while English sources use both "Tibet" and "Xizang". NE carries `name_zh` with the
  full official names (for example 广西壮族自治区, 新疆维吾尔自治区), which is the most reliable
  join key against Chinese-language sources.
- **Scope decision needed (not taken here):** whether the Paracel Islands polygon is a monitored
  region. It is disputed territory with no energy statistics. Leaving it as context, unscored,
  follows the pattern of the four excluded annexed oblasts, where sovereignty questions are not
  settled by the index. **This is a project-owner decision.**
- **Decision: adopt**, with a curated `name_zh`-keyed crosswalk.

## 18. English Wikipedia — *List of oil refineries*, China section

- Fetched 2026-10-30. **48 entries**, and "Fushun Petrochemical Refinery" appears **twice**.
  **15 entries have no capacity figure**. Units are **mixed**: 32 in bbl/d, one (Tahe) in t/a.
  Three are flagged [citation needed]. One is listed as "closed 2006" (Anshan). Every operator
  given is Sinopec or PetroChina/CNPC, apart from one row (WEPEC Dalian) with no operator.
- **No Shandong independent (地炼 / "teapot") refinery and no large private integrated refiner**
  appears in the section. The latter is checked by name: ZPC/Rongsheng, Hengli, Shenghong and
  Yulong are all absent. Several listed capacities are implausibly small for the named complexes.
  For example, Beijing Yanshan is listed at 16,500 bbl/d. That observation is this audit's, and
  the correct figure was NOT VERIFIED.
- **Decision: reject** as a denominator. A denominator from this list would be a state-owned
  subset of unknown vintage on two unit bases, measured against a national total it cannot
  reach. That is exactly the "35 refineries is the inventory, not the denominator" problem, made
  worse.

## Out of scope — recorded so it is not re-proposed

- **Strategic and commercial oil reserve sites, and gas storage at facility level.** EIA gives an
  aggregate storage figure. Facility-level storage inventories are not pursued. They add nothing
  to regional disruption monitoring that national aggregates do not already give, and they are
  the class of asset closest to the project's scope boundary.
- **Any source whose value is location precision.** Tianditu, commercial satellite products, and
  GEM coordinates (dropped at import).
- **Commercial refinery databases** (S&P, Argus, OilChem 隆众, Sublime China Information 卓创
  and the like). These are where complete independent-refinery coverage reportedly lives. They are
  not open, not redistributable, and conflict with the project's "public, open, redistributable"
  rule. Not used.

## Cross-cutting findings

1. **Access.** Six of the primary Chinese-hosted sites tested failed from this environment:
   CEC, GACC, Sinopec, PetroChina, State Grid, and the NBS data portal. NBS press releases,
   NEA, NDRC, CSG, CHN Energy, CNOOC and NMSA were reachable. A scheduled job cannot depend on
   the failing set.
2. **Format.** The official tables that matter most are **images**: the NEA monthly table (PNG)
   and every energy table in the Statistical Yearbook (JPG). Machine-readable official data is
   limited to headline sentences in HTML press releases.
3. **Provincial breakdowns exist for output and consumption, annually and as images. No open
   provincial installed-capacity table was found** for any sector. Province-level denominators
   therefore have to come from facility inventories (GEM), not official statistics.
4. **Reliability.** Chinese energy statistics have a documented history of material revision. The
   widely reported 2015 upward revision of coal consumption followed the economic census. **Its
   magnitude was NOT re-verified in this pass, because the primary and secondary pages could not
   be fetched.** Cite it only after checking. The scope effect in source 2 is a current, verified
   instance of the same issue: two official series disagree by about 8% on 2025 electricity
   because of scope, not error.
5. **Language and naming.** NEA, NMSA, MEM, provincial bureaux and most SOE reports are
   Chinese-only. Facility names appear in up to four forms: Chinese legal entity name, pinyin,
   company English and press English. GEM's local-name fields allow a Chinese-keyed crosswalk.
   The crosswalk key should be the Chinese name, with every English form an alias, and **no
   machine translation stored as a name**.
