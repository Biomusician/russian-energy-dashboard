# Owner decisions (iteration 22)

Four questions from `ITERATION_22_REVIEW.md` §34 that only the owner can settle, written so each
can be ruled on from this page. **Nothing here is implemented.** Until a row is ruled, the "current
rule" line is what the code does. The iteration-20 matrix (`OWNER_DECISION_MATRIX_20.md`) still
stands; where a question here touches one of its open rows, the row is named.

Counts of held or refused candidates are given across all systems, never per system under the
campaign policy (the convention of the iteration-20 matrix). No held record is named.

---

## D-I22-1 A record held from a country system, against the impact layer's own threshold

**Question.** The import refuses an impact candidate that matches, by date and class, a record a
country system holds or rejected, whatever the reason, a threshold included; there is no override
(CLAUDE.md, methodology §1 and §12, tested). Should a record held only because it misses the
country system's quantitative threshold be allowed into the impact layer, whose inclusion contract
is different (§3: no universal numeric threshold)?

**Current rule: no override. It stays no override until the owner rules.**

**Number affected.** 39 matches were refused at import, covering 23 distinct candidates in six
country systems (five under the campaign policy, and the United States). The import's own
classifier (`scripts/import_impacts.py::hold_kind`, which reads the country queue record's written
reasons and fails closed) labels the 39 matches: threshold 16, unclear 13, safety 4, campaign 3,
evidence 3. Per candidate, taking every match into account: 7 are held on threshold grounds alone;
3 on threshold plus an unclear match; 5 on unclear matches alone; 8 carry at least one safety,
campaign or evidence hold. Almost all are electricity shortfalls and blackouts (for example, Iraqi
national blackouts held for a missing customer count). **Each of the 7 threshold-only candidates is
held under a clause an open row of the iteration-20 matrix asks about** (D-01 seasons of load
shedding, D-08 emergency footing, D-09 supplier maintenance, D-17 megawatts or demand-peak cuts,
D-18 official extent with no customer count, D-20 maintenance seasons).

**Option A: no override (current).** *Product:* unchanged; the 23 candidates stay refused, and the
impact layer never shows an event its country system holds. *Safety:* strongest; one rule, no
judgement at the boundary. *Consistency:* complete in one direction (the two layers never disagree
about an event), at the cost of the impact layer applying the country systems' thresholds to records
its own contract would admit, so the impact corpus under-represents exactly the national blackouts
and shortfalls a reader looks for in the Gulf. *Implementation:* none.

**Option B: threshold-only override, narrowly defined.** An impact candidate may be imported despite
a matching country hold only when **all** hold: it is non-kinetic and not sabotage; it is
country-level (no region); it independently meets an impact inclusion basis and passed the three
blind impact reviews; the safety reviewer cleared it under the impact layer's own rules (including
the campaign policy's dating rule for these systems); and **every** matching country hold is
classified `threshold`, the record being held solely on a different quantitative threshold.
Absolute no-override stays for safety holds, campaign holds, evidence failures, and taxonomy or
identity ambiguity (`unclear` fails closed). *Product:* at most 7 records today, all national
electricity or supply events; the Atlas and the country's impacts tab would then show an event the
country's own event list does not, and the country page has to say why in one line (two contracts,
two thresholds) without describing the hold. *Safety:* low risk for these records (non-kinetic,
national); the risk is the precedent, a crack in "never widens publication" that a later reading
could widen, which is why the override must be per record and reasoned. *Consistency:* every one of
the 7 is held on a clause the owner has not yet ruled on (above). Ruling B first would publish
through the impact layer what the country system holds pending those rows; ruling the D-rows first
restores the records in both places by re-import, with no override needed. *Implementation:* a lead
file `reconcile_override.json` (one entry per record, naming the threshold clause it misses and the
impact basis it meets; the import refuses an entry whose matches are not all `threshold`, or whose
record is kinetic, sabotage or regional); CLAUDE.md, methodology §1 and §12 amended; the existing
no-override tests rewritten to the narrower rule, plus a mutant for each condition.

**Option C: full independent impact-review override.** Any candidate the three impact reviewers
accept may be imported whatever the country hold, except safety and campaign holds. *Product:* up to
the 15 candidates without a safety, campaign or evidence hold, including those whose country hold
the classifier cannot read. *Safety:* weaker; `unclear` includes duplicates and rejections whose
reason is not stated as a threshold, so admitting them means publishing on a reading nobody wrote
down. *Consistency:* the two layers would routinely disagree, and a held country record would have a
second door. *Implementation:* the reconciliation becomes advisory; most of the import's
reconciliation tests go.

**Recommendation.** Rule the iteration-20 rows the seven records hang on (D-01, D-08, D-09, D-17,
D-18, D-20) first; that is the consistent path and may restore some of these records in both
layers. If the owner then still wants the impact layer to admit what a country threshold excludes,
adopt **B as defined above, and only B**: non-kinetic, country-level, independently
impact-qualified, safety-cleared, held solely on a quantitative threshold, one reasoned entry per
record. Keep absolute no-override for safety holds, campaign holds, evidence failure and taxonomy or
identity ambiguity. Reject C. Until the owner rules, the rule is no override.

