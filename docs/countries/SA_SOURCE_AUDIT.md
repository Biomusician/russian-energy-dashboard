# Saudi Arabia — source audit

Written 2026-10-30 by the Saudi Arabia source-audit lane. **Nothing in this document is wired into
the pipeline or the published index.** It records, for every candidate source, what the source is,
what it can and cannot support, and whether this project should adopt it. Incident research is a
separate lane and is deliberately not done here.

Scope boundary applies in full (see the project `CLAUDE.md`). This audit treats infrastructure only
as public descriptive context — name, operator, class, capacity, status, province — taken from
sources that already publish it. It does not assess the importance, vulnerability, protection,
interdependence or routing of any facility, and it recommends **province-level presentation** for
everything Saudi.

Every figure below was read on a page or document during this session unless it is marked
**(not verified this session)**. Where a site could not be reached, that is recorded as a finding
about machine accessibility, not papered over.

---

## 0. Summary

| Source | Sector(s) | Decision |
|---|---|---|
| Saudi Aramco Annual Report (2021–2025) | refining, upstream/gas aggregates | **adopt** (refining denominator, gross basis) |
| Saudi Aramco quarterly / interim reports | aggregate production, disclosures | **derived-facts-only** |
| Saudi Aramco bond / base prospectus | context | **discovery-only** |
| Saudi Electricity Company (SEC) results and annual reports | generation, transmission aggregates | **derived-facts-only** |
| SERA (formerly ECRA, then WERA) statistical booklet | generation, by SEC operating area | **discovery-only** (unreachable) |
| Ministry of Energy | policy, announcements | **discovery-only** (unreachable) |
| GASTAT (General Authority for Statistics) | energy statistics | **derived-facts-only** (open licence; content not yet located) |
| JODI Oil / JODI Gas | monthly national flows | **adopt** (national context series) |
| OPEC ASB and MOMR | national production, refining | **derived-facts-only** (blocked to scripts) |
| EIA country analysis brief | national context, refinery list | **derived-facts-only** |
| Energy Institute Statistical Review | national context | **derived-facts-only** (blocked to scripts) |
| GEM trackers (GIPT, GOGPT, GGIT/GOIT) | generation; pipelines | **adopt** GIPT for generation once acquired; **reject** pipeline trackers for Saudi |
| WRI GPPD v1.3 | generation | **reject** as denominator; discovery-only |
| OpenStreetMap | transmission, pipelines | **reject** for Saudi analytics; discovery-only |
| Natural Earth admin-1 | boundaries | **adopt** |
| English Wikipedia *List of oil refineries* (Saudi section) | refining | **reject** as denominator |

The single most important finding: **Aramco publishes a complete, single-source, single-basis
per-refinery capacity table every year**, which is a better refining denominator than anything the
Russia build has. Everything else is national aggregate, stale, or unreachable.

---

## 1. Geography — the 13 regions (مناطق, *manāṭiq*)

Saudi Arabia has 13 first-level administrative regions (منطقة, *minṭaqa*; usually rendered
"province" or "region" in English). Natural Earth `ne_10m_admin_1` (the file already cached at
`data/raw/ne_10m_admin_1.geojson`) carries exactly 13 `SAU` features, all `type_en = "Region"`:

| ISO 3166-2 | Natural Earth `name` | Arabic (`name_ar`) | Common English alternatives |
|---|---|---|---|
| SA-01 | Ar Riyad | منطقة الرياض | Riyadh |
| SA-02 | Makkah | منطقة مكة المكرمة | Mecca, Makkah al-Mukarramah |
| SA-03 | Al Madinah | منطقة المدينة المنورة | Medina, Al Madinah al Munawwarah |
| SA-04 | Ash Sharqiyah | المنطقة الشرقية | Eastern Province |
| SA-05 | Al Quassim | منطقة القصيم | Al Qassim, Qaseem, Gassim |
| SA-06 | Ha'il | منطقة حائل | Hail |
| SA-07 | Tabuk | منطقة تبوك | Tabouk |
| SA-08 | Al Hudud ash Shamaliyah | منطقة الحدود الشمالية | Northern Borders / Northern Frontier |
| SA-09 | Jizan | منطقة جازان | Jazan, Gizan |
| SA-10 | Najran | منطقة نجران | — |
| SA-11 | Al Bahah | منطقة الباحة | Baha |
| SA-12 | Al Jawf | منطقة الجوف | Jouf, Jowf |
| SA-14 | `Asir | منطقة عسير | Asir, Aseer |

**Join hazards, same class as the Russian Moscow-code swap:**

- There is no SA-13; codes run 01–12 then 14. A loop over `range(1, 14)` silently misses Asir.
- Natural Earth spells Qassim **"Al Quassim"** (non-standard) and writes Asir with a **leading
  backtick** (`` `Asir ``). Neither will match a source that says "Qassim" or "Asir".
