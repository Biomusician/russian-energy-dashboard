# Iran — source audit

Written 2026-11-11 by the Iran source-audit lane (iteration 19, Wave A). **Nothing in this document
is wired into the pipeline or a published payload.** It records, for every candidate source, what the
source is, what it publishes, how it was reached on this date, under what terms, and whether this
project should use it. Incident research is a separate lane (Wave B) and is deliberately not done
here: no declared query of `IR_SYSTEMATIC_SWEEP.md` was run.

Scope boundary applies in full (project `CLAUDE.md`; `data/candidates/gulf19/AGENT_BRIEF.md`). Iran
is treated as a system under the active-campaign rule of `docs/CURRENT_EVENT_PUBLICATION_POLICY.md`.
This audit names no facility, carries no facility capacity, and opened no page for the current
condition of any attacked site. Everything Iranian is recommended for **province-level presentation
at most**, and country-level for kinetic and sabotage records.

Every statement below was read on a page or file during this session unless it is marked
**(not verified this session)**. Where a site could not be reached, that is recorded as a finding
about access on this date from this machine. **A site that refused access is an access limitation.
It is not evidence that the body publishes nothing.**

Searches used: 3 of the 4 allowed (one on the province count, one to test whether a search engine
indexes SHANA, one looking for a readable page with national generating capacity).

---

## 0. Summary

| Source | Sector(s) | Reached 2026-11-11 | Decision |
|---|---|---|---|
| Ministry of Petroleum (mop.ir) | oil, gas, refining | no: bot check | **discovery only** (through search) |
| SHANA (shana.ir), the ministry's news agency | oil, gas, refining | no: connection closed; indexed by search | **adopt for event search**, through search; pages not openable here |
| NIOC (nioc.ir) | upstream | no: bot check | **discovery only** |
| NIGC (nigc.ir) | gas processing, transmission, distribution | no: certificate error | **discovery only** |
| NIORDC (niordc.ir) | refining, product distribution | **yes** | **adopt for event search** (listing page 1 only); yearbooks **derived facts only** (stop at 1396-97) |
| Ministry of Energy (moe.gov.ir) and its news site (paven.ir) | electricity, water | no: names did not resolve | **discovery only** (through search) |
| Tavanir (tavanir.org.ir) | generation, transmission, distribution | no: name did not resolve | **discovery only**; statistics **derived facts only** once readable |
| Iran Grid Management Company (igmc.ir) | grid operation | no: name did not resolve | **discovery only** |
| Statistical Center of Iran (amar.org.ir) | national statistics, geography | no: name did not resolve | **derived facts only** once readable |
| Ministry of Interior (moi.ir) | administrative divisions | no: HTTP 403 | **discovery only** |
| IRNA | all, media | no: script redirect shell | **adopt for event search**, through search |
| ISNA | all, media | no: script redirect shell | **adopt for event search**, through search |
| Mehr | all, media | no: connection closed | **adopt for event search**, through search |
| Tasnim (tasnimnews.ir) | all, media | **yes** | **adopt for event search** |
| Fars | all, media | no: name did not resolve | **adopt for event search**, through search |
| U.S. EIA country analysis brief | national context | **yes** | **adopt** (national context) |
| OPEC ASB and MOMR | national oil and gas | no: HTTP 402 | **derived facts only**, read by a person |
| JODI Oil | monthly national flows | yes | **reject** for the window: no Iranian submission since July 2018 |
| GECF | national gas | site yes; bulletin PDF over the fetch size limit | **derived facts only** |
| IEA, Energy Institute | national context | no: HTTP 403 | **derived facts only**, read by a person |
| Reuters, AP, AFP | all, media | no: the fetch tool refuses these hosts | **adopt for event search**, through search |
| S&P Global Commodity Insights | oil, gas, refining | no: HTTP 403 | **adopt for event search**, through search |
| Iran International | all, media outside Iran | English site yes | **adopt for event search, corroboration required** |
| Radio Farda (RFE/RL) | all, media outside Iran | yes | **adopt for event search, corroboration required** |
| Wikipedia compilation articles | all | yes | **discovery only** |
| WRI Global Power Plant Database v1.3 | generation | local cache | **reject** as denominator |
| OpenStreetMap | grid, pipelines | not queried | **reject** for Iranian layers |
| GEM trackers | generation; pipelines | not acquired | GIPT **discovery only until acquired**; pipeline trackers **reject** |
| Natural Earth admin-1 | boundaries | local cache | **adopt**, with the code crosswalk in section 1 |

