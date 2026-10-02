# Iteration 12 — the refresh stopped and nothing said so

Working notes for the iteration. The numbers in this document are the ones observed at the time
each finding was made; for current figures see [CURRENT_STATE.md](CURRENT_STATE.md).

---

## 1. The outage

On **2026-10-01** the deployed dashboard was serving `as_of 2026-09-20`: eleven days stale, with
no indication anywhere on the page. A fresh build the same day gave ESDI 10.38 against the 12.49
production was showing, and 176 events against 175.

The refresh workflow had not been disabled and had not stopped running. It fired every morning:

| Runs | Dates | Result |
|---|---|---|
| #8–#26 | 2026-09-02 → 09-20 | success |
| #27–#37 | 2026-09-21 → 10-01 | **failure, 11 consecutive** |

Step results on every failed run: `Build dataset` **ok** → `Test` **FAIL** → `Commit if data
changed` **skipped**. The pipeline was healthy throughout. A failing test was discarding a correct
build, every day, silently.

### Root cause

`tests/test_pipeline.py::test_transmission_alternative_models_are_deterministic_and_bounded`
asserted:

```python
assert am["E_esdi_if_transmission_removed"] <= snap["esdi"] + 1e-6
```

**The assertion is mathematically false.** The ESDI is a weighted *mean* over the covered sectors,
not a sum. Excluding a sector whose value sits *below* the mean of the others necessarily *raises*
the mean. The identity is

```
esdi − E = w_tx · (v_tx − E) / (w_tx + W_others)
```

so `sign(esdi − E) = sign(v_tx − E)`. Removing transmission lowers the headline only while
transmission is the above-average sector.

Pinned to the day by rebuilding at successive dates:

| as_of | transmission | ex-transmission mean | assertion |
|---|---|---|---|
| 2026-09-19 | 12.77 | 12.69 | pass |
| 2026-09-20 | 12.48 | 12.49 | pass, by 0.01 |
| **2026-09-21** | 12.20 | 12.29 | **fail** |

2026-09-21 is exactly the date of the first failed run. Ordinary time decay took production down.

The pipeline arithmetic was recomputed independently from `methodology/scoring.json` and is
correct (10.3771 → 10.38 published; 10.4687 → 10.47 published). **No methodology change was made.**
The test now asserts the identity — Model E must equal the ex-transmission composite through the
shipped `_composite`, and the direction of the move must *follow* `sign(transmission − E)` rather
than be assumed. A pipeline-free unit test shows both directions are reachable.

### The lesson, stated plainly

A test that is true at today's values and false at tomorrow's is not a test. It is a timer. And
because `refresh.yml` gates its commit on the suite, every such timer is wired to publication.

---

## 2. Publication freshness (P2)

The deeper defect is that **eleven days passed and the product never said so**. The only freshness
signal on the page was `· live`, which meant nothing more than "the scrubber is at the last
timeline step" — equally true of a payload frozen a month earlier.

Design, and the two rules behind it:

1. **The age is computed in the browser, against the reader's clock.** The payload ships reference
   dates and thresholds and deliberately **no precomputed age**: an age computed at build time
   freezes with the build and would read "0 days old" forever on a dashboard that had stopped
   rebuilding. That is the exact lie being fixed. A test pins the emitted field set so a day count
   cannot be added later.
2. **Unknown, unclassifiable and stale stay three different answers.** A payload with no readable
   date gets no age at all; one with no published cadence gets a factual age and no verdict.
   Neither is reported as fresh, and neither is reported as stale — asserting staleness we cannot
   establish is the same error as asserting freshness we cannot.

Thresholds live in `PUBLICATION_CADENCE` (`pipeline/config.py`) and travel in the payload, so
neither Python nor a React component hardcodes one. They are deliberately **separate** from
`data_quality`'s source-freshness thresholds, and a test asserts they differ: a fresh build of
stale sources and a stale build of fresh sources are different failures.

