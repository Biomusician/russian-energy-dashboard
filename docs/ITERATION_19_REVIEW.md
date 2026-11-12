# Iteration 19 review — Gulf energy expansion


The brief for this run was titled "Iteration 18 — Gulf energy expansion". The repository had
already used iteration 18 for the rest-of-world pass (`ITERATION_18_REVIEW.md`), and the repo wins
over the prompt, so this is iteration 19. Every "iteration 18" file name in the brief maps to 19.

## 0. Checkpoint (2026-11-11, before any Gulf research)

### 0.1 Baseline

| | |
|---|---|
| Local HEAD | `8e51bb7`: iteration 18 complete, **never pushed** (the release push was not run) |
| origin/main | `f74a12b`: daily refresh 2026-11-11 |
| Production | iteration-17 code with the 2026-11-11 refresh: Russia ESDI 6.8, 184 theatre events, six systems, five-country corpus 195 records and 161 episodes. Global energy context returns 404 there because iteration 18 is not deployed |
| Local five-country corpus (iteration 18) | 197 records and 165 episodes: US 139, CA 28, CN 10, IN 11, SA 9 |
| Saudi | 9 records, 8 with recovery status withheld under the active 2026 campaign |
| Tests at local HEAD | Python 613 passed, 2 skipped; vitest 254; Playwright 131 passed, 1 skipped; mutations 56 of 56 caught |

Iteration 18 ships with this iteration's release, behind the same gates.

### 0.2 Scope, codes and groups

Seven new country systems, ids `ae bh iq ir kw om qa`, Natural Earth `ARE BHR IRQ IRN KWT OMN QAT`.
Saudi Arabia (`sa`) is unchanged in id and deepened, not rebuilt.

Group metadata on every system, kept apart because they are different things:

- `regional_groups`: `["gulf_littoral"]` for the eight.
- `gcc_member`: true for `sa kw bh qa ae om`, false for `ir iq`, null outside the Gulf.
- `opec_member`: true for `ir iq kw sa ae`, false for `bh qa om` (Qatar left OPEC in 2019). Membership is checked against OPEC's own member list during the source audit.
  *Corrected during the run: the UAE left OPEC on 2026-05-01 and is published as a non-member; OPEC's own page could not be read (§2).*

Groups are navigation and context only, never a score input.

### 0.3 Campaign determination, before any event ingestion

One agent reviews public evidence for each of the eight systems and classifies it as
`ACTIVE_KINETIC_CAMPAIGN`, `RECENT_ENDED_CAMPAIGN`, `NO_ACTIVE_CAMPAIGN` or `UNCERTAIN`, with a
dated basis, never from a single incident. `UNCERTAIN` takes the conservative posture. A system
in an active or uncertain campaign gets a `conflict_campaigns.json` entry with `policy_applied:
true` before any of its events are imported. Iran is expected to need this: Saudi records already
cite a 2026 Iran war.

### 0.4 Regional common sources (to be assessed, then adopted or rejected)

| Source | Likely use | Known risk |
|---|---|---|
| EIA International Energy Statistics | already adopted (iteration 18); crude, gas, electricity, consumption for all eight | no LNG, no refining capacity |
| OPEC Annual Statistical Bulletin 2026 | refining capacity, exports, LNG for members | redistribution terms; OPEC's site refused automated access in iteration 18 (HTTP 402) |
| JODI Oil and Gas | monthly validation, never incident attribution | terms; coverage gaps |
| Energy Institute Statistical Review | LNG trade, refining capacity | terms unreadable in iteration 18 (403): do not commit |
| GECF, IRENA | gas and renewables context | licence per dataset |
| GCC-Stat, GCCIA | GCC electricity and exchanges, high level only | access; no line-level data may be taken |

Rule: one source per comparison column, labelled with year and definition. A metric with no
redistributable common source is omitted, never filled from a second source.

### 0.5 Geography and microstate precision

Natural Earth admin-1 is behind current divisions in three places: Bahrain shows 5 governorates
(4 since 2014), Qatar 7 municipalities (8 since 2014), Iraq 18 governorates (Halabja recognised
in 2025). Each gets a ruling in `geography.rulings`. Events are never placed in a unit Natural
Earth cannot draw. The UAE file carries two "Neutral Zone" units, which are not used as
analytical units.

Precision rule, enforced in the build and tested:

- Admin-1 is a maximum. `system.json` → `geography.max_precision` sets, per cause class, the finest level allowed.
- Kinetic and sabotage events are country-level by default in Bahrain, Qatar, Kuwait and the UAE. In Iran during an active campaign they are country-level too.
- Industrial and natural-hazard events may use admin-1 where the safety reviewer finds it non-identifying.
- Iraq uses governorates, with Kurdistan Region treated as part of Iraq. Musandam is an ordinary governorate.
- Disputed islands are never analytical units.

