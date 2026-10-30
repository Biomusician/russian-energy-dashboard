# Canada — index readiness

Lane: CANADA source audit, written 2026-10-30. **Nothing here changes a published number.**
Source details and licences are in [CA_SOURCE_AUDIT.md](CA_SOURCE_AUDIT.md); sourced context
figures in `data/candidates/ca_profile.json`. The decay, transmission and denominator reasoning
builds on [../GLOBAL_METHODOLOGY.md](../GLOBAL_METHODOLOGY.md) §2–§4 and is not repeated here.

Per-sector states follow the lane brief: **READY / EXPERIMENTAL / INCOMPLETE / UNSUITABLE**
(same definitions as GLOBAL_METHODOLOGY §4.1). The country bottom line uses **INDEX_READY /
EXPERIMENTAL / CONTEXT_ONLY / INSUFFICIENT_EVIDENCE**.

---

## Bottom line

**EXPERIMENTAL.** Canada has denominators for three sectors that are better than Russia's
(official, dated, province-resolved), and one regulator-grade restoration signal (CER
interruption-duration class and pipeline available-capacity variance). It does **not** have a
national disruption register for any sector, its grid data are mostly not openly licensed, and
its typical disruption — wildfire evacuations and shut-ins, weather, technical fires — breaks
every conflict-calibrated constant in `methodology/scoring.json`. A Canadian ESDI run on the
Russia model today would be an estimate presented as an observation.

**Minimum work to reach INDEX_READY** (in order; each item is necessary):

1. **Cause taxonomy.** Add natural-hazard/weather and wildfire (and a *precautionary shutdown*
   damage state) to the taxonomy. Today `causes` has no such class, so the dominant Canadian
   cause would land in `unknown` (weight 0.7), and `damage_severity.shutdown = 1.0` would treat
   a precautionary evacuation shut-in like physical destruction.
2. **Recovery model.** Adopt GLOBAL_METHODOLOGY recommendation (2) for Canada: observed-duration
   step plus a declared confirmation window W and a disclosed `status_unknown` share — **no
   modelled decay**. Wire CER `Duration of interruption` and CER available-capacity variance as
   observed recovery evidence.
3. **Refining registry.** Build a curated per-refinery registry from the CER provincial profiles
   (2023–2024 capacities), seeded from NACEI 2016 and reconciled to CER's ~1.93 million b/d /
   17-refinery total; **upgraders excluded** and carried separately.
4. **Generation layer.** Acquire GEM GIPT (Sept 2026 release) for unit-level MW with start and
   retirement years; reconcile its province-year totals to StatCan 25-10-0022 before use.
5. **Drop transmission from any Canadian composite** (renormalise, as uncovered sectors already
   are), and track grid events as events only.

Items 1–2 are methodology changes that need owner sign-off; 3–5 are data work.

---

## Russia-model assumptions that fail in Canada

