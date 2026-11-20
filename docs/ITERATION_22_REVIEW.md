# Iteration 22 review: from event database to impact evidence

<!-- status: in-progress -->

Iteration 21 made the existing data easier to use. Iteration 22 adds new kinds of evidence: a
second, non-scored corpus of reviewed cyber and civilian-service impact records from any country,
attribution and AI involvement as first-class and separately-evidenced claims, a new evidence
confidence measure that counts originating statements instead of links, and an aggregate, dated
context timeline for the Gulf and the Strait of Hormuz. No country system was added and no score
changed. Live figures are in [CURRENT_STATE.md](CURRENT_STATE.md).

**The short version.**

- **Built, integrated, tested locally, not released.** Everything below is on the local branch
  `iteration-22`. It has not been pushed: the independent safety red teams for Iran, the Gulf, the
  Strait of Hormuz and cyber detail were cut off by a usage limit before they reported, and the brief
  makes those a condition of release. The lead ran a scripted safety sweep in their place (§25); it
  found no blocker, but a sweep is not a red team. Release is the first item in §35.
- **A second corpus.** 245 reviewed impact records (237 disruptions, 8 attempts with no service
  effect) from 77 country codes, January 2022 to November 2026, plus 35 dated aggregate statements
  about the Gulf and the Strait of Hormuz. Every record passed three blind reviewers (evidence,
  attribution and source, safety). None enters any index or any country's count, and nothing ranks
  countries.
- **Iran.** From no published record to 16 country-level impact records (gas and electricity
  shortfalls, drought water cuts, authority-ordered internet shutdowns, one cyber record), a
  country page that explains what it can and cannot say, and an impact brief.
- **Evidence Confidence v2** is served on every impact record and every country event, as a
  category with its reasons, never a probability. A methodology red team found five blockers; all
  five were fixed. The first blind calibration did **not** pass (§15): the thresholds stay
  provisional and the theatre's scoring multiplier is unchanged.
- **AI involvement: zero reviewed incidents.** The AI lane found 2 candidates and 27 near misses;
  neither candidate survived review as an AI-involved disruption. The product says so.
- **Tests and mutants.** See §28 and §29 for exact totals.

---

## 0. Baseline

| | |
|---|---|
| Start | local `main` fast-forwarded to `origin/main` `1b61ec7` (daily refresh of 19 November; ESDI 5.97, 184 events); iteration 21 released (`91c3136` and its review note) |
| Work branch | `iteration-22`, foundation commit `5417e92` |
| Systems | 13, unchanged: the Russia theatre (index) and 12 country systems (no score) |
| Country corpus at start | 175 published records in 12 country systems; 65 research lanes |
| Tests at start | pytest 1,235 passed, 2 skipped; vitest 454; TypeScript clean; Playwright 400 passed, 1 skipped; mutation campaign 376 of 376 caught (0 survived, 0 invalid, 0 errors) |
| Served data at start | 10.6 MB under `web/public/data`; built JavaScript 1.75 MB |
| Link health at start | last full check 12 November: 299 cited addresses |
| Iran at start | research preview, campaign-restricted, no published record; no regional context anywhere in the product |

## 1. Product objective

The dashboard answered "what reviewed energy disruption records have we found?". It now also
begins to answer: which civilian services were affected; whether a disruption was cyber, kinetic,
technical or natural; who is publicly attributed and how firmly; whether AI was materially
involved; whether wind, solar, hydro or storage was affected; what credible reporting says about
the wider Gulf; and how strong the evidence is for each claim. It still does not answer, and is
built not to answer: which facility matters most, where a weak point is, which route is
vulnerable, what is still offline at a struck site, or where any vessel is.

## 2. Global impact architecture

The contract is [GLOBAL_IMPACT_METHODOLOGY.md](GLOBAL_IMPACT_METHODOLOGY.md).

- **Curated truth:** `data/curated/global_impacts/{events.json, regional_context.json,
  research_log.json}`. **Served:** `global/impacts.json`, `global/regional_context.json`,
  `global/evidence_confidence.json` (registered in `pipeline/artifacts.py`), lazy-loaded by the pages
  that need them. `pipeline/global_impacts.py` builds and gates them; no analytic module imports it.
- **One way in:** `scripts/import_impacts.py` reads the local review queue
  (`data/candidates/impacts22/`), applies the three blind roles' corrections (evidence, then
  attribution and source, then safety), then an optional lead normalisation pass that may only make
  mechanical corrections on records all three roles accepted (it cannot change a verdict, weaken a
  publication policy, add a region or turn an attack into anything else). It mints keyed opaque ids
  for abstracted records, dedupes across lanes, reconciles with the country queues, runs the build's
  own gate, and stamps `first_published`.
