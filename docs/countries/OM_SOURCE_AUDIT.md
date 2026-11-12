# Oman — source audit

Written 2026-11-11 by the Oman source-audit lane (iteration 19, Wave A). **Nothing in this document
is wired into the pipeline or a published payload.** It records, for every candidate source, what
the source is, what it publishes, how it can be reached by ordinary access, under what terms, and
whether this project should adopt it. Incident research is Wave B and is deliberately not done here.

Scope boundary applies in full (project `CLAUDE.md`, `docs/CURRENT_EVENT_PUBLICATION_POLICY.md`
§1-§3, `data/candidates/gulf19/AGENT_BRIEF.md`). Infrastructure appears here only as public
descriptive context at governorate level or coarser. This audit does not assess the importance,
vulnerability, protection, interdependence or routing of any facility, and it records no facility
capacity.

Every figure below was read on a page or document during this session unless it is marked
**(not verified this session)** or attributed to a file already committed in this repository. Each
"how reached" entry is the result of one ordinary WebFetch on 2026-11-11. Where a site returned an
empty shell, a certificate error or a refusal, that is recorded as a finding about access and was
not worked around.

Web searches used by this audit: **4 of 4** (two English, two Arabic), all to locate report
endpoints. None was an incident query.

---

## 0. Summary

| Source | Language | Sector(s) | Reached 2026-11-11 | Decision |
|---|---|---|---|---|
| NCSI Monthly Statistical Bulletin | ar+en (one bilingual PDF) | oil, gas, refining output, electricity, national | yes: static PDF | **adopt** (national context) |
| NCSI data portal (data.gov.om) | ar+en | national series | partly: shell readable, datasets script-loaded | **derived facts only** |
| Nama Power and Water Procurement: annual report, 7-Year Statement | en (ar editions exist) | generation, demand | yes: static listing, PDFs | **adopt** (facts only) |
| Oman LNG annual reports | en (ar editions exist) | LNG | yes: static listing, PDFs 2009-2024; 2025 is a web page that returned no body text | **adopt** (facts only) |
| PDO sustainability report | en | upstream | PDO site script-only; report PDFs reached on the parent company's site (edoman.om) | **derived facts only** |
| OQ group: annual reports, newsroom | en, ar, zh | refining, petrochemical, upstream, gas | yes: static report list; newsroom first page static, rest behind "Load more" | **derived facts only**; newsroom **discovery only** |
| OQ Exploration and Production (listed) | en, ar | upstream | report list readable, document links not exposed; announcements list empty to a fetch | **derived facts only** |
| OQ Gas Networks (listed) | en, ar | gas transmission | **SOURCE_BLOCKED**: country selector and terms-acceptance gate | **discovery only** (not read) |
| OQ Refineries / OQ8 | en | refining | reached only through the OQ newsroom; OQ8 site not fetched | **derived facts only** |
| Muscat Stock Exchange disclosures | ar+en | listed-company disclosures | listing script-loaded (empty to a fetch); RSS returns the current day only | **discovery only** |
| Ministry of Energy and Minerals (mem.gov.om) | ar+en | policy, annual report, statistics | **SOURCE_BLOCKED**: script-only shell (title only) | **discovery only**; its figures are adopted through NCSI |
| Authority for Public Services Regulation (apsr.om) | ar+en | electricity regulation | **SOURCE_BLOCKED**: script-only shell (the text "APSR" only) | **discovery only** until a report is readable |
| Oman Electricity Transmission Company (omangrid.com) | ar+en | transmission | site reached, annual-report and publication listings empty | **discovery only**; national totals only, if ever read |
| Oman News Agency (omannews.gov.om) | ar+en | official news | **SOURCE_BLOCKED**: TLS certificate chain error on every address tried | **discovery only** (through syndication in the press) |
| JODI Oil / JODI Gas | en | monthly national flows | yes | **adopt** (national context series) |
| U.S. EIA International Energy Statistics | en | national context | already committed in this repository (bulk file release 2026-10-16) | **adopt** as the existing context layer; nothing new |
| U.S. EIA country analysis brief: Oman | en | national context | yes: last updated 2019-01-07 | **reject** for figures (stale); discovery only |
| GCC-Stat | ar+en | regional statistics | home page yes; energy page 404; data-portal host did not resolve | **derived facts only** (nothing read yet) |
| Oman Daily (جريدة عمان) | ar | news | yes: static, paged section listings | **event search** (state-published) |
| Oman Observer | en | news | yes: static, paged energy section | **event search** (state-published) |
| Al-Watan (الوطن) | ar | news | yes | **event search** (private) |
| Al-Shabiba (الشبيبة) | ar | news | yes | **event search** (private) |
| Times of Oman | en | news | yes: static, paged category listings | **event search** (private) |
| Muscat Daily | en | news | **SOURCE_BLOCKED**: HTTP 403 | **event search** only through search results; pages not opened |
| Reuters | en | wire | **SOURCE_BLOCKED**: the fetch tool refuses the host | **event search** through search results only |
| S&P Global Commodity Insights | en | trade press | **SOURCE_BLOCKED**: HTTP 403 | **event search** through search results only |
| attaqa.net (الطاقة) | ar | trade press | seen in search results, not opened | **discovery only** |
| WRI Global Power Plant Database v1.3 | en | generation | cached in this repository | **reject** as denominator |
| Third-party report aggregators (e.g. sustainabilityreports.com) | en | company reports | seen in search results, not opened | **reject** |
| decree.om / qanoon.om (private legal databases) | en / ar | law text | decree.om reached | **discovery only** (unofficial translation) |
| Natural Earth admin-1 | — | boundaries | cached in this repository | **adopt**, with two code rulings |

