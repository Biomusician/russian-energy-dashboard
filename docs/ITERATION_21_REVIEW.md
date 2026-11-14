# Iteration 21 review: from instrument to product

<!-- status: in-progress -->

Iteration 21 added no country, no score and no new kind of data. It turned the dashboard into a
product people can use: one first screen that says what the site is and what to open next, search,
navigation that always leads home, a safe comparison workspace, a research-coverage explorer, a
per-record evidence inspector, a "what's new" panel, a redesigned Gulf overview and Russia theatre
header, error containment per view and per panel, and a mobile and accessibility pass. Live figures
are in [CURRENT_STATE.md](CURRENT_STATE.md), which the build regenerates; none is re-quoted here
except where a figure is the point of a finding.

**The short version.**

<!-- LEAD: fill at release -->

---

## 0. Baseline

| | |
|---|---|
| Start commit | `51eb9c6` (iteration-20 release) locally; origin/main at `5b68a82` (the daily refresh of 12 November), fast-forwarded |
| First commits of the iteration | `3713096` (export caveats found by iteration-20 production QA) and `94620d4` (iteration-20 review §28) |
| Systems | 13: the Russia theatre (index) and 12 country systems (no score), unchanged |
| Mutation campaign at start | 234 mutants |
| First-time-user baseline | production, before any change (§2) |

## 1. Product strategy

The site's job is unchanged: calibrated honesty about what is and is not known, with a good map. The
iteration-20 product did that job for a reader who already knew how to read it. A first-time reader
met thirteen near-identical cards, the only indexed system tenth in alphabetical order, internal
vocabulary, hover-only definitions and no way home.

The strategy was therefore to make the existing honesty legible, not to add claims:

- **Answer "what should I open next?" on the first screen**, without ordering anything by a figure.
  The theatre leads because it is a different kind of system (the only one with an index), the
  countries follow in alphabetical order.
- **Make every distinction visible where it is used**: research coverage versus source health,
  observed versus modelled, unknown versus not applicable versus not yet researched, no index versus
  zero, "no qualifying record" versus "no disruption".
- **Let readers do analyst tasks**: compare systems on the dimensions that mean the same thing
  everywhere, inspect one record's evidence, cite it with a stable link, export a self-explaining
  image.
- **Keep every safety rule on every new surface.** Each new view was built under the campaign policy
  and then attacked by a safety red team (§24).

Eight features were built in parallel in separate checkouts and integrated deliberately (§27), then
six red teams and fix passes ran against the integrated tree.

## 2. User research and baseline usability

A first-time-user pass ran against production before any change: 20 tasks a new reader should be
able to do, each scored OBVIOUS, FINDABLE, NOT STATED or MISLEADING.

| Result | Tasks |
|---|---|
| Obvious | 6 |
| Findable | 12 |
| Not stated | 1 — "what should I click next?" |
| Misleading | 1 — the theatre's Recent tab |

The misleading one was the most serious finding of the iteration. The Recent tab printed a modelled
"Impaired · impaired 33 d · modelled horizon ~100 d" chip beside "Current facility status withheld
during active campaign", and the reader concluded that the site shows facility status. It does not:
the chip was the index's own decay model, rendered per facility. It is fixed (§9).

The other findings, routed to the feature that owned the surface:

1. The flagship was buried and nothing said what to do next (§3).
2. The headline read 6.7 on cards and 6.69 in the explanation, with no scale (§9).
3. Internal vocabulary reached readers: iteration numbers, file names, "search allowance", Saudi
   Arabia's "open decision" (§7, §8).
4. The theatre ribbon was cramped and scrolled sideways; per-sector cells were zero pixels wide (§9).
5. The theatre on a phone: truncated selector, clipped headline, legend over the attribution (§9, §13).
6. Clicking a dossier tab at 1440 px slid the whole app 400 px left (§9).
7. A black screen while loading; the world map captured the mouse wheel (§3, §15).
8. No way home, three names for the theatre, a stale tab title (§4, §9).
9. Definitions only on hover, which a touch screen does not have; a zero-record country carried the
   badge "Reported events, no index"; Bahrain offered a region filter that could filter nothing (§3, §7).
10. A monolithic methodology with a broken sentence (§9).
11. Feeds padded with one identical safeguard line per record; the Gulf map opened grey and read as
    broken (§3, §8).

The pass was repeated on the final build (§22).

## 3. Global home

The first screen now answers "what is this and what do I open next?" without ordering anything by a
figure.

- **First screen:** product name, a one-line purpose, the search box and three actions (Explore the
  Gulf littoral, Compare systems, Russia, Belarus & Crimea). A fourth action, "Search systems", was
  removed after the second first-time-user pass: the search box above it already searches. The
  comparability note stays visible in a compact form.
- **Start here:** six points and "What to open next". It can be dismissed; the choice is kept in
  browser storage behind a try/catch, so a private window or blocked storage still renders it. It
  does not take focus on a first visit (§14).
- **The indexed system leads** in its own entry, "the only one with a score", with what the score
  means and the sentence "Built for this area alone. No country below has an index". It leads
  because it is a different kind of system, not because of its value. Country cards follow in
  manifest (alphabetical) order and are never re-sorted.
