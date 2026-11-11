# Bahrain — source audit

Written 2026-11-11 by the Bahrain source-audit lane (iteration 19, Wave A). **Nothing in this
document is wired into the pipeline or a published payload.** It records, for every candidate
source, what the source is, how it was reached, under what terms, and whether this project should
adopt it. Incident research is a separate lane (Wave B) and is deliberately not done here.

Scope boundary applies in full (project `CLAUDE.md`; `data/candidates/gulf19/AGENT_BRIEF.md`). This
audit treats infrastructure only as public descriptive context. It does not assess the importance,
vulnerability, protection, interdependence or routing of any facility. It did not open, and does not
record, anything about the current status of a facility after an attack. Whether a kinetic campaign
is recorded for Bahrain is the campaign-status lane's finding, not this document's.

Every statement below was read on a page or document during this session unless it is marked
**(not verified this session)**. Each source was tested with ordinary `WebFetch` requests; a refusal
is recorded as a finding about machine access and was not worked around. Web searches used: 3 of a
cap of 4.

---

## 0. Summary

| Source | Language | Reached | Decision |
|---|---|---|---|
| Bahrain Open Data Portal, `data.gov.bh` (iGA): Ministry of Oil and Environment and EWA annual series | ar, en | yes, by its public API | **adopt** (national context; open licence) |
| IRENA Energy Profile: Bahrain | en | yes (PDF) | **adopt** (national context) |
| Electricity and Water Authority (EWA) news listing, `ewa.bh` | ar, en | yes, paged static listing | **discovery only** for events (BH2 enumeration); terms restrict linking |
| EWA annual statistics books (`legacy.ewa.bh`) | ar, en | no: PDF over the 10 MB fetch limit; newer path 404 | **derived facts only**, not read |
| Bapco Refining, `bapco.net` (press releases, annual reports) | en (ar reports listed) | yes, static | **discovery only** for events (BH1 enumeration) |
| Bapco Energies group, `bapcoenergies.com` (media centre, annual report) | en, ar | home page once; then a bot-manager challenge | **SOURCE_BLOCKED**; discovery only if ordinary access returns |
| Bapco Upstream (formerly Tatweer Petroleum) | — | no own site reached; old domain does not resolve | **discovery only**, through the group site |
| Bapco Gas (Banagas) | — | no own site reached; old domain does not resolve | **discovery only**, through the group site |
| Ministry of Oil and Environment site, `moo.gov.bh` | — | placeholder page only | **reject** as a source; its statistics are read on `data.gov.bh` |
| Bahrain News Agency, `bna.bh` | ar, en | no: HTTP 405 twice | **SOURCE_BLOCKED**; official-statement role, reached only through search |
| JODI Oil / Gas | en | yes | **derived facts only** (no Bahrain value read) |
| U.S. EIA: Bahrain | en | brief readable, dated December 2016; country data page is a script shell | **derived facts only** (stale) |
| GCC-Stat (`gccstat.org`, Marsa data portal) | ar, en | yes | **derived facts only** (GCC aggregates on the pages read) |
| Akhbar Al Khaleej | ar | yes, static section listing | **discovery only** (media) |
| Al-Ayam | ar | no: HTTP 403 | **SOURCE_BLOCKED**; discovery through search only |
| Al-Watan | ar | no: HTTP 403 | **SOURCE_BLOCKED**; discovery through search only |
| Gulf Daily News / GDN Online | en | yes; search endpoint did not answer a query | **discovery only** (media) |
| Reuters | en | no: the fetch tool refuses the domain | discovery through search only |
| S&P Global Commodity Insights | en | no: HTTP 403 | discovery through search only |
| Natural Earth admin-1 | — | local file | **adopt** for boundaries, with the rulings in §1 |

The two findings that shape everything else:

1. **Bahrain's official open-data portal is the best-licensed national source in the Gulf set seen
   so far**: annual oil, gas, refining and electricity series under an explicit open licence, with a
   working public API. It is annual and national, so it is context and can never attribute a change
   to an event.
2. **No source reached publishes event-level outage or incident notices.** The operator listings
   sampled carry corporate news. Official statements about incidents reach the public through the
   state news agency, which refused automated access.

---

## 1. Geography — four governorates today, five in Natural Earth

