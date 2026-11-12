# Iteration 20 review: Gulf maturity, strict reading, safer campaign surfaces

Iteration 20 added no country. It continued the Gulf research that iteration 19 started, read every
published record of every country system against the written inclusion rule, hardened the parsers
and the citation-address gate, collected the owner questions into one matrix, and ran two rounds of
red teams. Live figures are in [CURRENT_STATE.md](CURRENT_STATE.md), which the build regenerates;
none is re-quoted here except where a figure is the point of a finding.

**The short version.**

- **The written rule is now enforced, not stretched.** Published records whose basis depended on a
  reading broader than the clause were held (24 public holds by the end of the iteration, each with
  a tag) or had their basis corrected where their own text met the clause. Re-bases onto another
  clause and the four US operational definitions went to the owner (D-27 to D-30, D-35). No clause
  was changed.
- **The Gulf is still mostly a research preview, and that is the correct outcome.** Eleven lanes
  reached "declared search complete". Seven stopped on the shared search allowance and say so.
  Bahrain, Iran, Oman, Qatar and the UAE have no published record. Iraq has two, Kuwait three and
  Saudi Arabia six.
- **Campaign surfaces are safer.** No per-system held count is published for a system under the
  campaign policy, committed research logs carry no outcome counts for them, no national figure newer
  than the comparison year is shown for them, and the address gate now reads place names in every
  common spelling and script.
- **Russia did not move.** The theatre index is 6.69 as of 12 November. A reconstruction as of
  11 November gives 6.80, the iteration-19 value, so the code effect is zero and the difference is
  time decay.

---

## 0. Baseline

| | |
|---|---|
| Start commit | `e626df2` (iteration 19, release gate totals and production verification) |
| origin/main at start | `e626df2`, so no moving-main integration was needed at the start |
| Systems | 13: the Russia theatre (index) and 12 country systems (no score), unchanged |
| Published country records at start | iteration-19 corpus (see `ITERATION_19_REVIEW.md` §5) |
| Mutation campaign at start | 133 mutants (iteration 19) |
| First commit of the iteration | `c03bff6`, the Gulf continuation plan, committed before any search |

## 1. Iteration-19 debt inventory

Iteration 19 left 26 owner questions (§27 of its review), seven confirmed records held on lead rulings
after the release gate, no Gulf lane run as far as declared, a parser that read a few ambiguous
number and date forms as certain, and a Saudi system whose attack records followed an older
convention than the seven new systems. Each is accounted for below: the owner questions in §2, the
lanes in §5 to §12 and §31, the parsers in §17, Saudi Arabia in §4.

## 2. Owner-decision matrix

[OWNER_DECISION_MATRIX_20.md](OWNER_DECISION_MATRIX_20.md) replaces the scattered iteration-19
questions with one list of 41 rows. Rows D-01 to D-26 are the iteration-19 questions; D-27 onward are
new. Each row states the question, the written rule, precedent, systems, published and held records
affected, safety, a recommendation, what approval would implement, and the conservative behaviour
the code runs until then.

New this iteration, after the red teams: **D-34** (withheld material in git history and old
deployments), **D-35** (re-bases onto another clause, and the asymmetry of D-27 to D-30), **D-36**
(event totals), **D-37** (EEA-3 with no load shed), **D-38** (pipeline loops, mine halts, sub-day
trips), **D-39** (Saudi Arabia and the Gulf route rule), **D-40** (a cause value for shortfalls),
**D-41** (superseded unit codes).

The matrix header now states one exception openly: D-27 to D-30 keep records that the clause alone
would not admit, because each was adopted, documented and tested in iteration 16. Holding about
twenty records on a reading the owner was never asked about would itself be a lead ruling. D-35 asks
the owner to close the asymmetry either way.

## 3. Threshold consistency

[CROSS_SYSTEM_THRESHOLD_AUDIT_20.md](CROSS_SYSTEM_THRESHOLD_AUDIT_20.md) read every published record
of all twelve country systems against `inclusion_threshold.json`. The principle: **a written rule is
not broadened by precedent.** A record that depends on a broader reading with no owner ruling is held
with a tag; a record whose own text meets the clause but whose basis cited a weaker fact had its
basis corrected.

