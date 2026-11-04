# Current-event publication policy: kinetic campaigns

*Iteration 16. Status: the interim rule (§3) is implemented; the release rule (§5) is a
PROPOSAL awaiting owner approval. Machine-readable form: `data/curated/systems/conflict_campaigns.json`.*

**ONGOING CONFLICT MONITORING MUST NOT BECOME A FACILITY-STATUS FEED.**

The dashboard records historical disruption. During an active kinetic campaign, a struck
facility's *current* operating state — restarted, still offline, running at 70%, restart
postponed — is battle-damage-assessment information. It is public, but collected facility by
facility and kept current, it would be exactly the feed this project must never become.

## 1. What is always published, campaign or not

| Element | Published | Why |
|---|---|---|
| Event occurrence (that it happened, date) | yes | the historical record; reported publicly at the time |
| Administrative-level placement | yes, admin-1 only | the project's only geographic precision |
| The reported effect at the time (shut, cut by a stated volume) | yes | the disruption itself, as reported |
| Sources | yes, publisher and link | provenance |

## 2. What a record in an ACTIVE campaign does not publish

| Element | Published while active | Where the evidence goes |
|---|---|---|
| Facility restart, recovery, return to service | no — the withheld marker instead | the local candidate queue (never the public repository) |
| Continuing outage ("still shut", "had not resumed") | no | same |
| Operating rate after the event ("running at about 70%") | no | same |
| Planned or postponed restart dates | no | same |
| Dependency between facilities ("knock-on", "after the pipeline was shut") | no | removed for everyone, campaign or not |
| A citation whose address announces status ("…-delays-refinery-restart-to-august-30", "…-to-resume-operations-in-2027") | no | the local candidate queue, restored automatically when the campaign ends |
| A capacity note quoting a post-event operating rate | no — the capacity field is left empty | same |

The withheld marker is a **publication state**, `WITHHELD_ACTIVE_CAMPAIGN`, distinct from the
research states: it never reads as "no evidence" or "not researched". The page says, on the
record, that the facility's status is not published while the campaign is active.

## 3. The interim rule (implemented)

A record is covered when its system has a campaign recorded as `active` with `policy_applied:
true`, its cause is `kinetic_strike` or `sabotage`, and it is dated on or after the campaign's
`member_rule.from`. A record is also covered if it is named in `member_rule.also_covers`, with a
reason. This catches a record at a struck site whose own cause is not kinetic: its status is
the site's status. The first such record is the February 2026 Juaymah LPG halt. Its recovery
note traced the outage for seven months, and the site was struck in April. For a covered
record:

- `scripts/import_candidates.py` writes the withheld marker in place of the recovery block, drops
  citations whose address matches `STATUS_WORDING` or that were published more than 7 days after
  the event (after the end of the month for a month-precision date), and empties a capacity note
  that matches. A late citation is where restart and operating status live, and an opaque address
  such as `/news/1996027` cannot be read for it; the
  evidence stays in the queue. A covered record left with no publishable citation is **held**,
  not published uncited.
- `pipeline/build_systems.py` refuses to build if a covered record carries recovery content, or
  if its summary, effect, capacity note or any citation address contains current-status wording
  (`STATUS_WORDING`), or if it has no citation, and refuses the
  withheld marker on a record no active campaign covers — so recording a campaign as ended forces a
  deliberate re-import rather than leaving status hidden by accident.

**Applied now:** Saudi Arabia, "Attacks on Saudi energy facilities, 2026", active (attacks were
still reported in late October 2026; no ceasefire found). Ten records publish the event and withhold facility status: nine 2026
kinetic records, plus the Juaymah LPG halt by name; their summaries were trimmed of restart, operating-rate and
dependency wording. The citation rule was added after the iteration-16 safety review of the
served payload found status in places the summary check did not look:

- six citations' addresses, across five records, announced restarts, resumptions or recovery
  plans; they were moved back to the queue;
- one capacity note quoted SATORP's post-restart operating rate; it was emptied;
- one effect line said loadings stopped "briefly"; it was reworded through a review edit.

