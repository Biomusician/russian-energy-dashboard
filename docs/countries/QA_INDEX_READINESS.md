# Qatar — index readiness

Written 2026-11-11 by the Qatar source-audit lane (iteration 19, Wave A). Companion to
[QA_SOURCE_AUDIT.md](QA_SOURCE_AUDIT.md), which carries the evidence and addresses for every source
named here. **Nothing here changes a published number, and no score is activated.** Incident
coverage is assessed from the nature of the sources, not from incident research, which is a
separate lane.

Readiness vocabulary, as in `SA_INDEX_READINESS.md`:

- **READY** — denominator exists on one stated basis, dated, complete enough to score against.
- **EXPERIMENTAL** — usable with disclosed caveats; a labelled sensitivity, not a headline.
- **INCOMPLETE** — a credible path exists, but a required input is not yet acquired or reconciled.
- **UNSUITABLE** — should not be built, for data reasons, scope-boundary reasons, or both.
- **NOT APPLICABLE** — the sector does not exist in the country's energy system (a sourced zero,
  not a gap). Distinct from **UNKNOWN** (exists, unmeasured) and **NOT YET RESEARCHED**.

This document names no facility and gives no facility capacity. Where a list exists it says so and
says where.

---

## Bottom line

**CONTEXT_ONLY** today, and likely to stay so.

Qatar is the reverse of the usual problem. The denominators are good: the utility publishes a
complete, dated list of contracted generating capacity, and the operator publishes national oil,
gas and LNG totals, both under CC BY. What blocks a score is not missing data. It is that **the
system has so few facilities that a sector share is a facility's status under another name**, and
that there is no event stream to put over the denominator.

| Sector | Complete national inventory | Capacity available | Basis and vintage | Verdict |
|---|---|---|---|---|
| refining | yes (EIA Table 4) | yes, national total | nameplate crude and condensate, 2025; secondary compilation | **UNSUITABLE** |
| electric_generation | yes (KAHRAMAA, annual) | yes | contracted capacity, annual 2019–2025 | **EXPERIMENTAL** (denominator READY) |
| transmission | national aggregates only | lengths and counts | annual | **UNSUITABLE** |
| oil_logistics | none sought | — | — | **UNSUITABLE** |
| gas | LNG: yes; processing: not researched | LNG national nameplate | end-2024 (EIA); operator statement undated | **UNSUITABLE** to score; LNG is a context dimension |
| coal | — | — | EIA marks coal not applicable | **NOT_APPLICABLE** |

---

## 1. Refining — **UNSUITABLE** (context only)

| Item | Finding |
|---|---|
| Inventory | EIA's Country Analysis Brief (updated 20 October 2025), Table 4, lists the country's crude and condensate refineries and, separately, its gas-to-liquids plants. EIA's text counts two oil refineries |
| Total capacity | **443 thousand b/d** crude and condensate processing, 2025 (Table 4 total). Gas-to-liquids is a separate total and is not refining |
| Basis | nameplate; stream-day or calendar-day not stated; a secondary compilation. The operator's own table was not read (report PDFs over the fetch limit) |
| Throughput | QatarEnergy publishes national refinery throughput annually, 2020–2025, CC BY |
| Vintage | one EIA vintage (2025); annual throughput to 2025 |
| Missing | operator's own capacity statement; whether condensate splitting and crude refining should share one base |

**Why unsuitable.** With two plants, a refining share takes only a handful of values, and each one
says which plant is affected. That is facility status, which this project does not publish for a
system under a recorded campaign and should not approximate through a ratio at any time. Refining
is also a small part of this energy system: most liquids are exported unrefined or as condensate.
The national capacity total and annual throughput belong in the profile as context.

---

## 2. Electric generation — **EXPERIMENTAL** (denominator READY, not scored)

| Item | Finding |
|---|---|
| Inventory | KAHRAMAA's Annual Statistics Report, table ET1 "Contracted capacities by IWPPs", and the same table as a CC BY dataset on the Qatar Open Data Portal (annual). **A list exists there; it is not copied here** |
| Total capacity | **10,573 MW** contracted from independent power and water producers, 2023 (ET1 total). The report adds that a 350 MW first phase of utility solar was commissioned in 2023. EIA gives 11.4 GW for 2023; the National Planning Council's series gives 10,574 MW installed for 2022 |
| Basis | contracted capacity bought by the single buyer. Whether industrial captive generation is included is **not yet researched** |
| Unit | MW |
| Vintage | annual, 2019–2025 on the portal; report editions to 2023 located |
| Status / retirement | none explicit; changes appear as differences between annual editions |
| Cross-check | annual generation (59,641 GWh in 2025) and peak load (10,220 MW in 2024) from the same publisher |

**Why not READY as a sector.** The denominator is the best of any country system so far: one
publisher, one basis, annual, open licence. Three things stop it short.

1. **No event stream.** KAHRAMAA publishes no outage notices and no reliability statistics (audit
   §2.6–2.8). The inclusion rule's absolute thresholds (about 500 MW; about 100,000 customers) are
   large against a system of about 10.6 GW and about 520,000 customers: a plant-level event here is
   several percent of the country.
2. **Few plants.** The list is short. A national share is not identifying by itself, but it must
   never be broken down below the country.