The main finding is about access, not content. Of the Iranian official and agency hosts tested, two
could be read (NIORDC and Tasnim). The rest failed in four different ways (section 2.0). Wave B will
therefore depend on a search engine's index of Iranian sites, and most Iranian citations it finds
will carry `opened: false`. That is a property of this date and this machine and must be logged
lane by lane, not smoothed over.

---

## 1. Geography — the 31 provinces (استان, *ostān*)

**Current official count: 31.** The most recent change was the creation of Alborz Province from
part of Tehran Province in 2010. No later province was found: one search for a new province approved
up to 1405 returned only proposals and older stories, and neither Wikipedia edition (English,
Persian) mentions one. The official bodies that would settle it could not be opened on this date
(Ministry of Interior: HTTP 403; Statistical Center of Iran: name did not resolve), so the count
rests on three independent-enough readings:

- ISO 3166-2:IR lists 31 provinces (read as transcribed on English Wikipedia; the ISO browsing
  platform itself is a script application and was not opened);
- English and Persian Wikipedia both state thirty-one (Persian: «کشور ایران به سی‌ویک استان تقسیم می‌شود»);
- Tasnim's provincial desk menu lists the same 31 provinces, plus two desks that are not provinces
  (a city desk for Kashan and a desk named «جزایر خلیج فارس», "Persian Gulf islands").

**Natural Earth also has 31 features** (`ne_10m_admin_1`, `adm0_a3 = IRN`, all `type_en =
"Province"`), so `units_expected` is 31 and no province is missing or extra. The differences are in
the codes, and they are serious.

### 1.1 Ruling 1: Natural Earth's codes are not the current ISO codes

ISO 3166-2:IR was renumbered on 2020-11-24. Natural Earth (frozen since 2022) still carries the
earlier numbering, and it gives **Alborz the same code as Tehran (`IR-07`)**. Under the current
standard `IR-07` is Fars. Only two of the 31 Natural Earth codes still point at the same province.

| Natural Earth `name` | Persian (`name_fa`) | Natural Earth code | Current ISO 3166-2 (2020-11-24) |
|---|---|---|---|
| East Azarbaijan | استان آذربایجان شرقی | IR-01 | IR-03 |
| West Azarbaijan | استان آذربایجان غربی | IR-02 | IR-04 |
| Ardebil | استان اردبیل | IR-03 | IR-24 |
| Esfahan | استان اصفهان | IR-04 | IR-10 |
| Ilam | استان ایلام | IR-05 | IR-16 |
| Bushehr | استان بوشهر | IR-06 | IR-18 |
| Tehran | استان تهران | IR-07 | IR-23 |
| Alborz | استان البرز | **IR-07 (duplicate)** | IR-30 (IR-32 before 2020) |
| Chahar Mahall and Bakhtiari | استان چهارمحال و بختیاری | IR-08 | IR-14 |
| Khuzestan | استان خوزستان | IR-10 | IR-06 |
| Zanjan | استان زنجان | IR-11 | IR-19 |
| Semnan | استان سمنان | IR-12 | IR-20 |
| Sistan and Baluchestan | استان سیستان و بلوچستان | IR-13 | IR-11 |
| Fars | استان فارس | IR-14 | IR-07 |
| Kerman | استان کرمان | IR-15 | IR-08 |
| Kordestan | استان کردستان | IR-16 | IR-12 |
| Kermanshah | استان کرمانشاه | IR-17 | IR-05 |
| Kohgiluyeh and Buyer Ahmad | استان کهگیلویه و بویراحمد | IR-18 | IR-17 |
| Gilan | استان گیلان | IR-19 | IR-01 |
| Lorestan | استان لرستان | IR-20 | IR-15 |
| Mazandaran | استان مازندران | IR-21 | IR-02 |
| Markazi | استان مرکزی | IR-22 | IR-00 |
| Hormozgan | استان هرمزگان | IR-23 | IR-22 |
| Hamadan | استان همدان | IR-24 | IR-13 |
| Yazd | استان یزد | IR-25 | IR-21 |
| Qom | استان قم | IR-26 | IR-25 |
| Golestan | استان گلستان | IR-27 | IR-27 |
| Qazvin | استان قزوین | IR-28 | IR-26 |
| South Khorasan | استان خراسان جنوبی | IR-29 | IR-29 |
| Razavi Khorasan | استان خراسان رضوی | IR-30 | IR-09 |
| North Khorasan | استان خراسان شمالی | IR-31 | IR-28 |

