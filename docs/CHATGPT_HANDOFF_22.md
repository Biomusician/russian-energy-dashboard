# Handoff to ChatGPT: iteration 22 release closure, then iteration 23a

This is a working brief for a ChatGPT conversation that plans the next Claude Code sprint on the
Energy Disruption Monitor. It is self-contained: read it all before starting. It replaces the
19 November version of this file. Claude Code owns the repository, the machine, the builds and every
release step. ChatGPT's part is planning, red-teaming, research design and drafting. Return work in
the formats in §7 so Claude Code can apply it through the project's own gates.

The main thing this pass should produce is **the next directive for Claude Code** (§6). The last
directive was "Iteration 22 release closure → iteration 23a Gulf / Iran / cyber maturity blitz".
Most of its content work is done. Release is not.

## 1. What the project is (one paragraph)

An open-source-only dashboard of publicly reported disruption to energy and essential civilian
infrastructure. Its main product is calibrated honesty about what is and is not known:
- it never presents an estimate as an observation;
- it keeps "unknown", "not applicable" and "not yet researched" distinct.

It monitors 13 systems:
- one Russia/Belarus/Crimea theatre, with an exposure index;
- 12 country systems, with no score.

Iteration 22 adds a separate, non-scored **impact layer**: cyber, technical, natural-hazard and
civilian-service impact records from any country. It also adds two artifacts:
- regional context for the Gulf: dated, aggregate, sourced statements;
- an evidence-confidence method, `2.0-draft`.

## 2. The hard limits (binding on everything you write)

This is never a targeting or operational tool. Never produce, suggest or infer any of these:
- target rankings;
- criticality, importance or vulnerability of any asset;
- weak points;
- dependence of anything on a facility or route;
- chokepoint exploitation;
- alternate routes or bypass capacity;
- vessel names, positions, lists or tracking, or vessel counts that read as monitoring;
- the current operating, repair or restart status, or the remaining capacity, of anything reported
  attacked;
- coordinates, or any place finer than a first-level region;
- weapon or method detail;
- IP addresses, CVEs, device makes or models, protocols, access methods, credentials or exploit
  chains;
- malware or tool names outside an attribution statement;
- personal data.

Two placement rules:
- **The eight Gulf states** (Iran, Iraq, Kuwait, Saudi Arabia, Bahrain, Qatar, the UAE and Oman):
  no record carries a province, city, plant, facility, port, field, or an operator below a national
  body.
- **Every kinetic or sabotage record anywhere** is published at country level only, with no place,
  operator, method, headline or later status.

Sources must be public, open and unclassified. No logins, no private groups.

Two rules about reviewers:
- **A Claude agent, or ChatGPT, is not an outside human reviewer.** Never let a model stand in for
  one in a plan.
- The rules do not relax on request. If a task seems to need anything beyond this, say so and stop.

## 3. State on 20 November 2026

### Where the code is

- **Branch `iteration-22`.** It is local and has not been pushed, so production still serves
  iteration 21 plus the daily data refreshes.
- `origin/main` has moved on with the 2026-11-20 refresh and has not been merged in yet.

### Done since 19 November

- **Four content red teams ran.** Each ran blind first, then was given the earlier findings list.
  The teams were:
  - Iran, Gulf and Hormuz safety;
  - cyber safety and exports;
  - attribution, AI and social;
  - energy analyst and multilingual.
- **Three rounds of lead rulings were applied, all through the review queue and the import gate.**
  - The first round's findings were B1–B12 and S1–S8, plus regional-context corrections RC1–RC5.
  - Round two issued rulings R1–R13. They covered:
    - billing-only cyber incidents, which are now attempts;
    - the attribution contract;
    - one served form for "no figure";
    - origin counts that ignore sources the lead added;
    - citation addresses that name places or later status.
  - Round three made fixes and holds.
- **A final verifier found no blockers.**
- **Link check on all 650 published citations.**
  - It made one request per address, rate-limited.
  - A blocked page is never counted as dead.
  - It scanned redirect targets for leaks.
  - Eight citations whose final address named a Gulf place or a later status were removed, or their
    records held.
- **First-time-user, mobile and accessibility reviews ran.** Findings C1–C9 and A1–A14 are fixed in
  the frontend, with two exceptions:
  - C1 (a count on the home card) has no manifest field to supply it;
  - A8 (merging two disclaimers) is blocked because tests pin both texts.
- **A test-architecture red team ran with real mutants.**
  - It found two missing guards, now enforced at import and build:
    - an affected figure must be a scale, never a duration or a restoration;
    - inclusion basis 2 needs the source's own figure.
  - It also added a build check refusing queue wording and pipeline wording in served research notes.
- **Mutation campaign: 827 mutants.**
  - The last full run caught 826.
  - The survivor is now killed by a new test, checked by hand.
  - The full campaign has not been rerun since that test was added.

### Corpus as served

| | Count |
|---|---|
| Disruptions | 220 |
| Attempts with no service effect | 11 |
| Countries | 74 |
| Citations | 600 |
| Held at import | 26 |
| Country-abstracted records | 7 |

