# India (IN) — index readiness

**Status: candidate assessment. Nothing here changes a published number, and no India index
exists.** Compiled 2026-10-30. Source details, access results and the provenance of every figure
are in [IN_SOURCE_AUDIT.md](IN_SOURCE_AUDIT.md). Framing and the readiness states are in
[../GLOBAL_METHODOLOGY.md](../GLOBAL_METHODOLOGY.md) §4 and §7.

Sector classification used here (same as the other country lanes):

- **READY:** a complete, single-basis, dated denominator exists and is acquirable.
- **EXPERIMENTAL:** a credible denominator exists but needs a basis decision, acquisition, a
  crosswalk or a completeness check before any value can be published.
- **INCOMPLETE:** a partial denominator exists, with a known gap.
- **UNSUITABLE:** no defensible open denominator, or the Russia construct does not transfer.

All years are Indian fiscal years (April–March) unless marked "calendar".

## Bottom line

**Country recommendation: CONTEXT_ONLY today.** Do **not** publish an India composite.

India is the opposite of China. Its **denominators are the best in the non-US set**: PPAC
publishes every refinery, PSU and private, on one nameplate table with state, and CEA/NPP publish a
dated, unit-level conventional fleet with daily outage observations. What does not transfer is the
**event model**. Russia's index is a strike campaign scored against a decay calibrated to strike
damage. India's disruption is weather, technical failure, fuel shortfall and grid disturbance, and
India *reports routine outages at census density*. Fed into the Russia model unchanged, the
generation sector would measure the fleet's ordinary forced-outage rate, and transmission would sit
at the saturation ceiling permanently.

Two sectors are one step from **EXPERIMENTAL**: **refining** and **electric generation (coal and
conventional)**. Both need methodology decisions more than data.

**Minimum work to move India from CONTEXT_ONLY to EXPERIMENTAL (refining and generation only):**

1. **Decide HRRL's status** and publish the refining base on one basis: 258.1 MMTPA (Ready
   Reckoner, "22 operational") **or** 267.1 MMTPA (PPAC capacity page, HRRL included), with the
   other disclosed. Curate the 24 PPAC rows into `data/curated/` with the PPAC URL and file date.
2. **Add cause classes** for weather/natural hazard and fuel-supply shortfall, and an explicit
   **exclusion** for economic reserve shutdown ("RSD/low schedule"). These are taxonomy changes,
   so they are owner decisions.
3. **Write an inclusion threshold** for Indian generation events (for example: unplanned, forced,
   at or above a stated MW and duration, or reported by an independent publisher). Without it the
   NPP outage reports turn the sector into an availability statistic.
4. **Build the generation denominator by physical location** from NPP Sub-report 2 station/unit
   rows (conventional) plus GEM GCPT start/retired years for a census-at-date, and **add back**
   CEA's temporarily removed long-outage units.
5. Adopt **GLOBAL_METHODOLOGY model (iv)** (step function with a confirmation window) instead of
   modelled decay, with W sized from NPP re-commissioning data and PPAC monthly processing.
6. Ask the PPAC/CEA web teams for reproduction permission (GIGW policy), or locate GODL mirrors on
   data.gov.in, before redistributing any raw table.

Reaching **INDEX_READY** additionally needs a measured incident coverage ratio from the incident
lane, Grid-India access for transmission, and a decision on what India's exposure index is *for*
when there is no campaign to track.

---

## Refining — **EXPERIMENTAL** (denominator near READY) → sector bottom line **CONTEXT_ONLY** today

**Denominator.**

| Property | Finding |
|---|---|
| Inventory | 24 PPAC rows: 22 producing refineries + CPCL Cauvery Basin (0, under augmentation) + HRRL Pachpadra (9.0, no processing in FY 2025-26) |
| Total | **258.1 MMTPA** (Ready Reckoner, nameplate, April 2026) vs **267.116** (PPAC capacity page, 1.04.2026). MoPNG's page says 248.866 and is stale |
| Basis | Nameplate MMTPA (crude), self-reported by oil companies; single table, single unit |
| PSU vs private | **Both on the same basis in the same table.** Private: RIL Jamnagar DTA 33.0 + SEZ 35.2, Nayara Vadinar 20.0 = 88.2 MMTPA, about 34% of 258.1 (Ready Reckoner says 34.3%). JV HMEL Bathinda 11.3. PPAC groups by parent company, not ownership class (HMEL under HPCL, MRPL under ONGC), so ownership class must be curated |
| Vintage | 1 April 2026; annual |
| Status | No status field. "0" for an augmentation; HRRL carried at full capacity while its own publisher describes it both as commissioning and as commercially operating |
| Retirement | No field. History of throughput per plant since 2020-21 (Ready Reckoner Table 4.1) |
| Missing values | None in the April 2026 table |
| Geography | State per refinery; RIL's two Jamnagar entries are one site |

