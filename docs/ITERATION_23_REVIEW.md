# Iteration 23 review: map-first navigation, a Help Center, and a methodology adversary

<!-- status: in-progress -->

Iteration 22 added new kinds of evidence. Iteration 23 adds no data source and no country: it makes
the world map the way in, moves the teaching out of the home page into a Help Center, and turns seven
red teams on the methodology and its implementation. Everything a red team found that broke an
existing rule was fixed; everything that would change analytical meaning is an owner memo, not code.

Every reviewer named here is a Claude agent. A Claude agent is not an outside human reviewer, and
nothing in this iteration stands in for one. Figures below are dated; live figures are in
[CURRENT_STATE.md](CURRENT_STATE.md).

## 0. Baseline

| | |
|---|---|
| Iteration 22 release | `45458c5` deployed 20 November 2026; CI failed six phone-layout tests under the runner's wider font; fixed in `5b06c05`; release documentation `8f17610`. CI green, production serving `8f17610`, all 71 data files byte-identical to the commit |
| Branch | `iteration-23`, from released `main` (`8f17610`); iteration-23 work began in scratch clones on `45458c5` and was merged in |
| Tests at the iteration-22 release | pytest 1924 passed, 2 skipped; vitest 701; Playwright 512; mutation campaign 829 of 829 caught |
| Theatre | ESDI 5.87 (20 Nov build), 184 events |

## 1. Product problem

The home page was an instrument panel. At 1440x900 it showed 25 controls above the fold (11 at 390
px), about 3,500 words and five `<select>` elements (measured on the iteration-22 build by UX
designer A). The world map was context, not navigation: a click on a monitored country did not open
it. Teaching was in three places (a glossary dialog, "How to read this", "How this works"), none of
them linkable. A reader could not answer "where do I click to see Iran?" from the first screen.

## 2. UX research

Three agent designers built competing clickable prototypes against the iteration-22 build:

| | Direction | Words on load | Verdict |
|---|---|---|---|
| A | The map is the page; everything else gets out of the way | ~476 | Text route below a full-screen map; a lightness ladder in the fill reads as severity |
| B | Map beside (desktop) or above (phone) a concise panel of the thirteen systems, the Gulf group and the Atlas | ~360 | **Selected** |
| C | Search first, with a map you can choose from | ~370 | Search-first where the owner asked map-first |

A fresh judge agent scored them and chose B: the only design where the map leads and its text
equivalent sits beside it on the first screen, where the map encodes only what one click does, and
where navigation still works if the map library is slow or fails. B took exactly three items from the
others, as the directive required (no merging of all three): C's Back-restores-selection mechanism
instead of a new `?sel=` parameter (existing URLs unchanged), A's flat alphabetical list of country
systems with Gulf membership as a quiet tag, and C's search-option wording ("France — impact records
available · not a monitored country system").

## 3. Map-first navigation

What a click does on the default map ("Where to explore"):

| Place | Result |
|---|---|
| A monitored country system | Its page, in one click; Bahrain, Qatar and Kuwait, too small to click at world zoom, carry a fixed-size dot in the same neutral colour; overlapping dots offer an alphabetical choice |
| The theatre (Russia, Belarus, Crimea) | The theatre; Crimea and Sevastopol have their own hatch and read "Ukrainian territory under Russian occupation · monitored as a separate unit"; the other occupied oblasts read as Ukraine |
| A country with impact records only | A card: "Impact records available · Not a monitored country system", with a button to the Impact Atlas filtered to that country |
| A country with neither | A card that says the site has not searched it, so nothing here says whether disruptions happened; no button, no dashboard |
| Eastern Russia | "Outside the monitored area"; Russia chosen from the list or search reads "Partly monitored, in the Russia, Belarus & Crimea theatre" |

The selection lives in the home's own history entry, so no URL parameter was added and Back restores
the selection with focus on the card. Routing reads only served public files (manifest, world map,
the manifest's impact-presence field); the home never loads the impact corpus or a candidate queue
(map red team R10).

## 4. World-map interaction

Two modes. The default colours only what one click does (monitored system, Crimea's occupied hatch,
base). National energy context is the second mode, unchanged in meaning: one source, one year,
national only, never monitoring. Hover cards carry names and status, never a count (map red team R6:
no digit in 30+ hover labels, titles or accessible names). On a phone a tap shows a sheet before
opening a system (the documented fat-finger rule); "Show on map" scrolls the map into view.

## 5. Regional navigation

The Gulf littoral is the only regional view (`?group=gulf`), one row in the panel with its members
and "Show on map". `?group=gcc` and `?group=opec` say "not found". The Gulf map draws countries only:
no facility, route, strait or incident point.

## 6. Home simplification

| | |
|---|---|
| Removed from the home | Start here (now in Help); the system picker; the second "Find a country" box; the world map card's false "no disruption record" for impact-record countries; the national-figures prefetch (165 KB) |
| Moved below the map, collapsed | Recent evidence, What's new, data quality, why these systems, the country record (recovery and review sub-totals dropped, each system's reporting environment stated instead of a count comparison), the national figures table |
| Kept on the first screen | The map, "Where to explore" (the theatre with its headline, the Impact Atlas, the Gulf littoral row, the twelve country systems, Compare, every country A to Z), search |