- Sources mix the region name with its capital (Jazan/Jizan, Riyadh city vs Riyadh region,
  Makkah city vs region). Rabigh is in **Makkah** region; Yanbu' is in **Al Madinah** region; Jubail
  and Ras Tanura are in the **Eastern Province** — a reader expecting "Yanbu → Makkah" will be wrong.
- Join by **ISO code**, with a curated alias table (English + Arabic) for incoming text; never by
  English name alone.

**Electricity statistics do not use the 13 regions.** SEC and the regulator report by the four SEC
operating areas (Central, Eastern, Western, Southern). EIA's 2021 brief, citing the regulator's
*Annual Statistical Booklet 2019*, reports gas shares of generation for "the eastern and central
regions" versus "the western and southern regions". Those are operating areas, not منطقة
provinces, and there is no published crosswalk. Any regional electricity figure therefore needs a
plant-level inventory placed into provinces by point-in-polygon — it cannot be read off an official
table.

No other boundary issue was found: Natural Earth has no separate feature for the Saudi–Kuwaiti
Partitioned (Neutral) Zone.

---

## 2. Source-by-source audit

Field order follows the lane brief. "Raw redistribution" means: may this project vendor and
republish the source file itself (as `data/processed/` effectively does), not merely cite facts
from it.

### 2.1 Saudi Aramco — Annual Report

- **Provider / product:** Saudi Arabian Oil Company (Aramco), *Annual Report* (English and Arabic
  editions). 2025 edition read via its "Results and performance" section PDF:
  `https://www.aramco.com/-/media/publications/corporate-reports/reports-and-presentations/2025/fy/sections/ara-2025-results-english.pdf`.
  The full report PDF exceeds 10 MB and was not fetched.
