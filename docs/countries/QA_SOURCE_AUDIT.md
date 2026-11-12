# Qatar — source audit

Written 2026-11-11 by the Qatar source-audit lane (iteration 19, Wave A). **Nothing in this
document is wired into the pipeline or a published payload.** It records, for every candidate
source, what the source is, how it was reached today, under what terms, and whether this project
should adopt it. Incident research is a separate lane (Wave B) and was deliberately not done here.

Scope boundary applies in full (project `CLAUDE.md`, `docs/CURRENT_EVENT_PUBLICATION_POLICY.md`).
A campaign is recorded for Qatar in `data/curated/systems/conflict_campaigns.json`
(`qa-2026-attacks-on-energy-facilities`, status `uncertain`, treated as active, from 2026-01-01).
This audit therefore read **no** page about the state of any facility after an attack, and none of
its figures is later than the 2025 annual totals the publishers themselves have released.

Every figure below was read on a page, dataset or document during this session unless it is marked
**(not verified this session)**. An access failure is recorded as a finding about machine
accessibility from this machine on this date, not as proof of geo-blocking.

Companions: [QA_INDEX_READINESS.md](QA_INDEX_READINESS.md), [QA_SYSTEMATIC_SWEEP.md](QA_SYSTEMATIC_SWEEP.md),
`data/candidates/gulf19/qa_system_draft.json`, `data/candidates/gulf19/qa_profile_draft.json`.
Web searches used by this audit: **3 of 4**.

---

## 0. Summary

| # | Source | Language | Publishes | Reached today | Decision |
|---|---|---|---|---|---|
| 1 | QatarEnergy — news releases | ar, en | corporate news; statements | homepage only (latest 12); listing and item pages are script-only | **discovery only** (SOURCE_BLOCKED for enumeration) |
| 2 | QatarEnergy — sustainability reports, annual review | en, ar | annual company totals | direct PDFs answer 200 but are 31–91 MB; listing script-only | **derived facts only** (not read: over the fetch limit) |
| 3 | QatarEnergy datasets on the Qatar Open Data Portal | en, ar | annual national production and exports, 2020–2025 | yes (API, JSON) | **adopt** (national context) |
| 4 | QatarEnergy LNG (formerly Qatargas) — news archive | en | company news, 2015–2026 | yes, static paged archive | **adopt as a Wave B enumeration lane** (event search) |
| 5 | QatarEnergy LNG — sustainability reports | en | annual company totals | listing yes; PDFs over the fetch limit or HTTP 403 | **derived facts only** (not read) |
| 6 | KAHRAMAA — website news and publications listings | ar, en | nothing rendered | `www.km.qa` fails TLS; `km.qa` answers, listings empty | **reject as an event feed** |
| 7 | KAHRAMAA — Annual Statistics Report | en, ar | annual national electricity and water statistics | 2023 edition read (PDF, 7.9 MB) | **derived facts only** (restrictive site terms) |
| 8 | KAHRAMAA datasets on the Qatar Open Data Portal | en, ar | annual and monthly national electricity series | yes (API, JSON) | **adopt** (national context) |
| 9 | National Planning Council (formerly Planning and Statistics Authority) | ar, en | Qatar Monthly Statistics; annual abstract; open data | `npc.qa` only by a validating system request; `psa.gov.qa` fails TLS | **derived facts only** |
| 10 | Qatar Open Data Portal (`data.gov.qa`) | ar, en | 69 datasets matching electricity, LNG, gas or crude oil | yes (Opendatasoft API) | **adopt** (the delivery route for 3 and 8) |
| 11 | Qatar News Agency (QNA) | ar, en (+6) | official statements, including operator and ministry statements | article pages yes; listings and search are script-only | **adopt as an event-search source** (through declared queries) |
| 12 | GECF | en | Annual Statistical Bulletin; Monthly Gas Market Report | listings yes; ASB PDF 21.7 MB, over the fetch limit | **derived facts only** (not read; terms unreadable) |
| 13 | JODI Gas / JODI Oil | en | monthly national flows | yes | **derived facts only** (validation; no licence) |
| 14 | U.S. EIA Country Analysis Brief: Qatar | en | national context | yes | **adopt** (national context) |
| 15 | GCC-Stat | ar, en | GCC aggregates; energy bulletins; Marsa portal | yes | **derived facts only** (regional aggregates) |
| 16 | Al-Raya (الراية) | ar | daily newspaper | yes; dated URLs; section listing script-only | **event search — media record** |
| 17 | Al-Sharq (الشرق) | ar | daily newspaper | yes; dated URLs; paged categories | **event search — media record** |
| 18 | Al-Watan (الوطن) | ar | daily newspaper | partly; ID URLs, no date in URL | **event search — media record (discovery)** |
| 19 | The Peninsula | en | daily newspaper | yes; dated URLs; paged Energy category | **event search — media record** |
| 20 | Gulf Times | en | daily newspaper | yes; ID URLs, no date in URL | **event search — media record** |
| 21 | Reuters | en | wire | the fetch tool refuses the host | **discovery only** (SOURCE_BLOCKED) |
| 22 | S&P Global Commodity Insights | en | energy press | HTTP 403 | **discovery only** (SOURCE_BLOCKED) |
| 23 | Al Jazeera (extra, not in the brief) | ar, en | regional news | yes; dated URLs | **event search — media record (discovery)** |
| 24 | Natural Earth admin-1 | — | boundaries, 7 units | local file | **adopt**, with the ruling in §1 |
| 25 | WRI Global Power Plant Database v1.3 | en | plant list | local file | **reject** as a denominator |
| 26 | OpenStreetMap; GEM pipeline and LNG-terminal trackers | en | geometry, facility rows | not queried | **reject** for Qatar |
| 27 | Qatar Stock Exchange company disclosures | ar, en | listed-company announcements | one address tried, HTTP 404 | **not yet researched** |
| 28 | OPEC | en | — | not tried | **not applicable** as a member source (Qatar left OPEC in 2019, not verified this session) |

