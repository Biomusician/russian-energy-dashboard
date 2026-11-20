# Evidence Confidence v2: calibration run 2 plan

Iteration 22 closure. **Preparation only.** Nothing here has been run. Evidence Confidence stays
`2.0-draft` and is served as `provisional: thresholds not calibrated`; the theatre's multiplier is
untouched whatever this run shows (`docs/EVIDENCE_CONFIDENCE_V2.md` §8).

**If no human reviewer from outside the build is available, the packet is prepared and the run
stops. The draft remains.** Agent labels, however many and however they agree, do not substitute.

Run 1 (19 November 2026, recorded in `docs/EVIDENCE_CONFIDENCE_V2.md` §6) failed: reviewers agreed
with each other (kappa 0.73) and barely with the model (0.10 and 0.02). It also could not have
passed on its own terms, because both labelers were agents of the build and most disagreement came
from unreviewed records the model holds at Moderate by rule. This plan fixes those design faults
before anyone labels anything.

## 1. Population

- **Imported, reviewed impact records only**: `data/curated/global_impacts/events.json`. At this
  plan's writing that is 245 records, every one with `origins.basis: "reviewed"`, so the
  origins-not-reviewed cap is not what the run measures.
- **Excluded**: country-system events (their origins were never reviewed, so they are capped at
  Moderate by rule; run 1 showed that cap dominates any comparison), queue candidates (never
  reviewed), the theatre.
