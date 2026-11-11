# Bahrain — index readiness

Written 2026-11-11 by the Bahrain source-audit lane (iteration 19, Wave A). Companion to
[BH_SOURCE_AUDIT.md](BH_SOURCE_AUDIT.md), which carries the evidence and addresses for every source
named here. **Nothing here changes a published number, and no score is activated.** Incident
coverage is assessed from the nature of the sources, not from incident research, which is Wave B.

Readiness vocabulary, as in `SA_INDEX_READINESS.md`:

- **READY** — denominator exists on one stated basis, dated, complete enough to score against.
- **EXPERIMENTAL** — usable with disclosed caveats; a labelled sensitivity, not a headline.
- **INCOMPLETE** — a credible path exists, but a required input is not yet acquired or reconciled.
- **UNSUITABLE** — should not be built, for data reasons, scope-boundary reasons, or both.
- **NOT_APPLICABLE** — the sector does not exist in the country's energy system (a sourced zero).
  Distinct from **unknown** (exists, unmeasured) and **not yet researched**.

This document deliberately lists no facility with a capacity. Where a list exists, it says so and
says where.

---

## Bottom line

**CONTEXT_ONLY** today, and for a structural reason that more data would not remove.

Bahrain is a microstate with very few facilities in each class. A sector exposure share is a
facility's share; a regional series is a facility's status under another name. That is the feed the
scope boundary rules out, so the two hydrocarbon sectors are **UNSUITABLE** for scoring however good
their denominators are. Electricity has more units but the same problem at governorate level, and
its capacity inventory was not read. Coal is a sourced zero.

What Bahrain does support well is **national context**: official annual series for crude, gas,
refining and public electricity supply, under an open licence (audit §2.1).

| Sector | Verdict |
|---|---|
| Refining | **UNSUITABLE** |
| Electric generation | **INCOMPLETE** |
| Transmission | **UNSUITABLE** |
| Oil logistics | **UNSUITABLE** |
| Gas | **UNSUITABLE** (processing); LNG **not yet researched** |
| Coal | **NOT_APPLICABLE** |
| Upstream (note) | national context only |

---

## 1. Refining — **UNSUITABLE**

| Item | Finding |
|---|---|
| Complete national inventory | Yes, trivially: the official refining datasets describe one refinery, operated by Bapco Refining. Whether any other crude-processing plant exists was **not researched**; none appears in any source read |
| Capacity available | Published by the operator and quoted by EIA (2016). **Not recorded in this repository** |
| Basis and vintage | Not established this session. The operator's annual reports for 2021-2023 are listed on `bapco.net` but their files were not reachable. A modernisation programme was inaugurated in December 2024 (operator press-release title), so any pre-2025 capacity figure is out of date |
| Activity series | Official annual throughput and output, 2017-2025, `data.gov.bh` (Ministry of Oil and Environment) |

**Why UNSUITABLE rather than EXPERIMENTAL.** With a single plant the "share of national refining
capacity affected" can only ever be 0% or about 100%, and a decaying sector score would be a public
estimate of that one plant's condition over time. No reconciliation of capacity bases repairs that.
The national throughput series stays as dated context, ending at 2025 (audit §5).

**Achievable incident coverage:** major incidents are likely to surface through official statements
and wire coverage; technical unit outages are not. Coverage cannot be computed: there is no register.

**Restoration evidence:** not assessed. Under campaign policy it would not be collected at all.

---

## 2. Electric generation — **INCOMPLETE**

| Item | Finding |
|---|---|
| Complete national inventory | Partly. EWA's open dataset lists generation for 8 station rows a year, 2008-2025 (`data.gov.bh`); a station list with capacities is said to be in EWA's annual statistics books (latest edition found: 2022), which were **not read** (file over the fetch limit). The per-station rows are not read by this project (audit §5) |
| Completeness | The EWA rows are public supply only. IRENA's national generation for 2023 (37,523 GWh) is about twice the EWA total for the same year (19,285), so roughly half of national generation is outside the EWA list. Its composition is not stated on either page |
| Capacity available | National: 9,954 MW installed in 2024 (IRENA: 9,885 non-renewable, 69 renewable). Scope of the IRENA figure against EWA's own system is not reconciled |
| Basis and vintage | IRENA, year-end 2024, profile dated 22 September 2025. EWA books: 2022 at the latest, unread |
| Unit defect | The EWA generation dataset is titled MWh but its magnitudes are GWh (audit §2.1) |