## 7. Search and fallback navigation

One search finds every world country, every system, every theatre region (Sevastopol finds the
Crimea unit) and every Help section by plain words (export, csv, reviewer, coordinates, percentage,
corrections…). A match inside a word appears only when nothing matches at the start of one ("review"
no longer finds only "Research preview"). The A–Z list is one vertical column of all 242 countries
on the map. Every action is reachable without the map.

## 8. Help Center

`?view=help#<anchor>`, lazily loaded, replacing the glossary dialog, "How to read this" and "How this
works". Sections: start-here, how-it-works, navigating-the-map, what-to-click, product-types, esdi,
recovery, why-no-country-score, impact-records, evidence-confidence, attribution, ai-involvement,
research-coverage, source-health, whats-new, history, gulf-context, cyber, absence, withheld,
exports, do-not-infer, glossary. Live values come from `global/help_facts.json`, built from the
payloads, so Help never quotes a number by hand (tested). Evidence Confidence is shown as
`2.0-draft`, provisional, with calibration run 1 performed and failed. Deep links land on the heading
with focus; Back and Forward restore position (first-time-user red team: all sections and 34
glossary entries checked).

## 9. Contextual help

"Learn more" links open the right Help section from the theatre headline, recovery, evidence
confidence, exports, Compare and the Evidence Inspector. On a phone, where the theatre header is
height-capped, the links sit inside the expandable panel. Under every list of theatre events a line
says how those records were checked (not the three-role review), with a Learn more.

## 10. Mobile

CI's Linux runner draws DejaVu Sans, wider than this machine's fonts; a phone layout that fit locally
overflowed there (the iteration-22 CI failure). Every first-screen phone check now also runs with a
wide-font style (`WIDE_FONT`), and it caught two iteration-23 regressions before CI did. Phone
sideways scrollers carry an edge fade. Measured map tops at 390x844 in the wide font, iteration-23
build: UAE 679, Bahrain 666, Oman 663, Kuwait 631, Iran 627, home 346 (limit 694).

## 11. Accessibility

Choosing a country from the A–Z list or search, or returning to a restored card with Back, moves
focus to the card heading (it had stayed on the list item, 96 Shift+Tab presses from the card's
button). Escape closes the card before anything behind it. Help has one H1 and no skipped heading
levels; keyboard order is skip link, header, contents, section. Keyboard-only paths have e2e tests.
Not verified: real screen-reader output and real touch hardware.

## 12. Methodology adversary

Seven agent red teams (ESDI, conceptual validity, cross-layer and history, thresholds and
attribution, implementation contract, Evidence Confidence, information architecture), each working
on repo copies and served bytes: 137 findings. Every one is classified and dispositioned in
[METHODOLOGY_RED_TEAM_23.md](METHODOLOGY_RED_TEAM_23.md), with fifteen owner memos; the eleven
concepts by six layers, with the test behind each cell, are in
[METHODOLOGY_CONSISTENCY_MATRIX_23.md](METHODOLOGY_CONSISTENCY_MATRIX_23.md). Three product red teams
followed on the integrated build (first-time user and Help, map-first navigation, expert analyst
with a screenshot review), then a final methodology and a final test-architecture red team (§24).

## 13. ESDI findings

No scoring change. The headline is mostly a decay assumption (the modelled horizons move it far more
than any other choice: 1.65 to 13.76 at the red-team run), refining carries most of it, and the
confidence multiplier is nearly constant. Fixed: the ribbon and Recovery tab say "still in the index,
no full-restoration report by the cut-off", not "no restoration report" (six of those facilities
carry a report); the horizon sweep is shown where the headline is explained; the headline copy names
the transmission event count beside the capacity shares; nulls instead of zeros for uncovered sectors
and zero denominators; the coverage ratio's numerator is clipped to its benchmark's window (153/305
became 116/305); the ribbon's peak is labelled as the peak of a weekly reconstruction; Help says the
index is not a percentage. Owner memos M1–M4 (refinery horizon and basis, sector composition,
aggregation and weights, confidence v1 and damage severity).