The current-ISO column was matched by province name against the ISO table as transcribed on
English Wikipedia, and the lead checked all 31 rows against an independent listing of the
2020 revision before adopting it. It has not been checked against the ISO browsing platform itself.

**Consequences, same class as the Moscow swap and the 2023 Indian recodes:**

- `pipeline/build_systems.py` keys units on `iso_3166_2`, so Tehran and Alborz would arrive as two
  units with one code. A fix keyed on the Natural Earth code alone cannot separate them; it has to
  be keyed on name or on `adm1_code` (`IRN-3216` Tehran, `IRN-5490` Alborz).
- A code typed by a researcher from a current source ("IR-07", meaning Fars) silently lands on
  Tehran while the Natural Earth numbering is in use. **Lead's decision (2026-11-11): all 31
  units are moved to the current ISO codes by name (`NAME_CODE_FIXES` in
  `pipeline/build_systems.py`, the India precedent), so the code a researcher finds in any current
  source is the code used here.** A unit the table does not cover fails the build rather than
  falling back to its old code, which would be another province's. Every candidate still carries
  `admin1_name` beside `admin1_code`, and the reviewer checks the two agree. Every ruling in the draft repeats the province name
  so that a change of scheme cannot move a ruling onto another province.
- Join incoming text by a curated alias table (English and Persian), never by English name alone.
  Natural Earth's spellings ("Esfahan", "Ardebil", "Kordestan", "Chahar Mahall", "Buyer Ahmad")
  will not match "Isfahan", "Ardabil", "Kurdistan", "Chaharmahal", "Boyer-Ahmad".
- Province and capital often share a name (Tehran, Isfahan, Kerman, Yazd, Bushehr, Zanjan and
  others). A source naming a city is naming a place inside a province, not the province.

### 1.2 Ruling 2: Abu Musa and the Greater and Lesser Tunbs

A cartographic matter, stated in sovereignty-neutral words. The three islands are administered by
Iran and claimed by the United Arab Emirates. Natural Earth's default edition draws **Abu Musa as
one small polygon inside the Hormozgan feature**; the two Tunbs are **not drawn** at 1:10m (checked
in the cached file: one island polygon in that part of the Gulf, attached to Hormozgan, none
attached to any UAE emirate). The project draws them as Natural Earth does. That is an analytic and
cartographic choice in the style of the Crimea rule, not a statement about sovereignty.

**The islands are never an analytical unit.** No event is assigned to them, no count or context
figure is computed for them, and they get no code of their own. A report placed on one of the
islands is held at country precision. Tasnim's "Persian Gulf islands" desk is a newsroom category,
not an administrative unit, and must not be mistaken for one.

### 1.3 Other geographic notes

- **Offshore.** Offshore oil and gas installations lie outside every province polygon. An offshore
  event takes the province only when the source itself names it; otherwise country precision.
  Kinetic and sabotage records are country precision in any case under the campaign rule.