- **Sector:** refining (per-refinery), upstream and gas aggregates, captive power, chemicals.
- **Coverage:** Aramco group worldwide, with in-Kingdom assets separable. Refining: all nine
  in-Kingdom refineries in which Aramco has an interest (five wholly owned, four affiliated, in
  Aramco's own words), plus eight international ones.
- **Temporal range:** annual since the 2019 IPO; the 2025 report carries a 2021–2025 history of
  gross and net refining capacity and of total liquids and gas production.
- **Cadence:** annual (published ~March for the prior 31 December).
- **Machine accessibility:** PDF only; the full report is too large for a simple fetch, the section
  PDFs are not. Text extracts cleanly with `pypdf`. No API. `aramco.com` HEAD requests from a script
  hung on this machine; GET via the fetch tool worked.
- **Authentication:** none.
- **License / terms:** corporate copyright; no open licence. **(Terms page not read this session.)**
- **Raw redistribution:** **no** — treat as all-rights-reserved. Facts (capacities, equity
  percentages, dates) may be extracted and cited; the PDF must not be vendored.
- **Geography precision:** facility name only. Province is inferable from the facility's town
  (Ras Tanura, Jubail → Eastern; Riyadh → Riyadh; Yanbu' → Al Madinah; Rabigh → Makkah;
  Jazan → Jazan) and that is the only precision this project needs or should use.
- **Status semantics:** none explicit. A refinery is listed or not listed. The closed Jeddah
  refinery simply does not appear. No commissioning or retirement dates on the capacity page;
  changes must be inferred by diffing annual editions.
- **Capacity semantics:** **mbpd (thousand barrels per day), 100% gross basis per refinery**, with
  Aramco's "effective ownership" percentage alongside. Verified arithmetically, not assumed: the 17
  listed refineries sum to 7,776 mbpd against the stated "gross refining capacity of 7.8 mmbpd",
  and applying the equity percentages reproduces the stated net figures (in-Kingdom ≈ 2,638 mbpd ≈
  63% of 4.2 mmbpd as stated; international ≈ 1,581 mbpd vs stated 1.6 mmbpd). Stream-day vs
  calendar-day basis is **not stated**.
- **Known biases:** company presentation; capacities may be nameplate after debottlenecking
  rather than operable; no utilisation per plant; financial-materiality framing.
- **Language:** English and Arabic editions.
- **ADOPTION: adopt** — as the refining denominator, **gross basis, in-Kingdom rows only**, one
  edition per year to build a dated census. Reason: it is the only source found that covers every
  in-Kingdom refinery on one stated basis, and it is internally reconcilable.

### 2.2 Saudi Aramco — quarterly results, interim reports, press releases

- **Provider / product:** Aramco quarterly and half-year interim reports and results press releases
  (index at `aramco.com/en/investors/reports-and-presentations`). Read: FY-2025 results press
  release; H1-2026 interim report.
- **Sector:** aggregate upstream (total liquids, total gas, total hydrocarbons), downstream KPIs
  ("supply reliability", "downstream utilisation of Aramco's crude production").
- **Coverage:** Aramco company totals. Not facility-level.
- **Temporal range:** quarterly since 2019.
- **Cadence:** quarterly.
- **Machine accessibility:** small PDFs, text-extractable.
- **Authentication:** none.
- **License / terms:** corporate copyright. **Raw redistribution: no.**
- **Geography precision:** national (company) only.
- **Status semantics:** none at facility level. Material events appear only as narrative
  disclosure, framed against financial materiality. The H1-2026 interim report states that certain
  Company and affiliate facilities in the Kingdom "were targeted in attacks" during Q2 and July 2026
  and that the impact was "not material" to financial position as of 30 June 2026 — **without
  naming any facility**.
- **Capacity semantics:** production in mbpd / mmscfd / mboed, company basis; "total liquids"
  includes NGL and condensate, so it is **not** a crude-only figure.
- **Known biases:** investor-relations framing; disruption is disclosed at the company-financial
  threshold, not the operational one.
- **Language:** English and Arabic.
- **ADOPTION: derived-facts-only** — as dated national context and as evidence of the reporting
  environment. Never as an index input, and never converted into a capacity-loss figure.

### 2.3 Saudi Aramco — bond prospectuses / IPO prospectus

- **Product:** 2019 IPO prospectus (listed on the investor page); international bond / sukuk base
  prospectuses (EIA's 2021 brief cites a 16 November 2020 bond prospectus).
- **Assessment:** richer than annual reports for one point in time, but one-off, very large, and
  written for investors. **Not opened this session.**
- **Raw redistribution:** no.
- **ADOPTION: discovery-only** — useful to settle a specific historical capacity question, not as a
  feed.

### 2.4 Saudi Electricity Company (SEC)

- **Provider / product:** SEC (Tadawul-listed, majority state-owned) earnings releases, results
  presentations, annual reports. Read: *Earnings Release Q3 2025* (Nov 2025),
  `https://www.se.com.sa/-/media/sec/Investors/Earning-Reports/SEC_ER_2025-Q3_Final.ashx`.
- **Sector:** generation (aggregate), transmission (aggregate), distribution.
- **Coverage:** the Kingdom's grid-connected generation broken into three owner classes, plus SEC's
  own network statistics. Q3 2025: grid-connected capacity **93,858 MW** (SEC 55,962; IPP & IWPP
  22,572; Others 15,324), up from 89,181 MW at Q3 2024; renewables ~12.3 GW grid-connected;
  transmission **104,628 circuit-km**, **1,305 substations**, 529,382 MVA.
- **Temporal range / cadence:** quarterly releases; annual reports.
- **Machine accessibility:** the `.ashx` PDF links work from a script; the HTML investor pages
  returned a WAF "Rejected" page. Text extracts with `pypdf`.
- **Authentication:** none.
- **License / terms:** corporate copyright. **Raw redistribution: no.**
- **Geography precision:** **national only** in the releases read. No plant list, no
  province breakdown.
- **Status semantics:** connected capacity at a quarter end; no units, no retirements.
- **Capacity semantics:** MW / GW grid-connected. **Scope caveat:** "grid-connected" is not "all
  generating capacity". Aramco alone reports **6.3 GW** of captive generation in 2025, of which only
  0.5 GW was spilled to the grid. Third-party totals (one aggregator states 121.4 GW for 2024 —
  **not verified**) are on a different scope again. Do not mix scopes.
- **Known biases:** company framing; Q3 numbers are summer-peak quarter.
- **Language:** English and Arabic.
- **ADOPTION: derived-facts-only** — a dated national denominator cross-check for whatever
  plant-level inventory is adopted. It cannot itself be a regional denominator.

### 2.5 SERA — the electricity regulator (formerly ECRA, then WERA)

- **Provider / product:** the electricity regulator's *Annual Statistical Booklet for Electricity
  and Seawater Desalination Industries*. Naming history: Electricity & Cogeneration Regulatory
  Authority (ECRA) → Water & Electricity Regulatory Authority (WERA; EIA's 2021 brief cites
  "WERA, ... Annual Statistical Booklet 2019") → SERA (per the lane brief; **current name not
  confirmed from a primary page**).
- **Sector:** generation and transmission by operating area; plant lists in older booklets.
- **Coverage / precision:** by the four SEC operating areas, per the EIA citation — not provinces.
- **Machine accessibility:** **`www.ecra.gov.sa` no longer resolves (DNS ENOTFOUND)**;
  **`sera.gov.sa` timed out** from this machine on 2026-10-30. Whether this is geo-restriction or an
  outage is not established. WRI GPPD's Saudi rows are almost entirely ECRA-sourced (84 of 90), so
  an ECRA plant list did once exist publicly.
- **License / terms, raw redistribution:** unknown — not readable.
- **Language:** historically Arabic and English.
- **ADOPTION: discovery-only.** Re-try from another network; if the booklet is reachable and has a
  dated plant list, it is the natural Saudi-official cross-check for GEM.

### 2.6 Ministry of Energy (وزارة الطاقة)

- **Product:** policy statements, announcements, any published statistics.
- **Machine accessibility:** `www.moenergy.gov.sa` **timed out** from this machine (twice, plus a
  scripted probe). The national open-data portal `od.data.gov.sa` also timed out.
- **Assessment:** in practice the Ministry's announcements reach the outside world through the
  Saudi Press Agency (SPA) and wire services; it is not known to publish facility-level capacity
  tables. **(Content not verified this session.)**
- **Raw redistribution:** unknown.
- **ADOPTION: discovery-only.**

### 2.7 GASTAT — General Authority for Statistics (الهيئة العامة للإحصاء)

- **Provider / product:** GASTAT energy statistics: categories "Oil and Gas Statistics",
  "Renewable Energy Statistics", "Energy Efficiency Statistics", "Electrical Energy Statistics",
  "Household Energy Statistics" under `stats.gov.sa/statistics?index=124295&subindex=124703`.
- **Coverage / temporal range / cadence:** not established — the category links are JavaScript
  placeholders and the listing page returned "No Results Found" to a scripted reader.
- **Machine accessibility:** site reachable (HTTP 302 → content); publication listing not
  machine-navigable.
- **Authentication:** none.
- **License / terms:** **open.** The Use Policy (§1.2.2) permits users to "copy, reproduce, publish,
  distribute, transmit, adapt, modify" GASTAT material "for any purpose, including commercial use",
  provided GASTAT is acknowledged as the official source and modifications are marked; modified
  material may not be presented as official GASTAT statistics (§1.4.2). Trademarks excluded.
- **Raw redistribution:** **yes**, with attribution and change-marking. The only clearly
  redistributable Saudi-official source found.
- **Geography precision:** unknown for energy; GASTAT does publish other series by administrative
  region, so a regional electricity table is possible but **not found**.
- **Language:** Arabic and English.
- **Note:** "SASO" in the lane brief is the Saudi Standards, Metrology and Quality Organization — a
  standards body, not a statistics publisher; it has no role here.
- **ADOPTION: derived-facts-only**, upgradable to **adopt** if a regional electricity table is
  located. Licence is the best of any Saudi-official source.

### 2.8 JODI — Joint Organisations Data Initiative (Oil and Gas World Databases)

- **Provider / product:** JODI-Oil and JODI-Gas World Databases (IEF-coordinated; OPEC is a partner
  organisation). Countries self-report monthly.
- **Sector:** crude production, exports, refinery intake/output, direct crude burn, stocks; gas
  production and consumption.
- **Coverage / temporal range:** national monthly, January 2002 → about one month ago. Latest
  update seen: 21 October 2026, with "51 countries" reporting August 2026 data.
- **Cadence:** monthly.
- **Machine accessibility:** **good.** Annual CSVs (`primaryyear2026.csv`, `secondaryyear2026.csv`,
  back to 2002), a full `.ivt` bundle, country notes in `jodi-oil-country-note.xlsx`, and a REST API
  (free account required). The last CSV column is a colour code (1 blue / 2 yellow / 3 white) which
  is JODI's per-value quality assessment — carry it, never drop it (meaning of each colour **not
  re-read this session**).
- **Authentication:** none for bulk CSVs; free account for the API.
- **License / terms:** no licence text on the download pages; only "© Copyright JODI 2026" and the
  statement that data "can be downloaded, for free". **Treat as attribution-required,
  redistribution-unclear.**
- **Raw redistribution:** **unclear** → store derived Saudi series with citation, do not vendor the
  world file.
- **Geography precision:** national.
- **Status / capacity semantics:** flows, not capacities. Self-reported by the Saudi side (EIA's
  2021 brief draws Saudi crude-burn and fuel-oil-demand figures from JODI, confirming Saudi oil
  participation). JODI-Gas Saudi participation **not confirmed** this session.
- **Known biases:** self-reported; revisions; the Saudi submission is the official figure, which is
  exactly why OPEC also publishes independent "secondary sources".
- **Language:** English.
- **ADOPTION: adopt** — as the national monthly context series (refinery throughput, crude burn,
  exports). Never as an index input; a monthly national dip is not a facility-attributed disruption.

### 2.9 OPEC — Annual Statistical Bulletin (ASB) and Monthly Oil Market Report (MOMR)

- **Product:** ASB (annual: production, refining capacity, exports, by member); MOMR (monthly crude
  production by **secondary sources** alongside **direct communication**).
- **Why it matters:** the secondary-source series is the standard independent check on a member's
  self-reported production; the gap between the two is itself informative.
- **Machine accessibility:** `opec.org` and `asb.opec.org` returned **HTTP 403 / 402** to scripted
  requests on 2026-10-30. Interactive ASB normally offers Excel downloads. **No figure read.**
- **License / terms:** **not verified.**
- **Raw redistribution:** assume **no** until terms are read.
- **Geography precision:** national.
- **ADOPTION: derived-facts-only** — cite specific national figures with edition, manually.

### 2.10 U.S. EIA — Country Analysis Brief: Saudi Arabia

- **Product:** `eia.gov/international/content/analysis/countries_long/saudi_arabia/` — **last
  updated 4 October 2024** (an older executive summary dated 2 December 2021 is also live as a PDF).
- **Sector:** all, national; plus an Aramco domestic refinery table (2023, nine refineries, total
  3,291 thousand b/d, "includes only domestic refining operations", sourced OPEC/Aramco/SATORP) and
  an estimated gas-processing-plant capacity table (2023, eight plants).
- **Key facts read:** primary energy production 2022 **29.7 quad Btu**, 85% petroleum liquids,
  15% gas, 0% coal; crude production **9.5 million b/d in 2023**; dry gas **4.3 Tcf** in 2022 and
  2023; generation **~453 TWh in 2023** (62% gas, 38% oil, <1% renewables); crude exports
  **7.0 million b/d in 2023**; "Saudi Arabia meets all of its natural gas consumption with domestic
  production"; 76% average utilisation of the 3.3 million b/d domestic refining capacity.
- **Cadence:** irregular (2021, 2024).
- **Machine accessibility:** HTML readable; PDF versions text-extractable.
- **License / terms:** U.S. government work, public domain. **Raw redistribution: yes** for EIA's
  own text and figures — but its refinery table is credited to OPEC and Aramco, so those numbers
  carry *their* terms.
- **Geography precision:** national; facility names only.
- **Capacity semantics:** refinery table **does not state gross vs net**; it matches Aramco's gross
  per-plant figures for some plants and differs for others (Yanbu' 220 vs Aramco-2025 250;
  Riyadh 126 vs 130; YASREF 430 vs 450) — a vintage difference, not a basis difference.
  Gas-plant capacities are labelled **"estimated"**.
- **Known biases:** secondary compilation; stale between editions.
- **Language:** English.
- **ADOPTION: derived-facts-only** — national context and an independent cross-check on the Aramco
  refinery list. Never a denominator by itself.

### 2.11 Energy Institute — Statistical Review of World Energy

- **Product:** annual national series (production, consumption, capacity) — the continuation of the
  BP Statistical Review.
- **Machine accessibility:** `energyinst.org` returned **HTTP 403** to scripted requests. Normally
  offers XLSX / CSV "consolidated dataset" downloads. **No figure read.**
- **License / terms:** **not verified this session.**
- **Raw redistribution:** assume **no** until verified.
- **Geography precision:** national.
- **ADOPTION: derived-facts-only** — consistent cross-country national context, cited by edition.

### 2.12 Global Energy Monitor — trackers

- **Products:** Global Integrated Power Tracker (GIPT; "most recent release ... September 2026";
  unit capacity, status, ownership, fuel, start year, retirement date, geolocation); Global Oil and
  Gas Plant Tracker; Global Gas / Oil Infrastructure Trackers (GGIT / GOIT).
- **License / terms:** CC BY 4.0, verified verbatim in this repo's earlier work
  (`docs/POWER_SOURCE_RECONCILIATION.md`, "Licence position"); the GIPT landing page itself shows
  only "All Rights Reserved" site boilerplate, so cite the tracker licence, not the page footer.
- **Raw redistribution:** **yes**, with attribution (per the earlier verification).
- **Machine accessibility:** form-gated download — the same human-in-the-loop acquisition the
  pipeline importer already models.
- **Geography precision:** unit-level coordinates — **aggregate to province before anything is
  emitted**, as the Russia build already does for plants.
- **Status semantics:** explicit status plus start and retirement years — the axis whose absence
  blocks the Russian historical denominator (`docs/GENERATION_DENOMINATOR_AUDIT.md`).
- **Saudi coverage:** **not inspected this session** (file not acquired).
- **ADOPTION:**
  - **GIPT → adopt** as the generation denominator once a release is acquired.
  - **GGIT / GOIT for Saudi → reject.** The Saudi pipeline system is not needed for any province-level
    exposure measure this project can support, and a pipeline layer for this country would centre
    the map on exactly the routing information the scope boundary excludes. Recommend no Saudi
    pipeline geometry at all, analytic or context.

### 2.13 WRI Global Power Plant Database v1.3

- **Already cached:** `data/raw/wri_gppd.csv`. Saudi (`SAU`) rows, counted this session:
  **90 plants, 84,342 MW** — 53 oil (49,702 MW), 31 gas (34,502 MW), 6 solar (137 MW), **no wind**.
  84 of 90 rows cite "ECRA" as source. Newest commissioning year **2016**; `year_of_capacity_data`
  empty on all 90.
- **Licence:** CC BY 4.0; raw redistribution yes.
- **Status semantics:** none (no status, no retirement field) — the known WRI defect.
- **Why reject as denominator:** it is a ~2016 snapshot of the regulator's list. It misses the
  entire renewable build-out (WRI 137 MW solar vs SEC-reported ~12.3 GW grid-connected renewables at
  Q3 2025; the 400 MW Dumat Al Jandal wind farm that EIA reports online in August 2021 is absent)
  and its 84.3 GW total sits ~9.5 GW below SEC's 93.9 GW grid-connected figure for Q3 2025 — a gap
  of unknown composition, because WRI's scope (grid vs captive) is not stated. Its oil/gas split
  is by primary fuel only, while Saudi plants commonly switch fuel (SEC's Q3-2025 release describes a
  liquid-to-gas conversion at Rabigh-2).
- **ADOPTION: reject** as denominator; **discovery-only** for crosswalking to GEM (WRI gives an
  ECRA-derived plant name and a location).

### 2.14 OpenStreetMap (Overpass)

One count query, 2026-10-30, area `ISO3166-1=SA`:

| Selector | Count |
|---|---|
| `power=plant` (nwr) | 199 |
| `power=substation` tagged 380/230/220/132 kV | 638 |
| `power=line` ways | 3,229 |
| `industrial=oil_refinery` | **0** |
| `man_made=pipeline` + `substance=gas` ways | 119 |
| `man_made=pipeline` + `substance~oil` ways | 1,271 |
| `route=pipeline` relations | **0** |

- **Licence:** ODbL; raw redistribution yes with share-alike.
- **Assessment:** zero refinery tags (as in Russia) and **zero pipeline route relations** — the
  method this project uses to reconstruct pipelines (`docs/PIPELINE_GAP_AUDIT.md`) has nothing to
  work on. Transmission lines exist as ways, but SEC reports 1,305 substations against 638 tagged in
  OSM at ≥132 kV, so OSM substation coverage is roughly half.
- **ADOPTION: reject** for Saudi analytic layers; **discovery-only**. In particular no Saudi
  pipeline geometry should be drawn (see 2.12).

### 2.15 Natural Earth admin-1

- Public domain; 13 Saudi regions present with ISO codes and Arabic names (section 1).
- **ADOPTION: adopt**, with the alias table and the SA-13 gap handled explicitly.

### 2.16 English Wikipedia — *List of oil refineries*, "Saudi Arabia" section

- Read via the MediaWiki API (section 57) this session. Nine bullet entries.
- **Defects:** four entries carry "Citation needed (May 2026)"; it lists the **closed Jeddah
  refinery**; it gives SASREF a Shell partner (Aramco's 2025 report lists SASREF at 100% equity);
  Petro Rabigh at 325 kb/d with an ownership string that matches neither Aramco's 57.61% nor any
  current shareholder description; Yanbu' 225 and Riyadh 120 vs Aramco 250 and 130; most citations
  are 2009–2013 trade blogs.
- **Licence:** CC BY-SA 4.0.
- **ADOPTION: reject** as a denominator. This is the Saudi version of the problem
  `REFINERY_CAPACITY_BASIS.md` documents for Russia: an unreconciled list of mixed vintage.

---

## 3. The refining capacity basis — the mixed-basis trap, explicitly

`docs/REFINERY_CAPACITY_BASIS.md` found that the Russian refining numerator and denominator come
from different sources and disagree by ~6%. Saudi Arabia is **more** exposed to that trap than
Russia, for a structural reason: **four of the nine in-Kingdom refineries are joint ventures**, so
every capacity figure exists in at least two legitimate forms.

Aramco's 2025 Annual Report lists all nine in-Kingdom refineries with gross capacity and Aramco's
effective equity; four are joint ventures (50-62.5%). Summed: **3,352 mbpd gross**, **≈ 2,638 mbpd**
Aramco net share (computed). **The per-refinery table is deliberately not reproduced in this repository**
(iteration-14 red team): nothing for Saudi Arabia is scored, so a facility-by-facility capacity list
would serve no analytic purpose here while an attack campaign on the same facilities is under way. A
future iteration that scores refining rebuilds it from the annual report, region-level only.

Three possible bases, which must never be mixed:

1. **Gross (100%) physical capacity** — 3,352 mbpd. What a disruption physically affects.
2. **Aramco net equity share** — ≈ 2,638 mbpd. What Aramco's "net refining capacity" headline
   (4.2 mmbpd, of which 63% in-Kingdom) is built from. A financial concept.
3. **Third-party compilations** (EIA 3,291; Wikipedia) — mixed vintages, basis unstated.

**Recommendation:** gross basis, from the Aramco annual report, for **both** numerator and
denominator; record equity percentage as metadata only. A strike-report "capacity" figure carried
on an incident must **not** be used as the numerator capacity — resolve the incident to the
registry row and take the registry's gross figure, which is option B of
`REFINERY_CAPACITY_BASIS.md` applied from day one. Net-share capacity would understate JV plants by
37.5–50% and make the exposure a statement about Aramco's balance sheet rather than the country's
refining system.

Open points, recorded rather than guessed:

- Whether any **non-Aramco** crude refinery operates in the Kingdom — **not yet researched**. Aramco
  describes itself as sole supplier of the domestic market, and EIA's table has the same nine plants,
  but neither statement is a census.
- **Stream-day vs calendar-day**: not stated by Aramco.
- **Vintage drift is real**: three of the nine plants' capacities changed between EIA's 2023
  table and Aramco's 2025 report. A dated census needs each annual report's page, not one edition.
- Petro Rabigh is an integrated refining and petrochemical complex; its published refinery
  capacity is the right figure for a fuels-refining base (contrast Tobolsk in the Russian
  registry, which is excluded as non-fuels).

---

## 4. How opaque facility-level reporting is

Plainly: **very**, except for refinery capacity.

- **Capacity** is published for refineries (Aramco, annually) and for some gas plants (EIA,
  "estimated"). For power plants the only plant-level public list found (WRI ← ECRA) is a decade
  old; the current official figures are national aggregates by owner class.
- **Status and disruption** are disclosed by Aramco at the **company-financial materiality
  threshold** in quarterly reports, without naming facilities (H1-2026 interim report, quoted in
  2.2). SEC releases contain no outage reporting.
- **Recovery** is almost never quantified. Aramco and Saudi official statements, where they exist,
  tend to say operations "resumed" or were "not material"; durations and partial-operation levels are
  rarely stated. That is a statement about the sources found, not about events.
- **Official primary sites** (Ministry, regulator, national open-data portal) were unreachable from
  this machine. Much official information reaches the outside world only through SPA and wire
  services.

## 5. Low reported incidents ≠ low disruption

The number of incidents that will be found for Saudi Arabia is a property of **the reporting
environment**: a state-majority operator with a materiality-based disclosure policy, state-aligned
domestic media, no independent regulator publication reachable from outside, no structured
open-source compilation equivalent to the Wikipedia strike table used for Russia, and — for
attacks — parties to a conflict whose claims are themselves unreliable. Technical outages (fires,
trips, unplanned shutdowns) are the least likely to surface at all.

The dashboard must therefore never render a sparse Saudi map as "low disruption". The correct
reading is **"low *reported* disruption, coverage unknown"** — the *unknown* / *not yet researched*
distinction the project already enforces. Aramco's own H1-2026 disclosure of attacks on unnamed
in-Kingdom facilities, alongside a reported fall in quarterly total liquids production from 10,561
mbpd (Q1 2026) to 7,566 mbpd (Q2 2026), shows that material disruption can be visible in
national aggregates while remaining invisible at facility level. Those aggregate figures are
context; they are not a capacity-loss estimate and must not be turned into one.

---

## 6. Attribution string if adopted

> Refining capacity: **Saudi Aramco Annual Report** (facts extracted; not redistributed).
> Boundaries: **Natural Earth** (public domain). National context: **U.S. EIA** (public domain);
> **JODI** World Databases; **GASTAT** (official source; figures modified by this project where
> marked). Generation (when acquired): **Global Energy Monitor, Global Integrated Power Tracker**,
> CC BY 4.0.
