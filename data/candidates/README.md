# Candidate queues (research output, not published)

`data/candidates/<id>.json` holds every record a research lane found for a country system:
accepted, rejected, duplicate, out of scope and insufficient evidence, with the lane's notes.
`data/candidates/<id>_profile.json` holds the lane's compiled context statistics.

**These files are deliberately not committed** (`.gitignore`). The queue is a working research
record: its rejected and held entries include narratives such as "attacked, no reported
operational effect" for named facilities, which, collected per facility, read as damage-assessment
feedback for an attack campaign that is still under way. The iteration-14 safety red team found
this; the published product carries only reviewed events. Keep the files on the machine that
does the research; never move them into `data/processed/` or the site.

Nothing reads these files except `scripts/import_candidates.py`, which applies the review rules
and the reviewer edits in `data/curated/systems/review_edits.json` and writes
`data/curated/systems/<id>/events.json` (committed). A test fails if the build ever references
this directory.

## Queue state at the iteration-14 review (2026-10-30)

| System | Records | Lane accept | Shipped | Insufficient evidence | Reject | Duplicate | Out of scope |
|---|---:|---:|---:|---:|---:|---:|---:|
| ca | 39 | 23 | 23 | 4 | 11 | 0 | 1 |
| cn | 30 | 14 | 14 | 12 | 2 | 1 | 1 |
| in | 30 | 15 | 15 | 8 | 4 | 0 | 3 |
| sa | 33 | 11 | 11 | 13 | 6 | 0 | 3 |
| us | 55 | 34 | 31 | 11 | 7 | 2 | 1 |

The difference between "lane accept" and "shipped" is the import gate: for the US, three Puerto
Rico events are held because US territories are outside the US system's geography this iteration.

## Iteration-15 research pass (2026-10-30)

A targeted pass over the gaps iteration 14 named and the major 2025-2026 events. Every source
used was opened and read; leads the earlier lane left as insufficient evidence were replaced in
place (same id) when the research resolved them. Counts per system, also published in
`data/curated/systems/<id>/research_log.json`:

| System | Accepted | Insufficient evidence | Rejected |
|---|---:|---:|---:|
| ca | 3 | 1 | 1 |
| cn | 1 | 3 | 0 |
| in | 1 | 2 | 0 |
| sa | 1 | 1 | 0 |
| us | 6 | 2 | 0 |
