# Iteration 23 — methodology adversary report

21 November 2026. Covers the red-team run of 20 November 2026 and the fixes committed on branch
`iteration-23` (range `8f17610..iteration-23`, through `c09919e`, the record corrections).

**Every reviewer in this report is a Claude agent.** A Claude agent is not an outside human
reviewer, and nothing here stands in for one. Where a finding says "independent", it means a
separate agent session, not a separate person or organisation.

## 1. What was red-teamed, and how

The directive's teams A–L were run as seven agent red teams:

| Team (short name used below) | Scope | Input file |
|---|---|---|
| ESDI | The theatre index: decay, horizons, weights, sector composition, confidence v1, served copy | `rt_esdi/FINDINGS.md` |
| Concept | Conceptual validity and reporting bias across the thirteen systems and the impact layer | `rt_concept/FINDINGS.md` |
| Cross-layer | Consistency between theatre, country systems, impact layer, Gulf context and What's New; history and first publication | `rt_crosslayer/FINDINGS.md` |
| Thresholds | Country inclusion clauses, impact inclusion bases, attribution statuses | `rt_thresholds/FINDINGS.md` |
| Impl | Implementation contract drift, duplicated logic, missing invariants | `rt_impl/FINDINGS.md` |
| ECI | The source model and Evidence Confidence v2 | `rt_eci/FINDINGS.txt` |
| IA | Information architecture of the whole app, and the Help Center proposal | `ia_audit/AUDIT.md` |

Method. Each team worked on copies, never on the repository:

- **Real builds on repo copies.** The ESDI team ran `build_index.build` on a copy with the network
  off; it reproduced the served headline and every sector exactly, ran 45 variants, and reran the
  baseline afterwards. The ECI team reproduced every served evidence-confidence block, origin count
  and attribution confidence exactly (220 impact records, 11 attempts, 175 country events, 0
  mismatches at the run).
- **Served payloads and the served site.** The iteration-22 release build was served read-only
  from a local copy; screenshots and rendered text were taken from it.
- **No source was reopened** by any team (by brief). Verdicts about what a source says rest on the
  served `derived_claim` and source text.
- **Fix verification for this report.** Every FIXED claim below was checked against a commit
  message and its diff, and where one exists, against a named test in
  `tests/test_iteration23_*.py` or a named mutant in `scripts/mutation_campaign.py`
  (`ITER23_THEATRE_MUTATIONS`, `ITER23_HELP_MUTATIONS`, `ITER23_IMPACT_MUTATIONS`,
  `ITER23_HOME_MUTATIONS`). The drafter did not run tests, builds or the mutation campaign. Where no
  fix could be found, the row says NOT FIXED.

Figures in this report are **as at the red-team run** unless stated. They are not live numbers;
the current figures are in `docs/CURRENT_STATE.md`.

Standing decisions this report does not touch: the theatre's scoring multiplier stays
**Evidence Confidence v1**; Evidence Confidence stays **`2.0-draft`**; Saudi harmonisation
**Option B** stays; **Release Rule A** and **D-34 to D-37** stay the owner's.

## 2. Classification and disposition vocabulary

Classification (exactly one per finding; where a finding has a fixable part and an owner part, it is
classified by the fixable part and marked "+ owner memo"):

- **BUG** — code or curated data does something an approved rule forbids.
- **DOCUMENTATION DRIFT** — a document, served string or comment says something the code does not do.
- **UX MISREPRESENTATION** — the page leads a reader to a reading the data does not support.
- **METHODOLOGY WEAKNESS** — the rule itself is weak; no rule is broken.
- **OWNER DECISION** — only the owner can settle it.
- **FALSE POSITIVE** — checked and not a defect.

Disposition:

- **FIXED (sha)** — a commit fixes it; the sha is the commit that does.
- **QUEUED — record correction** — a curated-record correction that goes through the private review
  queue and the import gate later. Not applied in iteration 23.
- **OWNER MEMO (Mn)** — written up in §4 for the owner. Not implemented.
- **LIMITATION** — recorded, deliberately not fixed; the row says why.
- **NOT FIXED** — no fix was found in the iteration-23 commits.
- **FALSE POSITIVE**.

A row may carry more than one disposition when parts of the finding went different ways.

## 3. Every finding

### 3.1 ESDI (theatre index)

| ID | Classification | Finding | Disposition |
|---|---|---|---|
| ESDI-01 | DOCUMENTATION DRIFT + owner memo | The 150-day refinery horizon contradicts the served observed refining median (47 days, n=4); METHODOLOGY §5 called it "broadly consistent with reported timelines". Evidence can only shorten decay, so less-reported facilities look worse. | FIXED ca5f75a (sentence replaced: the match is untested, see the sweep and the observed median) · OWNER MEMO M1 |
| ESDI-02 | UX MISREPRESENTATION | "Why this number?" showed the small sensitivities (−0.9, +0.38) but not the horizon range (1.7–13.9); decay shape, residual and aggregation sensitivities were published nowhere. | FIXED f0b5083 (horizon sweep in the headline inspector and the ribbon tooltip; tests 25b902a) · residual, shape and aggregation sweeps NOT FIXED |
| ESDI-03 | BUG | The ribbon's "50 with no restoration report by the cut-off" was a model count; 6 of the 50 carried released restoration reports. | FIXED ca5f75a (served `unresolved_with_recovery_report`), f0b5083 (relabelled "still in the index, no full-restoration report by the cut-off"), 809974e |
| ESDI-04 | DOCUMENTATION DRIFT | `recovery.partial_operations_floor` and `resolved_statuses` in `scoring.json` are read by no code. | FIXED ca5f75a (`_unread_keys`; floor note says NOT APPLIED; test that every key is read or marked unread) |
| ESDI-05 | DOCUMENTATION DRIFT + owner memo | The Methodology panel repeated a refining-basis invariance claim retracted in iteration 13. | FIXED f0b5083 · OWNER MEMO M1 (refining capacity basis) |
| ESDI-06 | DOCUMENTATION DRIFT + owner memo | Transmission is a unitless event count, not comparable with capacity shares. "Worth under one index point" was a hard-coded string true only on one day; the verdict said transmission "never needs a reconstitution duration", but it decays on modelled horizons. | FIXED ca5f75a (comparison computed each build; verdict corrected) · OWNER MEMO M2 · possible duplicate Crimean transmission node NOT VERIFIED |
| ESDI-07 | UX MISREPRESENTATION + owner memo | Gas is excluded for lack of a capacity base while transmission enters with a constant denominator (8); headline copy and the renormalisation note called the whole index a capacity share. | FIXED ca5f75a (renormalisation note), f0b5083 and cbf5aa8 (headline copy names the transmission event-burden count) · OWNER MEMO M2 |
| ESDI-08 | METHODOLOGY WEAKNESS | Oil logistics divides terminal and pumping-station throughput by refining capacity; five live nodes score zero for lack of a capacity figure, and `impairment_not_sized` discloses refining only. | NOT FIXED (the disclosure is not owner-gated) · OWNER MEMO M2 |
| ESDI-09 | METHODOLOGY WEAKNESS | Confidence v1 acts as a near-constant ×0.77; two hosts versus one origin moves nothing (0.00); damage "unknown" (1.0) outweighs "degraded" (0.7), so reporting damage lowers the score. | OWNER MEMO M4 (the multiplier stays v1) |
| ESDI-10 | OWNER DECISION | The max-per-facility rule is an unpublished lever of about ±50%. | OWNER MEMO M3 |
| ESDI-11 | METHODOLOGY WEAKNESS | Refining carries 88.6% of the points; generation has 23.5% effective weight on a 0.03 sector value; the weights are an unvalidated judgement. | OWNER MEMO M3 |
| ESDI-12 | DOCUMENTATION DRIFT | METHODOLOGY.md quoted 127 events and ~42% coverage; the panel formula omitted damage severity; "collapses" misdescribed the residual cap; a docstring quoted a stale 97% modelled share. | FIXED ca5f75a (live figures replaced by CURRENT_STATE pointers; docstring dated), f0b5083 (formula, residual cap) |

