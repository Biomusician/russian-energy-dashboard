# Operational-status delay options for the theatre (iteration 17)

**Adopted: 60 days** (`methodology/scoring.json` → `campaign_publication.evidence_embargo_days`),
plus the rule that a repair estimate is held until its own horizon has run out. The theatre
campaign's entry in `data/curated/systems/conflict_campaigns.json` states the policy; the code is
`pipeline/recovery.py` (`apply_campaign_embargo`, `embargo_effects`). This document is the
evidence for the number and for what it costs.

## 1. What is being delayed, and why only this

Every modelled number the theatre publishes is a function of public strike dates and a fixed
class horizon (`sector_fallback_horizon_days`). It says when a facility was struck and what the
model assumes, never what the facility is doing now. Occurrence is published at
administrative-region level as before.

The channel that does carry current operational information is **recovery evidence**: a restart
reported last week, a repair estimate whose horizon has not closed, or an effect reported weeks
after the strike ("not yet fully restored as of 30 June"). During an active campaign that is
facility-by-facility current status, which the scope boundary forbids. It is withheld until it is
history, for the dossier, the index and the build ledger alike. Withholding it from the dossier
alone would not work: a region with one struck facility publishes that facility's state through
its regional index (26 regions carry a live disruption, 17 of them a single one), and the ledger
would announce the day the evidence arrived.

Release rule, per recovery record of a campaign incident:

- **evidence date** = the latest of the observed restoration date, the partial-restart date and
  `evidence_as_of` (the date the cited source reports the state as of, where it gives no restart
  date). A forecast with none of these uses the incident date, because its estimate horizon
  decides its release. Where no source date is curated this is a floor, not the publication date;
- **released** when the evidence date is at least D days old **and**, if the record carries a
  repair estimate, the incident date plus the estimate's upper bound has passed;
- an observed status (a restart or restoration) with no date of any kind is never released,
  and nor is an effect with no date (fail closed; the final red team found both failing open).

An effect report is treated the same way, except that one reported **within 7 days of the strike
is occurrence** and is published at once (the same window as the country systems' late-citation
rule). A current build **refuses to run** while an embargoed record is in the curated files: the
repository is published as well as the payload. Such records are held locally until their
release date.

## 2. The inputs (aggregate only)

From the theatre corpus at this commit. Inter-strike intervals are reported as quantiles only:
a per-facility list would be a re-strike calendar.

| Measure | Value |
|---|---|
| Recovery records | 26 before this iteration (3 open-horizon estimates now held locally) |
| Evidence lag, strike to evidence date (n=22 dated) | median about 3 days; 0-7 days for 14 of 22; longest 209 |
| Age of the youngest recovery evidence on 2026-11-03 | 74 days |
| Facilities struck more than once | 35 of 83 |
| Re-strike interval, all repeat strikes (n=94) | p10 6 d, p25 25 d, p50 67 d, p75 178 d, p90 266 d |
| Share of re-strikes within D days of the previous strike | 7 d: 13% · 14 d: 19% · 30 d: 31% · 45 d: 44% · 60 d: 48% · 90 d: 59% |

The second-to-last line is the reason D matters. Evidence about a strike typically appears within
a few days. A facility that is struck again is struck again within 67 days half the time. With
an embargo of D days, evidence about a facility's state is published only after the re-strike
decisions that fall within D days of the previous strike have already been taken. At 60 days
that covers about half of them; at 7 days, one in eight.

## 3. What each option costs the index

ESDI under each embargo, with the same code and corpus, at three dates
(reconstructions for 2026-08-28 and 2026-10-01; the current build for 2026-11-03):

| D (days) | 2026-08-28 | 2026-10-01 | 2026-11-03 |
|---|---|---|---|
| 0 | 16.00 (0 withheld) | 8.89 (0) | 7.80 (0) |
| 7 | 16.00 (0) | 8.89 (0) | 7.80 (0) |
| 14 | 16.11 (2) | 8.89 (0) | 7.80 (0) |
| 30 | 16.11 (3) | 8.89 (0) | 7.80 (0) |
| 45 | 16.48 (5) | 8.96 (2) | 7.80 (0) |
| **60** | **16.48 (6)** | **8.96 (2)** | **7.80 (0)** |
| 90 | 16.48 (7) | 9.18 (6) | 7.86 (2) |

Withheld counts were re-measured after the final red team dated one status record
(`evidence_as_of`); the index values did not change.

An embargo raises the index slightly, because withheld restorations are scored on the modelled
horizon until they are released, which overstates exposure for that period. At 60 days the cost
is at most +0.48 points (3%) at any tested date, and nothing today: no current number changes.
That is the trade: a small, temporary over-statement of exposure, stated in the methodology and
counted in the snapshot, in exchange for not publishing facility status while it is still
operationally current.

A reconstruction before 2026-08-29 is not possible for some inputs: two Wikipedia articles have no
revision on 2026-07-01, so the earliest tested date is 2026-08-28.

## 4. Options considered

| D | Covers re-strike decisions | Index cost (max tested) | Assessment |
|---|---|---|---|
| 7 | 13% | 0 | Publishes most status inside the window when it is still useful to a targeter |
| 14 | 19% | +0.11 | As above |
| 30 | 31% | +0.11 | Better; still publishes status for most quick re-strikes |
| 45 | 44% | +0.48 | Same index cost as 60, slightly less protection |
| **60** | **48%** | **+0.48** | **Adopted, as a judgement: no current number changes, and the cost is the same as at 45** |
| 90 | 59% | +0.48 (more records held for longer) | More protection at a rising cost, and the delay starts to hide restorations a reader needs to make sense of the index |

## 5. What is published instead

- On every campaign incident without released evidence: "Current facility status withheld during
  active campaign; historical recovery evidence may be published later." This appears on **every**
  such incident, not only where a record was actually withheld. A note that appeared only on those
  would itself say which facilities have fresh reporting.
- In the snapshot (`campaign_policy`): the rule, D, and the **counts** withheld. Never the ids.
- Saudi Arabia keeps its stricter rule: no facility status at all until the campaign ends plus
  30 days (release rule A, owner decision pending).

## 6. Leakage audits (brief §6-7)

- **Region aggregates.** A region index moves only on modelled values (public strike dates times
  a class horizon) and on released evidence (at least 60 days old). In a single-facility region it
  therefore reveals nothing a public strike report did not, until the evidence is history.
- **Ledger.** The build ledger reports recovery changes by comparing consecutive snapshots.
  Because evidence enters the snapshot only once it is released, a ledger entry about recovery
  always describes something at least 60 days old, and is labelled `historical_evidence_added`
  rather than a current event.
- **Text.** The theatre's own notes, effects and recovery text were reviewed for the same
  abstraction rules as the country records. Unit inventories, criticality framing, a
  strike-damage count, sub-region places with an outage time and repair timelines were removed; a
  test holds them out.
- **Repository.** git history still contains the three held estimates and the removed wording from
  earlier commits. History is not rewritten. The policy prevents continued republication; it
  cannot recall what was published.

## 7. Open for the owner

1. Confirm D = 60 and the estimate-horizon rule (adopted here because the brief asked for it,
   and because it changes no current number).
2. Whether the theatre should ever move to the Saudi rule (no facility status until the campaign
   ends). The theatre's index is built on recovery evidence, so that would freeze its recovery
   model for the duration of the war.
3. Recording each recovery source's publication date, so that the evidence date is no longer a
   floor.
