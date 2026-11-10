# Iteration 18 review — the rest-of-world picture

*In progress. Sections are filled in as work completes; a section that still says "pending" is not
done.*

## 0. Checkpoint (2026-11-10, before any research)

### 0.1 Baseline

| | |
|---|---|
| Start SHA | `a5c628e` (fast-forwarded from `024a43d` over five bot refreshes; the 2026-11-08 refresh is absent from history) |
| Production | serving the 2026-11-09 build, ESDI 7.02, 184 events, built 13:57 UTC |
| Country corpus | US 139 records / 110 episodes; Canada 26 / 25; China 11 / 9; India 10 / 8; Saudi Arabia 9 / 9. Total 195 / 161 |
| Recovery (observed + estimate / researched, none / not researched / withheld) | US 73 / 7 / 59 / 0; Canada 17 / 0 / 9 / 0; China 6 / 5 / 0 / 0; India 8 / 1 / 1 / 0; Saudi 0 / 1 / 0 / 8 |
| Held in local queues | US 12, Canada 9, China 4, India 9, Saudi 2 (36 by independent-review flag; 12 are owner rulings) |
| Global payload | manifest 5.3 KB (1.7 gz), world 431 KB (125 gz) |
| Country payload gz | US 136 KB, CA 114, CN 88, IN 61, SA 21 |

### 0.2 All 35 lanes under the new vocabulary (iteration-17 evidence only; nothing upgraded)

| Lane | Execution | Source window | Basis |
|---|---|---|---|
| US G1 | enumerated_complete | publisher_not_yet_released | 2022-2025 enumerated; no 2026 file |
| US G2 | partial | inaccessible | NERC read; FERC refused; no 2026 report |
| US H1 | partial | current_through_end_date | through 2026-10-31 |
| US H2 | enumerated_complete | publisher_not_yet_released | four 2026 TCRs unpublished |
| US U1 | partial | inaccessible | BSEE refused; EIA half covered |
| US P1 | partial | inaccessible | CAOs enumerated; incident files refused |
| US L1 | partial | no_census_exists | 10 of 90 queries |
| US R1 | declared_search_complete | no_census_exists | 15 of 15 |
| US C1 | declared_search_complete | no_census_exists | 10 of 10 |
| CA CG1 | enumerated_complete | publisher_not_yet_released | source stops 2022-12-22 |
| CA CG2 | enumerated_complete | publisher_not_yet_released | no 2026 report |
| CA CG3 | partial | rolling_archive_gap | IESO keeps 90 days; AESO no 2026 list |
| CA CH1 | partial | publisher_not_yet_released | no 2026 edition; holds lack a peak |
| CA CP1 | partial | inaccessible | CER enumerated; TSB refused |
| CA CR1 | declared_search_complete | no_census_exists | 15 of 15 |
| CA CU1 | partial | no_census_exists | 5 of 10 |
| CA CL1 | not_started | no_census_exists | not run |
| CN CN1 | partial | current_through_end_date | 2 of about 57 releases |
| CN CN2 | partial | unknown | queries run, endpoints not enumerated |
| CN CN3 | partial | no_census_exists | no official notice reached |
| CN CN4 | not_started | unknown | exchange search forms not reached |
| CN CN5 | partial | no_census_exists | 5 of 15, named outlets not reached |
| CN CN6 | not_started | no_census_exists | not run |
| IN IN1 | not_started | inaccessible | every Grid-India host refused |
| IN IN2 | partial | unknown | search ignored the site operator |
| IN IN3 | partial | unknown | endpoints not enumerated |
| IN IN4 | partial | unknown | endpoints not enumerated |
| IN IN5 | not_started | unknown | not run |
| IN IN6 | not_started | no_census_exists | not run |
| IN IN7 | partial | no_census_exists | not restricted to named outlets |
| SA SA1 | partial | inaccessible | SPA script-rendered; queries missing |
| SA SA2 | partial | inaccessible | Tadawul refused; annual reports unread |
| SA SA3 | partial | unknown | JODI has no attribution; GASTAT not reached |
| SA SA4 | not_started | inaccessible | MOMR refused |
| SA SA5 | partial | no_census_exists | 6 of 15 |

