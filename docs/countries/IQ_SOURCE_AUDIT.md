# Iraq — source audit

Written 2026-11-11 by the Iraq source-audit lane (iteration 19, Wave A). **Nothing in this document
is wired into the pipeline or a published number.** It records, for every candidate source, what the
source is, how it can be reached, under what terms, and whether this project should adopt it.
Incident research is a separate lane (Wave B) and is deliberately not done here.

Scope boundary applies in full (project `CLAUDE.md`, and
`docs/CURRENT_EVENT_PUBLICATION_POLICY.md` §1-§3). Iraq is treated at **governorate level at most**.
This audit does not assess the importance, vulnerability, protection, interdependence or routing of
any facility. It records no facility capacity, no export route, no port or terminal breakdown and no
facility status.

Every statement below was read on a page during this session unless it is marked **(not verified
this session)**. Pages were read through an ordinary fetch that returns a text rendering; where a
site refused it, that is recorded as a finding about access, and nothing was done to get around it.
Web searches used by this audit: **3 of 4**.

---

## 0. Summary

| Source | Role | Access on 2026-11-11 | Decision |
|---|---|---|---|
| Ministry of Oil (`oil.gov.iq`) | official | **blocked**: security-check page | **discovery only** (read through agencies) |
| SOMO (`somooil.gov.iq`) | official, state marketer | reachable; report listings not rendered | **derived facts only** (national monthly total) |
| Ministry of Electricity (`moelc.gov.iq`) | official | **blocked**: security-check page | **discovery only** |
| Iraqi News Agency (`ina.iq`) | state news agency | **blocked**: HTTP 403 | **discovery only** |
| Basra Oil Company, North Oil Company, Midland and North Refineries Companies (`*.oil.gov.iq`, `nocoil.gov.iq`) | operator (state) | **blocked**: security-check page | **discovery only** |
| South Refineries Company (`src.gov.iq`) | operator (state) | reachable, dated news list | **adopt** for event search |
| KRG Ministry of Natural Resources, KRG Ministry of Electricity (`gov.krd`, `moel.gov.krd`) | official (regional government) | **blocked**: HTTP 403 | **discovery only** |
| APIKUR | industry association | own site not reached | **discovery only** |
| Iraq Oil Report | subscription energy press | headlines only; paywall | **reject** as a citation; discovery only |
| Shafaq News | media (Iraqi news agency) | reachable, paged, dated, ar/en/ku | **adopt** for event search |
| Rudaw | media (Kurdistan Region) | articles reachable; listings not rendered | **adopt** for event search |
| Kurdistan24 | media (Kurdistan Region) | reachable, paged, undated listing | **adopt** for event search |
| Reuters, AP | news agencies | refused by the fetch tool | **adopt** for event search, by search result only |
| S&P Global Commodity Insights | energy press | HTTP 403 | **discovery only** |
| Argus | energy press | empty page returned | **discovery only** |
| OPEC (ASB, MOMR) | intergovernmental | HTTP 402 | **derived facts only**, manual |
| JODI | intergovernmental | reachable | **derived facts only** |
| U.S. EIA country analysis brief | government (US) | reachable | **adopt** (national context) |
| IEA, Energy Institute | statistics | HTTP 403 | **derived facts only**, manual |
| Constitution of Iraq (Constitute Project text) | legal text | reachable | **adopt** (geography ruling) |
| Official Gazette / Ministry of Justice (`moj.gov.iq`) | official | connection closed | **discovery only** |
| Ministry of Planning, statistics authority (`mop.gov.iq`, `cosit.gov.iq`) | official | home page only; statistics site closed the connection | **discovery only** |
| Natural Earth admin-1 | boundaries | cached in repo | **adopt** |
| GEM Global Integrated Power Tracker | dataset | not acquired | denominator candidate, **not yet acquired** |
| WRI Global Power Plant Database v1.3 | dataset | cached in repo | **reject** as denominator |
| OpenStreetMap | dataset | not queried | **reject** for any Iraqi layer |
| English Wikipedia | aggregator | reachable | **discovery only** |

The main finding: **almost every Iraqi official site refuses automated reading.** The oil and
electricity ministries and four of the five state company sites tested sit behind the same
security-check page; the state news agency and the Kurdistan Regional Government portal return
HTTP 403. Official statements therefore reach this project only as carried by media, and a media
copy of a ministry statement is one source, not two.

---

## 1. Geography — governorates (محافظات, *muḥāfaẓāt*)

