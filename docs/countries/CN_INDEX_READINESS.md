# China (CN) — index readiness

**Status: candidate assessment. Nothing here changes a published number, and no China index
exists.** Compiled 2026-10-30. Source details, access results and every figure's provenance are in
[CN_SOURCE_AUDIT.md](CN_SOURCE_AUDIT.md). This document answers one question per sector: could
this project compute an honest exposure share for China today, and if not, what is missing?

Classification used per sector:

- **READY:** a complete, single-basis, dated denominator exists and is acquirable.
- **EXPERIMENTAL:** a credible denominator exists, but needs acquisition, a crosswalk or a
  completeness check before any value can be published.
- **INCOMPLETE:** a partial denominator exists, with a known, unquantified gap.
- **UNSUITABLE:** there is no defensible open denominator, or the Russia scoring model does not
  transfer.

## Bottom line

**Country recommendation: CONTEXT_ONLY.** Do **not** publish a China composite ESDI.

Two sectors could reach **EXPERIMENTAL** with bounded work: **coal power** (GCPT) and **electric
generation** (GIPT). Both have unit-level, dated, province-tagged CC BY 4.0 inventories. **Coal
mine supply** is a weaker third (GCMT). Every other sector lacks a defensible open denominator. A
composite renormalised over two or three power and coal sectors would be called an
"energy-system" index while measuring a coal and power index. That is a labelling failure the
project's rules exist to prevent.

The binding constraint is **not** the denominators. It is incident coverage. The Russia corpus is
dominated by a reporting environment (a strike campaign, covered by many independent publishers)
that has no Chinese analogue. Chinese disruption is mostly technical, weather-driven or
administrative. It is reported by fewer independent outlets, often in Chinese only, sometimes
months later through official accident reports. Without a measured coverage ratio, any index value
is uninterpretable. That ratio is this project's own headline-weight requirement.

**Minimum work to move China from CONTEXT_ONLY to EXPERIMENTAL (power and coal only):**

1. A human acquires the GEM GCPT and GIPT release files through GEM's form. Record the **file's
   own** release stamp, because the landing page and the API disagree (July against January 2026
   for GCPT).
2. Build the denominator as a **census at date**, `installed_mw(t)`, from `Start year` and
   `Retired year`. That is the method `GENERATION_DENOMINATOR_AUDIT.md` prescribes for Russia, and
   for China it is not optional (see generation, below).
3. Reconcile the census against NBS year-end capacity by type, and publish the coverage ratio.
4. Run a coverage benchmark for incidents before scoring anything: the coverage-ratio requirement
   is part of the bar, not an extra. This audit found no Chinese equivalent of the Russian
   benchmark table, and whether one exists is for the incident lane to establish.
5. Settle the province join (`name_zh` crosswalk) and the scope of the Paracel Islands polygon
   (project-owner decision).

---

## Refining — **UNSUITABLE** → sector bottom line **INSUFFICIENT_EVIDENCE**

**Is there any complete, single-basis refinery registry for China? No.** None was found among open
sources, and the structure of the sector explains why one is unlikely to exist openly.

| Candidate | What it is | Why it fails as a denominator |
|---|---|---|
| English Wikipedia China section | 48 entries (one duplicated), 15 without capacity, bbl/d and t/a mixed | SOE-only; **no Shandong independents and no large private integrated refiners** (ZPC, Hengli, Shenghong, Yulong absent by name); vintage unknown |
| EIA brief | 19 million b/d total capacity (2024), citing Reuters; 20 million b/d government cap | a national aggregate, not a registry; basis unstated; secondary |
| NBS crude processing | 737.59 Mt in 2025 (enterprises above designated size) | **throughput, not capacity**; national monthly; provincial annual only as JPG |
| SOE annual reports | company-wide processing capacity | plant-level capacity is not systematically tabulated (NOT VERIFIED for 2025 reports); sites partly unreachable |
| OSM | `industrial=oil_refinery`: **1 feature** in China | none |
| GEM | no refinery tracker in the GEM catalog listing | none |

