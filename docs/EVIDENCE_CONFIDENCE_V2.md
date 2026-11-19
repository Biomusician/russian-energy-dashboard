# Evidence Confidence v2

How the dashboard describes the quality of the public evidence behind a record: the method, the
properties it is held to, how it is calibrated against blind reviewers, and what it would do to the
theatre's index if it were ever used there (it is not).

The contract is `docs/GLOBAL_IMPACT_METHODOLOGY.md` §8. The code is
`pipeline/evidence_confidence.py`; every parameter is in `methodology/evidence_confidence.json`.
The tests are `tests/test_iteration22_confidence.py`.

## 1. What it is, and is not

Three separate questions, three separate answers:

1. **Evidence confidence**: did it happen, and is the reported effect supported? (`assess`)
2. **Attribution confidence**: how strong is the evidence about who did it? (`attribution_confidence`)
3. **AI involvement**: does a source tie AI to this incident, at the strength claimed? (`ai_problems`)

None is a probability. None is severity, infrastructure importance or research completeness. A
well-evidenced event can have an unknown actor; a firmly attributed one can have an uncertain
effect. The three are never merged into one figure.

**Where it is used.** On impact records, and (since iteration 22) on each published country-system
event as `evidence_confidence`, with a by-category summary inside that country's own `system.json`
(`evidence_confidence_summary`). It appears in no manifest, no cross-country file and no ranking.

**Where it is not used.** The theatre's index. The ESDI multiplies each incident by a v1 weight set
from cited-host count (`confidence_weights` in `methodology/scoring.json`). That path is unchanged,
`pipeline/build_index.py` does not import this module, and tests pin both (§6).

## 2. Evidence confidence: the method

Computed from the sources that support `occurrence` or `effect`. A source that supports only
attribution or AI involvement adds nothing here.

| Component | Points | Rule |
|---|---|---|
| Who is speaking | 40 / 28 / 15 / 10 / 4 | The best supporting source: direct authoritative 40; independent reporting 28; secondary 15; a researcher's social post 10; an unverified claim 4. |
| Independent originating statements | 0 / 16 / 25 | One, two, three or more, among direct and independently reporting sources only. |
| Effect specificity | 15 / 8 / 0 | Quantified, described, vague; counted only when a direct or independent source supports the effect. |
| Read by a reviewer | 10 | A reviewer opened a direct or independent source. "Not recorded" earns nothing. |
| Reported at the time | 10 | A direct or independent source dated from the day before the event to 30 days after its end. |

Categories: **High** ≥ 78, **Moderate** 55–77, **Limited** 35–54, **Preliminary** < 35.

Two overrides, each a rule of its own rather than a consequence of the points:

- **Disputed.** The record says its occurrence or effect is contested (`dispute`), or a direct or
  independent source is recorded as disputing one of them (`disputes` on the source, the mirror of
  `supports`). The score is still shown; the category is Disputed and the product does not choose.
  An anonymous denial is not credible disagreement. A dispute about who did it belongs to
  attribution and does not touch this.
- **Unverified only.** A record resting only on unverified posts, a researcher's post or the
  actor's own claim is Preliminary whatever the points say.

**Who is speaking.** The role → tier table is data (`role_tier`). Nothing is promoted in code: a
dataset restating others is secondary, and a regulator's own filing is cited with the regulator's
role and `medium: "dataset"`. Social media is a medium, not a quality level: an S1 account counts as
its organisation only when the record says how its identity was established, and a platform badge
is not a way; S2 is secondary; S3 is a researcher's post; S4, or a post with no tier, is
unverified whatever role it is given.

**Independent originating statements.** The smaller of two counts over the direct and independent
sources: distinct origins (an explicit `origin`, else the named wire, else the registered domain,
else the account) and distinct publishers. So a wire story and its republications are one; three
releases from one utility are one; an organisation's website and its official account are one;
Wikipedia and content aggregators are discovery aids and count for nothing. The publisher step can
only lower the count. Republication a record does not name stays invisible, which is the one way
the count can overstate independence; a lane that can see it sets `origin`.