### 1.1 Current divisions

Iraq's first-level unit is the governorate (محافظة). The Constitution of 2005 says the federal
system is made up of "a decentralized capital, regions, and governorates" (Art. 116) and recognises
the region of Kurdistan as a federal region (Art. 117, First). Text read at
`https://www.constituteproject.org/constitution/Iraq_2005`.

**Count: 19 governorates since 2025; 18 before.** The nineteenth is Halabja (حلبجة). The steps, as
read this session:

| Step | Date | Source read |
|---|---|---|
| Federal Council of Ministers approves the draft law | 13 March 2023 | Asharq News, 2025-04-29, `https://asharq.com/politics/133512/العراق-حلبجة-المحافظة-رقم-19/` |
| Council of Representatives passes the law | 14 April 2025 | Kurdistan24, 2025-04-14, `https://www.kurdistan24.net/en/story/834969`; Asharq News as above |
| President ratifies the law | 29 April 2025 (a Tuesday) | Asharq News as above |
| Publication in the Official Gazette (الوقائع العراقية) | reported as 5 May 2025 | **search-result summary only; the gazette issue was not opened** (`moj.gov.iq` closed the connection) |
| Federal Supreme Court rejects challenges to the law | reported 22 July 2025 | Kurdistan24 Arabic, 2025-07-22, `https://www.kurdistan24.net/ar/story/853315` (the article gives two dates for the ruling) |

Asharq describes Halabja as "المحافظة رقم 19 في العراق، والرابعة في إقليم كردستان" (governorate
number 19 in Iraq and the fourth in the Kurdistan Region). The Kurdistan Regional Government had
treated Halabja as a governorate since 2014 (English Wikipedia, citing a 13 March 2014 report;
**discovery only, not verified at a primary source**).

Every source in this table is media. **No official page stating the count was reached**: the
presidency, parliament, gazette and statistics sites all refused or dropped the request. The count
of 19 is therefore well reported but not read at an official source in this session.

A proposal to create a further governorate was reported in April 2025 (English Wikipedia, citing an
Arabic news report). It is a proposal, not a division, and is not used.

### 1.2 The Kurdistan Region

The Kurdistan Region is **part of Iraq**: a federal region recognised by the Constitution
(Art. 117), which contains governorates. It is never a separate system here. Its governorates are
Erbil, Duhok, As-Sulaymaniyah and, since the 2025 law, Halabja. They are shown as Iraqi
governorates like any other. Two things follow for sources, not for the map:

- Oil, gas and electricity in the Region are administered by regional ministries, so there are two
  official voices (Baghdad and Erbil) and they sometimes describe the same event differently.
- EIA reports electricity for "Federal Iraq" and for the Kurdistan Region separately. A "national"
  electricity figure is often a federal-grid figure. Each profile row says which.

### 1.3 Natural Earth

Natural Earth `ne_10m_admin_1` (cached at `data/raw/ne_10m_admin_1.geojson`) has **18** `IRQ`
features, all `type_en = "Province"`:

| NE code | Natural Earth `name` | Arabic (`name_ar`) | Common alternatives |
|---|---|---|---|
| IQ-AN | Al-Anbar | محافظة الأنبار | Anbar; Ramadi (capital) |
| IQ-AR | Arbil | محافظة أربيل | Erbil, Irbil, Hewlêr |
| IQ-BA | Al-Basrah | محافظة البصرة | Basra |
| IQ-BB | Babil | محافظة بابل | Babylon; Hilla (capital) |
| IQ-BG | Baghdad | محافظة بغداد | — |
| IQ-DA | Dihok | محافظة دهوك | Duhok, Dahuk |
| IQ-DI | Diyala | محافظة ديالى | — |
| IQ-DQ | Dhi-Qar | ذي قار | Thi Qar; Nasiriyah (capital) |
| IQ-KA | Karbala' | محافظة كربلاء | Kerbala |
| IQ-MA | Maysan | محافظة ميسان | Missan; Amarah (capital) |
| IQ-MU | Al-Muthannia | محافظة المثنى | Al-Muthanna; Samawah (capital) |
| IQ-NA | An-Najaf | محافظة النجف | Najaf |
| IQ-NI | Ninawa | محافظة نينوى | Nineveh; Mosul (capital) |
| IQ-QA | Al-Qādisiyyah | محافظة القادسية | Diwaniyah (capital, and common name) |
| IQ-SD | Sala ad-Din | صلاح الدين | Salah al-Din, Salahuddin; Tikrit (capital) |
| IQ-SU | As-Sulaymaniyah | محافظة السليمانية | Sulaimani, Slemani |
| IQ-TS | At-Ta'mim | كركوك | **Kirkuk** |
| IQ-WA | Wasit | محافظة واسط | Kut (capital) |

