# Evidence Confidence v2

How the dashboard describes what the sources a record cites support: the method, the properties it
is held to, how it would be calibrated against blind reviewers, and what it would do to the
theatre's index if it were ever used there (it is not).

The contract is `docs/GLOBAL_IMPACT_METHODOLOGY.md` §8. The code is
`pipeline/evidence_confidence.py`; every parameter is in `methodology/evidence_confidence.json`.
The tests are `tests/test_iteration22_confidence.py` and, for the methodology red team's findings,
`tests/test_iteration22_redteam.py`.

**Status: provisional.** The method version is `2.0-draft` and the method is served with
`status: "provisional: thresholds not calibrated"`. One blind calibration has been
run and the thresholds did not pass it (Results, below). A test ties the two: while the version ends `-draft`, no document may say otherwise.

## 1. What it is, and is not

Three separate questions, three separate answers:

1. **Evidence confidence**: on the sources this record cites, did it happen, and is the reported
   effect supported? (`assess`)
2. **Attribution confidence**: how strong is the evidence about who did it? (`attribution_confidence`)
3. **AI involvement**: does a source tie AI to this incident, at the strength claimed? (`ai_problems`)

None is a probability. None is severity, infrastructure importance or research completeness. A
well-evidenced event can have an unknown actor; a firmly attributed one can have an uncertain
effect. The three are never merged into one figure.

**What the category describes.** The sources the record cites, not everything published about the
event. A record with one citation attached may concern an event the whole press covered. It covers
occurrence and effect. It does **not** cover the cause (whether an outage was an attack or a fault)
or who was responsible. The served statement says all of this.

**Where it is used.** On impact records, and on each published country-system event as
`evidence_confidence`, with a by-category summary inside that country's own `system.json`
(`evidence_confidence_summary`). It appears in no manifest, no cross-country file and no ranking.

**Where it is not used.** The theatre's index. The ESDI multiplies each incident by a v1 weight set
from cited-host count (`confidence_weights` in `methodology/scoring.json`). That path is unchanged,
`pipeline/build_index.py` does not import this module, and tests pin both (§6).

## 2. Evidence confidence: the method

Computed from the sources that support `occurrence` or `effect`. A source that supports only
attribution or AI involvement adds nothing here, and a source recorded as disputing a claim
(`disputes`) never backs that claim.

