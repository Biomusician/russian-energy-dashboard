# Global methodology — what of the ESDI can travel

Written 2026-10-30 by the cross-country methodology lane. **Nothing in this document changes a
published number, the scoring code or `methodology/scoring.json`.** It is an analysis for the
project owner, in the same status as [REFINERY_CAPACITY_BASIS.md](REFINERY_CAPACITY_BASIS.md):
proposed, not deployed.

Scope: the project is adding **China, United States, Saudi Arabia, Canada and India** to a
dashboard whose headline index (ESDI) was designed for **one** theatre — Belarus, western Russia,
the Siberian Federal District and occupied Crimea, under a sustained long-range strike campaign.
Separate country lanes are producing per-country readiness documents; this is the cross-cutting
view and does not replace them.

Live figures are in [CURRENT_STATE.md](CURRENT_STATE.md). Figures quoted here are **dated
findings from the 2026-10-30 build** and are deliberately not kept current. General-knowledge
figures about other countries' energy systems are marked *(approx.)* — they are orders of
magnitude for argument, not inputs, and each must be confirmed by the relevant country lane
before it appears anywhere a reader can see it.

The governing rules this document is held to, verbatim from the project:

> Never present an estimate as an observation. If the data does not support a number, emit null
> and make the UI say why. OBSERVATION > SOURCED ESTIMATE > TRANSPARENT PROXY > MODEL > UNKNOWN.
> UNKNOWN ≠ ZERO. UNKNOWN ≠ NOT APPLICABLE. REPORTING DENSITY ≠ REAL-WORLD DISRUPTION RATE.
> CROSS-COUNTRY EVENT COUNT ≠ CROSS-COUNTRY DISRUPTION SEVERITY.

---

## 0. The short version

| # | Question | Recommendation |
|---|---|---|
| 1 | Sector weights | They are an **unvalidated judgement set once at the MVP**, unchanged since except for one split, and fit neither Russia's own energy mix nor anyone else's. **Keep the ESDI Russia-only (A).** New countries get **per-sector measures with no composite** until the owner approves a weight-*derivation rule* (the route to D). Do not do B. It looks neutral but is not: renormalisation gives each country a different set of effective weights anyway. |
| 2 | Decay outside a conflict | **No modelled decay in any new-country score.** Where outage duration is reported, use a **step function**: impaired until the observed restoration date, then closed. For an open event, hold it at full impairment only inside a declared confirmation window, then move it to **"status unknown — not scored"** and count it in a disclosed coverage ratio. Grid outages lasting hours to days get **event tracking only**. |
| 3 | Transmission proxy | **Not portable.** Saturation-8 is calibrated to a handful of struck substations. Any country that systematically reports grid events pins it at 100. A defensible measure is a **consequence measure normalised by system size** (customer-hours interrupted per customer served, or load shed as a share of regional load). That exists for the US and partly for India, and nowhere else in this set. |
| 4 | Denominators | Matrix in §4. The US is the only country READY across most sectors. Seven classes of **same-label, different-measurement** traps are listed. The worst is using the refining base as the oil-logistics proxy for a crude exporter: in Saudi Arabia a single export terminal would exceed 100% of that base. |
| 5 | Inclusion threshold | It produces non-comparable counts by construction: absolute thresholds against systems that differ by 30×, and mandatory-reporting regimes against media-only ones. **The existing Russia corpus does not pass it.** At most 34 of 184 events (18%) carry any sourced operational effect or recovery record. Fix: tag every event with `inclusion_basis` and the criterion it met; add normalised severity fields and duration floors; group events into episodes; **never filter Russia by it**. |
| 6 | Cross-country comparison | **Comparing disruption across countries is not defensible now.** Energy-system context, freshness, readiness states, evidence coverage and reporting environment may be compared. Event counts and scores may not. Exact UI wording is in §6. |
| 7 | Readiness states | Six testable **sector** states (SCORED, EXPERIMENTAL, CONTEXT_ONLY, INSUFFICIENT_EVIDENCE, NOT_APPLICABLE, NOT_YET_RESEARCHED), plus a **country** onboarding gate and a separate, stricter **composite** gate. These map onto the project's three absences. |

---

## 1. Where do the sector weights come from?

### 1.1 What the record shows

| Where | What it says |
|---|---|
| `methodology/scoring.json` → `sector_weights._comment` | "A judgement call about systemic importance, not a measured quantity. Sums to 1.0. Iteration 3 split the old electric_power 0.30 into generation 0.20 + transmission 0.10." |
| `docs/METHODOLOGY.md` §2 "Composite" | "These are a judgement about systemic importance, not a measured quantity." |
| `docs/MVP_REVIEW.md` l.112–113 | "A judgement about systemic importance. Defensible, unvalidated." |
| `docs/ITERATION_1_REVIEW.md` l.131 | Listed as an open assumption: "Sector weights (unvalidated judgement)." |
| `docs/ITERATION_4_REVIEW.md`, `ITERATION_5_REVIEW.md` | "Sector weights were **not** retuned." |
| `git log -p -- methodology/scoring.json` | Introduced in the MVP commit `b67799b` (2026-08-26) as refining 0.35 / electric_power 0.30 / oil_logistics 0.20 / gas 0.10 / coal 0.05. **The only change since is the iteration-3 split** (`c68cabf`) of electric 0.30 into generation 0.20 and transmission 0.10. No commit message, review or comment gives a derivation for any number. |

**Finding: the weights have no recorded derivation.** No source, formula or data series stands
behind them. They are a single analyst prior, entered once and preserved for continuity.

### 1.2 Do they track anything measurable?

Three candidates, tested against the Russia case they were built for:

1. **Russia's domestic energy mix.** They do not track it. Russia's primary energy supply is
   dominated by natural gas *(approx. half)*, with oil about a fifth and coal about a tenth.
   The weights give oil 0.55 (refining 0.35 + oil logistics 0.20), gas 0.10 and coal 0.05.
   Weights built on domestic energy shares would have to make gas the heaviest sector.
2. **Economic value / export revenue.** They are **plausibly aligned** with it, since oil and
   products dominate Russian export and budget revenue. But no revenue or value-added series was
   consulted. This is the most charitable reading, and it is an interpretation.
3. **The strike campaign's target mix.** They are **loosely aligned** with it. In the 2026-10-30
   corpus, 154 of 184 events (84%) are oil-sector: 97 refinery, 44 oil terminal, 13 oil
   pipeline. 22 (12%) are electricity and 8 (4%) are gas, and there are no coal events. The
   weights give oil 0.55, electricity 0.30, gas 0.10 and coal 0.05. That is the same ordering
   but not proportional to it. Deriving weights from the target mix would also be circular: the
   attacker's choices would define what the index calls important.

**Conclusion:** the weights are an **analytical convenience for the Russia theatre**. They encode
"this is an oil-export economy under attack mostly on its oil system", not a general theory of
energy-system importance.

### 1.3 The weights actually in force are not the declared ones

`_composite_raw` (`pipeline/build_index.py`) divides by `Σ weights[s] for s in covered`. Gas and
coal are uncovered (`sector_basis`: `uncovered`), so the weights in force for Russia today are:

| Sector | declared | in force (÷ 0.85) |
|---|---|---|
| refining | 0.35 | **0.412** |
| electric_generation | 0.20 | **0.235** |
| oil_logistics | 0.20 | **0.235** |
| transmission | 0.10 | **0.118** |
| gas, coal | 0.15 | 0 (renormalised away, disclosed as `esdi_all_sectors`) |

This matters for portability. **"Apply the same weights" never yields the same weights.** Each
country's set of covered sectors differs (§4), so renormalisation gives each country a different
effective weight vector. Two examples, assuming the §4 readiness holds:

- **China** with refining INCOMPLETE and transmission UNSUITABLE: the only covered sectors are
  generation and perhaps coal. Generation's 0.20 becomes 0.80, or 1.0 if coal is not covered.
  The "ESDI" becomes a generation index.
- **Saudi Arabia** with no coal (NOT_APPLICABLE), transmission UNSUITABLE and the oil-logistics
  proxy invalid (§4.3): refining 0.35 and generation 0.20 renormalise to 0.64 / 0.36.

The same formula and declared weights therefore produce three different instruments.

### 1.4 The four options

**(A) Keep the ESDI Russia-only.**
- *Requires:* renaming nothing (it is already "Monitored-Area ESDI"). New countries get their
  own sector panels and no composite, and a test forbids a composite field on non-Russia country
  records until §7.3 is met.
- *Could mislead:* a reader may infer that Russia is "the only country with disruption" or "the
  most disrupted", because only Russia has a headline number. This is mitigated by the §6
  wording and by giving new countries visible per-sector cards in place of a blank.
- *Assessment:* the honest default. The ESDI's whole construction — exposure, strike-shaped
  decay, saturation-8 transmission, refining-base logistics proxy — is theatre-specific.

**(B) Apply the same generic weights, after justification.**
- *Requires:* a written argument that 0.35/0.20/0.10/0.20/0.10/0.05 represents systemic
  importance in China, the US, Saudi Arabia, Canada and India. No such argument is available:
  §1.2 shows they do not represent Russia's own energy mix. Coal at 0.05 for China and India,
  where coal is *(approx.)* more than half of primary energy and the main driver of their
  recent power-shortage episodes, cannot be defended.
- *Could mislead:* the reader would conclude the scores are comparable because "same
  methodology". They are not, for two reasons: renormalisation (§1.3), and inputs that differ in
  basis, threshold and reporting environment (§4–§5). False comparability is the worst possible
  outcome under this project's doctrine.
- *Assessment:* **reject.**

**(C) Country-specific scores, explicitly non-comparable.**
- *Requires:* a per-country weight rationale document, a sector readiness state per §7, its
  own recovery model per §2, and a hard UI/payload rule that no two country scores appear on one
  axis, in one table or in one sentence.
- *Could mislead:* labels erode. A number from 0 to 100 next to a country's name *will* be
  compared, whatever the caption says. Two country cards side by side are a ranking in practice.
  The weights would also be one analyst's prior per country, so five unvalidated priors replace
  one.
- *Assessment:* acceptable only **after** per-sector measures have run for long enough to show
  that a composite adds information. Even then it should take its weights from a rule (D),
  never from five independent judgements.

**(D) A new, globally comparable weighting framework.** *Not to be deployed without owner
approval.* What it would take:
1. **A defined construct.** For example: "the share of the country's final energy service that
   flows through this sector". It must be stated in one sentence and be measurable.
2. **One common source for it**, at one vintage: e.g. IEA World Energy Balances or the Energy
   Institute Statistical Review, applied by the same published formula to every country.
   Weights would then be country-specific numbers produced by **one identical rule**, and the
   *method* would be comparable even though the numbers differ.
3. **A weight for every sector, including uncovered ones.** The covered share
   (`Σ covered weights`) would be published as a first-class coverage figure. A composite whose
   covered share is below a floor (proposed 0.5) would not be published (§7.3).
4. **Common denominator bases, a common inclusion threshold and a common recovery model**
   (§2, §4, §5). Weight comparability is worthless if the sector scores underneath are
   measured differently.
5. **Retroactive application to Russia**, which **changes what the published ESDI means**. A
   rule built on energy shares would make gas Russia's heaviest sector, and gas is uncovered.
   Russia's composite would then rest on a minority of its weight.
6. **Validation:** a back-test showing the composite moves when known major disruptions occur
   (Winter Storm Uri; the 2019 Abqaiq attack; the July 2012 Indian grid collapse; Hurricane
   Harvey refinery shutdowns), and stays flat through periods that are known to be quiet.

Even a complete D gives **method comparability, not observation comparability**: the event
detection underneath still depends on each country's reporting environment (§5, §6).

> **RECOMMENDATION (1).** **A now**, with new countries shown as per-sector measures and no
> composite. **Reject B.** It presents false comparability and does not even preserve the
> weights (§1.3). Treat C as a later step that **must** take its weights from a D-type rule
> rather than from five separate judgements. Do not deploy D. If the owner wants to pursue it,
> the first deliverable is the one-sentence construct (D.1) and its effect on Russia's own
> published ESDI (D.5), computed as a sensitivity alongside the existing
> `esdi_all_sectors` / `esdi_excluding_transmission` counterfactuals.

---

## 2. Decay outside a conflict

### 2.1 What the current model does, mechanically

`build_index._weight_trace`:

```
value = confidence × cause × damage_severity × 0.5 ^ (days / half_life)
half_life = horizon / 3.3219            (recovery.effective_half_life)
```

`recovery.assess` chooses the horizon: observed full reconstitution or substantial restoration
(conf ≥ medium), then a sourced estimate (conf ≥ medium), then the **modelled sector fallback**
(`sector_fallback_horizon_days`: refinery 150, oil_terminal 100, pipelines 70, substation 100,
transmission_line 46, thermal 200, nuclear/hydro 400, LNG 300). Contributions below 0.01 are
dropped (`cutoff.min_contribution`).

Three properties of an exponential with horizon *H* drive everything below:

- **Area** (impairment-days contributed by one event, base 1): `h / ln 2 = H × 0.4343`. For a
  refinery that is **65 impairment-days**.
- **Shape**: impairment is 0.63 at day 30, 0.40 at day 60, 0.25 at day 90 and 0.10 at day 150.
- **Dropout**: an event with base *b* leaves the score at `h × log2(b / 0.01)`. A *probable*
  (0.75) refinery strike drops out at **about 281 days**.

In steady state, a sector's exposure is roughly *event rate × capacity share × base ×
0.4343 H*, which is **linear in H**. The published sweep
(`snapshot.recovery_horizon_sensitivity`, `pipeline/horizon_sensitivity.py`) confirms this
empirically. On the 2026-10-30 build it gives 3.53 at 0.5× H, 8.33 at 1×, 16.43 at 2×, an
elasticity of about 1. Of 53 classified live facilities, 52 decay on the modelled horizon and 1
on an estimate. **The Russia headline is, to first order, proportional to an unobserved
constant.**

### 2.2 Why the conflict assumptions do not transfer

