# Saudi Arabia — index readiness

Written 2026-10-30 by the Saudi Arabia source-audit lane. Companion to
[SA_SOURCE_AUDIT.md](SA_SOURCE_AUDIT.md), which carries the evidence and URLs for every source named
here. **Nothing here changes a published number.** Incident coverage is assessed from the nature of
the sources, not from incident research, which is a separate lane.

Readiness vocabulary:

- **READY** — denominator exists on one stated basis, dated, complete enough to score against.
- **EXPERIMENTAL** — usable with disclosed caveats; publish as a labelled sensitivity, not headline.
- **INCOMPLETE** — a credible path exists, but a required input is not yet acquired or reconciled.
- **UNSUITABLE** — should not be built, for data reasons, scope-boundary reasons, or both.
- **NOT APPLICABLE** — the sector does not exist in the country's energy system (a sourced zero,
  not a gap). Distinct from **UNKNOWN** (exists, unmeasured) and **NOT YET RESEARCHED**.

---

## Bottom line

**CONTEXT_ONLY** today.

- One sector — **refining** — has an index-grade denominator (Aramco's annual per-refinery table,
  gross basis), better than the Russian one. It is **EXPERIMENTAL** only because the incident side
  (coverage, attribution, recovery evidence) is untested for Saudi Arabia, and because a composite
  built from refining alone would be a refining index with a misleading name.
- Every other sector is INCOMPLETE, UNSUITABLE or NOT APPLICABLE.

**Minimum work to reach EXPERIMENTAL (refining sub-index only, clearly labelled):**

1. Curate `refineries_sa` from the Aramco annual reports **2021–2025, one dated row per refinery
   per edition**, gross basis, equity as metadata, province by ISO code. (Nine plants; a few hours.)
2. Confirm or rule out non-Aramco crude refineries (open question in the audit, §3).
3. Incident lane delivers a sourced Saudi corpus resolved to those registry rows, with the
   numerator taking the **registry's** gross capacity (never a strike-report figure).
4. State a coverage ratio honestly: there is no Saudi equivalent of the Russian coverage benchmark
   table, so the ribbon must say **coverage: unknown**, not a number.
5. Replace the heating-season logic with nothing (or a cooling-season flag) for Saudi Arabia — see
   "Russia-model assumptions that fail".

**Minimum further work to reach INDEX_READY (multi-sector):** acquire GEM GIPT and build a dated
province-level generation census (§2); establish a regional power-outage source (§3). Until both
exist, a Saudi composite would be refining under another name.

---

## 1. Refining — **EXPERIMENTAL** (denominator READY)

| Item | Finding |
|---|---|
| Inventory | 9 in-Kingdom refineries (5 wholly owned, 4 affiliated), Aramco Annual Report 2025 |
| Total capacity | **3,352 mbpd gross** (sum of published per-plant figures) |
| Basis | **gross 100% physical**, Aramco equity carried separately; reconciles to Aramco's own gross 7.8 / net 4.2 mmbpd headlines |
| Unit | mbpd (thousand barrels per day); stream- vs calendar-day not stated |
| Vintage | 31 Dec 2025; each annual edition gives that year's table (2021–2025 headline history published) |
| Status | none explicit; closures appear as absence (Jeddah); commissioning must be inferred by diffing editions |
| Retirement | none listed; not needed for 2022–present if editions are diffed |
| Missing values | none within the nine; completeness vs non-Aramco plants **not yet researched** |

**Why gross:** joint-venture equity ranges 50–62.5% on four of nine plants. Net basis would
understate those plants by 37.5–50% and measure Aramco's balance sheet, not the country's refining
system. This is exactly the mixed-basis trap in `docs/REFINERY_CAPACITY_BASIS.md`; Saudi Arabia can
avoid it from the start by taking numerator and denominator from the same Aramco row.

**Granularity caveat:** with nine plants, each is on average ~11% of the base. The sector series
will be lumpy — one event moves it by whole percentage points — and that should be explained in the
UI rather than smoothed.