**Differences from current divisions, and join hazards:**

- **Halabja has no feature.** Natural Earth draws its area inside As-Sulaymaniyah (IQ-SU). An event
  reported in Halabja governorate is placed in IQ-SU, and the record's text says so. Halabja is
  never silently dropped and never invented as a nineteenth polygon.
- **Kirkuk is coded IQ-TS and named "At-Ta'mim"**, the governorate's former name. English
  Wikipedia's transcription of ISO 3166-2:IQ lists Kirkuk as IQ-KI, and lists 18 governorates plus
  one region code, IQ-KR, added on 2022-03-03, with no Halabja entry. ISO's own page returned
  HTTP 403, so that is **not verified at ISO**. Join on the Natural Earth code and keep an alias
  for IQ-KI and for "Kirkuk".
- Natural Earth spells Muthanna **"Al-Muthannia"**, Erbil **"Arbil"**, Duhok **"Dihok"** and
  Salah ad-Din **"Sala ad-Din"**. None matches the spellings in news copy.
- Sources name a governorate by its capital as often as by its name (Mosul for Ninawa, Nasiriyah
  for Dhi Qar, Kut for Wasit, Amarah for Maysan, Diwaniyah for Al-Qādisiyyah). "Basra", "Kirkuk",
  "Baghdad", "Erbil" and "Najaf" are each both a city and a governorate.
- Natural Earth's `region` attribute tags Arbil, Dihok and As-Sulaymaniyah "Kurdistan" and the
  other fifteen "Iraq". That attribute is a label in the source file. It is not used to split the
  country.
- Join by code with a curated alias table in Arabic, English and Kurdish; never by English name.

### 1.4 Disputed internal territories

Article 140 of the Constitution provides for a process, including a referendum "in Kirkuk and other
disputed territories", to "determine the will of their citizens", with a deadline of 31 December
2007. The Constitution names Kirkuk and does not list the other areas. Their administration is
contested between the federal government and the Kurdistan Regional Government. They are commonly
described as parts of Ninawa, Diyala and Salah ad-Din governorates as well as Kirkuk **(the list
beyond Kirkuk was not verified at a primary source this session)**.

**This project does not resolve them.** The ruling is an analytic choice, not a statement about
which authority should administer any area: **an event is placed by the governorate Natural Earth
draws at the place the source names.** No record says which authority a disputed place belongs to.
Where a source places an event only by a contested description, the record keeps the source's
wording and the Natural Earth governorate.

---

## 2. Source-by-source audit

### 2.1 Ministry of Oil — `oil.gov.iq`

- **What it is:** the federal ministry; publishes ministry statements and, each month, export
  totals **(content not verified this session)**.
- **Language:** Arabic (English pages exist, not seen).
- **Access:** `https://oil.gov.iq/` answers HTTP 307 to `/verify/index.php?url=/`, a page titled
  "One More Step — Please complete the security check to access oil.gov.iq" with a verification
  code image. That is a bot challenge: **SOURCE_BLOCKED**. Not worked around.
- **Cadence:** event-driven statements; monthly export announcement.
- **Terms:** not readable.
- **Decision: discovery only.** Ministry statements are read as carried by agencies and media, and
  the record's source role is then `media`, not `official`, unless the ministry's own page is
  opened by a person.

### 2.2 SOMO — State Oil Marketing Organization (شركة تسويق النفط), `somooil.gov.iq`

- **What it is:** the state crude and products marketer, under the Ministry of Oil.
- **Language:** Arabic only (no English edition found; `/en` returns the Arabic site).
- **What it publishes:** a monthly report on crude and products exports (`/ar/researches`), a
  monthly world-market report (`/ar/reports`), an export chart (`/ar/exports/chart`), news
  (`/ar/news`, items at `/ar/news/<id>`), tenders, events, final accounts. The home page also shows
  a breakdown of exports below the national total and a section on vessel positions.
- **Access:** reachable, no challenge. But `/ar/researches`, `/ar/reports` and individual news
  items returned only the site's home-page content to an ordinary fetch: **the listings and article
  bodies are not rendered without a browser.** The chart page did show one headline figure:
  "صادرات النفط الخام … الشهر: كانون الثاني 2026 … الكمية المصدّرة: 107.6M برميل". No other
  monthly total was visible as text. The news list shows seven undated items (ids 111 to 127).
