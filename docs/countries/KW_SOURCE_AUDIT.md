# Kuwait — source audit

Written 2026-11-11 by the Kuwait source-audit lane (iteration 19, Wave A). **Nothing in this
document is wired into the pipeline or a published payload.** It records, for every candidate
source, what the source is, how it was reached today, under what terms, and whether this project
should adopt it. Incident research is a separate lane (Wave B) and was deliberately not done here.

Scope boundary applies in full (project `CLAUDE.md`, `docs/CURRENT_EVENT_PUBLICATION_POLICY.md`).
A campaign is recorded for Kuwait in `data/curated/systems/conflict_campaigns.json`
(`kw-2026-attacks-on-energy-facilities`, status `uncertain`, treated as active, from 2026-01-01).
This audit therefore read **no** page about the state of any facility after an attack, and none of
its figures is later than a 2025 annual total.

Every figure below was read on a page or in a file during this session unless it is marked
**(not verified this session)**. An access failure is recorded as a finding about machine
accessibility from this machine on this date, not as proof of geo-blocking. This lane was
time-boxed: each endpoint got one ordinary request, at most one retry at a second address, and no
workaround.

Companions: [KW_INDEX_READINESS.md](KW_INDEX_READINESS.md), [KW_SYSTEMATIC_SWEEP.md](KW_SYSTEMATIC_SWEEP.md),
`data/candidates/gulf19/kw_system_draft.json`, `data/candidates/gulf19/kw_profile_draft.json`.
Web searches used by this audit: **1 of 4**.

---

## 0. Summary

| # | Source | Language | Publishes | Reached today | Decision |
|---|---|---|---|---|---|
| 1 | Kuwait Petroleum Corporation (KPC) — public statements, publications | ar, en | corporate statements; annual and sustainability reports | home page yes; the statements and publications lists show "Loading..." only | **discovery only** (SOURCE_BLOCKED for enumeration: script-only) |
| 2 | Kuwait National Petroleum Company (KNPC) — site and annual reports | en, ar | annual reports by fiscal year; publications | home page and annual-report listing yes (static); no news listing found | **derived facts only**; the report archive is a Wave B enumeration (KW1) |
| 3 | Kuwait Oil Company (KOC) — news and annual reports | en, ar | company news; annual reports | landing page yes; both lists script-only | **discovery only** (SOURCE_BLOCKED for enumeration) |
| 4 | Kuwait Integrated Petroleum Industries Company (KIPIC) | en, ar | company news | TLS failure on both hosts | **SOURCE_BLOCKED** |
| 5 | Ministry of Oil | ar, en | ministry news; statistics | no answer (connection closed), twice | **SOURCE_BLOCKED** |
| 6 | Ministry of Electricity, Water and Renewable Energy (MEW) — news archive | ar, en | ministry news, 2019–2026 | yes, static, both languages | **adopt as a Wave B enumeration lane** (event search, KW2) |
| 7 | MEW — Statistical Year Book | ar, en | annual national electricity and water statistics | page yes; shows covers for 2017–2019 and no file | **denominator candidate, not acquired** |
| 8 | Central Statistical Bureau (CSB) — Annual Statistical Abstract | ar, en | annual national statistics | listing yes; downloads are script postbacks; usage policy not readable | **derived facts only** (not read) |
| 9 | Kuwait Government Online (`e.gov.kw`) | ar, en | administrative facts | HTTP 403 | **SOURCE_BLOCKED** |
| 10 | Kuwait News Agency (KUNA) | ar, en | official statements, including ministry and company statements | home and article addresses return a title only | **adopt as an event-search source through declared queries** (SOURCE_BLOCKED for direct enumeration) |
| 11 | Al-Qabas (القبس) | ar | daily newspaper | title only (script-only) | **event search — media record, via search results** |
| 12 | Al-Rai (الراي) | ar | daily newspaper; an oil section | yes, static; ID addresses, no date in address | **event search — media record** |
| 13 | Al-Anba (الأنباء) | ar | daily newspaper | HTTP 403 | **SOURCE_BLOCKED**; search results only, `opened: false` |
| 14 | Al-Jarida (الجريدة) | ar | daily newspaper; a dated archive 2007–2026 | yes, static; day-by-day archive | **event search — media record**; archive used to open a known date |
| 15 | Arab Times | en | daily newspaper | yes, static; undated slugs; RSS | **event search — media record** |
| 16 | Kuwait Times | en | daily newspaper | first batch static; "Show More" is script | **event search — media record** |
| 17 | Reuters; S&P Global Commodity Insights | en | wire; energy press | not tested by this lane | **discovery only** (the Qatar audit of the same day records both as SOURCE_BLOCKED) |
| 18 | U.S. EIA — International Energy Statistics, bulk file | en | national annual series | yes (local copy, release 2026-10-16) | **adopt** (national context) |
| 19 | U.S. EIA — Country Analysis Brief: Kuwait | en | national context | yes; last updated 2023-07-20 | **adopt** (national context; old) |
| 20 | GCC-Stat; JODI; OAPEC; OPEC | ar, en | regional and member statistics | not retested; see `data/candidates/gulf19/regional_sources.md` | **derived facts only / validation only**; OPEC SOURCE_BLOCKED there |
| 21 | Natural Earth admin-1 | — | boundaries, 6 units | local file | **adopt**, with the rulings in §1 |
| 22 | WRI Global Power Plant Database; OpenStreetMap; pipeline and terminal trackers | en | plant rows; geometry | not queried | **reject** for Kuwait |
| 23 | Boursa Kuwait company disclosures | ar, en | listed-company announcements | not tried | **not yet researched** |