**Path, if ever wanted:** a person opens the EWA statistics book for national totals only; the
public-supply and national scopes are reconciled; a national (not governorate) generation context
row is published. A governorate-level generation measure is **not recommended**: with this few
stations a governorate share identifies a station.

**Achievable incident coverage:** low. EWA's listing carries no outage statements on the pages
sampled and begins in 2024. Clause 4 (about 500 MW forced offline) and clause 5 (about 100,000
customers) are absolute thresholds written for far larger systems.

---

## 3. Transmission — **UNSUITABLE**

No inventory was read, and none should be built. EWA's home page has a network-statistics block
that does not render without scripts; the statistics books may hold national circuit lengths. A
substation-level or line-level picture of a grid this small is exactly the material the brief
excludes, and the task rules out substation-level material in the event lane as well. National
aggregates, if a person reads them, may appear as dated context.

---

## 4. Oil logistics — **UNSUITABLE**

No public capacity inventory of terminals, storage or pipelines was read, and assembling one would
centre on import and export routing, which the scope boundary excludes. The official crude-import
dataset exists and is deliberately not carried (audit §5). The sector stays uncovered: excluded,
never zero.

---

## 5. Gas — **UNSUITABLE** for scoring; national series as context

- **Production:** official annual national series, 2017-2025, for associated and non-associated gas
  (`data.gov.bh`). National, complete, open-licensed. Context only.
- **Processing:** the group site lists Bapco Gas and Bapco Gas Expansion. A capacity figure was not
  read. A list exists only as the group's own description, which was blocked. The single-operator
  reasoning of §1 applies in full.
- **Pipelines:** no inventory; not to be built.
- **LNG:** a company named Bahrain LNG is listed among the group's operating companies. Whether an
  import terminal is in service, and on what basis its capacity is stated, is **not yet
  researched**. This is not a NOT_APPLICABLE: the sector appears to exist.
- **Storage:** **not yet researched**.

---

## 6. Coal — **NOT_APPLICABLE**

IRENA's energy profile (22 September 2025) shows "Coal + others" at **0%** of total energy supply in
2022 (gas 89%, oil 11%) and at 0% of power-sector CO2 emissions, which it shows as 100% gas. The
official portal's energy and oil-and-gas themes hold no coal dataset. A sourced zero, so NOT
APPLICABLE rather than unknown. Caveat: IRENA rounds to whole percentages, so minor industrial use,
if any, is below its precision; that does not create a sector to monitor.

---

## 7. Upstream — a note, not a sector

The taxonomy has no upstream sector. The official series give Bahrain-field crude production (13,505
thousand barrels in 2025) and gas production by type. The crude series is titled for the Bahrain
field only; any other production attributable to Bahrain is not in it, so it must not be labelled
"national crude production" without that qualification. Upstream stays national context, by year.
A field-level or facility-level upstream inventory is not recommended.

---

## Russia-model assumptions that fail for Bahrain

| Russia assumption | Bahrain reality |
|---|---|
| A region holds many facilities, so a regional share is an aggregate | A governorate, and for two sectors the country, holds one |
| Admin-1 placement is safely coarse | Admin-1 plus asset class can identify a facility; kinetic and security events default to country level |
| Natural Earth admin-1 matches current divisions | Natural Earth draws five governorates; four exist since 2014, with different shapes |
| A structured strike table gives events and a coverage benchmark | No register of any kind; coverage reads "unknown" |
| Heating season marks the stress months | Demand is cooling-driven (not sourced this session; the heating flag must simply not be applied) |
| Absolute thresholds separate large from small events | 500 MW and 100,000 customers are large fractions of this system |
| Recovery evidence accumulates from wire reports | Under campaign policy it is not collected; otherwise it is rarely published |

---

## Transparency limits, stated once

- The group site (after one request), the state news agency, two of three Arabic dailies, Reuters
  and S&P Global refused automated access; none was worked around.
- No operator annual report and no EWA statistics book was read. Every capacity statement above is
  either IRENA's national figure or marked as not read.
- A sparse Bahrain record is a property of this environment and must be presented as "coverage
  unknown", never as low disruption.