### 0.6 Language and agent assignments (Fable)

Wave A, before plans: one campaign-status agent (all eight), one regional-sources agent, and
seven source-audit agents (IR in Persian and English; IQ in Arabic and English, with Kurdish where
material; KW, BH, QA, AE, OM in Arabic and English).

Wave B, after plans are committed: Iran ×3 (official Persian oil and gas, electricity, media and
international corroboration with campaign-occurrence events), Iraq ×3 (SOMO and Ministry of Oil,
electricity, KRG and media), UAE ×2, Qatar ×2, Kuwait ×2, Oman ×2, Bahrain ×1, Saudi ×1.

Then blind three-role review (fresh agents), country red teams, and Iran, Saudi, Iraq and regional
safety red teams.

### 0.7 Source-audit lanes

Each country gets `<CC>_SOURCE_AUDIT.md`, `<CC>_INDEX_READINESS.md` and `<CC>_SYSTEMATIC_SWEEP.md`.
The sweep's Part A plan is committed before Wave B runs. Lanes follow the brief: IR1-IR6,
IQ1-IQ5, KW1-KW4, BH1-BH3, QA1-QA3, AE1-AE4, OM1-OM4, and Saudi's unfinished SA1-SA5.

### 0.8 Regional context schema

`data/curated/global_context/gulf_energy_context.json` → `global/gulf_energy_context.json`:
`{source[], comparison_year, metrics{id: {label, unit, definition, source_id}}, countries[{system_id,
a3, values, newer}], region{values, world_share}}`. Built only from sources whose terms allow
redistribution, and it carries no facility field. EIA rows already exist in
`energy_context.json`; the Gulf file adds only metrics that EIA lacks (refining capacity, LNG),
and only if a licensed common source exists. Otherwise those metrics are omitted, not estimated.

### 0.9 Country artifact architecture

Unchanged pattern: `systems/<id>/{system,events,regions}` built by `build_systems.py` from
`data/curated/systems/<id>/`. The registry gains `regional_groups`, `gcc_member`, `opec_member`
and `aliases` (native names). The manifest carries groups and aliases, so the frontend has no
country list. The Gulf overview is a view over the manifest, `energy_context.json` and the Gulf
context file. Country payloads lazy-load as now.

### 0.10 Expected bottlenecks

- **The web-search allowance: 200 per turn, shared by every agent.** Iteration 18 ran out of it. Budget: about 55 for Wave A, 125 for Wave B, 20 in reserve. Agents must enumerate directly first, write progress after each source family, and stop cleanly at their cap.
- Iranian official sites refusing access, or reachable only by script.
- SOMO and ministry archives that are PDF scans.
- Arabic and Persian dates in Hijri and Solar Hijri calendars.

### 0.11 Licensing risks

OPEC, Energy Institute, JODI and GCC-Stat redistribution terms. Unknown terms mean no committed
values. News articles: metadata, short own-words summary and URL only.

### 0.12 Safety risks

- Current facility status during the 2026 conflict: Iran and possibly Gulf neighbours.
- Microstate admin-1 that effectively names a facility.
- Export and pipeline context drifting into route or chokepoint analysis.
- Aggregates that identify one struck facility.
- Source titles and URLs that carry status or distance.

None of these features is built: Hormuz analysis, tanker or AIS tracking, route or bypass
capacity, importance scores, facility point layers, or nuclear-site material.

### 0.13 Sequence

1. Merge the 2026-11-11 refresh and regenerate.
2. Run Wave A in parallel with the scaffold: registry, groups, geography policy, calendar and numeral normalisation, an empty corpus per system.
3. Write and commit the plans.
4. Run Wave B.
5. Candidates go through blind review and confirmation, then import.
6. Build the Gulf context, Gulf overview, search aliases and filters.
7. Tests, mutations to 85 or more, and red teams.
8. Docs, fetch and integrate, gate, push, verify production, final report.

---

# End of run (2026-11-11)

Sections 1 to 28 follow the brief's list. Section 0 above is the checkpoint as written before any research, kept unchanged apart from one dated correction.

## 1. Baseline

As in §0.1. The run started from local `8e51bb7` (iteration 18, never pushed) and `origin/main`
`f74a12b` (the 2026-11-11 refresh), merged in `6503acc` and rebuilt in `da64985`. Iteration 18
therefore ships with this iteration, behind the same gates.

## 2. Gulf scope

