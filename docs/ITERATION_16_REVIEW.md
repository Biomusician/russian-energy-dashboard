# Iteration 16 — provenance and coverage closure

Theme: **before adding more data, make it clear what every record means, who reviewed it, when
the dashboard knew it, and whether a historical result is a reconstruction or an actual archived
publication.** No Wave 2 country. No new composite index. No change to how the theatre's index is
computed.

Live figures are in [CURRENT_STATE.md](CURRENT_STATE.md). Figures below are dated findings from
2026-10-31 and are deliberately not kept current.

---

## 1. Owner rulings implemented

| Ruling | What now holds | Where |
|---|---|---|
| 2.1 Depth before Wave 2 | No country added. | — |
| 2.2 Dual review | The import gate and the build refuse a country record without an independent review that opened a source, unless its id is in the frozen grandfather list (94 ids, may only shrink). | [REVIEW_GOVERNANCE.md](REVIEW_GOVERNANCE.md) |
| 2.3 Retroactive review of the 12 iteration-15 records | 3 confirmed, 9 corrected, 0 held, 0 removed. Aggregate published; no per-facility negative narratives. Jazan was later held at publication by the campaign citation rule (§4), which is not a review finding. | REVIEW_GOVERNANCE §5 |
| 2.4 Active kinetic campaigns | Saudi 2026 campaign: the event is published, the facility's status is not. Release rule A (ended + 30 days) is proposed. The theatre is recorded but not applied: owner decision. | [CURRENT_EVENT_PUBLICATION_POLICY.md](CURRENT_EVENT_PUBLICATION_POLICY.md) |
| 2.5 One statement is not one episode | `single_statement` retired. The Saudi April five are separate episodes. Bases are named hazard, explicit common event, coordinated wave or explicit continuation, each with evidence; otherwise singleton. | GLOBAL_METHODOLOGY §5.3 |
| 2.6 Source freshness ≠ research completeness | Gate items 7A and 7B; two separate badges on every country page. | GLOBAL_METHODOLOGY §7.2 |
| 2.7 Stale thresholds are display policy | Five named policies with rationale. A test shrinks every limit to one day and shows nothing a reader counts changes. | `build_systems.STALE_POLICIES` |

## 2. Historical model

Three concepts, never one number ([HISTORICAL_REPRODUCIBILITY.md](HISTORICAL_REPRODUCIBILITY.md)):