**The independent-refinery (地炼 / "teapot") problem.** The independent refiners, concentrated in
Shandong, are numerous. They are privately owned, partly consolidated, closed and replaced under
policy (EIA: 10 small refineries totalling 540,000 b/d shut in 2022 ahead of Yulong), and their
capacity is tracked mainly by commercial consultancies whose data is not open. Any open registry
assembled from SOE disclosures plus press would therefore be **complete for the state sector and
systematically incomplete for exactly the segment with the most churn**. That bias is not random.
It is correlated with ownership and province (Shandong), so it would distort regional exposure,
not merely add noise.

**The basis problem, already learned on Russia.** Chinese policy states caps in tonnes per year.
EIA states capacity in b/d. Plant figures in press mix CDU nameplate, "crude processing capacity"
(原油加工能力) and integrated-complex capacity. `REFINERY_CAPACITY_BASIS.md` shows what a 5.7%
basis mismatch did to a 35-plant registry. A China registry would start with a larger mismatch,
over far more plants.

**Incident coverage:** Fires and explosions at large SOE and private complexes are reported by
Chinese media and sometimes by Reuters and Bloomberg. Run cuts are reported by trade press, much of
it paywalled. Independent-refinery outages are mostly visible only in commercial data.
**Restoration evidence:** Rarely published. Companies seldom announce restarts.

**Russia assumptions that fail:**
- **The 150-day modelled reconstitution horizon** was calibrated to strike damage on CDUs. Chinese
  refinery disruptions are predominantly technical (fire, unit trip) or economic (run cuts). For
  those, the horizon is unknown, ranging from days to a turnaround cycle. A 150-day fallback would
  systematically over-score them.
- **The cause weights** (`technical: 0.8`) were tuned for an index whose mass is kinetic. If they
  were applied to a corpus that is almost all technical and economic, `unknown: 0.7` and
  `technical: 0.8` would carry the whole sector. That is a regime the weights were never examined
  for.
- A **run cut is not a capacity disruption.** The current taxonomy has no economic or
  market-curtailment cause. The Russian `sanctions` workaround (see the Sudzha precedent) should
  not be stretched to cover it.

**Minimum to move up one level (to CONTEXT_ONLY with a sized national figure):** Adopt a single
declared basis, either nameplate CDU in t/a or EIA b/d, for a **national** figure only, and show
it as context. **To reach EXPERIMENTAL,** an open, sourced, single-basis plant registry must
reconcile to ≥90% of an official national total on the same basis, *and* independents must be
covered. No path to that from open sources was identified.

---

## Electric generation — **EXPERIMENTAL** (after GIPT acquisition) → sector bottom line **CONTEXT_ONLY** today

**Denominator available:**

| | GEM GIPT | NBS / NEA | WRI GPPD (rejected) |
|---|---|---|---|
| Granularity | unit | national by type | plant |
| Basis / unit | MW, AC for solar | 10,000 kW; solar AC/DC not stated | MW |
| Vintage | September 2026 release (landing page) | end-2025: 3,891.34 GW; end-Sep-2026: 4.13 billion kW (NEA) | ≤2018 |
| Status | yes | n/a | **none** |
| Start / retire year | **yes / yes** | n/a | start for 1,086 of 4,235; no retirement |
| Province | yes (subnational field) | **no open provincial capacity table found** | — |
| Missing | distributed solar <1 MW (national aggregate only) | — | 64% of capacity, 95% of solar |

**Why the census-at-date is mandatory for China, not just better.** China's installed capacity
rose 16.1% in 2025 (NBS) and is up 11.2% y/y to September 2026 (NEA). Solar alone grew 35.4% in
2025. Freezing a denominator at any date makes the share drift by double digits a year. As an
illustration of the arithmetic only, not a measured series: at 16% a year, a base four years
newer is 1.16⁴ ≈ 1.8× larger, so an early event's share would be understated by about 45%. The
Russian denominator
was stale by a few percent. China's would be stale by a growth rate.

