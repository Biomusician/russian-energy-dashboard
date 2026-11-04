# Iteration 17 — governed, reproducible, reviewable

**Rule of the iteration: no new country until the existing six systems are governed,
reproducible, reviewable and operationally mature.** No Wave-2 country was started. Live numbers
are in [CURRENT_STATE.md](CURRENT_STATE.md) and the manifest's corpus totals; figures below are
dated 2026-11-03 and are not kept current.

## 1. Baseline

- Start: commit `4656234`, production ESDI 7.8 (as of 2026-11-03), five country systems with
  209 published records, 94 of them grandfathered on a single review from iteration 14.
- Known open items carried in: the theatre's facility-status exposure (iteration-16 policy §8);
  `--as-of` builds writing into `data/processed/`; Canada's facility lanes; no systematic plan
  for China, India or Saudi Arabia; four UX defects (phone timeline, 1024 px header, double
  close control, raw ids in the comparison workspace).

## 2. Campaign policy (theatre)

The theatre is now under an active-campaign policy of its own
([OPERATIONAL_STATUS_DELAY_OPTIONS.md](OPERATIONAL_STATUS_DELAY_OPTIONS.md), METHODOLOGY §12).

- **Fields classified.** Occurrence (published at admin-region level, as before); modelled
  exposure (published: a function of public strike dates and a class horizon); recovery
  evidence and late effect reports (current facility status: delayed).
- **Rule.** Recovery evidence is used for display, scoring and the change ledger only once it is
  60 days old and past any estimate horizon. An effect reported within 7 days of the strike is
  occurrence. Counts withheld are published (`snapshot.campaign_policy`), ids never. Every
  campaign disruption without released evidence carries the withheld-status note, so the note
  reveals nothing. A current build refuses to run with an embargoed row in the curated files.
- **Delay stress test** (D = 0, 7, 14, 30, 45, 60, 90 at three dates): at 60 days the largest
  index effect at any tested date is +0.48 (2026-08-28: 16.00 → 16.48) and nothing today. 60 is a
  judgement, not a knee in the data: it covers about half of re-strike intervals (median 67 days)
  at the same index cost as 45, and 90 would cover 59%.
- **Moved to a local hold:** three open-horizon repair estimates and one forward effect estimate.
  ESDI unchanged at 7.8.
- **Safety review of what the theatre already published.** Removed from curated text: unit
  inventories and per-unit capacity shares, criticality framing ("largest", "key node"), a
  strike-damage tank count, sub-region places with an outage time, sanctions-tied repair
  timelines, and four asset notes that ranked possibly-undamaged facilities by size. A lint holds
  the theatre's text to the country abstraction rules. A 2024 note that wrongly said Crimea is
  excluded from the ESDI was corrected.
- **Leakage audits.** Region aggregates move only on modelled values and released evidence;
  the ledger reports recovery only once released, as `historical_evidence_added`; the repository
  does not carry embargoed rows. git history still holds the earlier text; history is not
  rewritten.

## 3. Historical isolation

- **Build modes** (`pipeline/outputs.py`): `current`, `reconstruction`, `fixture`. Only a current
  build for today may write `data/processed/`, mirror to `web/public/data/`, rewrite
  CURRENT_STATE or extend the production ledger. A past `--as-of` without `--mode
  reconstruction`, or a reconstruction into a protected root, is refused before any work. An AST
  test forbids any writer naming the production directory directly.
- **Proven:** a 2026-08-28 reconstruction into a scratch root leaves the hashes of
  `data/processed/`, `web/public/data/` and CURRENT_STATE byte-identical.
- **Archive extraction** (`scripts/extract_published.py`): the build served at the end of a UTC
  day, written out of git byte for byte and blob-verified, with a provenance file. It reproduces
  the October fixture: 9.08 served on 9 October, 14.40 on 10 October, the seven backfilled
  records absent then present.
- **Pinned reconstruction reference** (`--as-of 2026-08-28`): **16.48** (16.16 at iteration 15),
  re-run at HEAD; the change is the embargo.
- **Mutation tests** for isolation: refused roots, refused modes, the mirror and CURRENT_STATE
  writers refusing on their own.

## 4. Review governance

[REVIEW_GOVERNANCE.md](REVIEW_GOVERNANCE.md) §7. Three blind roles: A evidence, B safety and
abstraction, C taxonomy and episodes. Packets carry the claim and its sources, never the
researcher's reasoning. Outcome rule: any reject rejects; any hold or duplicate holds; any owner
question holds for the owner; there is no majority vote. Corrections to the same field are
reconciled into one text, then every role confirms the final text; one objection holds the
record. A fix round sent role-specific fixes back to the objecting role. The published record
carries `blind_reviewed`, `reviewer_count` 4 and each role's verdict, never the reasoning.