The modelled horizons encode a specific world:
- **Repeated kinetic damage** to the same plant, often before the last repair is finished.
- **Almost no restoration reporting**, in a reporting environment that restricts operational
  disclosure.
- **Physical reconstitution** that includes sanctioned-equipment replacement.

Hurricanes, winter-storm grid emergencies, refinery fires, wildfire shut-ins and grid failures
differ on every one of these axes:
- Duration is **often reported**: operator restart announcements, BSEE daily shut-in
  statistics, EIA/ISO notices, NRC daily reactor status, EAGLE-I restoration curves, Grid-India
  disturbance reports.
- The damage is usually **one event**, not a campaign.
- Restoration is commonly **days to weeks**, not months.

Applying the modelled refinery horizon to a refinery that restarted after 10 days scores **65
impairment-days for an observed 10**, a 6.5× overstatement. At day 30 the refinery would still
show 0.63 impaired when it has been running for 20 days. That is an estimate presented as an
observation, the one thing the doctrine forbids.

### 2.3 A defect the "observed" path already has

Even the current *observed* path imposes the strike-campaign **shape**. An observed restoration
after *D* days becomes horizon *D*, so impairment is 0.32 at *D*/2 and 0.10 at *D*. The area is
0.4343 *D*, which is **43% of the observed outage**, followed by a tail after restoration. The
observation sets the timescale, but the curve between disruption and restoration is still
modelled. For an outage whose start and end are both reported, the honest representation is a
**step**: full impairment from the start date to the restoration date, then closed. This
matters little for Russia today (1 of 53 live facilities is observed-driven). It would matter a
great deal for any country where most durations are reported.

### 2.4 The candidate recovery models

| Model | What it does | Failure mode | Where it fits |
|---|---|---|---|
| **(i) No modelled decay; impaired until observed restoration** | Step at 1 × base until a restoration record, then closed | **Reporting asymmetry.** Outages are news and restarts often are not. If restarts are reported with probability *p*, a fraction 1−*p* of events never close. Live open events then grow without limit, at about (1−*p*) × event rate × elapsed time. The index ratchets upward and ends up measuring **how rarely restarts are reported**, not disruption. The bias also differs by country: small in the US (dense restart reporting), large in China or Saudi Arabia. A single rule therefore produces opposite biases in different places. | Never on its own. |
| **(ii) Observed-duration only** | Score only events with both a start and a reported end, as a step; ignore the rest | **Silent omission.** Every event still ongoing, or whose end was never reported, scores zero, so unknown is treated as zero. It also biases toward short, well-reported outages, and the current period always reads low because recent events have not ended yet. | Valid for **retrospective** statistics (duration distributions), not for a live score. |
| **(iii) Event-class horizons from a measured distribution** | Replace the modelled constants with the median (or full distribution) of observed durations for that class, as an explicit `kind=modelled_from_distribution` | **Survivorship bias.** The durations that get reported are disproportionately the short ones. The Russia corpus illustrates this: the observed refining median is 47 d (n ≥ 3, CURRENT_STATE) against a modelled 150 d, and the gap is uninterpretable because unreported long outages are missing from the sample. A distribution also cannot represent permanent closure: Hurricane Ida (2021) ended one Louisiana refinery's operations for good. It is still a model, only a calibrated one. | Usable as a **sensitivity**, and as a **cap** on how long an unconfirmed event is held (model iv), not as the decay curve. |
| **(iv) Step model with a confirmation window** *(proposed)* | Observed start and end gives a step. An open event is held at full impairment while its status was confirmed within a **class-specific window W**. After W without confirmation, its state becomes **`status_unknown`**: it leaves the score and is **counted in a disclosed ratio**, "share of tracked exposure whose current status is unknown", shown at the same visual weight as the score | The cut-off at W is a rule, and it must be declared and swept like every other parameter. It never invents a partial recovery; the event moves from "known impaired" to "unknown". | **Recommended** for capacity sectors in non-conflict countries. |
| **(v) Event tracking only, no exposure score** | List events with observed start, end, duration and consequence. No time-decayed exposure | Loses the "share of base impaired" view. | **Recommended for grid outages** and for any class whose typical duration is shorter than the timeline step. |

### 2.5 Why grid outages must be event-only

The scoring timeline samples weekly (`timeline.step_days: 7`). A step-function outage shorter
than 7 days is sampled **once or not at all**, depending only on which weekday it began. Most
storm-driven customer outages are restored within hours to a few days, so a weekly exposure
series of them is mostly noise from sampling phase. Event tracking with **customer-hours
interrupted** and **duration** (§3) is the correct instrument. Moving to daily sampling would
fix the aliasing but not the deeper point: a capacity *share* is the wrong unit for an areal
service outage.

### 2.6 Sizing W

W should come from the observed duration distribution for that class in that country: for
example, its 90th percentile once n ≥ 10 observed episodes, with a declared conservative default
until then. It must be published together with a sweep (0.5×, 1×, 2×), in the
`recovery_horizon_sensitivity` pattern. Since W only controls *when an event becomes unknown*,
the sweep moves points between "scored" and "status unknown" rather than inventing impairment.
That is a strictly better failure mode than (i) or the current modelled decay.

### 2.7 Russia

This section does **not** recommend changing the Russia model. The conflict reality (very
sparse restoration reporting and repeated re-strikes) is exactly where model (iv) would push most
of the corpus into `status_unknown` and empty the score. The current exponential with a
published sweep is a defensible, disclosed choice *for that theatre*. Two changes for Russia are
still worth owner consideration, and they change Russia's numbers, so they are owner decisions:
- the **step representation** for events whose start and end are both observed (§2.3);
- publishing the **status-unknown share** alongside the ESDI.

> **RECOMMENDATION (2).** In new-country scores, **no modelled decay**. Use **model (iv)**: an
> observed-duration step, open events held only inside a declared, swept confirmation window
> and then moved to `status_unknown` with a disclosed ratio, for capacity sectors (refining,
> generation, LNG and processing, production shut-ins). Use **model (v), event tracking only**,
> for grid and customer outages. Use measured distributions (iii) only to size W and as
> sensitivities. Never use model (i) on its own. Add the step representation for fully observed
> Russian events to the owner's decision list.

---

## 3. The transmission proxy

### 3.1 What the code does

`build_index._share` for `transmission` returns `voltage_weight / SATURATION_EVENTS` with
`saturation_events = 8.0`. `voltage_weight` comes from bands 750 kV = 2.0, 500 = 1.6, 330 = 1.3,
220 = 1.0, 110 = 0.7, default 1.0, assigned by `kv >= band`. Each disrupted transmission
facility contributes this share times its decayed facility weight (strongest incident wins, with
modelled horizons of 100 d for a substation and 46 d for a line). The national sector value is
`min(1, Σ) × 100`. So **eight concurrently live, fully weighted 220 kV events saturate the
sector at 100.** `_regional_intensity` uses the same constant per region.

The project already treats the measure as fragile:
- It is labelled a "burden", never "% of grid offline".
- It ships a saturation sweep (2.48–9.94 across constants 16→4 on the 2026-10-30 build).
- It publishes a concentration split (the top theatre is 54.9% of burden, across 2 regions).
- It carries four alternative models (A–D) and an ex-transmission counterfactual.
- The iteration-7 red team kept it only because "the honest fix is LABELLING not surgery".