### 3.2 Concept (conceptual validity and reporting bias)

| ID | Classification | Finding | Disposition |
|---|---|---|---|
| C1 | BUG | The theatre coverage ratio mixed windows: the benchmark ends with its Feb–Jun 2026 period, the numerator counted strikes to the build date (153/305 = 50%; window-matched 116/305 = 38.0%). It rose each build with no new benchmark. | FIXED ca5f75a (numerator clipped to the benchmark's last period; later strikes counted apart; tests and two mutants) |
| C2 | UX MISREPRESENTATION + owner memo | "Monitored" / "Research preview" is a hand-set per-country cohort flag, shown in Compare under a common-basis row. India was "Monitored" with 4 of 7 source groups unavailable; Iran "Research preview" with 5 of 6 run. | NOT FIXED (the definition was reworded in 15aa32e and no longer says "added recently"; the flag is still hand-set and still under a common-basis row) · OWNER MEMO M5 |
| C3 | METHODOLOGY WEAKNESS + owner memo | Evidence confidence is nearly constant on country records (all Moderate by construction), so China ("Moderate 9", 1 first-party of 22 citations) reads as equal to the US ("Moderate 108, Limited 3", 64 of 119 first-party). | FIXED in part 25d3b5b (summary shows the provisional status and says High is unreachable and why; Compare reads no confidence) · OWNER MEMO M6 |
| C4 | UX MISREPRESENTATION | The Impact Atlas map draws CN, IN and SA, which have reviewed records on their own system pages, like countries searched and found empty; the map tracks where research lanes ran. | NOT FIXED (the Atlas map is unchanged; the new home-map card states whether the Atlas holds a record, 4028eec, which is a different surface) |
| C5 | BUG | Eight published US records cite only Wikipedia, contrary to REVIEW_GOVERNANCE §6 (the aggregator ruling: a figure needs a utility, state agency, DOE or an outlet citing one; §6 now names encyclopedias explicitly) and the discovery-aid rule. | FIXED c09919e (the eight records held for re-sourcing; the primary figures found, several different, are recorded in the queue for re-review) |
| C6 | BUG | 38 curated theatre strikes carry a hand-typed "confirmed", mostly on one article each, rendered "(confirmed) — reported, not independently confirmed"; METHODOLOGY said probable. | FIXED f0b5083 (shown as reported, never "(confirmed)"), ca5f75a (METHODOLOGY §7.6 says the label is hand-set and unread by the score); `test_the_score_does_not_read_attribution_confidence` confirms no score effect · Help glossary still says attribution confidence is "never typed by hand" without limiting it to the impact layer: NOT FIXED |
| C7 | METHODOLOGY WEAKNESS | `damage_severity` unknown = 1.0 (169 of 184 events) and degraded = 0.7 (11): a sourced partial-damage report lowers weight against no information. "Active" 1.0 is applied to a contract expiry. | OWNER MEMO M4 |
| C8 | METHODOLOGY WEAKNESS | v1 confidence depends on the entry path: 40 curated single-citation incidents at "confirmed" (1.0) against 108 single-host strike-table incidents at "probable" (0.75); 11 of 50 live facilities are driven by curated entries. | OWNER MEMO M4 · one curated record's swapped source types NOT FIXED (not in the queue list) |
| C9 | UX MISREPRESENTATION | Home "103 with a recovery report" of 175 read as a twelve-country rate; 95 of the 103 were US and Canada. | FIXED 4028eec (recovery and review sub-totals dropped; reporting sentence added) |
| C10 | UX MISREPRESENTATION | Iran page said "All 8 registered sources checked on schedule" while one source group was inaccessible; "checked" meant a registry re-check. | FIXED 25d3b5b, 9c645ae, 6156ebc |
| C11 | UX MISREPRESENTATION + owner memo | Iran's empty page blamed "the inclusion rule is strict" when the electricity lane could not be read; nothing routes an impact record that meets a system clause into that system's review; reconciliation reads start date ±1 day and ignores `date_end` (unverified at the run). | FIXED 25d3b5b, 6156ebc (reason leads with the research state; the impact-tab line names both searches) · OWNER MEMO M8 · `date_end` in reconciliation NOT FIXED |
| C12 | UX MISREPRESENTATION + owner memo | "Independently reviewed" / "three independent reviewers" on Home, Atlas, Inspector and Glossary; no reader text said the reviewers were sessions of the same model. | FIXED 25d3b5b, f30293d · OWNER MEMO M13 (outside human sample) |
| C13 | OWNER DECISION | Two Alberta EEA-3 records published with no load shed while about nine similar ones were held. | OWNER MEMO M7 |
| C14 | DOCUMENTATION DRIFT | METHODOLOGY.md §1 and §8 quoted 127 events / 42%; every `system.json` said "episodes are not yet grouped" (they have been since iteration 15). | FIXED ca5f75a, f30293d |

### 3.3 Cross-layer and history

| ID | Classification | Finding | Disposition |
|---|---|---|---|
| XL-01 | BUG | Gulf context: "A later statement of this type is listed above" was false on two cards (list sorted by `date`, latest marked by `as_of`). One entry's `as_of` is after its `date`; the gate never refuses that. | FIXED 25d3b5b (direction computed from the order drawn), 02c7d7a (`date` and `as_of` defined, §10), a624ec7 (the gate refuses `as_of` after `date`), c09919e (the UKMTO entry's `as_of` is its date) |
| XL-02 | BUG | What's New's first-release branch swallowed the regional context's first publication, and a test enshrined it. | FIXED f30293d |
| XL-03 | METHODOLOGY WEAKNESS | Three different backfill rules (theatre ledger, country records, impact records), plus the Atlas card's own. | LIMITATION (documented side by side in SCHEMA.md, 02c7d7a; unifying them changes what each panel calls historical, a methodology decision) |
| XL-04 | BUG | A month-dated country record ("2026-11") was called "all dated before the previous build" against 2026-11-19. | FIXED f30293d |
| XL-05 | BUG (latent) | `impact_timing` ignored `date_end`; the card's `isHistoricalAddition` used it. | FIXED f30293d (observed end read; parity test) |
| XL-06 | UX MISREPRESENTATION | 38 theatre incidents read "(confirmed) — reported, not independently confirmed"; one with attribution `none` carried "confirmed". | FIXED f0b5083 (display), ca5f75a (`not_applicable` on the record without attribution) |
| XL-07 | METHODOLOGY WEAKNESS + owner memo | No-widening applies only to events that reached a country queue. Iran's system had 0 records (pass stopped at the search limit) while the impact layer held about 10 Iranian energy disruptions; reconciliation ignores `date_end`; the country page blamed the gap on the impact layer's "broader contract". | FIXED 25d3b5b (country line reworded) · span-overlap reconciliation NOT FIXED · OWNER MEMO M8 |
| XL-08 | UX MISREPRESENTATION | Compare said Saudi Arabia places nothing finer than one region; the Saudi page names facilities on attack records (Option B). | FIXED f30293d (`attack_records` flags read from the records), 25d3b5b (Compare discloses it) |
| XL-09 | METHODOLOGY WEAKNESS | `first_published` is stamped by hand before deployment and not reconciled with the production history. | NOT FIXED |
| XL-10 | DOCUMENTATION DRIFT | The history doctrine and `production_history` are theatre-only; country, impact and context reconstructions carry no `history_concept`; HISTORICAL_REPRODUCIBILITY has no section for them. | NOT FIXED (Help `#history`, e4145fe, explains reconstruction to readers; the documents and payloads are unchanged) |
| XL-11 | BUG (latent) | `lifecycle.py` drops presumed lineage while the Lifecycle panel says "First present in dashboard". | NOT FIXED |
| XL-12 | DOCUMENTATION DRIFT | The comparison panel said the dashboard "LEARNED" of each event; the lint missed it. | FIXED f0b5083 (test and mutant in 25b902a, cbf5aa8) |
| XL-13 | UX MISREPRESENTATION | "First seen" has four meanings across the app. | NOT FIXED |
| XL-14 | UX MISREPRESENTATION | The same chip is used whether origins were counted by publisher or by reviewed origin. | FIXED in part 25d3b5b (the country summary says when every record was counted by publishers) · per-chip basis marker NOT FIXED |
| XL-15 | BUG | The late-citation rule (>7 days) is absent for abstracted impact records; one Ukrainian record has citations 8 and 12 days late. | FIXED a624ec7 (gate and import rule for abstracted records) · c09919e (the two late citations removed) |
| XL-16 | OWNER DECISION | No reconciliation between theatre incidents and impact records; the Atlas presence fill by country code shades Crimea and Sevastopol for any Ukrainian record. | OWNER MEMO M12 |
| XL-17 | DOCUMENTATION DRIFT | GLOBAL_IMPACT_METHODOLOGY §2 said "nothing finer than admin-1 in any field"; a natural-hazard record names an area inside its region (harmless). | FIXED 02c7d7a (scope stated as what the gate enforces) |
| H-M1 | BUG (test gap) | Mutant predicted to survive: `present_before_tracking` → `first_served` in `production_history.py`. | FIXED 25b902a (`_check_backfill` asserts in the live rebuild; mutant in ITER23_THEATRE_MUTATIONS) |
| H-M2 | FALSE POSITIVE | Predicted gap; mutant killed at the run. | FALSE POSITIVE |
| H-M3 | BUG (test gap) | Mutant predicted to survive: the `history_concept` call site compares `as_of` with itself. | FIXED 25b902a |
| H-M4 | BUG (test gap) | Mutant predicted to survive: the ribbon never treats its payload as reconstructed. | FIXED 25b902a |
| H-M5 | BUG (test gap) | Mutant predicted to survive: `impacts/model.ts` `endDay` → `startDay`. | NOT FIXED as a named mutant (the XL-05 parity test may catch it; not verified) |
| H-M7 | BUG (test gap) | Mutant predicted to survive: XL-04 unpinned. | FIXED f30293d, 1dab991 (XL-04 mutant) |
| H-M8 | BUG (test gap) | Mutant killed only once XL-02 is enforced. | NOT FIXED as a named mutant (XL-02 is now enforced and has its own mutant, 1dab991; identity with H-M8 not verified) |
| H-M9 | FALSE POSITIVE | Predicted gap; mutant killed at the run. | FALSE POSITIVE |
| H-M10 | FALSE POSITIVE | Predicted gap; mutant killed at the run. | FALSE POSITIVE |
| H-M11 | BUG (test gap) | Mutant predicted to survive: no context `as_of` > `date` guard. | FIXED a624ec7 (guard added; mutant "a context entry may describe a day after it was made" caught) |

