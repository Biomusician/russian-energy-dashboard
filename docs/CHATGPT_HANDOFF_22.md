# Handoff to ChatGPT: iteration 22, what is left

This is a working brief for a ChatGPT conversation that continues iteration 22 of the Energy
Disruption Monitor alongside Claude Code. It is self-contained: read it all before starting. Claude
Code owns the repository, the machine, the builds and every release step; ChatGPT's part is review,
red-teaming, research planning and drafting, returned in the formats at the end so Claude Code can
apply it through the project's own gates.

## 1. What the project is (one paragraph)

An open-source-only dashboard of publicly reported disruption to energy and essential civilian
infrastructure. Its main product is calibrated honesty about what is and is not known: it never
presents an estimate as an observation, and it keeps "unknown", "not applicable" and "not yet
researched" distinct. It monitors 13 systems (a Russia/Belarus/Crimea theatre with an exposure
index; 12 country systems with no score). Iteration 22 adds a separate, non-scored **impact layer**.

## 2. The hard limits (binding on everything you write)

This is never a targeting or operational tool. Never produce, suggest or infer: target rankings;
criticality, importance or vulnerability of any asset; weak points; dependence of anything on a
facility or route; chokepoint exploitation; alternate routes or bypass capacity; vessel names,
positions, lists, tracking or counts that read as monitoring; the current operating, repair or
restart status or remaining capacity of anything reported attacked; coordinates or any place finer
than a first-level region; weapon or method detail; IP addresses, CVEs, device makes or models,
protocols, access methods, credentials, exploit chains, malware or tool names outside an
attribution statement; personal data. In Iran, Iraq, Kuwait, Saudi Arabia, Bahrain, Qatar, the UAE
and Oman no record carries a province, city, plant, facility, port, field or operator below a
national body. Every kinetic or sabotage record anywhere is published at country level only, with
no place, operator, method, headline or later status. Public, open, unclassified sources only; no
logins, no private groups. If a task seems to need anything beyond this, say so and stop.

## 3. State on 19 November 2026

- **Branch `iteration-22`, local only, not pushed.** Production still serves iteration 21.
- **Impact corpus:** 245 records (237 disruptions, 8 attempts with no service effect), 77 country
  codes, January 2022 to November 2026; every record accepted by three blind reviewers (evidence;
  attribution and source; safety). Cause: cyber 78, technical failure 70, natural hazard 39, supply
  shortfall 34, unknown 9, ordered by an authority 6, kinetic 3, sabotage 3, civil disruption 3.
  Sector: electricity 126, telecom 30, fuel supply 17, healthcare 17, transport 16, water 14,
  municipal 12, oil and gas 7, district energy 5, desalination 1. 59 social sources on 36 records.
  AI-involved records: 0.
- **Regional context:** 35 dated, sourced, aggregate statements on the Gulf and the Strait of
  Hormuz (1 March to 19 November 2026), from EIA, IMO, IEA, UNCTAD, FAO, METI, the UN and wires.
- **Evidence Confidence v2:** served on every record (High 114, Moderate 121, Limited 4, Preliminary
  5, Disputed 1 on impact records). A methodology red team's five blockers were fixed. The first blind
  calibration **failed** (two labelers: kappa 0.73 with each other, 0.02 and 0.11 with the model), so
  the thresholds are provisional and the theatre's scoring multiplier is unchanged.
- **Tests:** green on the branch; totals in `docs/ITERATION_22_REVIEW.md` §28 and §29.
- **Not done, and the reason release is held:** four content red teams (below) were stopped by a
  usage limit before they reported. Also not done: link check on the new corpus, next-day refresh
  simulation, merge with the moving `origin/main`, the UX red teams.

## 4. What ChatGPT cannot see, and how to give it

The branch is not on GitHub, and the review queue (`data/candidates/`) is never published. To work
on a package below, the user attaches the files it names from the local checkout
`C:\Users\Jonathan\Russian Energy Dashboard` (branch `iteration-22`). The served files contain no
withheld material by design; the review queue does, and must not be uploaded anywhere.

Core attachments for most packages:

- `data/processed/global/impacts.json` (the served impact corpus, 1.2 MB)
- `data/processed/global/regional_context.json`, `data/processed/global/evidence_confidence.json`,
  `data/processed/global/gulf.json`
- `docs/GLOBAL_IMPACT_METHODOLOGY.md`, `docs/EVIDENCE_CONFIDENCE_V2.md`,
  `docs/ITERATION_22_REVIEW.md`, `CLAUDE.md`

## 5. Work packages, in priority order

### WP1. Content red teams on the served bytes (release blockers)

Four independent passes. Each reads the attached served files only, cites `impact_id` and the field
path for every finding, and grades BLOCKER (must fix before publication), SHOULD FIX or NOTE.