**Achievable incident coverage:** attacks on refineries in the 2022–present window are publicly
reported by wire services and sometimes acknowledged by Aramco or official statements; Aramco's
H1-2026 interim report acknowledges attacks on unnamed in-Kingdom facilities. Expect partial
coverage of kinetic events, poor coverage of technical outages, and frequent conflicting or
unattributed accounts. **Coverage ratio cannot be computed** — no independent benchmark list exists.

**Restoration evidence:** sparse. Statements of resumption without durations are typical; observed
reconstitution windows (`kind=observed`) will be rare. Most Saudi refining recovery would fall back to
`kind=modelled`, which must be shown as such.

---

## 2. Electric generation — **INCOMPLETE**

| Item | Finding |
|---|---|
| Inventory | no current public plant list found. WRI GPPD: 90 plants, ECRA-sourced, newest 2016. GEM GIPT: unit-level with status and dates, **not yet acquired** |
| Total capacity | SEC: **93,858 MW grid-connected**, Q3 2025 (SEC 55,962 / IPP-IWPP 22,572 / Others 15,324) |
| Basis | grid-connected; excludes most captive generation (Aramco alone: 6.3 GW captive in 2025, 0.5 GW spilled to grid) |
| Unit | MW |
| Vintage | quarterly (SEC); WRI frozen ~2016 |
| Status / retirement | none in SEC aggregates; none in WRI; present in GIPT |
| Missing values | WRI lacks almost all renewables (137 MW solar vs ~12.3 GW renewables grid-connected at Q3 2025) and has no wind |

**Path:** GIPT → crosswalk to WRI/ECRA names → point-in-polygon to province → step-function
census by start/retirement year → reconcile national total against SEC's quarterly grid-connected
figure, disclosing the captive-vs-grid scope gap. Until then: INCOMPLETE. WRI alone would repeat the
Russian stale-denominator defect in a worse form.

**Achievable incident coverage:** low. Power-plant outages are seldom reported at plant level;
large regional blackouts may be reported, but SEC and regulator statistics are by **four operating
areas**, not provinces.

**Restoration evidence:** effectively none found.

---

## 3. Transmission — **UNSUITABLE** (as an event-burden sector), context only

| Item | Finding |
|---|---|
| Inventory | SEC aggregates only: 104,628 circuit-km, 1,305 substations, 529,382 MVA (Q3 2025) |
| OSM | 3,229 `power=line` ways; 638 substations tagged ≥132 kV — about half SEC's count |
| Basis / vintage | national aggregates, quarterly |

The Russian transmission sector is an event-burden measure with a modelled saturation constant. For
Saudi Arabia there is neither a regional event stream nor a regional inventory to normalise against,
and building a substation-level map of a grid where none is officially published is not something
this project should do. Recommend **no Saudi transmission sector**; the national SEC aggregates may
appear as dated context.

---

## 4. Oil logistics — **UNSUITABLE**

No consistent public capacity inventory for terminals, storage or crude pipelines was found, and the
work needed to build one would centre on export routing — which the scope boundary excludes. OSM has
zero pipeline route relations for Saudi Arabia, so the project's route-reconstruction method has
nothing to run on even before the scope question. Recommend the sector stay **uncovered** (excluded
and weights renormalised — never zero), with the UI saying "not modelled for Saudi Arabia: no
suitable public inventory, and out of scope".

---

## 5. Gas — split, as requested

### 5a. Gas processing — **INCOMPLETE**

- Inventory: EIA (Oct 2024) publishes an **estimated** capacity table for eight plants (2023);
  Aramco publishes aggregates and project-level capacities for new plants, not a per-plant census.
- Basis: EIA "estimated", raw-gas processing, Bcf/d; Aramco reports raw-gas *and* sales-gas
  capacities for projects, which are different quantities.
- Vintage/status: single EIA vintage; new plants commissioning through 2027 per Aramco.
- Verdict: a denominator could be assembled, but on an estimated basis and only one vintage —
  INCOMPLETE. Gas processing is not in the Russian scored sector set either (`gas: uncovered`).

### 5b. Gas pipelines — **UNSUITABLE**