The main finding: **Oman publishes good national statistics under an open licence and good annual
company reports, and almost no event-level outage record that an ordinary fetch can reach.** The
ministry, the electricity regulator and the national news agency all failed ordinary access on this
date, for three different technical reasons. What they say reaches a reader mainly through the
state-published and private press, which is readable.

---

## 1. Geography — the 11 governorates (محافظات, *muḥāfaẓāt*)

**Current official division: 11 governorates.** Read this session in the National Centre for
Statistics and Information's *Monthly Statistical Bulletin*, October 2026, Table 1 ("Total
Population Registered by Governorate and Nationality"), which lists exactly eleven: Muscat, Dhofar,
Musandam, Al Buraymi, Ad Dakhliyah, Al Batinah North, Al Batinah South, Ash Sharqiyah South, Ash
Sharqiyah North, Adh Dhahirah, Al Wusta. The legal basis is Royal Decree 114/2011 (administrative
division) and Royal Decree 36/2022 (System of Governorates); both were located on a private
translation database (decree.om), which shows the decree titles and Official Gazette references
but not the attached lists, so **the count rests on the NCSI table, not on the decree text**. The
official Arabic decree text was not read this session.

Natural Earth `ne_10m_admin_1` (cached at `data/raw/ne_10m_admin_1.geojson`) carries **11 `OMN`
features**. The count matches. The codes and labels do not all match:

| Natural Earth `iso_3166_2` | Natural Earth `name` | Arabic (official short form) | Current ISO 3166-2 | Note |
|---|---|---|---|---|
| OM-MA | Muscat | مسقط | OM-MA | |
| OM-ZU | Dhofar | ظفار | OM-ZU | three parts: mainland and two offshore island polygons |
| OM-MU | Musandam | مسندم | OM-MU | two parts, see below |
| OM-BU | Al Buraymi | البريمي | OM-BU | |
| OM-DA | Ad Dakhliyah | الداخلية | OM-DA | |
| **OM-BA** | Al Batnah North | شمال الباطنة | **OM-BS** | Natural Earth keeps the code of the former undivided Al Batinah region |
| OM-BJ | Al Batnah South | جنوب الباطنة | OM-BJ | |
| **OM-SH** | Ash Sharqiyah South | جنوب الشرقية | **OM-SJ** | Natural Earth keeps the code of the former undivided Ash Sharqiyah region |
| OM-SS | Ash Sharqiyah North | شمال الشرقية | OM-SS | |
| OM-ZA | Al Dhahira | الظاهرة | OM-ZA | |
| OM-WU | Al Wusta | الوسطى | OM-WU | |