## 5. Grandfathered corpus review

All 94 records published in iteration 14 on a single review, in governance order (2026 kinetic;
single-source; weak-source; multi-region; unusual cause; the rest):

| | US | Canada | China | India | Saudi Arabia | Total |
|---|---|---|---|---|---|---|
| Reviewed | 31 | 23 | 14 | 15 | 11 | 94 |
| Published (`blind_reviewed`) | 29 | 16 | 11 | 10 | 9 | **75** |
| Held | 2 | 7 | 3 | 5 | 2 | **19** |

Why the 19 are held: **6 for the owner** (a rule question, §17); **5** because two roles'
corrections could not both be honoured (for example, the safety role removing the only source
for a figure); **6** because a role objected to the reconciled text at confirmation (a citation
address naming a city, an unsupported peak, a hazard name an episode depends on); **2** because
the evidence did not support the clause. 79 of the 85 records now published after blind review
carry at least one correction (307 field edits in `review_edits.json`). The grandfather list is
empty and its frozen bound is zero.

## 6. US sweep

Lane completion pass from a plan committed before searching
([US_LANE_COMPLETION_17.md](countries/US_LANE_COMPLETION_17.md)). **0 of 9 lanes complete.** 78
candidates: 3 accepted by lanes, 25 rejected, 38 duplicates, 8 held, 3 out of scope. Blind review
of the new records: 3 of 4 published, 1 held for the owner (Hurricane Lee in Maine). G1, G2 and
H2 wait on 2026 publications; BSEE and PHMSA's incident files refused access; L1 ran one terminal
of nine before the search cap; R1 and C1 have no census source. **Lane H1 was declared in the plan
but not assigned**; the plan-commit test caught it, and the log records it as partial through
2026-10-31.

## 7. Canada sweep

[CA_LANE_COMPLETION_17.md](countries/CA_LANE_COMPLETION_17.md). **0 of 8 lanes complete.** 56
candidates: 6 accepted, 12 rejected, 11 duplicates, 27 held. All 6 published after blind review.
The hazard census has published nothing after 2022-12-22; AESO has no 2026 list; IESO keeps 90
days of notices; TSB refused; CU1 ran half its queries; CL1 was not run (search cap).

## 8. China, India, Saudi Arabia

First systematic plans, committed before searching, and first passes:

- **China** ([CN_SYSTEMATIC_SWEEP.md](countries/CN_SYSTEMATIC_SWEEP.md)): 0 of 6 complete; 13
  candidates, none accepted (9 held, 2 rejected, 2 duplicates). Two of about 57 monthly releases
  read; CN4 and CN6 not started.
- **India** ([IN_SYSTEMATIC_SWEEP.md](countries/IN_SYSTEMATIC_SWEEP.md)): 0 of 7 complete; 22
  candidates, 1 accepted and published, 2 more lane-accepted but held at review (IOCL for the
  owner; GAIL by the safety role for a citation address). Every Grid-India and RLDC host refused
  connection.
- **Saudi Arabia** ([SA_SYSTEMATIC_SWEEP.md](countries/SA_SYSTEMATIC_SWEEP.md)): 0 of 5 complete;
  30 candidates, 18 duplicates of published records, none accepted. Tadawul (403), OPEC MOMR
  (402) and the ministry site could not be enumerated.

**Lane contract** (all countries): each lane records `covered_through`; "complete" requires the
end of the window; the build fails a complete lane that ends early. Corpus after review: **200
records** (209 − 19 held + 10 new), 166 episodes; **0 of 35 lanes complete**. Per-agent search
caps, with lane logs written after every source family, replaced the shared budget that stalled
iteration 16.

## 9. Threshold study

[THRESHOLD_STUDY.md](THRESHOLD_STUDY.md). Proposals only; the inclusion rule is unchanged
(version 2026-10-30.1). Safety principle for every option: severity is a property of the reported
effect, never of the asset; no option ranks facilities or sizes a dependency. Six owner decisions:
EEA-3 without load shed (three published Canada records would move to held); CER interruption
flags; cross-border pipelines; a reported effect or 24-hour floor for clauses 1-2; absolute
customer floors with a proportional disclosure line later; peak at one time stays the rule.

## 10. History

- Archive extraction and the as-published first-seen record (§3). Lifecycle: **16** episodes
  `present_before_tracking` (no date claimed), **7** `first_served` with the build that first
  carried them; a reconstruction for D never learns of a first-served date after D.
- OSM provenance now hashes every query, including the two pipeline-relation fetches, and
  records the relation count and a hash of the sorted relation ids.
- Curated-history note (HISTORICAL_REPRODUCIBILITY §4a): a reconstruction uses today's reviewed
  corpus, so the 19 held records and the corrections apply to every past date; as-published
  keeps what was served.
