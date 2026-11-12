# Owner decision matrix (iteration 20)

The one authoritative list of methodology questions that only the owner can settle. It replaces
the owner questions scattered across the iteration-19 source audits and §27 of
`ITERATION_19_REVIEW.md`; rows D-01 to D-26 are those questions, D-27 onward are new.

**While a row is unresolved, the conservative behaviour in its last line is what the code does.**
Nothing here is implemented beyond that. A ruling is implemented by the row's "if approved" line,
and every held record it names is restored by re-import from the local queue, with no re-research.

Counts of held candidates are given across all systems, never per campaign system: a per-country
count of held attack candidates would hint at the scale of a campaign (§42 of the brief).

Each row: **Question** · **Written rule** · **Precedent** · **Systems** · **Published records
affected** · **Held records affected** · **Safety** · **Analysis** · **Recommendation** ·
**If approved** · **Until then**.

---

### D-01 Scheduled seasons of load shedding
- **Question.** A government's published season of rotating cuts (Iran, Iraq, Kuwait): one record per announced cut, one record for the season, an episode, or national context only?
- **Written rule.** Clause 4, second limb: a generation shortfall that forced rotating outages. Silent on duration.
- **Precedent.** Single dated programmed-cut days were published (Kuwait 2024).
- **Systems.** ir, iq, kw. **Published.** 3 (Kuwait, single days). **Held.** several season-level candidates.
- **Safety.** Low; national, non-kinetic. **Analysis.** A season recorded as daily records would dominate the corpus; one record hides duration.
- **Recommendation.** One record per announced season where a source ties it to a shortfall, dated to the announcement, with the season as an episode.
- **If approved.** A `season` episode type; season records imported.
- **Until then.** Single dated days that meet clause 4 are published; seasons held.

### D-02 Taxonomy gaps
- **Question.** Add classes or causes for a fuel depot, petrochemical plant, power-and-water plant, gas-to-liquids plant; causes for a precautionary shutdown during hostilities, a protest or blockade by non-workforce actors, demand above available generation?
- **Written rule.** `taxonomy.json` plus `TAXONOMY_EXTENSIONS`. **Precedent.** None added to rescue a record.
- **Systems.** all Gulf, us (petrochemical). **Published.** 0. **Held.** 5 tagged [TAXONOMY] this pass.
- **Safety.** A new class can identify a site where a country has one such plant (D-14). **Analysis.** See `TAXONOMY_OPTIONS_20.md`.
- **Recommendation.** As in `TAXONOMY_OPTIONS_20.md`: no new asset class. A power-and-water plant is truthfully a thermal power plant and is classified so where an electricity effect is reported; a fuel depot is `oil_terminal` only where clause 2 is met; petrochemical output is outside the product; a gas-to-liquids plant is `gas_processing`.
- **If approved.** No code change; held records re-reviewed under those readings.
- **Until then.** Held [TAXONOMY]; no label is forced.

### D-03 Attack occurrence with no effect within seven days
- **Question.** Is a sourced attack with no qualifying effect reported within seven days a record?
- **Written rule.** Every clause names an effect; none admits occurrence alone. **Precedent.** Held since iteration 19.
- **Systems.** all Gulf. **Published.** 0. **Held.** 5 this pass, plus earlier.
- **Safety.** Publishing occurrence alone moves the product toward an attack log. **Analysis.** Effect-based records are the threshold's whole point.
- **Recommendation.** Confirm: not a record.
- **If approved.** No change. **Until then.** Held [NO-EFFECT].

### D-04 Production halted because an export route or export line was unavailable
- **Question.** Out of scope by the route rule? Is a field halted by a fault on its own export line the same case?
- **Written rule.** Gulf systems: nothing about routes, export-route dependence or bypass capacity. Clause 7 is otherwise met by a stated volume.
- **Precedent.** iq-2025-12-08 published in iteration 19, held in 20.
- **Systems.** iq (and potentially every exporter). **Published.** 0 (1 held this iteration). **Held.** 2.
- **Safety.** Recording why a field stopped (its outlet failed) is a dependency statement. **Analysis.** The shut-in volume is a real disruption.
- **Recommendation.** A record may state that production was shut in and the volume; it must not state that the cause was the export route. Where the route is the only stated cause and the record cannot be written without it, hold.
- **If approved.** Edit wording; re-import. **Until then.** Held [ROUTE].