| Assumption (scoring.json) | Why it fails here |
|---|---|
| **150-day modelled refinery horizon** (`sector_fallback_horizon_days.refinery`) | Calibrated to repeated kinetic damage with almost no restart reporting. Canadian refinery outages are fires, unplanned technical shutdowns and turnarounds, usually weeks, and restarts are visible in CER weekly regional crude runs. A 150-day exponential would score ~65 impairment-days for an outage observed to last far less (GLOBAL_METHODOLOGY §2.2). Turnarounds must not score at all as disruption (`maintenance` 0.15 is still a positive contribution) |
| **Conflict-derived decay** (exponential with `horizon_to_halflife_factor`) | Wildfire shut-ins are *precautionary*: no physical damage, restart gated by evacuation orders being lifted. The curve shape (0.63 impaired at day 30) has no physical basis for them. Province-month production in StatCan 25-10-0063 shows the dip and the recovery directly — that is observed, aggregate evidence |
| **Transmission saturation-8** (`transmission.saturation_events`) | Canadian grid disruption is weather-driven and areal (ice storms, wind, wildfire), mostly on *distribution*. One event can down many lines at once; there is no national register to count events against; utility outage feeds are live-only and non-commercially licensed. The constant would convert reporting density into score (GLOBAL_METHODOLOGY §3.2). Voltage bands also misfit: Canadian classes are 735/500/345/315/240/230 kV; a ≥330 kV selector drops most of Ontario, Alberta and Hydro-Québec's backbones |
| `refining: capacity_mtpa` basis | Canadian refining data are in b/d or 10³ m³/d. Conversion to tonnes needs a crude density, which varies widely between bitumen blends, synthetic crude and light imports. Keep the Canadian sector in volume units, never mixed with Russian MTPA |
| Sector set excludes upstream | Canada's largest disruptions by volume are oil-sands and gas-field shut-ins; with no upstream sector they would either vanish or be mis-filed into refining (via upgraders) or oil_logistics |
| Region = admin-1 choropleth | Quebec and Ontario are enormous; the 3 territories have tiny systems. A province-level share is fine as arithmetic, but regional intensity in NT/YT/NU will be dominated by single small plants — publish with the denominator alongside, as the Russia regional figures should be (GENERATION_DENOMINATOR_AUDIT §Regional) |

---

## Sector by sector

### Refining — **EXPERIMENTAL**

| | |
|---|---|
| Inventory | CER: **17 refineries, ≈1.93 million b/d (as of 2024)**, Canada profile. Per-plant capacities are in the 14 provincial profiles (prose, 2023–2024). NACEI 2016: 14 refineries (1,845.1 thousand b/d atmospheric distillation) + 2 asphalt refineries (45.0) + **5 upgraders (1,430.5) in the same layer** |
| Total capacity / basis / unit | crude (atmospheric) distillation, thousand b/d or 10³ m³/d; CER weekly runs imply ≈295 thousand m³/d ≈ **1.86 million b/d** regional capacity (week ending 2026-09-15, derived) |
| Vintage | CER totals 2024; NACEI 2016; crude-runs weekly current |
| Status / retirement | none in any open per-plant source. Known changes since 2016 must be curated by hand with citations (e.g. Come By Chance converted to renewable diesel — CER; Sturgeon added — CER Alberta profile) |
| Missing values | plant-level current capacity in machine-readable form; operable vs nameplate basis is unstated for the % of capacity series |
| **Upgraders** | **Exclude from the refining denominator.** CER and StatCan both treat them as distinct (SCO production; upgrader capacity ≈1.4 million b/d bitumen in Alberta + 81.5 thousand b/d Lloydminster, SK). NACEI mixes them in and must be filtered on `Type`. Carry upgraders as an upstream/upgrading class; never as refining |
| Achievable incident coverage | Moderate: refinery fires/outages are reported by operators, regional press and CER's weekly runs (a regional utilisation drop is observed evidence an outage happened, though not which plant). No regulator incident register for refineries (CER does not regulate them; provincial regulators vary) |
| Restoration evidence | **Good at regional level** (weekly CER runs/% capacity); plant-level restarts usually in operator releases |
| Fails | 150-day horizon; MTPA basis |

### Electric generation — **EXPERIMENTAL** (READY at aggregate)

