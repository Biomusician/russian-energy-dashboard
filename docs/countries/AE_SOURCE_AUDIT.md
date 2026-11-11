# United Arab Emirates — source audit

Written 2026-11-11 by the UAE source-audit lane (iteration 19, Wave A). **Nothing in this document
is wired into the pipeline or a published payload.** It records, for every candidate source, what
the source is, how it was reached by one ordinary page request, what it can and cannot support, and
whether this project should adopt it. Incident research is a separate lane (Wave B) and is
deliberately not done here.

Scope boundary applies in full (project `CLAUDE.md`; `data/candidates/gulf19/AGENT_BRIEF.md`). This
audit treats infrastructure only as public descriptive context at national or emirate level. It
does not assess the importance, vulnerability, protection, interdependence or routing of any
facility, and it lists no facility with a capacity.

Every figure below was read on a page or in a file during this session unless it is marked
**(not verified this session)**. Where a site could not be reached, that is recorded as a finding
about machine accessibility, not papered over. Web searches used: 4 of 4.

---

## 0. Summary

| Source | Language | Reached by ordinary request | Decision |
|---|---|---|---|
| U.S. EIA country analysis brief (updated 2026-07-28) | en | readable | **adopt** (national context) |
| U.S. EIA International Energy Statistics, bulk file | en | read from the project's cached copy | **adopt** (national context) |
| JODI Oil / JODI Gas | en | readable | **adopt** (national context series) |
| Natural Earth admin-1 | — | cached file | **adopt** (boundaries) |
| u.ae federal portal, energy pages citing the Ministry | ar, en | readable | **derived facts only** |
| Ministry of Energy and Infrastructure (moei.gov.ae) | ar, en | connection closed, three attempts | **discovery only** (unreachable) |
| ADNOC group (adnoc.ae) | ar, en | HTTP 403, two pages | **discovery only** (blocked) |
| ADNOC Gas (adnocgas.ae) | ar, en | readable; announcements widget empty | **derived facts only**; AE2 enumeration endpoint |
| ADNOC Drilling (adnocdrilling.ae) | ar, en | investor home readable; report list broken | **discovery only** |
| Borouge (borouge.com) | ar, en | readable | **discovery only** |
| ADX company disclosure pages (adx.ae) | ar, en | HTTP 403 | **discovery only** (blocked) |
| EWEC (ewec.ae) | ar, en | readable | **derived facts only**; AE3 enumeration endpoint |
| Abu Dhabi Department of Energy (doe.gov.ae) | ar, en | home readable; listings empty | **derived facts only** |
| DEWA (dewa.gov.ae) | ar, en | HTTP 403, three addresses | **discovery only** (blocked) |
| DFM disclosures (dfm.ae) | ar, en | script-only shell | **discovery only** (blocked) |
| SEWA (sewa.gov.ae) | ar, en | readable | **discovery only** |
| Etihad Water and Electricity (etihadwe.ae) | ar, en | readable | **derived facts only**; AE3 enumeration endpoint |
| TAQA (taqa.com) | ar, en | CAPTCHA | **discovery only** (blocked) |
| ENOC (enoc.com) | ar, en | HTTP 403 | **discovery only** (blocked) |
| FCSC and UAE Stat (fcsc.gov.ae, uaestat.fcsc.gov.ae) | ar, en | HTTP 403, both | **discovery only** (blocked) |
| WAM, Emirates News Agency (wam.ae) | ar, en | script-only shell, five addresses | **discovery only**; AE1 by search, pages not openable |
| OPEC | en | HTTP 402, two addresses | **derived facts only** (manual; nothing read) |
| GCC-Stat | ar, en | home and terms readable; energy platform under maintenance | **derived facts only** (validation) |
| Energy Institute Statistical Review | en | HTTP 403 | **derived facts only** (nothing read) |
| Al-Ittihad (aletihad.ae) | ar | timed out twice | **discovery only** (unreachable) |
| Al-Khaleej (alkhaleej.ae) | ar | HTTP 403 | **discovery only** (blocked) |
| Al-Bayan (albayan.ae) | ar | readable | **discovery only** |
| The National (thenationalnews.com) | en | readable | **discovery only** |
| Gulf News (gulfnews.com) | en | section readable; search is a shell | **discovery only** |
| Khaleej Times (khaleejtimes.com) | en | section and search readable | **discovery only** |
| Reuters | en | host refused by the fetch tool | **discovery only** (not reachable here) |
| S&P Global Commodity Insights | en | HTTP 403 | **discovery only** (blocked) |
| Global Energy Monitor trackers | en | not acquired | **denominator candidate**, generation only |
| WRI Global Power Plant Database v1.3 | en | cached file | **reject** as denominator |
| OpenStreetMap | — | not queried | **reject** for UAE analytics |
| Arab Union of Electricity (auptde.org) | ar | home readable; no bulletin located | **discovery only** |