Totals: 4 enumerated through the latest publication (G1, H2, CG1, CG2), 3 declared query sets run
(R1, C1, CR1), 20 partial, 8 not started... the counts are recomputed by the build from
`research_log.json` once the new pass is logged.

### 0.3 Research workers

Fable for source discovery and enumeration, Opus for adjudication, integration and review. One
worker per lane family: US L1; H1, U1, P1 and annual re-checks; recovery. Canada CL1; CU1; CG3, CP1,
hazards and recovery audit. China CN1; CN2 and CN3; CN4; CN5; CN6; recovery. India IN1; IN2, IN3,
IN4; IN5; IN6; IN7; recovery. Saudi SA1; SA2; SA3 and SA4; SA5. Global context: licensing and source
comparison. Each worker writes `data/candidates/sweep18/<tag>_{candidates,lanes}.json` after every
source family and has a stated search cap. Web search is shared and limited; fetches of official
listings are used first.

### 0.4 Global context sources

| Source | Coverage | Licence | Decision |
|---|---|---|---|
| EIA International Energy Statistics, bulk `INTL.zip` (release 2026-10-16) | about 230 countries, total production and consumption, by fuel, oil, gas, coal, electricity by fuel, 2024 common | US government work, series copyright field "None"; attribution requested | **Canonical** |
| Our World in Data energy dataset (Energy Institute, Ember and others) | oil, gas, coal, electricity, primary consumption | CC BY 4.0 for OWID's compilation; underlying terms vary | Validation only; no values committed |
| Energy Institute Statistical Review | full | free use with attribution; redistribution terms to confirm | Validation only unless licence confirmed |
| Ember | electricity | CC BY 4.0 | Not needed: EIA carries generation by fuel. Validation only |
| World Bank | few current energy indicators | CC BY 4.0 | Not used |
| IEA | full | restrictive | Rejected |
| Global Energy Monitor | facility level | CC BY 4.0 | Rejected for this feature: facility catalogue |
| LNG and refining capacity | EIA has no current series | n/a | Omitted unless one common licensed source is found; never mixed |

### 0.5 Priorities

- **US:** L1 first (80 queries remain), then H1 from 2026-10-31, PHMSA and BSEE alternatives, annual
  re-checks, US corpus red team, then 59 unresearched recovery records.
- **Canada:** CL1 first, CU1 remainder, CG3 and CP1 alternatives, then hazards and the recovery audit.
- **China:** Chinese-language work leads. CN1 all monthly releases by fetch, CN4, CN6, CN5 missing
  families, CN2 direct archives, CN3 by province.
- **India:** IN5 and IN6 first, then IN1 alternatives with an evidence comparison, direct PIB, PPAC and
  Coal India enumeration, IN7 restricted to the five named outlets.
- **Saudi:** occurrence and contemporaneous effect only; every published record re-read for status leaks.

### 0.6 Global context payload and UI

`global/energy_context.json`: one row per country, national aggregates only, comparison year 2024,
about 60 KB raw and 15 KB gzipped. Map colour is a sequential national-energy scale, unrelated to
the ESDI palette; monitored status is a separate thick outline plus ring marker, stated in the
legend. A context-only country opens a small card saying "Not systematically monitored for
disruptions" and loads nothing else. Home page order: world context, monitored systems, recent
evidence (chronological, filterable). `global/data_quality.json` carries lane states and vintages.

### 0.7 Risks

1. The shared web-search budget ends before the plans finish: lanes are logged partial with exact counts.
2. A world map coloured by production reads as "monitored" or as a ranking: separate encodings, alphabetical default table.
3. New Saudi or theatre text leaks status: same gates, exhaustive re-read.
4. Daily refresh churn from a new artifact: context file has no build time and is reused.
5. Reviewer throughput: every accepted record needs three blind roles plus confirmation.
6. The bot moves `main` during the run: fetch, regenerate, never pick a generated side.

### 0.8 Order

Plans committed; workers launched; coverage model and global context built while they run; imports
after blind review; corpus, recovery and episode audits; UX; tests and mutations; red teams; release.

## Sections pending

1-17 are written at the end of the run.