## 14. Country-system methodology findings

Inclusion clauses rank procedure above physical severity in places (T-A1), Evidence Confidence on
country records cannot reach High (C3, AN-14), and the "research preview" cohort is hand-set (C2):
owner memos M5–M7. Fixed: eight US records whose figures came only from Wikipedia and one Canadian
record whose provincial figure did are held for re-sourcing (primary figures were found for most and
several differ); the build now refuses an encyclopedia named as a source in any country record; the
Wipha record is held under the D-36 interim practice; each affected country's research log states
the re-reading and how many were held.

## 15. Impact-layer findings

Fixed through the review queue: relays joined into one origin on six records; the Ghana dispute is
about the effect; four records that meet no inclusion basis (one island outage, one airport, two
single hospitals) held; three re-based; a Ukrainian abstracted record lost two late citations. New
gate rules: an abstracted record states no duration and cites nothing dated more than seven days
after the event; basis 4 needs a national or regional scope; a context entry's `as_of` cannot follow
its date; a lead correction carries its own date. Owner memos M8 (no-widening per rule, not per
event) and M9 (inclusion bases).

## 16. ECI findings

Evidence Confidence stays `2.0-draft`. The theatre multiplier stays v1. Fixed: "provisional method"
beside every category; no total of points in "Why?"; components not earned read "not recorded" or
"not counted"; wire names match whole words; first-party roles come from the method's direct tier;
the served status says calibration run 1 was performed and did not pass. Not applied: retyping four
official accounts from S2 to S1 (a public-source check established officiality from the
organisation's own site for none of the four): memo M15. Calibration bar: memo M13.

## 17. Attribution findings

The gate accepts suspected, assessed and attributed alike for a government source, and descriptors
("unidentified perpetrators", "a Russia-based group (not named)") are served as actor names (T-C1,
T-C7). Replacing a descriptor with no actor would change the attribution status, which lead
normalisation may not do: memo M10 (an attribution-instrument field). The theatre's
Confirmed/Probable/Possible labels are now defined in Help as the older method, not comparable with
Evidence Confidence.

## 18. History findings

Three backfill rules disagreed (theatre, country, impact); What's New called a month historical
before it ended and ignored observed end dates; `first_published` is hand-stamped. Fixed: the month
rule, the observed end, the context first-publication sentence, and **What's New is now built after
the impact layer** (AN-01): built before it, it compared the previous run's impact files, so the four
impact records this iteration withdrew were not reported. Production-history mutants H-M1, H-M3,
H-M4 and H-M11 are now killed.

## 19. UX-semantic findings

The map card said "no disruption record … not searched" for impact-record countries (gone); the
build date read "Data as of" (now "Built"); Compare's "Record as of" showed the build date (now
"Record reviewed", or "No qualifying record yet"); a home sentence compared record counts across
countries and was false (gone); a campaign page said both that candidates remain under review and
that whether any are under review is withheld (one rule now: how many is withheld); the Gulf card
misstated Bahrain's placement; first screens said "reviewed impact records" for countries with none;
the theatre "cannot tell you" list called a model count a reporting fact.

## 20. Implementation-contract findings

Origin grouping was implemented three times with different first-party roles (now one source); the
impact gate did not check that a region code belonged to the record's country (now refused);
documents claimed rules the code did not enforce (scoped to what the gate does); a US threshold-basis
fix had been made in a curated file a re-import would revert (moved into `review_edits.json`); a lead
correction restamped every record in its lane file (now dated per verdict).

## 21. Bugs fixed

| ID | Fix | Commit |
|---|---|---|
| CI (i22) | Phone country overview fits the first screen in a wide font | `5b06c05` |
| ESDI-03, C1, F8, ESDI-02/07, C6, XL-12 | Theatre copy and served fields say what each number counts | `ca5f75a`, `f0b5083` |
| F3, F4, F5, F11, ECI-06, ECI-14, XL-02, XL-04, XL-05, T-A8 | Impact and ECI pipeline fixes | `f30293d` |
| C10, C11, F2, F13, F14, XL-01, XL-08, T-A7 | Evidence confidence and country pages | `25d3b5b` |
| XL-15, T-B2, XL-01 gate | Gate rules behind the record corrections | `a624ec7` |
| ECI-01, ECI-07, T-B2, T-B3, T-A6, C5, F12, XL-01, XL-15 | Record corrections through the queue | `c09919e` |
| H-01 | "Cannot tell you" model count | `7f50fe0` |
| AN-01, AN-05, AN-06, AN-12, AN-13 | What's New order; encyclopedia rule; held-record disclosure | `813e1ad` |
| H-02–H-11, MU-01–MU-07, AN-03–AN-11, V-01–V-10 | Help, search, map reach and focus, country and Gulf wording | `a693aa6`, `e4a651f` |