This is the single-basis registry Russia does not have. The only open item is HRRL, which moves
the base by 3.5%. **Recommended:** use 258.1 (operational basis, matching the publisher's narrative
count and the processing table), and record HRRL in inventory with `status: commissioning` and the
contradiction cited. Revisit when HRRL appears in monthly processing.

**Achievable incident coverage.** Refinery fires, unplanned shutdowns and cyclone/flood-related
stoppages are reported by Indian business press and stock-exchange material-event disclosures by
listed operators (disclosure rules not verified in this audit). There is no strike campaign and no regulator incident
register was found. Coverage must be measured by the incident lane; events will be **rare and
short** relative to Russia's.

**Restoration evidence.** Strong at monthly resolution: PPAC refinery-wise **monthly crude
processed** shows when a plant's runs return. It cannot see outages shorter than a few weeks and
does not say why runs fell (turnaround vs unplanned). Use it as observed recovery evidence, never as
a loss figure inside an exposure score.

**Russia assumptions that fail.**

- *150-day modelled refinery horizon.* Calibrated to strike damage to distillation units. Indian
  refinery outages are mostly short technical or weather events; a 150-day tail would dominate the
  sector with modelled, not observed, impairment (`model_dominated`).
- *Conflict-derived decay.* No decay should be modelled; use the step-with-window model and PPAC
  monthly runs to close events.
- *Planned turnarounds.* `maintenance` carries weight 0.15 today. In India, scheduled turnarounds
  will be a large share of observable throughput dips; counting them at any weight changes what the
  sector measures. Recommend excluding scheduled maintenance from the Indian score and listing it.

---

## Electric generation — **EXPERIMENTAL** (national) / **INCOMPLETE** (state) → **CONTEXT_ONLY** today

**Denominator.**

| Property | Finding |
|---|---|
| Inventory | CEA monthly installed capacity (utilities): **558,896 MW on 30.09.2026**; NPP Sub-report 2 lists every monitored conventional station and unit daily, grouped by physical state |
| Basis | MW nameplate; utilities only (captive excluded); conventional by CEA, RE by MNRE |
| Coal share | Coal 225,068 MW = **40.27%**; lignite 1.14%; gas 3.43%; nuclear 1.57%; hydro incl. PSP 9.32%; solar 30.61%; wind 10.59% |
| Vintage | Monthly; unit commissioning and retirement are announced in the monthly report |
| Status | **Long-outage units are removed from installed capacity** (2,825 MW coal, 4,400.84 MW gas, 100 MW nuclear since 30.04.2025; 370 MW coal/lignite, 978.4 MW gas, 300.861 MW diesel since 31.08.2026) and added back on return |
| Retirement | Monthly "capacity retired" line in CEA; unit-level start/retired years via GEM GCPT (coal) |
| Missing values | RE at unit level is not in NPP; RE state split is "provisional" |
| Geography | **CEA state tables are entitlement-based** ("including allocated shares in joint & central sector utilities", plus Central-Unallocated, NLC, DVC rows). NPP Sub-report 2 is location-based |

The national denominator is good and dated. It is not READY at state level, because the obvious
state table measures who is *entitled* to power, not where plants are. A physical regional
denominator must be built from NPP Sub-report 2 (conventional) plus MNRE or GEM GIPT (renewables).
The CEA removal rule must be reversed in the denominator, or a long outage lowers exposure.