- **Cards:** "No index" in words, neutral shape-coded tags (research preview, Gulf littoral,
  publication safeguards) that open by tap or click rather than hover, the date the newest published
  record was reviewed or "No qualifying records yet", the last systematic research pass and the
  reporting environment. The amber readiness badge, which read as a warning, is gone. Ages are
  computed on the reader's calendar, so a UTC build date no longer reads as tomorrow.
- **Recent published evidence:** date, country link, class, cause and placement; no effect text.
  Consecutive campaign-covered rows of one country fold into one line with no count. One line says
  "Newest is not worst, and a country with no item here is not a quiet country", and the list now
  says how it is sorted (latest date of an episode).
- **Data quality** became separate plain questions: when the site was rebuilt, when sources were
  re-checked, how complete research is, observed versus modelled, what is withheld, whether
  countries can be compared, how old the national context is.
- **Pipeline:** manifest country entries carry `record_reviewed` (a date, or null when there is no
  record).

## 4. Navigation and search

- **One header per page.** Every global view (home, country, Gulf, Compare) has one site bar: the
  product name linking home, a breadcrumb built from the manifest groups (Home › Gulf littoral ›
  Iran), search, What's new, How to read this, How this works, Glossary, Copy view link and the
  system picker; the page title follows it. Integration had produced two stacked headers on
  country, Gulf and Compare pages, about 240 px on a phone before any content; the design red team
  caught it and it was consolidated. The theatre keeps its own bar (§9), which carries the same
  breadcrumb, picker and a Compare link.
- **Phone:** at 600 px or less a "Menu" toggle folds the secondary tools; search and the picker stay
  visible. The country bar fell from five rows to about three and is tested to stay under 22% of an
  844 px screen.
- **What's new** is in the site bar. On home it scrolls to the panel and focuses its heading; from
  another view it goes home as a new history entry.
- **Back and forward work:** every move is a history entry; `document.title` is set per route.
- **Search** is one ARIA 1.2 combobox with no dependency, focused by `/`. Matching ignores case,
  diacritics, Arabic and Persian letter variants, tatweel and direction marks, so Iran is found as
  ایران, ايران, Iran or iran; displayed text is never altered. It indexes systems, aliases, groups,
  views and glossary concepts. Theatre region names (one 17 kB file) are fetched on first focus;
  Crimea is labelled "Occupied unit, internationally Ukrainian". A country's regions are added once
  its page has loaded.
- **Glossary:** a native modal dialog with "How this works" in six steps and the terms the site uses,
  including the research-coverage states and the placement words, each read from the module that
  renders them so the glossary cannot drift from the page. `?help=glossary` opens it.

## 5. Safe compare workspace

`?compare=us,ca,sa` sets two to four monitored systems side by side, only on dimensions that mean the
same thing in every system. The URL is the only state; Back leaves the view.

- **Common basis:** what the system is, record as-of date, index ("No index" in words; the theatre
  reads "Has its own index, not comparable" and its value never appears), research maturity, latest
  systematic pass, source-group states (one count per state, zeros kept, never a percentage),
  campaign safeguards, most precise placement.
- **National context:** the four energy-context figures with unit, year and definition; "no data" is
  distinct from a reported zero, and the theatre reads "No single national figure".
- **Within each system only:** reporting environment, how records are sourced, source check dates,
  under a heading that says it is not a comparison.
- **Never shown:** event, attack or held counts, severity, any ranking or sort. "Not on this basis",
  "no data" and "could not be loaded" are three different cells.
- Only the chosen systems' `system.json` files are fetched, never their event lists, and a
  malformed file affects only its own column. MapLibre is no longer downloaded on this route (§15).
- **Export:** a 1600×900 PNG carrying the title, systems, build date, context year and source, the
  research-coverage states, the no-index meaning, "Not comparable: event counts" and, added by the
  analyst red team, the caveat that a larger national figure does not mean a more important country.
- Entry points: the country header, the home actions, and the theatre's Tools menu.

## 6. Research coverage UX

The country "Research coverage" tab now answers "how well has this country actually been searched?"
in plain words.

- One card per source group (the research plans call them lanes): source family, how it is searched
  with search and item counts, languages required versus run with missing ones named, search window,
  covered-through date, what the source allows, the limitation, and a folded note of what the search
  learned. An overview table jumps to each card.