Eight systems make the Gulf littoral group: Bahrain, Iran, Iraq, Kuwait, Oman, Qatar, Saudi Arabia,
United Arab Emirates. Seven are new. No other country was added. The group is geography. GCC and
OPEC are separate membership fields and are never used as shorthand for the eight.

**Deviation from the brief, stated.** The brief listed the UAE as an OPEC member. Its government
announced on 2026-04-28 that it would leave on 2026-05-01. OPEC's own member page returned HTTP 402
and was not read, so the published list rests on that announcement as reported, and says so.

## 3. Architecture

See [GULF_ARCHITECTURE.md](GULF_ARCHITECTURE.md) and the iteration-19 section of
[GLOBAL_ARCHITECTURE.md](GLOBAL_ARCHITECTURE.md). In one paragraph: the registry gained seven
systems and three groups; one regional context file is built from the national context already in
the product; every Gulf system is classified for campaign state before any event is ingested; each
states a precision policy; and the import gate and the build both enforce the text rules listed in
[GLOBAL_METHODOLOGY.md](GLOBAL_METHODOLOGY.md) under "Gulf rules". The frontend reads groups and
systems from the manifest and holds no country list. The daily refresh builds from curated files
and does no research.

Three things changed after the plan was committed, each because the research or the review showed
the plan was not strict enough:

1. **Iraq's attack records moved from governorate to country level** before review. The Kurdistan
   Region lane showed that a governorate and a class name the site for most of them.
2. **The gate gained rules from the blind safety review**: a citation address that names any
   first-level unit, the operator, or how an attack was carried out is not published on a record
   without its place; such a record carries no headline; review edits commit no reviewer prose for
   it.
3. **Lane notes publish process facts only.** Read together before release, the researchers' notes
   were a list of strikes by date and class, with tallies, that no reviewer had accepted. Every
   sentence about an attack, a tally, a dated event of 2026 or held material is now removed before
   a note is written to a research log, and a test fails if one returns.

Five release reviews then read the candidate (§24). Each of the following became a rule with a
test; [GULF_ARCHITECTURE.md](GULF_ARCHITECTURE.md), "Changes after the release reviews", lists
them.

4. **Campaign bases say only that attacks are reported.** The first versions gave a region, a
   class and a date three days old for a system whose attack records are the country's.
5. **No researcher prose is published for a Gulf lane.** Rule 3 above used word lists, and
   paraphrase went through twice. A lane now publishes counts and sentences from a closed list.
6. **The public review-edits file keeps only the result** for a system under the campaign policy.
   Reasons and replaced text restated what the edits removed.
7. **A short link is not a citation** for a record published without its place, and an
   iteration-19 record is imported only with three confirmations of its final text.
8. **A unit where no record can be placed serves no count**, and the regional list places a
   campaign-covered record at country level under a row key.

## 4. Regional context data

[GULF_ENERGY_CONTEXT.md](GULF_ENERGY_CONTEXT.md). Four national annual totals for each of the
eight, all from the U.S. EIA International Energy Statistics bulk file and one year: total primary
energy production, crude oil production, dry natural gas production, net electricity generation.
The regional sum and its share of the world total are shown only when all eight report.

**Looked for and not adopted:** refining capacity, LNG exports and current crude exports on a
common basis. The one source whose terms were read and allow reuse has no LNG or refining-capacity
series, and its crude-export series ends in 2018. OPEC, the Energy Institute and IRENA refused
automated access, so their terms are unread; JODI, GECF, GCCIA and OAPEC were reached and none
grants redistribution. A metric with no committable common source is left out, not estimated.

**Not built, by design:** any route, strait, shipping or tanker information, any facility layer,
and any measure of dependence or importance.

## 5. Iran

Campaign state `ACTIVE_KINETIC_CAMPAIGN`. Attacks and sabotage are recorded for the country; other
events by province. Six lanes, Persian and English, all partial; most official Persian archives
were unreachable or script-only, and every Iranian official statement read was a relayed copy.

**No record is published.** Thirty-five candidates; two reached blind review. One is with the
owner (clause 3: no opened source says the line was shut). One is held because the evidence
reviewer's footing and the safety reviewer's removal could not both be honoured. The country page
says "No qualifying records in the current reviewed corpus", states that this describes the
dataset and not Iran, and gives the number of candidates held.

Nothing nuclear appears in any record, citation or profile row. Iran's 31 provinces are on current
ISO codes; the map source gave Alborz Tehran's code and used pre-2020 numbering, and both were
corrected by name.

## 6. Iraq