The first pass (checkpoint `33d3101`) held 17 records. The methodology red team (§26) found more of
the same defect and some inconsistencies between held and published records under the same question.
The lead held what failed on its own stated basis or whose analogue was already held:

- `[C1-AGGREGATE]` a regional total of refinery capacity with no plant named;
- `[NO-EFFECT]` a mine collapse with no stated output reduction;
- `[C1-PARTIAL]`, `[C1-MATERIAL]` one of two crude units shut with no throughput figure; "run at a low
  level", the reduced-rates wording already held elsewhere;
- `[C5-LOADSHED]` four OE-417 firm-load-shed filings with no stated cause and no customer count at the
  floor (four that state a generation cause stay, by D-27, and their re-base is D-35);
- `[C3-PARTIAL]` a pipeline record that says its parallel loops kept running;
- `[C5-SUBSTITUTE]`, `[C5-SOURCE]`, `[C5-TOTAL]` people counted as customers; an aggregator snapshot as
  the only at-one-time figure; an event total under three times the floor;
- `[C2-PORT]` a port-level precautionary suspension with no terminal statement, as the US port
  closures already were;
- `[TAXONOMY]` a precautionary pipeline shutdown with no damage stated, as the analogous Iraq records
  already were;
- `[D-10]` two facility-named non-attack records in a class with attack records in the campaign window.

Two basis texts were corrected without changing their clause (an at-one-time figure the basis
called unconfirmed; an Iraq record restated on the limb its own effect states). Every hold is pinned
by `test_no_record_held_on_a_strict_reading_is_published`, and the clause tests were strengthened
to read the basis text, not only the unit field ("people" written up as customers; "peak demand"
as well as "demand peak").

## 4. Saudi harmonisation study

[SAUDI_HARMONISATION_STUDY_20.md](SAUDI_HARMONISATION_STUDY_20.md) sets out five options, from
grandfathering the older convention permanently to abstracting every Saudi attack record for good.
**Recommendation: option C**, abstract campaign-covered Saudi records on every served surface while
the campaign restricts, keep the full record in the local queue, and restore detail under release
rule A. **Implemented: option B**, which changes no canonical fact: the global and Gulf recent lists
show a campaign record as national with a row key, carry no effect text, and name no episode that
contains one; the Saudi page says plainly that its older records keep the earlier convention; a
nameplate is marked as the facility's size. Option C is the owner's (D-11, D-33). The Gulf route rule
for Saudi Arabia is D-39.

## 5 to 12. Gulf research, by system

The continuation followed [GULF_CONTINUATION_PLAN_20.md](countries/GULF_CONTINUATION_PLAN_20.md),
committed before any search. Every lane says why it stops, in fixed sentences only (§19). The
per-lane table is in §31.

| System | Published | Episodes | Lanes declared complete | Partial | Stopped by the search allowance | Languages run | Campaign state | Index |
|---|---|---|---|---|---|---|---|---|
| Bahrain | 0 | 0 | 1 of 3 | 2 | 1 | Arabic, English | uncertain (treated as active) | none, by design |
| Iran | 0 | 0 | 4 of 6 | 2 | 1 | Persian, English | active | none |
| Iraq | 2 | 0 | 3 of 5 | 2 | 0 | Arabic, Kurdish, English | active | none |
| Kuwait | 3 | 0 | 1 of 4 | 3 | 1 | Arabic, English | uncertain | none |
| Oman | 0 | 0 | 1 of 5 | 4 | 0 | Arabic, English | uncertain | none |
| Qatar | 0 | 0 | 1 of 3 | 2 | 1 | Arabic, English | uncertain | none |
| Saudi Arabia | 6 | 0 | 0 of 5 (one not started) | 4 | 2 | Arabic, English | active | none |
| UAE | 0 | 0 | 0 of 4 | 4 | 1 | Arabic, English | uncertain | none |