- States are text plus a distinct shape, all one neutral colour, and never a percentage.
- **One vocabulary everywhere.** The first-time-user pass found one fact described three ways ("not
  exhaustive", "finished", "declared complete"); Compare had a five-bucket map whose "declared
  complete" bucket merged three different build states, and that went into the PNG. All surfaces
  (country header, tab, home, Gulf cards, Compare and its PNG, the empty-corpus page, the glossary)
  now read one module that uses the build's eight lane states and matches the build's rule for rule:
  "Every published item read", "Searched through the publisher's latest release", "Planned searches
  run (not exhaustive)", "Partly searched", "Source unavailable", "Stopped at this site's search
  limit", "Not started", "Logged in an earlier format". A typical line reads "6 source groups: 5 with
  planned searches run (not exhaustive) · 1 with the source unavailable."
- Research coverage and source health are separate headed blocks, with one line saying neither
  implies the other.
- **Campaign systems** never show an outcome count, even if a served log carried one; "under review"
  appears only where the build says so, and in the past tense for older passes.
- When a country has no published record, the tab says there is no recovery research and no citation
  to describe, instead of listing zeros.
- A real gap surfaced in the data: the Saudi OPEC-archive lane requires English and ran in none. It
  shows "Not run in: English".

## 7. Country pages

- **Event cards:** date, class and cause tags, title, summary, then labelled rows for effect,
  placement, recovery and review. On campaign records the recovery row is "Later status" and reads
  as withheld. The evidence block says "N cited pages · M originating statements" and says plainly
  when a record rests only on Wikipedia or an aggregator; the origin rule is mirrored in the browser
  and checked record by record against the build's own count.
- **Evidence Inspector** (§11).
- **Record links:** "Link to this record" on every card that has a stable anchor, `?sys=<id>#ev-<id>`.
  Following one opens the full list, scrolls to the record and marks it. A campaign record gets an
  anchor only if its id is the build's opaque form, so Saudi Arabia's campaign records, whose ids
  name facilities, get none.
- **Empty corpus** (Bahrain, Iran, Oman, Qatar, UAE): leads with "No qualifying records in the current
  reviewed corpus — this is not evidence that no disruption occurred", then what was searched, how
  the country reports, national context, sources, safeguards and what remains incomplete. No zeros,
  no held counts, and the map shrinks instead of filling the first screen with an empty country.
- **Why no score:** a plain paragraph, then "No score is not a score of zero", then what the page
  shows instead; technical detail is folded. File names and "open decision" wording are gone.
- **Filters:** a region filter that could filter nothing is replaced by one line saying why; a Year or
  Type filter with one option says so instead. The selects are styled like the rest of the site.
- **One placement vocabulary**, from one module: National; Several regions; One region; National,
  under safeguards. It replaced five labels for "not placed in one region". On aggregating surfaces a
  safeguarded row keeps an opaque list position, now written "list entry 15" rather than a raw key.
- **Saudi Arabia's older convention** is stated plainly: its older records name facility and region;
  the newer Gulf pages record an attack for the country as a whole. Its data and convention are
  unchanged (owner rows D-11/D-33, §29).

## 8. Gulf overview

- **First screen:** purpose, a caveat line visible at every width ("National context only · not
  comparable between countries · no index or score"), the controls on the map's top edge, the map,
  and beside it the chosen figure's facts and the member list.
- **Neutral default:** the map opens uncoloured but with members distinctly filled and outlined, and
  says "Geography only — choose a national figure to colour the map". The first pass read the grey
  map as broken.
- **Members** are listed in name order beside the map. Pointing or focusing highlights the member;
  Enter or a tap selects it and zooms to its box; a selection panel offers Open, Zoom to, Show all and
  Clear, so nothing is hover-only.
- **Legend:** in-view, filtered-out, other and selected each have their own swatch; zero and no-data
  get their own when they occur.
- **Feed:** a campaign country's consecutive covered rows fold into one line with no count, and a
  line explains why a record reads "National" here while its country page may say more. A fold
  regression found during integration (rows that merely carried a list key were folded as campaign
  records, mislabelling Kuwait's grid faults) was caught in the browser and fixed; the fold now reads
  only the members' withheld flag, and tests pin it on both served lists.
- **Brief export bug fixed:** the export copied the live style and camera, so a selection highlight
  and the reader's zoom would have gone into the brief. It now always frames the whole group and
  drops selection and hover layers.

## 9. Russia theatre UX

No score, weight or meaning changed. The work was to make the existing figures readable.

- **The misleading status chip is gone.** A withheld row shows only "Status withheld", which expands
  to its meaning. Rows with released, dated evidence keep that status without the modelled chip,
  impairment age or horizon.
- **Top bar:** Home › Russia, Belarus & Crimea breadcrumb (one name, also used in the tab title and the
  dossier), system picker, a view switch (Analyze · Map focus · Briefing & export) derived from
  existing state, and tools folded behind "Tools" below 1280 px, including "Compare systems".
- **Headline:** one decimal everywhere a level is shown (ribbon, briefing, Inspector, methodology,
  What's new); changes keep two. A scale line states what the number is, from METHODOLOGY §1, shared
  by the ribbon and the methodology panel. "Why this number?" opens the Inspector, or the historical
  breakdown when the timeline is scrubbed. The peak to date is shown.
- **A live but tiny value no longer reads "0.0".** Electric generation (0.03) and some regions showed
  "0.0", which means "measured, nothing disrupted". They now show "<0.1"; an exact zero stays "0.0"
  and a missing value stays "—".
- **"Why this number?" said coal had documented unscored events; it has none.** The text now uses the
  build's own count and says a zero is not evidence none occurred.
- **Sector cells were zero pixels wide at every width**; they are visible, each with its basis
  (capacity share or event-burden proxy). Both coverage ratios sit beside the headline at the same
  size at every width.
- **Tab bug at 1440 px:** the closed dossier drawer made the root scrollable, so focusing into it slid
  the app about 400 px left. Fixed with `overflow: clip` and hidden closed drawers.
- **Text defects fixed:** "a oil terminal", a spliced methodology sentence, three names for the
  theatre, developer wording in the build ledger, raw ISO dates.
- **Phone:** stacked header within its height cap, compact legend with "All keys", attribution behind
  its own button, presets on one row.

**Recovery wording (wave 3).** The after-pass evaluator still read the recovery block as "these
Russian facilities are down now". The figures were right; the words were facility-status words.
The rule behind them is that, while attacks on energy facilities are being reported, a restoration
report is used only once it is 60 days old (`campaign_policy.evidence_embargo_days` in the
snapshot). A "no report" count therefore means no public restoration report dated on or before the
status cut-off; the facility may already be working. Every surface now says that:

| Before | After |
|---|---|
| Facilities awaiting reconstitution | No restoration report by the cut-off |
| Median impairment age | Median days since disruption, no report |
| Unresolved disruptions | No restoration report by the cut-off, with one shared meaning sentence |
| Reconstitution backlog | Modelled reconstitution backlog, "an assumption, not a report of any facility" |
| "Impaired · impaired 54 d" | "No restoration report · 54 d since disruption" |
| Current activity (camera preset) | Regions with no report, "not a map of facilities down now" |
| "impaired, but no capacity figure" (rankings, zero notes, Inspector) | "disruption reported, but no capacity figure" |
| Planned economic indicators / "ready · no figures yet" | Economic figures not yet available, with the reason |

The meaning sentence, the cut-off date and the delay come from one module (`web/src/statusDelay.ts`)
reading the served policy, so the wording cannot drift from the rule. The home "What is withheld?"
now has a theatre line; it reads the delay from a new manifest field (`status_delay_days`), because
the home page does not load the theatre snapshot.

**A real bug found on the way.** With a region selected (for example Samara Oblast) the Recovery tab
showed the whole area's tiles and the whole area's facility list, including other regions'
facilities, under the region's name. The Repair-burden tab did the same for three national figures.
The Recovery tab now heads its pooled figures "whole monitored area · not filtered to <region>",
lists only the region's facilities (with an empty state saying no evidence is not a statement about
current condition), and area-wide repair figures carry "· all regions". A Playwright test pins it,
including that another region's facility is absent.

## 10. Maps

- The shared map component (home, country, Gulf) has HTML zoom and reset buttons of at least 44 px,
  credits as text under the map rather than an icon over it, an optional empty-state note, a "Same
  data as a table" link and a highlight layer. No basemap, tiles, glyphs or symbol layers were added.
- The home world map no longer captures the mouse wheel: the page scrolls, and zoom needs Ctrl or ⌘
  with the wheel, the buttons, or a click into the map.
- A country map with no record placed in a region shrinks to a smaller fixed height instead of
  dominating the first screen.
- The theatre's controls on the map are 44 px; its header controls stay 24 px (§14, §29).

## 11. Evidence and provenance

- **Evidence Inspector** per record: a button with `aria-expanded` whose content renders only while
  open. It answers in plain words why the record is included (with the rule version and clause in a
  folded "Technical detail"), where each report came from (role, language, date, whether opened,
  whether the link still loaded), how many originating statements there are, what the record does
  not establish, and the review verdicts. Campaign records show no headline, capacity figure or later
  status, enforced in code.
- **Per-citation link state:** each served citation carries `link_check` from the last automated visit
  (§18). The safety red team added a build gate so the curated file can never name an unpublished
  address (§24).
- **Original headlines** sit on their own line with language and direction set, separate from the
  English gloss.

## 12. Briefing and exports

- **Theatre briefing on screen** no longer draws presets, drawer toggles and a duplicate scope note
  under its frame; the legend moves out of the way and controls sit on the map. The exported PNG is
  unchanged.
- **Country PNG:** found broken for countries whose live map is a short strip (the UAE export failed
  with "the rendered map came back blank"), because it copied the live camera into a 1600×900 frame.
  It now frames the country's own bounds with padding for the text panels. The frame text formats
  dates and names countries grammatically.
- **Gulf brief** always frames the whole group, without selection or hover (§8).
- **Compare PNG** (§5) carries the same research-coverage lines as the page.

## 13. Mobile

Driven with Playwright at 390×844, 768×1024, 1440×900 and 720×450 at device scale 2 (the 200% zoom
case) before any source was read.

- Country pages put the navigation below the whole event list on a phone, because phone CSS reordered
  the page. Reordering now happens only inside the page's `<main>`, so the header stays first and the
  map still starts above 430 px.
- At 200% zoom the theatre map was squeezed to about 190 px under its legend; at heights of 520 px or
  less the page now scrolls vertically and the map keeps at least 340 px.
- Compare was 290 px wider than the screen; fixed. No view scrolls sideways at 390 or 720 px.
- Touch targets: 44 px minimum on primary controls at 600 px or less or on a coarse pointer, 24 px on
  inline disclosures; the theatre header is the documented exception (§29).
- The phone site-bar menu (§4); the theatre's weighting clause moves to screen-reader text on phones
  so its header stays inside its height cap.

## 14. Accessibility

- One `h1` and one `main` per view; heading levels never skip; tables captioned.
- Escape closes every disclosure, the evidence inspector, the theatre's methodology dialog (which
  now takes focus and traps Tab), the tools menu (focus returns to its toggle) and any open native
  `<details>`, except inside the glossary dialog, which keeps its native behaviour.
- No two controls share an accessible name where they do different things: 119 buttons named
  "Evidence inspector" now carry the record's title and date as hidden text, and the same was done
  for Compare's definition toggles, the glossary, the theatre filters and the Gulf member buttons.
  Citation links keep their publisher names: their purpose is set by the card around them (WCAG
  2.4.4), and repeating hidden text on hundreds of links would add noise. A lead decision (§29).
- Reading order reaches the header before the theatre's drawer toggles; Start here does not steal
  focus on a first visit.
- One shared `prefers-reduced-motion` rule; more specific transitions had been overriding the old one.
- Focus rings on the theatre's region search.

## 15. Performance

Measured with a reusable tool (`web/scripts/measure-routes.mjs`: cold cache, requests, bytes, time to
map idle, maps created, long tasks, layout shift), five runs per route, before and after.

- **Home layout shift fell from 0.86 to under 0.001.** The manifest and the national context each
  inserted content above the map; home now waits for both before drawing its body, and the map draws
  into a fixed box.
- **One request per file per page.** A shared request cache covers the manifest, country bundles, the
  world map, group context, recent evidence, data quality and the theatre bundle. Before, home → Gulf
  → home downloaded the 428 kB world map three times. A failed request is never kept, so the next
  caller retries.
- **Prefetch:** a route's data starts with its code download; hovering or focusing a card fetches only
  that system.
- **Country pages** no longer fetch the national-context file (164 kB) until a tab or export needs it.
- **The world map is a lazy chunk**, so MapLibre (1.05 MB) is off the home page's critical path.
- **The release red team found three regressions on the integrated build** and fixed them: Compare
  downloaded MapLibre (its transfer fell from 462 kB to 183 kB); opening a country page after Compare
  fetched its `system.json` twice; searching on home and then opening the theatre fetched the region
  file twice. Playwright now asserts each.
- Not changed: the theatre still loads about 3.4 MB because its map uses all of it at load. Splitting
  the 2.4 MB line file is a candidate for a later iteration.

## 16. Error containment

- **A failure stays where it happened.** A view boundary wraps each route, keyed per route so a
  failure does not carry over; its fallback keeps the system picker and offers a way home, a reload
  and a clean link. Panel boundaries wrap each home panel, each Gulf section and each country tab.
- **Validation at load** for every file a view iterates over: manifest, group context, recent
  evidence, data quality, world geometry, What's new and the country fields that had none. A
  malformed optional part is dropped, never invented; a malformed required part refuses the file.
- Tested in the browser: missing and malformed country files, malformed Gulf context with the theatre
  untouched, garbage coordinates in one region, a wrong-type leaf caught by its panel, a country code
  chunk that returns 404.

## 17. Gulf research continuation

The iteration-20 continuation left seven lanes stopped by the shared search allowance (AE4, BH1, IR6,
KW4, QA3, SA1, SA5) and one Saudi archive lane (SA4) unworked. All eight ran in this pass, under the
same plan and inclusion rule, with no candidate threshold lowered.

- **Ran their remaining declared queries:** AE4, BH1, IR6, KW4, QA3 and SA5 (declared search
  complete), SA1 (every declared query run; partial because the archive endpoints refuse an automated
  reader, which is a statement about the source).
- **SA4** (the OPEC report archive) was limited to the period before the campaign, so that no current
  status of an attacked facility was researched. The archive refused access; the lane reads "source
  unavailable", and its required English-language pass is shown as not run.
- **No candidate met the inclusion rule.** The curated corpus is unchanged; the review queue
  re-imports byte-identical.
- The research log records the pass for the six systems worked (`EDM_PASS=21`). A lane worked in this
  pass replaces its iteration-20 entry; a lane not worked is carried forward and marked so.
  Campaign systems publish no outcome counts, only whether review continues.

After the pass no Gulf lane is stopped by the search allowance. Lane states per Gulf system:

| System | Declared search complete | Partly searched | Source unavailable | Last systematic pass |
|---|---|---|---|---|
| Bahrain | 1 | 1 | 1 | 12 Nov 2026 |
| Iran | 5 | 0 | 1 | 12 Nov 2026 |
| Iraq | 3 | 0 | 2 | 11 Nov 2026 |
| Kuwait | 2 | 2 | 0 | 12 Nov 2026 |
| Oman | 1 | 4 | 0 | 11 Nov 2026 |
| Qatar | 2 | 1 | 0 | 12 Nov 2026 |
| Saudi Arabia | 1 | 3 | 1 | 12 Nov 2026 |
| UAE | 1 | 2 | 1 | 12 Nov 2026 |

## 18. Link health

`scripts/check_source_links.py` made one automated visit to each cited page on 12 November: 299
cited addresses, 277 reachable, 1 redirected, 9 blocked, 4 dead, 8 errors (the PHMSA report generator
returning server errors). Every dead link was already dead in the iteration-20 run; none is new. The
check now covers fewer addresses than in iteration 20 (349) because the records held in iteration 20
are no longer cited.

**New this iteration: per-citation state.** Each served citation now carries the state of its last
check (`link_check`), and the evidence inspector says, per citation, whether it still loaded. The
curated file gains `link_states`, keyed by address. Before it was merged, every address in it was
checked against the served payloads: all are cited by published records, and held records never
enter the curated corpus, so the file names no unpublished citation.

**Not a signal: "content changed".** The checker compares a page's hash with the previous run's. On
this run nearly every page reported a change, because news pages rotate advertising and related
links. The flag stays local and is not used as evidence that an article was edited.

## 19. Data and model changes

No score, weight, half-life, sector definition or inclusion rule changed. The headline moved only
with time and the daily data.

| Change | Where | Why |
|---|---|---|
| `record_reviewed` on each manifest country entry (a date, or null) | `pipeline/build_systems.py` | Home cards say when the newest published record was reviewed |
| New payload `global/whats_new.json`, registered in `artifacts.GLOBAL_PAYLOADS` | `pipeline/whats_new.py` | What changed, by cause, from published payloads only (§3) |
| `lineage.previous_dated_build`: the last committed build dated before this one | `pipeline/lineage.py` | One baseline per day; any number of same-day rebuilds produce identical output |
| The theatre ledger `build_changes.json` uses the same dated baseline | `pipeline/diff_builds.py` | A second build of the day re-baselined onto the morning's commit and published an empty story over the since-yesterday one (§27) |
| Facility attribution ties break on asset id | `pipeline/diff_builds.py` | Row order followed the hash seed, so two builds of identical data differed |
| `link_check` on each served citation; curated `link_states` keyed by address | `scripts/check_source_links.py`, `pipeline/build_systems.py` | Per-citation link state in the Evidence Inspector (§11, §18) |
| Home index-card meaning text | `pipeline/build_systems.py` | Now carries the weighting from METHODOLOGY §1 |
| Opaque attack id token: six hex digits of an HMAC keyed by a local secret; the build refuses any other form | `scripts/import_candidates.py`, `pipeline/build_systems.py` | An unkeyed hash could be reversed by guessing facility names (§24) |
| New build gates `link_health_problems` and `held_wording_problems` | `pipeline/build_systems.py` | §24 |
| One Saudi research-gap sentence reworded | `data/curated/systems/sa/system.json` | It described a held record (§24) |
| Research log entries for pass 21 in six Gulf systems | `data/curated/systems/<id>/research_log.json` | §17 |

| `status_delay_days` on the theatre's manifest entry, from the snapshot's campaign policy (null when no policy applies) | `pipeline/build_systems.py` | The home "What is withheld?" theatre line states the delay without loading the 283 kB snapshot (§9) |
| Zero notes and the data-quality "cannot tell you" answer reworded from "impairment" to "reported disruption with no published restoration report" | `pipeline/explain.py`, `pipeline/data_quality.py` | §9; text only, the index and every count unchanged |

## 20. Tests

<!-- LEAD: final counts at the release gate -->

## 21. Mutations

<!-- LEAD: final campaign result -->

## 22. First-time-user review

The 20-task pass of §2 was repeated on the integrated build (`8bf2160`), on desktop and phone, by an
evaluator who had not built any of it.

| Result | Before (production, iteration 20) | After (`8bf2160`) |
|---|---|---|
| Obvious | 6 | 13 |
| Findable | 12 | 7 |
| Not stated | 1 | 0 |
| Misleading | 1 | 0 |

The misleading status chip was gone and "what should I click next?" was answered on the first screen.
The pass ranked five remaining problems. All five were then worked:

1. **The theatre's recovery wording still read like facility status** ("awaiting reconstitution",
   "impairment age", "impaired"), and the home "What is withheld?" named only the Gulf states although
   the theatre also has a withholding rule. Fixed: every recovery count is
   now worded as "no restoration report by the cut-off" with the delay rule beside it, and the home
   panel has a theatre line (§9). The pass also found and fixed a region-filter bug in the Recovery tab.
2. **Research-coverage vocabulary drifted** between surfaces, and "declared complete" in the Compare
   PNG overstated thoroughness. Fixed with one vocabulary module (§6).
3. **Five labels for "not placed in one region".** Fixed with one placement vocabulary (§7).
4. **What's new was buried.** It is now in the site bar (§4). It still lists kinds of change, not the
   records changed; linking each change to its records is in §31.
5. **Phone leftovers:** the country header was five rows (now about three, behind a Menu), the
   selects were unstyled (fixed), the theatre's ratio captions are hidden on phones (kept, to stay
   within the header cap), maps show no loading indicator for two to three seconds (open, §31).