Campaign state `ACTIVE_KINETIC_CAMPAIGN` from 2022. Five lanes in Arabic, English and Kurdish, all
partial. Sixty-nine candidates, five published: two national-grid collapses, one fuel-supply
shortfall for which the ministry reported reduced supply hours, one production halt at a stated
volume, and one attack record at country level.

Ten were accepted by the three roles. After the release reviews the lead held four of them: three
fuel-supply shortfalls with a stated megawatt loss and no reported load shedding, which
`REVIEW_GOVERNANCE.md` §7.3 holds for the owner and on which iteration 17 had un-published three
records elsewhere; and one production cut whose sources give three different figures. Three more
were narrowed and sent to three fresh roles: two were confirmed, and one is held on a taxonomy
objection to its cause (a blockade by people who were not the workforce is not labour action, and
the vocabulary has no value for it).

Also held or with the owner, as before: attack records whose every citation names the place in its
address, a set the safety reviewer judged to read as a tally, non-attack records at or about a
site that has attack records, a blackout whose reported cause may include sabotage, two shortfalls
whose stated reason is a supplier's maintenance, and one attack record with no stated volume.

Three disputed-area rulings proposed by the audit were not verified and were dropped; the Kirkuk
ruling was kept. The map file's former name for Kirkuk is no longer shown.

## 7. Kuwait

Campaign state `UNCERTAIN`, treated as active. Four lanes; the ministry's Arabic and English
listings were read by title for the window. Forty-eight candidates, five published: four
dated episodes of programmed power cuts announced by the ministry, and one attack record at
country level. With the owner: a programmed cut that coincided with periodic maintenance, and two
attack records whose only qualifying statement is that emergency plans were activated.

## 8. Bahrain

Campaign state `UNCERTAIN`. Every record is the country's: the map source still draws five
governorates where there are four, and the country is small enough that a governorate would name a
facility. Three lanes. **No record is published.** One attack record reached review and is with
the owner: the sources report a force-majeure declaration and disrupted operations, and clause 1
asks for a shutdown or a throughput cut. The electricity authority's terms forbid linking, so it
was never cited.

## 9. Qatar

Campaign state `UNCERTAIN`. Three lanes. Twelve candidates. **No record is published.** One attack
record passed three roles and their confirmation. The release safety review then pointed out that
the country has one facility of that class, so the class and the country name it whatever the
text withholds. That is an owner question (§27), and the brief holds a record that waits on one,
so the lead held it. A second attack record was already with the owner. The utility's terms forbid
linking, so it was never cited.

## 10. United Arab Emirates

Campaign state `UNCERTAIN`. Four lanes. Twenty-one candidates. **No record is published.** One
attack record passed three roles and their confirmation; its only citation is a publisher's short
link, and the release safety review reported that the address it redirects to names the place.
The gate had read only the stored string. The lead held the record and the gate now refuses such
a link. Four other attack records and a 2023 gas-plant fault were already held. The two areas the
map source labels as a neutral zone are drawn and never used for a record.

## 11. Oman

Campaign state `UNCERTAIN`. Five lanes. Fourteen candidates, one published: a 2022 grid event,
accepted under clause 5 on stated extent with no customer count, on the precedent of existing
records. The Oman audit had said a report with no figure cannot meet clause 5; that sentence now
carries a dated correction note, and the question is listed for the owner. Musandam is drawn as
its own governorate with no narrative attached.

## 12. Saudi regression and deepening

The nine published Saudi records are unchanged: the import was re-run and produced the same file.
Five lanes ran again on a plan of their own. The sections of the Arabic annual reports for four fiscal years that carry incident wording, and all
24 monthly statistical releases for 2024 and 2025, were read by keyword; none attributes a change to a
disruption. No new record: thirty candidates, fourteen already known, six held, nine rejected, one
out of scope. SPA, the ministry site, Tadawul and OPEC refused access again.

Saudi records predate the Gulf rules and place attacks by region with the facility named. That is
stated on its Gulf card. Bringing them under the country-level rule would change published records
and is an owner decision (§28).

## 13. Multilingual research

Persian and English for Iran; Arabic and English for the Arab states; Kurdish (Sorani) for the
Kurdistan Region lane. A lane that ran in fewer languages than its plan requires is `partial`, and
[GULF_RESEARCH_COVERAGE.md](GULF_RESEARCH_COVERAGE.md) lists which. Non-English pages were read in
their own language; a translation or a syndicated copy is not counted as a second source.

Citations keep `language`, and on non-attack records a non-English citation may keep its own
headline with a gloss, rendered with its script direction. A headline that states later status,
weighs a facility or names one the record does not is not shown. No published record needed a
calendar conversion: `pipeline/calendars.py` converts Solar Hijri exactly and Hijri to within a
day, and is tested, but every date published this pass was written in the Gregorian calendar by
its source.