Where it surfaces: a full-width strip above the ribbon at headline weight; the ribbon's `live`
suffix, now earned; a "How old this page is" block leading the Data Quality panel; the Briefing
overlay footer; and the exported PNG, above the caveat and not droppable by an Include toggle —
because an image outlives the page it came from.

Defects found while verifying this, each caught in the browser rather than by a test:

- The floating drawer toggles sat on top of the banner and covered the words "NOT CURRENT" at
  narrow widths.
- "has not rebuilt in 11 days ago" — the age was assembled from two pieces and both carried "ago".
- The ribbon measured age in local time and the export in UTC, so one page showed "11 days" in the
  header and "12 days" in the briefing footer.
- `briefing.test.ts`'s `bundle()` helper re-spread its argument *after* the merged snapshot, so
  `bundle({snapshot: {...}})` silently produced a fixture with no as-of, no sectors and no regions.
  Any test using it was testing nothing.

---

## 3. The other time bombs

A test-architecture audit, driven by rebuilding the dataset at future dates and replaying the real
weekly series, found five more assertions of the same class.

| Assertion | What turns it | Fix |
|---|---|---|
| `abs(total − headline) <= 0.02` over two 2-dp floats | Exactly 0.02 evaluates as 0.020000000000000462. ~4 of 248 real weekly steps. Set the published `exact` flag **and** was retyped in the test | Compared in integer hundredths through one shared `within_rounding` |
| `snap["esdi"] > 0` | A true 0.00 is reachable by decay (confirmed at 2027-07-15) | Floor the whole *series*, which decay cannot flatten; a quiet world is a finding, not a failure |
| Crimea's `esdi > 0` | Rounds to 0.00 on 2027-01-23 | Assert the exposure is *counted* while live disruptions exist, and that a zero is explained |
| `transmission_concentration["top"]` non-empty | No live transmission facility after ~2027-02-20 | Conditional on there being a live transmission disruption |
| live refining contributors; refining-denominator offenders | No live refining facility after ~2027-06-26 | Invariants over whatever exists; loud skip when there is nothing |
| `unscorable_only` non-empty | The one region carrying it loses it to decay | Skip, with the branch covered unconditionally by a synthetic test |

Also fixed: `top_region_share_pct` divided a 3-dp-rounded numerator by an exact denominator and
published **101.3%** once the sector had decayed far enough. A share of a whole cannot exceed the
whole.

Re-verified by rebuilding and running the full suite at 2026-12-15, 2027-01-31, 2027-03-15,
2027-07-15, 2027-09-15 and 2028-06-01.

### A test that tested nothing

The guard for the unscorable-zero category fed `regional_explanations` a hand-made fraction map
(`{"gas": 0.4}`) that the real scorer can never produce — `_share` returns 0 for a sector with no
denominator, so the accumulation loop drops the facility before its sector is recorded. Real data
arrives through `unscored_by_region`, a separate map, and nothing exercised it. There is now a
synthetic test that drives the parameter real data actually uses.

---

## 4. A zero that lied

Rebuilding at 2027-01-31 caught Crimea publishing **"Nothing is recorded as impaired"** while
carrying two live electric-generation disruptions.

A facility can sit in a sector the index *does* score and still contribute exactly 0.00, because it
carries no capacity figure and `_share` has no numerator to work with. The zero taxonomy had four
categories and none of them covered that, so it fell through to "nothing happened".

**Eight regions in the live payload were affected** — Moscow and Volgograd among them. New
category `COVERED_IMPAIRMENT_WITH_NO_CAPACITY_FIGURE`, checked *before* the uncovered-sector case
so that case's name stays true, carrying the sectors it could not size.

No number changes: this labels an existing 0.00 correctly. An unsized facility is an unknown
magnitude, and an unknown is not a zero — which is the entire reason this taxonomy exists.

---

## 5. Links that could lie, or crash

