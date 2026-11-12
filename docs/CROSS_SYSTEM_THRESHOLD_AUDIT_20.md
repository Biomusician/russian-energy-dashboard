# Cross-system threshold audit (iteration 20)

Every published record of every country system, read against the written inclusion threshold
(`data/curated/systems/inclusion_threshold.json`, version 2026-10-30.1). No clause was changed. The
audit applies one reading to all twelve systems. The Russia theatre is not subject to the
threshold and is untouched.

## The principle

**A written inclusion rule is not broadened by precedent.** If a record's publication depends on a
reading broader than the clause, and no owner ruling exists, the record is held, consistent with
the records iteration 18 already held on the same questions (Yunnan curtailment under clause 4; the
Barmer commissioning fire under clause 1; Alberta, Mumbai and Chennai). A held record stays in the
queue with its evidence; a ruling that broadens a clause restores it by re-import, with no
re-research.

Where a record qualifies on a fact its own text states, but its basis cited a weaker fact, the basis
was corrected instead of holding the record.

## How each clause is read

| Clause | Written | Read as | Not enough on its own |
|---|---|---|---|
| 1 | Refinery, gas-processing plant or LNG terminal shut down, or throughput materially cut, with the effect reported | (a) the plant reported shut; (b) a plant-level cut with a volume, a share or explicit material wording; (c) a named major unit (crude unit, liquefaction train, coker) reported shut with a reported throughput effect | "some units", "several process units", "reduced rates", "cut back", "a temporary reduction", "affected exports", "a production outage" with no volume |
| 2 | Export or import terminal operations suspended | loadings or terminal operations reported suspended | force majeure with no stated suspension |
| 3 | Trunk pipeline shut down, or force majeure declared on it | as written: force majeure on a trunk pipeline qualifies by the clause's own words | a reported flow disruption with no shutdown (owner question D-16) |
| 4 | A power plant of about 500 MW or more forced offline with a reported effect, or a generation shortfall that forced rotating outages | either limb as written; the second needs load shedding, programmed cuts or reduced supply hours that a source ties to a supply or generation shortfall | megawatts lost with no load shedding; programmed cuts after a demand peak with no stated deficit |
| 5 | A grid event affecting about 100,000 customers or more, or a grid-operator emergency declaration | a stated count of customers (also customer accounts: households (户), service connections, service addresses) of about 100,000 at one time; or a declaration (EEA 3, an ordered firm load shed under the US operational definition, a grid operator's emergency notice) | geographic extent; megawatts; "people"; substations, calls, districts; "emergency plans activated"; "working on an emergency footing" |
| 6 | A coal-mine event that materially cut supply | as written | a closure with no production effect |
| 7 | Production shut in at a reported, material volume | a stated volume, or "most" of a stated production base | an unquantified "reduction" |

Reading (c) of clause 1, the firm-load-shed reading of clause 5 and the aggregate-megawatt reading
of clause 4 come from the US sweep's written operational definitions
(`docs/countries/US_SYSTEMATIC_SWEEP.md` §A.2), which iteration 16 listed for owner review. They are
applied to every system alike, and they are rows D-27 to D-29 of `OWNER_DECISION_MATRIX_20.md`.

## Impact

Published records before the audit: 208. Held by the audit: 17. Published after it, before the
iteration's new accepts: 191.

| System | Before | Held | After |
|---|---|---|---|
| Canada | 28 | 0 | 28 |
| China | 10 | 0 | 10 |
| India | 11 | 2 | 9 |
| Iraq | 5 | 3 | 2 |
| Kuwait | 5 | 2 | 3 |
| Oman | 1 | 1 | 0 |
| Saudi Arabia | 9 | 2 | 7 |
| United States | 139 | 7 | 132 |
| Bahrain, Iran, Qatar, UAE | 0 | 0 | 0 |

### Held

Rows for the eight Gulf systems, which are under the campaign policy, give the clause and the tag
only (§49 of the iteration brief); the reasoning is in the local queue. An attack record whose id
names its facility is given by country and year only (§48).

| Record | Clause | Tag | Why |
|---|---|---|---|
| iq-2025-12-08-west-qurna-2-production-halt-leak | 7 | ROUTE | depends on owner question D-04 |
| iq-2025-08-11-national-grid-collapse | 5 | C5-EXTENT, C5-EMERGENCY | no customer count, no declaration |
| iq-2026-03-04-national-grid-total-blackout | 5 | C5-EXTENT | no customer count, no declaration |
| kw-2025-04-09-programmed-power-cuts-demand-above-generation | 4 | C4-DEMAND | no source states a supply or generation shortfall |
| kw-2026-03-20-refinery-attack-1 | 1 | C1-PARTIAL | no plant-level effect stated |
| om-2022-09-05-main-grid-partial-blackout | 5 | C5-EXTENT | thirteen opened sources give no customer count and no declaration |
| a Saudi attack record, 2022 | 1 | C1-MATERIAL | no shutdown and no material cut stated |
| a Saudi attack record, 2026 | 1 | C1-MATERIAL | no shutdown and no material cut stated |
| us-2024-09-11-hurricane-francine-louisiana-outages | 5 | C5-SUBSTITUTE | the only source counts people, not customers |
| us-2022-12-23-pjm-forced-outages-elliott | 4 | C4-MW | fleet-wide forced outages, no plant named, no load shed, no EEA 3 (fails the US definition too) |
| us-2023-08-25-marathon-garyville-tank-fire | 1 | C1-MATERIAL | tank fire, "reduced rates", no volume |
| us-2025-10-02-chevron-el-segundo-fire | 1 | C1-PARTIAL | "several process units", "diminished rates" |
| us-2025-05-07-hunt-tuscaloosa-coker-fire | 1 | C1-MATERIAL | "reduced operating rates" |
| us-2025-06-14-marathon-galveston-bay-fire | 1 | C1-PARTIAL | one unit "cut back", size not reported |
| us-2025-08-14-phillips66-linden-fcc-fire | 1 | C1-PARTIAL | "a production outage", no volume |
| in-2022-02-21-chandigarh-power-strike-blackout | 5 | C5-EXTENT | half a territory, no count |
| in-2023-06-15-biparjoy-gujarat-power-outage | 5 | C5-EXTENT | "thousands of villages and towns" |

### Basis corrected, record kept

| Record | Was | Now |
|---|---|---|
| us-2024-11-19-bomb-cyclone-washington-outages | "far more than 100,000" (650,000 people) | one utility alone had over 135,000 customers out |
| us-2026-01-24-winter-storm-fern-tennessee-outages | "more than 100,000 customers" (up to 300,000 people, estimated) | more than 250,000 outages statewide on 26 January |

### Kept on a written operational definition (owner review pending)

- **Clause 5 by an ordered firm load shed** (US OE-417 rows): us-2022-06-05, us-2022-06-10,
  us-2022-06-14, us-2024-01-25, us-2024-04-28, us-2024-09-06, us-2025-03-31, us-2025-04-02 and
  us-2025-04-26 firm-load-shed records. (us-2025-05-25 also states more than 100,000 customers.)
- **Clause 1 by a named major unit with a throughput effect**: us-2022-03-27 (Billings crude unit),
  us-2023-02-23 and us-2024-10-10 (Deer Park), us-2024-03-22 (Port Arthur crude unit),
  us-2024-01-16 (one Freeport train), cn-2025-11-13 (Quanzhou crude unit).
- **Clause 4 by aggregate megawatts with load shed**: us-2025-11-13 (which also states 250,000
  customers), ca-2026-03-08 (900 MW of load shed), in-2023-03-16 (which also states 1.3 million
  households).
- **Customer accounts under another name**: Hydro-Québec "addresses" (ca-2025-11-10,
  ca-2026-03-11), households (cn-2023-07-28, cn-2024-09-06 Guangdong), service connections
  (in-2025-10-28).

## Checked and unaffected

- **Clause 3 force majeure**: qualifies by the clause's own words for a trunk pipeline. No published
  clause-1 or clause-2 record rests on force majeure alone (sa-2026-02-23 states that loadings were
  halted).
- **Attacks with no effect**: every published attack record states an effect at the time.
- **Capacity share as the only basis**: none.
- **Supplier maintenance**: no published record rests on it; the Iraq candidates that do stay held.

## Tests

`tests/test_iteration20.py` holds the audit in place: no held record is published, every hold is on
file with its tag, and property tests over every published record forbid a clause-5 basis that
rests on extent or emergency footing alone, a clause-5 count of people, a clause-4 basis on demand
alone, and a clause-1 effect that is vague with nothing plant-level beside it.