## 14. Event corpus

The final data audit, generated from the served payloads. Alphabetical; no row is a rank.

| System | Research window | Languages run / required | Lanes | Execution state | Candidates | Published | Held | Episodes | Records with recovery evidence | Campaign state | Index |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---|---|
| Bahrain | 2022-01-01 to 2026-11-11 | ar, en / ar, en | 3 | 3 partial | 9 | 0 | 3 | 0 | 0 | UNCERTAIN | none |
| Iran | 2022-01-01 to 2026-11-11 | en, fa / en, fa | 6 | 6 partial | 35 | 0 | 23 | 0 | 0 | ACTIVE_KINETIC_CAMPAIGN | none |
| Iraq | 2022-01-01 to 2026-11-11 | ar, en, ku / ar, en, ku | 5 | 5 partial | 69 | 5 | 43 | 5 | 1 | ACTIVE_KINETIC_CAMPAIGN | none |
| Kuwait | 2022-01-01 to 2026-11-11 | ar, en / ar, en | 4 | 4 partial | 48 | 5 | 18 | 5 | 0 | UNCERTAIN | none |
| Oman | 2022-01-01 to 2026-11-11 | ar, en / ar, en | 5 | 5 partial | 14 | 1 | 7 | 1 | 1 | UNCERTAIN | none |
| Qatar | 2022-01-01 to 2026-11-11 | ar, en / ar, en | 3 | 3 partial | 12 | 0 | 7 | 0 | 0 | UNCERTAIN | none |
| Saudi Arabia | 2022-01-01 to 2026-11-11 | ar, en / ar, en | 5 | 2 not started, 3 partial | 30 | 9 (0 new) | 6 | 9 | 0 | ACTIVE_KINETIC_CAMPAIGN | none |
| United Arab Emirates | 2022-01-01 to 2026-11-11 | ar, en / ar, en | 4 | 4 partial | 21 | 0 | 15 | 0 | 0 | UNCERTAIN | none |

"Held" counts every candidate not published and not rejected, duplicate or out of scope: records
held by a reviewer, by the lead, by the import gate, or waiting on an owner decision. "Index: none"
means `index` and `headline` are `null` with a reason. It is not zero.

Eleven records are published in three of the seven new systems, each its own episode: nine are
not attack records and two are. Four new systems have none. The path: 34 candidates reached blind
three-role review; 23 were accepted by all three; reconciliation and lead rulings held five; 18
were confirmed on the text the gate publishes. The release reviews then led the lead to hold six
of those 18, and a seventh was held when one role objected at re-confirmation. The country
systems together now hold 208 records in 176 episodes across twelve countries.

Uneven results are expected and say nothing about how often disruption happens. Four countries
have no published record while attacks on energy facilities there are widely reported: that is a
statement about what passed review under the safety rules in one pass, and each page says so.

## 15. Recovery

Observed only, as in every country system. Two new records carry a cited report: a partial
restoration for one Iraqi grid collapse and a stated full restoration for the Omani grid event.
Two new attack records have their recovery block withheld under the campaign rule. Recovery,
restart, repair and operating status were deliberately not researched for any attack record in
any of the eight systems.

One relayed report of restoration was removed from a non-attack record's effect text: the cited
page relays it and the record's recovery block says recovery was not researched.

## 16. Source coverage

[GULF_RESEARCH_COVERAGE.md](GULF_RESEARCH_COVERAGE.md) and Part B of each
`countries/<CC>_SYSTEMATIC_SWEEP.md`. Of 35 lanes across the eight systems none ran as far as
declared: 33 are partial and two (Saudi) were not started. A shared limit of 200 web searches per
turn bounded the pass and was not worked around; about 165 were used, four of them by evidence
reviewers.

What limits the record most, in order: official archives that are script-only, refuse automated
access or exceed the size the fetch tool reads; a search tool that gives little weight to year
terms, so 2022 to 2024 were reached mainly through publishers' own listings; and the safety rules,
which hold an attack record whenever every page that supports it names the place in its address,
and the owner questions in §27, which hold more candidates than any of these.

Gulf citations were not link-checked in this pass.

## 17. Campaign policy

Every Gulf system was classified before any event was ingested: Iran, Iraq and Saudi Arabia
`ACTIVE_KINETIC_CAMPAIGN`; the other five `UNCERTAIN`, which is treated as active. Each has a
campaign entry with `policy_applied: true`; the build refuses a restricted system without one, and
refuses to lift the policy until a campaign has been recorded as ended for 30 days. The sentence
that states a classification says that attacks are reported and whether an end is, and nothing
else; the build checks it.

