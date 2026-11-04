# Research coverage across the six systems (iteration 17)

**SOURCE FRESHNESS IS NOT RESEARCH COMPLETENESS.** This page answers one question for each
system: how was its record of events searched for? Whether its sources are current is a separate
question, answered on each country page (source freshness, and since iteration 17 source health).
Live counts are in `CURRENT_STATE.md` and the manifest's corpus totals. This page carries process
facts only, and a test does not keep it in sync with the data, so it is dated.

*State as of 2026-11-03.*

## The five country systems

Every country has now had a systematic pass, each from a plan committed before searching
(commit `a7f3a36`). **No lane in any country is complete.** A lane is complete only if its
declared universe was searched to the end of the window, 2026-11-03; each lane records how far
it got (`covered_through`).

| System | Research coverage (gate 7B) | Newest systematic pass | Lanes complete | What is missing |
|---|---|---|---|---|
| Canada | **partial** | 2026-11-03, lane completion | 0 of 8 | CG1, CG2, CH1 wait on sources publishing 2023-2026 or 2026; CG3 lacks an IESO archive; CP1's TSB half refused access; CR1 and CU1 have no census source and CU1 ran half its queries; CL1 not run (search cap) ([CA_LANE_COMPLETION_17.md](countries/CA_LANE_COMPLETION_17.md)) |
| China | **partial** | 2026-11-03, first systematic pass | 0 of 6 | Two of about 57 monthly statistical releases read; NEA, SGCC and CSG not enumerated directly; CN4 and CN6 not started; search results dominated by plans and foreign events ([CN_SYSTEMATIC_SWEEP.md](countries/CN_SYSTEMATIC_SWEEP.md)) |
| India | **partial** | 2026-11-03, first systematic pass | 0 of 7 | Every Grid-India / RLDC host refused connection, so the census lane could not run; PIB, PPAC and Coal India not enumerated; IN5 and IN6 not run ([IN_SYSTEMATIC_SWEEP.md](countries/IN_SYSTEMATIC_SWEEP.md)) |
| Saudi Arabia | **partial** | 2026-11-03, first systematic pass | 0 of 5 | SPA renders by script, the ministry site did not respond, Tadawul refused (403), OPEC's MOMR archive refused (402); JODI carries no attribution by design ([SA_SYSTEMATIC_SWEEP.md](countries/SA_SYSTEMATIC_SWEEP.md)) |
| United States | **partial** | 2026-11-03, lane completion | 0 of 9 | G1, G2 and H2 wait on 2026 publications; H1 was not assigned this pass (covered through 2026-10-31); BSEE refused again; P1 enumerated every corrective action order but its second endpoint, PHMSA's incident files, refused (403); L1 ran one terminal of nine; R1 and C1 have no census source ([US_LANE_COMPLETION_17.md](countries/US_LANE_COMPLETION_17.md)) |

What the column means:

- **partial**: a systematic pass declared its lanes before searching, in a committed plan, and
  at least one lane did not reach the end of the window. Every shortfall is stated.
- **unmet**: only targeted searches have been run. No system is in this state any more.
- **complete** would mean every declared lane reached the end of the window from 2022. It is a
  claim about the process, never that nothing else happened. No system is complete.

**Some lanes may never be completable.** The refinery, upstream and coal lanes (US R1 and C1,
Canada CR1 and CU1) have no census source to enumerate, only structured queries. Unless the owner
accepts a written query set as a complete enumeration for these classes, they stay "partial, by
construction". Lanes whose sources publish annually (OE-417, NERC's State of Reliability, the
Canadian hazard census) cannot be complete for the current year until the source publishes.
Both are open owner decisions in ITERATION_17_REVIEW.

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