- `?r=constructor` found a region. `regions[code]` on a plain object reaches `Object.prototype`,
  so the existence check passed and a dossier rendered headed "Object". `?cmp=constructor` went
  further: the comparison tray read `sectors` off the phantom, threw, and — with no error boundary
  anywhere — the app unmounted to a white page. `m=constructor` produced a legend reading "Change
  in ESDI · 90 days" over a surface computed from event counts.
- The **"none" filter button produced a link that showed the recipient more than the sender saw**.
  An empty set encoded as `cls=`, which decoded as "no filter pinned", which the app read as ALL.
- There was no error boundary at all.

Fixed: own-property lookups everywhere a query-string value indexes an object; an explicit empty
encoding with three cases kept apart (not pinned → all; pinned to nothing → nothing; stale keys →
all); and an error boundary that names the failure and offers to reopen without the query string.

Legacy `cls=` still means "unspecified", so links already in the wild are unaffected.

The existing scope test asserted that a query string *typed into the test itself* lacked `lat` and
`lon`. It could never have failed. It now drives the real encoder and pins the whole key
vocabulary.

---

## 6. Exports

- A **filtered** frame said nothing about being filtered: same title, same caveat, a smaller
  number and no explanation for it.
- For the events metric the headline was `incident_total` — the as-of total for the whole corpus —
  printed beside a map that might be scrubbed to 2024 and filtered to one cause.
- The **Legend checkbox had been shipped since P8 and was read by nothing**: `options.legend`
  appeared in no expression in the compositor, so the exported image had no colour key at all.
- Switching the **title off removed the metric, the value and every date**, leaving a coloured map
  of Russia that could be from any day of the war.

All four fixed and verified by capturing the PNG from the real export path and reading its pixels.

### Lifecycle A/B

`abPosition` compared milestone dates against what the reader *typed*, while the A and B figures
beside them come from the nearest earlier weekly series point — up to six days apart. A milestone
in that gap was labelled "by A" although the A value excluded it. Its own comment claimed "no
second date engine"; there were two. Now resolved through the same series the comparison reads,
extracted and unit-tested.

---

## 7. CI

`ci.yml` runs the frontend (typecheck, vitest, build) and the Python suite on push and pull
request. The frontend had gated **nothing**: `refresh.yml` never built it and Vercel runs its own
build at deploy time.

It is deliberately **not** added to `refresh.yml`. The lesson of §1 is not "add more gates to the
refresh" — it is that *the set of things able to freeze publication must be as small as the job
that publishes*, and frontend tests have no bearing on whether the dataset is sound. `refresh.yml`
also stays toolchain-free, which is a standing architecture decision.

Both checkouts gain `fetch-depth: 0`. `data_quality` dates the curated CSVs from `git log -1`,
which a depth-1 clone cannot answer: the 2026-09-20 payload published "retrieved 2026-09-19, 1 day
old" for files last genuinely edited on 2026-08-29. A provenance date that is wrong is worse than
one that is absent.

`scripts/ci_data_changed.py` stripped volatile keys only at the top level, so the ledger's
`current_build` survived and every same-day rerun read as substantive — the guard had never once
done its job. Now recursive, and tested against the real emitted files rather than a three-key
fixture.

---

## 8. Documentation

`docs/HANDOFF.md` said "Latest iteration: ITERATION_9_REVIEW.md" while reviews 10 and 11 both
existed, and had no section for either. README.md and CLAUDE.md both pointed at the iteration-5
review as "the current state", seven iterations on.

Worse, three documents actively contradicted the code:

- **METHODOLOGY §7.2 said Crimea was excluded** from the index — the opposite of §5a of the same
  document, of `CLAUDE.md`, and of the code. The Crimea lint missed it because the sentence named
  neither "composite" nor "the index". A future session reading it would have "fixed" working
  behaviour.
- **METHODOLOGY §9 described the pre-iteration-9 way-based pipeline builder**, a design `CLAUDE.md`
  explicitly forbids.