Engineering-demo leftovers it named: the raw row key (now "list entry N"), the redundant "Search
systems" button (removed), theatre jargon and process text (reworded in the same pass: "Full AOI", "Recovery
 lifecycle explorer" and the generator note on summaries now read in plain words, §9).

## 23. Analyst red team

| Finding | Status |
|---|---|
| A single record could not be cited: the anchor existed but nothing showed it | Fixed: "Link to this record" on every anchored card |
| The Compare PNG lacked the caveat that a larger national figure does not mean a more important country | Fixed |
| A UTC build date beside a local "as of" date read as a future date | Fixed: dates computed on the reader's calendar |
| The build ledger showed developer wording ("production ancestor", ISO dates) | Fixed |
| Recent evidence said "by event date" but sorts by an episode's latest date | Wording fixed |
| The Gulf event list ended items with a placeholder | Wording fixed; linking each to its record is open |
| Country pages cannot filter events by class or date; Compare has no CSV export | Open: new features (§31) |

The Kuwait task worked end to end: three records, every source linked, the inspector answering its
questions.

## 24. Safety red team

The safety red team tried to infer campaign-sensitive information from the new surfaces, using only
the public app and committed files. No surface exposed facility status, the region, facility or
operator of an abstracted record, or an incident coordinate, and none ranked systems. It found four
inference paths, all fixed with a gate, a test and a mutant:

| Surface | Finding | Fix |
|---|---|---|
| Record anchors and opaque attack ids | **Latent leak** (no abstracted attack record is published yet). The id token was an unkeyed hash of the queue id, and many queue ids contain a facility word, so hashing guesses at the published date and class could recover the facility. Lane-numbered tokens also said that a sibling candidate existed | Keyed HMAC token from a local secret that never leaves the machine; the build refuses any token that is not six hex digits |
| Curated link-health file | **No gate existed.** Every address in it was published, but a record withdrawn after a check would leave its address, which for Saudi Arabia names the facility | Build gate: no unpublished address, no unexplained redirect, no per-system count above the published citations |
| What's new | **Partial.** Per-record review changes were hidden for campaign systems, but a system-level line still announced a re-review | Suppressed for campaign systems |
| Saudi research gap | **Live rule breach**, re-surfaced by the new Research coverage tab: a sentence described a held record | Reworded; a new gate checks the gap and log prose of every campaign system |

Tried and blocked: matching What's new dates against country pages; row keys across builds; Compare
cells and PNG; the search index; the empty-corpus page; the Gulf member list and brief; theatre
withheld rows; every PNG export; the Gulf research logs. A final-artifact scan of every served file
and the built bundle found no incident coordinate, range field, campaign held count, route wording or
reference to a local file.