**Current first-level divisions: 4 governorates (محافظة, *muḥāfaẓa*).** Official source read this
session: the Survey and Land Registration Bureau's dataset *Area by Governorate* on `data.gov.bh`
(dataset `02-area-by-governorate-2023`, modified 2026-11-04). Its 2023 and 2024 rows list exactly
four units plus a total: **Capital (العاصمة), Muharraq (المحرق), Northern (الشمالية), Southern
(الجنوبية)**. Its description says the governorates "were redivided into 4 governorates instead of 5
in 2014". Rows up to 2013 carry a fifth unit, **Central (الوسطى)**. The Information and eGovernment
Authority's population dataset likewise refers to "the four governorates".

**Natural Earth `ne_10m_admin_1` (the cached `data/raw/ne_10m_admin_1.geojson`) carries 5 `BHR`
features**, all `type_en = "Governorate"`:

| ISO 3166-2 | Natural Earth `name` | `name_ar` in the file | English | Today |
|---|---|---|---|---|
| BH-13 | Al Manāmah | محافظة العاصمة | Capital | current, but drawn with its pre-2014 extent |
| BH-14 | Al Janūbīyah | جنوبية | Southern | current; includes the Hawar Islands polygons |
| BH-15 | Al Muḩarraq | محافظة المحرق | Muharraq | current |
| BH-16 | Al Wusţá | محافظة الوسطى | Central | **abolished in 2014** |
| BH-17 | Ash Shamālīyah | شمالية | Northern | current |

**How Natural Earth differs.**

- It still draws the Central governorate (BH-16). That the code was later withdrawn from ISO 3166-2
  is **(not verified this session)**; the abolition itself is sourced above.
- Its other polygons are therefore pre-2014 shapes. The official area series shows the Capital
  governorate at 38 km² in 2012 and 78 km² in 2015, so the Capital governorate as it exists today
  is about twice the area Natural Earth draws for BH-13. Which localities moved to which
  governorate was **not verified this session**.
- Consequence: a present-day governorate name taken from a source cannot be assumed to fall inside
  the Natural Earth polygon with the same code. A place a source puts in today's Capital
  governorate may lie inside Natural Earth's BH-16.

**Ruling on the abolished unit (BH-16).** No event is ever placed in BH-16. The polygon stays on the
map, because `units_expected` is the Natural Earth count (5) and the country outline would have a
hole without it, but it is drawn as a former unit and carries no event count: an absence there
means "not applicable", never "nothing happened". An event whose source locates it in the area of
the former Central governorate is recorded at **country level**. It is not reassigned to BH-13,
BH-14 or BH-17 by this project's own judgment, because the redistribution of localities was not
verified and the drawn shapes predate it. The pipeline today suppresses the event count only for the
status `disputed_unassigned`; the draft proposes a new status, `abolished_unassigned`, with the same
behaviour. That needs the lead's decision (see the draft's rulings).

**Microstate rule.** Bahrain's official land area is 787.79 km² (2024, same dataset). At that scale
a governorate is not a region in the sense the rest of this project uses: a governorate can hold a
single facility of a given class, so a governorate plus an asset class can identify the facility.
Therefore:

- **Kinetic and security events default to COUNTRY level** (`geography_precision: "country"`,
  `admin1_code: null`), whatever the source says.
- **Industrial and natural-hazard events use a governorate only where a safety reviewer finds it
  non-identifying**; otherwise country level.
- No locality, island, industrial-area or district name goes into a summary.