**Basis traps:**
- **Distributed solar.** NEA's 1,201.73 GW includes distributed PV. GEM tracks ≥1 MW per facility
  and distributed only as a national aggregate. Distributed capacity has no province in GEM, and
  open data does not locate it. It must be **excluded from the provincial denominator and
  disclosed**, never apportioned by guess.
- **AC against DC.** GEM solar is AC. Chinese solar capacity is commonly understood to be DC
  (NOT VERIFIED). The numerator and denominator must both come from GEM.
- **Scope.** NBS monthly generation covers enterprises above designated size. The Communiqué covers
  the whole economy (about 8% apart in 2025). Generation is never the denominator here, but if it
  is shown as context, its scope must be stated.

**Incident coverage:** Unit trips are rarely reported individually. Visible events are mostly
**system-level**: weather-driven shortfalls (drought cutting hydro output, heat-wave demand), and
administrative rationing (有序用电 [orderly power use]). These are **not facility disruptions** and
cannot be expressed as MW offline at a plant. A capacity-share index with such a corpus would show
near-zero exposure precisely when the system is most stressed. That is the "measured, nothing
wrong" false zero the project forbids.

**Restoration evidence:** Sparse at unit level. System-level restoration (an end to rationing) is
announced by provincial authorities and grid companies.

**Russia assumptions that fail:** Decay was calibrated on struck plants. A drought-driven hydro
shortfall is not a damaged asset with a reconstitution horizon, and `power_plant_hydro: 400` days
is meaningless for it.

**Minimum to move up:** The GIPT acquisition, census-at-date and NBS reconciliation steps listed
under the bottom line, and an explicit **out-of-model** label for system-level shortfalls, shown
separately and never scored as capacity.

---

## Transmission — **UNSUITABLE** → sector bottom line **CONTEXT_ONLY**

**Denominator:** None. Russia also has none, and uses an event-burden proxy. Official line length
and substation capacity by voltage are reportedly published by CEC, which was unreachable. OSM
counts at ≥500 kV are 21,954 line ways and 1,714 substation ways, with completeness unknown and
mapping legally restricted.

**The Russia assumption that fails, unambiguously: saturation at 8 concurrent weighted events.**
That constant was chosen as "fully exposed" for a regional grid under a strike campaign. In China,
the voltage-weight table also lacks the UHV classes (±800 kV DC, 1000 kV AC, ±1100 kV DC); they
fall to `default: 1.0`, below 500 kV. Eight events against a national grid of this size is not a
calibrated saturation. It is an arbitrary number with a different meaning. **Do not transfer it.**

**Incident coverage:** Grid faults are reported mainly as weather damage (typhoon, ice storm) at
city or provincial level, without asset identity.

**Restoration evidence:** Grid companies announce restoration of customer supply. That is restored
*service*, not reconstituted *assets*. The project already distinguishes the two.

**Minimum to move up:** An open, dated, voltage-class inventory with a known completeness ratio,
**and** an independently justified saturation constant. Neither exists. Keep this sector as context.

---

## Oil logistics — **INCOMPLETE** → **CONTEXT_ONLY**

**Denominator:** GEM GOIT for crude and product pipelines, with the provisional-release caveats
already documented for Russia. **No open crude or product terminal registry** was found. EIA gives
no terminal inventory. Strategic and commercial storage is **out of scope** (see the audit).

**Incident coverage:** Pipeline leaks and explosions are occasionally reported. Port disruptions
are mainly weather-related (typhoon closures), which are not asset damage.

**Russia assumptions that fail:** `oil_terminal: 100` and `pipeline_oil: 70` days were calibrated
on strike damage. Typhoon port closures last days, and scoring them with a strike horizon would
grossly over-weight them.