The lead also checked, before merging per-citation link state, that every address in the curated file
is cited by a published record; held records never enter the curated corpus.

## 25. Methodology red team

| Finding | Status |
|---|---|
| A live but tiny value showed "0.0" (§9) | Fixed: "<0.1" |
| "Why this number?" claimed documented unscored coal events; there are none | Fixed from the build's own count |
| What's new showed the index at two decimals against the Inspector's one | Fixed |
| The theatre scale line left out the weighting in METHODOLOGY §1 | Fixed: one shared string |
| The ribbon and What's new compare against different earlier builds and seemed to disagree | Wording fixed: the ribbon's tooltip names its baseline and points to the other. Two baselines kept (§29) |
| Compare's "declared complete" bucket contradicted "(not exhaustive)" elsewhere | Fixed by the one vocabulary (§6) |
| What's new says only "scoring method or campaign classification changed" for the theatre, without saying which | Open (§31) |
| A served coal limitations string still says documented strikes are not scored | Open; not rendered anywhere found (§31) |

Also confirmed: "No index" never renders as 0; "Not on this basis" stays distinct from "no data";
unknown, not applicable and not yet researched stay distinct; nothing is ordered by a figure.

## 26. Test-architecture red team

The test-architecture red team asked one question of every new surface: if this behaviour broke, would
any test notice? It wrote 95 behavioural mutants against the shipped TypeScript and Python (changes
to what the code does, not to strings a test happens to grep). **36 survived every layer** before it
added tests. The most serious:

| Mutant | What broke and nothing noticed |
|---|---|
| C04 | Compare's safeguards row said "No" for an UNCERTAIN Gulf campaign system |
| C05 | Compare said a country-level system placed its attack records by region |
| C06 | A lane blocked by its source was counted as searched to completion |
| R01–R03 | The research-coverage pages dropped the campaign signal (state, policy, under review) |
| T01, T02, T05 | Theatre rows showed modelled status for withheld records |
| E08–E10 | An unchecked citation read as reachable; the build could mark every citation reachable |
| W06, W07, W11, W13, W14 | What's new: a restricted system's changes, a diverged baseline, ordering by size of change |
| P04, P07, P09, P10 | Error boundaries that did not contain, failed requests kept in the cache |

Of the other 59, 14 were caught by pytest, 38 only by vitest and 8 only by Playwright. That matters
because the mutation campaign runs pytest alone, so a behaviour guarded only by vitest or a browser
test was invisible to it. The team added `tests/test_iteration21_testarch.py` (45 tests) and `web/src/global/testarch.test.tsx`,
which load the shipped TypeScript through esbuild and Node, so pytest now catches 90 of the 95.
**81** were registered in the campaign (`ITER21_TESTARCH_MUTATIONS`); the rest were already
caught by existing pytest, or were folded together when the code they targeted was merged. To make the behaviour
testable it exported a few pure helpers (`exportBlocker` and `moveColumn` in `compare.ts`, the
`WhatsNewPanel` view split from its loader, `EpisodeItem`, `EvidenceInspector`).

It also fixed a resilience e2e whose premise had gone stale (the injected bounds fault had to move to
a system that still has bounds) and one test fixture that named a real facility.

