# Iteration 14 — globalization: five major energy producers

Theme: **turn a one-theatre monitor into a reusable six-system instrument without lending the
new countries a precision their evidence does not have, and without moving the theatre.**

Live figures are in [CURRENT_STATE.md](CURRENT_STATE.md). Figures quoted below are dated
findings from 2026-10-30 and are deliberately not kept current.

Companion documents: [GLOBAL_COUNTRY_SELECTION.md](GLOBAL_COUNTRY_SELECTION.md),
[GLOBAL_ARCHITECTURE.md](GLOBAL_ARCHITECTURE.md), [GLOBAL_METHODOLOGY.md](GLOBAL_METHODOLOGY.md),
[GLOBAL_GEOGRAPHY.md](GLOBAL_GEOGRAPHY.md), [COUNTRY_ONBOARDING.md](COUNTRY_ONBOARDING.md), and
`docs/countries/<CC>_SOURCE_AUDIT.md` / `<CC>_INDEX_READINESS.md` for each country.

---

## 1. Baseline

`main` at `0fede38` (bot refresh 2026-10-30): as_of 2026-10-30, ESDI 8.33, 184 events, 383
Python tests, 217 frontend tests. The iteration-13 staging contract held in production: 14 of 14
bot commits carried an in-sync `CURRENT_STATE.md`, and CI ran on all 14 through `workflow_run`.

---

## 2. Gate zero: a real browser, and what it found on its first run