- **Holds carry over (owner brief §216).** A candidate that matches, by date and class, a record a
  country system holds or rejected is refused, whatever the hold reason, a threshold included.
  There is no override. The lead may only state that a match is a different event
  (`reconcile_distinct.json`, reason mandatory; used once). 39 matches were refused this way.
- **Group pairing is data.** The registry names the regional-context file once
  (`systems.GROUPS["gulf_littoral"]["regional_context"]`); the manifest and the served context file
  (`group`) carry it, and no page pairs a group with a file by hand.

## 3. Cyber and civilian inclusion policy

Methodology §3: a record needs a documented effect on an energy service or an essential civilian
service (electricity, oil and gas, fuel supply, district energy, water, wastewater, desalination,
telecom, healthcare, transport, municipal services), stated by a source that opens. Rulings made
this iteration and now in the methodology:

- A non-malicious, digitally triggered failure is `cause_family: industrial_technical` with
  `cyber_mechanism: it_outage_affecting_operations` and attribution `NOT_APPLICABLE`. "Cyber"
  filters show malicious causes only; "IT failure" is its own filter.
- A service restricted by order of an authority (exam- or protest-period internet shutdowns) is
  `cause_family: authority_order` (new), not malicious, not cyber.
- A malicious incident with no documented service effect is `attempt_no_service_impact`, and is
  published only on an official or operator statement (12 attempts were refused on that rule).
- Banking, card payments, tax and customs platforms and heavy industry are outside the sector list:
  such records were rejected (owner question, §34).
- A municipal or public body may be named for its own non-kinetic incident; geography stops at the
  first-level region. Iran and Gulf-state records never carry a region.

## 4. Iran

From nothing published to 16 impact records, all at country level, no region, no facility, no
operator below a national body: fuel supply 7 (winter gas cuts to industry and households, a gas
shortage that closed offices), electricity 4 (summer shortfalls, industrial restrictions,
scheduled cuts), telecom 2 (authority-ordered shutdowns), water 2 (drought cuts), municipal
services 1; by cause, supply shortfall 9, natural hazard 4, authority order 2, cyber 1; 2022 to 2026.
Iran's country page now opens with "What this page can tell you" (what is published, what is not
and why), has a Cyber & civilian services tab and a Gulf & Hormuz context tab, and offers an impact
brief that stays meaningful with no canonical energy record. Seven Iran candidates were refused
because the Iran country queue holds the same event (season-of-load-management holds and a taxonomy
hold); four cyber records on banks and steel were rejected as outside the sector list. Iranian
official sites (IRNA, ISNA, Mehr, Tasnim, SHANA) refused automated fetches for most of the run, so
most Iran records rest on Persian-language broadcasters and wires. Nothing about post-strike
recovery was researched.

## 5. Gulf and Hormuz

- **Gulf page** (`?group=gulf`): seven addressable sections (`section=` in the address): overview
  with "What this page can tell you", energy context, reported impacts, cyber and civilian services,
  Gulf and Hormuz context, research coverage. A Gulf impact brief.
- **Impact evidence:** 24 records across Iran, Iraq, Kuwait and the UAE (supply shortfall 9,
  authority order 6, natural hazard 6, cyber 2, unknown 1). Bahrain, Oman, Qatar and Saudi Arabia
  have none: Qatar was searched and nothing qualified; Bahrain's one candidate was rejected as
  conflict-linked; Saudi and Omani candidates matched records their country systems hold.
- **Regional context:** 35 dated statements, 1 March to 19 November 2026: aggregate supply 8,
  shipping status 7, market response 5, aggregate trade 4, policy response 4, reserve action 4,
  civilian and environmental 3. Sources: EIA 10, IMO 9, IEA 4, UNCTAD 3, plus wires and FAO, METI,
  the UN. Every statement names who said it and when; the newest of each type says "the most recent
  statement on record, not a current status"; there is no open or closed flag.
- **The narrowed rule.** Until now the Gulf carried nothing about straits or shipping. The owner's
  brief narrows that for one artifact: aggregate, dated statements in `regional_context.json` and the
  page's context section. Vessel names, vessel counts that read as monitoring, positions, routes,
  alternate routes, bypass capacity, port or facility dependence and status flags stay forbidden
  everywhere, including there; "tanker" appears once, in the block that says why there is no tanker
  map. `CLAUDE.md`, `pipeline/gulf_context.py` (its standing sentence now speaks for the figures and
  points to the separate context) and the end-to-end tests say the same.

