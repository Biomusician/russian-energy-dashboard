# Historical reproducibility: three questions, three answers

*Written in iteration 16. Live figures are in [CURRENT_STATE.md](CURRENT_STATE.md); numbers
below are dated examples, not current values.*

"What was the index on 28 August?" is three different questions. The project used to answer all
three with one command and one number. They are now separate concepts with separate names, and
none of them may borrow another's label.

| | Concept | Question it answers | Where it comes from | Label in data |
|---|---|---|---|---|
| A1 | **Current-evidence reconstruction, pinned sources** | Given today's accepted corpus and code, with the live article inputs pinned to their revision on date D, what does the model estimate for D? | `python -m pipeline.run --mode reconstruction --as-of D --output-root <dir>` (never `data/processed`; refused there since iteration 17) | `snapshot.history_concept.mode = "current_evidence_reconstruction"`, label "Pinned-source reconstruction for D" |
| A2 | **Current-evidence reconstruction, today's sources** | The same question, with today's article revisions: the timeline and the comparison workspace | the weekly series in `history_series.json`, computed inside a current build | `history_series.semantics`; on screen "CURRENT-EVIDENCE RECONSTRUCTION FOR D" beside any past date |
| B | **As-published snapshot** | What did this dashboard actually serve to readers then? | The payload committed at a commit Vercel actually deployed; `production_history.json` | `production_history.concept = "as_published"` |
| C | **Engineering regression fixture** | Did a scoring transformation change unexpectedly? | Synthetic and immutable inputs held in `tests/` | Test names; never published |

A1 and A2 answer the same question with different article revisions, so they can differ for the
same week (16.16 for the pinned 2026-08-28 run, 16.51 for the series' 2026-08-29 point at iteration
16; the pinned run reads 16.48 at iteration 17). They used to share one label; since the history red team they do not.

The doctrine in one line each:

- ONE EVENT DATE IS NOT ONE KNOWLEDGE DATE.
- CURRENT RECONSTRUCTION IS NOT AS-PUBLISHED HISTORY.
- PINNED INPUTS ARE NOT A TIME MACHINE FOR CURRENT CURATION.

---

## 1. A — current-evidence reconstruction

A build for a past date runs **today's** code over **today's** curated corpus and evaluates it
at date D. Since iteration 15 its live Wikipedia inputs are pinned to the revision saved on or
before the end of D (`pipeline/wikirev.py`). That removes the one input that changed under a
fixed commit. It does not turn the build into a time machine:

- the curated CSVs and the country corpora are read as they are now, including records research
  added long after D;
- the code is today's, including every methodology change since D;
- OSM context geometry is read as it is now (see §4 for why that does not matter to the score).

So a reconstruction answers "what does today's evidence say about D?" — which is usually the
more useful question for analysis, and never the question "what did readers see on D?".

**The pinned-source reconstruction reference.** `--mode reconstruction --as-of 2026-08-28
--output-root data/reconstruction/2026-08-28` is the project's standing
reconstruction reference for decomposing a change without time decay. At iteration 15 it gave
**ESDI 16.16**, byte-stable across reruns. At iteration 17 it gives **16.48**. With no embargo
(D = 0) the same corpus gives 16.00, so the theatre's campaign embargo
(`docs/OPERATIONAL_STATUS_DELAY_OPTIONS.md`), which withholds six recovery records under 60 days
old on 2026-08-28, adds +0.48, and the iteration's other curated changes (three open-horizon
estimates held locally, corrected text) account for −0.16. It is a type-A value. It is not "frozen history" and
not "as published": it moves, by design, whenever code or curated data change. Its earlier
values (18.50, then 16.8) also drifted with Wikipedia edits; pinning removed that drift only.

A build labels itself. `snapshot.history_concept` reads `current_build` for a current-date build
and `current_evidence_reconstruction` for a past date, and the console prints a warning that the
value is not what was published. `production_history.history_concept()` is the one function that
decides the label, and a test holds that a past date can never be labelled anything else.

## 2. B — as-published history

`pipeline/production_history.py` assembles `production_history.json` from two things that cannot
be rebuilt and so cannot drift:

1. **The deployment ledger** (`data/curated/production_deployments.json`), captured from GitHub's
   public deployments API by `scripts/capture_deployments.py`. Vercel records every production
   deploy against the exact commit it built.
2. **The payload committed at that commit**, read out of git (`web/public/data/snapshot.json`
   and `incidents.json` at that SHA).

Nothing is re-run. Each entry records the commit SHA, the time it began to be served, the
commit time, the analytical `as_of`, the headline ESDI, the event count, the schema version,
fingerprints (methodology file blob, input-group digest, output fingerprint, snapshot blob), the
events it added and removed relative to the build served before it, and its **lineage**:

| Lineage | Meaning |
|---|---|
| `deployed` | the ledger records a successful production deploy of exactly this commit |
| `deploy_status_unverified` | the ledger records a production deploy; its final status was not fetched (GitHub's unauthenticated API allows 60 calls an hour). Every status that was fetched was `success` |
| `bot_refresh_presumed_deployed` | a daily-refresh bot commit made after the ledger was last captured. Each bot commit is pushed alone and Vercel deploys every push to `main`; in the captured window this held for every bot commit after the first deploy. Presumed, and labelled presumed |

Most commits on `main` were never served: a push of several commits deploys only its tip. Those
commits are not in the history at all. A failed deploy is excluded.

**`earliest_reliable_as_published_date` is 2026-08-29**, the first recorded production deploy.
Before that the as-published value is **unavailable**. It is not reconstructed and relabelled.
On 2026-08-28 the dashboard published nothing that can be shown; the first deploy, on 29 August,
served `as_of` 2026-08-29 with ESDI 15.34.

**The served build on a day** is the latest entry whose `served_from` is on or before that UTC
day (`production_history.as_published_on`). Between 2026-09-21 and 2026-10-01 the refresh bot
failed and nothing was deployed, so the build served through that gap is the last one before it
— exactly what readers saw.

**Keeping it current.** The daily build regenerates `production_history.json` from git (the
refresh workflow checks out full history). New bot commits enter as `presumed`; running
`scripts/capture_deployments.py` at a release turns them into `deployed` and fetches pending
statuses. The ledger capture is a person's step, not the bot's: the build must not depend on a
third-party API.

## 3. The canonical fixture: the 2026-10-10 backfill

The build served on 9 October (`56ad203`, `as_of` 2026-10-09) carried 176 events. The build
served on 10 October (`6a77e67`) carried 184. Eight were new; **seven of them were dated before
9 October** — strikes from April, September and early October that research found on the 10th:

| | The seven backfilled records |
|---|---|
| As published, 9 Oct | absent |
| As published, 10 Oct | present (`events_added` of that entry) |
| Current reconstruction for their own dates | present at their event dates |

That is the whole difference between event date and knowledge date, in real data. Three tests
hold it permanently: one reads the committed `production_history.json`, one rebuilds the history
live from git and the ledger (so a change to how history is assembled cannot pass on a stale
artefact), and one checks the records exist in the current corpus at their own dates.

## 4. OSM and analytical reproducibility

OpenStreetMap is not pinned for historical builds. **This does not affect analytical
reproducibility**, because no OSM-derived value enters a scored number:

| OSM layer | Used for | Scored? |
|---|---|---|
| Substations (220 kV+) | map; per-region transmission context count | No — `tx_context` is published beside the transmission sector, which is measured by event burden against a fixed saturation constant |
| Transmission lines (330 kV+) | map; per-region line count (same context) | No |
| Gas and oil pipeline ways and relations | analytic line layer; the continental context network | No — the pipeline registry and gap audit are context, never an index input |

Generation's denominator comes from the WRI plant database (a fixed 2022 release), refining's
from the pinned Wikipedia refinery list and the curated canonical registry, and no curated
incident links to an OSM asset. This was checked empirically as well: on 2026-10-31 a fresh OSM
fetch changed two analytic line features and eleven context pipeline segments, and the headline
and every sector value were identical to the build before it.

What OSM does change is the **map**. For archival purposes each build now records which OSM state
it drew (`snapshot.context_geometry_inputs`): Overpass's own data timestamp, a content hash and
a hash of the query, per layer, and for the pipeline route relations their count and a hash of
their sorted ids (iteration 17). That says which OSM snapshot a published map showed. It cannot
re-create an old map — Overpass serves only current data — and exact cartographic replay is not
worth building: the score, not the line work, is what has to be reproducible.

## 4a. The curated corpus has a history too (iteration 17)

A reconstruction uses **today's** curated corpus. When the corpus changes, every reconstruction
changes with it, including reconstructions of dates when the old version was what readers saw.
Iteration 17 is the clearest case so far:

- **Country records held at review.** The blind three-role review held 19 of the 94 records first
  published in iteration 14. They left `data/curated/systems/<id>/events.json`, so a
  reconstruction of any date now lacks them, while the as-published history still contains them
  for every day they were served. Neither is wrong: one says what today's reviewed evidence
  supports for that date, the other what was shown on it.
- **Corrections.** 79 of the 85 records published after blind review carry at least one
  correction (307 field edits in `review_edits.json`). A reconstruction shows the corrected text
  for every date.
- **The theatre's embargo.** Recovery evidence younger than 60 days on the reconstruction date is
  withheld exactly as in a current build, so the pinned 2026-08-28 reference moved from 16.16 to
  16.48 (+0.48 from the embargo, −0.16 from other curated changes). Three open-horizon repair estimates also left the curated file and are held locally
  until their horizons close.

git is the audit trail for all of it: `git log -p -- data/curated/` shows every record added,
corrected or held, with the commit that did it. `scripts/extract_published.py` recovers what was
served on any day from 2026-08-29. Neither the build nor the UI tries to merge the two.

## 5. C — engineering regression fixtures

Scoring transformations are tested on inputs that never change: synthetic incident and recovery
fixtures in `tests/test_pipeline.py` (decay, renormalisation, the cap, transmission saturation,
the decomposition reconciling to the published index). They answer only "did the arithmetic
change?" and are never shown to a reader. The pinned-source reconstruction (§1) is not one of
them, because its inputs include the live curated corpus.

## 6. In the product

The two-date comparison and the dossier's history views show the current-evidence reconstruction,
and say so. The as-published series is served in `production_history.json` and shown in the
comparison workspace as a separate, labelled series that begins on
`earliest_reliable_as_published_date`; before it, the workspace says "unavailable" rather than
drawing a reconstructed line under an as-published label. Exports carry the concept in their
title: "AS PUBLISHED ON YYYY-MM-DD" or "CURRENT-EVIDENCE RECONSTRUCTION FOR YYYY-MM-DD".
