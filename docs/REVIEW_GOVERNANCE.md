# Review governance for the country corpora

*Iteration 16. Applies to the five country systems. The Russia theatre's curated workflow is
unchanged: it predates this rule and is not migrated (an owner decision if it ever should be).*

**ONE RESEARCHER MAY DISCOVER; CANONICAL PUBLICATION REQUIRES INDEPENDENT REVIEW.**

## 1. The rule

A research lead can come from one researcher. A record reaches the canonical public corpus
(`data/curated/systems/<id>/events.json`) only after two reviews:

| Review | Who | What it does |
|---|---|---|
| Primary | the researcher who found it | opens the sources, writes the record under the inclusion threshold, the source rules and the scope boundary |
| Independent | a second reviewer who did not write it | opens the evidence again and checks the record against it |

The independent reviewer does not rediscover the event from scratch. They do open enough of the
evidence themselves to validate, separately:

1. **identity** — the source describes this event as the record does;
2. **date** — event date, and end date if any;
3. **geography** — country and first-level region, and nothing finer;
4. **class** — infrastructure class and cause;
5. **threshold** — the clause, on what the source actually says (a peak, not a cumulative total;
   a shutdown, not a fire near a plant);
6. **provenance** — every cited URL public, opened by the reviewer or recorded as not opened, and
   supporting the claim; a paywall, login wall or bot challenge is "not opened" and is never
   worked around;
7. **safe wording** — nothing finer than admin-1, no ranking or criticality framing, no
   dependency or vulnerability language, no component-level damage;
8. **episode** — membership under the explicit-episode rule (GLOBAL_METHODOLOGY §5.3);
9. **recovery** — if published, the status, kind and date the source supports, with an estimate
   never shown as an observation.

The reviewer returns one disposition: `confirmed`, `corrected` (with the exact replacement),
`held` (cannot be confirmed now; stays out of the public corpus) or `removed`. Corrections may only
reduce specificity or fix an error, never add detail. The lead may be stricter than a reviewer
(hold what a reviewer passed) but never laxer (publish what a reviewer held) without a further
independent review.

## 2. Where it is enforced

- `scripts/import_candidates.py` refuses a record without `primary_review.completed` and
  `independent_review.completed`, a passing disposition, and at least one source the reviewer
  opened (review rule 6).
- `pipeline/build_systems.py` (`review_problems`) refuses to build a system whose published record
  claims a review it did not have: a `dual_reviewed` record needs both flags, two reviewers, a
  passing disposition and a reviewer-opened source; a `legacy_single_review` record must be on the
  grandfather list and must not claim an independent review.
- `data/curated/systems/review_grandfathered.json` lists, by id, the records published before the
  rule (iteration 14). It may only shrink: a test fails if it grows past the 94 frozen on
  2026-10-31, and a record leaves it when it is re-reviewed. "Legacy" is a status a record has by
  id; it cannot be claimed.

## 3. What is published

Each record's `review` block, and per country a `review_summary` (counts by status). Never the
reviewer's identity: `reviewed_at`, `review_status`, `primary_review_complete`,
`independent_review_complete`, `reviewer_count`, `disposition`, `source_count`,
`sources_opened_by_reviewer`, `process` and `source_access`. The reviewers' per-record working
files stay in the local candidate queue, because a rationale for holding a record about a named
facility is exactly the negative-information narrative the queue exists to keep private.

## 4. Who the independent reviewer was, honestly

In iteration 16 the independent reviewers were separate model sessions given only the published
record, the review brief and the threshold; none saw the researcher's reasoning, and each had to
open the sources itself. That is independence of context and of evidence-reading, not of model:
the reviewers and the researcher were the same model. A person reading a sample of reviewed
records is the stronger check and remains an owner option.

## 5. Iteration-16 outcomes

| Batch | Records | Confirmed | Corrected | Held | Removed |
|---|---:|---:|---:|---:|---:|
| Retroactive review of the iteration-15 additions | 12 | 3 | 9 | 0 | 0 |
| US systematic sweep, lane-accepted records | 113 | 43 | 58 | 11 | 1 |

The US sweep's 113 lane-accepted records went to six independent review batches. 101 were
published; Part B of [countries/US_SYSTEMATIC_SWEEP.md](countries/US_SYSTEMATIC_SWEEP.md) records
the lane-level counts, including the 92 records the lanes themselves held. The removed record is
Elba Island, whose effect had been inferred from timing.

**After review, at publication.** Jazan's review disposition is *corrected*, but the record is now
held by the active-campaign publication policy: its only citation's address announces a restart
delay ([CURRENT_EVENT_PUBLICATION_POLICY.md](CURRENT_EVENT_PUBLICATION_POLICY.md) §3). This is a
publication hold, not a review finding, so the review counts above are unchanged.

The iteration-15 corrections were: unit-level wording trimmed (El Segundo, Port Arthur), two
recovery claims that overstated their sources (El Segundo's "working to restart" shown as partial
restoration; Isaias' platforms "coming back", unsupported), one wrong date (Ontario thunderstorms
began on 1 July), attributions fixed, corroborating public sources added, and the Saudi Jazan
record's current-status detail removed (§ CURRENT_EVENT_PUBLICATION_POLICY). Two episodes were
dissolved because no source called their records one event: the Ontario/Quebec thunderstorms of
July 2026 and the five Saudi April 2026 records.

## 6. Lead rulings that apply to every review

Recorded so a reviewer and a later researcher apply them the same way:

- **Aggregator figures.** A customer figure that rests only on an outage aggregator (for example
  PowerOutage.us) is held: the threshold definition requires a utility, a state agency, DOE, or an
  outlet citing one of them. An operator's own figure quoted verbatim on an aggregator page passes.
- **Login walls.** A page that shows a log-in prompt over its text counts as not opened, even if
  the text is visible beneath it.
- **Trunk pipelines (clause 3).** An interstate or major transmission or trunk line; a short local
  line, a gathering line, or station and tank piping does not qualify.
- **Hazard names.** The name the source uses, in the corpus form "Hurricane Ian (2022)"; a source
  that says only "winter storm" gets no hazard name.