3. **Geography.** Under the rulings in the audit §1, most plant events resolve to country level, so
   a regional generation measure has nothing to stand on.

**Path, if the owner ever wants it:** national-only share of contracted capacity affected, from
ET1 for both numerator and denominator, labelled experimental, published only for non-conflict
events. Not recommended while the campaign is recorded as active or uncertain.

**Restoration evidence:** none found. Expect statements that supply "was restored", without
durations.

---

## 3. Transmission — **UNSUITABLE** (context only)

| Item | Finding |
|---|---|
| Inventory | national aggregates only: KAHRAMAA tables ET11–ET13 and portal datasets give substation counts and cable and overhead-line lengths by voltage class |
| Basis / vintage | annual |

The theatre's transmission sector is an event-burden measure with a modelled saturation constant.
Qatar has neither a regional event stream nor a regional inventory to normalise against, and its
grid is small enough that any substation- or line-level layer would be a map of the grid. **No
Qatar transmission sector.** A national circuit-length total may appear as dated context; the
substation table and zone-level consumption are never read (audit §4).

---

## 4. Oil logistics — **UNSUITABLE**

No inventory of terminals, storage or pipelines was sought, and none should be built: the work
would centre on export routing, which the scope boundary excludes, and the number of facilities is
small enough to be identifying. The sector stays **uncovered** (excluded and weights renormalised,
never zero). National crude export volume (QatarEnergy, annual, CC BY) is context.

---

## 5. Gas

### 5a. LNG — **context dimension; UNSUITABLE to score**

- **National capacity is published.** The operator states a company-total LNG production capacity
  of 77 million tonnes a year on its website. EIA gives a total nameplate export capacity of
  3.7 Tcf/y at end-2024. These are nameplate figures and say nothing about operating state.
- **National annual totals are published.** QatarEnergy's open dataset gives LNG exported per year,
  2020–2025 (between 77.8 and 79.3 million tonnes).
- **Train-by-train capacity exists publicly** (operator site and reports; EIA) and **is never
  recorded**, in this document or any output file.
- **Why not scored.** Liquefaction is concentrated in very few places. Any share of capacity
  affected would be readable as the status of particular trains, and during the recorded campaign
  it would be exactly the feed `CURRENT_EVENT_PUBLICATION_POLICY.md` forbids. No measure of any
  buyer's or country's dependence on these volumes is ever computed or shown.
- **What may be shown:** national nameplate capacity (dated), annual national exports, each with
  its source and year, labelled as context.

### 5b. Gas processing — **NOT YET RESEARCHED**

No national inventory of processing plants was sought. The operator's annual gross gas production
(BCFD, 2020–2025) is published and is context. Same concentration concern as 5a.

### 5c. Gas pipelines — **UNSUITABLE**

No inventory sought; scope boundary (routes, interconnector status). The national pipeline-export
volume (QatarEnergy, annual) may be shown as a national total, without route or destination.

### 5d. Gas storage — **NOT YET RESEARCHED**

Not investigated.

---

## 6. Coal — **NOT APPLICABLE**

EIA's Table 1 for Qatar marks coal production and consumption "--", which its note defines as not
applicable, and shows no coal in electricity generation (96.4% natural gas in 2023). WRI's 12
Qatari plants are all gas. A **sourced** not-applicable, not an unknown.

---

## 7. Upstream — a note, not a sector

Natural gas was 67.5% and petroleum liquids 32.5% of primary energy production in 2023 (EIA). The
taxonomy has no upstream sector, so most of this country's energy production is outside any sector
by construction. National totals are published annually by the operator (crude production; gross
gas production). A field- or platform-level inventory is **not recommended**: offshore installations
fall in no municipality and would be facility rows. Upstream stays national context; a `clause 7`
event (production shut in at a reported, material volume) is recorded at country level.

---

## Russia-model assumptions that fail for Qatar

| Russia assumption | Qatar reality |
|---|---|
| Events are placed in first-level regions | Seven drawn municipalities, several holding one large complex each: region is a facility identifier. Kinetic events are country level |
| A structured open-source strike table supplies events and a coverage benchmark | None identified. **Coverage ratio must read "unknown"** |
| Sector share of capacity affected is a safe aggregate | With this few facilities per sector, a share is facility status |
| Sector taxonomy covers the main energy activity | LNG and upstream gas, the bulk of the system, have no scored sector |
| `heating_season_months` marks the stress season | Demand peaks in summer: KAHRAMAA's yearly maximum load falls between late July and early September in every year 2019–2024 |
| Recovery evidence accumulates from wire reports | For 2026 kinetic records it is withheld by policy; for others, statements rarely give durations |
| Attribution confidence can be derived from publisher count | Five dailies come from three houses and repeat the state agency; in conflict, parties' claims are repeated across outlets |
| Coal and gas "uncovered" is a temporary gap | Coal is not applicable; gas is unsuitable by concentration and scope |

---

## Transparency limits, stated once

- No public outage register and no published reliability indicator for electricity or water.
- The operator's and the LNG company's report PDFs were not read (over the fetch limit, or HTTP
  403); their company totals are **not yet researched**, not absent.
- The utility's `www` host and the former statistics authority's host fail the TLS handshake from
  this machine; the utility's news and publications listings render empty.
- Low reported incident counts for Qatar are a property of this environment and must be presented
  as "coverage unknown", never as low disruption.