## 6. Oil, gas, refining, LNG

24 records in oil and gas or fuel supply: fuel storage or distribution 19, refining 2, LNG 1, oil
production 1; by cause supply shortfall 12, cyber 5, technical failure 3, civil disruption 2,
natural hazard 1, unknown 1. A dedicated lane added 12 non-kinetic records outside the theatre and
the Gulf (nine imported; two rejected because every usable source address named the facility or a
place below first-level region; one held because its only source for the subject would not open).

## 7. Power grids

126 electricity records: transmission 43, thermal generation 26, distribution 24, hydro 9, other 8,
withheld 5, wind 4, grid control 3, storage 2, unknown 2; by cause technical failure 49, natural
hazard 26, supply shortfall 21, cyber 16, unknown 7, kinetic 3, sabotage 3, civil disruption 1.
National blackouts (Iberia, Chile, Cuba, Sri Lanka, Pakistan, Kenya, Ecuador, Panama and others) are
the core of the layer.

## 8. Wind, solar, hydro, storage

15 records: hydro 9, wind 4, battery or grid storage 2; by cause technical failure 5, natural
hazard 4, cyber 3, supply shortfall 3. No solar record survived: the one solar cyber record was
rejected because every source stated the attacked plant's as-of status, and two US
inverter-based-resource disturbances matched records the US system holds. Grid disturbances where
generation tripped but no customer lost supply were rejected unless the regulator classed them as
reportable events with a stated system effect.

## 9. Civilian essential services

132 civilian-service effect rows carry a figure in the source's own unit. Effects recorded:
electricity 111, transport 36, telecom 35, water 28, healthcare 26, fuel supply 20, municipal
services 19, district energy 7, desalination 1, wastewater 1. Desalination is thin: no Gulf
desalination disruption with an openable source was found; that is a research gap, not a finding.

## 10. Cyber corpus

78 cyber records (70 disruptions, 8 attempts). By sector: healthcare 17, electricity 16, municipal
services 11, telecom 11, transport 10, water 7, fuel supply 3, oil and gas 2, district energy 1. By
mechanism: ransomware 28, not reported 24, operational-technology disruption 7, unauthorised access
6, destructive malware 5, denial of service 4, and one each of data wiper, malicious configuration
change, cyber-physical disruption and service-provider compromise. Plus 12 non-malicious IT
failures, filtered separately. No record carries an IP address, CVE, device, protocol, access
method or tool name (§25).

## 11. Attribution model

Methodology §6. Status: NOT_APPLICABLE 157, UNKNOWN 41, ASSESSED 16, CLAIMED 11, SUSPECTED 11,
ATTRIBUTED 6, DISPUTED 3. Computed attribution confidence for records with an attribution question:
NOT_ESTABLISHED 41, MODERATE 20, CLAIM_ONLY 11, LOW 10, DISPUTED 5, HIGH 1. Rules fixed after the
methodology red team: an actor's own claim never yields more than CLAIM_ONLY however it is relayed
(a wire report of a claim carries `attribution_basis: actor_self_claim`); a state body announcing
its own operation is a self-claim; SUSPECTED is capped at LOW and ASSESSED at MODERATE; a non-empty
`competing` list reads as DISPUTED; a relayed attribution never counts as a second origin.
Reviewers downgraded several statuses that said more than their sources (one official's interview
is not a formal attribution; a campaign-level advisory that does not name the victim attributes
nothing to it).

## 12. AI involvement

**Zero reviewed AI-involved incidents.** The AI lane searched for disruptions where a source ties AI
materially to the incident and found 2 candidates and 27 near misses (general warnings, defender
use, unverified claims). One candidate was a false alarm that fails inclusion; the other was
downgraded to an attempt and then refused because no official statement supports occurrence. All
245 records are NONE_REPORTED. The model is ready (status, relation `ai_assisted` vs
`ai_operational_cause`, role) and the Atlas has an AI filter; the product says that the reviewed
count is zero and that a general warning about AI-enabled campaigns is not involvement.

## 13. Social media sources