WRI GPPD is rejected for India: 316,089 MW across 1,589 plants (57% of today's CEA total), capacity
vintage 2019.

**Achievable incident coverage.** Paradoxically too high. NPP Sub-reports 10, 11 and 15 list every
day's forced and planned outages per unit, with reasons. On 28-10-2026 the first of three pages of the ≥500 MW
report alone listed eighteen units; several were "RSD/low schedule" (economic reserve shutdown). Public news
coverage of generation disruption is far sparser and skews to large events (coal shortages,
heat-wave peaks, cyclone damage). The index needs a written inclusion rule deciding which of these
is a "disruption".

**Restoration evidence.** **Observed, daily, unit-level**: outage start time, expected return,
Sub-report 14 re-commissioning, Sub-report 12/13 long outages. This is the strongest restoration
evidence in the five-country set outside the US.

**Russia assumptions that fail.**

- *Decay.* Thermal fallback horizon 200 days and nuclear/hydro 400 days are irrelevant when the
  return date is observed. Use observed step functions.
- *Exposure framing.* With census-density outage data, exposure (capacity at disrupted facilities)
  converges on a **forced-outage rate**, a different construct. GLOBAL_METHODOLOGY §4.1 already
  recommends building any capacity-loss observation as a separate, separately labelled measure; the
  Indian data makes that a real option rather than a hypothetical.
- *Cause weights.* `technical` at 0.8 would apply to almost every Indian event; weather and fuel
  supply have no class.

**Coal power** (asked separately under coal) is the coal subset of this sector: 225,068 MW CEA,
with GEM GCPT for unit-level start/retire years. It is the nearest-to-READY Indian cell once the
inclusion rule exists.

---

## Transmission — **INCOMPLETE** (access) → sector bottom line **CONTEXT_ONLY**

**Denominator.** CEA cumulative transmission ≥220 kV: **506,513 ckm up to March 2026**, national,
by voltage and ownership (no state split in that table); CEA monthly substation and line
completion reports. OSM maps the HV grid well (11,806 ways ≥400 kV; 2,946 substations ≥220 kV) as
display context. A consequence denominator — regional antecedent load — is built into the GD
categories themselves (GD-1 < 10% of antecedent regional generation or load, and so on).

**What Grid-India publishes.** Not verifiable from this environment: every Grid-India host failed
the TLS handshake. Secondhand: monthly reports list grid disturbances with category, utility/state,
load or generation loss in MW, and restoration. If confirmed, this is a **regulated event register
with a known inclusion rule and a magnitude**, which is exactly what GLOBAL_METHODOLOGY §3.3 says a
portable transmission measure needs.

**Achievable incident coverage.** Potentially complete for GD/GI events (rule-based), once access
works. News coverage alone would capture only the large ones (e.g. July 2012).

**Restoration evidence.** Reportedly event-level restoration times (hours). Grid events are
event-tracking only under GLOBAL_METHODOLOGY §2.5.

**Russia assumptions that fail.** *Saturation-8 event burden* is not portable: GD-1 events are
reportedly routine across India's regional grids, so a weighted count of 8 concurrent events would pin the
sector at 100. The `voltage_weight` bands (750/500/330/220/110 kV) are Soviet classes; Indian
classes are 765/400/220 kV and ±800/±500 kV HVDC. Replace with a load-loss-share measure
(MW lost × hours ÷ regional demand), or keep transmission event-only.

**To move up:** a human with working access (possibly from India) confirms the GD report format,
archive depth and terms; record only date, region/state, category, MW and duration.

---

## Oil logistics — **INCOMPLETE** → **CONTEXT_ONLY**

**Denominator.** No single registry. Crude and product pipelines: GEM GOIT (attributes) plus PNGRB
product-pipeline authorisations (names, endpoints, authorised entity) and Ready Reckoner pipeline
tables (length and capacity; their **utilisation columns are never read**). Port crude-handling and
tankage capacity: no consolidated official source found. OSM has 25 oil-pipeline ways.

**The Russia proxy breaks.** Russia uses the refining base as the oil-logistics denominator. India
imports ~90% of the crude it refines, so the logistics system is import-facing; the refining base
is at least the right order of magnitude for throughput, but it says nothing about terminals or
pipelines individually.

**Achievable incident coverage:** pipeline leaks/theft, port closures for cyclones; news-driven.
**Restoration evidence:** sparse, news-driven.

---

## Gas — assessed separately, as instructed

| Sub-sector | Denominator | State | Notes |
|---|---|---|---|
| **Production** | PPAC gross 34,776 MMSCM FY 2025-26 (net 34,326), onshore by state, offshore by basin | **INCOMPLETE** | 72% offshore (Mumbai and Eastern offshore) has **no state**; a state denominator would cover 28% of output |
| **Processing** | No public plant-level registry of gas processing / fractionation capacity located | **INSUFFICIENT_EVIDENCE** | Do not proxy from production |
| **Pipelines** | PNGRB via PPAC: 19,030 km operational, 27,598 km incl. partially commissioned (30.06.2026), by operator; authorised capacity is an arithmetic sum per entity; GEM GGIT attributes | **EXPERIMENTAL** as length context; **UNSUITABLE** as a capacity share | Same non-additivity trap as Russia's GEM capacities. No state geography |
| **LNG import terminals** | Ready Reckoner Table 3.9: 8 terminals, operator, location, capacity 01.04.2026, **53.5 MMTPA** total (chapter text says 52.7) | **EXPERIMENTAL** | Single basis (regasification nameplate); resolve 53.5 vs 52.7; small N means one event is a large share — publish as a list with context, not a percentage, unless the owner decides otherwise |
| **Storage** | No public commercial gas-storage inventory found | **INSUFFICIENT_EVIDENCE** | Strategic reserves are out of scope by rule |

**Restoration evidence:** PPAC monthly production and LNG import volumes (national, monthly) —
observed but not facility-level. **Russia assumptions:** `lng_terminal` 300-day and
`gas_processing` 200-day fallbacks are conflict-damage horizons with no Indian basis.

---

## Coal — assessed separately, as instructed

### Coal mine supply — **EXPERIMENTAL** (denominator) → **CONTEXT_ONLY** today

**Denominator.** Ministry of Coal: FY 2024-25 raw coal **1,047.52 MT** (CIL 781.06, SCCL 69.01,
captive & others 197.46); dispatch 1,025.33 MT; FY 2025-26 to December 721.65 MT; full FY 2025-26
all-India total **not found** in the material read. Production basis (MT/yr), not capacity; state
tables are in the Coal Directory (not mined). GEM GCMT (August 2026) would add mine-level
production and status — licence notice to resolve first. Coal is central to India's supply chain
(EIA: 17.34 of 22.35 quad Btu of 2024 production; 40% of generating capacity), so this sector
cannot be left uncovered in any honest India composite.

**Achievable incident coverage.** Expected classes (not yet measured): mine floods in the
monsoon, accidents, strikes and land/clearance stoppages; reported through PIB, company disclosures and regional press (often Hindi or state
languages). Coverage unmeasured.

**Restoration evidence.** Monthly company production releases (observed, company-level).

**Russia assumptions that fail.** The model has no coal events at all (`coal` is uncovered); the
`coal_mine` 150-day fallback is unused and has no Indian basis. **Rail evacuation and plant coal
stocks are out of scope** — the first edges into chokepoint analysis, the second is a fuel-state
field.

### Coal power — **EXPERIMENTAL** (see generation)

225,068 MW (CEA, 30.09.2026). Unit-level dated census achievable from GEM GCPT + NPP. The 2025
removal of 2,825 MW of long-outage coal capacity from CEA totals must be reversed in the
denominator.

---

## Summary

| Sector | State | Binding constraint |
|---|---|---|
| Refining | EXPERIMENTAL (denominator near READY) | HRRL basis decision; event definition; turnaround handling |
| Electric generation | EXPERIMENTAL national / INCOMPLETE state | Inclusion rule for census-density outages; physical-location denominator; CEA removal rule |
| Transmission | INCOMPLETE | Grid-India unreachable; saturation proxy not portable |
| Oil logistics | INCOMPLETE | No terminal registry; Russia proxy breaks |
| Gas — production / processing / pipelines / LNG / storage | INCOMPLETE / INSUFFICIENT_EVIDENCE / EXPERIMENTAL (length only) / EXPERIMENTAL / INSUFFICIENT_EVIDENCE | Offshore has no state; no processing or storage registry |
| Coal mine supply | EXPERIMENTAL | Production basis only; GCMT licence; FY 2025-26 total |
| Coal power | EXPERIMENTAL | As generation |
| **Country** | **CONTEXT_ONLY** | Event model, not data |

## Model assumptions that do not transfer (consolidated)

1. **150-day modelled refinery horizon** — strike-damage calibration; India has observed monthly
   recovery instead.
2. **Conflict-derived decay** — no decay; step-with-window model, closed by NPP re-commissioning or
   PPAC monthly runs.
3. **Transmission saturation-8 event burden** — pinned at 100 by routine GD-1 events; use load-loss
   share or event-only.
4. **Cause taxonomy** — no weather/natural-hazard or fuel-supply class; no exclusion for economic
   reserve shutdown.
5. **Exposure framing under census-density reporting** — risks becoming a forced-outage rate.
6. **Regional denominators** — CEA state capacity is allocation-based; Russia's WRI-by-oblast
   approach would mis-assign Indian capacity.
7. **Oil-logistics proxy** — the refining base is not a logistics denominator for an
   import-dependent system.
