# Iraq — index readiness

Written 2026-11-11 by the Iraq source-audit lane (iteration 19, Wave A). Companion to
[IQ_SOURCE_AUDIT.md](IQ_SOURCE_AUDIT.md), which carries the evidence and addresses for every source
named here. **Nothing here changes a published number, and no score is activated.** Incident
coverage is assessed from the nature of the sources, not from incident research, which is a
separate lane.

Readiness vocabulary:

- **READY** — a denominator exists on one stated basis, dated, complete enough to score against.
- **EXPERIMENTAL** — usable with disclosed caveats; a labelled sensitivity, not a headline.
- **INCOMPLETE** — a credible path exists, but a required input is not yet acquired or reconciled.
- **UNSUITABLE** — should not be built, for data reasons, scope-boundary reasons, or both.
- **NOT_APPLICABLE** — the sector does not exist in the country's energy system (a sourced zero).
  Distinct from **UNKNOWN** (exists, unmeasured) and **NOT YET RESEARCHED**.

This document lists no facility and no facility capacity. Where a list exists, it says so and
where.

---

## Bottom line

**CONTEXT_ONLY** today, for every sector that exists. No sector has a denominator that was read on
one stated basis in this session. Iraq also carries a structural difficulty the other systems do
not: **two jurisdictions report separately** (federal ministries and the Kurdistan Region's), so a
"national" inventory has to be assembled from two sets of sources that do not share a basis.

| Sector | Verdict |
|---|---|
| Refining | INCOMPLETE |
| Electric generation | INCOMPLETE |
| Transmission | UNSUITABLE |
| Oil logistics | UNSUITABLE |
| Gas | INCOMPLETE |
| Coal | NOT_APPLICABLE |
| Upstream (note) | national context only |

---

## 1. Refining — **INCOMPLETE**

| Item | Finding |
|---|---|
| Complete national inventory | **not found.** Federal refining is run by three state companies (north, midland, south); the Kurdistan Region has separate, largely private refining. No single list covering both on one basis was read |
| Capacity | a national total only: EIA states "total operating refining capacity is approximately 1.3 million b/d" (brief updated July 2025) |
| Basis | **operating**, approximate; EIA credits Argus Media and *Middle East Economic Survey*, not an Iraqi official table. Nameplate is not stated |
| Vintage | 2025, single |
| Where a list may exist | OPEC's Annual Statistical Bulletin and the Ministry of Oil (both refused access this session); the state refining companies' own sites (one of three reachable) |

A per-refinery table was neither found nor sought. Even if one is acquired later, it is rebuilt at
governorate level only and is not reproduced in this repository while nothing is scored.

**Achievable incident coverage:** partial. Fires and shutdowns at state refineries are reported by
the ministry through agencies; small private plants in the Kurdistan Region are seldom reported.
**Restoration evidence:** sparse, and not collected at all for kinetic or sabotage events.

## 2. Electric generation — **INCOMPLETE**

| Item | Finding |
|---|---|
| Complete national inventory | **not found.** WRI GPPD has 28 Iraqi rows, newest 2016, no status field. GEM's Global Integrated Power Tracker is unit-level with status and dates, **not yet acquired** |
| Capacity | installed capacity is **not stated** in EIA's brief. EIA gives an estimated **available peak supply of about 25 GW for Federal Iraq in 2024**, which is an availability figure, not a capacity |
| Generation | Federal Iraq an estimated 150 TWh in 2023 (EIA); the Kurdistan Region "at most" 17 TWh in 2024, reported separately |
| Basis | federal grid and Kurdistan Region grid are separate reporting bases; neither alone is the country |
| Vintage | 2023-2024 |

**Path:** GEM tracker, point-in-polygon to governorate, a dated census by start and retirement
year, reconciled against a federal and a regional total. Until then INCOMPLETE. Nameplate would in
any case overstate what the system can deliver: EIA's own figures put available supply far below
peak demand, for reasons that include fuel supply. A capacity denominator would measure installed
plant, not service.

**Achievable incident coverage:** low to partial. System-wide failures are announced. Plant-level
outages rarely are. Scheduled supply hours are background and never an event (audit §4).

## 3. Transmission — **UNSUITABLE**

No regional inventory was read, and none is sought: mapping a grid at line or substation level is
outside the scope boundary. The Monitored-Area transmission measure is an event-burden measure with
a modelled saturation constant; there is neither a regional event stream nor a regional inventory
to normalise against here. Recommend **no Iraqi transmission sector and no grid geometry**.
System-wide failures enter the record as `system_wide` events at country or governorate precision.

## 4. Oil logistics — **UNSUITABLE**

No consistent public capacity inventory for terminals, storage or crude pipelines was read. The
work needed to build one would centre on export routing, which the scope boundary and this
iteration's brief exclude outright. Recommend the sector stay **uncovered** (excluded, weights
renormalised if a composite ever exists, never zero), with the page saying "not modelled for Iraq:
no suitable public inventory, and out of scope". National export totals may appear as dated
context.

