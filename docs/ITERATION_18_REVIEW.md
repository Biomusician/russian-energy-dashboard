# Iteration 18 review — the rest-of-world picture

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
(R1, C1, CR1), 20 partial, 8 not started; the counts are recomputed by the build from
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

## 1. What this pass did and did not do

**The research pass did not finish.** A shared limit of 200 web searches per turn was reached about
two-thirds of the way through. Direct page requests still worked. The limit was not worked around.
Every lane it stopped carries `stopped_by: search_limit` and says so in its limitation. A new turn is
needed to run the rest: `scripts/research_tools.py next [cc]`.

Everything else in the brief was done or is listed in §16 as not done.

## 2. National energy context

One source (U.S. EIA `INTL.zip`, release 2026-10-16), one comparison year (2024), 219 countries and
territories, 22 series. Map modes: total production, crude, gas, coal, electricity, largest fuel,
producer or consumer. Separate doc: [GLOBAL_ENERGY_CONTEXT.md](GLOBAL_ENERGY_CONTEXT.md).

The map's fill is a national figure; monitoring is a separate thick outline, named in the legend. A
context-only country's card says "Not systematically monitored for disruptions" and shows no count.
Selecting a context-only country fetches nothing else.

Omitted: LNG and refining capacity. EIA has no such series and no open national source was verified.

The red team (§12) found rounding had created false zeros, so values now keep significant digits.

## 3. Coverage model

Two dimensions per lane; see GLOBAL_METHODOLOGY "Research coverage vocabulary". No percentage. Old
passes keep the status they were logged with.

## 4. Lane results, by country

Full per-lane tables are in Part B of each `docs/countries/<CC>_LANE_PASS_18.md`.

- **United States.** LNG 3 of 9 terminals; PHMSA's incident files still refused, the enforcement listing was enumerated instead; NHC's Arthur report read; no DOE report in the window.
- **Canada.** Terminals and upstream searched; bare terminal tokens do not work as search strings; TSB refused.
- **China.** Chinese-language sources ran in three lanes; NBS 53 of 53 releases, no attribution to any disruption; NEA's accident bulletins stop in 2021; notice archives unreachable.
- **India.** Every Grid-India and regional dispatch host refused for the third pass; no census alternative exists; MoPNG monthly reports stop attributing causes after June 2024; PNGRB has no incident stream.
- **Saudi Arabia.** Occurrence only. Two lanes could not start. No new event passed.

## 5. New and changed records

Seven new records, each through blind three-role review and a confirmation round: Osage pipeline, Whiffen Head, a British Columbia generation loss, British Columbia windstorms, Sichuan industrial power halt, Numaligarh refinery fire, Gauna-Bawana gas pipeline. Three more reached review and are held for owner rulings (§15).

Five published records were held after a corpus audit, because a clause was not met or no opened source supported the placement. Two Yunnan records' episode dissolved. One US record left a named-storm episode, because its only citation names no storm.

| Country | Records before | Records now |
|---|---|---|
| Canada | 26 | 28 |
| China | 11 | 10 |
| India | 10 | 11 |
| Saudi Arabia | 9 | 9 |
| United States | 139 | 139 |

Those are inside-country facts; they are not a comparison.

## 6. Recovery

32 updates after a two-role review (evidence, safety), one proposal not applied (the source was behind a registration wall), two rejected and recorded as no public evidence. OE-417 entries are partial with a caveat. The formal policy is in GLOBAL_METHODOLOGY. The cross-country statistic now has one row, by design: completed kinds, a sourced date, at least two countries.

## 7. Data quality

Link check of every published citation, once: counts per country on the country page. A refusal is not a dead link. Publication dates only from what a page states about itself. No date was inferred from an address or a retrieval date.

## 8. Product

Home in three levels (world, monitored systems, recent evidence), world context, country page Research tab, event filters by year and type, a region list as a keyboard route to the map, source browser filters.

## 9. Safety

A red team found that held records' names had reached research-log prose. `write_research_pass.py` now removes them, and a test checks that no queue id appears in any served string. Status wording now reads URL slugs and more Arabic forms and checks more fields. Theatre notes were generalised from component to plant level. Citation addresses stating strike distance were reduced to the publisher's home page, with the record's sources otherwise unchanged. Public documents no longer describe a covered record's status.