The main finding: **no UAE body reached this session publishes event-level outage or disruption
notices.** The listings that could be read (EWEC, SEWA, Etihad Water and Electricity, ADNOC Gas)
carry procurement, projects, agreements and results. The state news agency, which carries ministry
and authority statements, cannot be opened by an ordinary request. The record for this country
will therefore come from search-discovered media and company statements, in two languages.

---

## 1. Geography — the seven emirates (إمارات)

The federal portal states that the UAE is made up of seven emirates: Abu Dhabi, Dubai, Sharjah,
Ajman, Umm Al Quwain, Ras Al Khaimah and Fujairah (u.ae, "The seven emirates" page, read
2026-11-11; no last-updated date shown). These are the first-level divisions and the analytical
units.

Natural Earth `ne_10m_admin_1` (cached at `data/raw/ne_10m_admin_1.geojson`) carries **9** features
for `ARE`, all with `type_en = "Emirate"`:

| Code | Natural Earth `name` | Arabic (`name_ar`) | Polygon parts | Use |
|---|---|---|---|---|
| AE-AZ | Abu Dhabi | إمارة أبوظبي | 13 | analytical unit |
| AE-DU | Dubay | إمارة دبي | 2 | analytical unit |
| AE-SH | Sharjah | إمارة الشارقة | 5 | analytical unit |
| AE-AJ | Ajman | عجمان | 2 | analytical unit |
| AE-UQ | Umm Al Qaywayn | أم القيوين | 1 | analytical unit |
| AE-RK | Ras Al Khaymah | رأس الخيمة | 2 | analytical unit |
| AE-FU | Fujayrah | الفجيرة | 3 | analytical unit |
| AE-X01~ | Neutral Zone | المنطقة المحايدة | 1 | drawn; never an incident unit |
| AE-X02~ | Neutral Zone | المنطقة المحايدة | 1 | drawn; never an incident unit |

**How Natural Earth differs from the seven emirates.**

- It draws two extra units, both labelled "Neutral Zone". Its own notes describe `AE-X01~` as an
  area under joint control between Fujairah and Sharjah, and `AE-X02~` as an area under joint
  control between Ajman and neighbouring Oman. This project describes both only as **jointly
  administered areas as drawn by Natural Earth**. They are drawn on the map, carry no events, and
  are never used as an incident unit. The current administrative arrangement of either area was
  **not verified from an official source this session**.
- The two codes are Natural Earth's own (`X01~`, `X02~`), not ISO 3166-2 codes.
- The draft `system.json` gives both the status `disputed_unassigned`, because it is the only
  value in the closed vocabulary (`scripts/onboard_system.py`) that draws a unit and assigns it no
  events. The country page's text for that status says "Disputed", which does not describe a
  jointly administered area. **Lead decision:** add a neutral status, or list both codes under the
  precision policy's `no_event_units`, before the page is shown.

**Join hazards.**

