# United Arab Emirates — index readiness

Written 2026-11-11 by the UAE source-audit lane (iteration 19, Wave A). Companion to
[AE_SOURCE_AUDIT.md](AE_SOURCE_AUDIT.md), which carries the evidence and addresses for every source
named here. **Nothing here changes a published number, and no score is activated.** Incident
coverage is assessed from the nature of the sources, not from incident research, which is a
separate lane.

Readiness vocabulary:

- **READY** — denominator exists on one stated basis, dated, complete enough to score against.
- **EXPERIMENTAL** — usable with disclosed caveats; publish as a labelled sensitivity, not headline.
- **INCOMPLETE** — a credible path exists, but a required input is not yet acquired or reconciled.
- **UNSUITABLE** — should not be built, for data reasons, scope-boundary reasons, or both.
- **NOT APPLICABLE** — the sector does not exist in the country's energy system (a sourced zero,
  not a gap). Distinct from **UNKNOWN** (exists, unmeasured) and **NOT YET RESEARCHED**.

This document lists no facility with a capacity. Where a list exists, it says so and says where.

---

## Bottom line

**CONTEXT_ONLY** for every sector that exists; coal is NOT APPLICABLE.

No sector has an index-grade denominator. The operators that would publish one (ADNOC, DEWA, ENOC,
TAQA) and the federal statistics bodies refused ordinary access this session, so what exists is a
set of national totals from EIA and emirate or service-area totals from regulators and utilities.

A second limit is structural and would remain even with perfect data: **the country has few
facilities per class and seven small units.** A denominator by emirate would in several cases be
one facility's capacity under another name. Any future measure for this country should be
national, or should pool emirates, and that is an owner decision (`GLOBAL_METHODOLOGY.md` §8).

---

## 1. Refining — **INCOMPLETE**

| Item | Finding |
|---|---|
| Complete national inventory | A list exists: the EIA country brief (updated 2026-07-28) has a refinery table and states five operating refineries as of January 2026. Not read row by row |
| Capacity | National total 1,249 thousand b/d (EIA, January 2026) |
| Basis | Not stated: gross or net, stream day or calendar day. EIA's table source was not captured |
| Vintage | One vintage. No dated history found |
| Operator sources | ADNOC and ENOC pages returned HTTP 403; no operator table was read |
| Status and retirement | None |

A secondary compilation at one vintage is not a denominator. With five plants the series would
move in steps of a fifth of the base, and an emirate-level refining figure would identify single
plants. If this sector is ever measured it should be at national level only.

**Achievable incident coverage:** fires and attacks at refineries are reported by wires and
domestic press; the effect on throughput is seldom stated. Coverage ratio cannot be computed.

---

## 2. Electric generation — **INCOMPLETE**

| Item | Finding |
|---|---|
| Complete national inventory | None found. WRI GPPD has 30 rows from about 2016 with no nuclear and no status. GEM's power tracker has units, status and dates; not acquired, UAE rows not inspected |
| National capacity | 45.53 million kW in 2024 (EIA bulk series); about 48.3 GW in 2026 (federal portal, source not named on the page) |
| National generation | 169.03 billion kWh in 2024 (EIA bulk series): 71% natural gas, 23% nuclear, 5% renewables and other, 1% petroleum liquids |
| Basis | EIA: installed capacity and net generation, national. The portal's scope (grid, captive, industrial) is not stated |
| Sub-national figures | By authority, not by emirate: Abu Dhabi (Department of Energy technical reports, not opened), Dubai (DEWA booklet, blocked), Sharjah (none found), and the four northern emirates pooled (Etihad Water and Electricity statistical reports 2021–2025, not opened) |
| Status and retirement | None in any official aggregate |

**Path:** GEM power tracker, aggregated; reconciled against the EIA national total and the
authorities' totals. Two cautions. Four emirates share one authority, so official cross-checks
exist for four service areas, not seven emirates. And nuclear generation is carried only as one
national figure: a generation base by emirate would publish the nuclear site's capacity as an
emirate total, so nuclear cannot be placed below national level.

**Achievable incident coverage:** low. No authority page reached this session publishes outage
notices. Weather-driven outages reach the press when large; unit trips do not.

---

## 3. Transmission — **UNSUITABLE** (as an event-burden sector)