The single most useful finding: **the electricity ministry's news archive is static, bilingual and
enumerable, and it is the only official Kuwaiti event-level source that an ordinary request can
read.** Every oil-sector body either fills its listings by script, fails TLS or does not answer, and
the state news agency returns a title and nothing else. So for the oil sector the record will rest
on press copies of official statements, found by declared queries.

The second finding is about context: **no Kuwaiti national statistical source could be opened with
readable terms.** The profile draft therefore cites EIA alone.

---

## 1. Geography — six governorates, six drawn

**Current first-level divisions: 6 governorates (محافظة, *muhafazah*)**, as the lead's task states
and as the map file draws. **The count was not confirmed on an official page this session.** The
government portal's governorates page (`e.gov.kw`) returned HTTP 403, and the Central Statistical
Bureau's home page neither lists nor counts them. The one web search used returned only Wikipedia
and its mirrors (discovery only, never a citation), which give six and the same six names.

| Governorate | Arabic | ISO 3166-2 | In Natural Earth (as built into `data/processed/systems/kw/regions.geojson`) |
|---|---|---|---|
| Al Asimah (Capital) | العاصمة | KW-KU | yes, two separate polygons |
| Hawalli | حولي | KW-HA | yes |
| Al Farwaniyah | الفروانية | KW-FA | yes |
| Mubarak Al-Kabeer | مبارك الكبير | KW-MU | yes |
| Al Ahmadi | الأحمدي | KW-AH | yes; reaches the southern international boundary |
| Al Jahrah | الجهراء | KW-JA | yes, three separate polygons |

The Arabic names are the usual ones and were **not read on an official page this session**.
Natural Earth and the current divisions agree in number, so `units_expected` is 6 and no unit is
missing or merged.

### Rulings

1. **The Saudi–Kuwaiti Partitioned (Neutral) Zone is not a unit.** Natural Earth draws no separate
   feature for it. It draws the international boundary that divides the zone, and the part north of
   that line is inside the KW-AH polygon. An onshore, non-conflict event that a source places in the
   zone is placed by the drawn boundary: under KW-AH in this system, or in the Saudi system, where
   the source makes the side clear, and at **country level** otherwise. Shared onshore and offshore
   fields are never a unit of analysis, and no share of their output is attributed here. This is a
   statement about the map file, not about resource rights or sovereignty.