## 22. Methodology weaknesses not changed

Each has an owner memo in METHODOLOGY_RED_TEAM_23.md §4 and is unchanged in code: the refinery
horizon and refining basis; transmission's unitless count in the headline; the max-per-facility
rule and sector weights; confidence v1's near-constant multiplier and damage severity scoring
unknown above degraded; the hand-set research-preview cohort; country Evidence Confidence's
Moderate cap; inclusion clauses; no-widening per event rather than per rule; inclusion bases 1, 5 and
6 drift; attribution formality; observed-only end dates in country systems; theatre and impact-layer
reconciliation; the ECI calibration bar and components; comparison surfaces; the S1/S2 gap for
unproven official accounts.

## 23. Owner decisions

Standing, unchanged: Saudi harmonisation (Option B stays; the production red team's only
blocker-level item, not new), D-34 to D-37, Release Rule A, the impact-layer threshold override,
banking/payments/tax/heavy-industry scope, Baltic subsea.

New, none implemented:

| Memo | Question |
|---|---|
| M1–M15 | METHODOLOGY_RED_TEAM_23.md §4 |
| P1 Error reporting | There is no route to report an error. (a) a Help section pointing to the repository's issue tracker; (b) state that corrections come only from scheduled re-checks; (c) a per-record report link that collects no personal data |
| P2 Hormuz shares | The Gulf & Hormuz context includes the strait's share of world seaborne oil trade, the standard statement of a chokepoint's importance, and an authority's dated "virtually closed". Within the iteration-22 rule. (a) keep; (b) drop throughput-share figures; (c) rename the tab "Gulf regional context" |
| P3 Gulf phone header | Gulf country pages shift by 0.18 on a phone when the breadcrumb gains its group crumb (§26). Delay the header until the manifest loads, or give every phone page a two-row header |
| P4 Held-record counts in What's New | What's New caps lists and never counts the remainder ("capped and flagged, never counted"); a reader asked how many were held. Add a count field, or keep the rule |

## 24. Tests

PENDING: final gate totals (pytest, tsc, vitest, Vite, Playwright) on the release tree; the final
methodology red team; the final test-architecture red team (real mutant survivors only).

## 25. Mutations

PENDING: complete campaign on the release tree. The campaign holds 988 mutants (829 at the iteration-22
release; iteration 23 added theatre, help, impact, home, record-correction and fix lists). Every
iteration-23 list ran to zero survivors in its own clone; the merged anchors validate.

## 26. Performance

Single cold loads, local static server, Chromium; iteration-22 release build against the iteration-23
build after the record corrections.

| Home | 1440x900 | 390x844 |
|---|---|---|
| Bytes loaded | 2661 → 2434 kB | 2661 → 2434 kB |
| Data loaded | 688 → 453 kB (19 → 16 requests) | same |
| Map ready (median of three) | 1265 → 1085 ms | 1205 → 877 ms |
| JS heap | 20 → 18 MB | 17 → 12 MB |
| CLS | 0 → 0 | 0 → 0.015 |
| LCP | 216 → 440 ms (the map is now the largest first-screen element) | 112 → 152 ms |

A decluttered home that is lighter on every load measure. Total JS +5% (Help, home panel), loaded
lazily. Pre-existing and not fixed: Gulf country pages on a phone shift by 0.182 in both builds when
the breadcrumb gains its "Gulf littoral" crumb and wraps (owner item P3).

## 27. Moving-main integration

PENDING.

## 28. CI

PENDING.

## 29. Production

PENDING.

## 30. Remaining limitations

- Every reviewer is a Claude agent; no outside human reviewed the corpus or the methodology.
- The record corrections were applied by the lead and checked by the gates and tests; no blind
  reviewer re-read them.
- Held records await re-sourcing and re-review; until then the US Helene, Francine and Fern episodes
  and the Fiona record are incomplete, and the research logs say so.
- Japan and an Iranian water record may carry undeclared relays (need a reviewer).
- Real screen readers, real touch hardware, Firefox and Safari were not tested.
- On a phone, with the theatre's "Sector scores & recovery" panel open, the map legend can overlap
  the scope note, which is taller now that its Crimea sentence never folds away (V-01).