**Minimum to move up:** An acquired, release-stamped GOIT file and a completeness check against an
official pipeline-length figure (NOT located in this pass). Terminals stay context-only.

---

## Gas — assessed separately, as instructed

| Sub-sector | Denominator | Class | Notes |
|---|---|---|---|
| **Production** | NBS national output (262.06 bcm, 2025); provincial annual as JPG only; field registry: GEM GOGET (NOT audited in this pass) | **INCOMPLETE** | Output is a flow, not capacity. A field-level capacity basis is not published openly. |
| **Processing** | none found | **UNSUITABLE** | No open plant registry. OSM was not probed for China; it failed for Russia. |
| **Pipelines** | GEM GGIT (provisional, attributes only) | **EXPERIMENTAL** at best | Same caveats as Russia. `topology_only` route-accuracy rows cannot carry geometry. |
| **LNG import** | GEM GGIT terminals (China fields NOT VERIFIED); EIA aggregate: 29 terminals, 6.2 Tcf capacity (2023, citing IGU) | **INCOMPLETE** → plausible EXPERIMENTAL | The most tractable gas sub-sector: a small set of large, named terminals with published nameplate capacity. Confirm the GGIT terminal fields and the status/start-year columns. |
| **Storage** | EIA aggregate only (0.94 Tcf underground) | **UNSUITABLE** (and out of scope at facility level) | Not pursued. National aggregates are enough for context. |

**Incident coverage:** Pipeline explosions do get reported. Supply curtailment to industry in
winter shortages is administrative, not asset damage. **Restoration evidence:** sparse.

**Russia assumptions that fail:** `lng_terminal: 300` days assumes strike damage to liquefaction.
China's terminals are **regasification**, a different process with a different repair profile.
The horizon does not transfer.

**Gas sector bottom line: CONTEXT_ONLY**, with LNG import the only candidate for EXPERIMENTAL.

---

## Coal — assessed separately, as instructed

### Coal mine supply — **EXPERIMENTAL** (denominator) → sector bottom line **CONTEXT_ONLY** today

**Denominator:** GEM GCMT (May 2026 release per API). Fields: `status`, `capacity_mtpa`,
`production_mtpa` with its year, `opening_year`, `closing_year` and local-language names.
**There is no province field.** Province must be derived from coordinates, by the stdlib
point-in-polygon already in the pipeline, and labelled as derived. Coordinates are then
discarded. **Two capacity bases** (design capacity and production) must not be mixed. Choose
`capacity_mtpa` for both sides. Completeness against NBS raw-coal output (4.85 billion t, 2025) is
unmeasured. Thousands of small mines may fall below GEM's threshold.

**Incident coverage:** The best of any Chinese sector, for an unusual reason. Coal-mine accidents
have an **official** reporting channel: NMSA 事故案例 [accident cases] and MEM investigation
reports. They are Chinese only, published with a lag (cases published 2025-12-03 and identified
only by day-month codes), and limited to accidents above a severity threshold. The official
record of accidents and fatalities has historically been questioned, and concealment of mine
accidents (瞒报) is a recognised offence category in Chinese law. That is an inference about
under-reporting, not a measurement, and was NOT VERIFIED against a source in this pass.

**Restoration evidence:** Suspension and resumption orders (停产整顿 / 复产验收) are the natural
restoration evidence, and are issued by provincial mine-safety authorities.

**Russia assumptions that fail:**
- The dominant post-accident outage is an **administrative suspension**, often extended to
  *other* mines in the same city or province for inspection. That is a regional supply effect
  with no damaged asset. The facility decay model cannot represent it, and recording the
  suspended mines as "disrupted" would claim damage that did not happen.
- `coal_mine: 150` days is a strike-era assumption with no Chinese evidence behind it.

**Minimum to move up:** Acquire GCMT, derive and label province, measure completeness against NBS
provincial output (hand-transcribed from the yearbook's 9-19 image, with the transcription
recorded), and add an `administrative_suspension` concept distinct from damage. The last is a
taxonomy change, so it is the project owner's decision.

