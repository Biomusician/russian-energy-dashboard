# Country onboarding

How to add a monitored country, or grow one that exists. Everything here is a pipeline and data
change; the frontend reads the manifest and needs no edit.

Before starting, read `GLOBAL_METHODOLOGY.md` §7.2 (the eight-point onboarding gate) and the
project's scope boundary in `CLAUDE.md`. **Both apply in full to every country.**

## 1. Research (no code)

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
- `sources` (each with `checked`, `cadence` and `stale_after_days` unless rejected),
  `research_gaps`, `audit_docs`.

Also write `episodes.json` (any records that share one hazard or one source statement; the
rule is in GLOBAL_METHODOLOGY §5.3 fix 4 as implemented in iteration 15) and
`research_log.json` (one entry per research pass: window, status, and outcome COUNTS only).

Copy the lane's profile to `profile.json`.

## 4. Review the queue

```
.venv\Scripts\python.exe scripts\import_candidates.py <id>
```

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