For an attack or sabotage record the product publishes that it happened, its date, the broad class
of infrastructure, the country, and the effect reported at the time. It does not publish, and did
not collect: restart, current outage status, operating rate, repair schedule, continuing
impairment or remaining capacity.

**What was withheld or aggregated, and why.** Without naming any site:

- Region, facility and operator on every attack and sabotage record in the seven new systems,
  because in each of them a first-level unit and a class together can name one facility.
- Every headline on those records, and every citation whose address names the place, the operator
  or the method, or is a short link whose destination was never read. Where no citation was left,
  or the page stating the qualifying effect could not be cited, the record is held.
- An attack record in a country that has one facility of its class (owner).
- A set of attack records in one system whose reported effect is a downstream megawatt loss, which
  the safety reviewer judged to identify one site by its weight on the grid (owner).
- Non-attack records at or about a site that has attack records (owner).
- A capacity share, a per-plant figure, megawatts-against-load pairs, a sub-national placement of
  the cause of a national blackout, and a relayed restoration report, removed from text as
  importance, remaining-capacity, reserve-margin, dependency or status statements.
- From the pages around the records: the region, class, tally and dates in campaign bases; all of
  the researchers' own notes; reviewers' wording in the public edits file; descriptions of held
  records in the sweep documents; paths and table codes in the audits that said where withheld
  material is published; a single operator's capacity statement and a rank in two profiles.
- Shipping, strait and route material, and national production cuts attributed to export-route
  closure, which are outside the product.
- In the regional list: any place below the country for a campaign-covered record, and each
  country's own record ids.

**Residual risk, stated.**

- A published citation leads to a public news page, and for an attack record that page names the
  place. The release safety review opened the four pages then cited and found it so on each.
  Abstraction lowers what this product states and aggregates; it does not change the report.
- Saudi Arabia's attack records predate these rules. They name region and facility, and several
  carry a per-site figure. Nothing in them changed in this iteration; harmonising them changes
  published records and is an owner decision (§27). The Gulf overview no longer repeats their
  region or their ids, but the Saudi page and the home page's recent list do.
- The public repository's history keeps earlier versions of the review-edits file. History is not
  rewritten. What was pushed before this iteration stays readable there.

## 18. Geography

Admin-1 is a maximum. Natural Earth's line of actual control is drawn and rulings are stated as
sovereignty-neutral analytic choices. Stated to the reader where the map source differs from
today: Bahrain (five governorates drawn, four exist), Qatar (pre-2014 shapes), the UAE's two
neutral-zone areas (drawn, never used), Iran (codes corrected by name). The body of water is
called "the Gulf" throughout.

## 19. Licensing

Facts only, cited by link; no article text is stored. One regional source is adopted (EIA, public
domain). OPEC, the Energy Institute and IRENA were blocked and their terms are unread. JODI, GECF,
GCCIA and OAPEC are used for nothing published. Two utilities forbid linking in their terms and
are never cited. Natural Earth is public domain.

## 20. UX

A Gulf overview at `?group=gulf`: what the view is and is not, the three kinds of group as a list,
a map coloured by a national figure with a legend that says a larger figure is not a more
important country, an alphabetical table with a keyboard route, the regional sum, a card per
system, and reviewed events in date order. Each card states GCC and OPEC membership, research
preview, whether recovery status is withheld, the reporting environment, the latest research pass
and how the system places attack records.

The home page gained a group filter and a link to the overview; the system picker lists regional
overviews. A country with no published record says "No qualifying records in the current reviewed
corpus" and how many candidates are held; it never shows a zero. Search finds systems by local
names.

**First-time reader test.** An independent session was given only the visible text and
screenshots of six pages and asked the brief's thirteen questions. Nine answers were obvious from
the page, four had to be hunted for (which countries, which are GCC members, why Saudi Arabia
differs, why there is no index on the overview), and none was missing. The last two were answered
"no", as intended. The overview now names the eight and the GCC members in its first box, says in
one sentence each why there is no index and why two recording rules exist, and the card and list
wording that contradicted the country pages was rewritten. The same reader listed 42 problems;
§24 says which were fixed.

## 21. Performance

Lazy by route. The home page fetches no country payload and no Gulf context; the Gulf overview
fetches its context and no country's events; a country page fetches its own directory only. All
three are tested in a real browser. Sizes, uncompressed: `global/gulf.json` 19 kB; a new system's
`system.json` 26 to 30 kB and `events.json` under 18 kB; the Gulf view's own script chunk 16 kB;
the country view's 44 kB. `global/world.geojson` grew by about 6 kB (to 438 kB) because a
monitored country's detached parts are now kept.