## 5. Gas — **INCOMPLETE**

| Item | Finding |
|---|---|
| Complete national inventory | **not found** for processing plants in either jurisdiction |
| National figures | production 372 Bcf in 2023 (EIA; the page as read does not say dry or marketed); 625 Bcf flared in 2023 (World Bank, via EIA); 682 Bcf of dry gas consumed; 310 Bcf imported |
| Basis / vintage | national, 2023 |
| LNG | no LNG terminal appears in any source read. **Not yet researched** as a sourced zero |
| Gas storage | **not yet researched** |

A processing denominator cannot be assembled from what was read. Gas pipelines are **UNSUITABLE**
for the same reasons as oil logistics. The sector as a whole is recorded INCOMPLETE.

**Achievable incident coverage:** events at gas facilities are reported when they cut power
generation, because the ministries then say so. The power effect is the part most often quantified.

## 6. Coal — **NOT_APPLICABLE**

EIA's Table 1 for Iraq (2023) shows coal as "--", and the table note says the dash "signifies not
applicable"; nuclear is shown the same way. WRI's 28 Iraqi rows contain no coal plant. This is a
**sourced not-applicable**, not unknown. Caveat: it rests on one source's table convention; minor
industrial coal use, if any, would not create an energy-infrastructure sector to monitor.

## 7. Upstream — a note, not a sector

Crude oil and other petroleum liquids were **96.0% of Iraq's primary energy production in 2023**
(EIA). The taxonomy has no upstream sector, so any Iraqi index would omit most of the country's
energy production by construction. National series exist (EIA annual; SOMO monthly export totals;
OPEC and JODI, not read this session). A field-level inventory is **not recommended** under the
scope boundary. Upstream stays national context; a field event enters the record under clause 7
only when a source states a material volume shut in and why.

---

## Assumptions of the Monitored-Area model that fail for Iraq

| Assumption | Iraq |
|---|---|
| One reporting authority per system | two: federal and Kurdistan Region ministries, on separate bases |
| A structured open compilation supplies events and a coverage benchmark | none identified; **coverage must read "unknown"** |
| A generation shortfall is an exceptional event | shortage is the normal state; scheduled supply hours are background |
| Capacity is a fair proxy for service | available supply is well below demand; installed plant overstates service |
| Outage size is reported in customers | reported in megawatts and governorates; never converted |
| Official sources can be read by a scheduled job | nearly all refuse automated access |
| Sector taxonomy covers the main energy activity | upstream (96% of primary production) is absent |
| First-level units are settled | Halabja is a governorate in law but not in Natural Earth; several areas are disputed internally |

## Transparency limits, stated once

- No Iraqi official site except one state refining company and SOMO could be read by a script.
- Every national figure used comes from EIA or SOMO; OPEC, IEA and Energy Institute refused access.
- Low reported incident counts are a property of this environment and must be presented as
  "coverage unknown", never as low disruption.