- **Cadence:** monthly.
- **Terms:** footer "© 2026 شركة تسويق النفط (سومو)", all rights reserved. No terms page.
- **Fields that must never be read:** the breakdown of exports by loading point, by destination or
  by buyer; the vessel-position section; anything about export arrangements. Several news titles on
  the list concern exactly those subjects and are out of scope. Only the **national monthly total**
  and any sentence in which SOMO or the ministry **attributes a material change to a disruption**
  are in scope.
- **Decision: derived facts only.** National monthly totals as context. A change between two
  months with no official attribution is not an event.

### 2.3 Ministry of Electricity — `moelc.gov.iq`

- **What it is:** the federal ministry, which runs generation, transmission and distribution
  outside the Kurdistan Region; issues statements on shortfalls and system-wide failures
  **(content not verified this session)**.
- **Language:** Arabic.
- **Access:** same security-check page as the Ministry of Oil. **SOURCE_BLOCKED.**
- **Terms:** not readable.
- **Decision: discovery only**; statements read through agencies and media.

### 2.4 Iraqi News Agency — `ina.iq`

- **What it is:** the state news agency; the usual carrier of ministry statements. Editions in
  Arabic, English and Kurdish **(not verified this session)**.
- **Access:** `https://ina.iq/`, `https://www.ina.iq/` and `https://ina.iq/eng/` each returned
  **HTTP 403**. **SOURCE_BLOCKED.**
- **Decision: discovery only.** An INA page found by search and cited by a media report may be
  recorded by URL as unopened (`opened: false`); it cannot be the source that carries a record.

### 2.5 State oil companies

- **South Refineries Company (شركة مصافي الجنوب), `src.gov.iq`.** Reachable, Arabic with an English
  edition. `news.aspx` lists 21 items, each dated, from 21 September 2024 to 9 November 2026;
  detail pages `news-detail.aspx?id=N` (ids seen 15 to 1073) carry date and body in the HTML. Items
  are notices, visits, training, project and maintenance notes and some statements. No terms page;
  footer credit only. **Decision: adopt for event search** (role `operator`). It covers one company
  in the south, so silence elsewhere means nothing.
- **Basra Oil Company (`boc.oil.gov.iq`), Midland Refineries Company (`mrc.oil.gov.iq`), North
  Refineries Company (`nrc.oil.gov.iq`):** each answers with the security-check redirect.
  **SOURCE_BLOCKED.**
- **North Oil Company:** `noc.oil.gov.iq` redirects (301) to `nocoil.gov.iq`, which answers with
  the same security-check redirect. **SOURCE_BLOCKED.**
- **Decision for the blocked four: discovery only.**
- Other state companies were **not tested**.

### 2.6 Kurdistan Regional Government — `gov.krd`

- **What it is:** the regional government's portal. The Ministry of Natural Resources and the
  Ministry of Electricity publish there, in Kurdish, Arabic and English **(not verified this
  session)**.
- **Access:** `https://gov.krd/`, `/mnr-en/`, `/moel-en/` and `/english/government/entities/mnr/`
  each returned **HTTP 403**; `https://moel.gov.krd/` returned HTTP 403. **SOURCE_BLOCKED.**
- **Decision: discovery only.** Regional-government statements are read through Rudaw, Kurdistan24
  and Shafaq, in Sorani where the Kurdish text is the fuller one, and recorded as `media`.

### 2.7 APIKUR — Association of the Petroleum Industry of Kurdistan

- **Role: industry association.** It speaks for international oil companies operating in the
  Kurdistan Region. It is an interested party, not an operator and not an authority. A search
  result summary lists eight member companies **(member list not read on APIKUR's own page)**.
- **Access:** `apikur.uk` did not resolve (`ENOTFOUND www.apikur.uk`); `apikur.org` failed the TLS
  handshake. Its statements were found only as reproduced by media and by a business-news
  aggregator.
- **What it publishes:** statements, most of which concern commercial terms and export
  arrangements. Those subjects are out of scope and are not recorded.
- **Decision: discovery only.** A statement that member companies stopped production after a
  named event may support a record (role `operator` if the company's own statement is opened,
  otherwise `media`). Its statements on export arrangements are never read for this project.

### 2.8 Iraq Oil Report — `iraqoilreport.com`

- **What it is:** a subscription news and data service on Iraq's oil sector (Strategic News
  International, Inc.).
