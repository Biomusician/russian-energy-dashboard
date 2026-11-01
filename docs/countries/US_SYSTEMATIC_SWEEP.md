# United States — systematic research sweep (iteration 16)

**Part A, the search plan, was written on 2026-10-31 before any search of this pass was run.**
It is deliberately left as written; what actually happened is recorded in Part B, lane by lane,
so a reader can compare the plan with its execution. Completion is a claim about the process, not
about the world: "complete" means every declared lane below was executed across the declared
window and recorded its disposition. It never means "no other qualifying event exists".

---

## Part A — plan (written before searching)

### A.1 Universe

| | |
|---|---|
| Window | 2022-01-01 to 2026-10-31 (the US system's accepted coverage window, to the sweep date) |
| Geography | the 50 states and the District of Columbia. US territories are outside the system's geography pending an owner decision (ITERATION_14_REVIEW §10) and are recorded as out of scope, not researched-and-quiet |
| Qualifying rule | `data/curated/systems/inclusion_threshold.json` version `2026-10-30.1`, clauses 1-7 and its exclusions, unchanged. No new event class is added during the sweep; a class that looks valuable but is not in the rule is written up separately (Part B, "proposals") |
| Record unit | one record per affected state per event for grid outages (the existing US practice); one record per facility event otherwise; a nationally reported production effect is a country-level record |
| Episodes | under the iteration-16 rule (GLOBAL_METHODOLOGY §5.3): a named hazard, an explicitly identified common event, or an explicit continuation. A source that merely lists several events is not an episode |

### A.2 Operational definitions of the clauses for this sweep

These interpret ambiguous words in the rule so that two researchers would sort the same row the
same way. They narrow, never widen; each is listed for owner review (ITERATION_16_REVIEW).

- **Clause 5, customers.** The peak number of customers without power at one time in one state
  from one event, as stated by a utility, state agency, DOE or a reputable outlet citing them,
  is at least 100,000. Cumulative "customers restored" totals do not count; they double-count.
- **Clause 5, emergency declaration.** A grid operator declared NERC Energy Emergency Alert
  **Level 3** or ordered firm load shed. EEA levels 1-2, conservation appeals and "watch" notices
  are alerts with no reported physical effect, so the rule's own exclusion ("no reported effect")
  removes them.
- **Clause 4.** At least about 500 MW forced offline *and* a reported consequence (load shed, EEA3,
  or a stated supply effect). A unit trip with no reported effect is excluded by the rule.
- **Clause 1.** A refinery, gas-processing plant or LNG terminal reported shut, or a named major
  unit reported shut with a reported throughput effect. A fire with no reported effect on
  operations does not qualify.
- **Clause 7.** A shut-in volume reported by a regulator (BSEE storm statistics, which BSEE
  publishes only when a storm threatens Gulf production) or by EIA. A volume inferred from a
  storm track is never used.
- **Hazard ≠ effect.** A storm enters the corpus only through a documented energy-system
  consequence. Its path is never used to infer which infrastructure was affected.

### A.3 Source lanes

Each lane names its source, its enumeration method (how the researcher knows the list is
exhausted), and the clause(s) it serves. A lane that cannot be executed across the whole window
makes the pass PARTIAL, with the reason; it is not quietly dropped.

| Lane | Source family | Enumeration | Clauses |
|---|---|---|---|
| G1 | DOE OE-417 electric disturbance annual summaries, 2022-2026 | every row of each year's summary, filtered by the definitions above | 4, 5 |
| G2 | NERC and FERC event inquiries and NERC *State of Reliability* reports, 2022-2026 | every major-event review and each year's report | 4, 5 |
| H1 | DOE CESER emergency situation reports (the public archive), 2022-2026 | every event DOE reported on; for each, the per-state peak outage and any energy-supply effect | 1, 2, 5, 7 |
| H2 | NOAA National Hurricane Center seasonal summaries, 2022-2026 | every tropical cyclone with US landfall, cross-checked against H1 so a storm DOE did not report on is still examined | 5, 7 |
| U1 | BSEE Gulf of America storm shut-in statistics; EIA *Today in Energy* on production freeze-offs | every BSEE storm release; every EIA article on weather-driven shut-ins | 7 |
| P1 | PHMSA corrective action orders, hazardous-liquid and gas-transmission, 2022-2026 | every order issued in the window | 3 |
| L1 | US LNG export terminals operating in the window | each terminal checked for a reported unplanned shutdown (EIA, FERC, operator, Reuters/AP) | 1, 2 |
| R1 | US Chemical Safety Board investigations, plus a year-by-year structured query for refinery and gas-processing shutdowns (EIA, operator statements, Reuters/AP/Bloomberg-public) | every CSB investigation in the window; each year 2022-2026 queried with the same query set | 1 |
| C1 | MSHA and EIA coal reporting | any mine event EIA or MSHA reports as cutting supply | 6 |

**Corroboration only, not a lane:** EAGLE-I county outage history. Its yearly files are large
15-minute county snapshots; it is used to check a peak customer figure found elsewhere, not to
enumerate events. This is a declared limitation, not a skipped lane.

### A.4 Dispositions

Every candidate gets one of: `accepted` (meets a clause on what an opened source says),
`rejected` (examined, does not meet a clause, or an exclusion applies), `duplicate` (already in
the corpus or another candidate), `held` (looks qualifying but the evidence could not be opened or
is contradictory), `out_of_scope` (territory, outside the window). A lane records what it
examined and the counts; per-record notes stay in the local candidate queue.

### A.5 Review

The lane researchers produce candidates. Promotion into `data/curated/systems/us/events.json`
needs a second, independent reviewer who opens the evidence (docs/REVIEW_GOVERNANCE.md). The
import gate refuses a record without both reviews.

### A.6 What will make this pass PARTIAL

Any lane not executed across the whole window: a source that is unreachable, unpublished for a
year in the window, or behind a paywall or bot challenge (never worked around). A partial pass is
an honest result.

---

## Part B — execution record

Executed 2026-10-31 by three research lanes (grid, hazard, facility) and six independent review
batches. Counts only; per-record narratives stay in the local queue (`data/candidates/`, never
committed).

### B.1 Result

**PARTIAL. Two of the nine lanes are complete; seven are partial, each for a stated reason.**
The pass is published with that status (`research_log.json`, "iteration-16 systematic
sweep"), and the country page says "Systematic search partial".

| | Count |
|---|---|
| Candidates examined | 350 |
| Accepted after independent review | 101 (43 confirmed as found, 58 corrected by the reviewer) |
| Rejected | 77 (76 by the lanes, 1 removed by the reviewer) |
| Held | 103 (92 by the lanes, 11 by the reviewer or the lead) |
| Duplicate | 42 (17 of them were already in the corpus under the same id) |
| Out of scope | 27 (US territories, outside the window) |

The US corpus went from 37 records to 138. 107 are dual-reviewed: the 101 above plus 6
iteration-15 records reviewed retroactively. 31 records are grandfathered as single-review.

### B.2 Lane by lane

| Lane | Status | Accepted | Held | Rejected | Duplicate | Out of scope | Why not complete |
|---|---|---|---|---|---|---|---|
| G1 OE-417 | partial | 29 | 75 | 17 | 13 | 25 | 2022-2025 enumerated in full; no 2026 annual summary is published yet |
| G2 NERC / FERC | **complete** | 1 | 2 | 7 | 5 | 0 | |
| H1 DOE CESER | **complete** | 14 | 11 | 3 | 11 | 1 | |
| H2 NHC | partial | 2 | 2 | 16 | 2 | 0 | NHC's own summaries read for 2022 only; 2023-2026 landfalls checked through secondary season records |
| U1 BSEE / EIA | partial | 2 | 2 | 3 | 4 | 0 | BSEE's release listing refused automated access (not worked around); EIA enumerated in full |
| P1 PHMSA | partial | 18 | 1 | 10 | 2 | 1 | enumerated through 2026-10-02, the public data file's date |
| L1 LNG | partial | 9 | 6 | 8 | 2 | 0 | no public outage dataset; news search finds prominent outages only; one terminal not checked |
| R1 CSB + query set | partial | 20 | 2 | 13 | 3 | 0 | CSB in full; the year-by-year query set is a structured sample, not a census |
| C1 coal | partial | 6 | 2 | 0 | 0 | 0 | no public list of supply-cutting mine events; web search only |

A record two lanes found counts once per lane in this table, so lane totals can exceed B.1.

### B.3 Why so much is held

- **G1 is the main source of held records (75).** OE-417 reports an *incident total* of
  customers, which can be cumulative across a multi-day event or several states. The A.2
  definition needs a *peak at one time in one state*. Where no opened source gave that peak,
  the row is held, never accepted on the total. This is the strictest call in the sweep.
- **Aggregator-only figures are held.** A PowerOutage.us number quoted without a utility or
  agency figure is held (Hurricane Nicole 2022, by lead ruling). If the owner wants
  aggregator figures accepted, that is a rule change.
- **Port closures without a terminal-level statement** are held under L1 (3 records).

### B.4 Lead rulings during the sweep (owner review requested)

These are recorded in `REVIEW_GOVERNANCE.md` §6, and each narrows the rule rather than
widening it:

1. **Trunk pipeline** means an interstate or major transmission line. Five lines below that
   bar were rejected: Buckeye 602, Plains Buffalo, Enterprise C92.1, Marathon 8-inch Utah and
   Texas Gas 16-inch Louisiana.
2. **LNG terminals have no duration floor,** as the rule is written. This is flagged in
   ITERATION_16_REVIEW as an open question.
3. **Pipeline loop segments** with a PHMSA shutdown order but no stated supply effect are
   accepted under clause 3 as written. This is flagged for the owner.
4. **Records accepted on stated wording:** the Deer Park secondary crude unit, because the
   source states a throughput effect, and the Linden "production outage", because it is the
   operator's wording.
5. **Held:** Martinez Renewables, and Freeport December 2025, because the evidence was not
   opened.
6. **Removed:** Elba Island. The effect was inferred from timing alone, which the
   no-proximity rule forbids.

### B.5 Episodes

Hurricanes and winter storms with records in several states are `named_hazard` episodes:

- Helene: 10 states
- Elliott: 6
- Ian: 5
- Francine and Fern: 3 each
- Beryl, Heather, Idalia, Isaias and Milton: 2 each

The Texas City records share one `explicit_common_event`. No episode was formed from timing
or proximity.

### B.6 What the next pass must do to reach COMPLETE

- G1: re-run when DOE publishes the 2026 OE-417 annual summary.
- H2: read NHC's own Tropical Cyclone Reports for 2023-2026.
- U1: get BSEE's storm releases through a route BSEE offers to automated readers, or read
  them by hand.
- P1: extend the PHMSA file past 2026-10-02.
- L1: check the remaining terminal, and define a terminal-level enumeration source.
- R1 and C1 have no census source. Their best possible status is "partial, by construction",
  unless the owner accepts a declared query set as a complete enumeration for these classes.
  That is an open owner decision.