| Component | Points | Rule |
|---|---|---|
| Who is speaking | 40 / 28 / 15 / 10 / 4 | The best supporting source: a first-party or official statement 40; press or third-party reporting 28; a secondary source 15; a researcher's social post 10; an unverified claim 4. |
| Originating statements | 0 / 16 / 25 | One, two, three or more groups, among first-party and press sources only (see below). |
| Effect specificity | 15 / 8 / 0 | Quantified, described, vague; counted only when a first-party or press source supports the effect. |
| Opened during research or review | 10 | A first-party or press source carries `opened: true`, **or** the record's own review block says a reviewer opened its sources (`review.sources_opened_by_reviewer > 0`). `opened: null` is "not recorded", never "not opened". |
| Dated account | 10 | A first-party or press source dated from the day before the event to 30 days after its end, **or** a later formal account: a dated first-party source in a formal role (`formal_account_roles`: regulator, court record, law enforcement, CERT, government) or one that says so itself (`formal_account: true`, for an operator's regulatory filing). A regulator's final report eight months on is not marked down against a same-day line. `components.contemporaneous.dated` says which; when no counted source carries a date it is `not_recorded`, and a reason line says so. |

The points are points: ordinal, a way of ordering records by what their citations show. They are
never a percentage and never "out of 100". Categories: **High** ≥ 78, **Moderate** 55–77,
**Limited** 35–54, **Preliminary** < 35.

"First-party or official" says who is speaking, not that the statement was verified. "Press or
third-party" says a wire, an outlet or a trade title carried it, not that the reporting was its
own work; that question is the originating-statement count.

### Rules that override the points

- **Not assessed.** A record cited only through a discovery aid (Wikipedia, a content aggregator)
  has `category: null` and `reason: "cited through a discovery aid only; a primary source is not
  yet attached"`. The score and every component are `null`, not zero. That is a research state,
  not a finding about the evidence, so it is never Preliminary; summaries count it apart from
  every category.
- **Independence not reviewed: at most Moderate.** See "Originating statements" below. `cap` is
  `"origins_not_reviewed"` and a reason line says so.
- **Unverified only: Preliminary.** A record resting only on unverified posts, a researcher's post
  or the actor's own claim is Preliminary whatever the points say (`cap: "unverified_only"`).
- **Disputed.** The record says its occurrence or effect is contested (`dispute`), or a first-party
  or press source is recorded as disputing one of them. The category is Disputed and the product
  does not choose: **no total is shown** (`score: null`), the reasons open with the disagreement
  and say the lines after it describe the sources cited, not a settled reading. A source that
  disputes a claim is never counted as support for it, and one that denies the event does not
  back its effect either. An anonymous denial is not credible disagreement. A dispute about who
  did it, or about the cause, does not touch this; a `dispute.about` outside the vocabulary is
  read as a dispute about the record (and `dispute_problems` refuses it at the gate).

A first-party source that is the affected party itself (`party_roles`: the operator) gets a reason
line saying so: "first-party" says who is speaking, and where that is the party whose facility it
was, nobody else the record cites has checked the account.

### Who is speaking

The role → tier table is data (`role_tier`). Nothing is promoted in code: a dataset restating
others is secondary, and a regulator's own filing is cited with the regulator's role and
`medium: "dataset"`. Social media is a medium, not a quality level: an S1 account counts as its
organisation only when the record says how its identity was established, and a platform badge is
not a way; S2 is secondary; S3 is a researcher's post; S4, or a post with no tier, is unverified
whatever role it is given.

### Originating statements

Sources are **grouped** when they share any of: an origin (an explicit `origin`, else the named
wire, else the registered domain, else the account); a publisher name; an organisation in the
parameter file's table (`origins.organisations`: a domain, a domain suffix, a publisher name or a
handle maps to an organisation, and an organisation may name a `parent`); a declared relay (a
source's `relays` names the `ref` of the statement it relays, cited or not); or a filed form and
its filer (`origins.filed_forms`: a DOE OE-417 summary and the utility that filed it, when the
record cites both). The count is the number of groups (connected components), so:

- a wire story and its republications are one; three releases from one utility are one; an
  organisation's website and its official account are one;
- `energy.gov` and `eia.gov` are one; a state news agency and its state's ministries are one;
- a relay never adds an origin, however many outlets relay;
- Wikipedia and content aggregators are discovery aids and count for nothing.

A citation that links two groups shows they were one, so **adding a source can lower the count**.
That is the one exception to "adding a source lowers nothing", and it is tested as such.

**What the count is called depends on who checked it** (`components.origins.basis`):

| `basis` | When | Wording | Ceiling |
|---|---|---|---|
| `reviewed` | The record's review block shows the source-and-attribution role accepting it (`review.roles.attribution_source` is `accept` or `accept_with_correction`). That reviewer marks relays (`relays`, or a shared `origin`). Impact records. | "N independent originating statements" | High |
| `publishers` | Anything else. Country events: their reviewers did not check which sources relay which. | "N distinct publishers cited; whether they relay one statement was not reviewed" | **Moderate** |

No reader-visible string says "independent" for a count nobody reviewed. Republication a record
does not name is invisible to the count, which can therefore only overstate independence; that is
why an unreviewed count does not earn the top category.

**Consequence on today's country records.** With the cap and the review-block rule for "opened",
almost every published country event is Moderate: the category barely separates them. That is the
honest reading of records whose sources' independence nobody checked, and it means the country
population alone cannot calibrate the thresholds (§5).

## 3. Attribution confidence

`NOT_ESTABLISHED` (never "low") when nobody credible attributes; `CLAIM_ONLY`; `LOW`; `MODERATE`;
`HIGH`; `DISPUTED`.

**A claim is a claim, in every shape it takes.** A source is the actor's own claim when it is typed
`actor_self_claim`, when it declares `attribution_basis: "actor_self_claim"` (a wire or outlet
report of the claim: the shape reviewers were given), or when its publisher or origin is the named
actor, whatever role it was given (`attribution.actor`, plus optional `actor_aliases` for a
government body announcing its own operation). A name of two or more words also matches inside a
longer publisher name ("Group X News"); a one-word name must match whole.

**A relay of a claim is the claim.** A source that `relays` a claim (or a relay of one, to any
depth), and, wherever a claim is among the sources, any restating role (wire, media, specialist
media, industry, aggregator) that declares no `attribution_basis` of its own. So "Group X claimed
responsibility", carried by any number of outlets, is `CLAIM_ONLY`; status `CLAIMED` validates;
`ATTRIBUTED` is refused; and "CLAIMED but another party also attributes" fires only when a source
has a finding of its own (a declared or role-given basis of government, law enforcement, CERT,
cybersecurity firm, researcher or media investigation).

Other rules: `UNKNOWN` is `NOT_ESTABLISHED`; `ATTRIBUTED` needs a formal government or
law-enforcement basis (any number of technical or press attributions that agree is `ASSESSED`); an
anonymous post or a discovery aid attributes nothing; news coverage restating an attribution is
not a second attribution unless the record declares what it carries.

**The confidence never says more than the status** (`attribution.status_ceiling`): `SUSPECTED` is
at most `LOW` and `ASSESSED` at most `MODERATE`, however official the source. A non-empty
`competing` list is `DISPUTED`, whatever the status.

**Who may corroborate.** Only a first-party or press-tier source with a finding of its own: not a
restating role (unless it declares `attribution_basis: "media_investigation"`), not a relay of a
statement the record also cites (`relays`), and not a post, a dataset, an aggregator or an unknown
role, which can show that someone names the actor (`LOW`) and nothing more. An attribution carried
at one remove (a wire reporting a government's statement the record does not cite) is one
attribution of the relayed basis; however many outlets carry it, and whatever bases they declare,
together they add at most one, because they may all be one press conference. Organisations that
are parent and child in the table are one.

Methodology §6 used to say `ATTRIBUTED` could rest on "several independent credible attributions
that agree". Since the iteration-22 closure §6, §8.2 and the code say the same thing: `ATTRIBUTED`
needs at least one attribution source with a government or law-enforcement basis (by role, or
declared on a first-party or press source); §6 spells out how a source's basis is read.

## 4. Properties (each tested and mutation-tested)

- A duplicate citation changes nothing. A second citation from the same publisher at the same
  origin changes nothing. Source count never enters. Order never matters.
- Adding a source never lowers the score, a component or the category, **except** where it shows
  two cited sources are one account; removing one never raises them, except where it was the link.
- Ten syndicated copies of a wire story equal one. A relay never adds an origin.
- An official source alone beats an anonymous post alone, and is not marked down for corroboration
  it could not have. Two origins are worth more than one; a fourth adds nothing.
- A self-claim alone cannot support occurrence above Preliminary, on any number of channels.
- A record whose origins were not reviewed is never High. A record cited only through a discovery
  aid has no category.
- No set of sources that are all claims, or relays of a claim, yields more than `CLAIM_ONLY`.
- An AI status other than `NONE_REPORTED` needs a source that supports `ai_involvement`;
  `CONFIRMED` needs a first-party or official source, `ASSESSED` a first-party or press source; `NONE_REPORTED` with a
  role, a relation or an AI source is refused; an anonymous post is never the sole evidence.

The ten adversarial cases of the iteration-22 brief each have a test (`test_case_01` …
`test_case_10`); the red team's reproduced cases are pinned by their own ids (B1–B4, B26, B31,
B40, the OE-417 records, F2, F8, F15, F17).

### What the red team changed (iteration 22)

| Found | Now |
|---|---|
| "Read by a reviewer" was the research lane's flag and contradicted the review block | Earned by the source flag or by the record's review block; relabelled |
| "N independent originating statements" was a count of publishers; relays reached High | Groups (connected components) with an organisation table, relays and filed forms; `basis`; unreviewed is at most Moderate |
| `min(origins, publishers)` let a citation at an origin already counted raise the count | Connected components |
| A self-claim exceeded `CLAIM_ONLY` when relayed, or published under another role | Claim detection by declaration, publisher and relay |
| A Wikipedia-only record read "Preliminary" | Not assessed: `category: null` with a reason |
| The methodology claimed a calibration that had not been run | Provisional until a result is recorded |
| The denier in a dispute counted as support | A source that disputes a claim never backs it |
| "Direct authoritative statement", "Independent reporting" | "First-party or official statement", "Press or third-party reporting" |

Earlier hardening (same iteration): `dataset` is secondary, not direct; an S1 tier needs an
established identity; a dispute with no `about` is read as a dispute about the record; an anonymous
post attributes nothing; three technical attributions are not `ATTRIBUTED`.

## 5. On country records

`pipeline/build_systems.py` attaches `evidence_confidence` to each published event from the
**served** record alone: its published citations, its dates, whether it carries a figure, and its
review block. Country citations predate claim-level provenance, so each supports occurrence and
effect.

- `effect_specificity` is `quantified` when `capacity_affected` carries a value and its `measure` is
  not `facility_size` (a plant's nameplate is not the amount lost); otherwise `described`.
- `origins.basis` is `"publishers"` for every country event, so none is High.
- **Campaign-covered records carry it too.** It is a function of fields the record already
  publishes; a test recomputes every served value from `events.json` alone.
- It changes no inclusion, no count and no other field.
- The summary counts each category and, apart from them, `not_assessed`.

## 6. Calibration against blind reviewers

The thresholds are a claim about how a careful reader sorts records by what their sources support.
The claim is checked blind. **One run has been made (19 November 2026); the thresholds did not pass it** (Results, below).

```
.venv\Scripts\python.exe scripts\eci_calibration.py packets     # writes packets.json and key.json
# reviewers each write labels_<name>.json beside packets.json, without opening key.json
.venv\Scripts\python.exe scripts\eci_calibration.py compare     # comparison.md / .json, calibration_result.json
```

- `packets` draws about 60 records (`--target`) from every country system's published events, the
  imported impact records (`data/curated/global_impacts/events.json`) when present, and impact
  candidates still in the local queue. The draw is spread across record kind, country or lane, and
  a neutral description of the sources (a dispute, a social post, an actor's claim, a first-party
  statement, press only). It is **never** stratified by the model's own category, and a record the
  model does not assess is left out.
- A packet holds an opaque id, the record's summary, effect and reported figure, its dates, and
  for each source the publisher, role, medium, social tier, date, language, the named wire it
  carries and what it supports. **Never** the category, the score, a component, the record id or a
  source address. Order is shuffled.
- Reviewers get the **question** and five labels in plain words (`HIGH`, `MODERATE`, `LIMITED`,
  `PRELIMINARY`, `DISPUTED`), not the model's rubric: no points, no thresholds, no rule about
  wires or origins. A reviewer handed the rubric reproduces it.
- `compare` reports, for each reviewer against the model and for each pair of reviewers: the
  confusion matrix, exact agreement, agreement within one category (Disputed is off the scale),
  Cohen's kappa, and the packets where two reviewers agree with each other and not with the model.
  It writes `calibration_result.json`: agreement figures and counts, no record or packet id, and a
  `decision` left `null` for the owner.
- Everything stays in `data/candidates/eci_calibration/` (gitignored, never served).

**What this calibration cannot show.** Reviewers see the same typed role, medium and `supports`
the model reads and cannot open a source, so a mistyped role or an unmarked relay is invisible to
both sides: typing is a separate error rate, not measured. Sixty packets give Cohen's kappa a wide
interval. The country population has no social posts, no actor claims and no disputes, and is
almost all Moderate, so those rules are exercised only by impact records. A calibration that could
carry a threshold would also need a reviewer who is not an agent of the build, a floor stated
before the labels are read, and reviewers who open the sources.

**What would count as calibrated.** Stated before the run: reviewer–model agreement no worse than
reviewer–reviewer agreement, on exact agreement and on kappa, **with reviewer–reviewer kappa itself
at least 0.6** (reviewers who agree poorly with each other make the first condition empty); no
category the reviewers systematically place one step away from the model; and every "two reviewers
against the model" packet explained by a named rule rather than by a threshold. Where reviewers
agree with each other and not with the model, the model moves, not the label. Only then does the
version drop `-draft`.

### Results

<!-- calibration-results:begin -->
**Run 1, 19 November 2026 (method `2.0-draft`). Result: not calibrated. The thresholds
stay provisional, the version stays `2.0-draft`, and the theatre's multiplier is unchanged.**

| | Packets | Exact | Within one | Cohen's kappa |
|---|---|---|---|---|
| Reviewer r2 vs reviewer r3 | 72 | 0.83 | 1.00 | 0.73 |
| Reviewer r2 vs model | 72 | 0.50 | 0.96 | 0.10 |
| Reviewer r3 vs model | 72 | 0.42 | 0.96 | 0.02 |

- **Sample.** 72 packets from a population of 610: 13 country
  events, 21 imported impact records and 38 impact candidates still in the
  local queue; drawn by record kind, country or lane and source profile, never by the model's
  category. The model labelled them High 11, Moderate 55, Limited 2, Preliminary 0, Disputed 4.
- **Reviewers.** Two blind labelers (a sceptical standards editor and an incident analyst at a
  regulator), each given only the packets and the plain-words question. A third labeler was
  stopped by a usage limit before writing labels; it is not counted. All three were agents of the
  same build, not independent people.
- **What it says.** The reviewers agree with each other well (kappa 0.73, every packet within one
  category). Each agrees with the model barely better than chance (kappa 0.10 and 0.02), though
  almost always within one category. Against the pre-stated test (reviewer-model agreement no worse
  than reviewer-reviewer, reviewer-reviewer kappa at least 0.6, no systematic one-step shift) the
  first condition fails clearly and the third fails: on 33 packets both reviewers agree with each other
  and not with the model.
- **Where the model and the reviewers part.** Mostly in one direction: the model says Moderate where
  both reviewers say High. Most of those packets are records whose origins were never reviewed
  (country events and queue candidates without a review block), which the model holds at Moderate
  by rule ("independence of the cited sources has not been reviewed"); the reviewers, who see the
  sources typed, judge two first-party or press accounts as High. The model is right to refuse High
  to an unreviewed relay chain and the reviewers cannot see relays either, so this disagreement is
  partly the design, not a threshold error. The smaller, opposite group (model High, reviewers
  Moderate) is two publishers with no first-party source; and three packets the model calls
  Disputed the reviewers call Moderate or Limited, because a denial later superseded, or a conflict
  inside one source, does not read to them as two credible sources disagreeing.
- **What follows.** No parameter changed. Before a second run: draw only imported (reviewed)
  records so the origin cap is not what is being measured; add a written rule for "a denial later
  superseded" and "a figure disputed inside one source"; use at least three labelers including one
  person outside the build; and state the kappa floor again before reading the labels.
- **Limits.** Reviewers saw the same typed role, medium and `supports` the model reads, and no
  source address, so a mistyped role or an unmarked relay is invisible to both. Kappa over 72
  packets has a wide interval: read it as a direction. The per-packet comparison and the labels
  stay in the local queue (`data/candidates/eci_calibration/`); nothing here is served.
<!-- calibration-results:end -->

## 7. Limitations

Known, and not fixed in this iteration. Each is a way the category can say more than the record
supports, or a rule the data cannot yet carry.

- **Cause is not a claim (red team 15).** `supports` covers occurrence, effect, attribution and AI
  involvement. Nothing records which source supports the *cause*. A record whose occurrence is well
  sourced, and whose only source for "it was a cyberattack" is the actor's boast, has a strong
  evidence category beside a cause family that category does not cover. Not implemented: no record
  in the corpus carries a per-source `cause` claim, and adding the claim means re-reviewing every
  malicious-cause record. The served statement says plainly that the category does not cover cause.
- **AI statements are checked by who speaks, not by what they say (red team 18).** `CONFIRMED`
  needs a first-party or official source, but nothing records whether that source *states*, *assesses* or merely
  *suspects* AI involvement, or whether it is about this incident. Not implemented: it needs a
  `statement_strength` on every AI source, which no record carries.
- **The per-country summary can be laid beside another country's (red team 20).** It is served in
  one shape in every `system.json`. The manifest carries none of it, no cross-system file reads it
  and its note says it reflects how a country was researched; but two files side by side are a
  comparison, and part of any difference is process. The points also rise with the number of
  outlets and with a published figure, both of which follow how much attention an event drew, so a
  sort by points would be a sort by attention. Nothing sorts by them. Not fixed: removing the
  summary is an owner decision.
- **Typing is trusted, within limits.** The tier is the role the lane typed. A state news agency
  typed `wire` is press; typed `official` it is first-party. What is cross-checked: an address on
  a social platform is a post whatever medium was typed; an archive or AMP copy is the page it
  copies; a shortened link and a news aggregator count for nothing; one account under two
  platform names is one; a wire's own site, or a publisher that names a wire, is that wire
  (`origins.wires`); a basis made of badge words establishes no identity. `source_problems` and
  `dispute_problems` list what a gate refuses (an unknown medium, role or tier, `supports` that is
  not a list of claims, an unreadable date, a dispute with no `about`). Since the iteration-22
  closure they **gate the import and the build** (methodology §12). They are deterministic checks
  of the record's own fields: they cannot tell that a valid role was the wrong one, so a mistyped
  role remains a reviewer-error rate this module does not measure.
- **Internet-measurement organisations are typed as researchers (open).** Their own direct
  measurement is secondary today, so it never counts as an originating statement or earns effect
  points. Whether it should be first-party for connectivity claims is a question for calibration
  run 2, not a change: `docs/ECI_SOURCE_ROLE_MEMO_22.md`.
- **What the origin count still cannot see (red team 6: B6, B7, B8, B17).** An operator's website
  and its account under a different publisher string; its investor-relations site on a second
  domain; a wire copy a lane filed as the outlet's own reporting. Only a reviewer marking `relays`
  or a shared `origin` joins these, which is why an unreviewed count cannot earn High.
- **Host folding (red team 21).** Hosts under a listed shared suffix (`origins.shared_suffixes`:
  `gouv.fr`, `go.jp`, `gc.ca`, blogging hosts) are separate publishers. The list is short and
  hand-kept; a suffix it lacks still folds unrelated bodies into one origin. Safe in direction.
- **A later formal account is recognised by role.** A government page dated long after the event
  earns the dated-account points whether or not it is an inquiry. Year-precision dates are read
  loosely (any source in that year is "at the time").
- **Sources are not checked to name the same actor.** Two attribution sources naming different
  actors both count toward the record's actor unless the record lists `competing`.
- **The points are added.** Ten points for a recorded flag count the same as ten for a dated
  source. The categories are thresholds on that sum, and the category meanings describe the usual
  ways of reaching each, not every way.

## 8. The theatre: a shadow study, and why the multiplier is unchanged

The theatre's index uses **v1**: `confirmed` 1.0, `probable` 0.75, `possible` 0.45,
`unverified` 0.2, set by `pipeline/fetch_wikipedia.py::_confidence` from the number of distinct
hosts cited (two or more, one, none), or typed by the curator for a curated incident.

`scripts/confidence_shadow_study.py` computes the v2 category for every scored theatre incident
from the citations it already carries and asks what the index would be under a candidate mapping.
It runs the real index builder with the weights substituted in memory and restored afterwards; it
writes no payload, and its v1 column must reproduce the served headline or the study says its own
numbers should not be used. A Disputed incident and one v2 does not assess have no category to
map; the study gives each the lowest mapped weight, stated in its output, so that neither
outweighs an incident nobody disputes.

<!-- shadow-study:begin -->
*Generated by `scripts/confidence_shadow_study.py --write` for the build dated 2026-11-19 (method 2.0-draft). A dated study, not a live figure: re-run the script to refresh it.*

**Scope.** 184 scored theatre incidents carrying 218 citations, of which 0 sit on a recognisably official domain and 139 carry a readable date.

**Cross-tabulation** (rows: the v1 label the index uses today; columns: the v2 shadow category).

| v1 \ v2 | HIGH | MODERATE | LIMITED | PRELIMINARY | DISPUTED | NOT_ASSESSED |
|---|---|---|---|---|---|---|
| confirmed | 0 | 4 | 23 | 36 | 1 | 0 |
| probable | 0 | 0 | 81 | 38 | 0 | 0 |
| possible | 0 | 0 | 0 | 0 | 1 | 0 |

**Candidate mapping evaluated:** HIGH → 1.0, MODERATE → 0.75, LIMITED → 0.45, PRELIMINARY → 0.2. (v1: confirmed 1.0, probable 0.75, possible 0.45, unverified 0.2.)

**Off the scale:** DISPUTED → 0.2, NOT_ASSESSED → 0.2. Disputed and not-assessed incidents have no category to map. Each is given the lowest mapped weight, so neither outweighs an incident nobody disputes.

**Incidents whose weight would change:** 184 lower, 0 higher, 0 unchanged (2 of them off the scale).

**Why they differ** (incidents; each line is a property of the citations).

| | Incidents |
|---|---|
| Labelled `confirmed` by v1 | 64 |
| … and cite two or more distinct hosts | 24 |
| … where the label was typed by the curator (curated incidents), not derived from citations | 47 |
| Cite two or more distinct hosts (what v1 counts for a strike-table incident) | 24 |
| … and two or more distinct publishers as v2 counts them | 23 |
| … but only one publisher as v2 counts them | 1 |
| … but no countable publisher under v2 | 0 |
| … where one of the hosts is a discovery aid (Wikipedia) | 1 |
| Cite a discovery aid at all | 1 |
| Cite nothing but a discovery aid, so v2 does not assess them | 0 |
| Have an effect the v2 model counts as supported | 15 |
| Have a citation dated within 30 days of the event | 90 |
| Have no citation with a readable date | 68 |

**Index under each weighting** (the real builder, weights substituted in memory).

| Evaluation date | Headline, v1 (served) | Headline, shadow | Shadow ÷ v1 | refining, v1 / shadow | electric_generation, v1 / shadow | transmission, v1 / shadow | oil_logistics, v1 / shadow | gas, v1 / shadow | coal, v1 / shadow |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-19 (this build) | 5.97 | 3.34 | 0.56 | 12.83 / 7.28 | 0.03 / 0.00 | 3.14 / 1.30 | 1.33 / 0.80 | 0.00 / 0.00 | 0.00 / 0.00 |
| 2026-08-22 (90 days back) | 16.42 | 8.66 | 0.53 | 27.84 / 15.10 | 0.08 / 0.03 | 24.53 / 10.94 | 8.74 / 4.88 | 0.00 / 0.00 | 0.00 / 0.00 |
| 2026-05-23 (180 days back) | 15.17 | 7.33 | 0.48 | 21.43 / 10.35 | 0.22 / 0.10 | 1.57 / 0.31 | 25.95 / 12.78 | 0.00 / 0.00 | 0.00 / 0.00 |
| 2025-11-22 (365 days back) | 11.46 | 4.56 | 0.40 | 16.49 / 6.41 | 0.25 / 0.05 | 31.50 / 11.58 | 3.86 / 2.32 | 0.00 / 0.00 | 0.00 / 0.00 |

The replay rows are earlier evaluation dates of today's corpus and code, from one build's series; not a reconstruction of what was known then.

The v1 column reproduces the served headline exactly, so the study ran the model the build runs.

**Limits of this study.**

- Theatre citations carry no source role: each is treated as independent media reporting unless its address is on a recognisably official domain (a label that is exactly gov, gouv or mil, or kremlin.ru / government.ru). Official statements quoted by the press are counted as press.
- No theatre citation records whether it was opened, and theatre incidents carry no review block, so the 10-point 'opened during research or review' component is zero for every incident. That is 'not recorded', not 'not opened'.
- The Wikipedia strike table reports that a strike happened, not what it did. Its incidents carry no supported effect, so the 15-point effect component is zero for them.
- Nobody has reviewed which theatre citations relay which, so every origin count here is a count of distinct publishers and no incident can be High: Moderate is the ceiling by rule, whatever the citations. '0 higher' in the table above therefore follows from construction, not from the evidence.
- Origins are counted by named wire, registered domain, publisher name and the organisation table. Republication the record does not name is invisible, which can only overstate independence in v1 and v2 alike.
- The candidate weights are ranks given numbers. v2 is declared not to be a probability, and nothing here shows that a Moderate incident deserves three quarters of a High one.

**`theatre_shadow` block** (for the lead to place in a payload; this script adds it to none).

```json
{
  "theatre_shadow": {
    "as_of": "2026-11-19",
    "method_version": "2.0-draft",
    "status": "shadow only: the theatre's scoring multiplier is unchanged",
    "incidents": 184,
    "cross_tabulation": {
      "rows": "v1 label (scored today)",
      "columns": "v2 category (shadow)",
      "counts": {
        "confirmed": {
          "HIGH": 0,
          "MODERATE": 4,
          "LIMITED": 23,
          "PRELIMINARY": 36,
          "DISPUTED": 1,
          "NOT_ASSESSED": 0
        },
        "probable": {
          "HIGH": 0,
          "MODERATE": 0,
          "LIMITED": 81,
          "PRELIMINARY": 38,
          "DISPUTED": 0,
          "NOT_ASSESSED": 0
        },
        "possible": {
          "HIGH": 0,
          "MODERATE": 0,
          "LIMITED": 0,
          "PRELIMINARY": 0,
          "DISPUTED": 1,
          "NOT_ASSESSED": 0
        }
      }
    },
    "candidate_mapping": {
      "HIGH": 1.0,
      "MODERATE": 0.75,
      "LIMITED": 0.45,
      "PRELIMINARY": 0.2
    },
    "off_scale_weights": {
      "weights": {
        "DISPUTED": 0.2,
        "NOT_ASSESSED": 0.2
      },
      "why": "Disputed and not-assessed incidents have no category to map. Each is given the lowest mapped weight, so neither outweighs an incident nobody disputes."
    },
    "weight_change_under_mapping": {
      "higher": 0,
      "lower": 184,
      "same": 0,
      "off_scale": 2
    },
    "why_they_differ": {
      "labelled_confirmed": 64,
      "labelled_confirmed_citing_two_or_more_hosts": 24,
      "labelled_confirmed_by_the_curator": 47,
      "two_or_more_hosts": 24,
      "two_or_more_hosts_and_two_or_more_origins": 23,
      "two_or_more_hosts_but_one_origin": 1,
      "two_or_more_hosts_but_no_origin": 0,
      "two_or_more_hosts_one_of_them_a_discovery_aid": 1,
      "cite_a_discovery_aid": 1,
      "not_assessed_by_v2": 0,
      "effect_supported": 15,
      "a_citation_dated_at_the_time": 90,
      "no_citation_with_a_readable_date": 68
    },
    "esdi": {
      "current": 5.97,
      "shadow": 3.34,
      "shadow_over_current": 0.56,
      "sectors": {
        "refining": {
          "current": 12.83,
          "shadow": 7.28
        },
        "electric_generation": {
          "current": 0.03,
          "shadow": 0.0
        },
        "transmission": {
          "current": 3.14,
          "shadow": 1.3
        },
        "oil_logistics": {
          "current": 1.33,
          "shadow": 0.8
        },
        "gas": {
          "current": 0.0,
          "shadow": 0.0
        },
        "coal": {
          "current": 0.0,
          "shadow": 0.0
        }
      }
    },
    "replay": [
      {
        "date": "2026-08-22",
        "current": 16.42,
        "shadow": 8.66,
        "shadow_over_current": 0.53
      },
      {
        "date": "2026-05-23",
        "current": 15.17,
        "shadow": 7.33,
        "shadow_over_current": 0.48
      },
      {
        "date": "2025-11-22",
        "current": 11.46,
        "shadow": 4.56,
        "shadow_over_current": 0.4
      }
    ],
    "replay_kind": "earlier evaluation dates of today's corpus and code, from one build's series; not a reconstruction of what was known then",
    "limitations": [
      "Theatre citations carry no source role: each is treated as independent media reporting unless its address is on a recognisably official domain (a label that is exactly gov, gouv or mil, or kremlin.ru / government.ru). Official statements quoted by the press are counted as press.",
      "No theatre citation records whether it was opened, and theatre incidents carry no review block, so the 10-point 'opened during research or review' component is zero for every incident. That is 'not recorded', not 'not opened'.",
      "The Wikipedia strike table reports that a strike happened, not what it did. Its incidents carry no supported effect, so the 15-point effect component is zero for them.",
      "Nobody has reviewed which theatre citations relay which, so every origin count here is a count of distinct publishers and no incident can be High: Moderate is the ceiling by rule, whatever the citations. '0 higher' in the table above therefore follows from construction, not from the evidence.",
      "Origins are counted by named wire, registered domain, publisher name and the organisation table. Republication the record does not name is invisible, which can only overstate independence in v1 and v2 alike.",
      "The candidate weights are ranks given numbers. v2 is declared not to be a probability, and nothing here shows that a Moderate incident deserves three quarters of a High one."
    ],
    "note": "A comparison only. The index is computed with the v1 weights; the shadow column shows what it would be under a candidate mapping that has not been adopted."
  }
}
```
<!-- shadow-study:end -->

### Reading the study

The study is evidence about the *mapping*, not about the incidents.

- **Much of the difference is construction.** No theatre incident's origins were reviewed, so none
  can be High; no theatre citation records being opened; the strike table reports that a strike
  was reported, not what it did. "0 higher" follows from those three facts about what the theatre
  data records, not from the evidence. The study does not measure how large that part is: a
  like-for-like comparison needs an occurrence-only measure, which does not exist yet.
- **Hosts against publishers is a separate, narrower question.** v1 counts hosts; v2 groups
  publishers. The table's "two or more hosts" rows say how often the two counts disagree for the
  incidents as cited today. That comparison is like for like, and it is the only part of the
  difference that speaks to v1's own claim.
- **Not every v1 label comes from citations.** A strike-table incident's label is computed from its
  hosts; a curated incident's label is typed by the curator. A measure computed from citations
  cannot be compared with a typed label as if both were measurements.
- **The weights are ranks given numbers.** v2 is declared not to be a probability. Nothing here
  shows that a Moderate incident deserves three quarters of the weight of a High one.
- **Read the replay as a ratio.** If shadow ÷ v1 differs from date to date, the substitution is not
  a level shift a reader could discount: it would change the shape of the series.

### The bar for ever replacing the theatre multiplier

Replacing the multiplier is a separate decision (methodology §8.3). It is not taken unless **all**
of the following hold, and it is taken by the owner, not by a build:

1. **Same concept, measured better.** The replacement answers the question the multiplier answers
   (did the event occur?) and nothing else: an occurrence-only measure, not the full v2 points.
2. **Blind calibration supports it, against a floor stated in advance.** §6 has been run on theatre
   incidents, with at least one reviewer who is not an agent of the build; reviewer pairs reach a
   kappa of at least 0.6, and reviewers agree with the replacement at least as well as with each
   other.
3. **Replay is stable.** Over earlier dates the replacement moves the index for reasons that can be
   named, and does not change the order of events in the series without a named cause.
4. **Changes are attributable.** Every incident whose weight changes can be traced to a property
   of its citations a reader can check, never to a component the theatre data cannot supply.
5. **An independent review agrees**, in writing: the owner, or a reviewer the owner names, not a
   red team the same build spawned.
6. **The review quantifies old against new**: the headline and each sector, today and at replay
   dates, and how many incidents move in each direction.
7. **The replacement does not reward volume over independence.** No incident gains weight under
   the replacement from a second citation of one origin. (v1 counts hosts and so already fails
   this; that is an argument for a replacement, not a condition on v1.)
8. **The weights are justified by outcomes, not by rank.** The mapping from category to weight
   rests on a check of old records (how often records in each category were later confirmed,
   revised or retracted by a formal account), fixed before the replay is looked at.

**Status, iteration 22.** Not met, and not proposed. Condition 1 fails for the candidate mapping,
conditions 2, 5 and 8 have not been attempted, and the generated tables above speak to 3, 4 and 6.

A test (`test_the_theatres_confidence_multiplier_is_byte_for_byte_unchanged`) pins the weights, the
function that applies them and the function that assigns the v1 label. Changing any of them fails
the build with a pointer to this section.