National context is country-level and cannot reach analytics: `test_no_analytic_module_can_reach_national_context`, plus a build-level test that changing the source changes no disruption figure.

**Residual.** A withheld record's feed entry carries its episode id, which contains the facility's name. The name is already public on that record, so nothing new is disclosed, and the feed's withholding is of effect, not identity.

## 10. Tests

At the release commit: Python 613 passed, 2 skipped; frontend unit 254 passed; typecheck clean; Playwright 131 passed, 1 skipped (29 of them in the new context suite, across the viewport sizes in the brief); mutation campaign 56 of 56 caught, up from 36. A temporal fuzz test builds every country at five dates, and a repeat build changes only `build_time` and `publication_freshness`.

## 11. Performance

| Artifact | Before (gz) | After (gz) |
|---|---|---|
| manifest | 1,706 B | 1,822 B |
| energy_context (new, lazy) | none | 19,583 B |
| data_quality (new, lazy) | none | 9,312 B |
| recent_evidence (new, lazy) | none | 4,306 B |
| US system.json | 10,537 B | 13,173 B |

The JS entry grew from 68.37 kB to 76.61 kB gzipped; the country view from 9.26 kB to 11.25 kB. MapLibre is unchanged. Energy context and the data-quality panels load only after the page shell.

## 12. Red teams (subagents; findings fixed unless listed in §15)

Context, licence and data basis; research status, recovery and cross-country; first-time user; final safety and test architecture. Largest changes that came from them: the Far East and Ukraine card errors, false zeros, a recovery statistic that used partial reports and identified countries, CR1 and R1 corrected to partial, held-record leak.

## 13. First-time-user tasks

Browser tests cover the search, card, world-profile, ribbon, filter and region-list answers. The rest were read from the page source after the fixes, and are not separately tested: which are monitored (lead paragraph and outlines), is Australia monitored (search, plain card), largest producers (world profile, alphabetically), what year (selector and legend), major US disruptions (filters), how complete US research (Research tab), why China is thinner (reporting environment in the ribbon), can I compare counts (no, stated on both pages), India's latest state (ribbon), which Saudi statuses are withheld (ribbon count, Research tab).

## 14. Corrections carried in this file

The checkpoint in §0 lists starting states. It is left as written.

## 15. Owner questions

Threshold questions: MW load loss under clause 5; clause 4 generation loss with no load shed; single-mine halts with capacity but no lost volume; no-load-shed grid declarations under clause 5; CER's interruption flag under clause 3; month-level refinery shortfall with a stated cause; a transmission feeder to a city gate, and any PHMSA "transmission" line, as a trunk (Columbia SM-116 is held on this); residents versus customers; supply-driven run cuts; hours-long terminal suspensions; a refinery fire during commissioning (HRRL); the 12 earlier owner rulings.

Publication questions: a citation address that names a city (RIPET, Maharashtra substation, both held); weapon type in theatre notes (32 notes); whether a descending sort of the national table is acceptable; a login-walled lede counted as opened; the Saudi release rule, still "proposed".

**Fuel-supply cause: not proposed.** A definition would need: a trigger of explicit attribution by an operator, ministry or wire; an effect of rotating outages or forced curtailment, not low stocks; exclusions for hydro, demand-only deficits, price and contract cases; whether fuel quality counts; whether imported-supply interruption counts; a rule for disputed attribution; a date and geography convention.

Known and unchanged: `pipeline_registry.json` carries an observed physical status on pipelines from one date in August 2026; `pipeline/recovery.py` `withheld_records` counts curated rows only and is therefore 0.

## 16. Not done

- The search queries in every lane marked `stopped_by: search_limit`.
- 37 US, 4 Canadian, 1 Chinese and 2 Indian records still say recovery not yet researched.
- Lazy loading of the source browser's data beyond the panels listed in §11.
- A screen reader was not run. Contrast was computed, not measured on a device.

## 17. Wave-2 readiness: CONDITIONAL

Not ready to add a country. Coverage semantics are fixed and the world layer works, but the search-limited lanes have not run, India and Saudi depth has improved only at the level of source findings, and owner-held threshold questions have grown.