**Join hazards.** Join by ISO code. Natural Earth names the Capital governorate "Al Manāmah" (the
city's name), writes two Arabic names without the article and the word محافظة, and uses diacritics
that no source will match. Sources also use "Manama" for both the city and, loosely, the
governorate.

**Disputed or special units.** None is treated as disputed. The Hawar Islands are drawn inside
BH-14; their status was settled between Bahrain and Qatar by the International Court of Justice in
2001 **(not verified this session)**. Recorded in the draft as a note, in the same manner as the
Saudi file's note on the former Neutral Zone.

---

## 2. Source-by-source audit

### 2.1 Bahrain Open Data Portal — `data.gov.bh` (Information and eGovernment Authority)

- **What it is:** the government's open-data portal, run by the iGA. Arabic and English.
- **What it publishes:** annual national statistical series. Theme *Oil & Gas*, 7 datasets, all
  published by the Ministry of Oil and Environment: Bahrain-field crude production; associated gas
  production; non-associated gas production; refinery throughput (crude and feedstock); refinery
  production; crude imports; local sales of petroleum products. Theme *Energy and Water*, 11
  datasets, of which three are EWA electricity series: electricity consumption (2008-2025),
  sectoral consumption, and electricity generation by power station (2008-2025, 8 rows a year).
  No event-level content of any kind.
- **How it is reached:** the catalogue page (`/explore/`) is a script-only shell (unrendered
  template placeholders). The portal's own public API works without a key:
  `/api/datasets/1.0/search/?q=…` for the catalogue and `/api/records/1.0/search/?dataset=<id>` for
  rows; `/api/records/1.0/analyze/` returns sums. The v2.1 path returned HTTP 400 to the query
  forms tried.
- **Cadence:** annual values; the oil and gas datasets were modified between 2026-08-06 and
  2026-11-11, the EWA ones on 2026-09-13. Latest year in every series read: 2025.
- **Licence, as read in full:** *Bahrain Open Government Data License, Version 1.1 – 1 November
  2026* (`nea.gov.bh/Documents/OpenDataLicense.pdf`, 5 pages, bilingual). Grants "royalty-free,
  non-exclusive use" for "sharing, copying, distributing or transmitting", "adapting", use in
  applications and commercialising them (§3.1). Conditions (§3.3): state the source **and the date
  the datasets were extracted**; state that any analysis or transformation is the user's own and is
  not attributed to the iGA or the publishing entity; carry the licence's attribution sentence;
  stop using and remove the data if the iGA or the entity asks after a breach. §3.4 prohibits
  presenting the data "in a false, inaccurate, or misleading manner". The API's own `license` field
  is empty for every dataset; the licence applies by the portal's terms, not by dataset metadata.
- **Known limits:** annual only; units live in titles and field names, not in a unit field; one
  title and its values disagree on the unit (see below).
- **Decision: adopt** as national context. Raw redistribution is permitted with the conditions
  above. Never an event source: an annual change with no stated cause is not an event.

Figures read this session (annual, 2025 unless stated):

| Series | Value | Unit as titled | Note |
|---|---|---|---|
| Bahrain-field crude oil production | 13,505 | thousand US barrels | onshore field only, as titled; 14,430 in 2022 |
| Non-associated gas production | 560,481 | million cubic feet | 637,774 in 2024 |
| Associated gas production | 305,091 | million cubic feet | |
| Refinery throughput, crude and feedstock | 114,159 | thousand US barrels | **our sum** of the dataset's three category rows |
| Refinery production | 117,596 | thousand US barrels | 94,494 in 2022 |
| Electricity consumption | 19,391.6 | GWh | equals the sum of the four sector rows |
| Sectoral consumption | domestic 9,384.1; commercial 6,354.0; industrial 3,603.1; agricultural 50.3 | GWh | |

**Unit defect, recorded not guessed.** The dataset *Electricity Generation by Power Stations* is
titled "(MWH)". Its rows sum to 20,298.5 for 2025, against consumption of 19,391.6 GWh in the
sibling dataset, so the values are almost certainly GWh. Because the title and the magnitude
disagree, the generation total is **not carried into the profile**.

**Scope defect, recorded.** IRENA reports national generation of 37,523 GWh in 2023 (2.2). The EWA
rows sum to 19,285 in the same year. The EWA series is therefore about half the national total and
is a public-supply series, not national generation; what makes up the difference is not stated on
either page.

### 2.2 IRENA — Energy Profile: Bahrain

- **What it is:** the International Renewable Energy Agency's four-page statistical profile, "Last
  updated on: 22 September, 2025". English. PDF, 240 KB, read in full.
- **What it publishes:** national aggregates. Total energy supply 2022: **672,854 TJ**, of which
  gas 89%, oil 11%, coal and others 0%, renewables 0%, no nuclear. Installed electricity capacity
  2024: **9,954 MW** (non-renewable 9,885; renewable 69). Generation 2023: **37,523 GWh**
  (non-renewable 37,429; renewable 94). Power-sector CO2 emissions are shown as 100% gas, 0% coal
  and others, 0% oil.
- **How reached:** direct PDF link under `irena.org/-/media/Files/IRENA/Agency/Statistics/
  Statistical_Profiles/Middle-East/`.
- **Cadence:** annual. **Licence:** IRENA copyright; the terms page was **not read this session**.
- **Decision: adopt** as national context, and as the sourced zero for coal. Facts cited; the PDF is
  not vendored until the terms are read.

### 2.3 Electricity and Water Authority (EWA) — `ewa.bh`

- **What it is:** the state electricity and water utility. Arabic and English.
- **What it publishes on the site:** a news listing only. English: `ewa.bh/en/news`, 69 items, 9 a
  page, `news?page=N` (8 pages), year filters 2024, 2025 and 2026. Arabic: `ewa.bh/ar/news`, 79
  items, 9 pages. The Arabic listing is larger and more current (newest 2026-11-11 against
  2026-10-13 in English), so the Arabic listing is the primary one. The first page in each language
  carried tariff, billing-service, award, partnership and inauguration items; **no outage or
  interruption statement** was among the 18 items seen. The sitemap lists no statistics page, no
  annual report, no outage or interruption page and no open-data page. The home page has an "EWA in
  Numbers" block whose values do not render without scripts.
- **Archive depth:** the listing begins in 2024. **2022 and 2023 cannot be enumerated here.**
- **Terms, as read:** "Reproduction is prohibited other than in accordance with the copyright
  notice"; and "You may not create a link to this website from another website or document [without]
  EWA's prior written consent." No open licence.
- **Decision: discovery only.** The listing is the BH2 enumeration endpoint. **The linking clause is
  a decision for the lead**: this project cites sources by link. Until decided, an EWA statement is
  cited as carried by the state news agency or the press, with EWA named as the origin.

### 2.4 EWA annual statistics books

- **What they are:** an annual statistical book, Arabic and English, found by search on
  `legacy.ewa.bh` and older `ewa.bh` paths (editions 2016, 2017, 2018, 2021 and 2022 appear in the
  results). The search summary says their tables include installed capacity by station; **no
  edition was read**.
- **How reached:** the 2022 PDF exceeds the fetch tool's 10 MB limit; the 2021 path on the current
  site returns the site's "page not found"; the directory listing returns HTTP 404. No edition later
  than 2022 was found.
- **Decision: derived facts only**, and only for national totals (installed capacity, peak load,
  customer count) if a person opens the file. Per-station tables, network diagrams and substation
  lists are not to be read (§5).

### 2.5 Bapco Refining — `bapco.net`

- **What it is:** the refining company's own site (a banner says the business is now Bapco Refining,
  part of the Bapco Energies group). English pages; annual reports are listed in English and Arabic.