2. **Attacks and sabotage are recorded at COUNTRY level, for every date in the window.** The lead's
   precision policy (`lead_decisions.json`): a governorate and a class together would name the
   facility. Such records carry `geography_precision: "country"`, `admin1_code: null`, and no
   governorate, facility or operator in any published text.
3. **Other events are placed by governorate** (fires, technical outages, storms, load shedding with
   a dated qualifying loss). A multi-governorate electricity event lists the governorates the source
   names, or is country level if the source says only "several areas".
4. **Offshore is country level.** Offshore fields and installations fall in no governorate polygon
   and are never snapped to the nearest coast. This audit makes no statement on maritime boundaries.
5. **Islands belong to the unit the map file gives them.** KW-KU and KW-JA are drawn in more than
   one polygon; every part is that unit.

### Join hazards

- Spellings vary widely: Al Asimah / Capital / Al Kuwayt; Al Jahrah / Jahra; Al Farwaniyah /
  Farwaniya; Mubarak Al-Kabeer / Mubarak Al Kabir; Al Ahmadi / Ahmadi. **Join by ISO code**, with an
  alias table in both scripts.
- "Kuwait City" in a source is a city, not the Capital Governorate; several governorates make up the
  metropolitan area. A source that says only "Kuwait City" does not fix a governorate.
- Sources usually name a residential or industrial **area** (منطقة), the level below the
  governorate. Under ruling 2 an area is never recorded for an attack; for other events it is mapped
  to its governorate and not kept.
- The electricity ministry reports cuts by area lists. Those lists are read only to find the
  governorates and the stated megawatts or customer count; the area list itself is not copied.

---

## 2. Source-by-source audit

Access tests were made on 2026-11-11 with one ordinary request each, plus the single retry noted.

### 2.1 Kuwait Petroleum Corporation (KPC, مؤسسة البترول الكويتية)

- **What it is:** the state holding company for the oil sector; `kpc.com.kw`.
- **Language:** English and Arabic (an "AR" switch).
- **Publishes:** "Public Statements", a corporate magazine, annual reports, sustainability reports.
- **How reached:** the home page answers with readable navigation. `/PublicStatements` and
  `/Publications?filter=AnnualReport` both return the page frame with a "Loading..." placeholder and
  no items: the lists are filled in by script. A guessed `/media-center/press-releases` returned
  HTTP 404. **SOURCE_BLOCKED (script-only)** for enumeration. Not worked around.
- **Cadence:** not readable.
- **Terms as read:** footer "Copyright Kuwait Petroleum Corporation © 2026"; the link behind it is
  a placeholder. No terms-of-use page found.
- **Decision: discovery only.** KPC statements are found through the declared queries of lane KW1
  and read as carried by the press, or by KUNA where a reader can open it.

### 2.2 Kuwait National Petroleum Company (KNPC, شركة البترول الوطنية الكويتية)

- **What it is:** the state refining and gas-processing company; `knpc.com`.
- **Language:** English and Arabic.
- **Publishes:** annual reports by fiscal year, sustainability reports, publications, a media
  gallery. **No news or press-release listing is linked from the home page**; a guessed
  `/en/media-center/news` returned HTTP 404.
- **How reached:** static. `/en/media-center/publications/reports/annual-reports` lists PDF reports
  for fiscal years 2011-12 to 2025-26. **Fiscal year 2023-24 is not on the list.** The listing also
  carries an entry titled "KIPIC Annual Report 2025-2026" that points to the same file as KNPC's
  2025-26 report. The PDFs were not opened in this audit (size not tested).
- **Cadence:** annual, by fiscal year.
- **Terms as read** (`/en/term-of-use`): the company "Has the full copyrights of all images, videos
  and publications contained in this website" and "allows the storing and copying of these contents
  without modifying or reproducing or using them for commercial purposes." No clause on linking.
- **Fields never read:** unit-by-unit capacity, throughput by refinery, project status, and any
  post-event status material (see §4).