Its tests were then ported to the single coverage and placement vocabulary that landed in parallel
(§6, §7), and six mutant anchors re-written to the new code. Run on main after that merge, the 81
were all caught.

**Weak spots it left, honestly:** mutant 257 (every country sharing one error-boundary key) is caught
only by a source-text guard, not by behaviour; mutant 263 is caught through the count of a
manifest's files rather than the files themselves.

## 27. Release engineering

**Integration.** Eight feature branches were built in separate checkouts, each on its own preview
port, and merged one at a time with tests between merges. Conflicts were resolved by union unless the
features disagreed; the notable ones were the route switch (Compare placed inside the per-route error
boundary), the home and Gulf layouts (one feature's layout plus the other's boundaries and prefetch),
one shared lane-chip helper where two had been written, and the curated link-health file (rebuilt from
the current check rather than either branch's copy). Wave-2 red teams and two wave-3 fix passes then
ran against the integrated tree.

**Incident.** Early in the iteration, removing a test checkout whose dependency folders were
directory junctions deleted the main checkout's `node_modules`, raw-data cache and local review queue.
The queue was restored from a same-day copy and replayed from the known scripts; all twelve country
systems re-imported byte-identical to the committed build. Checkouts now copy those folders and never
link them.

**The daily refresh path** (found by the release red team, all fixed and tested):

| Defect | Fix |
|---|---|
| A second build on the same day re-baselined the theatre ledger onto the morning's commit; the change detector then reported a change and the bot would commit an empty story over the since-yesterday one. The committed payload had this shape | Ledger uses the dated baseline, the same rule as What's new |
| Facility attribution order followed the hash seed | Deterministic tie-break |
| `ci_data_changed.py` read only top-level files, so a change confined to `global/` or a country folder never published | Recursive scan |
| A frontend-reading pytest could block the bot on runners whose Node lacks type stripping | Flag passed, clean skip on old Node; CI's Python job pins Node 22 |
| Frontend source checks sat in the publication gate, so a frontend refactor could freeze publication | Marked repository hygiene; CI still runs them |
| `staging_paths.py` printed CRLF on Windows, so local staging added nothing | Bare LF |

A simulation in a scratch clone (bot build, same-day rerun, next-day build) confirmed: a same-day
rerun is byte-identical after normalisation and the detector says no change; the next day both the
ledger and What's new name the previous day's build.

<!-- LEAD: release gate table and moving-main integration -->

## 28. Production

<!-- LEAD: at release -->

## 29. Remaining owner decisions

**Unchanged and still the owner's** (OWNER_DECISION_MATRIX_20 is authoritative; conservative current
behaviour stays in force):

- **D-11 / D-33, Saudi harmonisation.** Option B remains: Saudi Arabia keeps its older convention, its
  records are not migrated to the newer Gulf form, and the country page says so plainly (§7).
- **D-34** old public history and old deployments, **D-35** methodology re-bases, **D-36**
  event-total interpretation, **D-37** EEA-3 interpretation, and **Release Rule A**: unruled.

**New this iteration, raised by the safety red team:**

- Should campaign systems keep showing per-record review dates (`reviewed_at`, the home card's
  `record_reviewed`)? They have been public since iteration 14; hiding them is a product decision.
- Should Saudi Arabia's superseded lane findings, which mention a 2022 record no longer published,
  stay in the served research log? The current UI does not render superseded lanes.

**Decided by the lead, not owner decisions** (recorded so they can be revisited):

- The theatre header controls stay at 24 px, which meets the WCAG 2.2 AA target-size minimum; 44 px
  broke the tested cap that keeps the header under 31% of a phone screen. Controls on the map are
  44 px.
- Citation links keep their publisher names (WCAG 2.4.4, purpose from context).
- Two "since" baselines are kept: the ribbon compares with the previous build, What's new with the
  previous dated build; the ribbon's tooltip names both.
- The theatre headline keeps its severity colour; the home card uses the neutral accent.
- "National" covers both whole-country and safeguarded records in What's new, because What's new
  cannot tell them apart without saying more than the aggregating surfaces do.

## 30. Remaining research gaps

- After the continuation pass (§17) no Gulf lane is stopped by the search allowance, but many remain
  "partly searched" or "source unavailable" because the sources refuse automated readers or keep only a
  recent window. Those are statements about the sources, not unfinished work.
- The Saudi OPEC-archive lane has not run its required English-language pass; the archive refused
  access.
- Bahrain, Iran, Oman, Qatar and the UAE have no published record. That is not evidence that no
  disruption occurred, and the pages say so.
- Per-citation link state is from one automated visit; the PHMSA report generator returned server
  errors, so those citations read as unchecked rather than dead.

## 31. Recommended next iteration

1. **What's new at record level** for non-campaign systems: link each change to the records it
   affected, using the country-page anchors, and say which of method or classification changed for the
   theatre.
2. **Event filters and CSV export** on country pages and Compare (analyst red team).
3. **A map loading indicator**; theatre and country maps are blank for two to three seconds.
4. **Split the theatre's 2.4 MB line file** so its map can draw before all of it arrives.
5. **The owner decisions in §29**, especially Saudi harmonisation and review dates on campaign systems.
6. Retire the served coal limitations string that no surface renders, after confirming no consumer
   reads it.