ISO codes are as listed on the English Wikipedia page *ISO 3166-2:OM* (read this session; the ISO
Online Browsing Platform itself was not opened). That page records that on 2015-11-27 OM-BA became
OM-BJ, OM-SH became OM-SJ, and OM-BS and OM-SS were added.

**Join hazards:**

- **OM-BA and OM-SH are stale codes carrying current polygons.** Natural Earth's OM-BA polygon is
  Al Batinah *North* (ISO OM-BS); its OM-SH polygon is Ash Sharqiyah *South* (ISO OM-SJ). A source
  that uses current ISO codes will not join on the code for these two. Worse, ISO's own change
  moved the old OM-BA code to the *South* (OM-BJ), so a naive "old code → new code" mapping sends
  North Batinah events to South Batinah. Join these two by name, through an alias table, never by
  code.
- Natural Earth spells Batinah **"Al Batnah"** and gives OM-SH the Arabic label
  **"المنطقة الشرقية"** (the name of the former undivided region; it also reads as Saudi Arabia's
  Eastern Province). Its `type_en` calls seven of the eleven "Region" (*Mintaqah*). All eleven
  have been governorates since 2011.
- English spellings vary across sources read this session: Dakhliyah / Dakhiliyah / Dhakiliya,
  Dhahirah / Dhahira / Ad Dhahira, Buraymi / Buraimi, Sharqiyah / Sharqiah / Sharqiya. The alias
  table needs English and Arabic forms.
- Reports often name a town or wilayat rather than the governorate. The alias table must resolve
  those to governorates; nothing finer than a governorate is recorded.

**Musandam (OM-MU)** is a governorate that is not contiguous with the rest of Oman. Natural Earth
draws it as two polygons. The smaller one is the wilayat of Madha, which belongs to Musandam
governorate and is surrounded by the United Arab Emirates; that polygon has an interior hole, and
Natural Earth draws the area inside the hole (Nahwa) with Sharjah, UAE. The geometry is therefore
correct for this project's purpose and needs only a note: an event reported in Madha is a Musandam
event. No other treatment is needed and none is given.

**No disputed area was found** in Natural Earth's Oman features.

**Electricity statistics do not use the 11 governorates.** Three groupings were read this session,
and they differ:

- NCSI's bulletin (Table 21, source: APSR) reports electricity production in eight rows: Muscat,
  Dhofar, Musandam, Ad Dakhliyah, "Al Batinah & Adh Dhahira" (three governorates merged), "Ash
  Sharqiya" (two merged), Al Wusta, and "Others".
- Nama PWP reports purchases and bulk supply by three power systems (Main Interconnected System,
  Dhofar Power System, Musandam Power System) and, inside the main system, bulk supply for nine
  named governorates.
- Al Buraymi has no row of its own in the NCSI production table.

A regional electricity figure for all eleven governorates therefore cannot be read off one official
table. This is the Omani form of the problem recorded for Saudi Arabia's four operating areas.

---

## 2. Source-by-source audit

"Raw redistribution" means: may this project vendor and republish the source file itself, not
merely cite facts from it.

### 2.1 National Centre for Statistics and Information (NCSI) — Monthly Statistical Bulletin

- **What it is:** the national statistics office. Monthly bilingual (Arabic and English, one PDF)
  bulletin. October 2026 issue read:
  `https://api.ncsi.gov.om/uploads/pdfs/monthly_statistical_bulletin__october_2026_1792489912.pdf`
  (36 pages, 3.9 MB, text extracts with `pypdf`).
- **What it publishes:** Table 9 oil and gas (oil production, daily average, total exports; gas
  supply split associated / non-associated plus imports; gas use by power generation, industrial
  areas, industrial projects, oil fields), source stated as the Ministry of Energy and Minerals.
  Table 10 refinery output, domestic sales and exports by product, with the note "The data
  represents all refineries". Table 21 electricity gross and net production by the eight groupings
  in §1, source stated as APSR. Each table gives the last three months, year-to-date for two
  years, and the previous full year. **No event-level content, no facility rows.**
- **Figures read (2025 full year, marked provisional):** oil production 365,754.4 thousand barrels
  (daily average 1,002.0 thousand b/d); total oil exports 307,960.9 thousand barrels; gas supply
  (local production plus imports) 57,055.6 million m³, of which power generation used 15,494.3;
  electricity gross production 50,973.5 GWh, net 49,532.4 GWh.