### 3.2 Why it is not portable

1. **The saturation constant is calibrated to strike rarity.** Steady-state burden is about
   `event rate/day × base × 0.4343 × 100 d`. With confirmed events and weight 1, saturation is
   reached at about **0.18 events/day, ~67 qualifying events a year** (~90/yr at *probable*
   confidence). The US public OE-417 summaries routinely record more reportable events than
   that in a year *(approx.; the US lane to confirm)*. A US transmission "burden" would sit at
   100 permanently and say nothing, while China (no event-level public reporting) would sit near
   0. **The constant converts reporting density directly into the score**, the error the
   doctrine names.
2. **The unit of measurement does not exist outside a strike campaign.** Russia's events are
   *named struck facilities*. Storm and heat outages are *areal* (counties or service
   territories losing customers) and mostly on the **distribution** system, not transmission.
   Turning a customer outage into a "disrupted substation" would need exactly the proximity
   inference the inclusion threshold excludes.
3. **The decay horizons are physical-rebuild times** (100 d substation, 46 d line). Grid
   restoration after weather is measured in hours to days (§2.5).
4. **The voltage bands are Soviet-standard classes.** US (765/500/345/230/138 kV), Indian
   (765/400/220/132), Chinese (1000/±800 UHV/500/220) and Saudi (380/230/132) classes map onto
   them only by the `>=` rule. For example, 345 and 400 kV both become "330 = 1.3", and 1000 kV
   becomes "750 = 2.0". It works mechanically, but the weights were never justified even for
   Russia.
5. **Customer counts measure consequence, not the asset.** That is the right direction (see
   3.3), but it is a different quantity from a facility-event burden, and the two must never
   share a sector label.

### 3.3 What a defensible transmission measure needs

It needs a **consequence measure, normalised by system size, from systematic reporting of known
coverage**:

| Requirement | Why | Who has it |
|---|---|---|
| Event-level public reporting with a **regulatory obligation** (known inclusion rule) | Reporting density must be a property of the rule, not of media attention | **US**: OE-417 (obligation under 10 CFR 205.351: e.g. firm load shed > 100 MW; loss of service to > 50,000 customers for a stated duration — the duration differs between form versions, so confirm against the current form). **India**: Grid-India/RLDC grid-disturbance reports under the CEA Grid Standards. **Canada**: provincial only. **China, Saudi Arabia**: none public. |
| **Duration and magnitude** (customers or MW, start and end) | Customer-hours or MWh is the quantity that matters | **US**: EAGLE-I (ORNL, county customers-out at 15-min resolution). **India**: GD reports give load or generation loss. Others: partial. |
| **A denominator**: customers served, or regional load | Normalisation | **US**: EIA-861 customers by state. **India**: the GD categories are *already* normalised (GD-1 < 10% … GD-5 ≥ 40% of antecedent regional generation or load). Others: not systematically published. |
| **Cause field** | To separate weather, technical, attack and load-shed-for-shortage | OE-417 has one; GD reports describe cause; elsewhere it comes from media only. |

Candidate measures:
- **Customer-hours interrupted ÷ customers served**, per admin-1 region and month, i.e. an
  event-driven SAIDI contribution (US).
- **Firm load shed (MWh) ÷ energy served** (US, India where reported).
- **Count of operator emergencies by severity class** (EEA-3 in NERC areas; GD-3+ in India),
  reported **as a count within its own country only**.

None of these is comparable with Russia's event burden, and none should be combined with it.

> **RECOMMENDATION (3).** Do **not** port the saturation-8 event burden to any new country.
> For the **US**, build a grid-consequence measure (customer-hours per customer served,
> admin-1, EAGLE-I + EIA-861, with OE-417 as the event register) as **event tracking plus a
> normalised consequence series**, labelled with its own name, never "transmission burden",
> never in a composite at launch. **India**: EXPERIMENTAL, from GD/GI categories. **Canada**:
> INCOMPLETE (province by province). **China and Saudi Arabia**: INSUFFICIENT_EVIDENCE for any
> grid measure; list reported major events with a reporting-environment caveat.
> Safety note: any grid measure stays at admin-region aggregation. No substation-level incident
> location, and no inventory of intact grid nodes ranked by anything, per the scope boundary.

---

## 4. Denominators across countries

### 4.1 Readiness matrix (first pass)

States: **READY** (an official or authoritative source exists at the needed granularity, with
vintage); **EXPERIMENTAL** (one exists but its granularity, vintage or basis needs work);
**INCOMPLETE** (only partial or aggregate coverage, or no plant-level census); **UNSUITABLE**
(the ESDI's construct for this sector does not work in this country); **N/A** (the sector does
not exist). Russia is shown as the reference, as currently built. Every cell needs confirming by
the country lanes.

| Sector → / Country ↓ | Refining | Electric generation | Transmission / grid | Oil logistics | Gas | Coal (supply) | Upstream production *(not in taxonomy)* |
|---|---|---|---|---|---|---|---|
| **Russia (ref.)** | in use, mixed basis (strike-table numerator vs registry denominator, REFINERY_CAPACITY_BASIS.md); lower bound of national total | in use, WRI census frozen at 2018, no retirements (GENERATION_DENOMINATOR_AUDIT.md) | event burden, saturation 8 | refining base as **proxy** | uncovered (incommensurable units) | uncovered (no events) | not modelled |
| **United States** | **READY**: EIA *Refinery Capacity Report*, per-refinery operable **atmospheric crude distillation**, b/cd and b/sd, annual Jan-1 census (supports a census at each date) | **READY**: EIA-860 / 860M, generator-level nameplate **and** net summer / net winter, with operating and retirement dates (fixes the vintage problem Russia has) | **READY for a consequence measure** (OE-417, EAGLE-I, EIA-861); **UNSUITABLE** for event burden | **INCOMPLETE**: no national terminal-capacity census; pipeline capacity fragmentary | **EXPERIMENTAL** as separate sub-measures: LNG *export* liquefaction capacity (EIA), processing plant capacity (EIA-757), pipeline capacity | **READY**, production basis: EIA-7A / MSHA mine-level production | **READY**: EIA state production; BSEE daily Gulf shut-in statistics (*observed*, operator-reported) |
| **China** | **INCOMPLETE**: NBS publishes crude *throughput* (runs), not capacity; national capacity totals come from industry bodies; plant-level nameplate for independent "teapot" refiners is poorly documented and disputed | **EXPERIMENTAL**: NEA/CEC national and provincial installed capacity by fuel type (aggregate READY); no official plant-level census, so a numerator would have to come from third-party trackers, the same numerator/denominator basis split as Russia's refining | **UNSUITABLE**: no event-level public reporting; annual reliability statistics only | **INCOMPLETE** | **EXPERIMENTAL** sub-measures; LNG is *import* (regasification) | **EXPERIMENTAL**: NBS monthly raw-coal production (national and provincial); mine capacity from official approvals, with mixed vintage | **READY** (aggregate): NBS monthly |
| **Saudi Arabia** | **EXPERIMENTAL**: plant nameplates from Aramco and JV disclosures; Aramco reports **gross vs net (equity)** capacity *including international assets*, so only the **domestic gross CDU** basis is valid | **EXPERIMENTAL**: national utility / regulator statistics; plant level via third-party trackers; cogeneration with desalination | **UNSUITABLE**: no public event reporting | **UNSUITABLE as built**: refining-base proxy invalid for a crude exporter (§4.3); terminal capacities only as secondary-source estimates | **EXPERIMENTAL**: gas processing capacity (company disclosures); no LNG | **N/A** | **EXPERIMENTAL**: official production via JODI/OPEC; "maximum sustainable capacity" is a *declared*, not audited, figure |
| **Canada** | **EXPERIMENTAL**: per-refinery capacity lists (CER / NRCan / StatCan); confirm one official per-plant source with vintage | **EXPERIMENTAL**: StatCan installed capacity by type and province (annual, aggregate); plant level from provincial operators or third-party trackers | **INCOMPLETE**: provincial utility outage data; no national event register | **EXPERIMENTAL** for pipelines: CER pipeline profiles publish throughput and capacity at key points of CER-regulated lines; terminals INCOMPLETE | **EXPERIMENTAL**: processing (provincial regulators), LNG *export* (new) | **INCOMPLETE** | **READY**: provincial regulator production statistics. Wildfire shut-in volumes are often **analyst estimates**, and must keep `kind=estimated` |
| **India** | **READY**: PPAC refinery-wise installed capacity (MMTPA); PPAC also publishes refinery-wise **crude processed** monthly, a rare *observed throughput* series | **READY**: CEA monthly installed capacity by state, sector and fuel; CEA daily reports list units under forced outage with MW (*observed* outages) | **EXPERIMENTAL**: GD/GI categories from Grid-India/RLDC reports, normalised by regional load; no customer counts | **INCOMPLETE**: port POL capacity, pipelines via regulator | **EXPERIMENTAL**: LNG is *import* (regasification) capacity (PPAC) | **READY**, production basis: Ministry of Coal / CIL monthly | **READY** (aggregate): PPAC |