The holds break down as duplicates, safety grounds and evidence grounds.

| Breakdown | Counts |
|---|---|
| Cause (all 231) | cyber 69, industrial or technical 67, natural hazard 38, supply shortfall 34, unknown 9, ordered by an authority 6, sabotage 3, civil disruption 3, kinetic 2 |
| Sector (220 disruptions) | electricity 114, telecom 28, healthcare 16, fuel supply 16, municipal services 12, transport 11, water 10, oil and gas 7, district energy 5, desalination 1 |
| Iran | 15 records |
| The Gulf eight | 21 records |
| Attribution | not applicable 151, unknown 39, assessed 15, claimed 11, suspected 7, attributed 7, disputed 1 |
| Evidence Confidence v2 | Moderate 117, High 104, Preliminary 5, Limited 4, Disputed 1 |
| AI involvement | none reported on all 231 |
| Social sources | S2 45, S1 10, S4 3; every S1 carries proof the account is official |
| `first_published` | empty everywhere; it is stamped at the release build date, because first published means first served |
| Regional context | 35 entries, 20 of which carry a number |

Link health, checked on 20 November:

| | Reachable | Redirected | Blocked | Dead | Error |
|---|---|---|---|---|---|
| Impact citations | 495 | 46 | 53 | 4 | 3 |
| Context citations | 30 | 12 | 8 | 0 | 0 |

Each dead citation sits on a record that still stands on other sources.

Evidence Confidence's first blind calibration **failed**. Its two labelers agreed with each other
(kappa 0.73) but not with the model (0.02 and 0.11). So the thresholds stay provisional, the label
stays `2.0-draft`, and the theatre's scoring multiplier stays at v1.

### Test gate

The last full run started on a tree that predates two fixes. Its results:

| Step | Result |
|---|---|
| tsc, vitest, vite build | green |
| Playwright | 512/512 |
| pytest | failed on a synthetic fixture record that broke the new basis-2 guard; the record is now fixed and the affected files pass 475/475 |
| Mutations | 826/827 |

A clean full gate at the branch's current commit has **not** run yet. The full gate takes about two
hours:
- Playwright takes about 16 minutes;
- the mutation campaign takes about 100 minutes.

### Docs that are behind

`docs/ITERATION_22_REVIEW.md` §30–35 still describe 19 November. They say the red teams did not
report and the link check did not run. They are rewritten at release. Where they disagree with this
file, this file is right.

## 4. What is left to release iteration 22 (Claude Code's work, in order)

1. Run the full gate at HEAD and fix anything red.
2. Merge `origin/main` with the 20 November refresh, or whatever is newer by then. Regenerate the
   generated payloads by rebuilding; never resolve them by taking one side.
3. Run a build for the current date.
4. Simulate the next day's refresh, including the two tests that run only with `RUN_BUILD_TESTS=1`.
   Check that `first_published` does not advance and that no new untracked files appear.
5. Stamp `first_published` with the release build date, then rebuild.
6. Run the full gate again, then push.
7. Watch CI and fix it until green.
8. Verify production:
   - the deployed commit, through the GitHub deployments API;
   - the served bytes against that commit;
   - a safety scan of production;
   - browser QA of the Atlas, the Gulf page, Iran and phones;
   - the CSV and brief exports;
   - a final red team by a fresh agent, reading production only.
9. Mark the release done:
   - update the review §30–35, `HANDOFF.md` and `CURRENT_STATE.md`;
   - bump the iteration markers to 22.

ChatGPT cannot do any of these steps. A directive may reorder or tighten them. It must not skip
them, and it must not move the push before the full gate.

## 5. Open items the next directive should account for

### The owner's decisions (never implement silently)

- **`docs/OWNER_DECISIONS_22.md` holds four memos**, each with options and a recommendation:
  - **D-I22-1:** whether a record held from a country system on that system's threshold may appear
    in the impact layer. Today the import refuses it, with no override.
  - **D-I22-2:** banking, payments, tax and customs platforms, and heavy industry. They are out of
    scope today.
  - **D-I22-3:** Baltic subsea cables and pipelines. They are not researched.
  - **D-I22-4:** the bar for dropping `-draft` from Evidence Confidence.
- **These stay as they are:**
  - Saudi harmonisation stays at Option B: Saudi Arabia's own page keeps first-level region and
    facility detail on attack records.
  - D-34 to D-37 and Release Rule A are unchanged.
- **Two regional-context entries need an owner glance.** They give the strait's share of world oil
  trade and of world fertilizer trade. They are aggregate, dated statements by an authority, so they
  were kept, but they come closest to route dependence.

### Notes left open by the verifier (not blockers)

| Note | Issue |
|---|---|
| N-a | One Iran record's municipal-statement wording is slightly stronger than its source |
| N-c | A Kazakhstan record at country precision names regions in its summary |
| N-d | A Pakistan record's affected figure is a supply deficit in MW, labelled as a deficit |
| N-11 | Three end dates rest on sources the lead added and nobody opened |
| N-1 | A citation address is a publisher's own headline wording and carries a figure the record withholds |
| N-8, N-10, N-12 | Small wording and consistency notes |
| N-14 | Not verifiable from open pages |