- **Decision: derived facts only.** The reports for fiscal years 2021-22 to 2025-26 are a Wave B
  report-archive universe for lane KW1: read for whether a dated incident is stated, nothing else.
  For the 2025-26 report, only occurrence, date, class and the effect stated at the time of a
  2026 attack may be taken, under the campaign policy.

### 2.3 Kuwait Oil Company (KOC, شركة نفط الكويت)

- **What it is:** the state upstream company; `kockw.com`.
- **How reached:** the bare host returned a title only. `/sites/EN/Pages/default.aspx` is readable
  and links a news list (`/sites/EN/Pages/Media%20Center/News%20And%20Events/Allitems.aspx`) and an
  annual-report page (`/sites/EN/Pages/Media%20Center/annual-report.aspx`). Both return a frame
  with "Loading..." or empty filters and no items. A guessed `News.aspx` returned HTTP 404.
  **SOURCE_BLOCKED (script-only)** for enumeration.
- **Terms as read:** a partial footer, "Kuwait Oil Company (KOC) copyright ©". No terms page found.
- **Decision: discovery only.** Upstream is a note, not a sector (see the readiness document), so
  a KOC statement matters only where it reports a qualifying effect.

### 2.4 Kuwait Integrated Petroleum Industries Company (KIPIC)

