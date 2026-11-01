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

The withheld marker is a **publication state**, `WITHHELD_ACTIVE_CAMPAIGN`, distinct from the
research states: it never reads as "no evidence" or "not researched". The page says, on the
record, that the facility's status is not published while the campaign is active.

## 3. The interim rule (implemented)

A record is covered when its system has a campaign recorded as `active` with `policy_applied:
true`, its cause is `kinetic_strike` or `sabotage`, and it is dated on or after the campaign's
`member_rule.from`. For a covered record:

- `scripts/import_candidates.py` writes the withheld marker in place of the recovery block; the
  evidence stays in the queue.
- `pipeline/build_systems.py` refuses to build if a covered record carries recovery content, or
  if its summary or effect contains current-status wording (`STATUS_WORDING`), and refuses the
  withheld marker on a record no active campaign covers — so recording a campaign as ended forces a
  deliberate re-import rather than leaving status hidden by accident.

**Applied now:** Saudi Arabia, "Attacks on Saudi energy facilities, 2026", active (attacks were
still reported in late October 2026; no ceasefire found). Ten 2026 kinetic records publish the
event and withhold facility status; their summaries were trimmed of restart, operating-rate and
dependency wording. The 2022 Yanbu record is outside the 2026 campaign and is unchanged.

**Not covered, by design:** natural-hazard, technical and unknown-cause records, including in
the same country. The February 2026 Juaymah LPG halt is recorded by its source as an accident
(cause unknown), so it is not a campaign record; its component-level wording and a dated
current-status quote were trimmed all the same.

**Not applied yet — the Russia theatre.** The theatre is the original, larger case of the same
problem: its war is an active campaign, and it publishes facility-level recovery evidence (26
records; 8 for 2026 incidents with 2026 evidence dates) and a "live disruptions" list of 53
facilities with modelled impairment ages. The register records the theatre's campaign as active
with `policy_applied: false` and the reason: the theatre's recovery evidence feeds its index, and
applying the policy changes what the Russia view shows, which this iteration's brief held fixed.
Applying it is the first owner decision in ITERATION_16_REVIEW. If applied, the index would be
unaffected (it aggregates to region and sector); the facility-level presentation would change.

A residual, stated rather than hidden: a regional exposure figure aggregates recovery evidence,
so in a region with one struck facility a falling regional value still reflects that facility's
restart. Aggregation to region is the accepted safeguard in the practices below, but it is not
perfect in single-facility regions.

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
