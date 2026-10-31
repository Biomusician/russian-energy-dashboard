# Iteration 15 — depth: reproducible history, episodes, freshness, research

Theme: **make what is already shown hold up better, before showing anything new.** No Wave 2
country, no score, no methodology change to the theatre's index.

Live figures are in [CURRENT_STATE.md](CURRENT_STATE.md). Figures quoted below are dated
findings from 2026-10-30 and are deliberately not kept current.

This iteration ran unattended overnight, at the owner's request, with no prompt beyond "deliver
the best production version" and a pasted recommendation (depth before Wave 2: reproducibility,
country research, episode modelling, safe research provenance, testing gaps). Every judgement
call that would normally have gone to the owner is listed in §8 rather than taken silently.

---

## 1. Historical builds no longer drift with Wikipedia

`--as-of 2026-08-28` used to read **today's** strike-table article and filter it by date. Editors
revise old rows, add citations and correct dates, so the frozen regression moved from 18.50 to
16.8 with no code change (ITERATION_14_REVIEW §9). A historical build that changes when someone
edits Wikipedia is not a historical build.

`pipeline/wikirev.py` now pins all three live article inputs (strike table, refinery list, fuel-
crisis coverage benchmark) to the last revision saved on or before the end of the `--as-of` day.
Revisions never change, so that fetch is cached indefinitely. A current build reads the latest
revision as before and records which one in `snapshot.source_revisions`, so any published build
can be re-fetched by `oldid`.

**Verified:** the pinned frozen build ran twice with the same output fingerprint (`bda51e4a`) and
no refetch on the second run. Under pinning the frozen reference is **ESDI 16.16**, read from
revisions 1371858526 (strike table), 1371652673 (refinery list) and 1370661946 (benchmark). The
gap from the 18.50 recorded at the time is now attributable to code and curated changes since,
not to Wikipedia.

**Not done:** OSM geometry and the curated CSVs are still read as they are now. The CSVs are
versioned by git; OSM is not pinned. This removes the one input that changed under a fixed commit.

---

## 2. Episodes: one storm is one episode

Hurricane Helene produced four state outage records. Counted as records, the US looked four
times as disrupted by it as by a refinery fire. GLOBAL_METHODOLOGY §5.3 fix 4 is now
implemented for the country systems:

- `data/curated/systems/<id>/episodes.json`, hand-curated under a stated rule: records share an
  episode only when they name the same hazard, one source statement reports them together, or a
  later record reports the same shortfall continuing. Being close in time or place is never
  enough.
- The build refuses an episode file that would merge, drop or double-count a record.
- Every record carries an `episode_id`; a record in no declared episode is an episode of one.
- Pages give counts in both records and episodes; the event list groups multi-record episodes;
  a region view keeps records separate and says which episode each belongs to; the PNG states
  both counts.
- Onboarding gate item 5 is now **met** for all five countries.

At release: US 37 records / 26 episodes, CA 26 / 24, CN 15 / 12, IN 16 / 14, SA 12 / 8.

---

## 3. Per-source freshness and a public research log

- Every registry source now states when it was last checked, its publication cadence and a stale
  limit. The page flags a source past its limit on the **reader's** clock (the iteration-12 rule:
  an age computed at build time freezes with the build).
- `research_log.json` per country publishes each research pass: window, scope, `complete` or
  `partial` with the reason, and outcome **counts only**. The build refuses a non-count field in
  the outcome. This is the safe form of research provenance: the queue's per-record narratives,
  which the iteration-14 safety red team found could read as damage-assessment feedback, stay on
  the research machine.
- Gate item 2 is **met**. Item 7 stays **partial**, honestly: every pass so far was partial, and
  the gate follows the newest pass.
- Every context metric now states its measurement basis (gate item 4 met everywhere), restated
  from the metric's own source and note; nothing new is asserted.

---

## 4. Country research: twelve events, every source read

A targeted pass over the gaps iteration 14 named plus the major 2025-2026 events. Every source
cited was opened and read in a browser; anything seen only as a search snippet is not cited. A
paywall, an "access denied" or a bot challenge meant the source was not used, never worked around.