- **How reached:** `ncsi.gov.om` home page static; the current bulletin is linked from it;
  `/publications` is a static paged listing (313 pages) with a classification filter. A complete
  list of back issues was not enumerated this session.
- **Cadence:** monthly, about six weeks after the reference month.
- **Licence (read in full, Arabic PDF `ncsi.gov.om/assets/docs/gov_license.pdf`):** "رخصة استخدام
  البيانات المفتوحة" (open data use licence). Grants use and re-use for any commercial or
  non-commercial purpose; copying, publishing, distributing, processing; combining with other data.
  Requires clear attribution to the original source and disclosure of any modification; forbids
  implying official endorsement. Excludes personal data, official logos, third-party intellectual
  property and classified data. States that it is compatible with CC BY 4.0.
- **Raw redistribution:** **yes**, with attribution and change-marking.
- **Bias:** national aggregates; preliminary figures are revised; a monthly dip carries no cause.
- **Never read as:** an incident source. A fall in a monthly series with no stated cause is not an
  event (brief, evidence rules).
- **DECISION: adopt** as the national context series, and as the route by which the Ministry's and
  the regulator's statistics are actually reachable.

### 2.2 NCSI data portal (data.gov.om)

- Readable shell with topic links (an "Electricity" topic links to a search page); key indicators
  and dataset bodies are script-loaded and were empty to a fetch. Same open licence.
- **DECISION: derived facts only.** Use the bulletin PDFs instead; open a dataset by hand only to
  settle a specific figure.

### 2.3 Ministry of Energy and Minerals (وزارة الطاقة والمعادن, mem.gov.om)

- **What it is:** the sector ministry; publishes an annual report and news. Omani press articles
  seen in search results cite "the Ministry's annual report" for reserves, export and drilling
  figures, so the report exists **(report itself not read this session)**.
- **How reached:** `https://mem.gov.om/en-us/` redirects (301) to `http://mem.gov.om/`, which
  returns a page whose only text is the title "MEM - الصفحة الرئيسية". Deeper addresses redirect
  to the same shell. **SOURCE_BLOCKED (script-only).** One Arabic search for the annual report PDF
  returned press coverage and trade press, not a ministry address.
- **Licence:** not readable.
- **DECISION: discovery only.** Its statistics are adopted through NCSI Table 9 and Table 10,
  which name it as source. Its statements are looked for in the press (lane OM1, OM5).

### 2.4 OQ group (OQ SAOC) — annual reports, financial statements, newsroom

- **What it is:** Oman's integrated energy group (upstream, refining, petrochemical, gas network,
  trading; the site's own words are "global integrated energy company"). Site `oq.com`, English,
  Arabic and Chinese.
- **What it publishes:** annual reports 2021-2025 and mid-year reports 2021-2022; consolidated
  financial statements half-yearly from 2020; a newsroom of 96 articles with a year filter
  2019-2026 and category and topic filters. One newsroom release was read (20 January 2026, OQ
  Refineries and Petroleum Industries performance in 2025): company aggregates only (crude
  refined: 93 million barrels in 2025), and it reports no unplanned shutdown or incident. On this
  sample the newsroom is an achievements feed.
- **How reached:** `oq.com/en/investors/financial-statements-and-reports` is a static list with
  direct PDF addresses on `assets.oq.com`. The 2025 annual report PDF exceeds the fetch tool's
  10 MB limit and was **not read**. The newsroom's first ten items are static; older items sit
  behind a "Load more" control.
- **Cadence:** annual; half-yearly financials; irregular news.
- **Licence:** "©2026 OQ SAOC. All rights reserved." The Disclaimer page read this session covers
  product information only and grants no re-use right. **Raw redistribution: no.**
- **Bias:** company presentation; turnarounds described as achievements; no outage reporting seen.
- **DECISION: derived facts only** for annual-report aggregates; **discovery only** for the
  newsroom.

### 2.5 OQ Exploration and Production SAOG (listed, MSX)