59 social sources on 36 records, all opened by the lane and by two reviewers (source check and
safety): S1 15 (official accounts whose identity was established from the organisation's own site
or domain), S2 41 (mostly internet-measurement organisations, as researchers), S4 3. Platforms:
Bluesky 39, Telegram 14, X 4, Mastodon 2. No record rests on social sources alone. Three posts were
rejected by safety (restoration progress of an attacked network; a network identifier of an
attacked operator; an effect placed at a named airport); four S1 claims were moved to S2 because
identity rested on a second-hand pointer. Public posts only, text only, no imagery as evidence, no
identification of people. An official account's own post was reachable without a login for about
one record in twenty.

## 14. Evidence Confidence v2

[EVIDENCE_CONFIDENCE_V2.md](EVIDENCE_CONFIDENCE_V2.md). Points for who is speaking, independent
originating statements, specificity of the effect, whether a source was opened, and whether a source
is dated near the event; categories High, Moderate, Limited, Preliminary, plus Disputed and Not
assessed. On impact records: High 114, Moderate 121, Limited 4, Preliminary 5, Disputed 1. Country
events are mostly Moderate, because their origins were not reviewed for relays and the model will
not call an unreviewed count "independent". The methodology red team's five blockers, all fixed:
"read by a reviewer" now reads the review block; an unreviewed origin count is called "distinct
publishers" and capped at Moderate, with an organisation table (one department, one state news
agency, a form and its filer count once); self-claims cannot climb; a record cited only through a
discovery aid is "Not assessed", never Preliminary; nothing claims a calibration that did not pass.

## 15. Confidence calibration

Run once (EVIDENCE_CONFIDENCE_V2.md §6). 72 blind packets; two labelers finished (a third was cut
off by the usage limit). Reviewer against reviewer: exact 0.83, kappa 0.73. Each reviewer against
the model: exact 0.50 and 0.42, kappa 0.11 and 0.02, though 96% within one category. **Not
calibrated.** The disagreement is mostly the model holding unreviewed records at Moderate where the
reviewers say High; the next run should draw imported (reviewed) records only and use at least three
labelers including one person outside the build. No parameter changed; the version stays
`2.0-draft`.

## 16. Theatre confidence shadow study

`scripts/confidence_shadow_study.py`, written into EVIDENCE_CONFIDENCE_V2.md §8: under v2 every one
of the 184 scored theatre incidents would get a lower weight and none a higher one, largely because
the theatre's citations carry no official domain and many no readable date; the shadow index is
about 3.3 against the served 5.97. None of the seven owner conditions for replacing the multiplier
holds (no passing calibration among them). **The theatre multiplier is unchanged**; tests pin
`build_index` against importing the confidence module.

## 17. Global Impact Atlas

`?view=impacts`: header with the corpus's own caveats, filters in the address, seven presets
(cyber, AI involved, attributed cyber, power-grid cyber, renewable cyber, civilian-service cyber, IT failure; attempts are a collapsed list of their own),
a chronological timeline, a one-colour presence map with an alphabetical country list (no counts
by country on the map), collapsed attempts, the shared Evidence Inspector, CSV with a README, empty
and error states. Reached from the site bar, the home page, search and the glossary (14 terms).

## 18. Filters and CSV

Shared filter model and bar (`recordFilters.ts`, `RecordFilterBar.tsx`) on country pages, the Atlas
and the Gulf page: state in the address, unknown values dropped with a note, "Showing n of N"
always visible, a phone sheet. CSV: allow-listed columns, RFC 4180, a formula guard, BOM, and a
separate "About this file" README; a campaign-covered record whose own text names a facility exports
date, class and cause only; a not-assessed record exports "Not assessed".

## 19. Evidence Inspector

The inspector shows the served reasons, the components and what produced the category, the
attribution block with its basis and competing claims, the AI block, the sources with role, medium,
tier and identity basis, and what the record does not establish. The country inspector's old
sentence, "this can undercount independence but never overstate it", was backwards and is replaced:
an unnamed republication makes the count overstate independence, which is why it is not called
independent until reviewed.

## 20. What's New

Record-level links (outside the campaign rule) and impact-layer changes in the home panel; links
open the right tab.

## 21. Research coverage

21 research lanes: 15 regional and thematic first passes, 3 second passes, a Gulf civilian-services
pass, an oil and gas pass and a social-corroboration pass; plus the Hormuz context lane. 321
candidate records and 35 context entries filed; 159 source families logged; 222 unfinished leads
recorded by name in the lane logs. WebSearch: 195 of the 200 shared calls. The published research
note carries process facts only.

## 22. Gulf research