- The difference view, change classification (`diff_builds.RECORD_CLASSES`) and method
  fingerprints in `production_history.json` are iteration-16 work, unchanged.

## 11. UX

Fixed, each held by a new browser test:

- Phone timeline: the chart was 0 px wide at 390-430 px; controls and chart now take separate
  rows below 600 px; at 1280×720 the scrubber was pushed below the viewport.
- 1024 px header: the drawer toggles sat on the title; they now position against the map.
- One close control per drawer ("clear selection" for the region); focus returns to the toggle.
- No raw ids: every contributing facility in the history series has a name (48 of 48), with a
  derived label or "Unknown asset" as fallback, counted in Data Quality; the picker no longer
  flashes "RU".
- Withheld UX: the campaign note in the theatre's dossier; held records appear only as counts.
- New: per-country **source health** and an alphabetical **source browser** with a role filter
  (§43-44); corpus totals for the five countries together on the global home (§50).
- **Error containment** (§65): a corrupt, missing or malformed country payload (including an
  invalid research log) is refused at load and contained to its system; a missing as-published
  history leaves the dashboard and reconstruction working. Before, a malformed research log
  would have thrown during render and taken the whole dashboard down.

## 12. Safety

- Theatre safety review and campaign policy (§2).
- Every country record passed a safety role that saw only the claim and its sources (§5).
- Abstraction lint extended to the theatre's curated text.
- Episode hierarchy evaluated (§49): one flat layer kept. No count or view needs a middle level,
  and adding one would group records by proximity, which the episode rules forbid.
- Dedup audits of the US and Canada corpora (§47-48): no duplicate found; the pairs the
  date/region/class screen flagged were different facilities or different events.
- Final red team: see §19.

## 13. Tests

*Filled in at the release gate (§19).*

## 14. Performance

Measured on the release candidate:

- **Payload** (`web/public/data`): 9.91 MB raw, 1.49 MB gzip, 42 files. Largest: the theatre's
  line layer (2.39 MB → 169 KB) and gas context network (1.61 MB → 172 KB). Countries: US 649 KB
  → 135 KB, Canada 406 → 114, China 292 → 88, India 208 → 62, Saudi Arabia 82 → 21.
- **JS/CSS**: maplibre 1053 KB → 282 KB gzip; app 244 → 71; index 212 → 68; country view
  30 → 9; CSS 116 → 19.
- **Country switching ×20** (RU → US → CA → CN → IN → SA): JS heap samples 17, 18, 34, 35, 36,
  36 MB: a plateau, no growth after the first full cycle; one map canvas throughout; no errors.
- No optimisation was made: no measured issue.

## 15. Production

*Filled in after deploy (§19).*

## 16. Methodology decisions still needed

1. **Campaign delay**: confirm D = 60 and the estimate-horizon rule; whether the theatre should
   ever move to the Saudi rule (no status until the campaign ends); recording each recovery
   source's publication date so the evidence date stops being a floor.
2. **Saudi release rule A** (campaign end plus 30 days) is still proposed.
3. **Inclusion threshold**: the six decisions in THRESHOLD_STUDY §3.
4. **Lane completion**: whether a declared query set can make a census-less lane complete (US R1,
   C1; Canada CR1, CU1); how annual-publication lanes count for the current year.
5. **India**: whether RPC minutes are an acceptable proxy for the Grid-India census.
6. **The `linked_asset_id` join** from struck power plants to the WRI asset layer (reveals no
   hidden location; makes the struck subset machine-joinable).

## 17. Owner questions holding records

Eight records are held for the owner (six grandfathered, two new). Each turns on a rule:

- Citation addresses or publisher names that name a city; facility names finer than admin-1;
  renaming a published id (these also held records at confirmation).
- Canada: Nova Scotia December 2023 windstorm (cumulative versus simultaneous peak); Firebag
  wildfire (clause 7 needs a reported volume).
- China: a cumulative national typhoon-season aggregate as one record.
- India: coal-shortage load shedding (cause "unknown" versus a new fuel-supply-shortfall cause);
  IOCL (does isolating one pipeline section meet clause 3).
- Saudi Arabia: a partial pipeline throughput cut (does clause 3 cover it), and a port record
  that turns on the same ruling.
- US: Hurricane Lee in Maine (multi-state record re-scoped to one state's peak).

Other questions raised in review, not holding records: Ras Tanura's published capacity figure may
overstate (the ministry said "some units"); the Jazan hold; Houston peak versus total; the CA
snowstorm ECCC source and the Milton Fox Weather source should probably record `opened: true`
(role A opened them).

## 18. Wave 2 readiness

*Answered after the release gate (§19).*

## 19. Release

*Filled in at the release gate.*