- `oqep.om`. Reports page lists Annual Report 2024 and 2025 and quarterly results, statements,
  earnings releases and session transcripts from the 2024 listing onward, with dates but without
  document addresses in the returned text (download icons only). The Announcements page returned
  no entries to a fetch. English and Arabic.
- **Licence:** "Copyright © 2026, All rights reserved. OQEP." **Raw redistribution: no.**
- **DECISION: derived facts only.** Wave B opens individual documents only where a document
  address can be obtained by ordinary access.

### 2.6 OQ Gas Networks SAOG (listed, MSX)

- `oqgn.om`. Owns and operates the gas transmission network. Investor pages (disclosures,
  financial information) sit behind a country selector and a disclaimer that must be accepted;
  the page returned no disclosure list. **SOURCE_BLOCKED (terms-acceptance gate).** Accepting
  terms on the owner's behalf is not something a research lane does.
- **Never read from this source, even if it becomes reachable:** network maps, route descriptions,
  station lists, pressure or flow by segment. Only company-level disclosures of a material
  interruption (that one occurred, its date, the effect reported at the time) are in scope.
- **DECISION: discovery only**, not read.

### 2.7 OQ Refineries and Petroleum Industries; OQ8 (Duqm)

- No separate report archive was reached for either. OQ RPI appears through the OQ group reports
  and newsroom (§2.4). A sustainability report for OQ8 appeared in search results on `oq8.om`; the
  site was not fetched.
- **DECISION: derived facts only.** See `OM_INDEX_READINESS.md` §1 for what this means for a
  refining inventory.

### 2.8 Muscat Stock Exchange (msx.om) — company disclosures

- **What it is:** the exchange on which OQ Gas Networks SAOG and OQ Exploration and Production
  SAOG are listed, and where listed power and water companies disclose **(the list of listed
  energy issuers was not read this session)**.
- **How reached:** home page static. The disclosure listing
  (`newsbytype.aspx?type=1&month=M&year=YYYY`) returned filter controls and no items (script
  loaded). The RSS feed `rss.aspx?t=Company` returned 20 items, all dated the current day, with
  generic titles and "refer to the attached file": no history and no issuer in the title.
- **Licence:** "© Copyrights 2026, Muscat Stock Exchange. All Rights Reserved"; a Disclaimer and
  Terms of Use PDF is linked and was not read.
- **DECISION: discovery only.** There is no ordinary-access route to a dated, per-issuer
  disclosure history. This is the Omani equivalent of the Tadawul limitation recorded for Saudi
  Arabia.

### 2.9 Petroleum Development Oman (PDO)

- **What it is:** an oil and gas producer, listed as a subsidiary on the site of Energy
  Development Oman. By the figures read this session its 2025 oil production was about 70% of the
  national figure (computed: 705,539 b/d against 1,002.0 thousand b/d).
- **How reached:** `pdo.co.om` home page static, but the Publications and Latest News pages return
  "Loading..." placeholders. **Script-only for listings.** One search located PDO Sustainability
  Reports for 2022 and 2025 as PDFs on `edoman.om`, the site of PDO's parent, Energy Development
  Oman, which lists PDO as a subsidiary: a legitimately published copy from the same body. The
  2025 report (55 pages, 7 MB) was fetched and read.
- **What it publishes:** company aggregates (2025: average oil production 705,539 b/d, condensate
  76,944 b/d, sales gas 47.54 million m³/day, about 1.1 million boe/d in total); process-safety
  incident counts by tier; a narrative that mentions "deferments" and facility availability
  without dated events. **No dated outage record.** No annual report distinct from the
  sustainability report was found.
- **Cadence:** annual (2025 edition dated August 2026 by its address).
- **Licence:** no licence text in the report; corporate copyright. **Raw redistribution: no.**
- **Never read as:** field-level or station-level production; the report names fields in its
  technology sections and none of that is recorded.
- **DECISION: derived facts only.**

### 2.10 Oman LNG

- **What it is:** the LNG producer. Its 2024 report counts Qalhat LNG cargoes together with its
  own and speaks of the "total complex".