| | |
|---|---|
| Inventory | StatCan 25-10-0022: installed capacity by province × type × producer class, **annual 2006–2025** — a dated census at each year, which is what Russia lacks. 2025: **155.9 GW**, hydro 83.0 GW |
| Facility level | none current and open. NACEI ≥100 MW: 247 plants, 125.1 GW, 2015–2017, no status. GPPD: 1,159 plants, 143.6 GW, 97% NRCan-derived, commissioning year on 29 rows. GEM GIPT: unit-level with start/retirement years (not yet acquired) |
| Status / retirement | StatCan: implicit (capacity changes year to year). Facility layers: none, except GIPT |
| Missing values | StatCan suppresses some cells (e.g. monthly conventional-steam generation returns "..") — treat as unknown, never zero |
| Coal power, temporally | CER Alberta profile: Alberta **fully phased out coal-fired generation by June 2024**; press reports (search results, e.g. power-eng.com, CBC — not read in full) date the last unit, Genesee 2, to 16 June 2024 with the station converted to gas. Federal SOR/2012-167 ends a coal unit's useful life at the earlier of 50 years after commissioning or **31 December 2029**. Remaining coal provinces per NACEI 2017: SK (3 plants), NS (4), NB (1); CER's SK profile (2021 data): coal 41% of SK generation. **A 2017 facility list applied to 2022–2026 would carry ~6.4 GW of Alberta coal that no longer burns coal** — the GPPD trap again. Use StatCan 25-10-0023 (thermal capacity by principal fuel, annual) for the coal subtotal by province-year |
| Achievable incident coverage | Low to moderate: plant outages appear in AESO (AB) and IESO (ON) unit-level data under restrictive licences; elsewhere only press/operator releases |
| Restoration evidence | AESO/IESO unit capability is observed but may only be cited as derived facts |
| Fails | 200/400-day thermal/hydro horizons are rebuild assumptions |

### Transmission — **UNSUITABLE** (as the saturation-8 event burden); grid consequence measure **INCOMPLETE**

| | |
|---|---|
| Inventory | OSM lines/substations (not probed for Canada). No official national HV inventory found |
| Denominator | none for an event burden; for a consequence measure one would need customers served by province (not located in this audit) |
| Incident coverage | No national obligation-based register. Provincial operator outage feeds are live-only (Hydro-Québec, BC Hydro) and non-commercially licensed; AESO/IESO transmission outage reports are partly forward-looking (planned outages) and must not be ingested |
| Restoration evidence | live feeds only — no history |
| Recommendation | Event tracking only, province level, cited from public reporting; never in a composite |

### Oil logistics — **EXPERIMENTAL** (pipelines); terminals **INCOMPLETE**

| | |
|---|---|
| Inventory | CER Key Attributes (system name, operator, start year, length, commodity, capacity in prose) and Throughput & Capacity (nameplate and available capacity at key points, monthly, 2006–2026-06) for CER-regulated oil systems |
| Basis / unit | nameplate capacity, 10³ m³/d, **at named key points** |
| Status | `Available Capacity` + `Reason For Variance` per month — an observed constraint signal |
| Missing | provincially regulated pipelines; export marine terminals and rail terminals have no open capacity census (CER crude-by-rail exports are flows, not capacity) |
| **Denominator caution** | Key-point capacities on one system are not additive, and the Russia proxy (oil logistics measured against the refining base) is invalid for an exporter (GLOBAL_METHODOLOGY §4.3): Canada exported 4.31 million b/d of crude in 2025 against 1.77 million b/d of refinery input. Use **system export capacity** (sum of one designated key point per system) or production as the base, decided by the owner |
| Incident coverage | CER incidents: 463 records since 2022, of which **36 interrupted operations** (33 short-term, 3 long-term) — a regulator-grade, complete-within-scope register for CER-regulated lines |
| Restoration evidence | **Best in Canada**: interruption class per incident + monthly available-capacity variance |
| Fails | 70-day pipeline horizon (most interruptions are short-term) |

### Gas — split into four, never one number