### D-05 Force majeure with no stated shutdown
- **Question.** Does a force-majeure declaration alone meet clause 1 or 2?
- **Written rule.** Clause 3 names force majeure for trunk pipelines only. **Precedent.** Two Qatar duplicates held.
- **Systems.** qa, sa, ae. **Published.** 0 rely on it alone. **Held.** 2.
- **Safety.** Low. **Analysis.** Force majeure is a contractual statement and may cover a reduction, not a stop.
- **Recommendation.** Not on its own; it qualifies with a stated suspension or cut.
- **If approved.** No change. **Until then.** Held [C3-FM].

### D-06 Capacity share as the only threshold basis
- **Question.** If the only fact that crosses a threshold is a share of national capacity, which the safety rule removes, does the record qualify on damage alone?
- **Written rule.** Brief §20: either another safe fact qualifies it, or hold. **Precedent.** Held.
- **Systems.** Gulf. **Published.** 0. **Held.** 0 this pass.
- **Recommendation.** Confirm: hold. **Until then.** Held [SHARE-ONLY].

### D-07 Substations, calls, districts in place of customers
- **Question.** May a count of substations, calls or districts stand in for customers under clause 5?
- **Written rule.** Clause 5 counts customers. **Precedent.** Held; customer-account counts under another name (households, service connections, addresses) are accepted (D-30).
- **Systems.** sa, kw, us. **Published.** 0 (Francine held this iteration for "people"). **Held.** 1 this pass plus Saudi regional outages.
- **Recommendation.** Confirm: not customers. "People" is not customers either. **Until then.** Held [C5-SUBSTITUTE].

### D-08 "Emergency plans activated" or "working on a full emergency footing"
- **Question.** Is either a clause-5 grid-operator emergency declaration?
- **Written rule.** A declaration. **Precedent.** iq-2025-08-11 published on it in iteration 19; held in 20.
- **Systems.** iq, sa. **Published.** 0 (1 held this iteration). **Held.** 2+.
- **Recommendation.** No. A declaration is a named, formal operator act (EEA 3, an emergency notice, an ordered load shed).
- **Until then.** Held [C5-EMERGENCY].

### D-09 An importer's shortfall caused by a supplier's planned maintenance
- **Question.** Excluded by the planned-maintenance exclusion, or a disruption of the importing system?
- **Written rule.** "planned maintenance and turnarounds" are excluded. **Precedent.** Held.
- **Systems.** iq. **Published.** 0. **Held.** 3 this pass (two report cut supply hours).
- **Safety.** Recording supplier, cut and megawatts is the dependency series of D-25. **Analysis.** The importer's shortfall is real; its cause is another system's plan.
- **Recommendation.** Excluded, unless the importing system reports rotating outages and the source states a shortfall beyond the planned volume.
- **Until then.** Held [SUPPLIER].

### D-10 Non-attack records at a site that has country-level attack records
- **Question.** Publish by name, cover by the campaign, abstract, or hold?
- **Written rule.** None. **Precedent.** Lead hold (iteration 19) on records naming a facility whose attack records are published without a place.
- **Systems.** iq, kw. **Published.** 0 affected. **Held.** 2+ new this pass.
- **Safety.** A named non-attack record beside an abstracted attack record re-identifies the site.
- **Recommendation.** For a system under the campaign policy, a non-attack record at a site with a published country-level attack record is published at the same abstraction (country level, no facility) while the campaign holds.
- **Until then.** Held.

### D-11 Saudi Arabia's region-level, facility-named attack records
- **Question.** See `SAUDI_HARMONISATION_STUDY_20.md`. **Recommendation.** Option C. **Until then.** Option B (aggregating surfaces only), implemented this iteration.

### D-12 Walking a utility's numbered pages as a discovery route
- **Question.** Where a listing is unreadable, may a researcher walk sequential article ids?
- **Written rule.** Direct fetch of reachable public pages is allowed; no workaround of access control. **Precedent.** Not used.
- **Recommendation.** Allowed where pages are publicly served and unthrottled, at one request per three seconds, logged as a method; never where a page sits behind a challenge.
- **Until then.** Not used.

### D-13 Release rule A
- **Question.** When do withheld campaign fields return? See "Release rule A: options" below. **Recommendation.** Explicit owner release per system, with a 45-day minimum after the campaign state leaves the restricting states. **Until then.** Nothing is released automatically.