- Natural Earth spellings differ from common usage: "Dubay", "Fujayrah", "Ras Al Khaymah",
  "Umm Al Qaywayn". A source that says Dubai, Fujairah, Ras Al Khaimah or Umm Al Quwain will not
  match by name. Join by code with a curated alias table (English and Arabic).
- The `name_en` property of `AE-X01~` is "Fujairah", the same English name as the emirate. A join
  on `name_en` would put Fujairah records into the jointly administered area.
- Both extra units share the `name` "Neutral Zone", so name is not a key.
- Sources routinely mix an emirate with its capital city of the same name (Abu Dhabi, Dubai,
  Sharjah, Ajman, Fujairah, Ras Al Khaimah). Several emirates are drawn in more than one part
  (table above), so a town's emirate must be looked up, never assumed from its neighbours.

**Electricity is not organised by the seven emirates.** The federal portal's electricity page
(last updated 2026-09-15) names four water and electricity authorities: the Department of Energy
and EWEC for Abu Dhabi, DEWA for Dubai, SEWA for Sharjah, and Etihad Water and Electricity for the
northern emirates; its energy-entities page (last updated 2026-09-14) lists Etihad Water and
Electricity against Ajman, Umm Al Quwain, Ras Al Khaimah and Fujairah together. Published
electricity statistics therefore pool four emirates into one service area. An emirate-level figure
for any of those four cannot be read off an official table found this session.

**Islands in the Gulf (cartographic note).** Abu Musa and the Greater and Lesser Tunbs are
administered by Iran and claimed by the United Arab Emirates. Natural Earth's default edition
draws Abu Musa inside Iran's Hormozgan unit (checked this session by a point test against the
cached file); no separate polygon for the Tunbs was found at this scale. The project keeps Natural
Earth's line of actual control, which is an analytic choice and not a statement about sovereignty.
The islands are never an analytical unit of the UAE system and never carry a UAE record.

**Event geography rule for this country.** The emirates are few and some are small, so an emirate
plus an infrastructure class can identify one facility. For **kinetic or security events the
default event geography is country level** (`geography_precision: "country"`, `admin1_code: null`).
Emirate-level placement is used for such an event only where the emirate has several facilities
of the reported class, so that the pair does not single one out, and where no campaign policy
applies to the record. For non-conflict grid and weather events that a source reports as
affecting customers across an emirate, emirate level is used. This document does not list which
emirate has how many facilities of which class.

---

## 2. Source-by-source audit

"Raw redistribution" means: may this project vendor and republish the source file itself, not
merely cite facts from it. Cadence is as observed on the page unless stated.

### 2.1 U.S. EIA — Country Analysis Brief: United Arab Emirates

- **What it is:** `eia.gov/international/content/analysis/countries_long/United_Arab_Emirates/`,
  English, **last updated 2026-07-28**. National narrative with tables.
- **What it publishes:** national aggregates (Table 1, 2024): primary energy production 11.8
  quadrillion Btu, 78% petroleum liquids, 19% natural gas, 0% coal; electricity generation shares
  71% natural gas, 23% nuclear, 5% renewables and other, 1% petroleum liquids. Crude oil and
  condensate production 3.8 million b/d in 2025. National refining capacity 1,249 thousand b/d in
  five refineries as of January 2026. Dry gas production averaged about 2.0 Tcf a year in
  2015–2024 against consumption of about 2.4 Tcf. Coal: no production; consumption averaged about
  2.9 million short tons a year in 2015–2024, all imported, used mainly in industrial processes.
- **Defect found:** Table 1 labels electricity generation "GWh" with a total of 169.0. The
  magnitude is that of billion kWh: EIA's own bulk series gives 169.03 billion kWh for 2024
  (§2.2). The printed unit is not used.
- **Sourcing caveats read on the page:** gas production and consumption are credited to OPEC's
  *Annual Statistical Bulletin 2026*; 2024 LNG imports to the Energy Institute; gas trade and
  crude exports to a commercial cargo-tracking database; reserve figures carry inconsistent
  attributions (text says OPEC, endnotes say otherwise). Those numbers carry their own terms.