Held candidates are not counted per system for any of these eight: a per-country count of held
attack candidates would hint at the scale of a campaign. Across all twelve country systems the local
queues hold 1,337 candidate records, published or not.

- **5. Iran.** The heaviest lane load of the iteration, roughly 890 requests across the Persian-language
  official and agency lanes. Most Iranian official and agency sites could not be read from outside
  the country; that is recorded per lane as a refused or unreadable source, not worked around. No
  record was published; the reporting note now says so instead of describing what an empty record
  "rests on".
- **6. Iraq.** Three lanes declared complete, including the Kurdish-language lane. Two records
  published. Iraq's attack candidates are held by the address gate or by review; the Kurdistan
  region words are now read by the gate.
- **7. Kuwait.** Three records published (programmed-cut days that meet clause 4). Two facility-named
  non-attack records were held under D-10, and a third under the strict reading.
- **8. Bahrain, 9. Qatar, 10. UAE, 11. Oman.** No qualifying record in the reviewed corpus. Each page
  says that this is a statement about the corpus, not the country (§E of the final handoff).
- **12. Saudi Arabia.** Six records published. The precautionary pipeline-shutdown record was held
  `[TAXONOMY]` for parity with the Iraq records; the Khurais figure now carries "about", as the
  record's own summary says.

## 13. Link-health audit

`scripts/check_source_links.py` made one automated visit to each cited page on 11 November
(`data/curated/systems/source_link_health.json`). Blocked means the site refused an automated
visitor, not that the page is gone.

| System | Reachable | Redirected | Blocked | Dead | Error |
|---|---|---|---|---|---|
| Canada | 54 | 0 | 3 | 3 | 0 |
| China | 24 | 0 | 2 | 0 | 0 |
| India | 24 | 0 | 3 | 1 | 0 |
| Iraq | 3 | 0 | 0 | 0 | 0 |
| Kuwait | 10 | 1 | 0 | 0 | 1 |
| Saudi Arabia | 8 | 0 | 0 | 0 | 0 |
| United States | 179 | 0 | 5 | 0 | 2 |

Every published Gulf citation was checked. The check predates the red-team holds, so a few rows count
citations of records since held. Citations are judged at the address they land on, not the one
written (`final_addresses`).

## 14. Source independence

The energy-analyst red team found that source health counted URLs, so two situation reports from one
agency, or a wire story and its republication, looked like corroboration. Source health now also
counts **originating statements**: a wire service the publisher field names (Reuters, Bloomberg, AP,
The Canadian Press, Xinhua, PTI, IANS, AFP, SPA and others), else the registered domain the citation
sits on. Wikipedia and content aggregators are discovery aids and count as no origin. The country
page shows both counts and the rule. Republication that a record does not name cannot be seen, so
the count can undercount independence but never overstate it. In the US corpus, 49 events rest on
one citation but 74 on one origin, and 8 only on Wikipedia or an aggregator.

## 15. Gulf national context

- **Labels carry their definitions.** "Crude oil incl. lease condensate", "Dry natural gas", "Net
  electricity generation". The full definition is the hover text on every figure and table header,
  and the Gulf table has a "What each column measures" list. A bare "Crude oil" invited comparison
  with crude-only figures 2.2 times smaller.
- **The accounting convention is stated** wherever an energy total or share appears: EIA counts
  nuclear by its heat and wind, solar and hydro by their electricity, so a share of the total
  understates those three. This is why Sweden and Switzerland map as "largest source: nuclear".
- **Scope notes** where an EIA figure's scope differs from what a reader would assume: Iraq's
  electricity may cover federal Iraq only; India's CEA figure is on another scope.
- **Superseded profile figures replaced.** Three Saudi rows from the October 2024 country brief were
  replaced with the current release (one was labelled crude-only on a crude-plus-condensate series).
  The US "22% of world oil" became the 2024 figures on both bases; the US LNG share is about 27%, not
  26% (26% was the year-on-year growth). China's coal line names its two bases.
