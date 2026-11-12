# Research coverage across the six systems (iteration 18)

**SOURCE FRESHNESS IS NOT RESEARCH COMPLETENESS.** This page answers one question for each system:
how was its record of events searched for? Whether its sources are current is a separate question,
answered on each country page. It carries process facts only and is dated.

*State as of 2026-11-10.* The Gulf systems' coverage is in [GULF_RESEARCH_COVERAGE.md](GULF_RESEARCH_COVERAGE.md);
the iteration-20 continuation pass is summarised in [ITERATION_20_REVIEW.md](ITERATION_20_REVIEW.md). Each country
page carries the live state.

## The coverage model

Since iteration 18 every lane states two things, kept apart: how far the analyst got (`execution`:
`not_started`, `partial`, `declared_search_complete`, `enumerated_complete`) and what the source
allows (`source_window`: `current_through_end_date`, `publisher_not_yet_released`, `inaccessible`,
`no_census_exists`, `rolling_archive_gap`, `unknown`). There is no percentage: a lane waiting on a
publisher and a lane that ran two of ninety queries must not add up to one number. A declared query
set is never a census. A lane stopped by this pass's own search allowance says so with `stopped_by`.

## The five country systems

**The 2026-11-10 pass stopped early.** A shared limit of 200 web searches per turn was reached. It
was not worked around. Each lane states what did not run.

| System | Lanes | Executed as far as declared | Of which carried from an earlier pass | Stopped by the search limit | Detail |
|---|---|---|---|---|---|
| Canada | 8 | 2 | 2 | 2 | [CA_LANE_PASS_18](countries/CA_LANE_PASS_18.md) |
| China | 6 | 4 | 0 | 1 | [CN_LANE_PASS_18](countries/CN_LANE_PASS_18.md) |
| India | 7 | 0 | 0 | 4 | [IN_LANE_PASS_18](countries/IN_LANE_PASS_18.md) |
| Saudi Arabia | 5 | 0 | 0 | 3 | [SA_LANE_PASS_18](countries/SA_LANE_PASS_18.md) |
| United States | 9 | 3 | 2 | 2 | [US_LANE_PASS_18](countries/US_LANE_PASS_18.md) |

"Executed as far as declared" is not complete knowledge. The per-lane tables and limitations are in
each country's Part B, and on the country page under Research coverage.

## The theatre

The theatre's corpus is not under the country-system research model. It is enumerated from the
Wikipedia strike table, pinned per build, plus a curated set of incidents, and its coverage is
stated as a ratio in the ribbon (enumerated oil strikes against reported). That ratio is a
different measure from 7B and is not comparable with it. Iteration 17 gathered no new tactical
detail for the theatre; it reviewed only what was already published.

## How the search was done in iteration 17, honestly

- **Search budget.** Each research agent had a fixed personal search cap (15 to 30 searches)
  and wrote its lane log after every source family, so a cap hit lost nothing already done. The
  caps, not the sources, are why US L1, Canada CU1 and CL1, China CN4 to CN6 and India IN5 and
  IN6 are short.
- **Refused access is never worked around.** Grid-India and the RLDCs, Tadawul, OPEC's MOMR
  archive, BSEE, PHMSA's incident files, TSB, ferc.gov and several news sites refused automated access. Each is recorded
  as a reason, not bypassed.
- **Review.** Every lane-accepted record went through the blind three-role review
  ([REVIEW_GOVERNANCE.md](REVIEW_GOVERNANCE.md) §7) before import: 13 records, 10 published and
  3 held. The reviewers were separate model sessions: independent in context and
  evidence-reading, not in model.

## Order of work before Wave 2

1. The lanes stopped by a search cap, not by a source: US L1, Canada CU1 and CL1, China CN4 to
   CN6, India IN5 and IN6.
2. The owner's rulings on query-set lanes and annual-publication lanes, which decide whether any
   lane can ever read "complete".
3. Re-run US G1, G2, H1 and H2, Canada CG2 and CH1 when their 2026 data is published.
4. India's census lane from a network that Grid-India does not refuse, or by the owner's
   decision that RPC minutes are an acceptable proxy.