The tenth record, the July 2026 Jazan refinery shutdown, is **held**. Its only citation's
address announces a restart delay, and no other public source has been opened yet. It returns
when one is found, or when the campaign ends. The 2022 Yanbu record is outside the 2026 campaign and is unchanged.

**Not covered, by design:** natural-hazard, technical and unknown-cause records, including in
the same country. The February 2026 Juaymah LPG halt is recorded by its source as an accident
(cause unknown), so it is not a campaign record; its component-level wording and a dated
current-status quote were trimmed all the same.

**The Russia theatre (applied since iteration 17, in its own form).** The theatre is the
original, larger case of the same problem. Withholding all facility status, as for Saudi Arabia,
would freeze its recovery model for the war's duration, so the theatre applies a delay instead:
occurrence is published at administrative-region level as before; modelled exposure is
published; recovery evidence (a restart, a restoration, a repair estimate, a late effect report)
is used for display, scoring and the change ledger only once it is 60 days old and past any
estimate horizon. The counts withheld are published, the ids never; every campaign disruption
without released evidence carries the withheld-status note. The evidence for 60 days, the index
cost and the leakage audits are in [OPERATIONAL_STATUS_DELAY_OPTIONS.md](OPERATIONAL_STATUS_DELAY_OPTIONS.md);
`conflict_campaigns.json` records `policy_applied: true` with the rule.

A residual, stated rather than hidden: a regional exposure figure aggregates recovery evidence,
so in a region with one struck facility a falling regional value still reflects that facility's
restart. Aggregation to region is the accepted safeguard in the practices below, but it is not
perfect in single-facility regions. For the theatre the delay closes most of it: a regional
value moves only on modelled values and on evidence at least 60 days old.

## 4. Comparable practice (the evidence for §5)

Opened and read for this policy (iteration 16):

- **Ukraine's Ministry of Energy, November 2024**, asked the public not to publish strike
  consequences, restoration work or the condition of energy facilities, on the ground that the
  attacker uses this data to coordinate new attacks; **no time limit**. The ministry stopped
  publishing regional outage and restoration statistics in October 2024 and the national
  restoration aggregate in March 2025 (DiXi Group's analysis argues aggregation is what would
  make resumed publication safe).
- **Ukraine's electricity-market trading data** has been closed since December 2024 for the
  duration of **martial law plus one month**.
- **Ukrainian imagery rules** (Ministry of Culture, Ministry of Defence and Mediarukh, April 2022;
  Southern Command, November 2023) delay photos of struck sites by hours (12 for military, 3 for
  civilian) because such material helps adjust fire. These apply to imagery of the hit, not to
  facility status.
- **Israel's military censor** (March 2026 directive) allows naming a city but not a street or
  address for a civilian impact site, and bars filming near security sites; approval-based, no time
  lag. **Saudi Arabia's Interior Ministry** warns against filming or sharing impact sites.
- **US FERC Critical Energy Infrastructure Information** (18 CFR 388.113) withholds information
  useful in planning an attack, excludes information giving only a general location, and
  designates for up to five years, renewable. **EU transparency rules** (Reg. 543/2013) let grid
  operators omit a sensitive asset's identity and location from outage publication, with no time
  limit. **Russia** stopped publishing petrol output data after refinery strikes in 2024, citing
  information security.
- **ACLED** publishes weekly with a lag, but states no security rationale for it, so it is not
  relied on here. The **Berkeley Protocol** sets a duty to minimise harm but no timing rule.

Takeaways: hours-scale delays apply only to imagery of a hit. Facility restoration status is
withheld for the whole campaign by the most directly comparable actor. No practice found publishes
a struck facility's status mid-campaign merely because a number of days has passed. Aggregation
to region is the accepted safe form.

## 5. Proposed release rule (Rule A, for owner approval)

**Facility-specific restart, recovery or operating status for a record in a campaign is
published only once the campaign is recorded as ended AND 30 days have passed.** While the
campaign is active, the event itself is published and the facility's status is not.