Lanes: gulf_states, iran_power (two passes), iran_cyber, hormuz, gulf_civil2. Qatar: nothing
qualifying. Bahrain and Oman: no surviving record. Persian and Arabic official sites refused
automated access for most of the run. Every outage dated after 28 February 2026 in these countries
was filed only where an authority stated a non-attack cause; ten such outages were logged by date
and country only and not filed. Two conflict-period technical records were held by the lead.

## 23. Global research

Records from 77 country codes (alphabetical list in `global/impacts.json`, never ranked).
Conspicuous gaps the lanes recorded: CERT and regulator archives not walked end to end (CISA, EPA,
HC3, CERT-UA, NERC beyond a sample); Baltic subsea cable and pipeline damage deliberately not
researched (owner question); desalination; Central Asia beyond single-origin records; a
healthcare backfill list (named in the water_health lane log).

## 24. Source and link health

632 citations, 585 opened by a researcher or reviewer. Sources that refused automated fetches,
named by two or more lanes: Reuters (12 lanes), BBC (12), AP (9), The Guardian (8), The Record (8),
NPR (7), web.archive.org (7), CNN (6), plus Iranian official sites. A record none of whose sources
opened was rejected. **The automated link check (`scripts/check_source_links.py`) has not been run
on the new corpus**; served `link_check` is "unchecked" for impact sources.

## 25. Safety

- **Scope boundary held in data and gates.** Every kinetic or sabotage record is country-abstracted
  with a keyed id (8 records); no Iran or Gulf-state record carries a region; the gate refuses
  coordinates, IP addresses, CVEs, exploit wording, route wording outside the context, status
  wording on abstracted records, and a held country record reappearing.
- **Blind safety review** of every candidate removed hundreds of leaks, most of them in addresses and
  titles rather than prose: URLs naming an emirate, a field, a facility or a method; headlines on
  abstracted records; vessel counts that read as monitoring; malware family and device names;
  failure-chain detail; an attacked plant's as-of status.
- **Lead sweep** (`safety_scan.py`, the served bytes): no place word from any campaign system's unit
  table or a list of common sub-national names in any text, id or URL path of the 24 Gulf-group
  records; no status wording on abstracted records; no forbidden maritime word in context entries
  beyond aggregate references to "vessels" in UN and IMO statements and one UNCTAD sentence on
  war-risk insurance costs (aggregate market effect, allowed); no technical exploit detail in any
  record (one US article slug says "exposing vulnerabilities"; one standard record's headline names
  the ransomware group its attribution block names). No blocker.
- **Not done:** the independent Iran/Gulf/Hormuz safety red team, cyber-safety red team,
  attribution red team and energy-analyst red team were each stopped by the usage limit before
  reporting. **Intentionally not collected:** facility criticality, vulnerability, dependence,
  routes, vessels, bypass capacity, current status of anything attacked, device inventories,
  exploit detail.

## 26. UX, mobile, accessibility

Each frontend agent checked its own pages at 390x844 and 430x932 (no sideways scroll), keyboard
paths and focus. The first-time-user, mobile and accessibility red teams were not run. The full
Playwright run caught one phone regression: the country impact-brief button, as a fourth header
button, wrapped onto a second row and pushed a Gulf member's map out of a 390x844 first screen (720 px
against a 694 px limit). The button now sits at the top of the country's impacts tab, beside the
records it summarises, with its own e2e test. A wider Linux fallback font could still tighten that
first-screen check in CI.

## 27. Performance

Served data 10.6 MB → 12 MB (the impact payload is 1.16 MB, lazy-loaded). Built JavaScript 1.75 MB
→ 1.90 MB. The theatre no longer waits for the network-lines file: map ready 4.7 s → 2.6 s on a
throttled connection (median of five, uncompressed preview).

## 28. Tests

Final local gate on the integrated branch (19 November 2026, commit `df252c8` plus docs):

| Suite | Result |
|---|---|
| pytest | 1769 passed, 2 skipped |
| TypeScript (`tsc -b --noEmit`) | clean |
| vitest | 665 passed in 44 files |
| Vite production build | OK |
| Playwright (Chromium, built bundle) | 496 passed, 1 skipped |

The first full run after integration failed 3 pytest, 2 vitest and 4 Playwright tests. None was a
data or safety defect: tests not yet following the registry-named `regional_context` key, a
calibration test that read "no run yet" as the only draft state, a stale inspector heading, a
fixture counted twice, the phone-width header regression in §26, and the over-strict context check
in §33. Each was fixed at its cause; none was skipped or loosened beyond the written rule.