- **How reached:** `omanlng.co.om/en/Pages/annual-reports.aspx` is a static list of 17 annual
  reports, 2009-2025, with direct PDF addresses for 2009-2024. The 2024 edition ("Outlook 2024",
  12 pages) was read. The 2025 edition is a web page of tabbed sections that returned navigation
  only. Sustainability reports (English and Arabic, 2025) appeared in search results on the same
  host and were not opened.
- **What it publishes:** annual production (2024: 11.98 million tonnes, described as the highest
  in the company's history), reliability and utilisation percentages, cargo counts, safety
  statistics. Short, promotional editions. **No dated interruption record** in the edition read.
- **Cadence:** annual, about mid-year.
- **Licence:** "Oman LNG © 2020 All Rights Reserved." **Raw redistribution: no.**
- **Never read:** cargo destinations, vessel or charter detail, anything about shipping routes.
- **DECISION: adopt (facts only)** for national LNG context; the annual reports are the lane OM3
  enumeration universe.

### 2.11 Nama Power and Water Procurement (PWP; formerly OPWP)

- **What it is:** the single buyer of power and water capacity. Site `omanpwp.om`, English and
  Arabic.
- **How reached:** static listings. Annual reports 2020-2025 on the first of four pages
  (`/annual-report`); 7-Year Statements for 2025-2031 and 2026-2032 (`/7-year-statement-
  electricity`) with an archive page for earlier issues. Both current documents were read: Annual
  Report 2025 (64 pages) and 7-Year Statement 2026-2032, Issue 20 (22 pages).
- **What it publishes:** system-level demand history and forecast (2025: main system peak
  7,863 MW and about 43 TWh; Dhofar system peak 850 MW and 5.5 TWh), renewable share of
  production (about 9% in 2025), fuel efficiency, energy purchased by system (2025: 43,826 GWh,
  5,475 GWh and 395 GWh for the three systems), a per-plant purchase figure, and bulk supply by
  governorate for the main system. **No outage or blackout narrative** was found in either
  document.
- **Cadence:** both annual.
- **Licence:** "Copyright © 2024 Nama Power and Water Procurement. All Rights Reserved."
  **Raw redistribution: no.**
- **Never read:** the interconnection and transmission-reinforcement passages of the 7-Year
  Statement, the site's "project locator", and any per-plant capacity. Per-plant energy rows exist
  in the annual report and are not copied into any output of this project.
- **DECISION: adopt (facts only)** for national electricity context; enumeration universe for
  lane OM4.

### 2.12 Oman Electricity Transmission Company (OETC, omangrid.com)

- **How reached:** home page static. `/en/Pages/Annual-Reports.aspx` returned the heading and no
  entries; `/en/Pages/Publications.aspx` returned headings only; the sitemap page reported a
  navigation error. No annual report was read. A sustainability report appeared in search results
  on a third-party aggregator and was not opened.
- **Licence:** "Copyright © Oman Electricity Transmission Company S.A.O.C All Right Reserved."
- **Never read, by task instruction and by the brief:** line-level, station-level, constraint or
  capability-statement data; the home page's project list. If an annual report becomes reachable,
  only national totals are taken.
- **DECISION: discovery only.** Nothing adopted.

### 2.13 Authority for Public Services Regulation (APSR, هيئة تنظيم الخدمات العامة)

- **What it is:** the electricity, water and gas-transmission regulator; licenses the sector and
  investigates major supply interruptions. It is the stated source of NCSI's electricity table.
- **How reached:** `apsr.om` (home, `/en/home`, `/en/annualreports`, `/en/publications`) returns a
  page whose only text is "APSR". **SOURCE_BLOCKED (script-only).** One English and one Arabic
  search for its annual report or an investigation report returned no APSR-hosted document. The
  English search did return Oman Observer and Times of Oman reports of APSR statements about
  outages, which establishes the route by which the regulator's findings reach the public:
  **statements carried by the press**, not a document this lane could open.
- **What is not established:** whether APSR publishes investigation reports, and whether its
  annual report carries interruption statistics. Both are **not yet researched**, not "none".
- **DECISION: discovery only** today. If a person can open an APSR annual report or investigation
  report in a browser, it becomes the best single Omani source for clauses 4 and 5 and the
  reporting environment should be re-read (see §3).

### 2.14 Oman News Agency (ONA, omannews.gov.om)

- **How reached:** every address tried (`omannews.gov.om/`, `www.omannews.gov.om/`,
  `/topics/en/`, `/topics/ar/`) failed with "unable to verify the first certificate".
  **SOURCE_BLOCKED (TLS chain).** Not worked around.
- **Consequence:** ONA text is reachable only as syndicated copy in Oman Daily, Oman Observer,
  Times of Oman and others. A syndicated copy is one source, not several (brief, evidence rules).
- **DECISION: discovery only.**

### 2.15 JODI Oil and JODI Gas

- Oman is listed as a participating economy in both (JODI-Gas lists it in the GECF group). Latest
  JODI-Oil update seen: 21 October 2026, with August 2026 data. Annual CSV downloads; footer
  "© Copyright JODI 2026", no licence text.
- **Raw redistribution:** unclear; store derived Omani series with citation only.
- **DECISION: adopt** as a monthly national context series, as for Saudi Arabia. Never an index
  input; a monthly dip is not an event.

### 2.16 U.S. EIA

- **International Energy Statistics:** already the source of this repository's global context
  layer (`data/curated/global_context/energy_context.json`, bulk release 2026-10-16, comparison
  year 2024). The Oman row there reads, among others: coal production 0.0 million tonnes,
  coal-fired generation 0 TWh, coal consumption 0.03 million tonnes. Public domain. **Adopt** as
  it stands; this audit adds nothing to it.
- **Country analysis brief, Oman:** reachable, **last updated 7 January 2019**, figures for 2017,
  and one visible unit error in its gas-production sentence. **Reject** for figures; discovery
  only.

### 2.17 GCC-Stat (المركز الإحصائي الخليجي)

- Home page readable (regional headline indicators; publications; a data portal named "Marsa").
  The energy statistics address tried returned 404 and the data-portal host did not resolve.
  Terms of Use are linked and were not read.
- **DECISION: derived facts only**; nothing read. NCSI is the primary for every Omani figure
  GCC-Stat would carry.

### 2.18 Omani press — record roles

| Outlet | Language | Publisher (as stated on the site) | Reached | Enumeration |
|---|---|---|---|---|
| Oman Daily (جريدة عمان) | ar | Ministry of Information | yes | `/morearticles/<section>?pgno=N`, 20 per page, 30 pages shown |
| Oman Observer | en | sister title of Oman Daily (state) | yes | `/morearticles/business/energy?pgno=N`, 16 per page, about 30 pages |
| Al-Watan (الوطن) | ar | private daily | yes | sections; a PDF archive at `/pdf-archive` |
| Al-Shabiba (الشبيبة) | ar | private (Muscat Media Group) **(group not verified on the page)** | yes | category pages |
| Times of Oman | en | Muscat Media Group (private) | yes | `/index.php/category/oman/page/N`, 10 per page, over 3,000 pages |
| Muscat Daily | en | private | **HTTP 403** | none |

- None exposes a date-addressed archive or a search address in its static HTML. The paged section
  listings run backwards from today; reaching 2022 by paging is not practical (hundreds to
  thousands of pages), so the press is a **declared query set**, never a census.
- All rights reserved on every site read. Facts only, cited by link.
- **Record roles:** Oman Daily and Oman Observer are state-published and carry ONA copy and
  regulator statements; they are the practical record of official statements. Times of Oman and
  the private Arabic dailies add independent reporting of the same events. Two outlets carrying
  the same ONA text are one source.
- **DECISION: event search (systematic lane OM5).**

### 2.19 Reuters; S&P Global Commodity Insights

- Reuters: the fetch tool refuses the host. S&P Global: HTTP 403. Both **SOURCE_BLOCKED** for
  reading pages; they can still surface in search results, where a title and address may be
  recorded but an unopened page supports nothing by itself (`"opened": false`).
- **DECISION: event search** through search results; held unless a readable page confirms.

### 2.20 Rejected or discovery-only sources

- **WRI Global Power Plant Database v1.3** (cached). Oman rows counted this session: **12 plants,
  6,011 MW** (9 gas, 3 solar), newest commissioning year 2008 among the 9 rows that state one, no
  `year_of_capacity_data`. Against a 2025 main-system peak demand of 7,863 MW it is plainly
  incomplete. **Reject** as a denominator.
- **Third-party report aggregators** (for example sustainabilityreports.com): copies of company
  reports of unknown provenance. **Reject**; use the publisher's own copy or none.
- **decree.om, qanoon.om:** private legal databases. decree.om's English text is an unofficial
  translation. **Discovery only**; cite the Official Gazette reference, not the database.
- **attaqa.net:** Arabic energy trade press that summarises the ministry's annual report.
  **Discovery only**; secondary.
- **OpenStreetMap, GEM trackers:** not inspected for Oman this session. **Not yet researched.**
  The Saudi ruling against drawing any pipeline geometry is recommended for Oman too.

---

## 3. Reporting environment and reporting bias

Recommended value: **`corporate_disclosure`**.

- Disruption becomes public mainly through statements: the regulator and the Nama group companies
  after a large power interruption, the ministry and state companies for oil and gas, listed
  companies through the exchange when an event is material.
- No public event register was found. The regulator's own documents could not be opened, so
  whether an investigation report is ever published is not established. If it is, the right value
  is `mixed_regulatory`; that is a decision for the lead once a person has opened apsr.om.
- State-published newspapers and the national agency are the main carriers of official
  statements. Company publications read this session describe performance and report no outage.
- Annual reports give national or company totals. A year with a serious interruption and a year
  without one look the same in them.
- Arabic and English editions of the same outlet, and several outlets carrying one agency text,
  are single sources.
- Weather events (tropical cyclones reaching the coast) are expected to be reported with
  restoration progress more often than with a customer count **(expectation, not verified this
  session)**. A report with no figure cannot meet clause 5; that would be a property of the
  reporting, not of the weather.

**Correction, 2026-11-11 (after review).** The last sentence above is too strong as written. Records in other systems have been accepted under clause 5 on a stated extent with no customer count, with the words "extent-based; no customer count published" in their basis. One Omani grid event was accepted by all three blind roles on that precedent, and the taxonomy reviewer recorded the conflict with this page. Whether clause 5 may be met by official extent alone is not written in `REVIEW_GOVERNANCE.md` and is listed for the owner in `ITERATION_19_REVIEW.md`. The sentence is left in place so the plan reads as it was committed.

## 4. Low reported incidents is not low disruption

The number of Omani incidents Wave B finds will be set by this environment: three official sites
that an ordinary fetch cannot read, an exchange with no reachable disclosure history, company
reports with no outage content, and a press that reports official statements. Technical trips,
unplanned unit shutdowns and upstream deferments are the least likely to surface; PDO's own report
speaks of "deferments" as a managed quantity and dates none of them.

A sparse Oman map must therefore read **"low *reported* disruption, coverage unknown"**, never
"low disruption". There is no benchmark list against which a coverage ratio could be computed, so
none is stated.

## 5. Fields and passages that must never be read into this project

- Any restart date, repair progress, operating rate, remaining capacity or current status of a
  facility attacked in an active or recent kinetic campaign. `conflict_campaigns.json` records an
  Omani campaign from 2026-01-01 with status `uncertain`, treated as active, so every kinetic or
  sabotage event dated 2026 is covered.
- Coordinates, distances, ranges, weapon or method detail, defences.
- Line-level, station-level, constraint or capability data for the transmission system; the
  interconnection passages of the 7-Year Statement; OETC's project list.
- Gas network maps, pipeline routes, station lists (OQ Gas Networks).
- Cargo destinations, vessels, shipping or export routes (Oman LNG, OQ Trading, any press report).
- Field-level or facility-level production and any facility capacity.
- Any description of a facility or a governorate as the largest, key, critical or sole anything.
  Musandam is recorded as a governorate and nothing else.

## 6. Attribution string if adopted

> National statistics: **National Centre for Statistics and Information, Sultanate of Oman** (open
> data licence; figures modified by this project where marked). Electricity context: **Nama Power
> and Water Procurement** (facts extracted; not redistributed). LNG context: **Oman LNG** (facts
> extracted; not redistributed). Monthly flows: **JODI** World Databases. National context layer:
> **U.S. EIA** (public domain). Boundaries: **Natural Earth** (public domain).
