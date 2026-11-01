# Research coverage across the six systems (iteration 16)

**SOURCE FRESHNESS IS NOT RESEARCH COMPLETENESS.** This page answers one question for each
system: how was its record of events searched for? Whether its sources are current is a separate
question, answered on each country page. Live counts are in `CURRENT_STATE.md`. This page carries
process facts only, and a test does not keep it in sync with the data, so it is dated.

*State as of 2026-10-31.*

## The five country systems

| System | Research coverage (gate 7B) | Newest systematic pass | Lanes searched in full | What is missing |
|---|---|---|---|---|
| Canada | **partial** | 2026-10-31, window 2022-01-01 to 2026-10-31 | 0 of 7 | CR1, CU1, CL1 not fully run (search budget); CG1, CG2, CH1 wait on sources publishing; TSB refused access ([CA_SYSTEMATIC_SWEEP.md](countries/CA_SYSTEMATIC_SWEEP.md) B.6) |
| China | **unmet**: targeted searches only | none | — | A systematic plan. Media-only reporting environment; the plan has to say what a lane can be when no regulator publishes events |
| India | **unmet**: targeted searches only | none | — | A systematic plan. Grid-India and RLDC grid-disturbance reports are the obvious first lane |
| Saudi Arabia | **unmet**: targeted searches only | none | — | A systematic plan. The active-campaign policy governs what a sweep may publish |
| United States | **partial** | 2026-10-31, window 2022-01-01 to 2026-10-31 | 1 of 9 | G1 and G2 wait on 2026 publications; H2, U1, P1 and L1 have stated shortfalls; R1 and C1 have no census source ([US_SYSTEMATIC_SWEEP.md](countries/US_SYSTEMATIC_SWEEP.md) B.6) |

What the column means:

- **partial**: a systematic pass declared its lanes before searching, in a committed plan, and
  at least one lane did not run across the whole window. Every shortfall is stated.
- **unmet**: only targeted searches have been run. Events nobody searched for are missing.
- **complete** would mean every declared lane ran across the window from 2022. It is a claim
  about the process, never that nothing else happened. No system is complete.

**Two lanes may never be completable.** The refinery and gas-processing lane (US R1, Canada CR1)
and the US coal lane (C1) have no census source to enumerate, only structured queries. Unless
the owner accepts a written query set as a complete enumeration for these classes, the best
these lanes can reach is "partial, by construction". That is an open decision in
ITERATION_16_REVIEW.

## The theatre

The theatre's corpus is not under the country-system research model. It is enumerated from the
Wikipedia strike table, pinned per build, plus a curated set of incidents, and its coverage is
stated as a ratio in the ribbon (enumerated oil strikes against reported). That ratio is a
different measure from 7B and is not comparable with it.

## How the search was done in iteration 16, honestly

- **Search budget.** Searches were run by research agents that share one per-turn web-search
  budget. The US sweep used most of it. Canada's grid lanes ran partly on it, and its facility
  lanes ran without it, from datasets and pages they could open directly. That is why Canada's
  CR1, CU1 and CL1 are partial for a reason that is about this run, not the sources.
- **Refused access is never worked around.** TSB, BSEE's release listing, one FERC presentation
  and several news sites refused automated access. Each is recorded as a reason, not bypassed.
- **Review.** Every published record from a sweep was opened and judged by a second, independent
  reviewer before import ([REVIEW_GOVERNANCE.md](REVIEW_GOVERNANCE.md)). The reviewers were
  separate model sessions: independent in context and evidence-reading, not in model.

## Order of work before Wave 2

1. Finish Canada's facility lanes in a session with search budget. It is the cheapest
   completion available.
2. Write systematic plans for India, then Saudi Arabia, then China, and run them.
3. Re-run US G1, G2 and P1 when their 2026 data is published.

Until each of the six current systems has had at least one systematic pass, adding countries
would add more records searched in an unknown way.