Two cells stand out because they offer what Russia never had: **India's PPAC monthly
refinery-wise throughput** and **CEA forced-outage reports**. These are observations of capacity
*actually unavailable*, at plant level. In those two cells India could support a **capacity-loss
observation**, which this project explicitly declined to estimate for Russia (METHODOLOGY §1).
That is a different construct from exposure. It should be built and labelled as a separate
measure, never blended into an exposure score.

### 4.2 Same label, different measurement

Each item below would let an identical sector label silently mean a different quantity across
countries. Every denominator must carry an explicit `basis` code, and a test must reject a
cross-country display of two values whose basis codes differ.

1. **Refining: crude distillation vs throughput vs total unit capacity.** EIA's basis is
   atmospheric CDU capacity. NBS publishes throughput (runs), which falls when plants are idle
   for any reason. Some corporate figures add secondary units. *Use CDU nameplate/operable
   capacity as the denominator everywhere. Throughput is an observation series, never a
   denominator.*
2. **Refining: barrels per calendar day vs per stream day.** Stream-day capacity is higher by
   several percent. *Use calendar-day.*
3. **Refining: gross vs equity-share, domestic vs global.** Aramco's "net" capacity is its
   equity share and its headline figures include overseas refineries. *Use physical domestic
   gross capacity. Ownership is irrelevant to exposure.*
4. **Refining: nameplate vs licensed or quota capacity** (Chinese independents); **eliminated
   capacity** still listed. *Flag and exclude unverifiable plants as unsized; never pad toward
   a national total (the Russia precedent: "an explicit lower bound").*
