# Country onboarding

How to add a monitored country, or grow one that exists. Everything here is a pipeline and data
change; the frontend reads the manifest and needs no edit.

Before starting, read `GLOBAL_METHODOLOGY.md` §7.2 (the onboarding gate; since iteration 16 its
item 7 is two items, 7A source freshness and 7B systematic research coverage), the project's scope
boundary in `CLAUDE.md`, and `REVIEW_GOVERNANCE.md`. **All of them apply in full to every
country.**

## 1. Research (no code)

**Write the search plan first.** A systematic pass starts with
`docs/countries/<CC>_SYSTEMATIC_SWEEP.md` Part A, committed before any search runs. Part A
declares the window, the geography, the qualifying definitions and the source lanes, and gives
each lane its enumeration method. Part B records what actually ran, lane by lane, as counts. A
pass is `complete` only if every declared lane ran across the whole window; anything less is
`partial`, with the reason. `US_SYSTEMATIC_SWEEP.md` is the template.

Two lanes, each writing only its own files:

- **Sources and readiness** → `docs/countries/<CC>_SOURCE_AUDIT.md`,
  `docs/countries/<CC>_INDEX_READINESS.md`, `data/candidates/<cc>_profile.json`.
  Every source gets a licence verdict: adopt / derived facts only / discovery only / reject.
  Every sector gets a denominator verdict and a §7.1 state. Name the fields that must never be
  read (incident coordinates, reservoir levels, route maps, anything about vulnerability).
- **Incidents and recovery** → `data/candidates/<cc>.json`, the candidate schema used by the
  first five (see any existing queue). Apply `data/curated/systems/inclusion_threshold.json`.
  Record rejects and insufficient-evidence records too: the queue is the audit trail. Separate
  "researched, no public recovery evidence" from "not yet researched" (a search cut short by a
  budget or an unreadable source is NOT YET researched), record `opened` on every source, and
  give every piece of recovery evidence its kind.
  **The queue is not committed** (`data/candidates/README.md`): its rejected and held narratives
  can amount to per-facility damage assessment. Keep it on the research machine.

## 2. Registry

Add one line to `SYSTEMS` in `pipeline/systems.py`, keeping alphabetical order by name:

```python
{"id": "id", "name": "Indonesia", "kind": "country", "admin0_a3": ("IDN",)},
```

`admin0_a3` is Natural Earth's code. Add special administrative units to `SAR_UNITS` in
`build_systems.py` if the country has any. Add any ISO code drift to `ISO_CODE_FIXES`.

## 3. Curated definition

Write `data/curated/systems/<id>/system.json` by hand (copy an existing one):

- `reporting_environment`: one of `systems.REPORTING_ENVIRONMENTS`.
- `geography.units_expected`: the number of first-level units. The build fails if Natural Earth
  disagrees, which is how a dropped region is caught.
- `geography.rulings`: every disputed or specially administered unit, in the Crimea style —
  a sovereignty-neutral analytic choice stated as such. Use `disputed_unassigned` for a unit that
  is drawn but never receives events.
- `sectors`: one entry per sector in `config.SECTORS`, each with `state`, `assessed_readiness`
  and a `reason`. The build refuses SCORED/EXPERIMENTAL until something is computed.
- `sources`. Every source has `last_checked`, `source_release` and `content_vintage` where
  known. A source in use also needs `publication_cadence` and a `stale_policy` from
  `build_systems.STALE_POLICIES`, with `stale_after_days` equal to that policy's days. The limits
  are display policy. They never decide inclusion and never enter a number, and a test enforces
  that.
- `research_gaps`, `audit_docs`.

Also write `episodes.json` and `research_log.json`.

**`episodes.json`.** Declare an episode only on an explicit basis (GLOBAL_METHODOLOGY §5.3):

- `named_hazard`: every member names the same hazard. Records naming the same hazard must
  all be in it.
- `explicit_common_event` or `coordinated_wave`: a cited source calls the records one event or
  one wave. Give `evidence {url, says}`, with the url among the members' sources.
- `explicit_continuation`: the same evidence requirement.

A source that merely lists several incidents is provenance, not an episode. Timing and
proximity never group records. An undeclared record is a `singleton`.

**`research_log.json`.** One entry per pass. Give its `kind` (`systematic` or `targeted`) and,
for a systematic pass, its lanes with a status each. Record the window, the status and the
outcome **counts** only.

Copy the lane's profile to `profile.json`.

## 4. Review the queue

```
.venv\Scripts\python.exe scripts\import_candidates.py <id>
```

**Two reviews before publication (iteration 16).** The researcher who found a record is the
primary reviewer. An independent reviewer then opens the evidence and records a disposition
(`confirmed`, `corrected`, `held` or `removed`) and how many sources they opened, under
`independent_review` in the queue record. The gate refuses a record with no independent
review, with any disposition other than confirmed or corrected, or whose reviewer opened no
source.

Only the frozen iteration-14 list in `review_grandfathered.json` is exempt. That list may only
shrink, and a test enforces it.

For a system with an active kinetic campaign (`conflict_campaigns.json`), the gate also writes
the withheld recovery marker. It keeps status citations and status-bearing capacity notes in
the queue, and it holds any record left uncited (`CURRENT_EVENT_PUBLICATION_POLICY.md`).

A later research pass sets `reviewed`, `review_process` and `research_pass` on its records;
the gate carries the first two into the published `review` block. It applies
`data/curated/systems/review_edits.json`, imports only lane-accepted, sourced,
in-geography, scope-clean records, writes `events.json`, and prints every lane-accepted record
it held back and why. **Read that list.** A scope-scan hit is held for a person; the fix is a
recorded edit with a reason, never a silent rewrite. Read the shipped summaries too: the scan
is a net, not a reviewer (it did not catch a substation described as a city's in-feed).

## 5. Build and test

```
.venv\Scripts\python.exe -m pipeline.run
.venv\Scripts\python.exe -m pytest
cd web && ..\scripts\npm.cmd run e2e
```

Add the country to `COUNTRIES` in `web/e2e/global.e2e.ts` and the unit count to
`test_every_first_level_unit_is_present`.

## 6. Moving a sector beyond CONTEXT_ONLY

Not an onboarding step. It needs the owner decisions in `GLOBAL_METHODOLOGY.md` §8 —
at minimum an approved recovery model for that country (§2) and a denominator on the same basis
as the numerator (§4.2) — plus code that computes and publishes the value with its basis,
vintage and sensitivity. A country composite needs the six-point gate in §7.3.

## What never changes

- No incident coordinates; admin-1 at most; multi-region events stay at country level.
- No ranking of countries, and no field that would allow one.
- Counts are shown with the reporting environment beside them.
- `null` with a reason, never `0`, where a value does not exist.