- **Reached:** readable HTML. **Cadence:** irregular.
- **Licence:** U.S. government work, public domain, credit requested (as recorded in
  `docs/GLOBAL_ENERGY_CONTEXT.md`). Raw redistribution: yes for EIA's own text and figures only.
- **Fields that must never be read** (the brief carries them): the refinery table (Table 3) and
  the LNG terminal table (Table 4) as facility rows; any pipeline, terminal, shipping-route,
  export-route, bypass or strait-transit commentary; any 2026 commentary on output or exports
  after the start of the 2026 war. This audit read the national total and the count from the
  refinery sentence and nothing from the rows.
- **Decision: adopt** as national context. Never an index input.

### 2.2 U.S. EIA — International Energy Statistics (bulk file)

- **What it is:** `INTL.zip`, the source of the project's world context layer; read from the
  cached copy at `data/raw/global/INTL.zip` (downloaded 2026-11-10).
- **What it publishes for the UAE (annual, read this session):** total energy production 11.80
  quadrillion Btu (2024); crude oil including lease condensate 3,771 thousand b/d (2025), 3,675
  (2024); petroleum and other liquids 4,339 thousand b/d (2025); dry natural gas production 2,098
  Bcf, consumption 2,535 Bcf, imports 771 Bcf, exports 286 Bcf (2024); electricity net generation
  169.03 billion kWh and installed capacity 45.53 million kW (2024); nuclear net generation 39
  billion kWh (2024, one national figure); coal production 0, consumption 3,672 thousand short
  tons (2024).
- **Licence:** public domain, credit requested. Raw redistribution: yes.
- **Fields that must never be read:** nuclear installed capacity (in this country it describes
  one site; only the national generation figure is used).
- **Decision: adopt** as national context.

### 2.3 JODI — Oil and Gas World Databases

- **What it is:** monthly self-reported national flows, English. The oil participants page lists
  the United Arab Emirates as a participating economy under OPEC. Latest update seen: 21 October
  2026, 51 countries reporting August 2026.
- **Reached:** readable; annual CSVs 2002–2026, a full bundle, an API behind a free account.
- **Licence:** only "© Copyright JODI 2026" and a statement that data are free to download. No
  reuse terms. Raw redistribution: unclear, so store derived series with citation only.
- **Limits:** participation is not the same as monthly reporting; the UAE's month-by-month
  completeness was not checked. A monthly national fall with no stated cause is context, never an
  event.
- **Decision: adopt** as the national monthly context series.

### 2.4 Federal portal u.ae — energy pages citing the Ministry

- **What it is:** the federal government portal, Arabic and English. Electricity page last
  updated 2026-09-15; energy-entities page last updated 2026-09-14.
- **What it publishes:** national electricity consumption 174,524 GWh in 2025, credited to the
  Ministry of Energy and Infrastructure; installed capacity of about 48.3 GW in 2026 "across the
  seven emirates" (no source named on the page); the four authorities by emirate (§1). No
  event-level notices.
- **Reached:** readable static HTML.
- **Licence:** copyright page says content is the property of the Telecommunications and Digital
  Government Regulatory Authority and that unauthorised use, reproduction or printing is
  prohibited; no open licence, no attribution rule. Raw redistribution: no.
- **Fields that must never be read:** the page prints a nuclear installed-capacity figure and a
  dated national peak-demand figure for 2026. Neither is recorded.
- **Decision: derived facts only.** It is the only route found to a Ministry statistic.

### 2.5 Ministry of Energy and Infrastructure (وزارة الطاقة والبنية التحتية)

- **What it is:** the federal ministry; expected to publish statistics, open data and news.
- **Reached:** `www.moei.gov.ae` closed the connection on three attempts (home, `/en/home.aspx`,
  `/en/open-data.aspx`). Whether this is geo-restriction, a bot rule or an outage is not
  established. Search found a 2016 edition of its annual energy and water statistics hosted on
  u.ae and references to a unified data platform; neither was opened.