## 22. Tests

TESTS_PLACEHOLDER

## 23. Mutations

MUTATIONS_PLACEHOLDER

## 24. Red teams

Before review: a blind safety review of the first packets changed the gate (§3, item 2). At
release: five independent sessions, none shown the others' work or the lead's reasoning. Four
said "do not release". All of their blockers are closed; the candidate that ships is the one
after their findings.

| Review | Verdict on the candidate | Blockers | Should-fix |
|---|---|---:|---:|
| Safety | do not release | 6 | 10 |
| Methodology and sources | do not release | 2 | 20 |
| Geography, language, dates, ids | do not release | 1 | 12 |
| Test architecture | (gaps only) | 6 high | 10 medium |
| First-time reader and UX | (ratings only) | - | 42 problems |

**Safety.** The record fields held. The leaks were in prose no gate read: campaign bases, lane
notes, sweep result paragraphs, review-edit reasons, one nuclear-adjacent clause in two documents,
and a short-link citation. All six blockers are fixed as rules with tests (§3, §17). Of the
should-fix items: campaign bases and status sources, lane notes, sweep tallies, the regional
list, profile rows and the audits' finding aids were fixed; two records were held on its
single-facility and partial-effect points. **Not changed:** Saudi Arabia's existing records
(owner); the share of the world total on the regional view, which the brief asks for and the
payload now words as descriptive (owner question on the exported image); held counts shown on a
country page; ids ending in a sequence number.

**Methodology.** Blocker 1 (three Iraq records published against `REVIEW_GOVERNANCE.md` §7.3):
held. Blocker 2 (the country image export printed "0 qualifying events ... reviewed null" for an
empty system): fixed. Also fixed: region zeros that should be "not applicable"; draft labels and
a rank in published profiles; coal marked not applicable where coal use is recorded; lanes
mislabelled as stopped by the search limit; "items read" for title-only listings; a link-check
note shown for systems never link-checked; undated memberships; stale "five countries" sentences;
one record held on conflicting figures. **Not changed, listed in §26 or §27:** clause 5 on extent
alone and clause 1 on a partial effect (owner); lower bounds stored in `capacity_affected.value`
with the range stated beside them; `single_source_events` counting citations, not statements.

**Geography.** The blocker was the same Iraq campaign sentence. Fixed: display names (and the gate
now reads addresses against every spelling a unit goes by, which closes a real gap: the map file
says "Dubay"); notes that described islands the map does not draw; detached parts of monitored
countries missing from the overview map; view bounds taken from the manifest; units with no
count; two map-extent notes for Iran and one for Baghdad; month dates parsed without relying on
one browser engine; common Arabic and Kurdish status wording. **Not changed:** `normalize_date`
and `parse_number` accept some malformed inputs they should refuse (no published record uses a
converted date and `parse_number` has no caller); month-precision dates are written two ways in
the data.

**Test architecture.** The gate and the country event files were well guarded; what was derived
from them was not re-checked as served. Fourteen simultaneous edits to the regional payload had
passed the whole suite, and the one browser test of how an attack record renders filtered on a
cause value that does not exist, so it had never checked a record. Adopted: final-artifact tests
for the regional list, regional figures, cards against each country's own payload, both copies of
every payload, every served headline against today's gate, every served date, the served maps,
campaign start dates, and every mutation's anchor; five browser tests, including the attack
rendering test rewritten on the real cause values. The build now refuses a declared episode on an
attack record published for the country.

**First-time reader.** See §20. Fixed: the contradictions it found between pages (what is
withheld, where effect text is shown, "no record reviewed yet" beside a count of candidates, an
empty outlined box beside two maps, attack placement stated on the Iraq banner), plural slips and
several unexplained phrases. **Not changed:** most of its jargon list ("system", "lane", language
codes, internal document names in the methodology tab) and the layout order of the overview's
first screen on a phone, which is explanation before map by design.

## 25. Production

PRODUCTION_PLACEHOLDER

## 26. Unverified

- Gulf citations were not link-checked. The pages say so per system.
- OPEC's member list was not read on OPEC's own page.
- No page was read in full by a person: reviewers read through a fetch tool that returns extracts,
  and checked claims with targeted quotations in the page's own language.
- Campaign states rest on one status search per system, in English, on 2026-11-11.
- The 2022 to 2024 record of every new system is thin for the reasons in §16. A year in which the
  queries found nothing is not a year shown to be quiet.
- The short-link finding rests on an automated yes/no reading of one page. The record is held
  either way.
