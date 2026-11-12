# Saudi harmonisation study (iteration 20)

## The inconsistency

Saudi Arabia was onboarded in iteration 14, before the seven systems added in iteration 19. Those
seven publish an attack or sabotage record at **country level**, with no facility, operator or
region, an opaque id, and no headline. Saudi Arabia's attack records keep the earlier convention:
the facility is named, the record sits in a first-level region, and its id names both.

Saudi Arabia's published corpus after the iteration-20 strict-reading audit was seven records; the
methodology red team then held the precautionary pipeline-shutdown record, leaving six, of which
five are attack records under the campaign policy. (The paragraph below describes the six attack
records as the audit found them; the held pipeline record, which listed two regions, was one.) Five
of the six were placed in a region, and four of those in the same one. One pipeline record listed
two regions. Two carry a per-site figure: one the
refinery's nameplate (marked `facility_size` since iteration 20) and one a stated production
reduction. At least one citation address names the attack method, the facility and its nameplate
capacity together. Each attack record's recovery status, end date and status-bearing citations are already
withheld, as for every system under the campaign policy.

Taken together, the Saudi attack records answer "which named facilities in which region were hit,
when, and with what stated effect": exactly what the newer rule exists to prevent beside an active
campaign. This is now the project's largest policy inconsistency.

## Options

| | A. Grandfather permanently | B. Harmonise aggregating surfaces only | C. Harmonise served records while the campaign restricts | D. Prospective only | E. Prospective and retrospective, permanently |
|---|---|---|---|---|---|
| What changes | nothing | home recent list, Gulf regional list, exports: no region, no facility-naming id, no effect text for campaign records | the served Saudi payload abstracts campaign-covered records to country level (opaque id, no facility, operator, region or headline); the local queue keeps the full record; detail returns under release rule A | future Saudi attack records follow the Gulf rule; existing ones unchanged | every Saudi attack record, current and future, at country level for good |
| Safety | weakest: a named, regional record of every strike beside an active campaign | better on the surfaces that set countries side by side; the country page still answers "which facility, where" | strong: the Saudi page says what the other seven say | weak until the existing records age out; meanwhile the two conventions sit on one page | strongest |
| Analytical utility | highest | high on the country page | lower during the campaign (country-level attack records); unchanged for every non-attack record | mixed | lowest, permanently: a historical attack record loses its region even after the conflict |
| Historical continuity | full | full | interrupted while the campaign restricts, restored by release | full for the past | lost |
| Compatibility with the Gulf rules | none | partial | full | partial | full |
| User comprehension | the page contradicts the other seven | the contradiction moves to the country page, stated there | one rule for eight countries | two rules on one page, explained by date | one rule |
| Data migration | none | none (implemented in code) | precision policy change and a re-import; no curated fact is lost (the queue holds it) | none now | as C, plus deleting detail from the canonical record |
| Links and history | stable | stable | the six attack-record ids change; the old ids are not redirected, because a map from a facility-naming id to an opaque one would itself re-identify the record | stable | as C |
| Tests | none | feed tests (done) | the existing precision-policy tests apply unchanged to Saudi Arabia | a date-split rule to test | as C |

## Recommendation

**Option C.** It removes the inconsistency on every served surface for as long as the campaign
restricts, loses no evidence (the queue keeps the full record and release rule A restores it), and
reuses rules and tests that already govern seven systems. Option E's permanent loss of historical
detail is not justified once a conflict has ended; options A and D leave the strongest identifying
material in place during the period that matters.

**Not implemented.** Changing what the Saudi page publishes is a methodology decision for the owner
(`OWNER_DECISION_MATRIX_20.md`, D-11 and D-33). If approved: set `precision_policy.kinetic` to
`country` in `data/curated/systems/sa/system.json`, re-import Saudi Arabia, and remove the old ids
from the episode file.

## Implemented now (option B, and the page statement)

These change no canonical fact:

- The global recent list and the Gulf regional list show a campaign-covered record as "National",
  replace an id that may name the facility with a row key, carry no effect text for any record of a
  system under the campaign policy, and name no multi-record episode that contains one.
- Under the campaign policy a country shows only the common comparison year of national context:
  no campaign-year total that could stand for one site's output.
- The Saudi country page states plainly that Saudi Arabia was onboarded before the newer Gulf
  rule, and that its older published records keep the earlier geography convention.
- A nameplate figure is marked as the facility's size, never as the amount lost.
- Current-status material stays withheld exactly as before.