| Sub-sector | State | Denominator / notes |
|---|---|---|
| **Processing** | **INCOMPLETE** | NACEI 2017: 718 plants (AB 601 from AER ST50, BC 84, SK 32, NS 1), licensed inlet ≈57,400 MMcf/d — about 3× 2025 marketable production (≈19.5 Bcf/d), so it is licensed nameplate including idle plants, not operating capacity. AER ST13 has monthly facility volumes but **no capacity**; ST50 capacity list appears discontinued on the AER listing; BC Energy Regulator *plant capacities* exists but licence unconfirmed. Restoration evidence: ST13B monthly volumes (derived facts only) |
| **Pipelines** | **EXPERIMENTAL** | CER throughput/capacity (daily) for NGTL, TC Mainline, Westcoast, Alliance, Foothills, TQM, M&NE, Brunswick; CER incidents. Same key-point non-additivity caution as oil |
| **LNG** | **UNSUITABLE as a share; CONTEXT** | One export terminal operating (Kitimat, first export June 2025, 14 Mtpa design per CER) plus one import terminal (Canaport). With n = 1, any event is a 0/100% swing — publish as an event with observed export flow (CER monthly by terminal), not as an exposure share. **Also a temporal denominator trap: export capacity is zero before mid-2025** |
| **Storage** | **CONTEXT_ONLY** | NACEI 2017: 57 underground storage facilities; StatCan 25-10-0086 monthly storage inventory and injections/withdrawals by province (observed, aggregate) |

### Coal — **INCOMPLETE** (mine supply); coal power belongs to generation

| | |
|---|---|
| Mine supply | StatCan 25-10-0046: monthly production by province (NS, NB, SK, AB, BC), 2008–2026; **2025: 42.4 Mt**. Metallurgical/thermal split partly **suppressed** (security level 1). AER ST26 for Alberta. No open mine-level capacity census found (GEM Coal Mine Tracker would be the candidate — not checked) |
| Coal power | model inside electric_generation with province-year coal capacity (StatCan 25-10-0023) so retirements apply only from their dates. Do not create a coal-power sub-score whose denominator shrinks toward zero by 2030 — an end-of-series ratio over a vanishing base is meaningless |
| Restoration evidence | monthly production volumes (aggregate) |

### Upstream production (oil sands) — **not a sector; EXPERIMENTAL as a context lane**

| | |
|---|---|
| Why it matters | 2025 crude production 4.79 million b/d, **73% of it oil-sands bitumen or synthetic crude**, **85% from Alberta** (StatCan 25-10-0063, derived from annual sums). Wildfire evacuations around oil-sands operations are the archetypal Canadian energy disruption, and they would dominate any Canadian volume-weighted measure |
| Denominator | StatCan monthly production by province and stream (in-situ bitumen 1.94, mined bitumen 1.77, synthetic crude 1.31 million b/d in 2025) — a production basis, not capacity. No open facility-level capacity census (AER ST39 for mines is monthly volumes; ST53 in-situ is sold) |
| Restoration evidence | **Observed at aggregate**: the province-month production dip and recovery in StatCan and CER series. Operator shut-in volumes in press releases are often **analyst or company estimates** and must carry `kind=estimated` |
| Treatment | A separate `upstream_production` lane — shut-in events with observed start/end, plus the province-month production series as context. **Not in the composite** until the owner decides the sector set (GLOBAL_METHODOLOGY §4.4). Upgrader outages belong here, not in refining |
| Safety | Production volumes are published aggregates; no facility ranking, no list of which operations are largest |

---

## Achievable incident coverage — overall

| Sector | Register with an inclusion rule? | Expected coverage of 2022+ disruptions |
|---|---|---|
| Pipelines (CER-regulated) | **Yes** — Onshore Pipeline Regulations | high within scope; scope excludes provincial lines |
| Refining | no | moderate (operator + press + regional utilisation dips) |
| Generation | no national; AESO/IESO data under restrictive terms | low–moderate |
| Grid | no | low; live-only feeds |
| Upstream | no event register; production statistics are complete | events: press-dependent; magnitudes: observed in aggregate |
| LNG | n = 1 terminal; CER monthly flows | high for the one terminal |

The Canadian Disaster Database cannot serve as a benchmark for 2022+ (coverage ends
2022-01-01).

---

## What is still unmeasured

- No Canadian incident has been scored; no sensitivity has been run. Every readiness state above
  is a judgement about sources, not a tested build.
- Whether CER weekly crude-runs "capacity" includes upgraders is inferred from magnitude, not
  confirmed.
- GIPT's Canadian coverage and reconciliation to StatCan are unknown until acquisition.
- The OSM Canadian grid has not been probed.