- Arabic, Persian and Kurdish status wording is matched by a list of common forms. It is not a
  parser; three reviewers read every published text and address as well.
- Spelling variants of unit names (`unit_aliases`) are a hand-made list and will miss some.
- Map extents: areas are as Natural Earth draws them. The notes on Iran's Yazd and South Khorasan
  and on Baghdad come from point tests against the map file, not from an official list.
- Known latent defects, not fixed: `calendars.normalize_date` returns a date for some malformed
  inputs, and `calendars.parse_number` joins two numbers in some strings. No published record
  uses either path.
- Three published records store a lower bound or a one-unit figure as `capacity_affected.value`,
  with the qualification written beside it. The value is not rendered or summed.
- `source_health.single_source_events` counts citations. Three published records cite more than
  one page that carry the same statement.
- Every reviewer was a separate session of the same model: independent in context, not in model.

## 27. Held owner decisions

Nothing below was deployed. Each holds the records or feature it names.

1. **Scheduled seasons of load shedding** (Iran, Iraq, Kuwait): a record, an episode, or context?
2. **Taxonomy gaps**: no class for a fuel depot, a petrochemical plant, a power-and-water plant or a
   gas-to-liquids plant.
3. **An attack with sourced occurrence and no effect reported within seven days**: accepted or held?
4. **Production shut in because an export route was closed**: out of scope by the route rule.
   Confirm, and say whether a field halted by a fault on its own export line is the same case.
5. **A force-majeure declaration with no stated shutdown**: does it meet clause 1?
6. **A share of national capacity as the only threshold basis**: the safety rule removes it. Does
   the record then qualify on damage alone?
7. **Counts of substations or calls** in place of a customer count.
8. **"Emergency plans activated"**, or a ministry "working on a full emergency footing": is either
   a clause-5 emergency declaration?
9. **An importer's shortfall caused by a supplier's stated maintenance**: excluded or not?
10. **A non-attack record at or about a site that has attack records** under a country-level rule:
    published by name, covered by the campaign, abstracted, or held?
11. **Saudi Arabia's region-level, facility-named attack records**: bring them under the
    country-level rule? The home page's recent list also carries their ids and regions.
12. **Walking a utility's numbered pages** as a discovery route where its listing is unreadable.
13. **Release rule A** (campaign ended plus 30 days) is still "proposed".
14. **One facility of a class in a country**: a coarser class for attack records there, a stated
    caveat on the page, or no record? Holds one confirmed record.
15. **Attack records whose reported effect is a downstream generation loss**: publish, given that
    the megawatt figure can identify the site?
16. **Clause 3 on a reported flow disruption** with no stated shutdown.
17. **Clause 4 on a stated megawatt loss with no reported load shedding** (`REVIEW_GOVERNANCE.md`
    §7.3). Holds three confirmed Iraq records, with the India and Canada records held since
    iteration 17. Also: programmed cuts on a demand peak where no source states a generation
    shortfall (one Kuwait record, published on its plan's reading).
18. **Clause 5 by official extent with no customer count**: the precedent, against the Oman plan's
    sentence. Three published records rest on it; Saudi regional outages are held for the same
    missing figure.
19. **Cause vocabulary**: no value for a precautionary shutdown during hostilities, a protest or
    blockade by people who are not the workforce (holds one record), or demand above available
    generation.
20. **The maintenance exclusion** against an unplanned shortfall during a maintenance season.
21. **A blackout with an official technical cause and separately reported sabotage**; and a
    national blackout whose published cause is the ministry's own statement of a supply drop,
    which a safety reviewer notes is a dependency statement even when attributed.
22. **Damage to a plant already halted**: a new record or a continuation?
23. **Clause 1 on a partial effect**: some units shut, with no shutdown or throughput statement for
    the plant (one published Kuwait record).
24. **The share of the world total in the exported regional image**, which travels without the
    page's caveats.
25. **Counts of held candidates on a country page**: process honesty, or a hint of scale beside an
    attack record?
26. **A guard on the national context's newer year** for a country under the campaign policy where
    a class is one site: a campaign-year national total would be that site's output.

## 28. Next-step recommendation

Do not add another country next. The seven new systems are research previews with no lane run as
far as declared, and four have no published record. The next pass should, in this order: put the
owner decisions above to the owner, since they hold more candidates than the search limit does
(seven records that three roles had confirmed are among them); decide the Saudi harmonisation
question, which is now the largest gap between what the rules say and what is published; run the
unrun declared queries, English first where a lane lacks it; have a person open the blocked
official archives in a browser; and link-check the Gulf citations. A further country should wait
until at least Iran and Iraq have a lane that ran as far as declared.