5. **Generation: nameplate vs net summer vs net winter vs derated, and firm vs variable.** EIA
   publishes all three. In China and India, nameplate is increasingly dominated by solar and
   wind with low capacity factors, so a 1 GW coal unit outage is a smaller *nameplate* share than
   its share of firm supply. *Declare the basis per country (proposed: nameplate, for
   consistency with Russia's WRI basis, with a firm-capacity sensitivity). Do not mix bases
   between numerator and denominator, the exact defect REFINERY_CAPACITY_BASIS.md found for
   Russian refining.* Captive and industrial generation (large in India), behind-the-meter
   solar and desalination cogeneration (Saudi Arabia) sit inside some national totals and
   outside others.
6. **Grid: customers vs consumers vs people.** A US "customer" is a metered account (~2.5 people
   per residential account), Indian statistics count "consumers" (connections), China publishes
   neither at event level, and media in all five report "people" or "households" loosely. *Never
   convert between them. Store the unit reported.*
7. **Oil logistics: export vs import terminals; crude vs products.** The `oil_terminal` class
   holds both. A Russian Baltic crude-export terminal and an Indian west-coast crude-import
   terminal perform opposite functions.
8. **Gas: LNG liquefaction (export) vs regasification (import).** The taxonomy has one
   `lng_terminal` class with one modelled horizon of 300 d, set for Russian *export* plants.
   China and India have *import* terminals, and US/Canada/Russia have *export* plants. A
   liquefaction train outage and a regas outage are different events with different system
   consequences. *Split the class before any non-Russian gas data is scored.*
9. **Coal: mine supply vs coal-fired generation.** The project already separates these
   (METHODOLOGY §9a: coal-fired generation sits in electric generation, `coal` = mines +
   terminals). Keep it that way. For China and India the dominant coal disruption mechanism is a
   **supply shortfall causing generation curtailment**. The event belongs to generation, and the
   cause is coal supply.
10. **Units and conversion.** `1 bbl/d = 49.6 t/yr` (0.136 t/bbl, METHODOLOGY §3) suits a medium
    crude. It is wrong by several percent for Arab Light and heavier still for Canadian bitumen
    blends. *Keep native units per country. Never convert across countries to sum or compare.*

### 4.3 The oil-logistics proxy breaks for exporters

`_denominators` sets `nat["oil_logistics"] = refinery_total_mtpa`, i.e. "the volume the
logistics chain exists to move". For Russia, export volume and refining runs are of a similar
order, so the proxy is crude but not absurd. For a **crude exporter** the logistics chain moves
far more than the refineries process: Saudi Arabia's largest export terminal alone *(approx.)*
handles more crude than the whole domestic refining base. Under `_share`, that single terminal
would be more than 100% of the denominator and saturate the sector by itself. Canada has the
same structure, with pipeline exports well above domestic refining runs. **The proxy must not
be applied outside Russia.** Use pipeline or terminal throughput capacity where published (CER
for Canada), otherwise INCOMPLETE.

### 4.4 A missing sector: upstream production

Threshold criterion (7) ("production shut in at reported material volume") and three of the
five new countries' signature disruptions — Gulf of Mexico hurricane shut-ins, the 2019 Abqaiq
attack, Alberta wildfire shut-ins — have **no sector in the taxonomy** (`SECTOR_OF_CLASS` has no
upstream class). Adding one is a taxonomy and scoring decision. Its natural denominator is
*observed production* (EIA, provincial regulators, NBS, PPAC), which is a flow rather than a
capacity. Saudi Arabia's "capacity" is a declared figure. Until the owner decides, production
shut-ins can be **tracked as events, not scored**.

> **RECOMMENDATION (4).** Adopt the matrix as the starting hypothesis for the country lanes.
> Carry an explicit `basis` code on every denominator, and forbid cross-country display of
> unlike bases. **Forbid the refining-base oil-logistics proxy outside Russia.** Split
> `lng_terminal` into liquefaction and regasification before scoring any non-Russian gas.
> Treat upstream production as a new sector for owner decision, tracked-not-scored meanwhile.
> Build India's observed-throughput and forced-outage series as a **separately named
> capacity-unavailable observation**, never merged into exposure.

---

## 5. The inclusion threshold

The proposed MAJOR ENERGY INFRASTRUCTURE DISRUPTION standard: (1) refinery/gas-processing/LNG
shutdown or material throughput cut with reported effect; (2) export/import terminal
suspension; (3) trunk pipeline shutdown or force majeure; (4) a plant of ≥~500 MW forced offline
with reported effect, or a shortfall forcing rotating outages; (5) a grid event with ≥~100,000
customers lost, or an operator emergency; (6) a coal-mine event materially cutting supply;
(7) production shut in at reported material volume. Exclusions: maintenance, minor trips, price
events, policy/sanctions, proximity inferences.

### 5.1 Red-team: where it produces non-comparable counts

1. **Absolute thresholds against systems that differ by more than 30×.** 500 MW is *(approx.)*
   ~0.04% of US installed capacity, ~0.015% of China's, ~0.1% of India's, ~0.3% of Canada's and
   ~0.5% of Saudi Arabia's. 100,000 customers is ~0.06% of US accounts and roughly 1% of Saudi
   accounts. The same threshold admits trivial events in large systems and only system-scale
   events in small ones.
2. **"Forced offline" without a duration floor includes routine trips.** Large thermal and
   nuclear units of ≥500 MW trip routinely, and the US publishes it daily (NRC reactor status).
   Criterion (4) would admit dozens of US events a year, and essentially no Chinese or Saudi
   ones, for identical physical behaviour. "Minor trips" is excluded in words but not defined.
3. **"With reported effect" measures the disclosure regime.** Mandatory regulatory reporting
   exists in the US (OE-417, NRC, BSEE, EIA) and partly in India (Grid-India, CEA). Corporate
   disclosure dominates in Saudi Arabia, media in China, and in Russia a state that restricts
   operational disclosure. The *same physical event* passes in one regime and fails in another.
4. **Customer outages are mostly weather and distribution.** Criterion (5) will make US counts
   dominated by thunderstorms and nor'easters. That is real disruption, but it is not
   commensurable with a refinery shutdown, and it would make the US the "most disrupted" country
   by count.
5. **One hazard, many qualifying events.** A Gulf hurricane yields refinery shutdowns, terminal
   closures, production shut-ins and grid outages, perhaps 10–30 qualifying records from one
   cause. A single Russian strike night yields several, which the project already handles with
   `episode_id`. Counting records rather than episodes inflates hazard-prone regions.
6. **The cause exclusions conflict with the existing scoring.** `cause_weights` includes
   `sanctions: 0.6` and `maintenance: 0.15`, and the Russia corpus contains one
   sanctions-caused event. The new standard excludes both. There is also **no cause value for
   weather or natural hazard** (`taxonomy.causes`: kinetic_strike, sabotage, cyber, technical,
   sanctions, maintenance, unknown), so a hurricane falls to `unknown` = 0.7, an unexamined
   30% discount on the commonest cause in four of the five new countries.
7. **Shortfalls driven by price or policy.** China's 2021 power rationing and India's 2022 coal
   shortage had price, tariff and policy drivers but forced rotating outages, which meets
   criterion (4). The "price events" exclusion needs to read "price *movements* are excluded;
   physical shortfalls are included whatever their cause", and the cause should be recorded.
8. **"Material" is undefined** in (1), (6) and (7).
9. **Safety-inspection shutdowns** (common after Chinese mine accidents) are regulatory and
   policy-like, yet cut supply materially. Criterion (6) needs a ruling.

### 5.2 Does the existing Russia corpus pass it?

**No. The Russia corpus is a different event definition.** Inclusion there is *occurrence*: the
facility appears in the Wikipedia strike table, or in curated, sourced strike reporting. The
2026-10-30 corpus has 184 events: 180 `kinetic_strike`, 3 `technical`, 1 `sanctions`. Of these:
- **0** carry a quantified capacity effect (`capacity_affected_*` all null; METHODOLOGY §1).
- **15** have a sourced operational effect in `data/curated/effects.csv` (production halt,
  throughput reduction, export interruption, power outage, fuel shortage).
- **26** have a recovery record, which implies an outage occurred.
- Their union is **at most 34 events, 18%**. Adding `status` degraded/damaged gives 41 (22%).

The other ~80% are reported strikes **without a reported effect**. They would fail criteria
(1)–(4) as written. Some would also trip the "proximity inference" exclusion (drone debris or a
fire *near* a refinery). The sanctions event would be excluded outright.

Filtering Russia by this threshold would be wrong: in a disclosure-restricted conflict, "no
reported effect" is far more likely to mean "not reported" than "no effect". It would turn a
reporting artefact into a large drop in the published index. The two corpora have to be
**labelled as different kinds**, not reconciled by deletion.

### 5.3 Proposed fixes

1. **`inclusion_basis` on every event**: `occurrence` (reported attack or incident at a
   facility, Russia) or `effect` (reported operational consequence, new countries).
   `criterion_met` records which of (1)–(7) was met. These are display and audit fields, never
   score multipliers. Events of different bases are never counted together.
2. **Severity normalisation fields, mandatory for any comparative display**:
   `pct_of_national_base` (MW, CDU or production), `pct_of_customers_served` and
   `pct_of_regional_load`, each null with a reason when no denominator exists. Inclusion stays
   absolute (it is a monitoring rule), but **no cross-country view may use an un-normalised
   field**.
3. **Duration floors** *(proposed values, owner to set)*: generation ≥ 72 h forced outage, **or**
   any duration if it caused load shedding or an operator emergency. Refinery, processing or LNG:
   ≥ 72 h, **or** ≥ 25% of plant crude capacity for ≥ 24 h. Customer outages: ≥ 100,000
   customers **and** ≥ 1 h (aligned with OE-417's customer criterion). These define "minor trip"
   and "material" (5.1 items 2 and 8).
4. **Episodes, not records**: one hazard or one attack wave is one `episode_id`. Counts
   default to episodes, and facility-records are a drill-down.
5. **A reporting-environment class per country**, displayed wherever a count appears:
   `mandatory_regulatory` (US), `mixed_regulatory` (India, Canada), `corporate_disclosure`
   (Saudi Arabia), `media_only` (China), `conflict_restricted` (Russia/Belarus).
6. **Cause vocabulary**: add `natural_hazard` (weather, wildfire, seismic) and
   `supply_shortfall` before any new-country event is entered. Their weights are an owner
   decision. Until then, no new-country score uses `cause_weights` at all. A step model (§2)
   with confidence only does not need them.
7. **Evidence kind on volumes**: a shut-in volume from an operator or regulator is `observed`;
   one from an analyst bank (common for Canadian wildfires) is `estimated`. The kind travels
   with the number, as in recovery.
8. **Russia**: keep the corpus unfiltered. Optionally publish an **"effect-qualified subset"
   count** (the ≤ 34 above) as a cross-walk, so a reader can see how a Russia count would look
   under the new standard. This is information, not a comparison.

> **RECOMMENDATION (5).** Adopt the threshold **with fixes 1–7 before the first new-country
> event is stored**. The cause vocabulary and duration floors are owner decisions, and
> `inclusion_basis` is required for everything else to be honest. **Do not apply the threshold
> to the Russia corpus as a filter.** It fails roughly 80% of it, for reasons that are mostly
> about disclosure, not effect. Label Russia `occurrence` basis and publish the effect-qualified
> cross-walk only as context.

---

## 6. Cross-country comparison

### 6.1 Is any comparison of disruption defensible now?

**No.** Any cross-country comparison of disruption needs the same event definition, the same
denominator basis, the same recovery model and a comparable reporting environment. As of this
writing, all four differ (§2–§5), and the last cannot be equalised by method at all.

### 6.2 What MAY be compared

| Dimension | Why it is safe |
|---|---|
| **Energy-system context**: installed generation, refining capacity, production, energy mix, with source, vintage and basis code | These are statistics, not disruption measures, and they are needed to read any country's figures. Shown as context only, never sorted into a ranking of "largest targets"; no ranking of intact infrastructure. |
| **Data freshness**: last successful refresh per source | A property of the pipeline. |
| **Readiness state per sector** (§7) | A property of the evidence base. |
| **Evidence coverage**: share of events with observed vs estimated vs modelled recovery; share with quantified effect; status-unknown share | A property of the evidence base, and honest about it. |
| **Reporting-environment class** (§5.3.5) | Explains why counts are not comparable. |
| **Which methods are applied** (exposure / step / event-only) | Makes non-comparability visible. |

### 6.3 What must NOT be compared

- **Event counts, episodes or records**, including per capita, per GW or per year.
- **Any score built on different methods**: ESDI vs a new country's sector measure, or two
  countries' sector measures with different basis codes or recovery models.
- **Sector exposures across countries**, even when both are labelled "refining", unless basis,
  threshold, recovery model and reporting class all match. None currently do.
- **"Resilience", "vulnerability" or "readiness to withstand" scores.** These would cross the
  scope boundary (vulnerability or defensive-gap assessment) and must never be built.

### 6.4 Exact UI wording

**Country-picker / multi-country header (always visible when more than one country is shown):**

> Each country is measured on its own terms. Event counts reflect what is publicly reported under
> that country's reporting rules, not how often disruption happens. **A country with fewer
> recorded events is not shown to be safer, more resilient or less disrupted.** Figures are not
> comparable across countries and are never ranked.

**Next to any event count:**

> {n} qualifying events recorded · reporting environment: {class}. This counts what was
> reported and found, not what occurred.

**Zero or empty state:**

> No qualifying events recorded for {country} in this period. This means none were found in the
> sources monitored ({source list}). It is not evidence that none occurred.

**Reporting-environment tooltip, `media_only`:**

> Operators and authorities in {country} do not publish event-level outage reports. Events here
> come from media and company statements, so most smaller disruptions will not appear.

**On any country's sector card:**

> {Sector} for {country}: {method}, basis {basis}. Not comparable with {other country}'s
> {sector} figure.

**Structural rules that make the wording hold** (testable):
1. No payload field orders countries by any event or score quantity.
2. No chart puts two countries' counts or scores on a shared axis.
3. Every country record carries `reporting_environment` and `comparability: "none"` for counts.
4. Country cards render in a fixed, non-data-driven order (alphabetical or geographic), never
   sorted by a figure.

> **RECOMMENDATION (6).** Compare context, freshness, readiness, evidence coverage and
> reporting environment only. Never compare counts or scores. Ship the wording above together
> with the four structural rules and tests for each. The wording on its own will not hold.

---

## 7. Readiness states

### 7.1 Sector-level states (per country × sector)

Each is a testable predicate over fields the pipeline would emit. Every country × sector pair
must resolve to **exactly one** state, and no pair is allowed to have no state.

| State | Predicate (all must hold) | What the UI shows |
|---|---|---|
| **SCORED** | (a) `denominator.source`, `denominator.vintage_date` and `denominator.basis` all non-null; (b) `basis(numerator) == basis(denominator)` for ≥ 95% of scored capacity, with the residual disclosed; (c) `denominator.coverage_vs_reference` ≥ 0.80, or published as an explicit lower bound; (d) `inclusion_threshold_version` declared and every event carries `inclusion_basis` and `criterion_met`; (e) `recovery_model` declared per asset class, with a sensitivity sweep published for each assumed parameter that moves the sector value by > 1 point; (f) ≥ 1 event source with a declared refresh cadence, and last refresh within its freshness limit; (g) safety tests pass for the country (no incident coordinates, no range fields, no ranking of undamaged assets) | Sector value, with basis, vintage and sensitivity. |
| **EXPERIMENTAL** | (a) and (f) hold, but at least one of (b), (c), (e) fails | Value behind an "experimental" label, **never in any composite**, with the reason for each failed predicate. |
| **CONTEXT_ONLY** | A context statistic (capacity or production) exists with source and vintage, but (a) fails for a scoreable denominator, **or** the sector's construct is UNSUITABLE (§4.1) | Context figure and an event list. No value. Text: "Tracked, not scored: {reason}." |
| **INSUFFICIENT_EVIDENCE** | The sector exists, but no denominator **and** no systematic event source can be characterised | `null` with a reason. Text: "Unknown — {reason}." |
| **NOT_APPLICABLE** | The sector does not physically exist in the country (e.g. Saudi coal) | "Not applicable." Never rendered as zero, never as unknown. |
| **NOT_YET_RESEARCHED** | No lane has assessed it | "Not yet researched." Distinct from unknown. |

These map onto the project's three absences: INSUFFICIENT_EVIDENCE is **unknown**,
NOT_APPLICABLE is **not applicable**, and NOT_YET_RESEARCHED is **not yet researched**.

A **`model_dominated`** flag is separate from the state and applies to every SCORED or
EXPERIMENTAL sector. It is set when more than 50% of the sector's live value comes from
`kind=modelled` decay. **Russia's refining sector carries it today** (52 of 53 classified live
facilities decay on the modelled horizon). The flag discloses; it does not demote.

### 7.2 Country onboarding — the minimum to be shown at all

A country is displayed only when **all** of these hold:

1. **Scope statement approved**: admin-1 geometry and source, plus an explicit ruling on
   disputed or occupied territory, in the style of the Crimea rule. India and China raise
   Kashmir, Aksai Chin and Arunachal Pradesh, and China raises Taiwan. These are owner
   decisions and must be sovereignty-neutral analytic choices, stated as such.
2. **Source registry**: ≥ 1 event source per displayed sector, each with licence, refresh
   cadence and reporting-environment class; the country-level `reporting_environment` is set.
3. **Every sector has an explicit §7.1 state**, enforced by a test that fails on any missing
   pair.
4. **Context statistics** for every displayed sector carry `source`, `vintage_date` and `basis`.
5. **Threshold declared**: `inclusion_threshold_version` is set and every stored event has
   `inclusion_basis`, `criterion_met`, `episode_id` and an evidence kind on any volume.
6. **Safety tests extended to the country**: no incident coordinates, no range-to-target
   fields, admin-region precision only, no ranking of intact assets.
7. **Freshness**: a last-successful-refresh date for each source, with a stale banner past a
   declared limit.
8. **Comparability fields**: `comparability: "none"` on counts, and §6.4's structural rules
   tested.

Zero SCORED sectors is acceptable. A country may launch entirely CONTEXT_ONLY, with an event
list. That is honest, and better than a weak number.

### 7.3 Composite gate (any country-level index)

A composite for any country other than the existing Monitored-Area ESDI requires **all** of:
1. Owner approval of a **weight-derivation rule** (§1.4 D); no hand-set weights.
2. ≥ 2 sectors SCORED.
3. Σ(declared weights of SCORED sectors) ≥ 0.5, so renormalisation is not doing most of the work.
4. A declared recovery model for every scored class, with sweeps (§2).
5. A published `all_sectors` counterfactual (uncovered weighted at zero) and per-sector
   exclusion counterfactuals, as Russia has.
6. A back-test against at least two known major disruptions in that country (§1.4 D.6).

> **RECOMMENDATION (7).** Adopt the six sector states, the `model_dominated` flag, the
> eight-point country onboarding gate and the six-point composite gate as **tests**, not prose.
> Launch new countries at whatever sector states they honestly reach, which for most will be
> CONTEXT_ONLY plus event lists, with no composite.

---

## 8. Decisions that require the project owner

Each of these would change what a published number means, or create a new published number.

1. **ESDI scope (§1).** Confirm that the ESDI stays Russia/Belarus/Crimea-only (option A), and
   that new countries launch with no composite.
2. **Weight derivation (§1.4 D).** Whether to pursue a rule-based framework at all. If yes, the
   one-sentence construct, and acceptance that applying it to Russia would change the published
   ESDI (gas would become its heaviest, uncovered sector).
3. **New-country recovery model (§2).** Adopt the step model with a confirmation window and a
   `status_unknown` ratio, the W values and their sweep, and event-only treatment for grid
   outages.
4. **Russia: step representation for fully observed events (§2.3)**, and whether to publish a
   status-unknown share beside the ESDI. Both change Russia's numbers.
5. **Cause vocabulary and weights (§5.1.6).** Adding `natural_hazard` and `supply_shortfall`,
   their weights, and reconciling `sanctions` and `maintenance` with the new exclusions.
6. **Threshold parameters (§5.3).** Duration floors, the meaning of "material", the coal
   safety-inspection ruling, and confirmation that the threshold is **not** applied to the
   Russia corpus.
7. **Grid measures (§3).** A US customer-hours consequence measure and an Indian GD-category
   measure, each with its own name, never "transmission burden" and never in a composite at
   launch.
8. **Upstream production sector (§4.4).** Whether to add it to the taxonomy, and on which basis
   (observed production vs declared capacity).
9. **Per-country denominator bases (§4.2).** CDU b/cd gross domestic for refining; nameplate vs
   net summer for generation (with a firm-capacity sensitivity); native units, no cross-country
   conversion.
10. **Oil-logistics proxy (§4.3).** Confirm that it is forbidden outside Russia.
11. **`lng_terminal` split (§4.2.8)** into liquefaction and regasification. It touches Russian
    data only by relabelling (all current Russian LNG is export).
12. **A capacity-unavailable *observation* for India (§4.1).** A new construct, distinct from
    exposure, that this project has so far declined to produce anywhere.
13. **Disputed-territory scope rules (§7.2.1)** for India and China.

---

## 9. Adjacent observations (not acted on, recorded for the owner)

- `recovery.partial_operations_floor` (0.5) is declared in `methodology/scoring.json`, with a
  `_partial_note` describing a floor, but **no code reads it**. `recovery.assess` sends
  `partial_restart` to the modelled fallback, and METHODOLOGY §5 rule 4 says partial restarts
  are display-only. The config describes behaviour the scorer does not have, the same class of
  defect as the `refinery_inventory.json` invariance note corrected in iteration 13. It should
  either be deleted or marked DEPRECATED, as `status_multipliers` is.
- The observed refining median (47 d) against the modelled 150 d is the single most informative
  number for the Russia horizon question. It is not evidence for shortening the horizon (§2.4
  item iii, survivorship bias), but it belongs next to the horizon sweep as context.

---

## Sources consulted for this document

Repository: `CLAUDE.md`, `docs/METHODOLOGY.md`, `methodology/scoring.json` (and its full git
history), `pipeline/build_index.py`, `pipeline/recovery.py`, `pipeline/horizon_sensitivity.py`,
`pipeline/config.py`, `docs/REFINERY_CAPACITY_BASIS.md`, `docs/GENERATION_DENOMINATOR_AUDIT.md`,
`docs/CURRENT_STATE.md`, `docs/ITERATION_13_REVIEW.md`, `docs/MVP_REVIEW.md`,
`data/processed/snapshot.json`, `data/processed/incidents.json`, `data/curated/recovery.csv`,
`data/curated/effects.csv`.

External (checked for this document; each country lane should confirm the current version):
- OE-417 criteria: 10 CFR 205.351 — https://www.law.cornell.edu/cfr/text/10/205.351 ; form
  versions via https://omb.report/icr/202402-1901-002/doc/140091601.pdf (the criterion
  numbering and the customer-outage duration differ between versions).
- Indian grid disturbance categories (GD-1 < 10% … GD-5 ≥ 40% of antecedent regional generation
  or load): CAG audit report 18 of 2014, ch. 10 —
  https://cag.gov.in/uploads/download_audit_report/2014/Union_Performance_Commercial_Transmission_Projects_Power_Grid_Ministry_Power_18_2014_chapter_10.pdf ;
  CERC — https://cercind.gov.in/2017/ROP/193M.pdf (confirm against the current CEA Grid
  Standards / IEGC 2023).
- Aramco gross vs net (equity) refining capacity, as disclosed in the 2019 bond prospectus —
  https://mees.com/2019/4/5/refining-petrochemicals/aramco-bond-prospectus-sheds-light-on-downstream-operations/ec82ff80-57bf-11e9-b767-6f67815ab764
  (an illustration of the basis trap; current figures from the latest Aramco annual report).
- All other country statements (EIA Refinery Capacity Report, EIA-860/860M, EIA-861, EAGLE-I,
  BSEE shut-in statistics, NRC reactor status, NBS, NEA/CEC, PPAC, CEA, Grid-India, CER,
  StatCan, provincial regulators) are from general knowledge of what these bodies publish and
  are marked for confirmation by the country lanes.