## 3. Properties (each tested and mutation-tested)

- Adding a source never lowers the score, any component or the category; removing one never raises
  them. (Random source sets, seeded.)
- A duplicate citation changes nothing. A second citation from the same publisher at the same
  origin changes nothing.
- Source count never enters: twenty copies of every citation give the same result.
- Ten syndicated copies of a wire story equal one.
- An official source alone beats an anonymous post alone, and is not marked down for corroboration
  it could not have: directness and corroboration are separate components.
- Two independent credible origins are worth more than one; a fourth adds nothing.
- A self-claim alone cannot support occurrence above Preliminary, on any number of channels.
- Link state never enters: a deleted official post beside an archived report still stands.
- Order of sources never matters.

Attribution and AI:

- `UNKNOWN` attribution is `NOT_ESTABLISHED`, never `LOW`.
- A self-claim alone is `CLAIM_ONLY` under any status, and cannot borrow authority through
  `attribution_basis`.
- `ATTRIBUTED` needs a formal government or law-enforcement basis. Any number of technical or
  press attributions that agree is `ASSESSED`.
- An anonymous post or a discovery aid attributes nothing.
- News coverage restating an attribution is not a second attribution: a wire, outlet or trade
  title counts toward corroboration only when the record declares what it carries
  (`attribution_basis`). Undeclared, it still shows that someone credible names the actor (`LOW`).
- An AI status other than `NONE_REPORTED` needs a source that supports `ai_involvement`;
  `CONFIRMED` needs a direct source, `ASSESSED` a direct or independent one; `NONE_REPORTED` with a
  role, a relation or an AI source is refused; an anonymous post is never the sole evidence.

The ten adversarial cases of the iteration-22 brief each have a test with an explicit expected
outcome (`test_case_01` … `test_case_10`).

### Changes made while hardening (iteration 22)

Each was a way the draft could reward volume or borrowed authority:

| Found | Now |
|---|---|
| `dataset` was promoted to direct in code, against the parameter file | Follows `role_tier`: secondary |
| An organisation's site and its official account counted as two origins | One (publisher count) |
| An S1 tier with no established identity counted as the organisation | Unverified |
| A source could not record that it disputes the record | `disputes`, honoured for direct and independent sources |
| A dispute with no `about`, or a list, was ignored | Read as a dispute about the record |
| A self-claim could carry `attribution_basis: government` | A claim is a claim |
| An anonymous post with role `government` could support `ATTRIBUTED` | Attributes nothing |
| A government statement plus a news report of it read as `HIGH` attribution | `MODERATE` unless the report declares a basis of its own |
| Three technical attributions were enough for `ATTRIBUTED` | An official basis is required (methodology §8.2) |

Methodology §6 still says `ATTRIBUTED` may rest on "several independent credible attributions that
agree"; §8.2 and the code say it needs an official basis. The code follows §8.2. §6 should be
brought into line.

## 4. On country records

`pipeline/build_systems.py` attaches `evidence_confidence` to each published event from the
**served** record alone: its published citations, its dates, and whether it carries a figure.
Country citations predate claim-level provenance, so each supports occurrence and effect.