### Limitations the corpus states as not yet researched (never as absent)

- US weather outages: hurricanes Ian, Beryl, Helene and Milton, and Winter Storm Elliott.
- India and China, which are thin in the impact layer.
- The December 2023 cyberattack on Iranian fuel stations.
- The Türkiye and Noto earthquakes.
- Thin kinetic coverage.

### Process lessons

- **A usage limit stopped all four content red teams once.** Plan the budget so release-critical
  reviews run before optional research.
- **Web search allows 200 calls per turn, shared with subagents.** Never route around it.
- **Many official sites refuse automated clients.** A refusal is recorded, never worked around.
- **Never junction a working tree into a worktree; copy only.** A junction once let worktree removal
  wipe the local review queue.
- **The review queue never leaves the machine:** `data/candidates/**` and its secret id key.

## 6. What to produce in this pass

### P1. The next directive for Claude Code (main deliverable)

Two phases:

- **Phase A: finish iteration 22's release.** Use §4 as written, plus explicit stop conditions:
  - no push if any gate step is red;
  - no release if production bytes differ from the commit;
  - no release if the production safety scan or the final production red team finds a blocker.
- **Phase B: iteration 23a**, only from released `main`. Candidate items to prioritise (choose and
  justify; at most eight):
  1. **Calibration run 2 design and execution.** Use imported, reviewed records only. Have at least
     three labelers, at least one of them a person outside the build. State a kappa floor before any
     label is read. Write rules for "a denial later superseded" and "a figure disputed inside one
     source". The human labeler is the owner's to arrange; the directive can only prepare the packet.
  2. **Research the not-yet-researched list in §5**, at the impact layer's inclusion contract
     (methodology §3), with the safety placement rules.
  3. **Read these archives end to end:** CISA, EPA, HC3, CERT-UA and NERC. Record how far each lane
     got (its `covered_through` date) and declare the plan before searching.
  4. **Gulf water and desalination.** Find Persian- and Arabic-language official statements where
     their sites open. Country level for anything attacked.
  5. **Find second origins for Central Asian records**, which mostly rest on one originating
     statement.
  6. **Close the open verifier notes in §5** through the review queue.
  7. **Add the manifest field the first-time-user finding C1 needs**, a count on the home card,
     without making it rankable across systems.
  8. **Schedule link-health refreshes** so a citation's state is dated and re-checked, never
     silently stale.

A good directive:
- states the budget order;
- names what counts as done in testable terms;
- lists what must never be added (§2);
- leaves every owner decision in §5 alone.

### P2. A calibration-run-2 packet and labeler instructions (optional)

Write the instructions in plain words, without the model's rubric. `docs/EVIDENCE_CONFIDENCE_V2.md`
§6 says what a packet may and may not hold.

### P3. A critique of the four owner memos (optional)

Read `docs/OWNER_DECISIONS_22.md`. For each memo, say whether its options are complete and whether
its recommendation follows from the rules. ChatGPT does not decide them.

### P4. A fresh red team of the served bytes (optional, if the user attaches them)

Use the same four lenses as the 19 November teams. Every finding needs a severity, an `impact_id` or
context `id`, and a field path.

### Attachments the user can provide

All of these come from the local checkout on branch `iteration-22`:
- `data/processed/global/impacts.json`
- `data/processed/global/regional_context.json`
- `data/processed/global/evidence_confidence.json`
- `data/processed/global/gulf.json`
- `data/curated/global_impacts/link_health.json`
- `docs/GLOBAL_IMPACT_METHODOLOGY.md`
- `docs/EVIDENCE_CONFIDENCE_V2.md`
- `docs/OWNER_DECISIONS_22.md`
- `CLAUDE.md`

The served files contain no withheld material by design. The review queue does, and must never be
uploaded anywhere.

## 7. How to hand results back to Claude Code

Claude Code applies nothing directly to data. Corrections go through the review queue and the
import gate. Return one of these:

- **A directive:** markdown, numbered sections, with explicit stop conditions and a final report
  format.
- **A findings list (markdown):** numbered, each item giving:
  - the severity;
  - the `impact_id` or context `id`;
  - the field path;
  - what it says;
  - what the source or rule says;
  - the fix.
- **Corrections (JSON), for records:**
  `{"<impact_id>": {"reason": "...", "set": {"<field path>": <value>}, "remove_sources": ["s3"]}}`.
  Field paths are dotted. List items go by index (`civilian_service_impact[0].affected.qualifier`).
  Sources go by ref (`sources[s2].title_en`).
- **Holds:** `{"<impact_id>": "reason"}` for any record that should not be published at all.

Never include in a reply anything §2 forbids, even to explain a finding. Describe a leak generically
("the URL path names the facility") and give the id and field path.