No inventory was found, and none should be built. The four authorities and the national grid
company do not publish line or substation lists on the pages reached. The Monitored-Area measure
is an event-burden figure normalised against a regional inventory; here there is neither an event
stream nor an inventory, and a substation-level picture of a grid that publishes none is outside
scope. National or authority-level network totals, if a statistical report states them, may
appear as dated context.

---

## 4. Oil logistics — **UNSUITABLE**

No consistent public capacity inventory for terminals, storage or crude pipelines was looked for,
because the work would centre on export routes, which the scope boundary and the iteration-19
brief exclude for this region. The ESDI's refining-base proxy also does not fit a crude exporter.
The sector stays uncovered: excluded and weights renormalised, never zero, with the page saying
"not modelled for the UAE: no suitable public inventory, and out of scope".

---

## 5. Gas — **INCOMPLETE**, split

### 5a. Gas processing — **INCOMPLETE**

ADNOC Gas publishes annual and integrated reports (2023, 2024, 2025) and quarterly data books.
They were located, not opened; whether they give a plant-by-plant capacity table on one basis is
**not yet researched**. Company totals would be a company basis, not a national one.

### 5b. LNG — applicable, **INCOMPLETE**

Unlike Saudi Arabia, the UAE exports LNG: EIA's bulk series gives dry natural gas exports of 286
Bcf in 2024, and the brief has an LNG terminal table (not read). It also imports gas (771 Bcf in
2024) and is a net importer. One vintage, a secondary compilation, and too few facilities for an
emirate-level figure.

### 5c. Gas pipelines — **UNSUITABLE**

No inventory sought; routing is out of scope. No UAE gas-pipeline layer, analytic or context.

### 5d. Gas storage — **NOT YET RESEARCHED**

---

## 6. Coal — **NOT APPLICABLE**

EIA reports coal production of 0 for the UAE (bulk series, 2022–2024) and no coal reserves
(country brief). Coal-fired generation is 0.0 and 0% in the brief's 2024 table. This is a sourced
zero for mining and for coal power, so the sector is NOT APPLICABLE, not UNKNOWN.

Caveat, stated so the zero is not over-read: coal **consumption** is not zero. EIA reports about
3,672 thousand short tons in 2024, all imported, used mainly in industrial processes. That is fuel
use by industry, not an energy-infrastructure sector this project monitors.

---

## 7. Upstream — not a sector in the current taxonomy

Petroleum liquids were 78% of UAE primary energy production in 2024 and natural gas 19% (EIA). The
taxonomy has no upstream sector, so a UAE index would omit most of the country's energy production
by construction. A facility-level upstream inventory is not recommended under the scope boundary.
Upstream appears only as national context: EIA annual production and JODI monthly flows, labelled
as context.

---

## Russia-model assumptions that fail for the UAE

| Russia assumption | UAE reality |
|---|---|
| A structured open-source strike table supplies events and a coverage benchmark | None identified; coverage must read "unknown" |
| Regional facts can be placed into first-level units | Electricity statistics are by four authorities; four emirates are pooled |
| A first-level unit holds many facilities of a class | Few facilities per class; emirate plus class can identify one facility |
| WRI GPPD is an acceptable, if stale, generation base | 2016 snapshot with no nuclear and little solar |
| Pipelines reconstructed from OSM route relations | Out of scope for this region; not queried |
| `heating_season_months` marks the stress season | Demand peaks in summer (federal portal electricity page); the heating flag is wrong |
| Coal is a temporary gap | Not applicable |
| Sector taxonomy covers the main energy activity | Upstream is absent from the taxonomy |
| Recovery evidence accumulates from wire reports | Facility status for 2026 kinetic records is not collected while the campaign's state is unresolved |
| Attribution confidence can be derived from publisher count | Domestic outlets repeat one official statement in two languages |

---

## Transparency limits, stated once

- No UAE body reached this session publishes event-level outage notices.
- The state news agency, the Abu Dhabi and Dubai exchanges, the ministry, the federal statistics
  centre, ADNOC, DEWA, ENOC and TAQA could not be read by an ordinary request.
- Two of three Arabic dailies could not be opened; Arabic coverage is thinner than English for
  access reasons, not because less was published.
- Low reported incident counts for the UAE are a property of this environment and must be
  presented as "coverage unknown", never as low disruption.
