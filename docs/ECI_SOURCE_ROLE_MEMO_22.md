# Evidence Confidence: how to type an internet-measurement organisation (open calibration issue)

Iteration 22 closure. **An open question recorded for calibration run 2, not a change.** Evidence
Confidence stays `2.0-draft`; no role, tier or parameter moves before a calibration run that tests
this question has passed (`docs/ECI_CALIBRATION_RUN2_PLAN.md`).

## The question

Some institutions publish their **own direct measurement** of networks: a connectivity
observatory that reports a national internet outage from its probes, or a content-delivery
network's traffic observatory that reports what its own traffic did in a country. When such an
organisation says "connectivity in country X fell to near zero at 14:00", is that:

- ordinary research commentary (someone analysing what others report), which is how it is typed
  today; or
- a first-hand account of an observation the organisation itself made, closer to an operator
  reporting its own network?

It matters because the impact layer cites these organisations often, and their typing decides
whether their citation counts at all.

## Current typing

Both organisations cited in the reviewed corpus are typed `source_role: "researcher"`; their posts
are social tier S2. Both map to the **secondary** tier (`methodology/evidence_confidence.json`:
`role_tier.researcher` and `social_tier.S2`), 15 points for "who is speaking".

In the 245 imported records: 35 records cite one or both (52 citations); 25 of those records are
electricity disruptions (a national blackout seen as a connectivity drop) and 10 are telecom
disruptions (outages and authority-ordered shutdowns).

## What that typing does to a score, in words

The secondary tier sits outside the tiers that corroborate (first-party and press). So a
measurement citation:

- is never counted as an originating statement;
- never earns the effect-specificity points, even when it carries the only figure for the effect;
- never earns the "opened during research or review" or "dated account" points, even when it is
  opened and timestamped to the minute;
- adds points only when it is the best source the record has, and then 15, which is Preliminary.

In practice: on a record that also cites an operator, a government or the press, the measurement
citation changes nothing. On a record that rests on it alone (in the corpus, telecom shutdowns where
no authority speaks and no outlet adds its own account), the record is **Preliminary**, "a lead more
than a finding", although the measurement is a direct observation of exactly the effect claimed.

A dry run on the imported corpus (in memory only; nothing was written or changed; posts and web
pages retyped alike, which assumes the social-tier question below is settled) shows the scale.
Of the 35 records: today 19 High, 11 Moderate, 5 Preliminary. Typed as press-tier, 11 would change
category (6 Moderate to High, 4 Preliminary to Moderate, 1 Preliminary to Limited). Typed as
first-party throughout, 16 would change. Typed as first-party for telecom records only, 8 of the 10
telecom records would change (3 Moderate to High, 5 Preliminary to Moderate) and no electricity
record would.

## Why the answer is not obvious

- **Direct for one claim, indirect for another.** The organisation observed its own traffic or
  probes. For "connectivity fell", that is a first-hand observation. For "the power grid failed", a
  connectivity drop is a proxy: it is consistent with a blackout and with a shutdown order, and the
  organisation usually says so. The role is the same; what it is first-hand about differs by claim.
- **Not the affected party, not an authority.** It is neither the operator whose network failed nor
  a body with a duty to report. It is also not a press outlet relaying someone else.
- **Interpretation is mixed in.** Posts often join the measurement ("traffic down 90%") to an
  inference ("consistent with a government-ordered shutdown"). Only the first part is the
  organisation's own observation; cause is not covered by Evidence Confidence at all
  (`docs/EVIDENCE_CONFIDENCE_V2.md` §7).
- **Origins.** The organisation's website and its social account are one origin. The organisation
  table has no entry for either organisation today. No current record cites both channels of one
  organisation under different publisher strings, but any retyping must add the table entries
  first, or two channels of one observatory could count as two statements.

## Options

**A. A new role, `measurement`, in the press tier.** The organisation's own measurement counts as
third-party reporting: an originating statement, effect points, opened and dated credit. Simple;
treats every claim alike, so an electricity record would gain from a connectivity proxy.

**B. Keep `researcher` (secondary).** No change. Conservative in direction: it can only understate.
Its cost is that records resting on direct measurement alone read as leads, and the High/Moderate
line for 25 electricity records is decided without counting the most precise timing evidence they
cite.

**C. First-party for connectivity claims only.** A measurement organisation's own observation is
first-party evidence for occurrence and effect **on a telecom or connectivity disruption**, and
stays secondary for every other claim (a power outage inferred from connectivity, a cause, an
attribution). This matches what the organisation actually observed. It needs a claim-scoped tier,
which the model does not have (a tier is per source, not per claim), so it is a code change with
its own tests, and a typing rule reviewers must apply consistently.

Any option other than B also needs: organisation-table entries for each measurement organisation
(website and account as one origin); a decision on the social tier, because an S2 post is
secondary whatever its role, so the organisation's own account would have to be S1 with its
identity established from its own site for a post to count as the organisation speaking; a written
line separating the measurement from the interpretation in a post; and a mutation for the new
rule.

## What calibration run 2 must test

1. **Include the case.** The draw must contain records whose only evidence for occurrence and
   effect is a measurement organisation (telecom), and electricity records where it sits beside
   other sources, enough of each to read a direction. The draw stays stratified by source profile,
   never by the model's category.
2. **Show reviewers what the source is, not what tier it gets.** The packet gives the role in plain
   words ("an internet-measurement organisation reporting its own measurement") and the claim it
   supports; never the tier or the points.
3. **Compare against each option, not only the current model.** For these records, compute the
   model's category under A, B and C (in memory, as the dry run above did) and report reviewer
   agreement with each. Fix which comparison decides before the labels are read.
4. **Check the claim split.** Report telecom and electricity records separately: option C predicts
   reviewers treat the two differently; option A predicts they do not.
5. **Decision rule, stated in advance.** If human reviewers who agree with each other (kappa at the
   run's floor) agree with an option better than with B on these records, without breaking any
   other condition of the run, that option goes to the owner as a proposal. If not, B stays. Nothing
   changes on the strength of agent labels alone.

Until then the typing is B, and this memo is the record of why it is an open question.