No public capacity inventory; OSM has 119 gas-pipeline ways and no route relations. Same scope
reasoning as oil logistics. Recommend no Saudi gas-pipeline layer, analytic or context.

### 5c. Gas storage — **NOT YET RESEARCHED**

Not investigated this session. Saudi Arabia is not known to have a gas storage system comparable to
Russia's; any storage would be a small number of Aramco projects, which is not an inventory.

### 5d. LNG — **NOT APPLICABLE (domestically)**

EIA: Saudi Arabia "meets all of its natural gas consumption with domestic production" (2024 brief)
and "does not import or export natural gas" (2021 brief). There are no in-Kingdom LNG import or
export terminals in any source read. Aramco's LNG role is **international**: offtake and trading
agreements and equity stakes abroad (Aramco 2025 Annual Report: a 20-year SPA with NextDecade for
1.2 mmtpa from Rio Grande Train 4, a Commonwealth LNG offtake agreement, and "assessing LNG
investments internationally"). None of that is Saudi domestic infrastructure.

---

## 6. Coal — **NOT APPLICABLE**

EIA's 2022 energy overview table shows coal at **0.0 quad Btu** of production and consumption and
**0%** of electricity generation. No coal mines and no coal-fired generation appear in any source
read (WRI's Saudi rows contain no coal plant). This is a **sourced zero**, so it is NOT APPLICABLE,
not UNKNOWN. Caveat: EIA rounds to 0.1 quad, so minor industrial coal use, if any, is below its
precision; that does not create an energy-infrastructure sector to monitor.

---

## 7. Upstream — not a sector in the current taxonomy

Crude and petroleum liquids were **85% of Saudi primary energy production** in 2022 (EIA). The
Russia-derived taxonomy has no upstream sector, so the Saudi index would omit most of the country's
energy production by construction. The only public upstream capacity measure is national (Aramco's
Maximum Sustainable Capacity, 12.0 mmbpd at end-2025). A facility-level upstream inventory is **not
recommended** under the scope boundary. If an upstream dimension is wanted, it should be national
context only (JODI monthly production; Aramco quarterly totals), labelled as context.

---

## Russia-model assumptions that fail for Saudi Arabia

| Russia assumption | Saudi reality |
|---|---|
| A structured open-source strike table (Wikipedia) supplies events and a coverage benchmark | No equivalent compilation identified; **coverage ratio must read "unknown"** |
| Regional electricity facts can be placed into first-level regions | Official electricity statistics are by **4 SEC operating areas**, not the 13 regions |
| WRI GPPD is an acceptable (if stale) generation denominator | WRI Saudi rows end in 2016 and miss nearly all renewables — **worse** than Russia |
| Pipelines reconstructed from OSM route relations | **Zero** Saudi pipeline route relations in OSM; and out of scope anyway |
| Refining numerator from the event source's capacity column | Must come from the Aramco registry row (gross) to avoid the mixed-basis trap |
| `heating_season_months` (Oct–Apr) marks the stress season | Saudi demand peaks in **summer** (EIA: crude burn for power peaks Jul–Sep) — the heating flag is wrong, not merely irrelevant |
| Gas and coal "uncovered" is a temporary gap | Coal is **not applicable**; LNG is not applicable domestically; gas is partly unsuitable by scope |
| Sector taxonomy covers the main energy activity | Upstream (85% of primary production) is absent from the taxonomy |
| Recovery evidence accumulates from wire reports | Saudi restart statements rarely give durations; expect `kind=modelled` to dominate |
| Attribution confidence can be derived from publisher count | Attacks in the window are subject to claims by a party to a conflict and official non-confirmation; publisher count overstates certainty when outlets repeat one claim |

---

## Transparency limits, stated once

- Facility status and disruption are disclosed at the corporate-materiality threshold, without
  facility names (Aramco H1-2026 interim report).
- The regulator's and ministry's sites were unreachable from this machine; whether that is
  geo-restriction is not established.
- OPEC and Energy Institute sites refused scripted access; their figures are cited manually or not
  at all.
- Low reported incident counts for Saudi Arabia are a property of this environment and must be
  presented as "coverage unknown", never as low disruption.