---

## D-I22-2 Banking and payments, tax and customs platforms, heavy industry

**Question.** These fall outside the impact sector list (methodology §5). Add sectors, or keep
rejecting? **Number affected:** about five reviewed candidates were rejected on this ground this
iteration (three banking or card-service outages, one national tax-and-customs platform, one heavy
industry), all cyber.

**Current rule:** rejected. A payment outage that stops an included service is already recorded
under that service (methodology §3, basis 4: "payments at fuel stations nationwide" is a fuel-supply
record), and so is transit ticketing (transport).

**Option A: keep rejecting (current).** *Product:* unchanged. The layer stays "energy and essential
civilian services"; a reader who looks for a national banking outage does not find it, and the
coverage note says why. **Option B: add one civilian sector, payments**, limited to a national or
regional card or payment network outage that stopped everyday purchasing. *Product:* a new sector
and filter; the rejected banking candidates re-reviewed from the queue; a definition test so that a
single bank's app outage does not qualify. **Option C: add payments, government digital services
and heavy industry.** *Product:* three sectors; heavy industry would be an output measure, the
first sector whose effect is economic rather than a service to people, and naming a steelworks or
smelter by an attack moves toward the industrial target sets the scope boundary forbids; government
platforms widen the layer toward "cyber incidents generally".

**Recommendation.** **A**, with the existing rule made explicit in the methodology: a payment or
platform outage counts only through the essential service it stopped (fuel, transport, healthcare,
water). Heavy industry stays out on scope grounds, not only taxonomy. If the owner wants payments,
B is the most it should be, and only for networks whose outage stopped everyday purchasing
nationally or regionally.

---

## D-I22-3 Baltic subsea cables and pipelines

**Question.** Damage to subsea telecom cables and gas pipelines in the Baltic was deliberately not
researched this iteration. Research it at country level under the abstraction rule, or leave it out?

**Current rule:** not researched; the research coverage says "not yet researched" for it, which is
different from "nothing happened".

**Option A: leave out, and say so.** *Product:* unchanged; the coverage statement names the gap
and the reason. **Option B: research at country level under the abstraction rule.** Every
sabotage-suspected or kinetic record is `country_abstracted`: country (or `MULTI` with the
countries), no cable or pipeline name, no place, operator, method, vessel, headline or later status,
a keyed opaque id; a cause still under investigation is `unknown`, and attribution reports only who
attributes. Only incidents with a documented service effect qualify under §3: damage that
redundancy absorbed is not a disruption. *Product:* probably few records, each saying little more
than "a telecom (or gas supply) disruption in country X, cause unknown or attributed by Y". The
research itself runs through reporting centred on named infrastructure and vessels, so the queue
would collect material the served record may never carry. **Option C: research with named
systems.** Naming a cable or pipeline names a facility and a route; it conflicts with the
abstraction rule and the route ban and is not a real option without changing both.

**Recommendation.** **A** for this release. The inclusion contract would admit few incidents, the
abstraction would leave each nearly empty, and the research exposure is high for little served
information. If the owner wants coverage, B exactly as written, as its own research lane with a
safety reviewer briefed on vessel and route wording, never C.

---

## D-I22-4 The bar for dropping `-draft` from Evidence Confidence

**Question.** Accept a second calibration run on reviewed records with human labelers as the bar for
moving Evidence Confidence from `2.0-draft` to `2.0`?

**Current rule:** `2.0-draft`, served as "provisional: thresholds not calibrated". Run 1 failed. A
test ties the version to the recorded result. Dropping `-draft` changes the served status line and
what documents may say; it does **not** touch the theatre's multiplier, which has its own eight
conditions (`EVIDENCE_CONFIDENCE_V2.md` §8).

**Option A: the run-2 bar as planned** (`ECI_CALIBRATION_RUN2_PLAN.md` §3): reviewed records only;
at least three human labelers, one outside the build; every reviewer pair at kappa 0.6 or more;
model agreement no worse than reviewer agreement on exact and kappa; no systematic shift by a sign
test; every reviewers-against-model packet explained by a named rule; agents as pilots only.
*Product:* if passed, the status line changes and the method may be described as checked against
blind human labels; if failed, nothing changes. **Option B: a lower bar** that counts agent labelers
when several diverse agents agree. *Product:* the draft could drop without any person. Run 1 shows
why not: two agents agreed with each other at kappa 0.73 and that said nothing about whether a
person would. **Option C: a higher bar**: A plus a second outside human, a typing audit in which
reviewers open the sources, and a replication run. *Product:* the strongest claim, at a cost in
people and time that may mean the draft never drops. **Option D: never claim calibration.** Keep the
method as a declared ordinal description with no calibration claim. *Product:* honest, permanent
"provisional"; no further runs.

**Recommendation.** **A**, with the owner confirming the sign test and the "every pair" reading of the
kappa floor before packets go out, and the measurement-organisation question tested in the same run
(`ECI_SOURCE_ROLE_MEMO_22.md`). If no outside human labeler can be found, the run stops at the
prepared packet and the draft stays, which in practice is D until one is found. Reject B.