The single most useful finding: **the Qatar Open Data Portal publishes QatarEnergy's and KAHRAMAA's
national annual series under CC BY 4.0, through a plain JSON API.** National LNG exports, crude
production and exports, gross gas production, refinery throughput, electricity generation and peak
load all come from the operator itself, on stated units, with a licence that allows reuse. That is
better than anything found for Saudi Arabia.

The second finding is the opposite: **no Qatari body publishes event-level outage or incident
reports.** KAHRAMAA's own news and publications listings rendered empty, its statistics carry no
reliability table, and the open-data portal has no outage dataset. Events can only come from
statements carried by QNA and from the press.

---

## 1. Geography — eight municipalities, seven drawn

**Current first-level divisions: 8 municipalities (بلدية, *baladiyah*).** Official source read
today: the Qatar Open Data Portal. KAHRAMAA's dataset *Electricity Network Coverage by Municipality*
(2019–2025, CC BY) and the National Planning Council's census dataset *Distribution of Business
Establishments and Employees by Municipalities According to Census 2015* each list the same eight:

| Official English (portal) | Arabic (portal) | ISO 3166-2 | In Natural Earth |
|---|---|---|---|
| Doha | الدوحة | QA-DA | yes, as "Ad Dawhah" |
| Al Rayyan | الريان | QA-RA | yes, as "Ar Rayyān" — **drawn on its pre-2014 extent** |
| Al Wakra | الوكرة | QA-WA | yes, as "Al Wakrah" |
| Umm Slal / Umm Salal | أم صلال | QA-US | yes, as "Umm Salal" |
| Al Khor and Al Thakhira | الخور والذخيرة | QA-KH | yes, as "Al Khawr" |
| Al Shamal | الشمال | QA-MS | yes, as "Madinat ach Shamal" |
| Al Daayen | الظعاين | QA-ZA | yes, as "Al Daayen" |
| **Al Sheehaniya / Al-Shahaniya** | الشيحانية | QA-SH | **no feature** |