- **Licence:** unread.
- **Decision: discovery only.** Its statements reach the outside through WAM (§2.16).

### 2.6 ADNOC group (adnoc.ae)

- **What it is:** the state oil company. Expected: sustainability reports, news, group facts.
- **Reached:** HTTP 403 on the press-release listing and on the investors page.
- **Decision: discovery only** (blocked). Nothing read; no claim is made here about what its
  reports contain.

### 2.7 ADNOC Gas (adnocgas.ae; listed on ADX)

- **What it is:** ADX-listed gas processing and LNG subsidiary. Arabic and English.
- **What it publishes:** a results-and-reports page listing, by year, quarterly financial
  statements, management discussion reports, analyst data books and presentations (2022–2026),
  an Annual Report 2023, Integrated Reports 2024 and 2025, Sustainability Reports 2024 and 2025.
  A press-release listing (six items visible, August–November 2026, "Load More").
- **Reached:** the report list is static and readable. The regulatory announcements page showed
  "This service is unavailable" and no entries. The press-release listing sits behind a
  country-selection and terms-agreement screen; the static listing came through without it, and
  no agreement was accepted.
- **Cadence:** quarterly and annual. **Licence:** corporate copyright; raw redistribution no.
- **Fields that must never be read:** any 2026 quarterly document, results release or data book
  (they describe operations during a campaign whose state is uncertain); utilisation, availability
  or restart wording in any edition; facility rows.
- **Decision: derived facts only.** The 2023–2025 annual and integrated reports are the AE2
  enumeration universe for incident occurrence. Company disclosure is framed against financial
  materiality.

### 2.8 ADNOC Drilling, Borouge and ADX

- **ADNOC Drilling:** investor home readable. The reports page showed widget errors and stale
  2021 entries behind a disclaimer gate; a guessed announcements address returned 404. A drilling
  contractor's disclosures rarely describe a qualifying disruption. **Discovery only.**
- **Borouge:** investor home and announcements page readable. The regulatory list is static but
  stops in September 2022; a separate company-announcements list is paged and runs to 2026-05-19.
  A petrochemical producer is outside the six sectors; a disclosure would matter only if it
  reports an interruption of gas processing or refining supply. **Discovery only.**
- **ADX:** the company disclosure page returned HTTP 403. **Discovery only** (blocked). ADX is the
  primary venue for listed-subsidiary disclosures, so this is a real gap: the AE2 lane cannot
  enumerate filings and depends on the companies' own pages and on search.

### 2.9 EWEC — Emirates Water and Electricity Company

- **What it is:** an Abu Dhabi water and electricity company, named by the federal portal beside
  the Department of Energy as the Abu Dhabi authority. Its exact role was not read from its own
  pages this session. Arabic and English.
- **What it publishes:** a media-release listing from 22 December 2020 to 5 November 2026, about
  133 items in the part read, on one long page. Titles cover procurement, project milestones,
  partnerships and certificate auctions. **No outage or disruption notice appears in the titles
  read.** The last 9,753 characters of the page were not read.
- **Statistical reports:** none found. Two guessed addresses returned 404, the home page links
  none, and one search found none; the search pointed instead to the Department of Energy (§2.10).
- **Licence:** terms page says most content belongs to EWEC and states no reuse rule. Raw
  redistribution: no.
- **Decision: derived facts only.** AE3 enumeration endpoint.

### 2.10 Abu Dhabi Department of Energy (doe.gov.ae)

- **What it is:** the emirate's energy regulator. Not in the task's source list; found by search.
- **What it publishes:** a home-page "key facts" block for the emirate (energy generated and
  available capacity as emirate totals). Search results show annual technical reports for the
  water, wastewater and electricity sector as PDFs (2019, 2020, 2021 and a 2023 edition); none
  was opened.