### D-14 One facility of a class in a country
- **Question.** For an attack record where country plus class names one facility: a coarser class, a caveat, or no record?
- **Written rule.** Brief §44: broaden truthfully or hold. **Precedent.** One confirmed record held (iteration 19); Qatar LNG candidates held.
- **Systems.** qa, bh, and any class that is one site. **Published.** 0. **Held.** 3+.
- **Recommendation.** The generic single-site rule implemented this iteration (see `GULF_ARCHITECTURE.md`): where a truthful parent class exists and the record still meets its clause, publish under the parent; otherwise hold.
- **Until then.** Held [SINGLE-SITE].

### D-15 Attack records whose effect is a downstream generation loss
- **Question.** Publish, when the megawatt figure can identify the site?
- **Recommendation.** Publish without the megawatt figure where the effect is otherwise stated; hold where the figure is the only effect.
- **Until then.** Held.

### D-16 Clause 3 on a reported flow disruption with no stated shutdown
- **Question.** Is a reported flow disruption a trunk-pipeline shutdown?
- **Recommendation.** No. **Until then.** Held.

### D-17 Clause 4 on megawatts lost with no load shedding; demand-peak cuts
- **Question.** Does a stated megawatt loss with no reported load shedding meet clause 4? Do programmed cuts on a demand peak, with no stated deficit, meet it?
- **Written rule.** Either limb needs a plant of about 500 MW offline with an effect, or rotating outages forced by a shortfall. **Precedent.** India and Canada records held since iteration 17; three Iraq records held in 19; one Kuwait record published in 19 and held in 20.
- **Systems.** iq, kw, in, ca. **Published.** 0 (2 held this iteration: the Kuwait demand-peak record and the PJM forced-outage record). **Held.** 6 [C4-MW] this pass plus earlier.
- **Recommendation.** Keep the clause as written.
- **Until then.** Held [C4-MW] / [C4-DEMAND].

### D-18 Clause 5 by official extent with no customer count
- **Question.** May a national or multi-governorate extent stand in for 100,000 customers?
- **Written rule.** About 100,000 customers or a declaration. **Precedent.** Three Gulf records and two India records published on extent; all held in iteration 20 (`CROSS_SYSTEM_THRESHOLD_AUDIT_20.md`).
- **Systems.** iq, om, in, sa, bh, ae. **Published.** 0 (5 held this iteration). **Held.** 3+ this pass.
- **Safety.** Low. **Analysis.** A national blackout plainly exceeds 100,000 customers; the rule exists so two researchers sort the same row the same way.
- **Recommendation.** A narrow, written extension: a source-stated loss of supply across an entire national grid or an entire first-level region whose published customer base exceeds 100,000 qualifies. Nothing partial ("parts of", "most of") qualifies.
- **If approved.** Restores the two Iraq national blackouts; the Oman and India records stay held.
- **Until then.** Held [C5-EXTENT].

### D-19 Cause vocabulary
- **Question.** Causes for a precautionary shutdown during hostilities, a non-workforce protest or blockade, demand above available generation? **Recommendation.** See `TAXONOMY_OPTIONS_20.md`: add one cause, `civil_blockade`, which recurs in at least four systems; a precautionary stop is an excluded decision; demand above generation is the clause-4 question (D-17). **Until then.** Held [TAXONOMY].

### D-20 The maintenance exclusion against an unplanned shortfall during a maintenance season
- **Recommendation.** The exclusion covers the planned work, not an unplanned shortfall that a source states. **Until then.** Held where the source does not separate them.

### D-21 Official technical cause and separately reported sabotage; supply-drop statements
- **Recommendation.** Record the official cause; never publish the sabotage claim as cause without an official or two independent statements. **Until then.** Held.

### D-22 Damage to a plant already halted
- **Recommendation.** A continuation of the existing record, not a new one. **Until then.** Held.

### D-23 Clause 1 on a partial effect
- **Question.** Does "some units shut" meet clause 1 without a plant-level statement?
- **Precedent.** One Kuwait record published in 19, held in 20; five US records held in 20.
- **Recommendation.** Adopt the clause-1 reading (c) of D-28 for every system, and nothing broader.
- **Until then.** Held [C1-PARTIAL] / [C1-MATERIAL].

### D-24 World share in the exported regional image
- **Question.** The share travels without the page's caveats. **Implemented this iteration:** the image carries the caveat on the same line as the share. **Recommendation.** Keep the share with its caveat. **Until then.** As implemented.