- `effect_specificity` is `quantified` when `capacity_affected` carries a value and its `measure` is
  not `facility_size` (a plant's nameplate is not the amount lost); otherwise `described`. Never
  `vague`: a country record is admitted only with a reported effect.
- **Campaign-covered records carry it too.** It is a function of fields the record already
  publishes, so it can say nothing its citations do not; a test recomputes every served value from
  `events.json` alone.
- It changes no inclusion, no count and no other field.

## 5. Calibration against blind reviewers

The thresholds are a claim about how a careful reader sorts records by evidence quality. The claim
is checked blind.

```
.venv\Scripts\python.exe scripts\eci_calibration.py packets     # writes packets.json and key.json
# reviewers each write labels_<name>.json beside packets.json, without opening key.json
.venv\Scripts\python.exe scripts\eci_calibration.py compare     # prints and writes comparison.md / .json
```

- `packets` samples every country system's published events, up to two from each category the
  model gave in each country, plus any impact candidates in the local queue. A packet holds an
  opaque id, the record's summary, effect and reported figure, its dates, and for each source the
  publisher, role, medium, social tier, date, language, the named wire it carries and what it
  supports. **Never** the category, the score, a component, the record id or a source address.
  Order is shuffled. Reviewers do not see whether a reviewer opened a source, so the model's
  10-point "read by a reviewer" component is invisible to them; `compare` lists the model's
  components beside each disagreement so that effect can be told apart from a threshold problem.
- Labels: `HIGH`, `MODERATE`, `LIMITED`, `PRELIMINARY`, `DISPUTED`, with a one-sentence reason.
- `compare` reports, for each reviewer against the model and for each pair of reviewers: the
  confusion matrix, exact agreement, agreement within one category (Disputed is off the scale and
  is within one of nothing), Cohen's kappa, and the packets where two reviewers agree with each
  other and not with the model.
- Everything stays in `data/candidates/eci_calibration/` (gitignored, never served).

**What would count as calibrated.** Reviewer–model agreement no worse than reviewer–reviewer
agreement, on exact agreement and on kappa; no category the reviewers systematically place one step
away from the model; and every "two reviewers against the model" packet explained by a named rule
rather than by a threshold. Where reviewers agree with each other and not with the model, the
model moves, not the label.

### Results

<!-- calibration-results:begin -->
*Not yet run. The lead fills this in from `comparison.md` after reviewers label the packets: the
number of packets and reviewers, each reviewer's exact / within-one agreement and kappa against the
model, the same between reviewers, the packets where two reviewers disagreed with the model, and
any parameter changed as a result (with the version bumped in `methodology/evidence_confidence.json`).
Until then `version` stays `2.0-draft` and the thresholds are provisional.*
<!-- calibration-results:end -->

## 6. The theatre: a shadow study, and why the multiplier is unchanged

The theatre's index uses **v1**: `confirmed` 1.0, `probable` 0.75, `possible` 0.45,
`unverified` 0.2, set by `pipeline/fetch_wikipedia.py::_confidence` from the number of distinct
hosts cited (two or more, one, none), or typed by the curator for a curated incident.

`scripts/confidence_shadow_study.py` computes the v2 category for every scored theatre incident
from the citations it already carries and asks what the index would be under a candidate mapping.
It runs the real index builder with the weights substituted in memory and restored afterwards; it
writes no payload, and its v1 column must reproduce the served headline or the study says its own
numbers should not be used.

<!-- shadow-study:begin -->
*Generated by `scripts/confidence_shadow_study.py --write` for the build dated 2026-11-19 (method 2.0-draft). A dated study, not a live figure: re-run the script to refresh it.*

**Scope.** 184 scored theatre incidents carrying 218 citations, of which 0 sit on a recognisably official domain and 139 carry a readable date.

**Cross-tabulation** (rows: the v1 label the index uses today; columns: the v2 shadow category).

| v1 \ v2 | HIGH | MODERATE | LIMITED | PRELIMINARY | DISPUTED |
|---|---|---|---|---|---|
| confirmed | 0 | 4 | 23 | 36 | 1 |
| probable | 0 | 0 | 81 | 38 | 0 |
| possible | 0 | 0 | 0 | 0 | 1 |

**Candidate mapping evaluated:** HIGH → 1.0, MODERATE → 0.75, LIMITED → 0.45, PRELIMINARY → 0.2. (v1: confirmed 1.0, probable 0.75, possible 0.45, unverified 0.2.)

**Incidents whose weight would change:** 182 lower, 0 higher, 0 unchanged, 2 Disputed with no mapped weight (kept at v1).

**Why they differ** (incidents; each line is a property of the citations).

| | Incidents |
|---|---|
| Labelled `confirmed` by v1 | 64 |
| … and cite two or more distinct hosts | 24 |
| … where the label was typed by the curator (curated incidents), not derived from citations | 47 |
| Cite two or more distinct hosts (what v1 counts for a strike-table incident) | 24 |
| … and two or more independent origins under v2 | 23 |
| … but only one independent origin under v2 | 1 |
| … but no independent origin under v2 | 0 |
| … where one of the hosts is a discovery aid (Wikipedia) | 1 |
| Cite a discovery aid at all | 1 |
| Have an effect the v2 model counts as supported | 15 |
| Have a citation dated within 30 days of the event | 90 |
| Have no citation with a readable date | 68 |

**Index under each weighting** (the real builder, weights substituted in memory).

| Evaluation date | Headline, v1 (served) | Headline, shadow | Shadow ÷ v1 | refining, v1 / shadow | electric_generation, v1 / shadow | transmission, v1 / shadow | oil_logistics, v1 / shadow | gas, v1 / shadow | coal, v1 / shadow |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-19 (this build) | 5.97 | 3.34 | 0.56 | 12.83 / 7.28 | 0.03 / 0.00 | 3.14 / 1.30 | 1.33 / 0.80 | 0.00 / 0.00 | 0.00 / 0.00 |
| 2026-08-22 (90 days back) | 16.42 | 8.66 | 0.53 | 27.84 / 15.10 | 0.08 / 0.03 | 24.53 / 10.94 | 8.74 / 4.88 | 0.00 / 0.00 | 0.00 / 0.00 |
| 2026-05-23 (180 days back) | 15.17 | 7.33 | 0.48 | 21.43 / 10.35 | 0.22 / 0.10 | 1.57 / 0.31 | 25.95 / 12.78 | 0.00 / 0.00 | 0.00 / 0.00 |
| 2025-11-22 (365 days back) | 11.46 | 4.65 | 0.41 | 16.49 / 6.41 | 0.25 / 0.05 | 31.50 / 12.40 | 3.86 / 2.32 | 0.00 / 0.00 | 0.00 / 0.00 |

The replay rows are earlier evaluation dates of today's corpus and code, from one build's series; not a reconstruction of what was known then.

The v1 column reproduces the served headline exactly, so the study ran the model the build runs.

**Limits of this study.**

- Theatre citations carry no source role: each is treated as independent media reporting unless its address is on a recognisably official domain (a label that is exactly gov, gouv or mil, or kremlin.ru / government.ru). Official statements quoted by the press are counted as press.
- No theatre citation records whether a reviewer opened it, so the 10-point 'read by a reviewer' component is zero for every incident.
- The Wikipedia strike table reports that a strike happened, not what it did. Its incidents carry no supported effect, so the 15-point effect component is zero for them.
- Because of the two limits above, no strike-table incident can reach High whatever its citations: the ceiling is 28 + 25 + 10 = 63, Moderate.
- Origins are counted by named wire, registered domain and publisher name. Republication the record does not name is invisible, which can only overstate independence in v1 and v2 alike.

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
          "DISPUTED": 1
        },
        "probable": {
          "HIGH": 0,
          "MODERATE": 0,
          "LIMITED": 81,
          "PRELIMINARY": 38,
          "DISPUTED": 0
        },
        "possible": {
          "HIGH": 0,
          "MODERATE": 0,
          "LIMITED": 0,
          "PRELIMINARY": 0,
          "DISPUTED": 1
        }
      }
    },
    "candidate_mapping": {
      "HIGH": 1.0,
      "MODERATE": 0.75,
      "LIMITED": 0.45,
      "PRELIMINARY": 0.2
    },
    "weight_change_under_mapping": {
      "higher": 0,
      "lower": 182,
      "same": 0,
      "disputed_no_mapping": 2
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
        "shadow": 4.65,
        "shadow_over_current": 0.41
      }
    ],
    "replay_kind": "earlier evaluation dates of today's corpus and code, from one build's series; not a reconstruction of what was known then",
    "limitations": [
      "Theatre citations carry no source role: each is treated as independent media reporting unless its address is on a recognisably official domain (a label that is exactly gov, gouv or mil, or kremlin.ru / government.ru). Official statements quoted by the press are counted as press.",
      "No theatre citation records whether a reviewer opened it, so the 10-point 'read by a reviewer' component is zero for every incident.",
      "The Wikipedia strike table reports that a strike happened, not what it did. Its incidents carry no supported effect, so the 15-point effect component is zero for them.",
      "Because of the two limits above, no strike-table incident can reach High whatever its citations: the ceiling is 28 + 25 + 10 = 63, Moderate.",
      "Origins are counted by named wire, registered domain and publisher name. Republication the record does not name is invisible, which can only overstate independence in v1 and v2 alike."
    ],
    "note": "A comparison only. The index is computed with the v1 weights; the shadow column shows what it would be under a candidate mapping that has not been adopted."
  }
}
```
<!-- shadow-study:end -->

### Reading the study

The study is evidence about the *mapping*, not about the incidents.

- **Under the candidate mapping the two measure different things.** v1 asks one question: how many
  hosts are cited? v2 also asks whether a reviewer read a source and whether the effect is
  supported, and the theatre's records hold neither: the strike table reports that a strike was
  reported, and no theatre citation records being opened. Those components are zero by
  construction for almost every incident (the "Why they differ" table counts the exceptions), so
  the shadow index is lower partly because of what the theatre data does not record. The study does
  not measure how large that part is: a like-for-like comparison needs an occurrence-only measure,
  which does not exist yet.
- **Hosts against origins is a separate, narrower question.** v1 counts hosts; v2 counts
  independent originating statements. The table's "two or more hosts" rows say how often the two
  counts disagree for the incidents as cited today. That comparison is like for like, and it is
  the only part of the difference that speaks to v1's own claim.
- **Not every v1 label comes from citations.** A strike-table incident's label is computed from its
  hosts; a curated incident's label is typed by the curator. The "labelled `confirmed`" rows show
  how many are which. A measure computed from citations cannot be compared with a typed label as if
  both were measurements.
- **Read the replay as a ratio.** If shadow ÷ v1 differs from date to date, the substitution is not
  a level shift a reader could discount: it would change the shape of the series.

### The bar for ever replacing the theatre multiplier

Replacing the multiplier is a separate decision (methodology §8.3). It is not taken unless **all**
of the following hold, and it is taken by the owner, not by a build:

1. **Same concept, measured better.** The replacement answers the question the multiplier answers
   (did the event occur?) and nothing else. Effect specificity and reviewer reading are not part of
   that question; a replacement would use an occurrence-only measure, not the full v2 score.
2. **Blind calibration supports it.** Section 5 has been run on theatre incidents, and reviewers
   agree with the replacement at least as well as with each other.
3. **Replay is stable.** Over earlier dates the replacement moves the index for reasons that can be
   named, and does not change the order of events in the series without a named cause.
4. **Changes are attributable.** Every incident whose weight changes can be traced to a property
   of its citations a reader can check (a host that is a discovery aid, two hosts that are one
   origin), never to a component the theatre data cannot supply.
5. **The methodology red team agrees**, in writing, in that iteration's review.
6. **The review quantifies old against new**: the headline and each sector, today and at replay
   dates, and how many incidents move in each direction.
7. **Nothing rewards volume over independence.** No incident gains weight from a second citation
   of one origin, under either measure.

**Status, iteration 22.** Not met, and not proposed. Condition 1 fails for the candidate mapping
(it imports two components the theatre cannot supply), condition 2 has not been run on theatre
incidents, and the generated tables above speak to 3, 4 and 6. A future proposal would have to be
occurrence-only, would have to say what replaces a curator's typed label, and would start from the
hosts-against-origins rows, not from the headline difference.

A test (`test_the_theatres_confidence_multiplier_is_byte_for_byte_unchanged`) pins the weights, the
function that applies them and the function that assigns the v1 label. Changing any of them fails
the build with a pointer to this section.