- **What it publishes:** press releases at `/en/page/press-releases` (8 items on the first page, a
  "Next" link, item pattern `/en/news-article/{slug}`; the first page runs from 2024-06-02 to
  2025-07-31). All eight items seen are corporate: visits, awards, a safe-hours record, a project
  inauguration, a partnership, an emergency-preparedness meeting. No operational incident notice.
  Annual reports are listed for 2021, 2022 and 2023, without exposed PDF links; none was read.
- **Terms, as read:** content "owned by the Company or its licensors"; users must not "reproduce,
  distribute, modify, create derivative works of" it or "republish any part of the Website on
  another website". No open licence.
- **Decision: discovery only.** BH1 enumeration endpoint. Facts cited by link; nothing vendored.

### 2.6 Bapco Energies (the holding group, formerly nogaholding) — `bapcoenergies.com`

- **What it is:** the group's site. The home page, read once, lists the operating companies: Bapco
  Refining, Bapco Upstream, Bapco Gas, Bapco Gas Expansion, Bapco Tazweed, Bapco Air Fueling,
  BeVentures, Bahrain LNG, BAC Jet Fuel, GPIC and ASRY. That the group is state-owned and was
  formerly named nogaholding is **(not verified this session)**.
- **What it publishes:** a media centre (`/media-centre`, press releases at
  `/media-centre/press-releases/{slug}`, Arabic under `/ar/`), an investors section, and an annual
  report (a 2024 report address appears in search results).
- **How reached:** the home page answered once. Every later request (media centre, terms of use,
  annual report) was redirected to a third-party bot-manager challenge. **SOURCE_BLOCKED**; not
  followed.
- **Terms:** not read (blocked).
- **Decision: discovery only**, blocked. If a later ordinary request succeeds, the press-release
  archive is the natural BH1 enumeration for the whole group; the annual report would be
  derived-facts-only for national aggregates.

### 2.7 Bapco Upstream (formerly Tatweer Petroleum) and Bapco Gas (Banagas)

- **Own sites:** none reached. `tatweerpetroleum.com` and `banagas.com` no longer resolve (DNS);
  `bapcoupstream.com` closed the connection; `bapcogas.com` returned an empty page. One search found
  no standalone site for either: both are presented on the group site (2.6), which is blocked.
- **Decision: discovery only**, through the group's press releases and the state news agency. Their
  national production totals are read on `data.gov.bh` (2.1).

### 2.8 Ministry of Oil and Environment — `moo.gov.bh`

