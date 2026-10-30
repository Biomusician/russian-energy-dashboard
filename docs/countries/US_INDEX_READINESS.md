# United States — index readiness

Lane: UNITED STATES source audit, written 2026-10-30. **Nothing here changes a published
number.** Sources and their licences are in [US_SOURCE_AUDIT.md](US_SOURCE_AUDIT.md); the
state vocabulary is GLOBAL_METHODOLOGY.md §4.1 (denominator readiness: READY / EXPERIMENTAL /
INCOMPLETE / UNSUITABLE) and §7.1 (what a sector may display: SCORED / EXPERIMENTAL /
CONTEXT_ONLY / INSUFFICIENT_EVIDENCE …). Two separate questions are answered per sector,
because the US answers them very differently:

- **Denominator** — is there a census, on one basis, at the needed date?
- **Events and recovery** — is there a *systematic* public record of disruptions, and of
  restoration, that a register could be built from without a curated hunt?

Admin unit: the 50 states + DC (Puerto Rico is a separate admin-0 in Natural Earth and has its
own sheets in EIA-860M; treat it as a separate, explicitly-scoped unit, not silently folded in).

---

## Bottom line

**Country: EXPERIMENTAL.** The US has the best denominators of any country this project has
examined — refining and generation are READY on a single, dated, official basis, and both
support a census at each scoring date, which Russia cannot do. What blocks INDEX_READY is not
data but **model fit**: the scoring engine's cause taxonomy has no natural-hazard class, its
modelled recovery horizons are conflict-derived, its "partial restart" rule ignores the most
common US recovery evidence, and the transmission proxy saturates permanently. A composite on
the current engine would be dominated by modelled decay applied to hurricane outages.

**Minimum work to reach INDEX_READY (one level up):**

1. Add a `natural_hazard` (weather) cause class and a `precautionary_shutdown` damage state to
   `taxonomy.json` / `scoring.json`. Today a hurricane shutdown can only be filed as `unknown`
   (0.7) or `technical` (0.8), with damage `shutdown` (1.0).
2. Replace conflict-derived fallback horizons for US non-kinetic causes with **hazard-specific
   fallbacks derived from US observed durations** (OE-417 restoration times, EAGLE-I recovery
   curves, PHMSA shutdown→restart), or make US events **unscorable without recovery evidence**.
3. Let a sourced **restart of normal operations** shorten decay for non-kinetic events, rather
   than being display-only (`partial_restart`).
4. Build census-at-date denominators for refining (annual EIA-820 vintages + Table 11/13 dates
   + monthly PADD lag check) and generation (860M Retired sheet).
5. Secure an acquisition path for OE-417 (unreachable from CI today) and pick an event source
   for refinery outages; drop the transmission saturation proxy for the US.

Items 1–3 are methodology changes that also touch the Russian index's code paths; they need the
owner's decision and a frozen-replay check that Russia's numbers do not move.

| Sector | Denominator | Events / recovery | §7.1 display state today |
|---|---|---|---|
| refining | **READY** | EXPERIMENTAL (no systematic register) | EXPERIMENTAL |
| electric_generation | **READY** | EXPERIMENTAL (nuclear daily; fossil unit outages not public) | EXPERIMENTAL |
| transmission | **UNSUITABLE** for event-burden; READY for a *customer-interruption* measure (different concept) | **READY** (OE-417, EAGLE-I) | CONTEXT_ONLY |
| oil_logistics | **INCOMPLETE** | EXPERIMENTAL (PHMSA; ports unverified) | CONTEXT_ONLY |
| gas — LNG export | **READY** with a basis rule | EXPERIMENTAL | EXPERIMENTAL |
| gas — storage | **READY** (design capacity) | INCOMPLETE (rare events) | CONTEXT_ONLY |
| gas — pipelines | **EXPERIMENTAL** (boundary capacity, mileage) | EXPERIMENTAL (PHMSA) | CONTEXT_ONLY |
| gas — processing | **INCOMPLETE** (2017 census) | INCOMPLETE | CONTEXT_ONLY |
| gas — production | flow only (not capacity) | candidate (BSEE, unverified) | CONTEXT_ONLY |
| coal — mine supply | **EXPERIMENTAL** (mine production; capacity by state only) | INCOMPLETE | CONTEXT_ONLY |
| coal — coal power | READY (subset of 860M) | as generation | belongs in electric_generation, not coal |

---

## 1. Refining

**Denominator — READY.** EIA *Refinery Capacity Report*, data as of 1 January 2026:

| | Value |
|---|---|
| Basis | operable **atmospheric crude oil distillation** capacity |
| Unit | **barrels per calendar day** (b/cd); b/sd also published |
| Sites with crude capacity | **124** (Σ = **18,160,493 b/cd**, exact match to Table 1; zero missing) |
| Operating / idle | 18,126,493 / 34,000 b/cd (idle: two sites) |
| Stream-day total | 19,157,174 b/sd (exact match) |
| "Operable refineries" count | 130 — **includes 6 non-crude processors** added by the 2024 frame change |
| Vintage | annual, 1 January; prior years back through the survey history |
| Retirement treatment | Table 11 (prior-year shutdowns with date of last operation), Table 13 (all permanent shutdowns 1990–2026) |
| Monthly lag check | PADD-level operable capacity: 18,015 kb/cd in Mar 2026 (Benicia's 145,000 b/cd has left) |

**The key lesson from this repo, checked explicitly.** REFINERY_CAPACITY_BASIS.md found Russia's
numerator (strike-table MTPA) and denominator (Wikipedia registry MTPA) on different bases,
disagreeing by 5.7% and by 2.3× for one plant, with two denominator members unable to reach
the numerator. In the US **one mandatory census supplies both sides on one basis**, refinery by
refinery, and the parts sum exactly to the published whole. Rules that keep it that way:

- Numerator capacity for a disrupted refinery comes **only** from this file, never from the
  press report of the incident (press figures are often b/d nameplate or "stream day").
- Use **b/cd**, not b/sd: b/cd is what respondents report; b/sd is partly derived (÷0.95 for
  imputed sites — 10 sites sit at exactly 0.95). Never mix the two.
- Membership is "has crude distillation capacity", not "is on the frame".
- Census-at-date: for scoring date *t*, use the most recent 1 January census ≤ *t*, minus
  shutdowns dated between that census and *t* (Table 11 of the next issue; monthly PADD totals as
  the cross-check). Benicia shows why: the 2026 census keeps a plant that had stopped by spring.

**Incident coverage — EXPERIMENTAL.** There is **no federal refinery-outage register.** Systematic
partial signals: EIA monthly/weekly PADD utilisation (aggregate, observed, not attributable);
DOE situation reports during activated emergencies (state-level, prose). Plant-level events come
from company statements, trade press and state agencies (TCEQ emission-event reports and
California outage reporting are candidates, unverified). An incident lane will have to curate,
as it does for Russia, but against a US event universe that is large and weather-clustered.

**Recovery evidence.** Restart dates are commonly *reported* (company statements, trade press)
but not *registered*. No official per-plant restart series exists.

**Russia-model assumptions that fail:**

- **150-day modelled refinery horizon** (half-life 150 ÷ 3.3219 = **45.2 days**). A refinery
  that shut for a hurricane and restarted in a week would still score 0.5^(30/45.2) = **63%
  impaired at day 30** and 25% at day 90. The horizon encodes reconstruction after kinetic
  damage; it has no meaning for a precautionary shutdown or a unit fire.
- **`partial_restart` is display-only.** In the US the typical recovery evidence *is* "the
  refinery restarted" — under current rules that never shortens decay, so the modelled tail
  would dominate (`model_dominated` would be set almost everywhere).
- **Cause taxonomy.** No weather/natural-hazard class; hurricanes fall into `unknown` (0.7).
- **Damage severity.** `shutdown` = 1.0 treats a pre-emptive, undamaged shutdown as full
  impairment.
- **Sector weight 0.35** reflects Russia's export economy; it is not transferable.

**Classification: denominator READY; sector EXPERIMENTAL** until (b) the cause/recovery model fits
non-kinetic events and (f) an event source with a declared cadence exists.

---

## 2. Electric generation

**Denominator — READY.** EIA-860M, September 2026 file:

| | Value |
|---|---|
| Unit of record | generator (unit-level), with plant, state, **county**, BA |
| Bases | **nameplate**, **net summer**, **net winter** MW (all three on every row; 65 summer cells non-numeric) |
| Operating sheet | 28,484 generators: OP 26,235 / SB 1,497 / OS 536 / OA 216; net summer 1,324,125 MW (OP-only 1,300,414) |
| Retirements | Retired sheet: **7,321 generators, retirement month/year 2002–2026**; e.g. 2022: 294 units / 17.4 GW summer; 2023: 474 / 15.4 GW; 2024: 338 / 9.5 GW; 2025: 206 / 5.1 GW |
| Planned retirements | 518 operating generators carry a planned year; 42.6 GW summer planned by 2030 (a plan, never a status) |
| Census-at-date test | 1 Jan 2022 rebuilt from the 2026 file: **1,149.5 GW** vs MER end-2021 **1,145.9 GW (+0.3%)** |
| National context | MER net summer capacity end-2025: 1,279.2 GW; EPM utility-scale Aug 2026: 1,318.8 GW |

Recommended basis: **net summer MW**, OP status only in the denominator (SB/OS/OA are disclosed,
not counted: OS units are "NOT expected to return"). Nameplate and net summer differ by ~7%
(1,417 vs 1,324 GW), so a numerator taken from a press report's "MW" must not be mixed in —
size numerators from 860M only.

This is the GIPT-style temporal axis GENERATION_DENOMINATOR_AUDIT.md said Russia lacks, and for
the US it is first-party, public domain and keyless.

**Incident coverage — EXPERIMENTAL.** Generation trips appear in OE-417 when they meet alert
criteria (system-level, not always unit-named). Nuclear: NRC daily reactor status and EIA's
`nuclear-outages` series give **daily observed** unit availability (not verified in detail here).
Fossil/renewable unit outages: **NERC GADS is not public**; ISO outage reports are partial and
mostly not openly licensed (CAISO). There is no public, systematic, unit-level forced-outage
record outside nuclear.

**Russia-model assumptions that fail:** 200-day thermal / 400-day nuclear and hydro horizons
(half-lives 60 and 120 days) describe rebuilding struck plants. US generation disruptions are
dominated by weather trips, fuel-supply failures and freezes measured in hours to days; NRC
data would show nuclear outages measured in days to weeks with observed end dates.

**Classification: denominator READY; sector EXPERIMENTAL.**

---

## 3. Transmission

**Denominator — UNSUITABLE for the event-burden construct.** No public, safety-acceptable
inventory of lines/substations (facility-level grid geodata is rejected on safety grounds). A
different, *outcome* denominator is READY: customers per county (EAGLE-I MCC field; EIA-861 by
state, unverified here).

**Incident coverage — READY (as a record of events, not of infrastructure).**

- **OE-417**: mandatory, with event start and **restoration timestamps**, demand loss MW,
  customers affected, state/area. A 2012–2021 analysis counted **2,286 incidents** (~229/yr;
  arXiv 2207.08146, secondary). Acquisition path unresolved (host unreachable; EIA mirror
  suspended).
- **EAGLE-I**: county customers-out every 15 minutes, 2014–2025, CC BY 4.0, ~92% of customers by
  2022 — a systematic, **observed** restoration curve for every event.
- DOE situation reports: state-level peak and restoration (e.g. Milton: 3,365,661 peak, 98%
  restored by 16 Oct 2024).

**The saturation-8 proxy fails, measurably.** With ~229 OE-417 events/yr and the modelled
transmission half-life (46 ÷ 3.3219 = 13.8 days, mean life ≈ 19.9 days), the steady-state
concurrent burden is ≈ 229/365 × 19.9 ≈ **12.5 events**, or ≈ 8.8 after the `unknown` cause
weight — **at or above saturation on an average day, before any storm clustering.** The US
transmission sector would read ~100% most of the time. (Illustrative: treats each OE-417 event
as one facility and ignores confidence weights.)

**Recommendation.** Do not port the event-burden model. If a grid measure is wanted, it is a
**customer-interruption** measure (customer-hours out ÷ customers served, from EAGLE-I), which
is a *consequence* concept, not infrastructure exposure, and must be labelled as such and kept
structurally distinct from the four ESDI concepts.

**Classification: UNSUITABLE (as built) → CONTEXT_ONLY**, with an event list from OE-417.

---

## 4. Oil logistics (export/import terminals, major storage, trunk-pipeline operations)

**Denominator — INCOMPLETE.**

- Terminals: **no official census of crude/product export or import terminal capacity** was
  found. Export *volumes* are published (MER: petroleum exports 10.78 MMb/d in 2025); capacity
  is not.
- Storage: EIA working/shell storage capacity is published by PADD (not verified in this lane);
  aggregate only.
- Trunk pipelines: no capacity registry in EIA (inter-PADD *movements* are flows). GEM GOIT
  carries partial capacity under the live-backend problem (no release identifier). PHMSA annual
  reports give **mileage** by operator and state — a length, not a capacity.

**Incident coverage — EXPERIMENTAL.** PHMSA hazardous-liquid incidents are systematic and
mandatory, with shutdown and **restart date/time** (observed duration, to be verified on
acquisition), at state/county precision after dropping coordinates. Most incidents cause no
throughput disruption, so an inclusion threshold (e.g. reported shutdown) is required. Port and
terminal closures (USCG port conditions, DOE sitreps) are event-driven prose.

**Assumptions that fail:** the Russian oil-logistics denominator (MTPA at struck terminals and
pumping stations) has no US equivalent; the 100-day terminal / 70-day pipeline horizons describe
strike damage, while PHMSA restarts are typically recorded within days.

**Classification: INCOMPLETE → CONTEXT_ONLY** (context: exports; event list from PHMSA).

---

## 5. Gas (separate sub-measures; never one gas number)

| Sub-sector | Denominator | Basis / unit / vintage | Events / recovery | Class |
|---|---|---|---|---|
| **Production** | None as capacity. Dry production 39,287.6 Bcf (2025, MER); marketed 43,229.1 Bcf | flow, annual/monthly | Freeze-offs and hurricane shut-ins; BSEE offshore shut-in statistics are a candidate (**unverified**) | CONTEXT_ONLY |
| **Processing** | EIA plant-level file is **2017** data, released Jan 2019; state volumes processed are annual and current | stale census, no retirement axis | none systematic | **INCOMPLETE** |
| **Pipelines** | EIA state-to-state capacity (Jan 2026; boundary-crossing MMcf/d, not a pipeline registry); PHMSA mileage; GEM GGIT partial | mixed | PHMSA gas transmission incidents (observed restart, to verify) | **EXPERIMENTAL** |
| **LNG export** | EIA liquefaction file, Q3 2026, per train, status and dates | **two bases** (baseload vs peak nameplate), Bcf/d and Mtpa | Plant trips and outages are reported by operators/press; no register | **READY with a basis rule** |
| **Storage** | EIA field-level storage (RP7), annual | **working gas design capacity** vs demonstrated peak (keep one) | Rare, well-documented events | READY / CONTEXT_ONLY |

**The LNG basis rule.** "Commercial operation" trains total 11.42 Bcf/d baseload, yet 2025 exports
averaged **15.1 Bcf/d** — because trains in **commissioning** (Plaquemines, Corpus Christi Stage 3)
were already exporting. A denominator of commercial-operation baseload would let a disruption
exceed 100% of its own base. Use **baseload nameplate of every train whose in-service date
(first cargo) ≤ t**: for end-2025 that is 11.42 + 3.96 = **15.38 Bcf/d** (excluding Golden Pass T1,
in service April 2026), consistent with observed exports. Never mix peak and baseload.

**Assumptions that fail:** 200-day processing and 300-day LNG horizons are strike-reconstruction
guesses. A US LNG outage record (e.g. a fire-driven multi-month outage) would be evidence-driven,
not modelled.

---

## 6. Coal

**Mine supply — EXPERIMENTAL.** Mine-level production 1983–2024 (EIA-7A/MSHA; 524 producing mines
and 512.5 MMst in 2024); **productive capacity only by state** (832.8 MMst, 2024). A
capacity-share score at mine level is not possible on one basis; a production-share score would
change the construct from capacity to flow. Incidents: mine-safety accidents (MSHA) are not supply
disruptions; supply interruptions (floods, rail) have no register — events INCOMPLETE.
**→ CONTEXT_ONLY.**

**Coal power — READY**, as a subset of EIA-860M (coal net summer 169.8 GW end-2025, MER). It
belongs in electric_generation; scoring it again under `coal` would double-count.

---

## 7. Cross-cutting: what the Russian engine assumes that the US breaks

| Assumption | Russia | US | Consequence |
|---|---|---|---|
| Cause classes | strike-dominated | weather-dominated; no class exists | add `natural_hazard` |
| Modelled horizons | reconstruction after kinetic damage | outages of days–weeks with observed ends | hazard-specific fallbacks or no fallback |
| `partial_restart` display-only | restart ≠ reconstitution after strikes | restart is the normal end of a weather outage | allow restart evidence to drive non-kinetic decay |
| `shutdown` severity 1.0 | shutdown follows damage | many shutdowns are precautionary | add a damage state |
| Confidence from publisher count | many outlets per strike | one mandatory official filing (OE-417, PHMSA) | official filing should rank as `confirmed` |
| Coverage benchmark | Wikipedia cumulative strike count | OE-417 is itself the universe for the grid | coverage = matched / OE-417 events |
| Event unit | discrete facility hit | regional hazard affecting many facilities at once | needs `episode_id` (already in GLOBAL_METHODOLOGY §7.2) |
| Denominator vintage | frozen census | dated monthly/annual census | census-at-date is feasible — do it from day one |
| Transmission saturation 8 | few concurrent events | ~12.5 concurrent on average | proxy saturates; drop |

## Provenance

Numbers are from files and pages read in this lane on 2026-10-30 (see US_SOURCE_AUDIT.md for
each URL). The census-at-date test, the refinery sums and the LNG sums were computed from EIA's
own XLSX files in the session scratchpad; nothing was written to `data/`. The OE-417 incident
rate is secondary (arXiv 2207.08146) and should be re-measured on acquisition.