### 3.4 Thresholds (inclusion and attribution)

| ID | Classification | Finding | Disposition |
|---|---|---|---|
| T-A1 | OWNER DECISION | Procedural limbs outrank physical severity: small events published on a procedural trigger (330 MW, 8,517 customers, about 1.5 h; EEA-3 with no outage) while national blackouts and about 24 outages just under 100,000 customers are held; two Chinese records on the same instrument split. | OWNER MEMO M7 |
| T-A2 | METHODOLOGY WEAKNESS | Clause 3 (pipelines) has no effect requirement: about 12 of 20 "segment isolated" federal notices pass while about 16 comparable Canadian flags are held. | OWNER MEMO M7 |
| T-A3 | METHODOLOGY WEAKNESS | The D-38 24-hour floor is incompatible with the campaign policy (two Saudi records). | OWNER MEMO M7 |
| T-A4 | METHODOLOGY WEAKNESS | Clause 4's second limb has no floor (one- to two-hour cuts). | OWNER MEMO M7 |
| T-A5 | METHODOLOGY WEAKNESS | Duration is ignored; a customer-hours limb was offered. | OWNER MEMO M7 |
| T-A6 | BUG | `cn-2025-07-20-typhoon-wipha-guangdong-outage` (245,000 households cumulative) is below the interim D-36 floor that held comparable US records. | FIXED c09919e (held under the D-36 interim practice) |
| T-A7 | UX MISREPRESENTATION | The evidence card printed the whole clause ("about 100,000 customers or more, or … declared an emergency") on an 8,517-customer record; country pages never show exclusions or known weaknesses. | FIXED 25d3b5b, 1dab991 (the grid sentence says which limb the record met) · exclusions and known weaknesses on the page NOT FIXED |
| T-A8 | DOCUMENTATION DRIFT | `inclusion_threshold.json` "episodes are not yet grouped" served in 12 `system.json`; one US record's basis said clause 5 "names EEA3 explicitly" (it does not); THRESHOLD_STUDY stale. | FIXED f30293d (rule text and that record's basis) · THRESHOLD_STUDY NOT FIXED |
| T-B1 | UX MISREPRESENTATION + owner memo | Basis 1 drift: the inspector tells readers an emergency was declared on records where none was (a boil-water advisory, a utility cyberattack assessed a year later, a data outage with no supply lost, a price-market suspension, "activated incident response"). | NOT FIXED · OWNER MEMO M9 |
| T-B2 | BUG | Basis 4 on all-local scopes: a Danish grid-outage record, an airport record and three single-hospital records. | FIXED a624ec7 (basis 4 needs a national or regional scope) · c09919e (Denmark, the airport and two single-hospital records held; the French hospital re-based to basis 1, its emergency plan) |
| T-B3 | BUG | Basis 5 on one-day events (two Iranian records). | FIXED c09919e (both re-based to basis 4) |
| T-B4 | METHODOLOGY WEAKNESS | Basis 6 without an output effect (three records, one where the first party says it was unaffected). | OWNER MEMO M9 |
| T-B5 | OWNER DECISION | Payment exception applied unevenly (one fuel record kept although cash worked; another held because manual sales continued). | OWNER MEMO M9 |
| T-B6 | OWNER DECISION | City ransomware counted as disruption while utility billing attempts are not. | OWNER MEMO M9 |
| T-B7 | OWNER DECISION | No-widening is enforced per event, not per rule: Iran (campaign policy, 0 system records) has 15 non-kinetic impact records, including facts of types the country layer holds for an owner decision. | OWNER MEMO M8 |
| T-B8 | UX MISREPRESENTATION | On the Atlas, monitored systems look less disrupted (held national blackouts absent) than extent-based blackouts elsewhere. | NOT FIXED |
| T-B9 | METHODOLOGY WEAKNESS | Basis 2 "large" reaches down to 45,000 households / 50,000 people. | OWNER MEMO M9 |
| T-C1 | METHODOLOGY WEAKNESS + owner memo | The gate accepts SUSPECTED, ASSESSED and ATTRIBUTED alike for government sources; the status encodes reviewer belief, not the formality of the instrument. | OWNER MEMO M10 |
| T-C2 | DOCUMENTATION DRIFT | An interview is not a formal instrument, yet a relay that declares a government basis passes ATTRIBUTED. | NOT FIXED · OWNER MEMO M10 |
| T-C3 | BUG (latent) | A campaign-level indictment and Treasury notice listed as attribution sources would give HIGH if the status were flipped; the campaign-advisory rule is not encoded. | NOT FIXED |
| T-C4 | BUG (latent) | A single media source with no basis passes ASSESSED; a relayed claim with an uncited original refuses CLAIMED but accepts SUSPECTED/ASSESSED. | NOT FIXED |
| T-C5 | BUG (latent) | A vendor digest plus a government source reaches HIGH (`cyber_firm` not restating role). | NOT FIXED |
| T-C6 | DOCUMENTATION DRIFT | `actor_aliases` documented in EVIDENCE_CONFIDENCE_V2 but refused by the gate. | FIXED 02c7d7a |
| T-C7 | BUG | Descriptors served as actors ("Unidentified perpetrators", "a Russia-based group (not named)", "Iran-nexus groups"); a group named where the source says an affiliate. | OWNER MEMO M10 (not a mechanical correction: replacing a descriptor with no actor changes the attribution status, which lead normalisation may not do) |