- **Current-evidence reconstruction.** Today's code and corpus at a past date. It comes in two
  forms, labelled differently since the red team: pinned-source (`--as-of D`) and the
  timeline/comparison series (today's article revisions). The 2026-08-28 pinned-source reference
  re-ran at **16.16**, unchanged from iteration 15.
- **As published.** Read from the 82 deployed commits; GitHub reports every deployment
  `success`. Reliable from 2026-08-29; unavailable, never reconstructed, before then.
- **Engineering fixtures.** Synthetic, in tests only.

**The October 9/10 fixture is permanent.**

- As published, the ESDI went from 9.08 (176 events) to 14.40 (184).
- Seven of the eight events first served on 10 October were dated before 9 October.
- Tests pin both views. One reads the committed artifact; one rebuilds history from git.

**On screen:**

- The comparison workspace has a History selector.
- Any past date on the ribbon or timeline says "CURRENT-EVIDENCE RECONSTRUCTION FOR D".
- Exports carry "AS PUBLISHED ON A AND B" or "CURRENT-EVIDENCE RECONSTRUCTION FOR …" in the
  image, the caveat and the file name.

**OSM is context only.** A fresh fetch changed geometry and left the ESDI and every sector
identical. Each build records its Overpass base timestamp and a hash per input.

## 3. Retroactive review

All 12 iteration-15 records were reviewed independently, against their sources:

- **3 confirmed.**
- **9 corrected:**
  - unit-level wording trimmed;
  - two recovery claims that overstated their sources were fixed;
  - one date was wrong;
  - attributions fixed and sources added;
  - Jazan's status detail removed.

Two iteration-15 episodes were dissolved, because no source called their records one event:
Ontario/Quebec July 2026, and Saudi April 2026.

## 4. Saudi Arabia

- **April 2026.** Five records that one ministry statement listed are five episodes.
- **Campaign records** publish the event and the withheld marker. Since the safety red team,
  the policy also covers:
  - citations whose address announces status;
  - citations published more than 7 days after the event;
  - capacity notes quoting operating rates;
  - one co-located record by name (the Juaymah LPG halt), whose recovery note had traced a
    struck site's outage for seven months.

  Ten records are covered.
- **Jazan is held.** Its only citation is a restart-delay article. It returns when an
  independent source for the shutdown is found, or when the campaign ends.

## 5. US systematic sweep

- **The plan came first.** Part A was committed before any search (`3c81d39`). A test compares
  the published lanes with Part A as committed.
- **Result: partial, 1 of 9 lanes complete.**
  - G2 was first recorded as complete. It was corrected to partial on the reasoning that
    already made G1 partial: no 2026 report exists yet.
  - Counts: 350 candidates; 101 accepted after independent review (43 confirmed, 58
    corrected), 77 rejected, 103 held, 42 duplicates, 27 out of scope.
  - The corpus went from 37 records to 138.
- **Most of what is held** is OE-417 rows whose figure is an incident total, not a peak.
- **No new event class.** A hazard path is never evidence of an effect.
- [countries/US_SYSTEMATIC_SWEEP.md](countries/US_SYSTEMATIC_SWEEP.md)

## 6. Canada (§25: budget remained)

- **Plan committed first** (`edd9cf6`).
- **Result: partial, 0 of 7 lanes complete.**
  - Three lanes wait on their sources to publish.
  - Four were limited by this run. The per-turn web-search budget, shared by every agent, was
    spent before the facility lanes began, and TSB refused automated access. Neither limit was
    worked around.
- **3 records accepted:**
  - two Alberta Level 3 alerts;
  - the Ontario half of the April 2023 ice storm, moved by the reviewer onto Hydro One's own
    figure. It now forms a named-hazard episode with Quebec.
- [countries/CA_SYSTEMATIC_SWEEP.md](countries/CA_SYSTEMATIC_SWEEP.md)

## 7. Research governance

- Every systematic pass names its plan document and commit.
- Every lane names the registry sources it searched, and a partial lane says why.
- "Complete" needs every lane, over a window starting 2022-01-01. A later top-up cannot
  complete the record.
- 7A is unmet when no source is in use.
- Research logs carry counts only, and the build refuses any other key.
- [GLOBAL_RESEARCH_COVERAGE.md](GLOBAL_RESEARCH_COVERAGE.md) states where all six systems are.

## 8. Recovery

**Non-conflict recovery stays observed-only, with labelled sourced estimates (A + D).**
[NONCONFLICT_RECOVERY_OPTIONS.md](NONCONFLICT_RECOVERY_OPTIONS.md) evaluates options A–E against
the observed inventory:

- US: 64 of 138 records have observed evidence. Canada: 22 of 26 (before this iteration's three
  additions).
- Twelve of sixteen US cause × class cells hold six records or fewer.
- Durations measure the time to the first report of recovery, not to full recovery.

Recommended, not deployed.

## 9. Product

- Research-status badges (completeness with a lane count; source re-checks).
- Review notes on every record, with totals.
- "Recovery" defined where it is shown.
- Standalone records say they stand alone.
- Plain-language reasons for "no index" and for withheld status.
- Internal process text removed from published recovery notes (15 records).
- **Theatre labels:**
  - "Currently impaired" became "No restoration report (modelled) · latest build";
  - "struck ×N" became "N recorded events";
  - dossier rows that do not follow the timeline say so.

## 10. Tests and verification

Release-gate totals are in §13.

- Python: 455 passed, 2 skipped.
- vitest: 230 passed.
- **Real-browser tests added for:**
  - the as-published October 9/10 fixture, and the unavailable case;
  - the reconstruction default, and a scrubbed `d=` link;
  - export caveats and file names;
  - research and source badges, as independent axes;
  - campaign records showing no status;
  - review notes;
  - episode bases.
- **Cross-platform visual check.** Each map is reduced to an 8×5 grid of mean colours and
  compared on every platform, with a negative control proving it fails a blank map. The win32
  pixel goldens remain.
- **Mutation campaign: 14 of 14 caught.** The brief's ten, plus two for the import and build
  halves of the second-reviewer rule, and two for the citation rule.

## 11. Red teams

Five reviews ran, none of them by the author:

- **Event review:** the independent review batches.
- **History:**
  - **Found:**
    - a scrubbed date or `d=` link showed a reconstruction unlabelled;
    - a published export carried the "Reconstructed" caveat;
    - an `--as-of` run rewrote CURRENT_STATE;
    - two reconstructions shared one label;
    - stale "no archive" wording;
    - a test that claimed to check the reconstruction did not.
  - **All fixed except the shared output directory**, which is guarded, not removed (§12).
- **Safety:**
  - **Found:**
    - Saudi status leaking through a non-kinetic record and through late or opaque citations;
    - theatre chokepoint, undamaged-part, sanctions-weakness and dependency wording;
    - modelled impairment shown as observed.
  - **All fixed.** The theatre's facility-status exposure is counted for the owner (policy §8).
- **Research completeness:**
  - **Found:**
    - lanes not tied to the plan;
    - a top-up pass could have flipped 7B;
    - lane sources missing from the registry;
    - 7A could be met vacuously;
    - G2 overclaimed;
    - docs overclaimed.
  - **All fixed.** The unwritten query sets are disclosed, not repaired.
- **UX (first-time user):**
  - **Found:**
    - unlabelled reconstruction;
    - singletons unmarked;
    - jargon;
    - a file path given as a reason.
  - **Fixed, apart from:**
    - the theatre timeline scrubber is about 37 px wide at phone width;
    - the "Layers" button overlaps the title at 1024 px;
    - comparison lists show asset ids for assets missing from the inventory;
    - panels show two close buttons.

## 12. Still unresolved

1. **The theatre and the campaign policy (owner).** The theatre publishes facility-level modelled
   impairment, sourced status text for 2026 strikes, and a per-facility build-change ledger.
   Single-facility regions make regional figures facility status. Apply the policy, aggregate,
   or accept it with reasons.
2. **Release rule A (owner).** Campaign recorded as ended, plus 30 days.
3. **Clause 5 and procedural EEA-3s (owner).** Canada's count would depend on which alerts NERC
   describes, and on one operator's procedure (CA Part B.4).
4. **CER "interruption" flags, cross-border pipeline shutdowns, coal export terminals** (owner,
   Canada).
5. **Census-less lanes (owner).** Should a written query set count as complete enumeration for
   refineries and coal?
6. **Absolute thresholds and no duration floor** (carried from iteration 15). LNG blips and the
   100,000-customer floor in small provinces.
7. **Pipeline loop segments** accepted under clause 3 with no stated supply effect (US B.4).
8. **`--as-of` writes into `data/processed/`.** Guarded three ways. The structural fix, a
   separate output root, touches every writer.
9. **Linux tolerance of the structure check** is unproven until CI runs it.
10. **Same-model independent review:** real in process, weak in diversity.

## 13. Release

The production deployment, the production browser run and the refresh simulation are recorded in
HANDOFF and in the final report.