- **OPEC and GCC membership** were verified against primary pages (OPEC's member list, read
  11 November, still lists the UAE after its announced departure on 1 May 2026; the GCC
  Secretariat's member page). Both bases are cited in `pipeline/systems.py`.
- **Under the campaign policy** a country's own profile shows no figure newer than the comparison
  year (`profile_year_cap` in `conflict_campaigns.json`, kept equal to the context year by a test).

## 16. Regional-source decisions

No new regional source was adopted. The Gulf context stays one source (EIA International Energy
Statistics), one year, national only. Membership is a field, never a shorthand for the eight.

## 17. Parser, calendar and number hardening

- **Numbers fail closed.** Refused: two numbers side by side, the Arabic comma, a decimal comma,
  "1.500", a leading zero, mixed marks, and now a space between groups unless the caller opts in,
  digits from any other script, and digit sets mixed in one number.
- **Dates fail closed.** One month-date form; Solar Hijri and Hijri months keep month precision with
  their Gregorian range. New: a Hijri day carries a range of one day either side (the tabular
  calendar can differ from the observed date), and a weekday the source states settles it; a weekday
  that does not match a Gregorian or Solar Hijri date is refused; an impossible time in a timestamp is
  refused.
- **The address gate folds every spelling** (`build_systems.fold`): letter forms (ی/ي, ک/ك, ة/ه,
  hamza forms), diacritics, tatweel, repeated percent-escapes, camelCase, attached Arabic prefixes,
  multi-word names as phrases, and a place in a subdomain. Every unit of the seven country-policy
  systems has a native-script and a Latin name (Iran had none in Persian, and Qom had no token).
  Method and route wording gained Arabic, Persian and Latin forms.

## 18. Geography

- The Nahwa enclave was drawn twice (inside Oman's Madha and as itself) because simplification
  dropped any hole under six points. Holes of four or more points are now kept. The same fix
  restored three enclave holes in the Russia theatre's display geometry (Orenburg, Tatarstan, Tyumen);
  no number changed.
- Display names replace raw Natural Earth spellings ("Al Quassim", "`Asir", "Inner Mongol", the
  Bahraini diacritics, "Karbala'"). The abolished Bahraini governorate shows as such.
- Siachen and the Spratly Islands are now stated in the India and China notes as outside the
  systems, by the source's classification.
- The review refuses a unit that never takes records in any code field, including a disputed,
  unassigned unit (the build already did).
- Right-to-left direction reads the whole language subtag (Sorani `ckb`, Uyghur, Pashto, Sindhi,
  Dhivehi) and a script subtag.
- Superseded codes for three units remain (D-41); a current code is refused loudly, so nothing is
  misplaced.

## 19. Campaign and publication safety

- The campaign-status text rule covers every country system, not only the Gulf.
- Committed research logs of systems under the campaign policy carry no outcome counts; the counts
  live in the local `data/candidates/research_outcomes.json`. Lane notes are fixed sentences only.
- The public `review_edits.json` keeps, for those systems, only one final `set` per field with a
  generic reason, and nothing for an unpublished record. A test and two mutants enforce it.
- A single-site class (one facility of its class in the country) refuses an attack record: country
  plus class would name the site.
- A headline whose script does not match its declared language is not published (a placeholder
  stored as an Arabic title would have rendered as English in a right-to-left span).
- Documentation redactions: the sweep and lane-pass documents, the iteration-19 review and the
  decision matrix no longer name withheld facilities or give per-campaign held counts. Earlier
  commits still contain them; that is D-34, and no history was rewritten.

## 20. Held-count and newer-context risk

A per-system count of held candidates for a system under the campaign policy, and a national total
newer than the comparison year, can each stand for "how much happened" or "what one site produces
now". Neither is served: the zero-record sentence says the reviewed corpus is empty without a held
count, and the newer-year guard withholds the figure with a note saying how many were withheld.

## 21. UX

The first-time-reader red team found 12 things obvious, 3 findable, 0 not stated. Changes this
iteration: a phone-first order on narrow screens with the caveats line first; a plain definition of
"research preview"; a "Why no score" tab; reader-facing text stripped of document references and
iteration labels; the Gulf overview's neutral default map (geography only until a metric is chosen);
the metric definitions and accounting note (§15); the origin count on the source-health block.

## 22. Accessibility

Hover definitions are `title` attributes on existing figures and headers, so they add no new focus
stops. Headlines keep `<bdi lang dir>`; direction is now right for every right-to-left language the
data could carry. The Playwright suite's drawer, focus-return and Escape tests pass.

## 23. Performance

| Asset | Bytes | Gzipped |
|---|---|---|
| MapLibre chunk | 1,053,009 | (vendor, cached) |
| App chunk | 244,079 | |
| Index chunk | 246,480 | |
| Country view chunk (lazy) | 47,758 | |
| `global/energy_context.json` | 165,403 | 20,118 |
| `global/gulf.json` | 13,911 | 3,180 |
| `global/manifest.json` | 13,122 | 3,010 |
| `systems/us/events.json` (largest country payload) | 304,755 | 40,541 |

No payload justified a lazy split. The whole served data directory is 11 MB, dominated by the
theatre's geometry.

## 24. Tests

Release gate, on the release commit:

| Suite | Result |
|---|---|
| pytest (full) | 1,074 passed, 2 skipped |
| vitest | 275 passed (22 files) |
| TypeScript | clean |
| Vite build | succeeds |
| Playwright (local preview) | 205 passed, 1 skipped |
| Refresh-gated pytest in the next-day simulation | 1,034 passed, 4 skipped, 24 deselected |

`tests/test_iteration20.py` holds the iteration's new Python tests.

## 25. Mutations

234 mutants at release (133 at the start of the iteration). Two rounds of survivors were real test
gaps, each closed by a stronger test or a new build guard, never by deleting the mutant:

- The project's own campaign: the research-log test checked only the iteration-19 Gulf pass, not
  the iteration-20 continuation; the free-text-reason mutant was aimed at a test that did not read
  Saudi edits.
- The test-architecture red team's independent mutants (§26): 24 survived against the tree it
  started from. All 24 were ported into `scripts/mutation_campaign.py` and are caught.

Release gate: **234 mutants, 234 caught, 0 survived, 0 invalid anchors, 0 errors, 0 baselines not green.**

## 26. Red teams

Two rounds. Round two ran six perspectives: first-time reader, safety, methodology, energy analyst,
geography and language, and test architecture. All findings were acted on or turned into a matrix row:

- **Safety.** Seven of eight findings fixed (served and committed held counts, research-log counts,
  newer profile figures, gate gaps). The eighth, withheld material in history and old deployments, is
  D-34.
- **Methodology.** Holds and basis corrections in §3; re-bases and the D-27 to D-30 asymmetry in
  D-35; event totals, EEA-3, loops, mine halts and trips in D-36 to D-38; D-28 and D-29 counts
  corrected.
- **Energy analyst.** Definitions, convention, scope notes, profile figures, significance arithmetic,
  origin counting, the CAISO recovery claim its own evidence did not support, the Numaligarh value
  (crude processed, not the amount lost, now `measure: other`), the Khurais qualifier. The cause
  vocabulary gap for shortfalls is D-40.
- **Geography and language.** Items 1 to 12, 14 and 15 fixed (§17, §18); 13 is D-41.
- **Test architecture.** It wrote its own mutants in a sandbox copy and ran them with a rebuild
  between each; 24 survived. The serious ones were places where the build trusted the import: a
  campaign-covered record's headline and its review source count (the import strips and recounts
  them; the build now refuses either), an opaque id that could carry a lane's free-text middle words
  (now date and class only, in the import and in the build), and a Gulf extra metric newer than the
  comparison year (now refused by the Gulf builder). The rest were rules with no test that pinned
  them: an English-only headline or method wording on an abstracted record, the publisher and hazard
  name in the status rule, the capacity note in the facility-name check, three-letter Arabic place
  names in an address, the capacity contract's defaults, the partial-pass research clock, the recent
  list's precision and episode names, two-country recovery durations, the context's finished-year
  rule, coverage counts and name order. Each now has a test and a mutant. The agent stalled on its
  own background work before writing a final report; its findings were taken from its transcript and
  scratch results, and it was stopped.

## 27. Moving-main integration

`origin/main` stayed at `e626df2` for the whole iteration: the daily refresh did not commit while this
work ran. Every iteration-20 commit is a fast-forward of it, so nothing needed integrating; a fetch
immediately before the push confirmed it.

## 28. Production

Recorded at release.

## 29. First unattended refresh

No scheduled refresh ran during the iteration, so a simulation stood in for it, as the brief allows.
A clean worktree at the release commit, the clock moved to 13 November, and the bot's steps from
`refresh.yml`: the build succeeds with no Gulf source fetched and no research invoked (ESDI 6.58, time
decay only); the refresh-gated tests pass (1,034 passed, 4 skipped, 24 deselected); change detection
reports a substantive change; staging from the artifact contract and `verify_staged.py` pass; all
thirteen systems are retained. One note for local runs only: piping `staging_paths.py` on Windows
needs carriage returns stripped; the Linux runner is unaffected.

## 30. Remaining owner decisions

All in the matrix. The ones that most change what the site publishes: D-33 and D-11 (Saudi
harmonisation), D-35 (re-bases and the US definitions), D-36 and D-37 (event totals and EEA-3), D-34
(history), release rule A. Until each is ruled, the code runs the row's conservative behaviour.

## 31. Remaining partial lanes

Every lane of the eight Gulf systems, iteration 19 to iteration 20. "Why it stops" is the lane's own
fixed note.

| System | Lane | Iteration 19 | Iteration 20 | Queries run (20) | Stopped by | Why it stops |
|---|---|---|---|---|---|---|
| AE | AE1 | partial | partial | 10 | — | Official statements were read as carried by other publishers, not on the issuing body's own site. |
| AE | AE2 | partial | partial | 4 | — | At least one source in this lane refused automated access and was not worked around. At least one official listing is built by script in the browser and could not be read. |
| AE | AE3 | partial | partial | 4 | — | Not run as far as declared in this pass. |
| AE | AE4 | partial | partial | 17 | search_limit | The shared search allowance ran out before every declared query was run. At least one source in this lane refused automated access and was not worked around. No complete public list of events exists for this lane, so ... |
| BH | BH1 | partial | partial | 4 | search_limit | The shared search allowance ran out before every declared query was run. At least one source in this lane refused automated access and was not worked around. The listings that could be read were read in part: by title... |
| BH | BH2 | partial | partial | 4 | — | At least one source in this lane refused automated access and was not worked around. |
| BH | BH3 | partial | declared_search_complete | 15 | — | Some declared documents were not read. No complete public list of events exists for this lane, so a search that finds nothing is not a year shown to be quiet. |
| IQ | IQ1 | partial | partial | 2 | — | Some declared documents were not read. |
| IQ | IQ2 | partial | declared_search_complete | 10 | — | At least one source in this lane refused automated access and was not worked around. At least one official listing is built by script in the browser and could not be read. No complete public list of events exists for ... |
| IQ | IQ3 | partial | partial | 15 | — | At least one source in this lane refused automated access and was not worked around. |
| IQ | IQ4 | partial | declared_search_complete | 13 | — | At least one source in this lane refused automated access and was not worked around. Official statements were read as carried by other publishers, not on the issuing body's own site. No complete public list of events ... |
| IQ | IQ5 | partial | declared_search_complete | 10 | — | Some declared documents were not read. No complete public list of events exists for this lane, so a search that finds nothing is not a year shown to be quiet. |
| IR | IR1 | partial | declared_search_complete | 12 | — | At least one source in this lane refused automated access and was not worked around. The search tool gave little weight to year terms, so earlier years were reached mainly through publishers' own listings. The listing... |
| IR | IR2 | partial | declared_search_complete | 6 | — | At least one source in this lane refused automated access and was not worked around. At least one official listing is built by script in the browser and could not be read. The listings that could be read were read in ... |
| IR | IR3 | partial | partial | 12 | — | At least one source in this lane refused automated access and was not worked around. Official statements were read as carried by other publishers, not on the issuing body's own site. |
| IR | IR4 | partial | declared_search_complete | 8 | — | At least one official listing is built by script in the browser and could not be read. The listings that could be read were read in part: by title, or for their newest pages only. No complete public list of events exi... |
| IR | IR5 | partial | declared_search_complete | 10 | — | No complete public list of events exists for this lane, so a search that finds nothing is not a year shown to be quiet. |
| IR | IR6 | partial | partial | 9 | search_limit | The shared search allowance ran out before every declared query was run. At least one source in this lane refused automated access and was not worked around. No complete public list of events exists for this lane, so ... |
| KW | KW1 | partial | partial | 2 | — | At least one source in this lane refused automated access and was not worked around. At least one official listing is built by script in the browser and could not be read. |
| KW | KW2 | partial | partial | 4 | — | Not run as far as declared in this pass. |
| KW | KW3 | partial | declared_search_complete | 4 | — | The listings that could be read were read in part: by title, or for their newest pages only. No complete public list of events exists for this lane, so a search that finds nothing is not a year shown to be quiet. |
| KW | KW4 | partial | partial | 16 | search_limit | The shared search allowance ran out before every declared query was run. Some declared documents were not read. No complete public list of events exists for this lane, so a search that finds nothing is not a year show... |
| OM | OM1 | partial | partial | 2 | — | Some declared documents were not read. |
| OM | OM2 | partial | partial | 2 | — | At least one source in this lane refused automated access and was not worked around. At least one document was too large for the fetch tool or timed out. |
| OM | OM3 | partial | partial | 2 | — | At least one source in this lane refused automated access and was not worked around. |
| OM | OM4 | partial | partial | 4 | — | Not run as far as declared in this pass. |
| OM | OM5 | partial | declared_search_complete | 20 | — | At least one source in this lane refused automated access and was not worked around. The search tool gave little weight to year terms, so earlier years were reached mainly through publishers' own listings. No complete... |
| QA | QA1 | partial | partial | 4 | — | At least one official listing is built by script in the browser and could not be read. At least one document was too large for the fetch tool or timed out. Official statements were read as carried by other publishers,... |
| QA | QA2 | partial | declared_search_complete | 6 | — | At least one official listing is built by script in the browser and could not be read. No complete public list of events exists for this lane, so a search that finds nothing is not a year shown to be quiet. |
| QA | QA3 | partial | partial | 16 | search_limit | The shared search allowance ran out before every declared query was run. No complete public list of events exists for this lane, so a search that finds nothing is not a year shown to be quiet. |
| SA | SA1 | not_started | partial | 6 | search_limit | The shared search allowance ran out before every declared query was run. At least one source in this lane refused automated access and was not worked around. Official statements were read as carried by other publisher... |
| SA | SA2 | partial | partial | 2 | — | At least one source in this lane refused automated access and was not worked around. The listings that could be read were read in part: by title, or for their newest pages only. |
| SA | SA3 | partial | partial | 0 | — | At least one source in this lane refused automated access and was not worked around. |
| SA | SA4 | not_started | not_started | — | — | Not run in every language its plan requires. At least one source in this lane refused automated access and was not worked around. |
| SA | SA5 | partial | partial | 13 | search_limit | The shared search allowance ran out before every declared query was run. At least one source in this lane refused automated access and was not worked around. No complete public list of events exists for this lane, so ... |

## 32. Recommendation on adding another country

**Not yet.** The case against Wave 3 is not the length of this iteration; it is the state of the
evidence. Seven Gulf lanes stopped on the search allowance, two Saudi lanes are not complete, five
Gulf systems have no record and cannot yet say whether that reflects the country or the search, and
eight owner rows decide whether about twenty published records stand. A new country would inherit
every one of those questions. Iteration 21 should finish the declared Gulf query sets, take the
owner's rulings on D-33, D-35 to D-37 and release rule A, and re-run the link check on the final
corpus. Wave 3 is ready to plan once the Gulf lanes are complete or stopped for a reason other than
the allowance.