- **Reached:** home readable. The publications and news listings returned zero results to an
  ordinary request (script-loaded), with placeholder text on the page.
- **Licence:** "© 2025 Abu Dhabi Government. All rights reserved." Raw redistribution: no.
- **Decision: derived facts only.** The technical reports are the natural official cross-check
  for Abu Dhabi emirate aggregates. Whether they contain station tables is not established; if
  they do, those tables are not read.

### 2.11 DEWA and DFM

- **DEWA:** HTTP 403 on the annual statistics page, the news page and a direct address of the
  2025 statistics booklet. Search-result titles show that annual statistics booklets exist
  (2015, 2017, 2021, 2025); no figure is taken from a search snippet. **Discovery only** (blocked).
- **DFM:** the disclosures page renders a filter form and "Fetching Data..."; no entries reach an
  ordinary request. **Discovery only** (script-only).

### 2.12 SEWA — Sharjah Electricity, Water and Gas Authority

- **Reached:** readable. News listing of 13 items, 28 November 2023 to 19 January 2025, not in
  date order, no paging. Projects, agreements, awards. No outage, interruption or storm title.
  No statistics or annual report link on the home page.
- **Licence:** terms page linked, not read.
- **Decision: discovery only.** The short listing is not an archive.

### 2.13 Etihad Water and Electricity (northern emirates)

- **Reached:** readable. News listing of about 109 items, 18 April 2018 to 6 July 2026, with a
  year filter; few or no entries between January 2022 and April 2025. One 2021 title concerns a
  supply response; none in the window does.
- **Statistics:** an open-data section lists annual Statistical Report PDFs for 2021–2025. Not
  opened.
- **Licence:** the open data policy page permits users to view and reuse open data without
  technical, financial or legal restriction, provided Etihad WE is named as the source with the
  file and its publication date, and the data are not misrepresented or used for political or
  illegal purposes. No standard licence is named. Raw redistribution: yes, with attribution, on
  this reading; the full policy PDF was not read.
- **Decision: derived facts only.** The best licence of any UAE source found, and the only
  official statistics for the four northern emirates, pooled.

### 2.14 TAQA, ENOC

- **TAQA:** the investors page returned a human-verification challenge. Not attempted.
  **Discovery only** (blocked).
- **ENOC:** HTTP 403 on the news listing. **Discovery only** (blocked).

### 2.15 Federal Competitiveness and Statistics Centre, UAE Stat, open-data portal

- **Reached:** `fcsc.gov.ae` and `uaestat.fcsc.gov.ae` both HTTP 403. The national open-data
  portal answered, but the guessed dataset address was its own 404 page; its energy listing was
  not found.
- **Decision: discovery only** (blocked). Whether an electricity table by emirate exists is
  **not yet researched**, not "none".

### 2.16 WAM — Emirates News Agency (وكالة أنباء الإمارات)

- **What it is:** the state news agency, Arabic and English; the channel through which ministry,
  authority and defence statements are issued.
- **Reached:** every address tried returned only the agency's name: English home, Arabic home,
  the search address, an English article (`/en/article/<id>-<slug>`) and an Arabic article
  (`/ar/details/<number>`). The site renders by script. A search restricted to `wam.ae` does
  return titles and addresses in both patterns.
- **Licence:** unread (no page text reached).
- **Consequence:** AE1 cannot be enumerated and a WAM page cannot be opened by an agent. A WAM
  citation found by search is recorded `opened: false` unless a person opens it in a browser.
- **Decision: discovery only.**

### 2.17 OPEC

- **Reached:** HTTP 402 on the member page and on the Annual Statistical Bulletin site. Nothing
  read. The regional lane (`data/candidates/gulf19/regional_sources.md`) records secondary reports
  that the UAE's membership changed in 2026; that is unverified here and no surface should state
  either membership or a rank within OPEC until a person reads OPEC's own list.