- **METHODOLOGY §2 gave the wrong per-event formula**, omitting `damage_severity` and presenting
  the deprecated `status_multipliers` as live.

All three corrected, with the error recorded in place rather than silently deleted — a reader who
finds the two accounts needs to know which one was wrong.

`test_the_handoff_cannot_lag_the_newest_iteration_review` now compares integers parsed from
`<!-- current-iteration: N -->` markers against the highest-numbered review file. Only explicit
markers and line-anchored headings are read; no prose is parsed, deliberately — the nearest
existing lint once matched the token "never" inside "whenever". The max is numeric, because a
string sort picks `ITERATION_9` over `ITERATION_11`.

---

## 9. The one I caused

`ci.yml`, added in §7, ran a full `pipeline.run` in its Python job. `data/raw` is gitignored, so
every push was a cold full fetch of Wikipedia and Overpass. Five pushes in one hour became five
fetch cycles against free public endpoints, and CI run #2 failed inside the fetch rather than in
anything it was testing.

It no longer builds. `data/processed` is committed, so the suite asserts on the bytes that ship —
which is the better test anyway: a job that builds its own payload and then checks it is grading
its own homework. The two tests that genuinely need a build or a live request are opt-in behind
`RUN_BUILD_TESTS`, which `refresh.yml` sets because it has already fetched and holds a warm cache.

Recorded here rather than quietly fixed, because it is the same shape as every other finding in
this document: a guard added in good faith that did something other than what it was for.

Side effect worth having: the default suite went from 100 s to 7 s.

---

## 10. Deferred, with reasons

Not done in this iteration. None is blocked; each is a scope decision.

**Features, deferred from iteration 11 and again here.** Saved workspaces; the command palette;
the multi-page Analyst Report; clipboard image copy (`copyBlobToClipboard` still has no callers).
Each adds interaction and persisted state without closing an analytical gap, and this iteration
was already large.

**Still open in the test architecture.**

- Artifact-guarded tests still skip when their file is missing. `REQUIRED_WEB_FILES` is the
  backstop and now covers the iteration-10/11 payloads, but the skip-is-a-pass shape remains.
- No end-to-end browser test. vitest runs in the `node` environment with no DOM, so there are no
  component tests at all; `App.tsx`'s validation, the replaceState effect and the Dossier tab
  effect are untestable as written.
- Several tests still assert on a hand-built input rather than on what the pipeline produces —
  `centroid.test.ts` copies `CLASS_PRIO` from `MapPanel` and tests the copy; `whatChanged.test.ts`
  composes its own lambda and would pass if the panel regressed to the behaviour it documents.
- `briefing.test.ts` hand-casts its bundle and uses `UA-43` for Crimea, which is not the real
  code (`UA-CR`).

**Still open in the data.**

- `dashboard_first_seen_build` is structurally inert: `lifecycle.build` accepts
  `first_seen_by_incident` and nothing ever passes it, so all 26 episodes carry `first_seen:
  null` and the UI branch that would show it never renders. The payload already DISCLOSES this
  honestly (`available: false`, with a note saying it is not a publication date), so it is a
  missing feature rather than a false claim. Populating it needs persisted per-incident
  first-seen state with an explicit "present before tracking began" marker for the existing
  corpus — anything else would invent a date.
- `http_source_metadata` is a declared retrieval basis that nothing produces.
- Incident `first_seen` / `last_verified` are dead temporal fields.
- GIE storage, GEM coal, GEM geometry precedence, the WRI per-unit-date denominator defect, and
  the GEM quarterly release, all carried forward from iteration 10.

**Standing.**

- `_DENIAL` in the semantic lint still uses raw substring exemptions. The frozen-payload lint was
  given word-boundary negation handling in §8; the Crimea lint's denial list was not revisited.
- The zero taxonomy now reaches the hover card, the rankings and the exported label (§4), but the
  PNG's own region label is the only export surface that carries it.