- **Draw**: about 80 packets, stratified by record kind and the neutral source profile the script
  already uses (disputed, social, actor's claim, first-party, press or secondary), plus one new
  profile for records citing an internet-measurement organisation (`docs/ECI_SOURCE_ROLE_MEMO_22.md`).
  Every record with a dispute in the record or its sources is drawn (6 today). **Never stratified by the model's
  category.**
- **What the population cannot show.** The model puts 235 of the 245 in High or Moderate and only 4
  in Limited, 5 in Preliminary, 1 in Disputed. The run mainly tests the High/Moderate line; the tails
  are reported descriptively and cannot carry a threshold. With prevalence this skewed, kappa can be
  low while exact agreement is high, so exact agreement is reported beside it (the bar still uses
  the predeclared kappa).

## 2. Labelers

- **At least three counted labelers, all people, at least one of them outside the build.** "Outside
  the build" means a person who has not researched, reviewed, imported or written any record, and
  has not written or read the Evidence Confidence method. The owner may be a counted labeler inside
  the build; a labeler who has read the method is recorded as having done so.
- **A Claude agent is not a human and is not outside the build**, whatever persona it is given. Agents
  may be **pilot labelers only**: their labels are reported in a separate section, never counted
  toward the three, never in the bar, and never cited as support for a threshold.
- Labelers work independently, see no other labels until all counted labels are in, and never see
  the key.

## 3. The bar, stated before any label is read

Frozen in this document and in a `bar.json` in the run folder whose hash is committed before packets
go out. The owner confirms or amends it (`docs/OWNER_DECISIONS_22.md`, D-I22-4) **before**
distribution; after that it does not move.

1. **Reviewers agree with each other.** Cohen's kappa of **every** pair of counted labelers is at
   least **0.6**. If any pair falls below, the run is inconclusive, not failed and not passed: the
   question was not answerable by these readers.
2. **The model agrees no worse than reviewers do.** Mean reviewer-to-model agreement is at least mean
   reviewer-to-reviewer agreement among counted labelers, on exact agreement **and** on kappa.
3. **No systematic category shift.** Over the packets where the counted labelers' majority label and
   the model's category are both on the ordinal scale and differ, a two-sided sign test on "reviewers
   one step higher" against "one step lower" is not significant at 0.05, overall and within each
   model category with at least eight such packets. (Proposed test; the owner confirms it.)
4. **Every "reviewers agree, model differs" packet is explained by a named rule**, not by a
   threshold. Where reviewers agree with each other and not with the model, the model moves, not the
   label.
5. Disputed is off the scale: agreement on it is reported, never folded into within-one figures.

All five hold: the result goes to the owner as a pass, who decides whether the version drops
`-draft`. Any fails: no parameter changes on this run's strength; findings go to the owner.

## 4. Frozen method

- **File and version**: `methodology/evidence_confidence.json`, `"version": "2.0-draft"` (points
  40/28/15/10/4 for who is speaking, 0/16/25 for originating statements, 15/8/0 for effect, 10
  opened, 10 dated account within 30 days; categories High 78, Moderate 55, Limited 35), with
  `pipeline/evidence_confidence.py` at the same commit.
- At packet time the key records the commit SHA and a sha256 of both files. A change to either
  between packets and comparison voids the run.
- **Rules to settle before freezing** (each would otherwise show up as disagreement the run cannot
  attribute): how the model treats a denial later superseded and a disagreement inside one source
  (today a record-level `dispute` about occurrence or effect, or any first-party or press source
  recorded as disputing one, makes the record Disputed whatever the dates and whether or not the
  disagreement sits inside one source: run 1's three Disputed disagreements came from exactly
  these); the measurement-organisation typing question,
  which the run tests rather than settles (memo, "What calibration run 2 must test").

## 5. Blind key handling

- **Secret seed.** Packet ids are a hash of seed, kind and record id. The default seed (22) is in the
  public code and record ids are served, so with the default anyone could map a packet to its record.
  Run 2 uses a random seed generated at packet time and stored only in `key.json`.
- **The key never leaves the owner's machine.** It stays in the gitignored `data/candidates/eci_calibration/`.
  Labelers receive `packets.json` alone, copied into a fresh folder: no repository access.
- **Look-up risk.** A packet's summary is the served summary, so a labeler could find the record and
  its served category on the dashboard or in the CSV. Labelers are asked not to look records up and
  to confirm they did not. Pilot agents run with only the packets file, in an empty folder, with no
  repository and no web access.
- **Order.** Commit the bar hash; generate packets; distribute; collect every counted label file;
  only then run `compare`. Nobody labels after seeing a comparison.
- **Same information on both sides.** Packets carry no source address (a test pins this), so the
  model and the reviewers see the same typed fields and the run isolates the thresholds from the
  typing. Typing error is a separate question: optionally, after labels are in, the outside reviewer
  opens the sources of a small subset and says whether each role was typed correctly. That estimates
  typing error and is reported apart from the bar.

## 6. The comparison script: what must change

`scripts/eci_calibration.py` (not changed by this plan; each item is a code change with tests and,
where it guards an invariant, a mutant):

1. **Population switch.** `build_packets` always mixes country events, imported records and queue
   candidates. Add `--population imported` (default for run 2) drawing only `impact_records()`,
   and a way to take every record of a named source profile (the round-robin draw does not
   guarantee that all six disputed-profile records are drawn).
2. **Seed.** Generate a secret random seed by default; refuse the public default for a counted run.
3. **Freeze.** Write the commit SHA and sha256 of the method file and module into `key.json`;
   `compare` refuses when they differ from the working tree.
4. **Roster.** A `reviewers.json` beside the labels: each label file's name, kind
   (`human_outside_build`, `human_inside_build`, `agent_pilot`) and whether that labeler has read
   the method. `compare` computes every bar figure over counted humans only, reports pilots in their
   own section, and refuses a label file with no roster entry or a run with fewer than three counted
   humans or no outside human.
5. **Bar.** Read the predeclared `bar.json` (floor, tests, alpha), refuse if it is newer than any
   label file, and compute each condition of §3 as true or false. `result_block` carries the
   per-condition results; `decision` stays `null` for the owner.
6. **Statistics now missing.** Mean pairwise kappa and mean reviewer-to-model kappa and exact
   agreement; the human majority label per packet; the sign test of §3.3, overall and per model
   category; a bootstrap 95% interval for each kappa (resampling packets), because 80 packets give a
   wide interval.
7. **Packet content the model reads and reviewers cannot see.** The model reads each source's
   `disputes`, the record's `dispute`, declared `relays`, `formal_account` and the review block;
   packets carry none of them. Add, in neutral words: which claim a source disputes, the record's
   dispute statement, "relays source N" as a packet-local index, and "formal account" where marked.
   The packet-fields test is updated to the new list; source addresses stay out.
8. **Measurement profile.** `source_profile` gains the measurement-organisation profile; the packet
   names the role in plain words; `compare` reports those packets separately and computes the
   model's category under each option in the memo, in memory.
9. **Run identity.** `key.json` and the result block carry the run number, so run 2 never overwrites
   run 1's record.

## 7. Reviewer instructions (plain language; no model rubric)

Given to every labeler, counted or pilot, with the packets. They state the question and how to read
four hard cases. They contain no points, no thresholds and no rule about wires or origins.

> **Your task.** Each packet describes one reported disruption and the sources cited for it: who
> published each source, in what role, when, in what language, and what it supports. For each
> packet answer one question: **on these sources, how well supported is it that the event happened
> and that the reported effect is as described?** Not how severe it was, not how likely, not how
> important the facility, and not who or what caused it.
>
> Use one label. **HIGH**: well supported. **MODERATE**: supported, with a gap you can name.
> **LIMITED**: reported, but thinly supported. **PRELIMINARY**: a lead more than a finding.
> **DISPUTED**: credible sources currently disagree about whether it happened or what the effect
> was. In one sentence, say what decided it.
>
> **Four cases to read carefully.**
>
> 1. *A denial later superseded.* Someone denied the event or its effect, and a later source (often
>    the same party) confirmed it. Judge the record as the sources stand now, using their dates. A
>    denial that has been withdrawn or overtaken is not a live disagreement; it is DISPUTED only if
>    a credible source still maintains it.
> 2. *Disagreement inside one source.* One article reports two figures, or reports a claim and a
>    denial side by side. That is one source describing uncertainty, not two sources disagreeing.
>    Ask whether the event and the reported effect are supported; an uncertain figure may lower
>    your label, but on its own it does not make the record DISPUTED.
> 3. *An actual dispute.* Two credible sources, each giving its own account, contradict each other
>    about whether it happened or what the effect was, and neither has been withdrawn. That is
>    DISPUTED. A disagreement about the cause or about who did it is not: judge only occurrence and
>    effect.
> 4. *An organisation reporting its own measurement.* Some sources are organisations that measure
>    networks (for example internet connectivity) and report what their own instruments recorded.
>    Treat such a report as what it is: a first-hand observation of what they measured, which may or
>    may not be the effect the record describes (a connectivity drop is not itself a power outage).
>    Weigh it as you judge right, and say how in your sentence.
>
> **Do not** open any key file, other reviewers' labels, the method documents or the dashboard, and
> do not search for the records. Return a file named `labels_<your name>.json`:
> `{"<packet_id>": {"label": "HIGH|MODERATE|LIMITED|PRELIMINARY|DISPUTED", "reason": "one sentence"}}`.

## 8. Owner decision template (filled after `compare`)

```
Calibration run 2: owner decision
Run date:                       Method file sha256 / commit:
Packets:            Counted labelers (outside / inside):        Pilot agents (reported apart):
Bar committed (hash, date):
Condition 1  every reviewer pair kappa >= 0.6:            met / not met   (lowest pair: )
Condition 2  model agreement >= reviewer agreement:       met / not met   (exact:   kappa:  )
Condition 3  no systematic shift (sign test):             met / not met   (where: )
Condition 4  every reviewers-vs-model packet named rule:  met / not met   (unexplained: )
Measurement-organisation records: best-agreeing option A / B / C, or no difference
Typing audit (optional): roles checked:     mistyped:
Decision:  [ ] drop -draft (version 2.0)   [ ] keep 2.0-draft   [ ] change rule ___ and run again
Reason (one paragraph):
Signed:                        Date:
```

## 9. Stop rule

No outside human labeler: stop after section 5's packet generation; record "run 2 prepared, not
run" in `docs/EVIDENCE_CONFIDENCE_V2.md` §6; the version stays `2.0-draft`. Fewer than three counted
human labelers: same. A pilot run with agents may be made to test the packets and instructions; its
figures are reported as a pilot and carry nothing.