- **Decision: derived facts only**, cited manually by edition, or not at all.

### 2.18 GCC-Stat

- **Reached:** home page readable (Arabic). Its energy statistics platform showed a maintenance
  notice and no data. Two guessed English addresses returned 404.
- **Licence:** the terms-of-use page permits content to be freely copied, used, published,
  translated or modified, provided the source is cited, modified content is marked as modified
  and it is not presented misleadingly; third-party material needs its owner's permission.
- **Decision: derived facts only**, as a validation source once its platform returns.

### 2.19 Energy Institute — Statistical Review of World Energy

- **Reached:** HTTP 403. Nothing read. **Derived facts only**, cited by edition by a person.

### 2.20 Arabic-language press

Record roles are stated where a page read this session supports them.

| Outlet | Reached | What was seen | Decision |
|---|---|---|---|
| Al-Ittihad (aletihad.ae), Abu Dhabi daily | timed out twice | nothing | discovery only (unreachable) |
| Al-Khaleej (alkhaleej.ae), Sharjah daily | HTTP 403 | nothing | discovery only (blocked) |
| Al-Bayan (albayan.ae), Dubai daily | readable | economy section about 72 items, no visible dates, no archive or search address | discovery only |

Ownership of the three was **not verified this session**; Al-Bayan's footer credits its copyright
to Dubai Media. All three are domestic outlets working inside the national media framework; treat
them as carrying official statements, not as independent confirmation of them.

### 2.21 English-language press

| Outlet | Reached | What was seen | Decision |
|---|---|---|---|
| The National | readable | energy section, about 31 items, dates in the address (`/business/energy/YYYY/MM/DD/`); terms allow personal, non-commercial use only | discovery only, cite by link |
| Gulf News | section readable; search is a shell | "Load more" listing; footer copyright Al Nisr Publishing | discovery only |
| Khaleej Times | section and search listing readable (no dates in the listing) | footer copyright Galadari Printing and Publishing | discovery only |
| Reuters | the fetch tool refuses the host | nothing | discovery only (not reachable here) |
| S&P Global Commodity Insights | HTTP 403 | nothing | discovery only (blocked) |

A wire story republished by a domestic outlet, and an Arabic and English version of one WAM
statement, are one source, not two.

### 2.22 Inventories and geometry

- **Global Energy Monitor trackers:** CC BY 4.0 per this repo's earlier verification
  (`docs/POWER_SOURCE_RECONCILIATION.md`); download is form-gated; UAE rows not inspected.
  **Denominator candidate for generation only**, aggregated before anything is emitted. Pipeline
  and terminal trackers: **reject** for this country, for the same scope reason as Saudi Arabia.
- **WRI Global Power Plant Database v1.3** (cached): 30 UAE rows, 30,327 MW, of which 24 gas
  (29,487 MW) and 6 solar (840 MW); 27 of 30 rows credited to the Arab Union of Electricity;
  newest commissioning year 2016; no status field. It has no nuclear and little solar against
  EIA's 45.5 million kW for 2024. **Reject** as a denominator.
- **Arab Union of Electricity:** home page readable in Arabic; no statistical bulletin located.
  **Discovery only.**
- **OpenStreetMap:** not queried this session. **Reject** for UAE analytics on scope grounds: no
  UAE pipeline, terminal or grid geometry should be drawn.
- **Natural Earth admin-1:** public domain; **adopt**, with the rulings in §1.

### 2.23 Rejected or not used, and why

| Source | Reason |
|---|---|
| WRI GPPD as a denominator | 2016 snapshot, no nuclear, no status |
| OSM, GEM pipeline and terminal trackers | routing and facility geometry are outside scope |
| Commercial aggregators returned by search (statistics resellers, market-report vendors) | paywalled or unsourced; conflicting capacity figures seen in snippets |
| IAEA country nuclear profile (returned by search) | nuclear programme detail; not opened, by rule |
| Search-result snippets for any figure | a snippet is not a page read |
| EIA brief facility tables and route commentary | never-read fields (§2.1) |