Playwright 1.62.0 (pinned to the Chromium already in the machine's cache, so no download) now
drives real Chromium with software WebGL against the production build. The Russia suite covers
boot and map paint, search, deep links, history, a hostile `r=constructor`, the Evidence
Inspector, Data quality, Methodology, Compare dates, Recovery lifecycle, Map Focus, network
layers, the PNG export decoded pixel by pixel, two responsive sizes and ten legacy links. Any
console or page error fails the test. A CI job runs it on every push and after every refresh.

**It found a shipped defect on its first run.** Iteration 12 (`44a4ceb`, 2026-10-01) added a
fourth row track to the shell grid and updated every layout variant's `grid-template-areas`
except map focus. Three areas against four tracks put the map in an `auto` track at height 0:
**for four weeks, Map Focus and Briefing Mode showed no map, and a "current viewport" export
was MapLibre's 300-pixel fallback canvas.** Every unit test was green throughout, because
nothing in node can lay out a page. Fixed, with a static guard (rows vs areas, mutation-checked
against the old CSS) and browser assertions on map height and export height.

---

## 3. The thirteen assertions that never ran

A line tracer over a green run found 16 `assert` lines never executed: 3 behind the
`RUN_BUILD_TESTS` gate by design, and **13** the data or code could never reach. Two were
vacuous in ways that mattered: the flow-rerouted recovery check looped over a collection that no
longer held any such record, and the simplifier-metric check only flagged one spelling of the
forbidden call — a mutation proved a bare imported call passed the whole suite. One was dead
(superseded). The rest were conditional branches with no synthetic case. All 13 now execute, and
the prose lints, which split sentences on newlines and so had never seen a wrapped claim, collapse
whitespace first. Frontend: 0 of 389 `expect()` sites unexecuted.

---

## 4. Identity before importing anyone else's names

`pipeline/ids.py`: facility ids were names cut at 60 characters, so two names sharing a prefix
silently became one facility, and a published id already sat on the edge. Short ids are now
unchanged; long ones keep a readable prefix plus a hash of the whole slug; the one id published
under the old rule is grandfathered, because incident ids and `recovery.csv` are keyed on it;
cross-system identity is `<system>:<id>`; collisions go to `parser_warnings`. Rebuilt payload
byte-identical.

---

## 5. The five systems, and what they are not

Selection: the five largest total primary energy producers excluding Russia — China, United
States, Saudi Arabia, Canada, India (EIA 2024). Canada and India differ by about 1% and swap
places between sources, so no order is ever displayed.

Twelve research lanes ran in parallel: per country, a source/readiness audit and an
incident/recovery lane, plus geography/licensing, cross-country methodology and a hostile-test
lane. Every lane worked to one written inclusion threshold (seven clauses) and one safety
boundary.

**The central decision: no country gets a score this iteration.** The methodology audit showed
the ESDI's weights are an unvalidated MVP judgement that fits no country's energy mix (Russia's
included); its decay horizons were calibrated on repeated strikes and score a refinery that
restarted on day 10 as 6.5 times more impaired than it was; its transmission measure would read
about 100% on an ordinary day in any country with mandatory outage reporting. Reusing it would
produce numbers that look comparable and are not. So every country publishes `index: null` and
`headline: null` with a stated reason, every sector carries one of six states with a reason (at
most CONTEXT_ONLY, because nothing is computed), and the lanes' assessments of what each sector
could reach are published beside the state, labelled as not published. The build refuses a
sector claiming a score it does not have.

What each country shows: reviewed, publicly reported major disruptions at first-level-region
precision (94 events at review: CA 23, CN 14, IN 15, SA 11, US 31), sourced energy-system context,
sources and licences, research gaps, the reporting environment, and the onboarding gate's status.

---

## 6. Geography and sovereignty

Natural Earth throughout (public domain; GADM ruled out on licence). Default edition, i.e. the
line of actual control, stated as an analytic choice. India's four 2023 ISO code changes applied;
Hong Kong and Macau added to China; Taiwan is not part of the China system; the Paracels are drawn
but never assigned an event; Kashmir, Ladakh, Arunachal and Aksai Chin carry neutral rulings.

**Crimea on the world map.** Natural Earth's admin-0 Russia polygon contains Crimea. Painting it
as "Russia" on the first screen a reader sees would have contradicted the project's oldest rule.
The world layer draws Russia from admin-1 instead, with Crimea and Sevastopol as their own
occupied, Ukrainian features — tested at both points.

**A region must never vanish.** `simplify_geometry` deleted Wyoming and Colorado (four corners
simplify to five points, below the six-point floor). Fixed; Russia's regions byte-identical.

---

## 7. The architecture

The theatre did not move: `data/processed/` is its root. Countries live under `systems/<id>/`,
one registry (`pipeline/systems.py`), one generated manifest, no country constants in React,
everything declared in `pipeline/artifacts.py`. A bare URL opens a new global home; every theatre
link that carried view state still opens the theatre, which now writes `sys=ru`. Each view is a
lazy chunk; switching countries aborts the old load (tested against a three-second delayed
response); one country's broken payload is contained to that country (tested with a forced 500).
The theatre's ribbon no longer turns a missing value into `0.0`.

A historical `--as-of` build now reconstructs each country as of that date rather than refusing
to run because the corpus has grown — the frozen regression found that.

---

## 8. Red teams

**Safety.** It found a blocker: an India event named a substation as Delhi's in-feed and gave the
megawatts the city draws through it. Removed. Also: pipeline and plant placements below admin-1,
a distribution-network inventory for the Kashmir valley, a cascading-failure description,
"largest facility" framing, a Saudi per-refinery capacity table shipping during an attack
campaign on those plants, and a scope scan that missed bare decimal coordinates, distance
phrasing, hyphenated "air-defence", weapon designators, cyber technique and dependency language.
Most seriously, **the committed candidate queue, read per facility, recorded which attacks had no
reported operational effect** — damage-assessment feedback. It had not been pushed. The queue
files are now uncommitted (`data/candidates/README.md` says why), the unpushed history that
contained them was folded before release, and every text fix is a recorded edit with a reason in
`data/curated/systems/review_edits.json`.

**Analytic honesty.** Three blockers, all fixed and tested: every kind of recovery evidence
(estimate, partial, service only, "nothing was lost") rendered as "evidence found"; a missing
`opened` flag counted as a source read for 63 of 94 events, while the page claimed the check ran;
a region view said "none found" beside a multi-region event naming that region. Also fixed: a
single colour scale shared by all five countries (a cross-country axis in colour; each country now
uses its own range and prints it), the PNG printing a count without its reporting environment, the
home map marking Russia's unmonitored Far East as monitored, the build date presented as the
record's date, context bases hidden, production figures shipping in descending order in the
manifest, and inaccurate claims about legacy links.

---

## 9. Verification

- Python: 421 passed, 2 skipped (the env-gated build tests).
- Frontend unit: 232 passed. Typecheck and production build clean.
- Browser: the Russia suite (25) and the global suite — home, all five countries, deep link, the
  picker across six systems with Back, the race, error containment, a PNG per country decoded
  pixel by pixel, print/PDF for all seven pages, two responsive sizes, three map goldens (win32).
- **Frozen regression** (`--as-of 2026-08-28`): ESDI **16.8** from both the pre-iteration commit
  and this one, over the same raw data, with identical sector values. Iteration 14 moved nothing
  in the theatre. The 18.50 previously recorded in HANDOFF is stale: the upstream strike table has
  been revised since (current reconstruction ≠ as-published history).
- Current build: ESDI 8.33, 184 events, unchanged.

---

## 10. Owner decisions (none taken here)

From [GLOBAL_METHODOLOGY.md](GLOBAL_METHODOLOGY.md) §8, plus three this iteration raised:

1. Keep the ESDI theatre-only (in force by default) or pursue a weight-derivation rule.
2. A recovery model for non-conflict events (step function with a confirmation window), without
   which no country sector can move past CONTEXT_ONLY.
3. New causes (`natural_hazard`, `labour`, `supply_shortfall`) and an upstream sector for the
   theatre taxonomy — used by the countries as a declared extension only.
4. Threshold parameters: duration floors, share-of-customers for small provinces, precautionary
   port closures.
5. Disputed-territory aggregate rules for India and China, needed only once an aggregate exists.
6. **US territories** (Puerto Rico's three accepted events are held).
7. **Recovery status of facilities under a live attack campaign** (Saudi Arabia): the theatre
   doctrine publishes it; a second live campaign was not anticipated when that was decided.
8. The refining basis proposal from iteration 13 (`REFINERY_CAPACITY_BASIS.md`), still undeployed.

---

## 11. Deferred, with reasons

- **Per-source freshness and episode grouping** for countries (onboarding-gate items 2, 5, 7 are
  partial and published as such).
- **Incident coverage**: every incident lane hit a shared web-search budget; 2025-26 coverage is
  thin and recorded as research gaps per country, not as quiet years.
- **A disputed-areas overlay** on the world map (Siachen is marked disputed; the full Natural
  Earth disputed-areas layer is not drawn).
- **Pinning Natural Earth to a tag**: it would change the theatre's geometry source mid-stream;
  a decision for an iteration that can rebuild and compare.
- **Wave 2** (Indonesia, Iran, Australia, then Qatar, Norway, Brazil, UAE, Iraq): ranked in
  GLOBAL_COUNTRY_SELECTION.md, not implemented.

---

## 12. What this iteration is actually about

Five countries were added and none of them got a number. That is the result, not a shortfall: the
work that would have produced five plausible headline figures in a day is precisely the work the
methodology audit showed cannot be defended yet. What shipped instead is the machinery for
honesty at scale — states with reasons, absences that say which absence they are, counts that
never travel without the reporting environment that produced them — and two red teams that
found the places where the first draft still said more than it knew.