- **How reached:** `www.moo.gov.bh` closed the connection; `moo.gov.bh/Home.aspx` returned a page
  containing only "Welcome to NOGA" (the former National Oil and Gas Authority's name). No news,
  statistics or publications were reachable. The domain itself is named as the ministry's by a
  third-party trade guide only.
- **Decision: reject** the site as a source. The ministry's statistics are published on
  `data.gov.bh` (2.1) and are adopted there; its statements are a state-news-agency matter (2.9).

### 2.9 Bahrain News Agency (BNA) — `bna.bh`

- **What it is:** the state news agency, Arabic and English. It is where ministry, EWA and operator
  statements are carried **(role as the task describes it; not verified, because the site was not
  read)**.
- **How reached:** `https://www.bna.bh/en/` and `https://www.bna.bh/` both returned **HTTP 405**.
  **SOURCE_BLOCKED.** No archive or search endpoint could be examined.
- **Decision: discovery only, through search.** Where a BNA page carries an official statement, the
  record's `source_role` is `official` or `government` with BNA as publisher. A newspaper item that
  reprints the same BNA text is a syndicated copy, not a second source.

### 2.10 JODI — Joint Organisations Data Initiative

- **What it is:** monthly national oil and gas flows, self-reported. English.
- **How reached:** download page readable; annual CSVs 2002-2026, a REST API with a free account.
  "JODI-Oil World Database: 2nd update on 21 October 2026". Bahrain appears in the participating
  list; under which partner organisation is not legible on the page. JODI-Gas participation not
  confirmed. **No Bahrain value was read.**
- **Licence:** only "© Copyright JODI 2026"; no terms text.
- **Decision: derived facts only.** National monthly context. A monthly dip with no stated cause is
  not an event.

### 2.11 U.S. EIA

- **What it is:** a short country analysis brief, `eia.gov/international/content/analysis/
  countries_short/Bahrain/`, **last updated December 2016**. The country data pages
  (`/international/analysis/country/BHR`, `/international/overview/country/BHR`) returned
  navigation only: the figures load by script.
- **Decision: derived facts only**, and stale. Ten years old; nothing from it enters the profile.
  The brief also carries field-level and pipeline material that this project does not read (§5).
  Public domain for EIA's own text.

### 2.12 GCC-Stat

- **What it is:** the GCC Statistical Center (Muscat). Arabic by default, English available. A
  statistics portal (`dp.marsa.gccstat.org`) with an Energy domain and country profiles, and a
  renewable-energy platform.
- **What was read:** GCC-wide aggregates only (for 2024: marketed gas, electricity production,
  crude production). No Bahrain energy figure appeared on the pages read; the data explorer was not
  driven.
- **Terms, as read (Arabic):** content may be freely copied, used, published, translated or
  modified, with the source cited and modifications declared; third-party rights excepted; governed
  by Omani law. Not a named open licence.
- **Decision: derived facts only**, as a cross-check on the national series. It republishes member
  states' own figures, so it is not independent of 2.1.

### 2.13 Bahraini press

| Outlet | Language | Reached | What was found | Role |
|---|---|---|---|---|
| Akhbar Al Khaleej (أخبار الخليج) | ar | yes | static site; section listing `/news/section/BNEW/{offset}` in steps of 25, offsets to 35,850; items carry relative timestamps only; a page-image edition by issue number; no search box; the masthead carries Gregorian and Hijri dates | media; discovery and corroboration |
| Al-Ayam (الأيام) | ar | HTTP 403 | nothing read | media; discovery through search only |
| Al-Watan (الوطن) | ar | HTTP 403 | nothing read | media; discovery through search only |
| Gulf Daily News / GDN Online | en | yes | sections and `/Details/{id}/{slug}` articles; `/Search?q=…` returned only the empty search form; sign-in and subscribe links present, gating not established | media; discovery and corroboration |

- All four are domestic outlets. On infrastructure incidents they are expected mostly to carry
  official statements, so agreement between them is one account repeated, not several. That Gulf
  Daily News and Akhbar Al Khaleej share a publisher is **(not verified this session)**; until it
  is, the two are not counted as independent of each other.
- **Decision: discovery only.** A press item can be a record's citation when it reports the effect
  at the time; `source_role` is `media`.

### 2.14 International agencies and energy press

- **Reuters:** the fetch tool refuses `reuters.com`. **S&P Global Commodity Insights:** HTTP 403.
  Neither was read. Both are reachable only as search results.
- **Decision: discovery only, through search** (lane BH3), as independent corroboration of a
  domestic account. A wire story that quotes the state news agency is still one account.

### 2.15 Natural Earth admin-1

- Public domain; five `BHR` features (§1). **Adopt** for boundaries with the BH-16 ruling. Not a
  current administrative map of Bahrain and must not be described as one.

### 2.16 Not audited

MEED, Zawya, the Daily Tribune (`newsofbahrain.com`), Oxford Business Group, the IEA country page
(HTTP 403) and the Energy Institute review were seen only as search results or refusals. They are
**not yet researched**, not rejected.

---

## 3. Reporting bias

Stated neutrally, as properties of the sources rather than of events.

- The hydrocarbon operators belong to one state holding group and the electricity utility is a
  state authority. Their own sites, as sampled, publish corporate and service news.
- Official accounts of incidents are issued as statements and carried by the state news agency.
  Domestic newspapers largely reproduce them. An account that appears in four outlets is usually
  one statement.
- No regulator, operator or ministry page reached publishes an outage register, an interruption
  log, or reliability statistics.
- English-language international coverage of Bahrain is thin outside major events, so the record
  will lean towards events large enough to draw a wire story.
- The enumerable operator archives are shallow: EWA's listing begins in 2024, and the first page of
  Bapco Refining's begins in mid-2024.
- For any security event, the parties' statements are the only accounts and are not independent.

**Reporting environment chosen for the draft: `media_only`** — "Operators and authorities do not
publish event-level outage reports. Events come from media and company statements, so most smaller
disruptions will not appear." This is what the pages sampled support. `corporate_disclosure` is the
alternative if Wave B finds that operator and ministry statements, carried by the state agency, are
in practice the origin of most records. The choice is provisional and is the lead's to confirm.

## 4. Low reported incidents is not low disruption

A small Bahrain corpus is the expected result of this reporting environment, not a measurement.
There is no event register to count against, so the coverage of whatever Wave B finds **cannot be
computed** and must read "unknown". Technical trips, partial unit outages and local supply
interruptions are the least likely to be published at all. The inclusion thresholds add to this:
the absolute figures in clauses 4 and 5 (about 500 MW; about 100,000 customers) were written for
much larger systems, and an interruption that is large relative to Bahrain's public supply can
still fall below them. The dashboard must present a sparse Bahrain record as "few records found",
never as "few disruptions". Annual national series (2.1) can show that output changed between
years; they cannot say why, and must not be turned into an event or a loss estimate.

## 5. Fields that must never be read

- **`data.gov.bh`, electricity generation by power station:** the per-station rows
  (`power_stations`). Only a national sum through the API's `analyze` endpoint. A refresh after 2025
  would carry per-station output for a period that may fall inside a campaign.
- **`data.gov.bh`, refinery throughput:** the crude-origin category split. Only the total.
- **`data.gov.bh`, crude imports:** the dataset and its description (supply-route wording). Not
  carried into any file.
- **Any refining or gas-processing series for 2026 or later** while a campaign is recorded as
  active for Bahrain: the refining series describes a single refinery and the gas series a single
  operating group, so a national figure is a facility's operating level. The profile stops at 2025.
- **EWA statistics books:** per-station capacity tables, network maps, single-line diagrams,
  substation and feeder lists, interconnection detail.
- **EIA brief:** field-level, pipeline-capacity and facility-capacity sentences.
- **Any news item:** restart or repair progress, operating rate, remaining capacity or current
  outage status after an attack; coordinates, distances, weapon or method detail, defences;
  locality below governorate; any characterisation of a facility's importance; shipping, export
  route or interconnector material.
- **Hijri dates** on mastheads are kept as `source_date_text` with `date_calendar: "hijri"` and a
  Gregorian `normalized_date`; a Hijri year is never read as Gregorian.

## 6. Attribution if adopted

> National series: datasets provided by the **Ministry of Oil and Environment** and the
> **Electricity and Water Authority** via www.data.gov.bh, governed by the Bahrain Open Government
> Data License available at www.nea.gov.bh/Documents/OpenDataLicense.pdf; extracted 2026-11-11;
> sums and selections are this project's own and are not attributed to the iGA or the publishing
> entity. National energy supply, capacity and generation: **IRENA**, Energy Profile: Bahrain
> (22 September 2025). Boundaries: **Natural Earth** (public domain; pre-2014 governorates).

The licence also requires its liability sentence (§3.3(c)) wherever the datasets are carried.