## 29. Mutations

Baseline 376 of 376 caught. The campaign now holds 713 mutants (filters 31, impact layer 97, Atlas
43, confidence 107, country pages 26, Gulf page 28, lead integration 9, and earlier lists).
Each agent ran its own list to zero survivors; the lead's integration list: 33 attempted, 33
caught. **Full campaign on the integrated branch: 713 attempted, 713 caught, 0 survived, 0 invalid
anchors, 0 errored, 0 baselines not green** (19 November 2026, 19:28-20:57). The sandbox was copied
after the Python and calibration fixes in `df252c8` and before that commit's frontend changes (the
brief button's move and the e2e rule); the campaign's mutants are pytest-keyed, and the anchor check
passes on the final tree.

## 30. Red teams

| Red team | State |
|---|---|
| Methodology and confidence | Done: 21 findings (5 blockers, 13 should-fix, 3 notes), all reproduced; blockers fixed, 10 should-fix fixed, 3 recorded as limitations |
| Iran, Gulf, Hormuz safety | Started; stopped by the usage limit before reporting. Lead sweep instead (§25) |
| Cyber safety and exports | Started; stopped by the usage limit |
| Attribution, AI, social | Started; stopped by the usage limit. Social sources had two blind reviews |
| Energy analyst and multilingual | Started; stopped by the usage limit |
| First-time user, mobile, accessibility, test architecture, final post-production | Not run |

## 31. Moving-main integration

Not done: `origin/main` keeps advancing with the daily refresh bot, and the branch has not been
merged with it. Before release: `git fetch`, merge `origin/main` (generated payloads conflict: take
ours and rebuild), current-date build.

## 32. Production

Not released. Production still serves iteration 21 plus the daily refreshes.

## 33. Unverified and limitations

- The four content red teams above did not report.
- Link check not run on the impact corpus.
- Full Playwright run on the integrated branch: 496 passed, 1 skipped (Chromium only, local; CI not run because nothing was pushed).
- Next-day refresh simulation not run with the impact layer present.
- Calibration used two agent labelers, not people; it failed, so nothing rests on it.
- One e2e check was stricter than the rule it tested: it refused the bare words "ship" and "vessel"
  in the Gulf context section, which methodology §10 allows in an authority's aggregate statement.
  It failed on nine real IMO, UNCTAD and UN statements (seafarers on ships, a fall in ship transits,
  IMO-recorded incidents involving vessels), never on a name, number, position, track, flag or list.
  The check now tests §10 as written (names, lists, tracks, positions, flags, AIS, MMSI, warships,
  routes, bypass, dependence). Whether those nine statements read well is for the Gulf content red
  team.
- Many news and official sites refused automated access; records rest on what opened.
- Counts are published records in this corpus, never rates, and never comparable across countries.

## 34. Owner decisions

Unchanged and still the owner's: Saudi harmonisation (Option B stays), D-34 to D-37, Release Rule A.
New:

1. **Held country records and the impact layer.** 39 impact candidates matched records that country
   systems hold, mostly on threshold or season-representation grounds (for example Iraqi national
   blackouts held for a missing customer count). Under brief §216 they are refused with no override.
   Should a non-kinetic, country-level record held only on a country system's threshold be allowed
   in the impact layer, which has its own inclusion contract?
2. **Sectors outside the list.** Banking and card payments, tax and customs platforms, heavy
   industry: add a sector, or keep rejecting?
3. **Baltic subsea cables and pipelines:** deliberately not researched; research at country level
   with the abstraction rule, or leave out?
4. **Release without the content red teams?** Recommended: no.
5. **Calibration:** accept a second run on reviewed records with a human labeler as the bar for
   dropping `-draft`?

## 35. Recommended next iteration

1. Run the four content red teams (Iran/Gulf/Hormuz safety, cyber safety and exports, attribution
   and AI, energy analyst and multilingual) on the served bytes; fix through review corrections.
2. Link check on the impact corpus; next-day refresh simulation; merge `origin/main`; full gate;
   push; CI; production verification (served bytes, safety scan, Atlas, Iran, Gulf, phones).
3. First-time-user, mobile and accessibility red teams on the Atlas, the Gulf page and Iran.
4. Calibration run 2 on reviewed records with three labelers including a person.
5. Research: Gulf desalination and water; CERT and regulator archives end to end; healthcare
   backfill; Persian and Arabic official sources when they open; Central Asia second origins.