The 30 days mirror Ukraine's "martial law plus one month" for market data. There is no
evidence-based shorter number: a time-since-event rule ("publish once the evidence is N days
old") was considered and rejected, because no comparable practice uses one and any N would be a
convenience. A hybrid (age plus no recent strike on the same facility) would need N derived from
re-strike intervals in this project's own data, which reach 16 strikes on one facility; it is
left as an alternative for the owner, not a default.

**Ending a campaign** is a curated fact with a dated, sourced basis (a ceasefire, an agreement, or
a sustained period with no reported attacks that the owner accepts), set in the register. Then a
re-import publishes the withheld evidence after the 30 days, and the build stops requiring the
marker.

## 6. Publication lag and later historical inclusion

New events in an active campaign are published as they are researched, at admin-1 precision and
with their effect at the time — the same lag as any research pass. Their facility status joins
the record later, through the release rule, as history.

## 7. Wording

Product text avoids presenting the dashboard as a real-time status board. Country pages say
"facility status not published while the attack campaign is active" on covered records, describe
recovery as "a cited public report that a facility or service came back", and never use "live"
for a country record. The theatre's ribbon item formerly labelled as live is
discussed in ITERATION_16_REVIEW (wording audit).

## 8. The iteration-16 safety review: what it found, and what is left for the owner

An independent safety review read the served payloads. It found, and the project fixed:

- **Status through records outside the cause rule.** Juaymah LPG is now covered by name.
- **Status through late or opaque citations.** Citations published more than 7 days after a
  covered event are held back. This moved three more Saudi citations into the queue.
- **Status words the check missed.** "cancelled", "expected" and "extended" were added to
  `STATUS_WORDING`.
- **A facility-dependency clause.** "Halted after an incident at the SAMREF refinery" was
  removed.
- **Theatre wording banned whether or not a campaign is active:**
  - Taman was described as the substation "through which all four Kerch energy-bridge lines
    pass", with its outages "consistent with the hub not being reconstituted". That is
    chokepoint and current-impairment framing.
  - One record said the Ust-Luga crude terminal "looked undamaged".
  - One record said Orsk's damaged equipment was "imported and under sanctions" (a supply-chain
    weakness).
  - One record named the cross-border feedstock dependency of the Orenburg plant.

  Each clause was removed from `data/curated/recovery.csv`. The recovery horizons they supported
  are unchanged.
- **Modelled status shown as observed.** The theatre's "currently impaired" counts are mostly
  modelled: 52 of 53 facilities have no restoration report and are modelled as not yet
  recovered. They are now labelled "no restoration report (modelled) · latest build". The
  "struck ×N" tag became "N recorded events".

What remains is **the owner decision on the theatre**, with the review's counts so it can be
weighed:

- `live_disruptions` lists 53 facilities with an impairment age and a modelled reconstitution
  horizon. 49 of them were struck in 2026, and 7 carry sourced status text.
- `recovery_events` holds 25 rows covering 8 distinct 2026 incidents.
- In 17 of the 26 regions with open disruptions there is exactly one facility, so the region's
  backlog figures are that facility's status.
- The build-change ledger would record a facility's recovery-status change as a dated entry.
- The pipeline registry describes current flow on the CPC line.
- Recovery-time distributions are published for classes with one or two observations.
- Struck power plants can be joined, through `linked_asset_id`, to the asset layer's WRI plant
  points. The asset layer shows every plant, struck or not, so this reveals no hidden location.
  It does make the struck subset machine-joinable.

Applying this policy to the theatre would withhold or aggregate all of these. That was the first
owner decision in ITERATION_16_REVIEW. **Iteration 17 applied it** in the delayed form above
(the brief asked for it): recovery evidence and late effect reports wait 60 days; the iteration-17
safety review removed unit inventories, criticality framing, a strike-damage count, sub-region
places with outage times and sanctions-tied repair timelines from the theatre's curated text;
and recovery-time medians are published only from three cases. The `linked_asset_id` join
remains (it reveals no hidden location) and is listed for the owner in ITERATION_17_REVIEW.