- **Access:** home page reachable; headlines and summaries visible; "Subscribe" and "Login"
  controls. **Paywall status: subscription.** Its terms (read at `/terms/`) limit licensed content
  to the subscriber and say that no portion "may be reproduced or stored in or transmitted to any
  other web site" without consent.
- **Decision: reject as a citation; discovery only.** A headline may point to an event; the record
  must rest on a source that can be opened. Its export-data products are out of scope whatever the
  access.

### 2.9 Regional media

| Outlet | Self-description, as read | Languages | Listings | Decision |
|---|---|---|---|---|
| **Shafaq News** (`shafaq.com`) | "an independent Iraqi news agency established in 2011", with roots in the Shafaq Foundation for Culture and Media of the Feyli Kurds (`/en/who-we-are`) | ar, en, ku | Economy section paged and dated: `/en/Economy?page=N` (12 per page, 1,351 pages); `/ar/اقتصـاد?page=N` (2,125 pages); archive at `/en/archive` | **adopt** for event search |
| **Rudaw** (`rudaw.net`) | an "independent media establishment" owned by RUDAW Co. for Media Affairs, for-profit, based in Erbil (`/english/about`) | ku (Sorani), en, ar, tr | article pages readable; section listings returned navigation only | **adopt** for event search |
| **Kurdistan24** (`kurdistan24.net`) | aims at "up-to-date, impartial, and quality information"; ownership and base not stated on its page | ku (Sorani `/ckb`, Kurmanji `/kmr`), en, ar, tr, fa | `/en/list/category/36/Economy?page=N`, 16 per page, **no dates on the listing** | **adopt** for event search |

All three state "all rights reserved"; their terms pages returned no terms text to the fetch. Facts
only, cited by link. **Record role `media` for all three.** Rudaw and Kurdistan24 are based in the
Kurdistan Region; outside descriptions of their closeness to governing-party figures there were
**not verified on a page this session** and are noted only so a reviewer weighs a single-outlet
report accordingly. An article in one language edition and its translation in another are one
source.

### 2.10 International agencies and energy press

- **Reuters, AP:** the fetch tool refused both hosts outright. They can be found by search and
  recorded by URL; a record carried only by an unopened page stays **held**.
- **S&P Global Commodity Insights:** HTTP 403. **Argus:** the page returned empty.
  **Discovery only.**
- **Iraq Business News** (`iraq-businessnews.com`): an aggregator that reproduces press releases.
  A tag listing returned HTTP 404. **Discovery only**, role `aggregator`.

### 2.11 OPEC, JODI, EIA, IEA, Energy Institute

- **OPEC:** `opec.org/monthly-oil-market-report.html` and `asb.opec.org` returned **HTTP 402**.
  No figure read. **Derived facts only**, by a person in a browser; MOMR text is read only for a
  production change the report itself attributes to a disruption.