1. **Iran, Gulf and Hormuz safety.** For every record whose `country_a3` is one of the eight Gulf
   states: any sub-national place, facility, field, port, cable, sea, route or operator below a
   national body in any text, id, source title, URL host, path or query (check transliterated
   Persian and Arabic slugs). For every `country_abstracted` record: can the place or facility be
   recovered from date + country + sector + technology + effect + URLs? Any later-status wording?
   For every context entry: vessel names, counts that read as monitoring, positions, routes,
   bypass capacity, dependence, naval movements, a single open/closed status, a forecast shown as
   fact, a figure with no stated basis. Nine entries use "ships" or "vessels" in an authority's
   aggregate words (IMO on stranded seafarers and attacks on commercial shipping, UNCTAD on a fall in
   transits, a UN briefing citing an IMO incident count). Methodology §10 allows that; judge whether
   any of them reads as vessel monitoring, and whether an incident or transit figure should stay. Could the Gulf records and context together rank countries
   or facilities by importance? The lead's own sweep found no blocker; it was a script, not a reader.
2. **Cyber safety and exports.** Every string of every record for technical detail beyond "who
   announced it, which service, how long, the broad mechanism, who attributed it to whom": IPs, CVEs,
   AS numbers of a named victim, protocols, devices, vendor products, malware and ransomware strain
   names outside `attribution`, access method, sequence of actions, set-points. Titles and URL slugs
   especially. Victim naming resting only on an attacker's leak site. Attempts that read as a list
   of who was probed and survived. Patient or personal data.
3. **Attribution, AI and social claims.** The 47 records whose attribution is not NOT_APPLICABLE or
   UNKNOWN: does `status` say more than the sources (a claim shown as an assessment; one vendor's
   "likely" as ASSESSED; "state" where sources say "linked to"; a victim government's accusation shown
   as formal attribution without saying so)? Prose attribution that bypasses the block. The zero AI
   count: honest in both directions? The 59 social sources: tier against `identity_basis`, `origin`
   (an organisation's post and its website must count once), any S4 source, any reproduced post text.
4. **Energy analyst and multilingual.** Units (customers vs people vs households vs MW), qualifiers
   against `source_says`, restored counts shown as affected, prospective figures shown as outcomes,
   end dates that were plans, causes the authority did not state, Persian calendar conversions,
   `title_en` against `title_original`, suspected duplicates across the corpus, and what a specialist
   would call conspicuously missing (for the limitations section, not for research now).

Return format: §6.

### WP2. Calibration run 2 design (no code)

Design a second blind calibration that could actually carry the thresholds: imported (reviewed)
records only, at least three labelers including at least one person outside the build, a kappa floor
stated before labels are read, and written rules for the two cases run 1 exposed ("a denial later
superseded", "a figure disputed inside one source"). Draft the reviewer instructions in plain words
without the model's rubric (EVIDENCE_CONFIDENCE_V2.md §6 says what a packet may and may not hold).

### WP3. Owner decision memos

Short memos the owner can rule on, each with the options, what each changes in the product, and a
recommendation (ITERATION_22_REVIEW.md §34): held country records and the impact layer (39 matches
refused under the no-override rule); sectors outside the list (banking, payments, tax platforms,
heavy industry); Baltic subsea cables and pipelines; releasing without the content red teams; the
bar for dropping `-draft`.

### WP4. Research plan for the next pass (no searching yet)

For each gap in review §23 and §35 (Gulf desalination and water; CISA, EPA, HC3, CERT-UA and NERC
archives end to end; a healthcare backfill; Central Asia second origins; Persian and Arabic official
statements), name the public archive, the query pattern and what would count as a qualifying record
under methodology §3. Nothing on attacked-facility recovery; nothing below first-level region in the
Gulf states.

### WP5. First-time-user review (from screenshots)

If the user shares screenshots of the Impact Atlas (`?view=impacts`), the Gulf page
(`?group=gulf`, every section) and Iran's country page (`?sys=ir`), try the 15 tasks in the brief's
first-time-user list (a country's impact brief is the button at the top of its impacts tab) and report where a reader would misread a count as a rate or ranking, a
confidence category as a probability, an aggregate statement as a current status, or "no record" as
"nothing happened".

## 6. How to hand results back to Claude Code

Claude Code applies nothing directly to data: corrections go through the review queue and the
import gate. Return one of these:

- **Findings list (markdown):** numbered; severity; `impact_id` or context `id`; field path; what
  it says; what the source or rule says; the fix.
- **Corrections (JSON), for records:** `{"<impact_id>": {"reason": "...", "set": {"<field path>":
  <value>}, "remove_sources": ["s3"]}}`. Field paths are dotted, list items by index
  (`civilian_service_impact[0].affected.qualifier`) and sources by ref (`sources[s2].title_en`).
  Claude Code maps served ids back to filed candidates and applies these as a review pass.
- **Holds:** `{"<impact_id>": "reason"}` for any record that should not be published at all.

Never include in a reply anything the rules in §2 forbid, even to explain a finding: describe a leak
generically ("the URL path names the facility") and give the id and field path.

## 7. What Claude Code will do after your packages

Apply corrections and holds; re-import; rebuild; run the link check and the next-day refresh
simulation; merge `origin/main`; run the full gate (pytest, TypeScript, vitest, Playwright, the
mutation campaign); push; watch CI; verify production (served bytes, safety scan, Atlas, Iran, Gulf,
phones); then mark iteration 22 released and bump the iteration markers.