### Coal power — **EXPERIMENTAL** → nearest to READY of any China sector

**Denominator:** GEM GCPT (unit-level, ≥30 MW, `Status`, `Capacity (MW)`, `Start year`,
`Retired year`, `Subnational unit (province, state)`, local-script names, SOE status). It is the
only China inventory with every field the census-at-date needs and an explicit province. It
cross-checks against NBS thermal capacity (1,539.04 GW at end-2025, which includes gas, oil and
biomass, so coal will be lower by construction).

**Why EXPERIMENTAL and not READY:** The file must be acquired by a human, with its release stamp
read from the file (the GEM page and API disagree). The cross-check with NBS needs a coal-only
official figure, which the Communiqué does not separate. And incidents are scarce: unit trips are
not reported.

**Incident coverage and restoration:** Thin. Most visible events are fuel-supply or system-level,
not unit damage.

**Russia assumptions that fail:** As for generation. `power_plant_thermal: 200` days is
strike-calibrated.

**Coal sector bottom line: CONTEXT_ONLY** today. Coal power becomes **EXPERIMENTAL** once GCPT is
acquired and reconciled. Coal mines become **EXPERIMENTAL** only with the administrative-suspension
concept, because without it the sector's dominant disruption type is unrepresentable.

---

## Summary

| Sector | Denominator class | Sector bottom line | Main blocker |
|---|---|---|---|
| Refining | UNSUITABLE | **INSUFFICIENT_EVIDENCE** | no open single-basis registry; independents uncovered |
| Electric generation | EXPERIMENTAL (post-GIPT) | CONTEXT_ONLY | acquisition; census-at-date; distributed solar; system-level events |
| Transmission | UNSUITABLE | CONTEXT_ONLY | no inventory; saturation-8 does not transfer |
| Oil logistics | INCOMPLETE | CONTEXT_ONLY | no terminal registry; strike horizons |
| Gas: production | INCOMPLETE | CONTEXT_ONLY | flow, not capacity |
| Gas: processing | UNSUITABLE | CONTEXT_ONLY | no registry |
| Gas: pipelines | EXPERIMENTAL at best | CONTEXT_ONLY | provisional GGIT |
| Gas: LNG import | INCOMPLETE → EXPERIMENTAL | CONTEXT_ONLY | GGIT terminal fields unverified |
| Gas: storage | UNSUITABLE / out of scope | CONTEXT_ONLY | — |
| Coal: mines | EXPERIMENTAL | CONTEXT_ONLY | no province field; administrative suspensions |
| Coal: power | EXPERIMENTAL | CONTEXT_ONLY → EXPERIMENTAL | acquisition, release stamp |
| **Country** | | **CONTEXT_ONLY** | incident coverage, not denominators |

## Model assumptions that do not transfer (consolidated)

1. **Modelled reconstitution horizons** (`sector_fallback_horizon_days`) are strike-calibrated.
   China's dominant event types (technical, weather, administrative, economic) have no evidence
   base for them. Every China score would rest on `kind=modelled`, the input the methodology
   itself calls "still the weakest".
2. **Cause weights** were never examined for a corpus with no kinetic mass. `unknown: 0.7` would
   become a dominant term.
3. **Transmission saturation 8 and the voltage-weight table** (no UHV classes) are Russia-specific.
4. **Occurrence confidence from distinct-publisher counts.** In China, many outlets reprint the
   same Xinhua or official text. Counting reprints as independent publishers would inflate
   `confirmed`. A China adapter must deduplicate by originating outlet, not by URL domain.
5. **A static denominator** is tolerable at Russia's growth rate. At China's (+16% capacity in
   2025) it is a first-order error.
6. **The taxonomy lacks** an administrative-suspension and an economic-curtailment cause. China's
   most common disruption types would be forced into `unknown` or mis-filed as `sanctions`.
