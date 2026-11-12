# Iteration 19 review — Gulf energy expansion

<!-- status: in-progress -->

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