### 3.5 Impl (contract drift, duplicates, invariants)

| ID | Classification | Finding | Disposition |
|---|---|---|---|
| F1 | UX MISREPRESENTATION | The world-map card said "no disruption record … it was not searched" for 72 impact-record countries. | FIXED 4028eec (card removed with the home rework; context PNG no longer says it) |
| F2 | UX MISREPRESENTATION | The impact inspector showed two different "originating statements" counts in the same words (differ on 41 of 220). | FIXED 25d3b5b |
| F3 | BUG | Origin grouping implemented three times; 6 US events differ between the Sources tab and the chips; the served origin rule claimed it "cannot overstate" independence; first-party role lists disagree. | FIXED f30293d (roles from the method's direct tier; rule text corrected), 25d3b5b (card wire matcher mirrors the build) · the three implementations remain (IMPL-D1) |
| F4 | UX MISREPRESENTATION + owner memo | "Blind reviewed by three independent reviewers" while REVIEW_GOVERNANCE §4 says they are the same model. | FIXED 25d3b5b, f30293d · OWNER MEMO M13 |
| F5 | UX MISREPRESENTATION | ECI's provisional status only behind "Why?"; the status text hid that calibration run 1 was performed and failed (kappa 0.10 / 0.02). | FIXED f30293d (served status), 25d3b5b (beside every category, summary, both CSV dictionaries) |
| F6 | BUG | Same as C6 (theatre "confirmed"), plus the glossary's "never typed by hand". | FIXED f0b5083, ca5f75a · glossary wording NOT FIXED (see C6) |
| F7 | DOCUMENTATION DRIFT | The country page described ESDI weights as "by share of monitored capacity" and a "fixed half-life". | FIXED f0b5083 (test in 25b902a) |
| F8 | BUG | Null shown as zero: uncovered gas and coal sectors 0.0, `_pct` 0.0 on a zero denominator, out-of-season heating 0.0, "Installed generation 0 MW" for Crimea. | FIXED ca5f75a (null served; missing sectors listed), f0b5083 ("no capacity figure in the census") |
| F9 | DOCUMENTATION DRIFT | CURRENT_EVENT_PUBLICATION_POLICY §3 said the campaign rule applied to Saudi Arabia only; §1 contradicted the Gulf country-only attack rule. | FIXED 02c7d7a |
| F10 | DOCUMENTATION DRIFT | GLOBAL_IMPACT_METHODOLOGY said no region on "any record in a system under the campaign policy"; the code restricts campaign country systems only; the test hard-coded the campaign set. | FIXED 02c7d7a (doc), f30293d (test derives the set from `conflict_campaigns.json`) |
| F11 | BUG | The impact gate never checked that an `admin1` code belongs to the record's country; a Russian record with a Crimean code would pass. | FIXED f30293d (gate check via `a2`; three mutants) |
| F12 | BUG + owner memo | Observed-only `date_end` applies only in the impact layer; one US record ends after its only dated source and its own recovery contradicts it; 12 more pass only because a source is undated. | FIXED c09919e (the US record is held with C5) · OWNER MEMO M11 |
| F13 | UX MISREPRESENTATION | The ECI breakdown printed "no" for "not recorded" / "not counted". | FIXED 25d3b5b |
| F14 | UX MISREPRESENTATION | Country records are capped at Moderate; the summary never said High was unreachable. | FIXED 25d3b5b |
| F15 | OWNER DECISION | National-table sort against GLOBAL_METHODOLOGY §6.2 (standing owner item). | OWNER MEMO M14 |
| F16 | OWNER DECISION | Compare's sourcing row sets shares side by side (standing owner item). | OWNER MEMO M14 |
| F17 | DOCUMENTATION DRIFT | SCHEMA.md lacks `impacts.json`, `regional_context.json` and `first_published`; a CSV note said "0 to 100". | FIXED in part 02c7d7a (iteration-23 fields, backfill rules) · dedicated `impacts.json` / `regional_context.json` sections NOT FIXED |
| IMPL-D1 | BUG | Origin grouping lives in four places; authority should be `evidence_confidence.json`. | NOT FIXED (F3 aligned roles and wires; the implementations are still separate) |
| IMPL-D2 | BUG | First-party roles duplicated. | FIXED f30293d |
| IMPL-D3 | DOCUMENTATION DRIFT | Heating months hard-coded in `tabs.tsx` ("Oct–Apr"); authority is `scoring.json`. | NOT FIXED |
| IMPL-D4 | DOCUMENTATION DRIFT | Transmission saturation "eight" hard-coded in the glossary. | FIXED e4145fe (Help glossary points to the derived value) |
| IMPL-D5 | UX MISREPRESENTATION | Confidence categories listed alphabetically in `groupImpacts.ts`, not in the method's order. | NOT FIXED |
| IMPL-D6 | BUG | Campaign set hard-coded in a test. | FIXED f30293d |
| IMPL-D7 | DOCUMENTATION DRIFT | Theatre attribution confidence described differently in CSV, parser and prose. | FIXED in part ca5f75a (prose), f0b5083 (display) · three copies remain |
| IMPL-D8 | DOCUMENTATION DRIFT | SCHEMA example shows 280.6 MTPA (served 273.8 at the run). | NOT FIXED |

Invariant proposals from the Impl team (proposed tests, each with the mutant it should kill):

| # | Proposed invariant | State after iteration 23 |
|---|---|---|
| INV-1 | Served impact countries sorted by name | Not added in iteration 23 |
| INV-2 | No confidence figure in any `global/*.json`; Compare never reads `by_category` | Partly: `test_f14_no_comparison_view_reads_a_countrys_confidence_distribution` (Compare); the existing `test_no_confidence_figure_reaches_the_manifest_or_any_cross_country_file` |
| INV-3 | `source_health.events` equals the event count and the category sum | Not added |
| INV-4 | Uncovered sectors and zero-denominator effects are null | Added: `test_a_percentage_of_nothing_is_null`, `test_uncovered_sectors_and_missing_denominators_are_null_in_every_served_file` |
| INV-5 | No status flag key in served context | Not added in iteration 23 (iteration-22 tests cover the context status flag) |
| INV-6 | ConfidenceSummary shows the served status | Added: `test_f14_f5_the_country_summary_says_its_status_and_that_high_is_unreachable` |
| INV-7 | Gate refuses a Russian record with a Crimean `admin1` | Added: `test_f11_the_gate_refuses_a_region_of_another_country` |
| INV-8 | `coordinate_problems` over incident and event text | Not added |
| INV-9 | Abstracted served test includes `contributing_factors` | Not added |
| INV-10 | `first_published` ≤ `as_of` and present in the lineage | Not added |
| INV-11 | Served `end_date_problems` (fails today on a US event) | Not added; waits on F12 |
| INV-12 | A test of `asOfText` | Added: `test_xl01_a_historical_statement_points_where_its_newer_statement_is_drawn` |

### 3.6 ECI (source model and Evidence Confidence v2)

| ID | Classification | Finding | Disposition |
|---|---|---|---|
| ECI-01 | BUG | Relays that a record's own text declares are not marked, so three records are served High that the approved rule makes Moderate (Romania, France, Ireland); three US records lose points without changing category; two more (Japan, an Iranian water record) need a reviewer. | FIXED c09919e (one origin on Romania, France, Ireland and the three US records) · Japan and the Iranian water record NOT FIXED (need a reviewer) · proposed gate check NOT FIXED |
| ECI-02 | METHODOLOGY WEAKNESS + owner memo | A source nobody opened earns full directness and origin weight; 19 records would change category without it (12 High→Moderate, 2 High→Limited, 5 Moderate→Limited). | NOT FIXED (reason line when the tier-carrying source was not opened) · OWNER MEMO M13 |
| ECI-03 | METHODOLOGY WEAKNESS | "Opened" and "dated" are effectively constants (551 of 600 impact sources opened), so three components decide the category. | NOT FIXED (the team asked for this to be documented; EVIDENCE_CONFIDENCE_V2 was not amended; recorded here) · OWNER MEMO M13 |
| ECI-04 | METHODOLOGY WEAKNESS | Many records sit on a threshold: 123 of 220 impact records change category under at least one of 22 perturbations; 35 Highs at exactly 79, 33 Moderates at exactly 56. | OWNER MEMO M13 (thresholds are the owner's; none proposed) |
| ECI-05 | METHODOLOGY WEAKNESS | A quantified press claim outranks a strong first-party claim; "quantified" is set once per record and partly measures media attention. | OWNER MEMO M13 |
| ECI-06 | DOCUMENTATION DRIFT | The served Limited meaning named "one origin, no figure", which the thresholds serve as Moderate 56. | FIXED f30293d |
| ECI-07 | BUG | A Ghanaian record's effect dispute is recorded as a cause dispute and served Moderate with a total. | FIXED c09919e (`dispute.about` = effect; the gate takes one value, and the effect dispute is what makes it Disputed; the statement keeps the cause dispute) |
| ECI-08 | UX MISREPRESENTATION | "Evidence confidence: High" sits under "Cause: cyber" where the cause evidence is weak; the cyber + High filter reads as a list of high-confidence cyberattacks. | FIXED 25d3b5b (every chip says confidence does not cover the cause) · filter rename NOT FIXED |
| ECI-09 | METHODOLOGY WEAKNESS | One typing decision often decides the category (retyping one press source as government moves 20 records Moderate→High); calibration cannot see it. | OWNER MEMO M13 (process) |
| ECI-10 | BUG | Official operator and government channels typed S2 (journalist tier); two records would be High as S1. | OWNER MEMO M15 (public-source check, 21 November: officiality not established from the organisation's own site for three of the four accounts, and only by a two-step chain for the fourth; nothing retyped) |
| ECI-11 | METHODOLOGY WEAKNESS | Closed reporting environments: official statements earn full points, and foreign press restating them counts as a second origin. | OWNER MEMO M13 (reviewer guidance) |
| ECI-12 | METHODOLOGY WEAKNESS | An authority or a victim restating an actor's self-identification counts as its own attribution. | OWNER MEMO M10 |
| ECI-13 | OWNER DECISION | Per-country summaries are all Moderate by construction; side by side they become cross-country counts. | OWNER MEMO M6 |
| ECI-14 | BUG (latent) | Short-word wire matching ("IANS Research" → the Indian wire; "Spa" → the Saudi agency). | FIXED f30293d, 25d3b5b |
| ECI-15 | UX MISREPRESENTATION | The "N points" total in "Why?" beside component maxima that sum to 100 invites a "79/100" reading. | FIXED 25d3b5b (total removed; components and reasons stay) |
| ECI-D1 | OWNER DECISION | Feasibility: per-source `supports: "cause"`. Partly feasible; a record-level `cause_basis` recommended instead. | OWNER MEMO M13; see §5 |
| ECI-D2 | OWNER DECISION | Feasibility: structured per-source actor field. Recommended NO for now. | OWNER MEMO M10; see §5 |
| ECI-D3 | UX MISREPRESENTATION | Raw score display (same as ECI-15). | FIXED 25d3b5b; see §5 |

### 3.7 IA (information architecture)

| ID | Classification | Finding | Disposition |
|---|---|---|---|
| IA-01 | UX MISREPRESENTATION | "How to read this site" was split across seven unlinked surfaces, none addressable but one. | FIXED e4145fe (Help page `?view=help#<anchor>`, Learn more links) |
| IA-02 | UX MISREPRESENTATION | The theatre was a navigational island with no Help or glossary, and its "Data quality" meant something different from the home's. | FIXED e4145fe (Help link in the theatre bar) · distinct titles for the two data-quality surfaces NOT FIXED |
| IA-03 | UX MISREPRESENTATION | "How to read this" on any non-home page navigated away to the home. | FIXED e4145fe |
| IA-04 | UX MISREPRESENTATION | `?view=help` and any unknown `view=` silently rendered the home. | FIXED e4145fe (help route; old glossary link rewritten) · notice for an unknown `view=` NOT FIXED |
| IA-05 | UX MISREPRESENTATION | Five "what changed" surfaces with at least two baselines, reconciled only by a hover tooltip. | FIXED e4145fe (Help `#whats-new` and `#history`; the ribbon's history line links to Help) |
| IA-06 | UX MISREPRESENTATION | What's New's "How this works" link landed on the system-selection section. | FIXED e4145fe, f30293d, ec05994 (links to a Help section; pipeline writes help anchors) |
| IA-07 | UX MISREPRESENTATION | The publication-safeguard concept has at least seven names and two definitions. | FIXED in part e4145fe (one Help definition, "Publication safeguards") · variant names remain in country, filter and export copy: NOT FIXED |
| IA-08 | UX MISREPRESENTATION | The indexed system has six names; the index is called a "disruption score". | FIXED in part 15aa32e (client copy says exposure index) · the served no-index reason deliberately left unchanged (d05d617, to avoid a twelve-country wording change on release day): NOT FIXED |
| IA-09 | DOCUMENTATION DRIFT | Help-type text leaked file names, keys and internal verdicts. | FIXED ca5f75a, f0b5083, e4145fe |
| IA-10 | UX MISREPRESENTATION | ECI's provisional status invisible at view level; the glossary omitted "does not cover the cause". | FIXED 25d3b5b, e4145fe |
| IA-11 | UX MISREPRESENTATION | Three corpora, three counts, no reconciliation. | FIXED e4145fe (Help states the collections are never added together) |
| IA-12 | UX MISREPRESENTATION | The Gulf overview and the Atlas are reading walls with repeated caveats. | NOT FIXED (Learn more links added, e4145fe; page length not re-measured) |
| IA-13 | UX MISREPRESENTATION | Exports have no common explanation and five naming patterns. | FIXED in part e4145fe (Help `#exports`) · naming patterns not unified: NOT FIXED |
| IA-14 | UX MISREPRESENTATION | Hover-only explanations remain. | NOT FIXED (not re-audited) |
| IA-15 | BUG | `whats_new.json` `comparison.mode = "development"` in a release-candidate payload would show "Built from a development copy" in production. | NOT FIXED at head: ec05994 committed a production-mode payload, but the merge rebuild 446a818 is `development` again. The release build on main must regenerate it |
| IA-16 | UX MISREPRESENTATION | The theatre Methodology modal named attacked gas-processing plants as "live-disrupted" with model weights, and carried a hard-coded sentence naming one power link. | FIXED f0b5083, ca5f75a (no named plants; concentration note computed, names no facility) |
| IA-17 | DOCUMENTATION DRIFT | Hand-copied lists and numbers in reader copy (four research states, "eight", "added recently"). | FIXED e4145fe, 15aa32e |

### 3.8 Totals

Rows: 137 findings in §3.1–3.7 (the twelve INV proposals are listed separately and not counted).

| Classification | Count |
|---|---|
| BUG (including latent bugs and mutation-test gaps) | 37 |
| DOCUMENTATION DRIFT | 23 |
| UX MISREPRESENTATION | 39 |
| METHODOLOGY WEAKNESS | 23 |
| OWNER DECISION | 12 |
| FALSE POSITIVE | 3 |

| Primary disposition (the first one in the row) | Count |
|---|---|
| FIXED (in whole or in part) | 79 |
| QUEUED — record correction | 0 |
| OWNER MEMO | 30 |
| LIMITATION | 1 |
| NOT FIXED | 24 |
| FALSE POSITIVE | 3 |

Across all dispositions in a row: 16 FIXED rows also carry a NOT FIXED remainder; 41 rows carry a
NOT FIXED part somewhere; no row carries a queued record correction; 48 rows point to an owner memo.

### 3.9 Record corrections applied through the review queue

Applied on 21 November 2026 (`c09919e`), through the private review queue and the import gates,
never by editing curated or processed data by hand. Each lead correction is dated by itself.

- ECI-01: one origin on Romania, France, Ireland and three US records. Japan and the Iranian water
  record need a reviewer and were not joined.
- ECI-07: the Ghanaian record's dispute is about the effect.
- XL-01: the UKMTO context entry's `as_of` is its date; the gate now refuses `as_of` after `date`.
- XL-15 and the iteration-22 production red team: a Ukrainian abstracted record loses two late
  citations and is basis 4; a German one no longer says how long the outage lasted; every abstracted
  record's duration is written as withheld.
- T-B2: Denmark's island outage, one airport and two single-hospital records held (no basis);
  France's hospital record is basis 1. The gate now requires a national or regional scope for basis 4.
- T-B3: two one-day Iranian closures re-based from basis 5 to basis 4.
- T-A6: the Typhoon Wipha record held.
- C5 and F12: eight US records whose figures came only from Wikipedia held for re-sourcing; a
  public-source check found primary figures for most, and several differ from what was published
  (two Helene state peaks, both Winter Storm Fern figures). They are recorded for re-review.

Not applied: ECI-10 (memo M15) and T-C7 (memo M10).

## 4. Owner decision memos

None of these is implemented, and none is pre-decided. Figures are from the red-team run on 20
November 2026 (theatre headline 5.87 at that run) and will move with the data.

### M1. Refinery reconstitution horizon and refining capacity basis (ESDI-01, ESDI-05)

**Question.** Should the 150-day refinery horizon stay, and should the refining denominator change
to Option B of `docs/REFINERY_CAPACITY_BASIS.md`?

**Why it matters.** The headline is mostly a decay assumption. All 50 live facilities at the run
decayed on modelled horizons; recovery evidence moved the headline by +0.05. Evidence can only
shorten decay, so a facility that is reported less looks worse.

**Evidence.** Served observed refining median 47 days (7, 22, 72, 98; n=4). Refinery horizon at 47
days: 1.25; 72 days: 2.18; 100 days: 3.51; 225 days: 8.96 (baseline 5.87). All horizons ×2 / ×0.5:
13.89 / 1.73. Option B refining basis: 6.21 (two-year ratio range 0.68–1.37). A "substantially
restored" report with no observed days changed nothing.

**Options.**
1. Keep 150 days and publish the observed-median counterfactual beside the sweep. Honest and cheap;
   two numbers may invite readers to pick one.
2. A pre-registered replacement rule: once a class has k observed episodes, its horizon is their
   median. The headline would fall sharply on today's evidence; n=4 is small, and reported
   restorations are biased toward quick ones.
3. Use `evidence_as_of` as an upper bound on decay where a restoration report lacks observed days.
   Narrow; fixes the "report changes nothing" case only.
4. Separately, adopt Option B for the refining basis, or keep the tracked basis.

**Recommendation.** Option 1 now, and pre-register option 2 with the owner choosing k, so the rule is
fixed before anyone sees the result. Decide the refining basis on its own memo.

**Not implemented.**

### M2. Sector composition: transmission, gas and oil logistics (ESDI-06, ESDI-07, ESDI-08)

**Question.** Should the headline keep mixing capacity shares with a unitless transmission count,
and should oil logistics keep refining capacity as its denominator?

**Why it matters.** The copy now says what the headline is (25d3b5b, f0b5083, ca5f75a), but the
composition is inconsistent: gas is excluded for lack of a base while transmission is admitted
against a constant denominator. One 500 kV substation weighs about ten times a 2.2 GW plant.

**Evidence.** Transmission: 4 facilities, 0.36 points; removing it, 6.25. Saturation 1/2/4/16/32:
8.40 / 6.95 / 6.23 / 5.69 / 5.60, and up to +8.66 in the series at 2; transmission was 36% of the
headline on 2025-11-01. All 11 transmission incidents are curated and single-source, 7 typed
"confirmed". Gas on the transmission rule: 5.72. Oil logistics: 12 facilities, 0.31 points; struck
capacity 208 of 274 MTPA; removed, 7.28 (ratio 0.50–1.32); five live nodes score zero for lack of a
capacity figure and are not disclosed.

**Options.**
1. Status quo with the corrected copy.
2. Move transmission to its own panel (the review's model E). The headline becomes capacity shares
   only; the transmission signal stays visible but stops moving the index.
3. A node identity table for transmission units (some records bundle several substations).
4. Treat gas and transmission by one rule: both admitted on a constant denominator, or both excluded.
5. Give oil logistics its own throughput base, or exclude it like gas.

The disclosure of zero-scoring oil-logistics nodes in `impairment_not_sized` is not owner-gated and
can be done regardless.

**Recommendation.** Option 2, and decide option 4 at the same time so the rule is one rule.

**Not implemented.**

### M3. Aggregation: max-per-facility and sector weights (ESDI-10, ESDI-11)

**Question.** Should the max-per-facility rule and the judgement weights stay, and should both be
published as sensitivities?

**Why it matters.** Both are large, unpublished levers. Refining carries most of the index.

**Evidence.** 20 facilities had concurrent incidents discarded by the max rule. Capped sum / noisy-OR:
9.20 / 8.51 (series up to 10.29). Equal sector weights: 4.25; refining only: 12.63. Refining 88.6%
of points; generation 23.5% effective weight on a 0.03 sector value; top five facilities 54%, top
ten 73%.

**Options.** Keep and publish both sweeps; change the aggregation; change the weights (equal, or by
capacity).

**Recommendation.** Publish both as served sensitivities, as the horizon sweep now is, before any
change.

**Not implemented.**

### M4. Theatre confidence v1 and damage severity (ESDI-09, C7, C8)

**Question.** Within v1, should curated labels be re-derived, and should damage "unknown" stop
outweighing "degraded"?

**Why it matters.** v1 behaves like a constant (×0.77), rewards the entry path, and lowers weight
when a source reports partial damage.

**Evidence.** Confidence all 1.0: 7.60; probable 0.45: 3.95; curated labels re-derived by the
strike-table rule: 5.76 (−0.11 today, −1.08 at most in the series); registered-domain host rule:
0.00; damage unknown at 0.7: 4.20. 169 of 184 events have damage unknown, 11 degraded. 40 curated
single-citation incidents at "confirmed" against 108 strike-table incidents at "probable"; 11 of
50 live facilities are curated-driven. The v2 shadow study capped the theatre at Moderate, ratio
drift 0.40–0.56, and condition 1 of the replacement bar fails.

**Options.**
1. Keep v1 as is. The multiplier stays v1 until every condition in EVIDENCE_CONFIDENCE_V2 §8 ("The
   bar for ever replacing the theatre multiplier") holds; this memo does not propose v2.
2. Re-derive curated labels by the strike-table rule. A v1 parameter change, not a move to v2;
   `test_the_theatres_confidence_multiplier_is_byte_for_byte_unchanged` pins the label function, so
   the owner would lift that pin deliberately.
3. Set damage "unknown" at or below "degraded".
4. Stop applying "active" (1.0) to non-physical events such as a contract expiry.

**Recommendation.** Options 2 and 3 together as a pre-registered v1.1 with the series published.

**Not implemented.**

### M5. Research-maturity cohort flag (C2)

**Question.** Should "Monitored" / "Research preview" be derived from lane states with a stated exit
rule, or renamed as a cohort and removed from Compare's common-basis rows?

**Why it matters.** It reads as search completeness and is not. Compare presents it on a common basis.

**Evidence.** India "Monitored" with 4 of 7 source groups unavailable and no `covered_through`;
Iran "Research preview" with 5 of 6 run. The "absence is not evidence" caveat appeared only on Gulf
cards. The definition was reworded in 15aa32e.

**Options.** Derive from lane states (needs an exit rule); rename as an onboarding cohort and move
it out of the common-basis rows; keep with the current definition.

**Recommendation.** Derive it, or move it out of the common-basis rows.

**Not implemented.**

### M6. Country evidence-confidence summary (C3, ECI-13, XL-14)

**Question.** Keep the per-country confidence summary, replace it, or remove it?

**Why it matters.** Every country record is capped at Moderate because its origins were never
reviewed. The summary therefore says almost nothing, and two summaries side by side would be a
cross-country count.

**Evidence.** Country events: Moderate 164, Limited 3, not assessed 8. Without the cap, 51 would be
High. China: "Moderate 9" with 1 first-party citation of 22; US: "Moderate 108, Limited 3" with 64
of 119 first-party. Since 25d3b5b the summary shows the provisional status and says High is
unreachable and why; Compare reads no confidence (tested).

**Options.**
1. Keep, as now.
2. Replace it with the source-composition line already served in `source_health`.
3. Remove it.
4. Add a per-chip basis marker (publishers versus reviewed origins), for XL-14.

**Recommendation.** Option 2. Never set two countries' summaries side by side.

**Not implemented.**

### M7. Country inclusion thresholds (T-A1 to T-A5, C13; with D-18, D-27, D-37)

**Question.** Should the procedural limbs get a magnitude floor, and should an official
whole-system-extent limb be added?

**Why it matters.** Procedural triggers outrank physical severity, so small events publish and
national blackouts are held.

**Evidence.** Published: a 330 MW firm load shed of 8,517 customers for about 1.5 hours; records
where "at least 100 MW" is the form trigger; EEA-3 declarations with no outage. Held: two Iraqi
national blackouts and one Omani, and about 24 outages just under 100,000 customers. Two Chinese
records on the same instrument went different ways. Clause 3 has no effect requirement; the D-38
24-hour floor conflicts with the campaign policy; clause 4's second limb has no floor; duration is
ignored.

**Options.** A magnitude floor on the procedural limb; an official whole-system-extent limb; a
customer-hours limb; keep.

**Recommendation.** The Thresholds team recommends deciding D-18, D-27 and D-37 together, with a
magnitude floor on the procedural limb and an extent limb. D-34 to D-37 remain the owner's.

**Not implemented.**

### M8. No-widening per rule, not per event (XL-07, T-B7, C11)

**Question.** Should the impact layer also hold a record whose class a country system holds pending
an owner decision, and should an impact record that meets a system clause be routed into that
system's review?

**Why it matters.** Safety-adjacent. No-widening currently binds only events that reached a country
queue. Where a country pass stopped early, facts of a held class can appear through the impact
layer. This extends iteration 22 §34 item 1.

**Evidence.** Iran's system had 0 records (the pass stopped at the search limit). The impact layer
held 15 non-kinetic Iranian records, including facts of types the country layer holds for owner
decision. Reconciliation matches on start date ±1 day and class, and ignores `date_end`.

**Options.**
1. Per event (status quo).
2. Per rule: a class held in a country system is held in the impact layer too.
3. Routing: an impact record meeting a system clause enters that system's review queue.

Span-overlap reconciliation (reading `date_end`) is not owner-gated.

**Recommendation.** Options 2 and 3, with span overlap regardless.

**Not implemented.**

### M9. Impact inclusion bases (T-B1, T-B4, T-B5, T-B6, T-B9)

**Question.** Should basis 1 require a formal declaration by a named authority, basis 2 a stated
minimum, and basis 6 an output effect?

**Why it matters.** The inspector tells readers an emergency was declared where none was.

**Evidence.** Basis 1 on a boil-water advisory, a utility cyberattack assessed a year later (50
households, 7 hours), a control-data outage with no supply lost, a price-market suspension, and an
"activated incident response". Basis 6 on three records without an output effect. The payment
exception applied unevenly. City ransomware counted while utility billing attempts are not. Basis 2
"large" down to 45,000 households / 50,000 people.

**Options.** Tighten the definitions and re-review the listed records through the queue; reword
the inspector so it shows the record's own basis rather than the whole definition; keep.

**Recommendation.** Tighten basis 1 and basis 2, and re-review the listed records.

**Not implemented.**

### M10. Attribution instrument (T-C1, T-C2, ECI-12, ECI-D2)

**Question.** Should records carry the formality of the attribution instrument, and should "a claim
is a claim" extend to authorities and victims relaying an actor's self-identification?

**Why it matters.** The status currently encodes reviewer belief. A minister's speech and a formal
notice can reach the same status.

**Evidence.** CERT notices typed ASSESSED while a speech, and a victim's president quoted by one
outlet, are ATTRIBUTED. A government accusation typed SUSPECTED would pass as ATTRIBUTED. A
Treasury notice restating a group's claim counts as a government attribution; a victim relaying the
actor's self-identification counts as ASSESSED.

**Options.** An `attribution_instrument` field (formal statement, indictment or sanction, technical
advisory, speech or interview, relay) and a victim/party flag; extend the claim rule; reviewer
guidance only. A structured per-source actor field (ECI-D2) is not recommended (§5).

**Recommendation.** The instrument field and the extended claim rule. The latent gate gaps T-C3 to
T-C5 are bugs and do not need this decision.

**Not implemented.**

### M11. Observed-only `date_end` in country systems (F12)

**Question.** Should country systems adopt the impact layer's rule that an end date needs a dated
source observing it?

**Why it matters.** An inferred end shortens a disruption and widens the ECI "dated" window.

**Evidence.** One US record ends after its only dated source, and its own recovery evidence says
customers were still out days later (queued). Twelve more US events pass only because a source is
undated.

**Options.** Apply the rule (many end dates and a What's New entry change); flag inferred ends
instead; keep.

**Recommendation.** Apply it, with the served `end_date_problems` test proposed as INV-11.

**Not implemented.**

### M12. Theatre and impact-layer reconciliation (XL-16)

**Question.** Should theatre incidents and impact records be reconciled, and should a country-level
Ukrainian record shade Crimea on the Atlas map?

**Why it matters.** Two corpora can describe one event without either knowing. The Atlas fill by
country code shades Crimea and Sevastopol for any Ukrainian record, which reads as a claim about
where the event was.

**Options.** A stated reconciliation rule for Russian and Belarusian impact records against theatre
incidents; no Crimea fill from a country-level record; keep, with a note. Any choice is an analytic
choice, not a statement about sovereignty; Crimea stays internationally Ukrainian.

**Recommendation.** A stated reconciliation rule, and no Crimea fill from a country-level record.

**Not implemented.**

### M13. Evidence Confidence calibration bar and component design (ECI-02, -03, -04, -05, -09, -11, ECI-D1, C12, F4)

**Question.** Is an outside human labeller the bar for leaving `2.0-draft`, and should the
components change before calibration run 2?

**Why it matters.** Run 2 should test the method that would be adopted, not one known to have two
constant components.

**Evidence.** Impact records: High 103, Moderate 107, Limited 4, Preliminary 5, Disputed 1. 123 of 220
change category under one perturbation; 35 Highs at 79, 33 Moderates at 56; 551 of 600 sources
opened; 19 records rest on an unopened source; retyping one press source as government moves 20
Moderate→High. Run 1: reviewers agreed with each other (kappa 0.73) and barely with the model (0.10,
0.02); both labellers were agents.

**Options.**
1. Accept run 2 with an outside human labeller as the bar (the plan is prepared, not run).
2. Change components first: "opened" and "dated" as gates rather than points; "quantified" tied to
   the source that gives the figure; the tier-carrying source must be opened.
3. A second reviewer checks the role and origin of the source that decides the category.
4. Reviewer guidance for closed reporting environments and for foreign outlets relaying domestic
   officials.

**Recommendation.** Decide options 2 and 3 before run 2, then run it under option 1. Agent labels do
not substitute for a human. ECI stays `2.0-draft`.

**Not implemented.**

### M14. Comparison surfaces (F15, F16)

Standing owner items, unchanged: the national-table sort against GLOBAL_METHODOLOGY §6.2, and
Compare's sourcing row setting shares side by side. No new evidence. **Not implemented.**

### M15. Social tier for an operator's or government's own account (ECI-10)

**Question.** Where should a post by an operator's or government's own channel sit when its
identity is not established from the organisation's own site?

**Why it matters.** S1 requires established identity; S2 is "a recognised journalist or
institution". A public-source check (21 November) established officiality from the organisation's
own site for none of the four accounts the ECI team named; one rests on a two-step chain (an
investor site linking a channel that forwards the cited one). Such an account fits neither tier, so
it is typed S2 by default, which can understate (two records would be High as S1) or overstate.

**Options.** (1) Keep S2 and say in the method that an unproven first-party account sits there. (2)
Add a tier between S1 and S2 for first-party accounts of unproven identity. (3) Accept a documented
chain of links as an identity basis.

**Recommendation.** Option 1 now, written into EVIDENCE_CONFIDENCE_V2; decide option 3 with the
calibration work (M13). A platform badge stays no basis.

**Not implemented.**

## 5. Evidence Confidence feasibility notes

### 5.1 Cause provenance (ECI-D1)

**Verdict: partly feasible.** A per-source `supports: "cause"` value is not recommended. A
record-level `cause_basis` enum is: first-party / official investigation / press report / actor
claim only / later statement / contested. It is shown beside "Cause:" and is **never a scoring
input**. Fed into points, it would create a cause-confidence figure nobody has calibrated.

Population at the run: 74 malicious-cause records (69 cyber, 11 of them attempts; 3 sabotage; 2
kinetic). On served text, 26 have an opened first-party source naming a malicious cause, 38 rest on
press text, and 9 have no served text naming one. Five of those nine are country-abstracted, so
their claims withhold the method by design. A hand-read sample of 22: 12 populatable without
inference, 4 needing judgement, 6 weak or contested. About 6 weak-cause records would gain from it.

**Hard rule.** Missing cause provenance is never answered by collecting exploit detail, device
inventories or technical access paths. The cyber ceiling stays the broad mechanism. Where provenance
is missing, the enum says so ("press report", "actor claim only", "contested"). On abstracted records
it stays at the cause family.

### 5.2 Actor consistency (ECI-D2)

**Verdict: not now.** 41 attributed records at the run. Only about 6 have attribution sources from
two or more separate organisations; one shows divergent actors and is already DISPUTED. Granularity
differs as a matter of course (persona, state-sponsored actors, government). A string field would
raise false conflicts or need an actor ontology, which would be false precision. About 20
attribution sources do not name the actor in served text, so filling the field would mean reopening
sources. Instead: a reviewer checklist item ("do the attribution sources name the same actor, at
the same level?"), fix ECI-12 first (M10), and revisit when multi-source attributions grow.

### 5.3 Raw score display (ECI-15, ECI-D3)

The total was removed from "Why?" in 25d3b5b; the category, reasons and per-component rows stay.
Open: the CSVs still export `evidence_confidence_score`, with a dictionary note that it is ordinal,
not a percentage or probability, and never to be sorted by. Whether a file should carry a total the
page no longer shows is a lead display decision.

### 5.4 Country ECI summary

See M6. Mitigated in 25d3b5b (status shown; High unreachable said; Compare reads none). Replacing it
is the owner's call.

## 6. False positives

Checked and found sound by the teams:

- **ESDI.** Embargo moves today's headline by 0. "No report" is not scored as continuing impairment
  (decay runs regardless). No capacity-loss wording. Repeat refinery strikes are not double-counted.
  Cut-off, voltage weights and Crimea inclusion are minor or documented.
- **Concept.** `next_due` equal to the last pass is intentional; `research_lanes_complete` is not
  rendered; the single-colour Atlas map is fine; Compare omits counts correctly; subdomain host
  counting is harmless; ESDI moving on backfill is covered by the three-histories rule.
- **Cross-layer.** Saudi page detail versus impact abstraction (Option B, disclosed); Saudi CSV
  blanks; "National" wording; embargo versus campaign rule (Rule A); the theatre having no threshold;
  history using later recovery; same-day bot relisting; v1 versus v2; one storm in both layers;
  Russian impact records unscored; Compare's "Record as of".
- **Thresholds.** Self-claim laundering is blocked; two vendors relaying one government statement
  count once; indictment plus sanctions naming an incident is correctly HIGH; victim operators
  ASSESSED per §6; actor types match sources.
- **ECI.** Archive and AMP copies unwrap; wire syndication resolves (90+ copies); state agencies of
  the table states join their state bodies; reviewer origins applied; a cause dispute does not make
  a record Disputed (by design); country events capped below High (documented); claims alone never
  exceed CLAIM_ONLY; lead-added sources never counted; High always has two origins.
- **IA.** Home corpus totals are one aggregate, not per country; the data-quality panel is
  alphabetical with state words only; the national table is sortable only by the reader's own act;
  Start here is recoverable; "plausibly still affected" is a modelled weighting, not a status claim.
- **History mutants.** H-M2, H-M9, H-M10 were killed at the run.

## 7. Not verified

- **No test, build or mutation campaign was run for this report.** FIXED rows rest on commit
  messages, diffs and the presence of named tests and mutants. Commit 1dab991 states its 39 impact
  mutants were all caught and 15aa32e its 15 help mutants; this report did not re-run them.
- **H-M5 and H-M8** are not named mutants in iteration 23; whether existing tests kill them is
  unverified.
- **Crimean transmission node identity** (ESDI-06): two records may describe one node.
- **The Ukraine-outlet heuristic** behind "87% Ukraine-based only" (ESDI) is a heuristic.
- **The theatre v2 shadow study** was quoted, not rerun.
- **Whether press sources actually relay a statement** (ECI-01 candidates, ECI-11, the 79-point
  Highs): no source was reopened.
- **Held counts** in the Thresholds findings come from documents, not from the queue.
- **Country-event cards** were checked in code, not on screen (ECI); theatre mobile panels beyond the
  first screen were not walked (IA).
- **IA-12 and IA-14** were not re-measured after the Help Center landed.
- **The preview caveat on non-Gulf country pages** (C2) was not re-checked after 15aa32e.
- **IA-15** will recur on any rebuild from a development branch; the release procedure, not this
  report, settles it.
- **The record corrections in §3.9** were applied by the lead and checked by the import gates and the
  test suite; no blind reviewer re-read them.