- **The Caspian Sea** has no agreed delimitation among its littoral states. No unit depends on it.
- **Electricity is not organised by province.** Regional electric companies (شرکت برق منطقه‌ای) and
  distribution companies do not map one-to-one onto the 31 provinces **(not verified this
  session: Tavanir's site did not resolve)**. A regional electricity statement must be placed by the
  province the source names, never by the company's name.
- No other difference between Natural Earth and the current divisions was found. The Natural Earth
  disputed-areas layer was not inspected (it is not in the local cache).

---

## 2. Source-by-source audit

### 2.0 What happened when each host was fetched

One ordinary request per host on 2026-11-11, plus the bare or `www` form where the first failed.
Nothing was retried through another route.

| Host | Result |
|---|---|
| `www.shana.ir`, `shana.ir`, `en.shana.ir` | connection closed by the remote side |
| `www.mop.ir` | browser-check page (CloudGuard.ir): bot challenge |
| `www.nioc.ir` | browser-check page (CloudGuard.ir): bot challenge |
| `www.nigc.ir`, `nigc.ir` | TLS failure: certificate chain could not be verified |
| `www.niordc.ir` | **read** |
| `moe.gov.ir`, `www.moe.gov.ir`, `paven.ir`, `www.paven.ir` | name did not resolve |
| `tavanir.org.ir`, `www.tavanir.org.ir` | name did not resolve |
| `igmc.ir`, `www.igmc.ir` | name did not resolve |
| `amar.org.ir`, `www.amar.org.ir` | name did not resolve |
| `www.moi.ir` | HTTP 403 |
| `www.irna.ir`, `en.irna.ir`, `www.isna.ir`, `financialtribune.com` | script redirect shell ("Transferring to the website..."), no content |
| `www.mehrnews.com`, `en.mehrnews.com`, `www.tehrantimes.com`, `www.asriran.com` | connection closed by the remote side |
| `farsnews.ir`, `www.farsnews.ir`, `www.tasnimnews.com`, `barghnews.com`, `www.entekhab.ir`, `www.taadolnewspaper.ir` | name did not resolve |
| `www.tasnimnews.ir` | **read** (Persian and English) |
| `www.presstv.ir` | TLS failure: certificate issued for another domain |
| `www.iranintl.com` | English home page **read**; a Persian section listing rendered no items |
| `www.radiofarda.com` | **read** |
| `www.eia.gov`, `www.jodidata.org`, `www.gecf.org`, `rsf.org`, Wikipedia | **read** |
| `www.opec.org`, `asb.opec.org` | HTTP 402 |
| `www.iea.org`, `www.energyinst.org`, `www.spglobal.com` | HTTP 403 |
| `www.argusmedia.com` | empty shell |
| `www.reuters.com`, `apnews.com`, `www.afp.com`, `www.bbc.com` | refused by this session's fetch tool before any request was made |

Why the Iranian hosts fail is **not established**. Possible causes include restrictions on
international connectivity (section 3), geographic filtering by the site or its protection service,
and name-server filtering. All are access limitations. Each should be tried again from another
network before anything is concluded about what the body publishes.

Every Iranian body below is **SOURCE_BLOCKED** for direct reading unless it says "read".

### 2.1 Ministry of Petroleum (وزارت نفت) — mop.ir

- **What it is:** the ministry over the four state oil companies (NIOC, NIGC, NIORDC and the
  petrochemical company) **(structure not verified this session)**.
- **Language:** Persian; an English edition is believed to exist.
- **What it publishes:** not read. Its announcements reach the public mainly through SHANA.
- **Access:** bot challenge. Not worked around.
- **Cadence, terms:** not read.
- **Decision: discovery only**, through search. Role when cited: `official`.

### 2.2 SHANA (شانا) — shana.ir

- **What it is:** the news agency of the Ministry of Petroleum. Official, single-ministry voice.
- **Language:** Persian; English edition at `en.shana.ir`.
- **What it publishes:** news items and official statements for upstream, gas, refining and
  distribution. Article addresses have the form `shana.ir/news/<numeric id>/<title>` (seen in
  search results). Whether it runs an event-notice series was not established. No event register
  is known.
- **Access:** all three hosts closed the connection. **A search engine does index it**: one
  site-restricted Persian search returned ten SHANA items with titles. So SHANA can be searched but
  not opened from here, and a SHANA citation found this way is `opened: false`.
- **Cadence:** continuous news.
- **Terms:** not read.
- **Reporting bias, neutrally:** a ministry agency reports the ministry's account. Its vocabulary for
  cause follows the official position of the day.
- **Decision: adopt for event search** (lane IR1, and IR2 for refining), through search. Role when
  cited: `official`.

### 2.3 NIOC (شرکت ملی نفت ایران) — nioc.ir

- **What it is:** the national oil company; upstream production through regional subsidiaries.
- **Access:** bot challenge. Not read.
- **What it publishes:** not established. No public production-by-field or outage series is known.
- **Decision: discovery only.** Role when cited: `operator`.

### 2.4 NIGC (شرکت ملی گاز ایران) — nigc.ir

- **What it is:** the national gas company: processing, transmission and distribution through
  provincial gas companies.
- **Access:** TLS certificate failure on both host forms. Not read.
- **What it publishes:** not established. Winter supply statements are usually carried by SHANA and
  the agencies **(not verified this session)**.
- **Decision: discovery only.** Role when cited: `operator`.

### 2.5 NIORDC (شرکت ملی پالایش و پخش فرآورده‌های نفتی ایران) — niordc.ir

- **What it is:** the national refining and distribution company.
- **Language:** Persian, with an English portal (`/en-US/en.niordc/5693/`) that showed no news items.
- **What it publishes (read):**
  - a paged news listing (about 1,400 items), each with a news code and a Solar Hijri date in
    Persian digits. Mostly corporate news, speeches, consumption figures and notices.
    **Post-event status items on an operator's site are not opened or recorded.**
  - a notices listing at `/fa-IR/Portal/5120`;
  - statistical yearbooks of energy-product consumption for 1384 to 1396-97 (one PDF a year). The
    newest covers 1397, about 2018-19. Nothing later is posted.
- **Access:** page 1 reads normally. Further pages are reached only through a script postback, so
  an ordinary request cannot enumerate the archive.
- **Cadence:** news daily; yearbooks stopped.
- **Terms (read, footer):** «همه حقوق این سایت متعلق به شرکت ملی پالایش و پخش فرآورده های نفتی ایران
  است» (all rights belong to the company). No open licence. Facts only, cited by link.
- **Decision: adopt for event search** (lane IR2; page 1 enumeration plus search). Yearbooks:
  **derived facts only**, and stale. Role when cited: `operator`.

### 2.6 Ministry of Energy (وزارت نیرو) and its news site — moe.gov.ir, paven.ir

- **What it is:** the ministry for electricity and water; `paven.ir` is its news site.
- **Access:** neither name resolved. Not read.
- **What it publishes (not verified this session):** statements on supply and demand, the national
  energy balance (ترازنامه انرژی), announcements of load-management programmes.
- **Decision: discovery only**, through search. Role when cited: `official`.

### 2.7 Tavanir (توانیر) — tavanir.org.ir

- **What it is:** the state holding for generation, transmission and distribution.
- **Access:** name did not resolve. Not read.
- **What it publishes (not verified this session):** detailed annual statistics of the power
  industry, and, since the shortfall years, schedules of planned rotating outages. WRI's database
  credits Tavanir for 75 of its 107 Iranian plants, so a Tavanir plant list was public at some time.
- **Decision: discovery only** for events; **derived facts only** for statistics once readable.
  Role when cited: `operator`.

### 2.8 Iran Grid Management Company (شرکت مدیریت شبکه برق ایران) — igmc.ir

- **What it is:** the national grid operator and market operator.
- **Access:** name did not resolve. Not read.
- **What it publishes (not verified this session):** daily peak-load and reserve figures. Whether it
  publishes event notices was not established.
- **Decision: discovery only.** Role when cited: `operator`. Line-level and dispatch detail is out
  of scope whatever it publishes.

### 2.9 Statistical Center of Iran (مرکز آمار ایران) — amar.org.ir

- **What it is:** the national statistics office: yearbook, census, administrative divisions.
- **Access:** name did not resolve. Not read.
- **Decision: derived facts only** once readable (national aggregates, province list). Role:
  `government`. The Ministry of Interior (`moi.ir`, HTTP 403) is the body that defines the
  divisions: **discovery only**.

### 2.10 The five Iranian news agencies

Affiliations are recorded as each is commonly described. **None was read on the outlet's own page
this session** except Tasnim's footer. They are stated for provenance, not as a rating.

| Outlet | What it is, neutrally | Access 2026-11-11 | Terms |
|---|---|---|---|
| IRNA (ایرنا) | the state news agency | script redirect shell | not read |
| ISNA (ایسنا) | students' news agency attached to a public academic body; semi-official | script redirect shell | not read |
| Mehr (مهر) | agency owned by a state-funded religious organisation; semi-official | connection closed | not read |
| Tasnim (تسنیم) | agency widely described as close to the Revolutionary Guards; semi-official | **read** at `tasnimnews.ir` (`.com` did not resolve) | footer: "All Content by Tasnim News Agency is licensed under a Creative Commons Attribution 4.0 International License." |
| Fars (فارس) | agency widely described as close to the Revolutionary Guards; semi-official | name did not resolve | not read |

- **What they publish:** continuous news, including ministry statements, provincial outage reports
  and officials' interviews. No event register.
- **Tasnim, as read:** energy desk at `/fa/service/80/` (20 items, then a script "show more");
  archive at `/fa/archive` (script filters); article addresses
  `/fa/news/<Solar Hijri year>/<month>/<day>/<id>/...`, so **the date in a Persian address is Solar
  Hijri**; English articles at `/en/news/<Gregorian year>/...`. The site search returned only the
  newest items for a test query, so it is not a way to reach older years. RSS at
  `/fa/rss/feeds/80/0/0/1`.
- **Independence:** these are five outlets inside one state-supervised media system, and they
  frequently carry the same ministry statement. Two of them repeating a statement is one source,
  not two. A translation by the same agency is not a second source either.
- **Decision: adopt for event search** (lane IR4), through search; Tasnim also by its desk listing.
  Role when cited: `media`.
- **Also tested, not adopted as separate sources:** Tehran Times, Financial Tribune, Press TV,
  Asr Iran, Entekhab, Taadol and Bargh News all failed to load. They may appear in search results
  and are then `media`, `opened: false`.

### 2.11 U.S. EIA — Country Analysis Brief: Iran

- **Product:** `https://www.eia.gov/international/content/analysis/countries_long/Iran/`, **last
  updated 2024-10-10**. English.
- **What it publishes (read):** national figures. Primary energy production 2022 **17.6 quads**
  (natural gas 55.7%, petroleum and other liquids 43.4%, coal 0.3%, nuclear 0.4%, hydro and other
  renewables 0.3%); petroleum and other liquids **4.0 million b/d in 2023**, of which "almost 2.9
  million b/d was crude oil"; dry gas production **9.4 Tcf** and consumption **8.9 Tcf** in 2023;
  gas exports **515 Bcf** in 2023; net generation **360.7 TWh** in 2022 (gas 85.2%, petroleum 8.1%,
  hydro 4.4%, nuclear 1.7%, other renewables 0.4%); crude distillation capacity "an estimated 2.1
  million b/d" and condensate splitter capacity 0.6 million b/d at the beginning of 2024; crude and
  condensate exports "nearly 1.4 million b/d" in 2023; proved gas reserves 1,200 Tcf at December
  2023. It states that "available capacity was less than 78% of installed capacity" in 2023 without
  giving the installed figure.
- **What it does not publish:** a refinery table. It does carry a table of named gas projects; that
  table was not transcribed and must not be.
- **Cadence:** irregular. **Terms:** U.S. government work, public domain; figures it credits to
  commercial trackers carry those trackers' terms.
- **Bias:** a secondary compilation; several Iranian figures are EIA estimates, and it says so.
- **Decision: adopt** as the national context source for the profile. Never an event source.

### 2.12 OPEC — Annual Statistical Bulletin, Monthly Oil Market Report

- **Access:** `www.opec.org` and `asb.opec.org` both returned HTTP 402. Nothing read.
- **What it publishes (not verified this session):** national production, refining capacity and
  exports by member; monthly production by secondary sources.
- **Decision: derived facts only**, cited by edition, read by a person in a browser. Not an event
  source: a production change with no stated cause is not an event.

### 2.13 JODI Oil

- **Access:** read. The availability file `jodi_oil_data_availability_by_country.xlsx` (latest
  update 2026-10-21) was downloaded and its Iran column read.
- **Finding:** Iran is marked as reporting for most months from January 2002 to July 2018, and
  **for no month from August 2018 to August 2026**. There is no Iranian JODI-Oil data anywhere in
  this project's window.
- **Terms:** "© Copyright JODI 2026"; no licence text.
- **Decision: reject** for 2022 onward. Derived facts only for pre-2018 history, which this project
  does not need. JODI-Gas was not checked.

### 2.14 GECF — Gas Exporting Countries Forum

- **Access:** site read. Annual Statistical Bulletin 2025 (9th edition) is a public PDF, but it is
  over the 10 MB fetch limit and was not read. There is no Iran country page at the address tried
  (HTTP 404). No Excel edition is listed.
- **Terms:** footer "© GECF 2026"; the copyright page holds placeholder text only. Treat as all
  rights reserved.
- **Decision: derived facts only** (national gas aggregates), read by a person.

### 2.15 IEA and Energy Institute

- Both returned HTTP 403. Nothing read. **Derived facts only**, cited by edition, by a person.

### 2.16 Reuters, AP, AFP

- **What they are:** international news agencies. Reuters and AFP have reported from inside Iran
  under accreditation at various times; conditions for foreign media in Iran are restrictive
  **(not verified this session)**.
- **Access:** this session's fetch tool refuses all three hosts. They can be found through search
  only, so citations are `opened: false` unless a person opens them.
- **Decision: adopt for event search** (lanes IR5, IR6). Role: `media`. A wire story carried by many
  outlets is one source.

### 2.17 S&P Global Commodity Insights (and Argus)

- **Access:** S&P HTTP 403; Argus returned an empty shell. Paywalled in the main.
- **Decision: adopt for event search** through search, headline and public summary only. Role:
  `media`. Their tanker-tracking and export-flow material is **out of scope and must not be read
  for this project** (section 6).

### 2.18 Iran International

- **What it is (read, footer):** a news outlet in Persian, English and Arabic; "All rights reserved
  for Volant Media UK Limited". Based outside Iran. It is commonly described as
  opposition-aligned, and the Iranian government has declared it hostile; reporting on its
  funding names Saudi-linked investors **(not verified this session)**.
- **Role for this project:** media outside Iran. It often reports events from viewer video and
  unnamed sources that Iranian outlets do not carry, and Iranian outlets dispute its accounts. It is
  a **discovery and corroboration** source: a record needs a second, independent source before it
  can be accepted on Iran International alone.
- **Access:** English home page read; article addresses begin with a Gregorian date string. A
  Persian section listing rendered no items to an ordinary request.
- **Decision: adopt for event search, corroboration required.** Role when cited: `media`.

### 2.19 Radio Farda

- **What it is:** the Persian service of RFE/RL, funded by the United States Congress **(funding
  not stated on the page read)**. Footer reserves all rights to Radio Farda.
- **Access:** read. Economy section at `/iran-economy`; article addresses `/a/<slug>/<id>.html`.
- **Decision: adopt for event search, corroboration required**, on the same footing as 2.18.

### 2.20 Wikipedia compilation articles

- Found by title only through the MediaWiki search API: an article on the energy crisis (its
  lead covers late 2024 to December 2025 and it carries a maintenance notice about
  machine-written text) and several on the 2026 war.
- No structured table comparable to the one behind the Russia theatre was looked for or found.
- **Decision: discovery only.** These articles carry material this project does not record.
  Leads only were read here, for dates and for the reporting environment. Wave B must not mine
  them.

### 2.21 WRI Global Power Plant Database v1.3 (local cache)

- Counted this session in `data/raw/wri_gppd.csv`: **107 Iranian plants, 61,362 MW** (gas 60, oil
  18, hydro 19, solar 8, nuclear 1, wind 1). 75 rows credit Tavanir. Newest commissioning year
  **2015**; `year_of_capacity_data` empty on all rows.
- Against a national total of roughly 94,600 MW quoted from Tavanir in spring 1404 (seen in a
  search summary only, **not read on a page**), the database is about a third short and a decade old.
- **Decision: reject** as a denominator. Discovery only.

### 2.22 OpenStreetMap, GEM trackers

- **OSM:** not queried. Pipeline routes and grid topology are outside what this expansion may
  collect. **Reject** for any Iranian layer.
- **GEM:** GIPT not acquired; Iranian coverage not inspected. It is the natural generation
  inventory if one is ever needed. Pipeline trackers: **reject**, same reasoning as for Saudi Arabia.

### 2.23 Natural Earth admin-1

- Public domain, 31 features. **Adopt**, with the code handling of section 1.1 and the rulings of 1.2.

---

## 3. Reporting environment, and reporting bias in neutral words

**Chosen: `conflict_restricted`.** Evidence, with its weight stated:

1. **A war is recorded as under way.** English Wikipedia's lead for "2026 Iran war" gives a start of
   28 February 2026, a ceasefire from 8 April that ended on 8 July, and no end date; it follows a
   twelve-day war in June 2025. *Tertiary source, lead only; the campaign-status lane owns this
   fact and should confirm it from primary reporting.*
2. **The parties restrict reporting of damage.** Wikipedia's "Censorship during the 2026 Iran war",
   citing Reporters Without Borders (11 March 2026) and Tech Policy Press, says the United States,
   Israel and Iran all restricted reporting of damage, and that Iran imposed near-total internet
   blackouts and restricted independent journalism. *Tertiary; the cited reports were not opened.*
3. **Connectivity.** Wikipedia's "2026 Internet blackout in Iran" (lead) reports a nationwide
   shutdown from 8 January 2026, connectivity at 4% of ordinary levels after 28 February according
   to NetBlocks, and a partial lifting ordered on 25 May with service still restricted. *Tertiary.*
4. **Media system.** RSF's own country page (read) ranks Iran 177th of 180 in its 2026 index and
   describes a media sector largely controlled by the state.
5. **Direct test.** Section 2.0: most Iranian official and agency hosts could not be read from
   outside on 2026-11-11.
6. **No register.** No Iranian body is known to publish an event-level outage or incident register,
   and none could be opened to check.

Why not `media_only`: that label fits the earlier part of the window better. From 2022 to mid-2025
the record would rest on ministry statements carried by state-affiliated agencies, with no
register, which is exactly `media_only`. But the vocabulary allows one value per system, an active
conflict governs how every recent record must be handled, and under-stating the restriction is the
worse error. The `reporting_note` therefore says both things. **The lead should confirm that one
value may stand for the whole window.**

Limitations, stated as limitations and never turned into a number:

- **State reporting.** Domestic outlets are supervised and often carry one official account. Cause
  wording follows the official position. Officials do speak openly about the chronic shortage, so
  load management is reported far more fully than accidents or attacks.
- **Conflict restrictions.** Each party to the conflict controls what is said about damage on its
  own side and makes claims about the other's. A claim by a party is a claim. Publisher count
  overstates certainty when outlets repeat one claim.
- **Sanctions.** Iran stopped reporting to JODI in 2018 (2.13). Export and production figures in
  international sources are third-party estimates, and EIA labels several of them so. Company
  disclosure of the kind listed firms make does not exist for the state oil companies.
- **Access.** Section 2.0. A blocked site was not searched.
- **Outlets outside Iran.** They report what domestic outlets do not, from sources that cannot be
  checked, and each has a stated or attributed position. Used for discovery and corroboration.
- **Language and calendar.** Persian sources date events in the Solar Hijri calendar. A year such
  as 1404 is never Gregorian. Persian and Latin digits are both in use.

None of this is a penalty applied to a count. It is the caveat that travels with every count.

## 4. Low reported incidents is not low disruption

Whatever number of Iranian records Wave B finds will be a property of this reporting environment:
no register, supervised domestic media, wartime restriction on damage reporting by every party,
official sites unreachable from outside, an internet shutdown lasting months, and a search that
runs on a search engine's partial index of Persian-language sites. Technical outages at single
facilities are the least likely to surface. Events during the 2026 war are the least likely to be
reported consistently by anyone.

The reverse error is also available here. Chronic gas and electricity shortage is discussed
constantly by officials, so a careless pass could produce hundreds of "events" out of scheduled
load management. Lane IR3 keeps four things apart for that reason (see `IR_SYSTEMATIC_SWEEP.md`):
chronic shortfall, planned load management, discrete grid events, and attack-related outages.

The dashboard must never render a sparse Iranian map as low disruption, nor a dense one as a
measure of the war. The correct reading is **reported disruption, coverage unknown**, beside the
reporting environment. No count for Iran may be compared with any other system's.

## 5. Fields and pages that must never be read

For every Iranian record, and for the kinetic and sabotage lane without exception:

- restart, resumption, repair, reconstruction, return to service, remaining or current capacity,
  operating rate, "still out", planned or postponed restart dates. Persian wording to treat as a
  stop signal in a title or address: `راه‌اندازی مجدد`، `ازسرگیری`، `از سر گرفته شد`، `بازگشت به مدار`،
  `به مدار بازگشت`، `تعمیر`، `ترمیم`، `بازسازی`، `بازیابی`، `همچنان متوقف`، `در مدار قرار گرفت`.
  **`STATUS_WORDING` in `pipeline/build_systems.py` has English and Arabic patterns and no Persian
  ones.** It needs Persian patterns before any Iranian record is imported.
- coordinates, distances, ranges, routes, weapon or attack-method detail, air-defence detail;
- any ranking of facilities by size or importance, and any dependency between facilities;
- tanker, vessel-tracking, shipping-route, export-route and Strait of Hormuz material, including
  the tracker-derived export destinations in EIA's brief and in the energy press;
- pipeline route detail, grid topology, line-level interconnector status;
- nuclear fuel-cycle, enrichment and nuclear-site material. National nuclear generation totals
  only (EIA: 6.0 TWh, 1.7% of generation, 2022);
- EIA's table of named gas projects, NIORDC's items on post-attack infrastructure condition, and
  the body text of the Wikipedia war articles.

## 6. Attribution string if adopted

> National context: **U.S. EIA**, Country Analysis Brief: Iran (public domain). Boundaries:
> **Natural Earth** (public domain).
> Events: publisher and link on each record.