### D-25 Iraq dependency series
- **Question.** Records pairing an imported-gas shortfall with megawatts lost form a dependency series.
- **Recommendation.** As implemented this iteration (see `GULF_ARCHITECTURE.md`): the regional and recent feeds carry no capacity figure for any Gulf record; the country page keeps the sourced figure. Supplier-maintenance records stay held (D-09).

### D-26 A newer national-context year under the campaign policy
- **Implemented this iteration:** a generic guard. Under the campaign policy a country shows only the common comparison year; no campaign-year value is surfaced. **Recommendation.** Keep.

### D-27 Clause 5 by an ordered firm load shed (US)
- **Question.** Is an operator-ordered firm load shed a "grid-operator emergency declaration"?
- **Written rule.** A declaration. **Precedent.** US operational definition (iteration 16, listed for owner review).
- **Systems.** us (and any system that reports load shed). **Published.** 9 US records.
- **Recommendation.** Yes: an ordered firm load shed is an emergency act under NERC EOP-011 and is reported by obligation.
- **Until then.** Kept, as the written US definition says.

### D-28 Clause 1 by a named major unit with a reported throughput effect
- **Question.** Does a crude unit, liquefaction train or coker shut, with a reported throughput effect, meet "throughput materially cut"?
- **Precedent.** US operational definition. **Published.** 6 records (5 US, 1 China). **Held.** applies to new Kuwait candidates.
- **Recommendation.** Yes, for a named major unit only.
- **Until then.** Kept for every system alike.

### D-29 Clause 4 by aggregate megawatts with a reported consequence
- **Question.** Does "at least about 500 MW forced offline" across several plants, with load shed, meet "a power plant of about 500 MW or more"?
- **Published.** 3 (each also meets another clause or limb). **Recommendation.** Yes, where the consequence is load shed; no otherwise.
- **Until then.** Kept where load shed is stated; PJM Elliott held.

### D-30 Customer accounts under another name
- **Question.** Are households (户), service connections and service addresses customers?
- **Published.** 5. **Recommendation.** Yes: each is a metered supply point. People are not.
- **Until then.** Kept.

### D-31 Cut supply hours with no figure (Kurdistan, January 2026)
- **Question.** The ministry reports cut supply hours with no megawatt figure, customer count or stated shortfall. The Iraq plan required one of the three.
- **Recommendation.** Clause 4's second limb needs the shortfall to be stated; the figure is not required. Publish where the shortfall is stated.
- **Until then.** Held, as the plan said.

### D-32 Water and desalination
- **Question.** Desalination plants are outside the taxonomy. **Recommendation.** Keep outside; a combined power-and-water plant is D-02. **Until then.** Not recorded.

### D-33 Saudi harmonisation
- See `SAUDI_HARMONISATION_STUDY_20.md`. **Recommendation.** Option C. **Until then.** Option B.

---

## Release rule A: options

Release rule A decides when fields withheld under an active campaign (recovery status, end dates,
status-bearing citations and headlines) return to the public payload. It is not active.

| Option | Operational sensitivity | Research utility | Simplicity | Comparability |
|---|---|---|---|---|
| Campaign end + 14 days | high: two weeks after a ceasefire is inside the window where repairs and restarts are still being targeted | earliest | simple | low: depends on when the campaign was declared over |
| Campaign end + 30 days | medium | good | simple | low |
| Campaign end + 45 days | low-medium | good | simple | low |
| Campaign end + 60 days | low | delayed | simple | low |
| Event age (e.g. 180 days after the event, whatever the campaign) | high during a long campaign: an old attack's site status can still be live | steady | simple | high |
| Explicit owner release per system | lowest: a person judges whether the conflict condition has really ended | slowest, and needs attention | simple in code; needs a ruling | medium |

**Recommendation.** Explicit owner release per system, with a minimum of 45 days after the system's
campaign state leaves the restricting states (ACTIVE, RECENT_ENDED, UNCERTAIN). A campaign end is a
judgement that public reporting makes slowly and sometimes reverses. A fixed timer releases on a
date a reverse can overtake; an owner release on top of a floor cannot release early.
Implementation if approved: a `released` date per system in `conflict_campaigns.json`, set only by
the owner; the import restores withheld fields from the queue for that system's records.
**Until then nothing is released.**