- The theatre strike table cites bare home pages in a few incidents (from the source table); the
  confidence labels they feed are memo M4.

## 31. Recommended iteration 24

1. Owner decisions M1–M15 and P1–P4, starting with the ones that block nothing else: P1 error
   reporting, M15 social tier, M10 attribution instrument, M5 cohort flag.
2. Re-source and re-review the held US, Canadian and Chinese records; a reviewer for the two
   undeclared-relay candidates.
3. A human-labelled Evidence Confidence calibration run (M13), the only route out of `2.0-draft`.
4. A screen-reader and real-device accessibility pass.
5. No new country, per the iteration-23 directive's own doctrine.

## Findings table (serious findings)

| ID | Layer | Finding | Classification | Evidence | User impact | Action | Owner decision? |
|---|---|---|---|---|---|---|---|
| AN-01 | What's New | Built before the impact layer; impact changes on release day unreported | BUG | `pipeline/run.py` order; this release's four withdrawals missing | A correction looks like nothing happened | Fixed `813e1ad` | No |
| C5 / AN-05 | Country | Figures resting only on Wikipedia; text naming it as a source | BUG | 8 US + 1 CA records; DOE and state primaries differ | A cited figure is wrong | Held; build rule | No |
| ESDI-03 / H-01 | Theatre | A model count presented as "no restoration report" | UX MISREPRESENTATION | `recovery_stats` definition vs served text | Reads as a reporting fact | Fixed | No |
| C1 | Theatre | Coverage ratio mixes windows | BUG | 153/305 vs window-matched 116/305 | Overstated coverage | Fixed | No |
| F8 | Theatre | Zero where the denominator is absent | BUG | `_pct` 0.0; Crimea "0 MW" | Unknown read as measured nothing | Fixed (null) | No |
| T-B2 | Impact | Basis 4 claimed for local services | BUG | four records | Inclusion overstated | Held; gate | No |
| XL-15 | Impact | Late citations on abstracted records | BUG | +8 and +12 day citations | Later status could publish | Fixed; gate | No |
| XL-01 | Context | `as_of` after `date`; "listed above" false | BUG | UKMTO entry | Wrong "latest" card | Fixed; gate | No |
| ECI-01 | ECI | Declared relays not joined | BUG | 3 records High that the rule makes Moderate | Confidence overstated | Fixed (queue) | No |
| MU-01 | Map | Bahrain unclickable at world zoom | UX MISREPRESENTATION | grid probe | A monitored system looks unmonitored | Neutral dot | No |
| MU-03 | Map | Focus stranded after list or search choice | BUG (a11y) | 96 Shift+Tab | Keyboard users lost | Focus to card | No |
| H-03 | Help | Search could not find Help topics | UX MISREPRESENTATION | 20 terms with no match | Help unreachable by search | Sections indexed | No |
| AN-03 | Home | Cross-country count comparison, false | UX MISREPRESENTATION | India 8 = China 8 | Invites ranking | Removed | No |
| AN-04 | Country | Two contradictory statements on held candidates | UX MISREPRESENTATION | UAE first screen | Undermines trust | One rule | No |
| ESDI-01 | Theatre | Refinery horizon 150 d vs own median 47 d | METHODOLOGY WEAKNESS | 1.25 vs 5.87 at 47 d | Headline rests on an assumption | Memo M1 | Yes |
| C3 / AN-14 | Country | ECI capped at Moderate on country records | METHODOLOGY WEAKNESS | 166/166 ≤ Moderate | Same score reads differently | Memo M6 | Yes |
| XL-07 / T-B7 | Impact | No-widening per event, not per rule | METHODOLOGY WEAKNESS | Iran: 15 impact records, 0 system records | Layers can disagree | Memo M8 | Yes |
| T-C1 / T-C7 | Attribution | Status encodes belief, not formality; descriptors as actors | METHODOLOGY WEAKNESS | CERT-UA notices, minister speech | Attribution overstated | Memo M10 | Yes |
| ECI-10 | ECI | Unproven official accounts fit neither S1 nor S2 | METHODOLOGY WEAKNESS | public-source check | Under- or overstatement | Memo M15 | Yes |
| H-04 | Product | No route to report an error | OWNER DECISION | Help, site | Corrections depend on re-checks | Memo P1 | Yes |
| MU-08 | Gulf | Strait trade-share figures | OWNER DECISION | regional context | Reads as chokepoint importance | Memo P2 | Yes |
