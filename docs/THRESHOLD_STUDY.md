# Inclusion-threshold study (iteration 17)

**Status: proposals for the owner. Nothing here is implemented.** The inclusion rule
(`data/curated/systems/inclusion_threshold.json`, version 2026-10-30.1) is unchanged by this
iteration. Every proposal below changes what is published, so each needs an owner decision and a
documented rule before it touches code (iteration-17 brief §79-80).

**Safety principle for every option.** A threshold decides which *reported disruptions* enter the
record. It must never become a measure of how much a facility *matters*: no option below ranks
facilities, sizes a dependency, or uses a facility's capacity or position as a reason to record
it. Severity is a property of the reported effect, never of the asset.

## 1. What the evidence says

Counts from the published country corpora at this commit and from the local candidate queues
(reasons classified by keyword, so the queue counts are approximate):

| Clause | US | CA | CN | IN | SA |
|---|---|---|---|---|---|
| 1 facility shutdown | 39 | 2 | 3 | 1 | 4 |
| 2 terminal/port | 3 | 1 | 0 | 2 | 2 |
| 3 trunk pipeline | 20 | 1 | 0 | 1 | 1 |
| 4 forced generation / load shed | 4 | 2 | 2 | 5 | 0 |
| 5 customers / emergency declaration | 60 | 24 | 5 | 5 | 0 |
| 6 mine supply | 6 | 0 | 2 | 0 | 0 |
| 7 regulator shut-in | 8 | 2 | 0 | 0 | 2 |

Clause-5 customer peaks in the published records: US n=45, median ~244,000, six at or below
150,000; Canada n=16, median ~392,000, four at or below 150,000. Records sit close to the floor in
both: the floor binds.

Held or rejected in the queues for reasons this study addresses: procedural grid alerts with no
reported outage (~40); event totals offered as peaks (~5); CER pipeline-incident "interruption"
flags with no stated effect (~16); sub-day facility trips (~14); counts just below 100,000 (~24);
cross-border pipeline shutdowns (2).

## 2. The questions

### 2.1 Level-3 grid alerts with no load shed (brief §26)

**Finding.** Clause 5 accepts "a grid-operator emergency declaration". The corpus publishes two
Alberta EEA-3 declarations with no firm load shed (`ca-2023-08-28-alberta-eea3`,
`ca-2024-07-08-alberta-eea3`) and one January 2024 alert. Iteration 17's operator lane found AESO
issued EEA-3 on at least nine more days in 2022-2025 with no load shed, and held all nine as
"procedural alert, no observed outage". **The corpus is therefore inconsistent**: the same kind of
declaration is published twice and held nine times. A procedural grid alert is not automatically a
disruption.

**Options.** (a) Count every EEA-3 declaration: consistent, but it records grid stress, not
disruption, and its frequency measures how cautious an operator is. (b) Count an EEA-3 only with
reported firm load shed or customer interruption: consistent with "disruption"; removes the two
published Alberta records and the January 2024 alert. (c) Keep declarations as context: list them
in the country profile as a count per year, never as events.

**Recommendation: (b) + (c).** Under (b) the two Alberta records and the January 2024 alert move
to held; the 5 April 2024 load shed (`ca-2024-04-05-aeso-load-shed`) stays.

### 2.2 Pipeline "interruption" flags (§27)

The CER incident file's interruption field states only that pipeline operations were interrupted,
with no duration, segment or flow effect, and the data dictionary does not define it. **Recommend:
not sufficient on its own.** An interruption flag plus a sourced flow, delivery or shut-in effect
meets clause 3; the flag alone stays held.

### 2.3 Cross-border pipelines (§28)

Keystone (2022) and Line 5 (2026) shut down across a border. **Recommend:** one record in the
system where the reported shutdown occurred (the rupture or the operator's shutdown point),
admin-1 there; the other system's view names it only as context. Never two records, which would
double count one event across systems that must not be compared anyway.

### 2.4 Duration floor (§29)

There is none. Sub-day LNG and refinery trips with no reported throughput effect are already
excluded by "minor unit trips with no reported effect". **Recommend:** no time floor (a duration
floor measures how quickly operators report recovery, which differs by country), but state
explicitly that a facility outage needs a *reported* throughput or supply effect, or a reported
duration of at least 24 hours, to count under clauses 1-2. That writes down the practice the
reviewers already apply.

### 2.5 Absolute versus proportional customer thresholds (§30)

The 100,000-customer floor means very different things in systems thirty times apart in size. A
proportional rule (say ≥5% of a unit's customers) needs a customer base per admin-1 unit for
every country, from a dated public source, which the project does not hold; and a share is easy
to misread as how much a unit *depends* on what failed. **Recommend:** keep the absolute floor
now; add a per-system disclosure line ("a 100,000 floor is about N% of the median unit's
customers here") once a sourced customer base exists. Do not publish per-unit shares.

### 2.6 Event totals versus peaks (§31)

Reviewers held several records whose only figure is an event total ("lost power over the
storm") rather than customers out at one time. **Recommend:** the peak-at-one-time reading stays
the rule (it is what clause 5 measures); an event total of at least 3× the floor may be accepted
as evidence that the peak exceeded the floor only if an operator figure confirms a same-day count
above it. Otherwise held.

## 3. Owner decisions this study asks for

1. EEA-3 without load shed: count, or not (§2.1). If not, three published Canada records move to held.
2. CER interruption flags: confirm "flag alone is not enough" (§2.2).
3. Cross-border pipelines: one record where the shutdown occurred (§2.3).
4. Clauses 1-2: a reported effect or ≥24 h duration (§2.4).
5. Customer floor: keep absolute; add the proportional disclosure line later (§2.5).
6. Event totals: peak-at-one-time stays the rule (§2.6).