- **How reached:** `www.kipic.com.kw` and `kipic.com.kw` both failed TLS ("unable to verify the
  first certificate"). **SOURCE_BLOCKED (TLS failure).** Not worked around.
- **Decision: not read.** Its statements are reached, if at all, through the press.

### 2.5 Ministry of Oil (وزارة النفط)

- **How reached:** `www.moo.gov.kw` closed the connection with no answer, on the first request and
  on one retry. **SOURCE_BLOCKED (no answer).**
- **Decision: not read.** The CSB home page links an "Oil Ministry and Companies Data" system; it
  was not opened.

### 2.6 Ministry of Electricity, Water and Renewable Energy (MEW) — news archive

- **What it is:** the ministry that owns and runs public generation, transmission, distribution
  and water production; `mew.gov.kw`.
- **Language:** Arabic and English, as parallel listings.
- **Publishes:** ministry news: meetings, contracts, campaigns, and announcements. Programmed-cut
  and emergency announcements, if the ministry posted them here, would be in this list. It is not
  an outage register and carries no reliability statistics.
- **How reached:** static. `/en/media-center/news/` and `/ar/media-center/news/` each return one
  long page (about 155,000 to 158,000 characters) headed "Archive News", newest item 5 November
  2026. Item addresses are `/en/NewsDetails?fromurl=news&&newsname=CODE` and the same under `/ar/`;
  the codes are irregular (spaces, brackets, mixed case). The first 100,000 characters of the
  English page run from November 2026 back to 12 November 2024, about 100 items; the rest holds
  about 134 items ending in 2019, with a pager showing pages 1 to 4. The Arabic page showed about
  230 items in its first 100,000 characters, back to June 2024.
- **Quality notes:** the list is not in strict date order, one item is dated 01-01-0001, and the
  English list is much thinner than five years of ministry activity would produce: the stretch from
  2019 to late 2024 has about as many items as the two years since. The archive is therefore an
  incomplete record for 2022–2024 and must not be called a census of ministry statements.
- **Cadence:** several items a month since late 2024.
- **Terms as read:** "© Copyrights 2023 Ministry of Electricity & Water & Renewable Energy, Kuwait.
  All rights reserved." No terms-of-use page found; no clause on linking was seen.
- **Fields never read:** area-by-area cut schedules beyond the governorate, substation or feeder
  names, plant unit status, interconnection flows (see §4).
- **Decision: adopt as the enumeration universe of lane KW2.** Titles are read in both languages
  for 2022-01-01 to 2026-11-11; an item is opened only if its title states an outage, a programmed
  or emergency cut, a plant fault or a storm effect.

### 2.7 MEW — Statistical Year Book

- **Publishes:** an annual statistical yearbook for electrical energy and for water **(the split is
  general knowledge, not read today)**.
- **How reached:** `/en/about/statistics/` is static but empty of data: three covers (2017, 2018,
  2019) that link only to in-page anchors, and headings "Annual Statistics", "Monthly Statistics",
  "Monthly Bulletin" and "Study performance indicators" with nothing under them. No file address.
- **Decision: denominator candidate, not acquired.** No value from it is in the profile. A plant
  table certainly exists in such a yearbook; it would never be copied (see §4).

### 2.8 Central Statistical Bureau (CSB, الإدارة المركزية للإحصاء)

- **Publishes:** the Annual Statistical Abstract (editions listed from 2000 to 2023-2024, PDF;
  Excel for 2013 to 2015-2016), and bulletins by subject. The home page has no energy section.
- **How reached:** the home page and the abstract's listing page are readable. Downloads are script
  postbacks, not file addresses, so an ordinary request cannot fetch an edition. The abstract's
  chapter list is not on the page, so an electricity or energy chapter is **not confirmed**.
- **Terms as read:** footer "All Rights Reserved © 2026 - Central Statistical Bureau", with a "Data
  usage policy" link. The policy address tried returned an error page (404), so **the terms are
  unread**.
- **Decision: derived facts only, and nothing read.** With the terms unread, no CSB address is
  cited in the profile.

### 2.9 Kuwait Government Online (`e.gov.kw`)

- **How reached:** the governorates page returned HTTP 403. **SOURCE_BLOCKED.** This is why the
  count of six is not confirmed from an official page.

### 2.10 Kuwait News Agency (KUNA, وكالة الأنباء الكويتية)

- **What it is:** the state news agency; `kuna.net.kw`.
- **Language:** Arabic and English (the site also offers French, not verified this session).
- **Publishes:** official statements, including those of the oil companies, the oil ministry, the
  electricity ministry, the fire force and the interior ministry.
- **How reached:** `Default.aspx?language=en` and `Default.aspx?language=ar` each returned the title
  "KUNA Website" and no body. Two article addresses of the usual form
  (`ArticleDetails.aspx?id=N&language=en` and `...&language=ar`, with guessed numbers) returned
  "Kuna News Agency" and no body. A guessed category page returned HTTP 404. So neither listings
  nor article text reach an ordinary request: **SOURCE_BLOCKED (script-only shell)**. Whether a real
  article id behaves differently from a guessed one was not established.
- **Terms:** not readable.
- **Decision: adopt as an event-search source through declared queries (lane KW3).** A KUNA item
  found by search is cited with `opened: false` unless its text was actually read. A press copy
  that quotes the KUNA statement is the same source, not a second one.

### 2.11–2.16 Domestic newspapers — record roles

| Paper | Reached | Addresses | Listing | Terms as read |
|---|---|---|---|---|
| Al-Qabas (`alqabas.com`) | title only; a guessed section address 404 | not seen | script-only | not readable |
| Al-Rai (`alraimedia.com`) | yes, static | `/article/{id}/{section}/{subsection}/{slug}`, no date | sections `/محليات`, `/اقتصاد`, and an oil section `/نفط` (9 items, no pager seen) | "جميع الحقوق محفوظة"; privacy page only |
| Al-Anba (`alanba.com.kw`) | HTTP 403 | — | — | — |
| Al-Jarida (`aljarida.com`) | yes, static | `/article/{id}`, no date in address; date in page text | sections `/محليات`, `/اقتصاد`; **archive by day** at `/archive/YYYY/M/D`, years 2007–2026; RSS | "جميع الحقوق محفوظة" |
| Arab Times (`arabtimesonline.com`) | yes, static | `/news/{slug}/`, no date | `/news/category/kuwait/`, 12 items, no pager seen; RSS at `/rss` | "All Rights Reserved"; no terms page seen |
| Kuwait Times (`kuwaittimes.com`) | first batch static | `/article/{id}/{section}/{slug}/`, no date | `/kuwait`; "Show More" is a script link | copyright page: permission needed to republish; attribution required; nothing on linking |

- **Roles:** all six are media records for lanes KW3 and KW4. None is an official source, though
  each carries official statements. Al-Anba and Al-Qabas are reached only as search results and are
  cited `opened: false` unless a reader opens the page.
- **Al-Jarida's dated archive** is the only day-by-day press archive found. At roughly 1,775 days
  in the window it is not run as a census; it is used to open a known date.
- **No newspaper's terms forbid linking** as far as they could be read. Facts are cited by link;
  no text is reproduced.

### 2.17 Reuters; S&P Global Commodity Insights

- Not tested by this lane. The Qatar audit of the same day records that the fetch tool refuses the
  Reuters host and that S&P Global returns HTTP 403. **Discovery only**: search results,
  `opened: false`.

### 2.18 U.S. EIA — International Energy Statistics (bulk file `INTL.zip`)

- **What it is:** EIA's international series, one JSON line per series. The local copy
  (`data/raw/global/INTL.zip`, release 2026-10-16) was read with `zipfile` and `json`.
- **Publishes for Kuwait:** 384 annual series. Read for the profile: total energy production and its
  split (2024), petroleum and other liquids production (2025), crude including lease condensate
  production (2025), petroleum consumption (2024), dry gas production, consumption and imports
  (2024), net generation with fossil and renewable totals (2024), net consumption (2024), installed
  capacity (2024), coal production (zero, 2024) and coal consumption (2024).
- **Limits:** the crude export series (`57-4`) stops at **2018**. There is no refining-capacity and
  no LNG series. Electricity imports and exports are both zero for 2024 in the file; that was not
  cross-checked and is not used. The file's split of renewable generation between technologies was
  not cross-checked against a national source and is not used.
- **Terms:** public domain (U.S. government work), as recorded in `regional_sources.md`.
- **Decision: adopt** for national context.

### 2.19 U.S. EIA — Country Analysis Brief: Kuwait

- **How reached:** static page, read today. **Last updated 20 July 2023.**
- **Publishes:** Table 1 (energy overview, 2021), a refining capacity table (Table 3, 2023) with a
  national total, a regasification table (Table 4, 2022), and text on production and exports.
- **Limits:** it is more than three years old, so it is past the registry's 400-day stale limit on
  the day it is adopted. Its refining total includes capacity that was still being brought into
  service when it was written. Its export statement ("around 1.9 million b/d" since 2020) is an
  approximation and is not taken into the profile. Table 4 is in effect facility-level and is not
  taken.
- **Decision: adopt** for one row, the national refining capacity total, with its vintage stated.

### 2.20 GCC-Stat; JODI; OAPEC; OPEC

- Assessed once for all eight Gulf systems in `data/candidates/gulf19/regional_sources.md` and not
  retested here. GCC-Stat allows reuse with attribution; JODI and OAPEC reserve rights (validation
  only); every OPEC host returned HTTP 402 there, so OPEC's terms and tables are unread.
- **Decision: derived facts only / validation only.** No value from them is in the profile.

### 2.21 Natural Earth admin-1

- Six `KWT` units, matching the task's list, as built into
  `data/processed/systems/kw/regions.geojson`. **Adopt**, with the rulings in §1.

### 2.22 WRI Global Power Plant Database; OpenStreetMap; pipeline and terminal trackers

- **Reject** for Kuwait. No facility row, facility coordinate or network geometry is drawn or
  stored for this system.

### 2.23 Boursa Kuwait disclosures

- Not tried. Listed petrochemical and service companies file announcements there. **Not yet
  researched.**

---

## 3. Reporting bias, in neutral words

- **Ownership.** The oil companies are subsidiaries of one state corporation; electricity and water
  are run by a ministry, not a company. The news agency is a state body. The daily newspapers are
  privately owned and publish under a press law (general knowledge, not read on a page today).
- **Disclosure rule.** No law or regulator was found that requires public outage reporting. An
  event is public when a company, a ministry or the fire force issues a statement, when it is
  visible to customers, or when a member of parliament or the press raises it.
- **Electricity is the more visible sector.** Cuts reach households, so they are announced and
  reported. A technical event inside an oil facility has no such audience unless there is a fire, a
  casualty or a change in deliveries.
- **Who reports from outside.** Crude and product trade is followed by wire services and the energy
  press, so an event that changes exports tends to be reported abroad. That reporting also carries
  shipping and routing material this project does not read.
- **Language.** Official statements are issued in Arabic first and in English by the same agency.
  The Arabic press carries more local detail on electricity; the English press is thinner.
- **Conflict.** For the 2026 attacks, parties to a war and the state concerned are the main
  sources. Statements may be made for effect, and outlets repeat one another. Publisher count
  overstates certainty.
- **Small-country effect.** With few facilities, almost any event description identifies a site.
  That is why attacks are recorded at country level (§1).

## 4. Fields that must never be read

From any source, public or not:

- any refinery's, plant's, unit's, terminal's or pipeline's status, restart date, repair progress,
  operating rate or remaining capacity after an attack;
- per-refinery, per-unit, per-plant or per-terminal capacity in any output file: lists exist in
  the EIA brief, the KNPC reports and the ministry yearbook; they are not copied;
- which facility is described as largest, key, critical or sole;
- coordinates, distances, ranges, weapon or attack-method detail, air or site defences;
- cargo, tanker, AIS, destination, loading-schedule or export-route material; any Strait of Hormuz
  or alternative-route material, including official remarks on it;
- pipeline routes; grid topology; substation, feeder and line names; interconnection flows and
  line-level interconnector status;
- the ministry's area-by-area cut schedules below the governorate;
- output shares or operating detail of fields in the Partitioned Zone.

For a kinetic or sabotage record: occurrence, date, broad class and the effect reported within
7 days only. Nothing later, and no page whose address or title states later status.

## 5. Low reported incidents is not low disruption

The number of Kuwaiti incidents this project will find is a property of the reporting environment:
state oil companies whose statement lists cannot be enumerated, a state news agency that an
ordinary request cannot read, a ministry archive that is thin before late 2024, no outage register
and no published reliability statistics. Technical trips, partial shutdowns and local outages are
the least likely to surface. The record for 2022 and 2023 may contain very little, and that would
say nothing about how reliably the system ran.

The dashboard must therefore never render a sparse Kuwait record as "low disruption". The correct
reading is **"low reported disruption, coverage unknown"**. The summer load-shedding episodes of
2024 and 2025 qualify only if a source gives a dated loss that meets the inclusion rule; routine,
scheduled cuts with no stated figure are not events, and their absence from the record is not a
finding that they did not happen. National annual totals are context. When a 2026 total is
published it may differ from 2025; that difference is not a capacity-loss estimate and must not be
turned into one.

Three absences stay distinct here as everywhere: **unknown** (reliability indicators exist inside
the ministry and are not published; recent crude exports on a reusable basis), **not applicable**
(coal), and **not yet researched** (the KNPC report PDFs; the ministry yearbook; the CSB abstract;
Boursa Kuwait disclosures; the official statement of the governorate count).

## 6. Attribution string if adopted

> National context: **U.S. EIA**, International Energy Statistics and Country Analysis Brief:
> Kuwait (public domain). Boundaries: **Natural Earth** (public domain), six governorates as drawn;
> the Partitioned Zone is not a unit.

## 7. For the lead

- The count of six governorates rests on the task statement, the map file and a secondary source.
  An official page should be read by hand before any surface cites one.
- The EIA brief (2023-07-20) is older than the registry's stale limit. Either accept a stale flag
  on it or drop the refining row.
- Crude exports are absent from the profile. EIA's series ends in 2018; the alternatives (OPEC,
  OAPEC, JODI, CSB) have unread or restrictive terms.
- KUNA cannot be opened by an ordinary request. Lane KW3 will mostly produce `opened: false`
  citations unless a press copy is read instead.