**Natural Earth `ne_10m_admin_1` carries 7 `QAT` features**, all `type_en = "Municipality"`
(counted from the cached file today): QA-DA, QA-RA, QA-WA, QA-US, QA-KH, QA-MS, QA-ZA. That is the
arrangement before Al-Shahaniya was separated from Al Rayyan in 2014. A point test on the cached
file places the town of Al-Shahaniya inside Natural Earth's QA-RA polygon. ISO 3166-2 added QA-SH on
2017-11-23 (read from English Wikipedia's rendering of the ISO change log, a secondary source). The
2014 creation is reported by Al-Sharq, 19 September 2014 (seen as a search result; the article was
not opened). The amending law's number was **not verified this session**.

### Rulings

1. **QA-RA is the pre-2014 Al Rayyan.** Natural Earth's Ar Rayyān polygon covers today's Al Rayyan
   **and** today's Al-Shahaniya. The system draws seven units (`units_expected: 7`). A record whose
   source places it in Al-Shahaniya is coded QA-RA at most, and its text says "Al Rayyan as drawn by
   Natural Earth, which includes Al-Shahaniya". No QA-SH geometry is invented, and no QA-SH code is
   written to a record. This is a statement about the map file, not about Qatar's administration.
2. **Kinetic and security events default to COUNTRY level.** Qatar is about 11,600 km² (not verified
   this session), and several municipalities contain a single large energy complex. Naming the
   municipality of a kinetic, sabotage or other security event would in practice name the facility.
   Such records carry `geography_precision: "country"` and `admin1_code: null`.
3. **Non-conflict events use a municipality only where a safety reviewer finds it non-identifying.**
   A grid event across Doha's customers can be placed in a municipality. A technical event at an
   industrial complex that is the only one of its kind in its municipality cannot, and stays at
   country level. The reviewer decides per record; ambiguous means country.
4. **Offshore is country level.** Offshore fields and installations fall in no municipality polygon.
   They are never snapped to the nearest coast.
5. **No disputed unit is drawn.** Natural Earth has no disputed or special feature for Qatar. This
   audit makes no statement on maritime boundaries.

### Join hazards

- Natural Earth names do not match official ones: "Madinat ach Shamal" for Al Shamal, "Al Khawr" for
  Al Khor and Al Thakhira, "Ad Dawhah" for Doha. Its Arabic names mix forms (بلدية الريان beside
  الدوحة). **Join by ISO code**, with an alias table in both scripts.
- The portal itself spells the eighth municipality three ways (Al Sheehaniya, Al-Sheehaniya,
  الشيحانية; the press also writes الشحانية and Al-Shahaniya). All map to the QA-RA ruling.
- KAHRAMAA also publishes consumption by **zone number** (a finer planning unit). Zones are never
  read: see §4.
- Sources often name a town or an industrial city instead of a municipality. Under rulings 2 and 3
  most of those resolve to country level anyway.

---

## 2. Source-by-source audit

Access tests were made on 2026-11-11 with one ordinary request each, plus the retries noted.

### 2.1 QatarEnergy — news releases

- **What it is:** the state energy company's own newsroom, `qatarenergy.qa`. Its headlines
  report the Minister of State for Energy Affairs' remarks alongside company news; he also heads
  the company (general knowledge, not read on a page today), so ministry and company statements
  appear in the same feed.
- **Language:** English and Arabic. The Arabic switch is a script postback; `/ar/Pages/default.aspx`
  answers HTTP 200.
- **Publishes:** corporate news — agreements, awards, appointments, ministerial remarks. Statements
  about operations appear in the same feed when the company chooses to make them. It is not an
  incident register.
- **How reached:** the page at `/en/MediaCenter/Pages/newsroom.aspx` returned the homepage, with a
  "Latest News" block of 12 items dated 5 July to 10 November 2026 and item addresses of the form
  `/en/MediaCenter/Pages/newsdetails.aspx?ItemId=N` (3915 to 3926 on the page). The full listing
  (`News.aspx`) and the item pages themselves (two tried) return a shell with no article: the
  content is filled in by script. **SOURCE_BLOCKED (script-only)** for enumeration. Not worked
  around.
- **Cadence:** several items a week.
- **Terms as read:** "Copyright © 2026 QatarEnergy. All rights reserved." No terms-of-use page found.
- **Fields never read:** see §4. In particular the feed carries ministerial remarks about export
  routes; those are not opened.
- **Decision: discovery only.** Releases are found through the declared queries of lane QA1 and
  read as carried by QNA, which serves them as static pages.

### 2.2 QatarEnergy — sustainability reports and annual review

- **Publishes:** an annual Sustainability Report (the 2023 edition calls itself the 14th, per a
  search-result summary) and an annual review. Company totals; safety and environment indicators.
- **How reached:** the Publications listing is script-only (an unfilled `{{LinkText}}` template in
  the raw page). Direct PDF addresses under `/en/MediaCenter/Publications/` answered a header
  request with HTTP 200: *Sustainability Report 2023* (31 MB), *QatarEnergy 2024 Sustainability
  Report* (91 MB) and its *Supplement* (69 MB). All are over the 10 MB fetch limit. **Not read.**
  No annual review PDF was located on the company's own site; search returned only third-party
  aggregator copies, which are not used.
- **Cadence:** annual, published about July–August for the prior year (from the files' dates).
- **Terms:** all rights reserved.
- **Decision: derived facts only**, once a person or a larger fetch reads them. Facts may be cited
  by link; the PDFs are not vendored. Company totals only; any facility table is never read.

### 2.3 QatarEnergy datasets on the Qatar Open Data Portal

- **What it is:** two datasets published by "Qatar Energy" on `data.gov.qa`:
  `production-qe-dataset` (*Qatar Energy Production of Crude Oil, Natural Gas and Refinery
  Throughput*) and `export-qe-dataset` (*Qatar Energy Exports of LNG, Gas, Naphta and Crude Oil*).
- **Language:** English and Arabic labels in each record.
- **Publishes:** annual national totals, 2020 to 2025: crude oil production (thousand b/d), gross
  natural gas production (BCFD), refinery throughput (thousand b/d); LNG exports (million tonnes,
  "Total annual LNG quantity exported"), pipeline gas exports (BCFD), naphtha exports, crude oil
  exports (thousand b/d).
- **How reached:** Opendatasoft API, plain JSON, no key:
  `https://www.data.gov.qa/api/explore/v2.1/catalog/datasets/<id>/records`. 18 and 24 records.
- **Cadence:** `update_frequency: ANNUAL`; both last modified 2026-08-18, carrying 2025.
- **Licence as read:** dataset metadata states `CC BY` with
  `https://creativecommons.org/licenses/by/4.0/`.
- **Limits:** one figure per product per year; no monthly series; no definition of "gross"; the
  description says crude exports cover onshore and offshore fields. No attribution of any change.
- **Decision: adopt** as the national context series for oil, gas and LNG. A year-on-year change in
  these totals is **never** an event and is never converted into a loss estimate.

### 2.4 QatarEnergy LNG (formerly Qatargas) — news archive

- **What it is:** the LNG operating company's site, `qatarenergylng.qa`.
- **Language:** English read; an Arabic edition was not tested.
- **Publishes:** company news. The items visible today are staff, safety-award and conference
  notices. Whether it carries operational statements is for Wave B to establish by enumeration.
- **How reached:** static. `/Media/News` shows 10 items per page, "Page 1 of 26" (about 260 items),
  paged at `/Media/News/pageindex563/N`, with a year category for each of 2015–2026 and item
  addresses `/Media/News/Article/ArticleID/N/slug`. **Enumerable.**
- **Cadence:** irregular; about ten items between December 2024 and November 2026.
- **Terms:** "© 2026 QatarEnergy LNG". No terms page found.
- **Fields never read:** pages that describe individual facilities. They are not opened. See §4.
- **Decision: adopt as the enumeration universe of lane QA1.**

### 2.5 QatarEnergy LNG — sustainability reports

- **Publishes:** annual report, editions 2015–2016 and 2018–2025 listed at
  `/Sustainability/Annual-Sustainability-Reports`. The homepage states a company-total LNG production
  capacity of 77 million tonnes a year.
- **How reached:** listing static. The 2024 PDF is over the fetch limit; the 2025 PDF answered a
  header request with HTTP 403. **Not read.**
- **Decision: derived facts only** — company totals (capacity, annual production, safety indicators)
  by link. **Train-by-train capacity is never recorded**, though the reports and the site publish it.

### 2.6 KAHRAMAA — website listings

- **What it is:** Qatar General Electricity and Water Corporation (كهرماء), the state transmission
  and distribution utility and single buyer.
- **How reached:** `https://www.km.qa/` failed three times ("Socket is closed"; a system request
  failed the TLS handshake). **`https://km.qa/` (no `www`) answers.** Its News page renders "No News
  Found" with a year filter that stops at 2023; its Publications page renders "No Publications
  Found". No outage or emergency notice section exists in the navigation.
- **Terms as read:** "KAHRAMAA owns all copyright in the content of this website"; printing for
  personal, non-commercial use; and "No part of this website may be reproduced on, or linked to,
  another website … without our prior written permission."
- **Decision: reject as an event feed.** The site publishes no event-level notices that a reader
  can enumerate. KAHRAMAA statements reach the public through QNA and the press (lane QA2).

### 2.7 KAHRAMAA — Annual Statistics Report

- **How reached:** direct PDF, `https://km.qa/MediaCenter/Publications/SR2023-English.pdf`
  (HTTP 200, 7.9 MB, 87 pages; found by search, since the listing is empty). Read with `pypdf`.
  Earlier editions (2012, 2018, 2020–2022) appear in search results under the `www` host, which
  fails; a 2024 edition was not located (one guessed address, 404).
- **Publishes (2023 edition):** key growth indicators; annual and monthly generation; energy
  transmitted; maximum and minimum system load; sectoral demand and consumption; customers; network
  lengths; water production, storage and demand. Table codes EWT1–10, ET1–15, WT1–28.
- **What it does not publish:** no reliability or outage table. A search of the text for SAIDI,
  SAIFI, interruption, outage and blackout found only the glossary.
- **Cadence:** annual; the 2023 edition's file is dated October 2024.
- **Terms:** the site terms in §2.6 apply; the report states its purpose is to inform "government
  institutions, investors, the academe and the general public".
- **Fields never read:** tables of capacity per producer and plant, of substations, and of
  storage per reservoir and tank. See §4.
- **Decision: derived facts only** — national totals, cited by link. Where the same figure exists
  on the open-data portal under CC BY, the portal is the source of record.

### 2.8 KAHRAMAA datasets on the Qatar Open Data Portal

- **Publishes (read today):** *Annual Electricity Generation* (2019–2025), *Maximum and Minimum
  System Load (MW)* (2019–2024, with the date of each year's peak), *Key Electricity Growth
  Indicators* (2011–2024), *Number of Electricity Customers* (2019–2024), *Total Electricity
  Consumption by Sectors* (monthly), *Electricity Network Coverage by Municipality* (2019–2025).
  The National Planning Council's *Electricity And Peak Load* adds installed capacity for 2018–2022.
- **Licence:** CC BY on every dataset listed.
- **Not published:** a search of the catalogue for outage, interruption, SAIDI and انقطاع returned
  no electricity reliability dataset.
- **Fields never read into any output:** *Contracted Capacities by IWPPs* (per-company capacity),
  *Electricity Total Consumption by Zone Number*, *Water Storage In KM Reservoirs*, and the network
  length datasets beyond a national total. See §4.
- **Decision: adopt** as national electricity context.

### 2.9 National Planning Council (NPC; formerly Planning and Statistics Authority, PSA)

- **What it is:** the official statistics body. The Planning and Statistics Authority's functions
  now sit with the National Planning Council (as the site styles itself; the date of the change was
  not verified this session).
- **How reached:** `www.npc.qa` — the fetch tool refused ("unable to verify the first certificate":
  the server does not send its intermediate certificate). An ordinary system request **with
  certificate validation on** succeeded (HTTP 200). No verification was disabled. `www.psa.gov.qa`
  fails the TLS handshake, though NPC pages still link to PDFs on it. The statistical subject pages
  and the Qatar Monthly Statistics page are script-rendered and list nothing to a plain reader.
- **Publishes:** *Qatar Monthly Statistics*. Its time-series workbook
  (`…/Qatar Monthly Statistics/QMS_PSA_Time_Series.xlsx`, 21 MB, HTTP 200) has yearly sheets from
  2018 to June 2024 and carries "Total generated electricity (GWh)" and "Total utilization of
  electricity (GWh)" by month. An annual statistical abstract exists (not reached). The site links
  to the open-data portal for datasets.
- **Cadence:** monthly bulletin; the workbook read stops at June 2024.
- **Terms as read:** all rights reserved; "When using content from the NPC's website for publishing
  or republishing, it is required to attribute the National Planning Council as the source." NPC
  datasets on the portal are CC BY.
- **Decision: derived facts only.** A monthly national electricity figure is context; a monthly dip
  with no stated cause is not an event.

### 2.10 Qatar Open Data Portal — `data.gov.qa`

- **What it is:** the government's Opendatasoft portal, Arabic and English.
- **How reached:** the HTML catalogue is script-rendered; the API answers plain requests. A
  catalogue search for electricity, LNG, natural gas, crude oil or كهرباء returned 69 datasets.
- **Licence:** per dataset, in metadata; `CC BY` 4.0 on all but one of those listed. The portal's
  licence and terms pages rendered no text to a plain reader.
- **Decision: adopt** as the delivery route for §2.3 and §2.8.

### 2.11 Qatar News Agency (QNA, وكالة الأنباء القطرية)

- **What it is:** the state news agency. It carries ministry, KAHRAMAA and QatarEnergy statements.
- **Language:** Arabic (root and `/ar-QA/`), English (`/en/`), and French, German, Spanish,
  Russian, Hindi and Urdu editions. The English and Arabic items are the same agency's text: **a
  translation is not a second source.**
- **How reached:** article pages are static and dated in the address:
  `/en/News-Area/News/YYYY-MM/DD/slug` and `/ar-QA/News-Area/News/YYYY-MM/DD/slug`. One was read in
  full. Section listings (`/en/economy`, `/ar-QA/economy`) show 12 items, all from today, with a
  script "Load More". The search page rendered "Nothing" and does not expose its parameters. **Not
  enumerable**; reached through declared search queries.
- **Hazard:** the dateline gives day and month without the year ("Doha, February 22 (QNA)"). Take
  the year from the address, never from the dateline.
- **Terms as read:** "All rights reserved for Qatar News Agency © 2021"; "Any rights not expressly
  granted herein are reserved." No reuse grant. Facts are cited by link.
- **Decision: adopt as an event-search source**, `source_role: official` for a statement it carries
  from a ministry or operator, `media` for its own reporting.

### 2.12 GECF — Gas Exporting Countries Forum

- **Publishes:** Annual Statistical Bulletin (editions 2017–2025, each a direct PDF) and Monthly Gas
  Market Report (45 editions, February 2023 to October 2026, direct PDFs).
- **How reached:** listings static. The ASB 2025 PDF answered HTTP 200 at 21.7 MB, over the fetch
  limit. **Not read.** The guessed country page returned 404.
- **Terms:** the site's Copyright page is placeholder text ("Lorem ipsum…"). Terms are unreadable.
- **Decision: derived facts only**, by a person, cited by edition. The monthly report is market
  commentary; it is read only for a production change it attributes to a disruption, and never for
  flows, cargoes or routes.

### 2.13 JODI Gas and JODI Oil

- **Publishes:** monthly national flows. Qatar is listed as a JODI-Gas participating economy, under
  GECF (88 economies listed). Its JODI-Oil participation was not found by the regional audit
  (`data/candidates/gulf19/regional_sources.md`).
- **How reached:** download pages static; CSV and `.ivt`; API with a free account.
- **Terms:** "© Copyright JODI 2026"; data "can be downloaded, for free"; no licence.
- **Decision: derived facts only**, as a cross-check on the operator's annual totals. Flows carry no
  attribution text, so JODI can never supply an event.

### 2.14 U.S. EIA — Country Analysis Brief: Qatar

- **How reached:** `https://www.eia.gov/international/content/analysis/countries_long/qatar/`,
  static HTML. **Last updated 20 October 2025.**
- **Read today:** primary energy production 10.0 quadrillion Btu in 2023 (67.5% natural gas, 32.5%
  crude oil and other petroleum liquids; coal marked "--", not applicable); petroleum liquids 1.9
  million b/d in 2024; natural gas exports 4.4 Tcf in 2024, of which nearly 0.8 Tcf by pipeline and
  3.6 Tcf as LNG (preliminary); total LNG nameplate export capacity 3.7 Tcf/y at end-2024;
  generation capacity 11.4 GW and net generation 56 TWh in 2023; refining capacity 443 thousand b/d
  for crude and condensate in 2025 (Table 4 total); dry gas consumption 1.7 Tcf in 2024.
- **Terms:** U.S. government work, public domain. Tables credited to others carry their terms.
- **Fields never read:** the brief has plant and train tables and a section on export routes. Only
  national totals are taken. See §4.
- **Decision: adopt** as national context and as the independent cross-check on operator totals.

### 2.15 GCC-Stat

- **How reached:** `gccstat.org` (Arabic by default; `/lang/en`). Publications listing static, 886
  items over 99 pages. Weekly Bulletin 344 (energy, 22 October 2026, one page) was read: it gives
  GCC aggregates credited to OPEC, with no row for Qatar.
- **Terms as read:** content may be copied, used, published, translated or modified with the GCC
  Statistics Center cited; modified content must say so; third-party rights are the user's to clear.
- **Decision: derived facts only**, for regional aggregates. For Qatar the national sources above
  are closer to origin; GCC-Stat names OPEC, OAPEC, GECF and IRENA among its inputs (regional audit).

### 2.16–2.20 Domestic newspapers — record roles

All five are Doha dailies. Domestic papers commonly carry QNA text (how often was not measured
here); a newspaper item that repeats a QNA statement is a syndicated copy, not a second source.

| Paper | Language | Publisher as read today | Address pattern | Enumeration | Terms as read | Role |
|---|---|---|---|---|---|---|
| Al-Raya, `raya.com` | ar | footer: شركة الخليج للنشر والطباعة (Gulf Publishing and Printing) | `/YYYY/MM/DD/slug` (dated) | section listing is an unfilled script template; archive-search form with date range, parameters not exposed | terms page linked, not read | media record; Arabic event search |
| Gulf Times, `gulf-times.com` | en | terms name Gulf Publishing and Printing Company | `/article/ID/section/slug` (no date) | search form with date range, parameters not exposed; RSS | personal, non-commercial use; no copying without written consent | media record; English event search |
| Al-Sharq, `al-sharq.com` | ar | footer: جريدة الشرق; The Peninsula's page names the Dar Al-Sharq group | `/article/DD/MM/YYYY/slug` (dated, day first) | categories paged, `/category/محليات/N`; over 10,000 pages for local news | "جميع الحقوق محفوظة"; terms page linked, not read | media record; Arabic event search |
| The Peninsula, `thepeninsulaqatar.com` | en | footer credits Al Sharq Technology; Dar Al-Sharq group | `/article/DD/MM/YYYY/slug` (dated, day first) | Energy category paged, `/category/Energy?page=N`, 65 pages of 18 | "Copyright © 2026 The Peninsula" | media record; **an enumerable English energy listing** |
| Al-Watan, `al-watan.com` | ar | not shown on the page read | `/article/ID/section/slug` (no date) | none found | not shown | media record; discovery only |

**Independence.** Al-Raya and Gulf Times share a publisher. Al-Sharq and The Peninsula share a
group. A pair from the same house counts as **one** source for an event, as does any pair that both
reproduce QNA.

**Date hazards.** Al-Sharq and The Peninsula write the day first (`/article/19/09/2014/`); Al-Raya
writes the year first. Gulf Times and Al-Watan addresses carry no date, so the publication date must
be read from the page.

### 2.21 Reuters

The fetch tool refuses the host outright ("unable to fetch from www.reuters.com"). **SOURCE_BLOCKED.**
Discovery through search results only; a Reuters item seen only as a search result is recorded
`opened: false`.

### 2.22 S&P Global Commodity Insights

HTTP 403 on the LNG news listing. **SOURCE_BLOCKED.** Discovery through search results only.

### 2.23 Al Jazeera (extra)

`aljazeera.com/where/qatar/` renders 19 items with dated addresses (`/news/YYYY/MM/DD/slug`) and a
script "Show more". "© 2026 Al Jazeera Media Network". Funded by the State of Qatar (not verified
this session). Its Qatar listing is mostly regional war coverage. **Event search — media record,
discovery.** Never read for routes or shipping.

### 2.24 Natural Earth admin-1

Public domain. Seven features. **Adopt**, with the ruling in §1 and a join by ISO code.

### 2.25 WRI Global Power Plant Database v1.3

Counted from the cached file: 12 `QAT` rows, 10,548 MW, all gas, source "GEODB", no commissioning
year on any row, no solar. **Reject** as a denominator: undated, and KAHRAMAA's own annual list is
the primary source it approximates.

### 2.26 OpenStreetMap; GEM pipeline and LNG-terminal trackers

Not queried. **Reject for Qatar.** No pipeline, grid or terminal geometry is drawn for this system:
there is no measure it would support, and in a country this small it would be a facility map.

### 2.27 Qatar Stock Exchange disclosures

Listed affiliates of the state energy company and the listed power-and-water producer file
announcements there. One guessed address returned 404; the site was not explored. **Not yet
researched.** If it is, it is read for occurrence only, like the Tadawul lane for Saudi Arabia.

---

## 3. Reporting bias, in neutral words

- **Ownership.** The oil, gas and LNG operator and the electricity and water utility are both
  state-owned and report to the same minister. The news agency is a state body. The five daily
  newspapers come from three publishing houses.
- **Disclosure rule.** No law or regulator was found that requires public outage reporting. An
  event is public when the operator, the ministry or the Ministry of Interior chooses to issue a
  statement, or when it is visible to customers or to trading counterparties.
- **Who reports from outside.** LNG and condensate trade is followed closely by wire services and
  the energy press, so an event that changes deliveries tends to be reported abroad. An event that
  changes only domestic supply has no such audience.
- **Language.** Official statements are issued in Arabic and English by the same agency. The
  Arabic press carries more local detail on electricity and water; the English press more on LNG.
- **Conflict.** For the 2026 attacks, parties to a war and the state concerned are the main
  sources. Statements may be made for effect, and outlets repeat one another. Publisher count
  overstates certainty.
- **Small-country effect.** With few facilities, almost any event description identifies a site.
  That is why this system records kinetic events at country level (§1).

## 4. Fields that must never be read

From any source, public or not:

- train-by-train LNG capacity, and any train's status, restart date, repair progress or operating
  rate; the same for any plant, unit, terminal, berth or pipeline;
- any measure of another country's or buyer's dependence on Qatari LNG, on particular trains, or on
  a shipping route; cargo, tanker, AIS, destination or diversion material; any Strait of Hormuz,
  bypass or "alternative route" material, including ministerial remarks on it;
- which facility is described as largest, key, critical or sole;
- coordinates, distances, ranges, weapon or attack-method detail, air or site defences;
- pipeline routes, landfalls and interconnector status; grid topology, including any substation
  table, cable and line datasets beyond a national total, and consumption by zone;
- per-producer and per-plant contracted capacity in any output file;
- water storage by reservoir, tank or tower;
- pages on an operator's site that describe individual facilities.

For a kinetic or sabotage record from 2026-01-01: occurrence, date, broad class and the effect
reported within 7 days only. Nothing later, and no page whose address or title states later status.

## 5. Low reported incidents is not low disruption

The number of Qatari incidents this project will find is a property of the reporting environment:
two state operators under one minister, a state news agency, no outage register, no reliability
statistics, a utility website whose news and publications listings render empty, and a statistics
series that is annual and unattributed. Technical trips, partial shutdowns and local outages are
the least likely to surface. Before 2026 the public record may contain very little, and that would
say nothing about how reliably the system ran.

The dashboard must therefore never render a sparse Qatar record as "low disruption". The correct
reading is **"low reported disruption, coverage unknown"**. National annual totals (LNG exported,
electricity generated) are context. When a 2026 total is published it may differ from 2025; that
difference is not a capacity-loss estimate and must not be turned into one.

Three absences stay distinct here as everywhere: **unknown** (reliability indicators exist inside
the utility and are not published), **not applicable** (coal), and **not yet researched** (the
stock-exchange disclosures; the QatarEnergy and QatarEnergy LNG report PDFs; gas storage).

## 6. Attribution string if adopted

> National oil, gas and LNG series: **QatarEnergy, Qatar Open Data Portal**, CC BY 4.0. National
> electricity series: **KAHRAMAA, Qatar Open Data Portal**, CC BY 4.0. National context: **U.S.
> EIA** (public domain). Boundaries: **Natural Earth** (public domain), seven municipalities as
> drawn; Al-Shahaniya is shown within Al Rayyan.