| System | Added | Notes |
|---|---|---|
| US | 6 | PBF Martinez fire (full restart May 2026); MISO Louisiana load shed; Chevron El Segundo fire; Valero Port Arthur explosion; Hurricane Isaias grid outages and Gulf shut-ins (one episode) |
| CA | 3 | Quebec windstorm (Mar 2026); Ontario and Quebec thunderstorms (Jul 2026, one episode) |
| CN | 1 | Typhoon Ragasa (Sep 2025) |
| IN | 1 | Cyclone Montha (Oct 2025) |
| SA | 1 | Jazan refinery shutdown (Jul 2026); restart not confirmed: `RESEARCHED_NO_PUBLIC_EVIDENCE` |

Four were leads the earlier lane had left as "insufficient evidence, budget exhausted"; they were
resolved and replaced in place under the same ids. Leads that did not reach the threshold or
could not be read are named in each country's research gaps (Typhoons Saola, Kajiki and Noul with
no readable customer count; Remal with no Indian count; the 2024 Sharurah outage counted in
residents, not customers; Fiona in New Brunswick at about 95,000, under the 100,000 floor).

**Safety read-through.** The scope scan passed every record, and every record was then read as it
ships. Two were trimmed: a sentence on the Louisiana grid's generation margin (dependency
analysis, however public) and a sub-provincial placement for Ragasa. Left out from the start:
parish and district names, the distribution-network damage inventory for Montha, the explosion's
felt distance at Port Arthur, unit-level damage at Jazan, and "largest refinery" framing for El
Segundo.

---

## 5. Tests

- Python: revision pinning (past date pins, current date records, missing revision fails loudly,
  snapshot names its revisions); episodes (partition, refusals, as-of filtering, Helene as one
  episode of four); sources and research log (stale limits, counts-only outcome, gate 7 follows
  the newest pass); import-gate provenance; every iteration-15 record says a source was read.
- Browser: episode grouping and counts; region view's episode note; source table and research
  log; a source past its limit flagged on the reader's clock (forced via a routed payload); a
  region deep link for every country, counting multi-region records beside, never in, the region.
- The US map golden was re-recorded after the new data (California went from one record to three;
  the diff was checked and showed that state only).

---

## 6. Verification

- Python 433 passed, 2 skipped (env-gated). Frontend unit 227. Typecheck and build clean.
- Browser 69 locally (see §7 for production).
- Current build: ESDI 8.33, 184 events — the theatre is unchanged by this iteration.
- Frozen reference (pinned): 16.16, byte-stable across two runs.

---

## 7. Release

See HANDOFF and the final report for the production run.

---

## 8. Judgement calls taken without the owner (to review)

1. **The iteration's scope itself.** No Iteration 15 prompt was received; scope came from the
   pasted recommendation. Wave 2 was not started.
2. **Twelve events published on a single researcher's reading.** Same review gate and scope scan
   as iteration 14, plus a full read-through, but no independent second reviewer and no red-team
   lane this time.
3. **A new Saudi event under a live attack campaign** (Jazan), including its restart status. This
   follows the theatre's doctrine and iteration 14's Saudi records; ITERATION_14_REVIEW §10 item 7
   (whether to publish recovery status during a live campaign) is still the owner's.
4. **Episode rule and the Saudi grouping.** Five April 2026 Saudi records reported in one ministry
   statement are one episode (`single_statement`). That groups attacks into a wave, as the
   theatre's `episode_id` does for strike nights.
5. **Gate item 7 tied to research completeness.** I made "freshness" mean the event search's
   coverage as well as per-source dates, which keeps item 7 partial. A narrower reading would
   mark it met.
6. **`stale_after_days` values** (120 / 180 / 400 by cadence) are my choice, not a methodology
   decision, and are not used in any number.
7. **The frozen reference value changed** from 16.8 to 16.16 because its inputs are now pinned
   (§1). Nothing in production depends on it.