---

## 3. Fields that must never be read, in one place

For every UAE source, in every lane:

- restart dates, repair progress, operating rate, remaining capacity or outage status of a
  facility attacked in 2026, including company results documents for 2026 periods;
- coordinates, distances, routes, weapon or method detail, defences;
- any statement that a facility is the largest, a main one or the only one of its kind;
- tanker, cargo-tracking, shipping-route, export-route, bypass or strait-transit material;
- pipeline route detail, grid topology, interconnector status;
- anything about the nuclear power site beyond the national generation figure: no unit status,
  no outage, no capacity, no site detail. A reported 2026 incident near that site is not
  researched or recorded (campaign-status lane note);
- facility rows with capacities in any table.

---

## 4. Reporting bias, in neutral words

- The oil and gas operator is state-owned; its listed subsidiaries disclose through exchange
  filings and quarterly results, framed against financial materiality.
- The electricity and water bodies are government authorities or government-owned companies.
  Their public pages reached this session publish projects and procurement, not outages.
- Domestic media in both languages operate within a national licensing framework and largely
  carry official statements. International wires and trade press add reporting, usually citing
  unnamed sources, and were mostly unreachable from this machine.
- For attacks, statements come from the authorities and from parties to a conflict. A count of
  outlets repeating one statement does not measure confirmation.
- English-language coverage of this country is extensive relative to its neighbours, which makes
  events easier to find here than in countries with less English reporting. That is a property of
  the press, not of the infrastructure.
- Arabic reporting was harder to reach than English: two of three Arabic dailies and the Arabic
  WAM site could not be opened.

## 5. Low reported incidents is not low disruption

The number of incidents that will be found for the UAE is a property of the reporting
environment: state-owned operators with materiality-based disclosure, authorities that do not
publish outage notices on the pages reached, an exchange and a news agency that cannot be
enumerated by machine, and no outage register. Technical outages, trips and short supply
interruptions are the least likely to surface. Small emirates may never appear at all.

A sparse UAE record must read as **"low reported disruption, coverage unknown"**. No coverage
ratio can be computed, because no independent benchmark list exists. A national production or
export fall seen in JODI or EIA with no stated cause is context and is never converted into an
event or a loss figure.

---

## 6. Attribution string if adopted

> National context: **U.S. EIA** (public domain); **JODI** World Databases. Boundaries:
> **Natural Earth** (public domain). Northern-emirates statistics, if used: **Etihad Water and
> Electricity** open data (source, file and publication date named). Other figures: facts cited
> by link to their publisher; not redistributed.

## 7. Blocked or unreachable endpoints (one ordinary request each unless noted)

| Endpoint | Result |
|---|---|
| moei.gov.ae (home, `/en/home.aspx`, `/en/open-data.aspx`) | connection closed, three attempts |
| adnoc.ae (press releases, investors) | HTTP 403 |
| adx.ae company page | HTTP 403 |
| dewa.gov.ae (statistics page, news, booklet file) | HTTP 403 |
| dfm.ae disclosures | script-only shell |
| taqa.com investors | CAPTCHA, not attempted |
| enoc.com news | HTTP 403 |
| fcsc.gov.ae, uaestat.fcsc.gov.ae | HTTP 403 |
| wam.ae (home en and ar, search, two article patterns) | script-only shell |
| opec.org member page, asb.opec.org | HTTP 402 |
| energyinst.org | HTTP 403 |
| aletihad.ae (home, economy) | timed out twice |
| alkhaleej.ae | HTTP 403 |
| spglobal.com commodity news | HTTP 403 |
| reuters.com | refused by the fetch tool |
| ncema.gov.ae news | connection closed |
| doe.gov.ae publications and news listings | page loads, zero results (script) |
| adnocgas.ae announcements | page loads, "service unavailable" |
| energy.gccstat.org | maintenance notice |