- **JODI:** download page reachable (annual CSVs 2002 to 2026, "© Copyright JODI 2026", data "can
  be downloaded, for free", no licence text). **Iraq's participation was not confirmed this
  session** (the page tried returned 404). **Derived facts only.**
- **U.S. EIA, Country Analysis Brief: Iraq**
  (`https://www.eia.gov/international/content/analysis/countries_long/iraq/`), **last updated
  14 July 2025**. Reachable. US government work, public domain, but several figures are credited
  to third parties (refining to Argus Media and *Middle East Economic Survey*; flaring to the World
  Bank) and carry those bodies' terms. National figures read are in the profile draft. The brief
  also describes export routes; **those passages are never read for this project.**
  **Decision: adopt** as national context.
- **IEA** (`iea.org/countries/iraq`) and **Energy Institute** (`energyinst.org`): HTTP 403.
  **Derived facts only**, manual.

### 2.12 Datasets

- **Natural Earth admin-1:** public domain; 18 features. **Adopt**, with the rulings in §1.
- **GEM Global Integrated Power Tracker:** CC BY 4.0 as verified earlier in this repository
  (`docs/POWER_SOURCE_RECONCILIATION.md`); form-gated download; Iraqi rows **not inspected**.
  Denominator candidate, **not yet acquired**.
- **WRI Global Power Plant Database v1.3** (cached): 28 Iraqi rows, 18,161 MW in total (14 gas,
  6 oil, 8 hydro), newest commissioning year 2016, `year_of_capacity_data` empty on all 28. It has
  no status field. **Reject** as a denominator; discovery only.
- **OpenStreetMap:** not queried this session. **Reject** for any Iraqi analytic or context layer:
  no Iraqi pipeline or grid geometry should be drawn at all (see the readiness note).
- **English Wikipedia:** used here only to find sources on Halabja and the ISO list.
  **Discovery only.**

### 2.13 Not tested

Bloomberg, *Middle East Economic Survey*, the Iraq Extractive Industries Transparency Initiative
(`ieiti.org.iq` did not resolve), the World Bank flaring data, the presidency, the Council of
Representatives and the cabinet secretariat (the first two returned HTTP 403, the third a loading
placeholder) were not read. They are **not yet researched**, not rejected.

---

## 3. Reporting bias, in neutral words

- **Two governments report.** Federal ministries and Kurdistan Region ministries each report on
  their own systems. On shared matters each side's account is one account.
- **Official statements arrive second-hand.** Because the official sites refuse automated reading,
  what this project sees is the media's selection of official statements. Statements that no outlet
  carried are invisible here.
- **State and party-adjacent media.** INA is the state agency. Outlets based in the Kurdistan
  Region cover that Region more closely than the south; Baghdad-based outlets the reverse.
- **An industry association is an interested party.** APIKUR's statements are made in the course of
  commercial disputes.
- **International energy press reports Iraq mainly when exports or prices move.** Domestic power
  and refining events are covered less, and oil events in the south more, than their share of
  what happens.
- **Kinetic events attract claims.** Attribution is often disputed or absent. A record states that
  an event was reported, its class and its governorate, and never who is said to have done it
  unless an official statement says so; method and site detail are never recorded.

## 4. Electricity: five things that must stay apart

Iraqi power reporting mixes five different things, and the event search must not merge them:

1. **Fuel shortage:** generation lost because gas or fuel supply fell.
2. **Grid failure:** a system-wide or multi-governorate collapse of the network.
3. **Technical outage:** a plant or unit fault, fire or trip.
4. **Load-shedding policy:** scheduled supply hours. EIA estimates available peak supply at about
   25 GW against about 48 GW of peak summer demand in 2024, so rationing is the normal state of the
   system. **It is background, never an event.**
5. **Kinetic disruption:** an attack or sabotage. Occurrence, date and class only, recorded for the country: the governorate was dropped on 2026-11-11 because, where most attacks were reported, a governorate and a class name one facility.

Clause 4 of the inclusion rule ("a generation shortfall that forced rotating outages") would be
met on most summer days if read literally. The plan (`IQ_SYSTEMATIC_SWEEP.md`, A.3) reads it as a
**dated, discrete loss with a stated cause and a stated size**, and holds everything else. Iraqi
statements give megawatts lost and governorates affected far more often than customers, so
clause 5's customer count will rarely be stated; megawatts are never converted to customers.

## 5. Low reported incidents is not low disruption

The number of Iraqi incidents this project will find is a property of the reporting environment:
ministries and state companies that publish statements but no event register; official sites that
cannot be read by a script; a power system in which shortage is the normal condition and so is
seldom news; two governments with separate reporting; and media whose coverage follows exports,
prices and politics. Technical outages at state facilities are the least likely to surface.
Disruption in a governorate with little media presence may never be reported in any language this
project reads.

A sparse Iraqi map must therefore read **"low reported disruption, coverage unknown"**, never "low
disruption". A governorate with no record is **not yet researched** or **unknown**, never zero.
No coverage ratio can be computed: there is no independent list to compare against.

## 6. Fields that must never be read or recorded

- SOMO's breakdown of exports by loading point, destination or buyer, and its vessel-position
  section; any export-route, alternative-route, port or terminal-dependence material from any
  source, including EIA's and APIKUR's.
- Pipeline routes, grid topology, and the status of any named line or interconnector. A cut in
  imported gas or electricity is recorded as a national supply effect only.
- Coordinates, distances, attack method, defences, and which facility is the largest or most
  important of its kind.
- For a kinetic or sabotage event: restart dates, repair progress, operating rate, remaining
  capacity or current status. A page whose address or title states such status is not cited.
- Field-by-field production in either jurisdiction.
- Facility capacities. None appears in this audit, the readiness note or the drafts.

## 7. Attribution string if adopted

> Boundaries: **Natural Earth** (public domain). National context: **U.S. EIA** (public domain;
> some figures credited by EIA to third parties); **SOMO** monthly export total (facts only, cited
> by link). Events: media and official statements cited by link.
